"""Static policy-contract checks; live admission and IAM/RBAC tests are separate."""

from pathlib import Path

from pytest import mark
from yaml import safe_load

ROOT = Path(__file__).resolve().parents[2] / "deploy/kubernetes"


def policy() -> dict:
    return safe_load((ROOT / "overlays/gke/namespace-policy.yaml").read_text())


def role() -> dict:
    return safe_load((ROOT / "delivery/role.yaml").read_text())


@mark.parametrize("mode", ["enforce", "audit", "warn"])
def test_gke_namespace_requires_pinned_restricted_policy(mode):
    value = policy()
    assert value["kind"] == "Namespace"
    assert value["metadata"]["name"] == "finsecure-pay"
    assert value["metadata"]["labels"][f"pod-security.kubernetes.io/{mode}"] == "restricted"
    assert value["metadata"]["labels"][f"pod-security.kubernetes.io/{mode}-version"] == "v1.36"


def test_namespace_policy_is_part_of_gke_overlay_only():
    gke = safe_load((ROOT / "overlays/gke/kustomization.yaml").read_text())
    assert {"path": "namespace-policy.yaml"} in gke["patches"]
    demo = safe_load((ROOT / "overlays/demo/namespace.yaml").read_text())
    assert not any(key.startswith("pod-security.") for key in demo["metadata"]["labels"])
    assert not any("delivery" in path for path in gke["resources"])


def test_deployer_has_only_the_reviewed_namespaced_rules():
    value = role()
    assert value["apiVersion"] == "rbac.authorization.k8s.io/v1"
    assert value["kind"] == "Role"
    assert value["metadata"] == {"name": "finsecure-deployer", "namespace": "finsecure-pay"}
    assert value["rules"] == [
        {
            "apiGroups": ["apps"],
            "resources": ["deployments"],
            "resourceNames": ["finsecure-pay"],
            "verbs": ["get", "patch", "watch"],
        },
        {"apiGroups": ["apps"], "resources": ["replicasets"], "verbs": ["get", "list", "watch"]},
        {"apiGroups": [""], "resources": ["pods"], "verbs": ["get", "list", "watch"]},
        {
            "apiGroups": [""],
            "resources": ["services"],
            "resourceNames": ["finsecure-pay"],
            "verbs": ["get"],
        },
    ]


@mark.parametrize(
    "resource",
    ["secrets", "nodes", "pods/exec", "pods/log", "serviceaccounts", "roles", "rolebindings"],
)
def test_deployer_does_not_directly_grant_sensitive_resources(resource):
    for rule in role()["rules"]:
        assert resource not in rule["resources"]
        assert "*" not in rule["resources"]
        assert "*" not in rule["apiGroups"]
        assert "*" not in rule["verbs"]


def test_deployer_cannot_directly_create_or_delete_resources():
    assert all(
        not {"create", "delete", "deletecollection"} & set(r["verbs"]) for r in role()["rules"]
    )
