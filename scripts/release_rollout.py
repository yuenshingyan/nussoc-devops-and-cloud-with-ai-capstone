"""Apply one reviewed image change and observe exact rollout identity, never automatic rollback."""

from time import monotonic, sleep

from scripts.release_deployment import (
    image_reference,
    require,
    spec_sha256,
    target_fields,
    verify_patch_response,
)
from scripts.release_http import DeploymentClient, remaining


def deployment_ready(deployment: dict) -> bool:
    """Require the current generation and all desired replicas, not just Available=True."""
    metadata, spec, _ = target_fields(deployment)
    desired = spec.get("replicas")
    require(type(desired) is int and desired > 0, "ROLLOUT_REPLICAS_INVALID")
    status = deployment.get("status", {})
    require(type(status) is dict, "ROLLOUT_STATUS_INVALID")
    conditions = status.get("conditions", [])
    require(type(conditions) is list, "ROLLOUT_STATUS_INVALID")
    for condition in conditions:
        require(
            type(condition) is dict
            and type(condition.get("type")) is str
            and bool(condition["type"])
            and type(condition.get("status")) is str
            and condition["status"] in {"True", "False", "Unknown"},
            "ROLLOUT_STATUS_INVALID",
        )
        if (
            condition.get("type") == "Progressing"
            and condition.get("status") == "False"
            and condition.get("reason") == "ProgressDeadlineExceeded"
        ) or (condition.get("type") == "ReplicaFailure" and condition.get("status") == "True"):
            raise RuntimeError("ROLLOUT_CONTROLLER_FAILED_INSPECT_MANUALLY")
    names = (
        "observedGeneration",
        "replicas",
        "updatedReplicas",
        "readyReplicas",
        "availableReplicas",
        "unavailableReplicas",
        "terminatingReplicas",
    )
    for name in names:
        value = status.get(name, 0)
        require(type(value) is int and value >= 0, "ROLLOUT_STATUS_INVALID")
    require(status.get("observedGeneration", 0) <= metadata["generation"], "ROLLOUT_STATUS_INVALID")
    return (
        status.get("observedGeneration") == metadata["generation"]
        and all(status.get(name) == desired for name in names[1:5])
        and status.get("unavailableReplicas", 0) == 0
        and status.get("terminatingReplicas", 0) == 0
    )


def controlling_owner(metadata: dict, kind: str) -> str | None:
    """Resolve one controller UID without treating labels as ownership."""
    owners = metadata.get("ownerReferences", [])
    require(type(owners) is list, "ROLLOUT_OWNER_INVALID")
    require(all(type(owner) is dict for owner in owners), "ROLLOUT_OWNER_INVALID")
    controllers = [owner for owner in owners if owner.get("controller") is True]
    require(len(controllers) <= 1, "ROLLOUT_OWNER_INVALID")
    if not controllers:
        return None
    owner = controllers[0]
    if owner.get("kind") != kind or owner.get("apiVersion") != "apps/v1":
        return None
    uid = owner.get("uid")
    require(type(uid) is str and bool(uid), "ROLLOUT_OWNER_INVALID")
    return uid


def listed_objects(document: dict, kind: str) -> list[dict]:
    """Require a complete bounded list, never count a partial pagination response."""
    require(
        type(document) is dict
        and document.get("kind") == kind + "List"
        and document.get("apiVersion") == ("v1" if kind == "Pod" else "apps/v1")
        and type(document.get("items")) is list
        and len(document["items"]) <= 128
        and type(document.get("metadata")) is dict
        and document["metadata"].get("continue", "") == "",
        "ROLLOUT_LIST_INVALID",
    )
    objects = document["items"]
    uids = set()
    for item in objects:
        # Kubernetes list members can omit TypeMeta even when the list has an exact kind.
        require(
            type(item) is dict and (item.get("kind") is None or item.get("kind") == kind),
            "ROLLOUT_LIST_INVALID",
        )
        metadata = item.get("metadata")
        require(
            type(metadata) is dict
            and metadata.get("namespace") == "finsecure-pay"
            and type(metadata.get("uid")) is str
            and bool(metadata["uid"]),
            "ROLLOUT_LIST_INVALID",
        )
        require(metadata["uid"] not in uids, "ROLLOUT_LIST_INVALID")
        uids.add(metadata["uid"])
    return objects


def ready_pod_uids(deployment: dict, replica_sets: dict, pods: dict, digest: str) -> list[str]:
    """Verify lineage and runtime digest; old, foreign or terminating Pods cannot count."""
    metadata, spec, _ = target_fields(deployment)
    expected_image = image_reference(digest)
    owned_sets = {
        item["metadata"]["uid"]
        for item in listed_objects(replica_sets, "ReplicaSet")
        if controlling_owner(item["metadata"], "Deployment") == metadata["uid"]
    }
    ready = []
    pending = False
    for pod in listed_objects(pods, "Pod"):
        info = pod["metadata"]
        require(
            controlling_owner(info, "ReplicaSet") in owned_sets,
            "ROLLOUT_FOREIGN_MATCHING_POD",
        )
        status = pod.get("status", {})
        require(type(status) is dict, "ROLLOUT_POD_STATUS_INVALID")
        # Retained terminal Pods cannot serve traffic and are not active rollout replicas.
        if status.get("phase") in ("Succeeded", "Failed"):
            continue
        if info.get("deletionTimestamp") is not None:
            pending = True
            continue
        pod_spec = pod.get("spec")
        require(type(pod_spec) is dict, "ROLLOUT_POD_SPEC_INVALID")
        containers = pod_spec.get("containers")
        require(
            type(containers) is list
            and len(containers) == 1
            and type(containers[0]) is dict
            and containers[0].get("name") == "api",
            "ROLLOUT_POD_SPEC_INVALID",
        )
        if containers[0].get("image") != expected_image:
            pending = True
            continue
        conditions = status.get("conditions", [])
        require(
            type(conditions) is list and all(type(c) is dict for c in conditions),
            "ROLLOUT_POD_STATUS_INVALID",
        )
        ready_conditions = [c for c in conditions if c.get("type") == "Ready"]
        require(len(ready_conditions) <= 1, "ROLLOUT_POD_STATUS_INVALID")
        statuses = status.get("containerStatuses", [])
        require(type(statuses) is list, "ROLLOUT_POD_STATUS_INVALID")
        if (
            status.get("phase") != "Running"
            or not ready_conditions
            or ready_conditions[0].get("status") != "True"
            or not statuses
        ):
            pending = True
            continue
        require(
            len(statuses) == 1 and type(statuses[0]) is dict and statuses[0].get("name") == "api",
            "ROLLOUT_POD_STATUS_INVALID",
        )
        runtime = statuses[0]
        require(
            type(runtime.get("imageID")) is str
            and runtime["imageID"] in {expected_image, "docker-pullable://" + expected_image},
            "ROLLOUT_RUNTIME_IMAGE_MISMATCH",
        )
        state = runtime.get("state", {})
        require(type(state) is dict, "ROLLOUT_POD_STATUS_INVALID")
        if runtime.get("ready") is not True or type(state.get("running")) is not dict:
            pending = True
            continue
        ready.append(info["uid"])
    return sorted(ready) if not pending and len(ready) == spec["replicas"] else []


def deploy_and_wait(
    client: DeploymentClient, expected_uid: str, expected_spec_sha256: str, digest: str
) -> dict:
    """PATCH once, then observe at one-second intervals under the same remaining deadline.

    Original-candidate eligibility and registry proof must precede this mutation stage in
    trusted controller code. Polls are new status observations, not retries of failed HTTP
    requests. Any failed request, drift, conflict or timeout stops for inspection. This
    function does not perform a smoke check or grant release authorization.
    """
    started = monotonic()
    before = client.get_deployment()
    _, before_spec, _ = target_fields(before)
    require(
        type(before_spec.get("replicas")) is int and before_spec["replicas"] > 0,
        "ROLLOUT_REPLICAS_INVALID",
    )
    after = client.patch_image(before, expected_uid, expected_spec_sha256, digest)
    while True:
        remaining(client.deadline)
        verify_patch_response(before, after, expected_uid, expected_spec_sha256, digest)
        if deployment_ready(after):
            pods = ready_pod_uids(after, client.get_replica_sets(), client.get_pods(), digest)
            if pods:
                # Close the observation window with another exact Deployment check.
                final = client.get_deployment()
                verify_patch_response(before, final, expected_uid, expected_spec_sha256, digest)
                if deployment_ready(final):
                    return {
                        "status": "rollout_verified",
                        "deployment_uid": expected_uid,
                        "generation": final["metadata"]["generation"],
                        "spec_sha256": spec_sha256(final["spec"]),
                        "pod_uids": pods,
                        "registry_manifest_digest": digest,
                        "elapsed_seconds": round(monotonic() - started, 3),
                        "smoke_verified": False,
                        "automatic_rollback": False,
                    }
        sleep(min(1.0, remaining(client.deadline)))
        after = client.get_deployment()
