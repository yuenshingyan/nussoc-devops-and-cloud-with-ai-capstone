"""Plan and check one image-only update; no I/O, credentials, retries or release authorization."""

from copy import deepcopy
from hashlib import sha256
from json import dumps
from re import fullmatch

REPOSITORY = "docker.io/yuenshingyan/finsecure-pay"
TARGET = "finsecure-pay"
CONTAINER = "api"
IMAGE_PATH = "/spec/template/spec/containers/0/image"


def require(allowed: bool, code: str) -> None:
    """Reject invalid control inputs without including server data in the error."""
    if not allowed:
        raise ValueError(code)


def json_types(value: object) -> None:
    """Prevent JSON serialization from silently coercing keys or custom Python values."""
    if type(value) is dict:
        for key, child in value.items():
            require(type(key) is str, "DEPLOYMENT_JSON_INVALID")
            json_types(child)
        return
    if type(value) is list:
        for child in value:
            json_types(child)
        return
    require(type(value) in {str, int, float, bool, type(None)}, "DEPLOYMENT_JSON_INVALID")


def spec_sha256(spec: dict) -> str:
    """Hash the complete spec using the existing reviewed deployment-checkpoint encoding."""
    require(type(spec) is dict, "DEPLOYMENT_SPEC_INVALID")
    try:
        json_types(spec)
        encoded = dumps(spec, sort_keys=True, allow_nan=False).encode("utf-8")
    except TypeError, ValueError, RecursionError:
        raise ValueError("DEPLOYMENT_JSON_INVALID") from None
    return sha256(encoded).hexdigest()


def image_reference(registry_manifest_digest: str) -> str:
    """Format a registry-verified digest; this function cannot establish registry provenance."""
    require(
        type(registry_manifest_digest) is str
        and fullmatch(r"sha256:[a-f0-9]{64}", registry_manifest_digest) is not None,
        "DEPLOYMENT_DIGEST_INVALID",
    )
    return REPOSITORY + "@" + registry_manifest_digest


def target_fields(deployment: dict) -> tuple[dict, dict, dict]:
    """Require the fixed, live single-container target and opaque concurrency identifiers."""
    require(type(deployment) is dict, "DEPLOYMENT_TARGET_INVALID")
    require(
        deployment.get("apiVersion") == "apps/v1" and deployment.get("kind") == "Deployment",
        "DEPLOYMENT_TARGET_INVALID",
    )
    metadata = deployment.get("metadata")
    spec = deployment.get("spec")
    require(type(metadata) is dict and type(spec) is dict, "DEPLOYMENT_TARGET_INVALID")
    require(
        metadata.get("name") == TARGET and metadata.get("namespace") == TARGET,
        "DEPLOYMENT_TARGET_INVALID",
    )
    require(
        metadata.get("deletionTimestamp") is None
        and metadata.get("deletionGracePeriodSeconds") is None
        and spec.get("paused", False) is False,
        "DEPLOYMENT_NOT_ACTIVE",
    )
    for key in ("uid", "resourceVersion"):
        require(
            type(metadata.get(key)) is str and bool(metadata[key]), "DEPLOYMENT_IDENTITY_INVALID"
        )
    require(
        type(metadata.get("generation")) is int and metadata["generation"] > 0,
        "DEPLOYMENT_GENERATION_INVALID",
    )
    template = spec.get("template")
    require(type(template) is dict, "DEPLOYMENT_CONTAINER_INVALID")
    pod = template.get("spec")
    require(type(pod) is dict, "DEPLOYMENT_CONTAINER_INVALID")
    containers = pod.get("containers")
    require(type(containers) is list and len(containers) == 1, "DEPLOYMENT_CONTAINER_INVALID")
    container = containers[0]
    require(
        type(container) is dict and container.get("name") == CONTAINER,
        "DEPLOYMENT_CONTAINER_INVALID",
    )
    old_image = container.get("image")
    require(
        type(old_image) is str
        and old_image.startswith(REPOSITORY + "@")
        and fullmatch(r"sha256:[a-f0-9]{64}", old_image[len(REPOSITORY) + 1 :]) is not None,
        "DEPLOYMENT_CURRENT_IMAGE_INVALID",
    )
    return metadata, spec, container


def image_patch(
    deployment: dict,
    expected_uid: str,
    expected_spec_sha256: str,
    registry_manifest_digest: str,
) -> list[dict]:
    """Produce a CAS patch from an independently approved baseline, not a self-approved GET.

    The caller must establish registry identity and current candidate eligibility separately.
    The UID/spec hash must come from trusted release control state. A resource-version conflict
    requires inspection, not automatic re-reading/rebasing/retry. An unchanged image is rejected;
    it is not proof that a prior ambiguous write succeeded.
    """
    require(type(expected_uid) is str and bool(expected_uid), "DEPLOYMENT_EXPECTED_UID_INVALID")
    require(
        type(expected_spec_sha256) is str
        and fullmatch(r"[a-f0-9]{64}", expected_spec_sha256) is not None,
        "DEPLOYMENT_EXPECTED_SPEC_INVALID",
    )
    new_image = image_reference(registry_manifest_digest)
    metadata, spec, container = target_fields(deployment)
    require(metadata["uid"] == expected_uid, "DEPLOYMENT_UID_CHANGED")
    require(spec_sha256(spec) == expected_spec_sha256, "DEPLOYMENT_SPEC_DRIFT")
    require(container["image"] != new_image, "DEPLOYMENT_IMAGE_UNCHANGED")
    return [
        {"op": "test", "path": "/metadata/uid", "value": expected_uid},
        {"op": "test", "path": "/metadata/resourceVersion", "value": metadata["resourceVersion"]},
        {"op": "test", "path": "/metadata/generation", "value": metadata["generation"]},
        {"op": "test", "path": "/spec/template/spec/containers/0/name", "value": CONTAINER},
        {"op": "test", "path": IMAGE_PATH, "value": container["image"]},
        {"op": "replace", "path": IMAGE_PATH, "value": new_image},
    ]


def verify_patch_response(
    before: dict,
    after: dict,
    expected_uid: str,
    expected_spec_sha256: str,
    registry_manifest_digest: str,
) -> None:
    """Check an API response for exactly the planned spec change, not rollout or smoke success."""
    patch = image_patch(before, expected_uid, expected_spec_sha256, registry_manifest_digest)
    old_metadata, old_spec, _ = target_fields(before)
    metadata, spec, _ = target_fields(after)
    expected_spec = deepcopy(old_spec)
    expected_spec["template"]["spec"]["containers"][0]["image"] = patch[-1]["value"]
    require(metadata["uid"] == expected_uid, "DEPLOYMENT_RESPONSE_UID_CHANGED")
    require(
        metadata["resourceVersion"] != old_metadata["resourceVersion"]
        and metadata["generation"] == old_metadata["generation"] + 1,
        "DEPLOYMENT_RESPONSE_VERSION_INVALID",
    )
    require(spec_sha256(spec) == spec_sha256(expected_spec), "DEPLOYMENT_RESPONSE_SPEC_CHANGED")
