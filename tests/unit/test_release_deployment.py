from copy import deepcopy
from hashlib import sha256
from json import dumps

from pytest import fixture, mark, raises

from scripts.release_deployment import (
    IMAGE_PATH,
    REPOSITORY,
    image_patch,
    image_reference,
    spec_sha256,
    verify_patch_response,
)

NEW_DIGEST = "sha256:" + "b" * 64


@fixture
def deployment() -> dict:
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "finsecure-pay",
            "namespace": "finsecure-pay",
            "uid": "opaque-synthetic-uid",
            "resourceVersion": "opaque/resource-version",
            "generation": 7,
        },
        "spec": {
            "replicas": 2,
            "strategy": {"type": "RollingUpdate", "rollingUpdate": {"maxUnavailable": 0}},
            "template": {
                "metadata": {"labels": {"app.kubernetes.io/version": "0.3.0"}},
                "spec": {
                    "automountServiceAccountToken": False,
                    "containers": [
                        {
                            "name": "api",
                            "image": REPOSITORY + "@sha256:" + "a" * 64,
                            "securityContext": {"readOnlyRootFilesystem": True},
                        }
                    ],
                },
            },
        },
    }


def plan(deployment: dict) -> list[dict]:
    return image_patch(
        deployment, "opaque-synthetic-uid", spec_sha256(deployment["spec"]), NEW_DIGEST
    )


def response(deployment: dict) -> dict:
    updated = deepcopy(deployment)
    updated["metadata"]["resourceVersion"] = "different/opaque-version"
    updated["metadata"]["generation"] += 1
    updated["spec"]["template"]["spec"]["containers"][0]["image"] = image_reference(NEW_DIGEST)
    return updated


def test_patch_has_one_image_write_after_identity_and_concurrency_tests(deployment):
    original = deepcopy(deployment)
    patch = plan(deployment)
    assert patch == [
        {"op": "test", "path": "/metadata/uid", "value": "opaque-synthetic-uid"},
        {"op": "test", "path": "/metadata/resourceVersion", "value": "opaque/resource-version"},
        {"op": "test", "path": "/metadata/generation", "value": 7},
        {"op": "test", "path": "/spec/template/spec/containers/0/name", "value": "api"},
        {"op": "test", "path": IMAGE_PATH, "value": REPOSITORY + "@sha256:" + "a" * 64},
        {"op": "replace", "path": IMAGE_PATH, "value": REPOSITORY + "@" + NEW_DIGEST},
    ]
    assert deployment == original


def test_spec_hash_matches_existing_checkpoint_encoding(deployment):
    assert (
        spec_sha256(deployment["spec"])
        == sha256(dumps(deployment["spec"], sort_keys=True).encode()).hexdigest()
    )


@mark.parametrize("digest", [None, True, 3, "", "b" * 64, "sha256:" + "B" * 64, NEW_DIGEST + "\n"])
def test_registry_digest_requires_exact_canonical_string(digest):
    with raises(ValueError, match="DIGEST_INVALID"):
        image_reference(digest)


@mark.parametrize("uid", [None, True, 3, ""])
def test_expected_uid_rejects_missing_or_coerced_identity(deployment, uid):
    with raises(ValueError, match="EXPECTED_UID_INVALID"):
        image_patch(deployment, uid, spec_sha256(deployment["spec"]), NEW_DIGEST)


@mark.parametrize("digest", [None, True, "", "F" * 64, "a" * 63])
def test_expected_spec_hash_is_required(deployment, digest):
    with raises(ValueError, match="EXPECTED_SPEC_INVALID"):
        image_patch(deployment, "opaque-synthetic-uid", digest, NEW_DIGEST)


def test_uid_recreation_is_rejected(deployment):
    deployment["metadata"]["uid"] = "different-uid"
    with raises(ValueError, match="UID_CHANGED"):
        plan(deployment)


@mark.parametrize(
    ("path", "value"),
    [
        (("apiVersion",), "v1"),
        (("kind",), "Pod"),
        (("metadata", "name"), "other"),
        (("metadata", "namespace"), "other"),
        (("metadata", "resourceVersion"), 123),
        (("metadata", "resourceVersion"), ""),
        (("metadata", "generation"), True),
        (("metadata", "generation"), 0),
        (("metadata", "generation"), 7.0),
        (("metadata", "deletionTimestamp"), "2026-11-04T00:00:00Z"),
        (("metadata", "deletionGracePeriodSeconds"), 0),
        (("spec", "paused"), True),
        (("spec", "paused"), 0),
        (("spec", "template"), None),
        (("spec", "template", "spec"), []),
        (("spec", "template", "spec", "containers"), []),
        (("spec", "template", "spec", "containers"), [{"name": "sidecar"}]),
        (("spec", "template", "spec", "containers"), [{}, {}]),
    ],
)
def test_malformed_or_wrong_target_is_rejected(deployment, path, value):
    parent = deployment
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = value
    with raises(ValueError, match="DEPLOYMENT_"):
        plan(deployment)


@mark.parametrize(
    "image", [None, "finsecure-pay:latest", "other@" + NEW_DIGEST, REPOSITORY + ":0.3.0"]
)
def test_current_image_must_be_pinned_in_fixed_repository(deployment, image):
    deployment["spec"]["template"]["spec"]["containers"][0]["image"] = image
    with raises(ValueError, match="CURRENT_IMAGE_INVALID"):
        plan(deployment)


@mark.parametrize("change", ["replicas", "security", "labels", "image", "numeric_type"])
def test_live_spec_cannot_approve_its_own_drift(deployment, change):
    approved = spec_sha256(deployment["spec"])
    if change == "replicas":
        deployment["spec"]["replicas"] = 3
    elif change == "security":
        deployment["spec"]["template"]["spec"]["automountServiceAccountToken"] = True
    elif change == "labels":
        deployment["spec"]["template"]["metadata"]["labels"]["changed"] = "yes"
    elif change == "image":
        deployment["spec"]["template"]["spec"]["containers"][0]["image"] = image_reference(
            NEW_DIGEST
        )
    else:
        deployment["spec"]["replicas"] = 2.0
    with raises(ValueError, match="SPEC_DRIFT"):
        image_patch(deployment, "opaque-synthetic-uid", approved, NEW_DIGEST)


def test_unchanged_image_is_not_treated_as_success_or_retried(deployment):
    deployment["spec"]["template"]["spec"]["containers"][0]["image"] = image_reference(NEW_DIGEST)
    with raises(ValueError, match="IMAGE_UNCHANGED"):
        plan(deployment)


@mark.parametrize("value", [{1: "coerced"}, {"value": float("nan")}, {"value": (1, 2)}])
def test_spec_hash_rejects_non_json_values(value):
    with raises(ValueError, match="JSON_INVALID"):
        spec_sha256(value)


def test_patch_response_accepts_only_expected_spec_without_claiming_readiness(deployment):
    after = response(deployment)
    after["status"] = {"availableReplicas": 0}
    original = deepcopy(deployment)
    assert (
        verify_patch_response(
            deployment, after, "opaque-synthetic-uid", spec_sha256(deployment["spec"]), NEW_DIGEST
        )
        is None
    )
    assert deployment == original


@mark.parametrize("change", ["uid", "version", "generation", "image", "security", "replicas"])
def test_patch_response_rejects_unexpected_identity_or_spec(deployment, change):
    after = response(deployment)
    if change == "uid":
        after["metadata"]["uid"] = "replacement"
    elif change == "version":
        after["metadata"]["resourceVersion"] = deployment["metadata"]["resourceVersion"]
    elif change == "generation":
        after["metadata"]["generation"] += 1
    elif change == "image":
        after["spec"]["template"]["spec"]["containers"][0]["image"] = image_reference(
            "sha256:" + "c" * 64
        )
    elif change == "security":
        after["spec"]["template"]["spec"]["automountServiceAccountToken"] = True
    else:
        after["spec"]["replicas"] = 3
    with raises(ValueError, match="DEPLOYMENT_RESPONSE_"):
        verify_patch_response(
            deployment, after, "opaque-synthetic-uid", spec_sha256(deployment["spec"]), NEW_DIGEST
        )
