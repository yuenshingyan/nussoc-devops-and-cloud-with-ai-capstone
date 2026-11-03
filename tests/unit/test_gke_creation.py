"""Exercise the one-time shell plan with a fake SDK, never a cloud account."""

from json import loads
from os import environ
from pathlib import Path
from subprocess import CompletedProcess, run
from sys import executable

from pytest import mark
from yaml import safe_load

ROOT = Path(__file__).resolve().parents[2]


def execute_plan(
    directory: Path,
    approval: str,
    fail_at: int = 0,
    project: str = "finsecure-pay-capstone-abcdef",
) -> tuple[CompletedProcess, list]:
    """Mock only the SDK executable and collect the actual shell argument vectors."""
    sdk = directory / "gcloud"
    log = directory / "commands.jsonl"
    sdk.write_text(
        f"#!{executable}\n"
        "from json import dumps\nfrom os import environ\nfrom pathlib import Path\n"
        "from sys import argv, exit\n"
        "p=Path(environ['FAKE_COMMANDS'])\n"
        "with p.open('a') as f:f.write(dumps(argv[1:])+'\\n')\n"
        "exit(9 if len(p.read_text().splitlines())==int(environ['FAKE_FAIL_AT']) else 0)\n"
    )
    sdk.chmod(0o700)
    env = {
        **environ,
        "PATH": str(directory) + ":" + environ["PATH"],
        "PROJECT_ID": project,
        "APPROVE_GKE_CREATION": approval,
        "FAKE_COMMANDS": str(log),
        "FAKE_FAIL_AT": str(fail_at),
    }
    result = run(
        ["bash", str(ROOT / "deploy/infrastructure/create-gke.sh")],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return result, [loads(line) for line in log.read_text().splitlines()] if log.exists() else []


def test_unapproved_creation_does_not_call_sdk(tmp_path):
    result, calls = execute_plan(tmp_path, "not-approved")
    assert result.returncode != 0
    assert calls == []


@mark.parametrize("project", ["", "unrelated-project", "finsecure-pay-capstone-invalid"])
def test_invalid_project_does_not_call_sdk(tmp_path, project):
    result, calls = execute_plan(tmp_path, "trial-only", project=project)
    assert result.returncode != 0
    assert calls == []


@mark.parametrize("failure", [1, 2, 3, 4, 5])
def test_partial_failure_stops_without_retry_or_deletion(tmp_path, failure):
    result, calls = execute_plan(tmp_path, "trial-only", failure)
    assert result.returncode == 9
    assert len(calls) == failure
    assert all("delete" not in call for call in calls)


def test_approved_plan_has_fixed_cost_and_identity_boundaries(tmp_path):
    result, calls = execute_plan(tmp_path, "trial-only")
    assert result.returncode == 0
    assert len(calls) == 5
    assert calls[0][:3] == ["compute", "networks", "create"]
    assert calls[1][:4] == ["compute", "networks", "subnets", "create"]
    assert calls[2][:3] == ["iam", "service-accounts", "create"]
    assert calls[3][:2] == ["projects", "add-iam-policy-binding"]
    assert "--role=roles/container.defaultNodeServiceAccount" in calls[3]
    args = calls[4]
    assert args[:4] == ["container", "clusters", "create", "finsecure-pay-demo"]
    assert {
        "--zone=asia-southeast1-a",
        "--node-locations=asia-southeast1-a",
        "--machine-type=e2-standard-2",
        "--num-nodes=2",
        "--disk-size=30",
        "--disk-type=pd-standard",
        "--no-enable-autoscaling",
        "--no-enable-autoprovisioning",
        "--max-surge-upgrade=1",
        "--max-unavailable-upgrade=0",
        "--enable-dns-access",
        "--no-enable-ip-access",
        "--no-enable-k8s-certs-via-dns",
        "--no-enable-k8s-tokens-via-dns",
        "--workload-metadata=GKE_METADATA",
        "--logging=SYSTEM,WORKLOAD",
        "--monitoring=SYSTEM",
        "--no-enable-managed-prometheus",
        "--auto-monitoring-scope=NONE",
        "--async",
    } <= set(args)
    assert not any(
        word in {"billing", "keys", "delete", "roles/editor"} for call in calls for word in call
    )


def test_gke_overlay_pins_published_image_and_only_exposes_application():
    base = ROOT / "deploy/kubernetes/overlays/gke"
    config = safe_load((base / "kustomization.yaml").read_text())
    assert config["resources"] == ["../demo"]
    assert config["images"] == [
        {
            "name": "docker.io/yuenshingyan/finsecure-pay",
            "digest": "sha256:1fc3362f15ba91f4161b8fccab644631ccc0733e9b9675bb7e2cb88e7aea5b4c",
        }
    ]
    workload = safe_load((base / "workload.yaml").read_text())["spec"]["template"]
    assert workload["spec"]["nodeSelector"] == {"kubernetes.io/arch": "amd64"}
    assert workload["metadata"]["labels"]["app.kubernetes.io/version"] == "0.3.0"
    service = safe_load((base / "service.yaml").read_text())
    assert service["metadata"]["name"] == "finsecure-pay"
    assert service["spec"]["type"] == "LoadBalancer"
    assert service["spec"]["ipFamilies"] == ["IPv4"]
    assert service["spec"]["loadBalancerSourceRanges"] == ["0.0.0.0/0"]
