from argparse import Namespace
from copy import deepcopy
from io import BytesIO
from json import dumps, loads
from pathlib import Path
from ssl import SSLContext
from time import monotonic

from pytest import MonkeyPatch, fixture, mark, raises

from scripts.release_command import CommandResult
from scripts.release_deployment import image_reference, spec_sha256
from scripts.release_execute import execute_child, supervise
from scripts.release_http import DEPLOYMENT_PATH, DeploymentClient
from scripts.release_rollout import deploy_and_wait, deployment_ready, ready_pod_uids
from scripts.release_smoke import (
    PUBLIC_HOST,
    verify_service,
    verify_smoke,
    wait_for_public_readiness,
)

DIGEST = "sha256:" + "b" * 64
UID = "synthetic-deployment-uid"


@fixture
def documents() -> tuple[dict, dict, dict, dict]:
    before = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "finsecure-pay",
            "namespace": "finsecure-pay",
            "uid": UID,
            "generation": 1,
            "resourceVersion": "opaque-before",
        },
        "spec": {
            "replicas": 2,
            "template": {
                "spec": {
                    "containers": [{"name": "api", "image": image_reference("sha256:" + "a" * 64)}]
                }
            },
        },
    }
    after = deepcopy(before)
    after["metadata"].update(generation=2, resourceVersion="opaque-after")
    after["spec"]["template"]["spec"]["containers"][0]["image"] = image_reference(DIGEST)
    after["status"] = {
        "observedGeneration": 2,
        "replicas": 2,
        "updatedReplicas": 2,
        "readyReplicas": 2,
        "availableReplicas": 2,
    }
    sets = {
        "apiVersion": "apps/v1",
        "kind": "ReplicaSetList",
        "metadata": {},
        "items": [
            {
                "metadata": {
                    "uid": "new-rs",
                    "namespace": "finsecure-pay",
                    "ownerReferences": [
                        {
                            "apiVersion": "apps/v1",
                            "kind": "Deployment",
                            "uid": UID,
                            "controller": True,
                        }
                    ],
                }
            }
        ],
    }
    pods = {"apiVersion": "v1", "kind": "PodList", "metadata": {}, "items": []}
    for index in range(2):
        pods["items"].append(
            {
                "metadata": {
                    "uid": f"pod-{index}",
                    "namespace": "finsecure-pay",
                    "ownerReferences": [
                        {
                            "apiVersion": "apps/v1",
                            "kind": "ReplicaSet",
                            "uid": "new-rs",
                            "controller": True,
                        }
                    ],
                },
                "spec": {"containers": [{"name": "api", "image": image_reference(DIGEST)}]},
                "status": {
                    "phase": "Running",
                    "conditions": [{"type": "Ready", "status": "True"}],
                    "containerStatuses": [
                        {
                            "name": "api",
                            "ready": True,
                            "imageID": image_reference(DIGEST),
                            "state": {"running": {}},
                        }
                    ],
                },
            }
        )
    return before, after, sets, pods


class Response(BytesIO):
    def __init__(self, status: int, body: bytes) -> None:
        super().__init__(body)
        self.status = status


@fixture
def transport(monkeypatch: MonkeyPatch) -> dict:
    state = {"responses": [], "calls": [], "closed": 0}

    class Connection:
        def request(self, method: str, path: str, body: bytes | None, headers: dict) -> None:
            state["calls"].append((method, path, body, headers))

        def getresponse(self) -> Response:
            status, body = state["responses"].pop(0)
            if isinstance(body, BaseException):
                raise body
            return Response(status, body if type(body) is bytes else dumps(body).encode())

        def close(self) -> None:
            state["closed"] += 1

    def factory(host: str, timeout: float, context: SSLContext) -> Connection:
        assert host == "synthetic.gke.goog"
        assert context.check_hostname and 0 < timeout <= 30
        return Connection()

    def public_factory(host: str, port: int, timeout: float) -> Connection:
        assert host == PUBLIC_HOST and port == 80 and 0 < timeout <= 30
        return Connection()

    monkeypatch.setattr("scripts.release_http.HTTPSConnection", factory)
    monkeypatch.setattr("scripts.release_smoke.HTTPConnection", public_factory)
    return state


def client() -> DeploymentClient:
    return DeploymentClient("https://synthetic.gke.goog", "synthetic-token", monotonic() + 30)


def test_complete_rollout_has_one_cas_patch_and_verified_runtime_lineage(documents, transport):
    before, after, sets, pods = documents
    transport["responses"] = [(200, value) for value in [before, after, sets, pods, after]]
    result = deploy_and_wait(client(), UID, spec_sha256(before["spec"]), DIGEST)
    assert result["status"] == "rollout_verified"
    assert result["pod_uids"] == ["pod-0", "pod-1"]
    assert result["spec_sha256"] == spec_sha256(after["spec"])
    assert result["smoke_verified"] is False and result["automatic_rollback"] is False
    assert [call[0] for call in transport["calls"]] == ["GET", "PATCH", "GET", "GET", "GET"]
    method, path, body, headers = transport["calls"][1]
    assert method == "PATCH" and path == DEPLOYMENT_PATH
    patch = loads(body)
    assert [entry["op"] for entry in patch] == ["test"] * 5 + ["replace"]
    assert patch[-1]["path"] == "/spec/template/spec/containers/0/image"
    assert headers["Content-Type"] == "application/json-patch+json"
    assert all(call[3]["Authorization"] == "Bearer synthetic-token" for call in transport["calls"])
    assert transport["closed"] == 5


def test_pending_generation_is_observed_again_not_repatched(documents, transport, monkeypatch):
    before, after, sets, pods = documents
    pending = deepcopy(after)
    pending["status"]["observedGeneration"] = 1
    transport["responses"] = [(200, value) for value in [before, pending, after, sets, pods, after]]
    waits = []
    monkeypatch.setattr("scripts.release_rollout.sleep", waits.append)
    result = deploy_and_wait(client(), UID, spec_sha256(before["spec"]), DIGEST)
    assert result["status"] == "rollout_verified" and waits == [1.0]
    assert sum(call[0] == "PATCH" for call in transport["calls"]) == 1


@mark.parametrize("status", [400, 401, 403, 404, 409, 422, 429, 500, 302])
def test_patch_errors_never_retry_rebase_follow_redirect_or_rollback(documents, transport, status):
    before, *_ = documents
    transport["responses"] = [(200, before), (status, b"untrusted private provider message")]
    with raises(RuntimeError) as caught:
        deploy_and_wait(client(), UID, spec_sha256(before["spec"]), DIGEST)
    assert "private" not in str(caught.value)
    assert [call[0] for call in transport["calls"]] == ["GET", "PATCH"]
    assert transport["closed"] == 2


@mark.parametrize(
    "body",
    [
        b"{} trailing",
        b'{"key":1,"key":2}',
        b"[]",
        b"x" * (1024 * 1024 + 1),
        OSError("private error"),
    ],
)
def test_patch_bad_response_is_unknown_outcome_without_another_request(documents, transport, body):
    before, *_ = documents
    transport["responses"] = [(200, before), (200, body)]
    with raises(RuntimeError, match="PATCH_OUTCOME_UNKNOWN"):
        deploy_and_wait(client(), UID, spec_sha256(before["spec"]), DIGEST)
    assert [call[0] for call in transport["calls"]] == ["GET", "PATCH"]
    assert transport["closed"] == 2


def test_spec_drift_before_patch_prevents_mutation(documents, transport):
    before, *_ = documents
    approved = spec_sha256(before["spec"])
    before["spec"]["replicas"] = 3
    transport["responses"] = [(200, before)]
    with raises(ValueError, match="SPEC_DRIFT"):
        deploy_and_wait(client(), UID, approved, DIGEST)
    assert [call[0] for call in transport["calls"]] == ["GET"]


def test_drift_at_final_observation_prevents_success_without_rollback(documents, transport):
    before, after, sets, pods = documents
    drifted = deepcopy(after)
    drifted["metadata"]["generation"] += 1
    transport["responses"] = [(200, value) for value in [before, after, sets, pods, drifted]]
    with raises(ValueError, match="RESPONSE_VERSION_INVALID"):
        deploy_and_wait(client(), UID, spec_sha256(before["spec"]), DIGEST)
    assert sum(call[0] == "PATCH" for call in transport["calls"]) == 1


@mark.parametrize(
    "field,value",
    [
        ("observedGeneration", 1),
        ("replicas", 3),
        ("readyReplicas", 1),
        ("updatedReplicas", 1),
        ("availableReplicas", 1),
        ("unavailableReplicas", 1),
        ("terminatingReplicas", 1),
    ],
)
def test_incomplete_deployment_cannot_count_as_ready(documents, field, value):
    _, after, *_ = documents
    after["status"][field] = value
    assert deployment_ready(after) is False


@mark.parametrize(
    "condition",
    [
        {"type": "Progressing", "status": "False", "reason": "ProgressDeadlineExceeded"},
        {"type": "ReplicaFailure", "status": "True"},
    ],
)
def test_controller_failure_stops_observation(documents, condition):
    _, after, *_ = documents
    after["status"]["conditions"] = [condition]
    with raises(RuntimeError, match="CONTROLLER_FAILED"):
        deployment_ready(after)


@mark.parametrize(
    "condition",
    [
        {"type": "Progressing", "status": False},
        {"type": None, "status": "True"},
    ],
)
def test_condition_types_are_not_coerced(documents, condition):
    _, after, *_ = documents
    after["status"]["conditions"] = [condition]
    with raises(ValueError, match="STATUS_INVALID"):
        deployment_ready(after)


@mark.parametrize(
    "field,value", [("readyReplicas", True), ("replicas", -1), ("observedGeneration", 3)]
)
def test_invalid_status_is_not_coerced_or_treated_as_success(documents, field, value):
    _, after, *_ = documents
    after["status"][field] = value
    with raises(ValueError, match="STATUS_INVALID"):
        deployment_ready(after)


@mark.parametrize("change", ["old_image", "terminating", "not_ready", "waiting", "missing_pod"])
def test_pending_or_old_pods_do_not_satisfy_rollout(documents, change):
    _, after, sets, pods = documents
    pod = pods["items"][0]
    if change == "old_image":
        pod["spec"]["containers"][0]["image"] = image_reference("sha256:" + "a" * 64)
    elif change == "terminating":
        pod["metadata"]["deletionTimestamp"] = "2026-11-04T00:00:00Z"
    elif change == "not_ready":
        pod["status"]["conditions"][0]["status"] = "False"
    elif change == "waiting":
        pod["status"]["containerStatuses"][0]["state"] = {"waiting": {}}
    else:
        pods["items"].pop()
    assert ready_pod_uids(after, sets, pods, DIGEST) == []


@mark.parametrize("phase", ["Succeeded", "Failed"])
def test_retained_terminal_pod_does_not_block_two_healthy_replacements(documents, phase):
    _, after, sets, pods = documents
    terminal = deepcopy(pods["items"][0])
    terminal["metadata"]["uid"] = "terminal-old-pod"
    terminal["status"] = {"phase": phase}
    terminal["spec"]["containers"][0]["image"] = image_reference("sha256:" + "a" * 64)
    pods["items"].append(terminal)
    assert ready_pod_uids(after, sets, pods, DIGEST) == ["pod-0", "pod-1"]


@mark.parametrize(
    "change", ["foreign_pod", "foreign_rs", "wrong_runtime", "duplicate_uid", "partial_list"]
)
def test_bad_runtime_identity_or_list_is_rejected(documents, change):
    _, after, sets, pods = documents
    if change == "foreign_pod":
        pods["items"][0]["metadata"]["ownerReferences"][0]["uid"] = "foreign-rs"
    elif change == "foreign_rs":
        sets["items"][0]["metadata"]["ownerReferences"][0]["uid"] = "foreign-deployment"
    elif change == "wrong_runtime":
        pods["items"][0]["status"]["containerStatuses"][0]["imageID"] = image_reference(
            "sha256:" + "c" * 64
        )
    elif change == "duplicate_uid":
        pods["items"].append(deepcopy(pods["items"][0]))
    else:
        pods["metadata"]["continue"] = "another-page"
    with raises(ValueError, match="ROLLOUT_"):
        ready_pod_uids(after, sets, pods, DIGEST)


@fixture
def smoke_responses() -> list[tuple[int, dict]]:
    return [
        (200, {"status": "healthy"}),
        (200, {"valid": True, "errors": []}),
        (200, {"valid": False, "errors": ["AMOUNT_NOT_POSITIVE"]}),
        (
            422,
            {
                "detail": [
                    {
                        "loc": ["body", "amount"],
                        "type": "string_type",
                        "msg": "Invalid request value. Check the API contract.",
                    }
                ]
            },
        ),
    ]


def test_smoke_runs_four_exact_contract_cases_without_credentials(transport, smoke_responses):
    transport["responses"] = smoke_responses
    assert verify_smoke(monotonic() + 30) == {
        "status": "smoke_verified",
        "cases": 4,
        "synthetic_data_only": True,
    }
    assert [call[0] for call in transport["calls"]] == ["GET", "POST", "POST", "POST"]
    assert [call[1] for call in transport["calls"]] == ["/health"] + ["/validate"] * 3
    assert all("Authorization" not in call[3] for call in transport["calls"])
    assert transport["closed"] == 4


@mark.parametrize("stage", [0, 1, 2, 3])
def test_smoke_failure_stops_without_retry_or_exposing_body(transport, smoke_responses, stage):
    smoke_responses[stage] = (503, {"private": "synthetic provider detail"})
    transport["responses"] = smoke_responses
    with raises(RuntimeError, match="SMOKE_RESPONSE_MISMATCH") as caught:
        verify_smoke(monotonic() + 30)
    assert "private" not in str(caught.value)
    assert len(transport["calls"]) == stage + 1


def test_smoke_does_not_coerce_numeric_response_to_boolean(transport, smoke_responses):
    smoke_responses[1] = (200, {"valid": 1, "errors": []})
    transport["responses"] = smoke_responses
    with raises(RuntimeError, match="SMOKE_RESPONSE_MISMATCH"):
        verify_smoke(monotonic() + 30)
    assert len(transport["calls"]) == 2


@fixture
def service() -> dict:
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": "finsecure-pay", "namespace": "finsecure-pay"},
        "spec": {
            "type": "LoadBalancer",
            "selector": {"app.kubernetes.io/name": "finsecure-pay"},
            "ports": [{"port": 80, "targetPort": "http", "protocol": "TCP"}],
        },
        "status": {"loadBalancer": {"ingress": [{"ip": PUBLIC_HOST}]}},
    }


@mark.parametrize("change", ["selector", "port", "ip", "type", "deleting"])
def test_service_drift_is_rejected_before_smoke(service, change):
    if change == "selector":
        service["spec"]["selector"] = {"app": "foreign"}
    elif change == "port":
        service["spec"]["ports"][0]["targetPort"] = 8080
    elif change == "ip":
        service["status"]["loadBalancer"]["ingress"][0]["ip"] = "192.0.2.1"
    elif change == "type":
        service["spec"]["type"] = "ExternalName"
    else:
        service["metadata"]["deletionTimestamp"] = "2026-11-04T00:00:00Z"
    with raises(ValueError, match="SERVICE_CHANGED"):
        verify_service(service)


@fixture
def arguments(tmp_path: Path, documents: tuple[dict, dict, dict, dict]) -> Namespace:
    parent = tmp_path.resolve()
    parent.chmod(0o700)
    key = parent / "synthetic-key"
    project = "finsecure-pay-capstone-" + "a" * 6
    key.write_text(
        dumps(
            {
                "type": "service_account",
                "project_id": project,
                "client_email": f"finsecure-gke-deployer@{project}.iam.gserviceaccount.com",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        )
    )
    key.chmod(0o600)
    return Namespace(
        key=str(key),
        directory=str(parent),
        uid=UID,
        spec_sha256=spec_sha256(documents[0]["spec"]),
        digest=DIGEST,
        deadline=monotonic() + 30,
    )


def test_child_composes_service_patch_rollout_smoke_and_profile_cleanup(
    arguments, documents, service, transport, smoke_responses, monkeypatch
):
    before, after, sets, pods = documents
    transport["responses"] = (
        [(200, value) for value in [service, before, after, sets, pods, after, service]]
        + [(200, {"status": "healthy"})] * 10
        + smoke_responses
    )
    monkeypatch.setattr("scripts.release_smoke.sleep", lambda seconds: None)
    profiles = []

    def token(environment: dict[str, str]) -> str:
        profiles.append(Path(environment["HOME"]))
        assert environment["GOOGLE_APPLICATION_CREDENTIALS"] == arguments.key
        return "synthetic-token"

    def endpoint(project: str, token: str) -> str:
        return "https://synthetic.gke.goog"

    monkeypatch.setattr("scripts.release_execute.adc_token", token)
    monkeypatch.setattr("scripts.release_execute.cluster_endpoint", endpoint)
    result = execute_child(arguments)
    assert result["status"] == "deployment_verified" and result["smoke_verified"] is True
    assert not profiles[0].exists() and Path(arguments.key).exists()
    assert sum(call[0] == "PATCH" for call in transport["calls"]) == 1
    assert all("Authorization" not in call[3] for call in transport["calls"][-4:])


def test_public_readiness_requires_stable_health_before_smoke(transport, monkeypatch):
    transport["responses"] = (
        [(200, {"status": "healthy"})] * 2
        + [(503, {"status": "starting"})]
        + [(200, {"status": "healthy"})] * 10
    )
    waits = []
    monkeypatch.setattr("scripts.release_smoke.sleep", waits.append)
    wait_for_public_readiness(monotonic() + 30)
    assert len(transport["calls"]) == 13 and waits == [1.0] * 12
    assert all(call[0] == "GET" and call[1] == "/health" for call in transport["calls"])


@mark.parametrize("failure", ["none", "exit", "timeout", "wrong_result"])
def test_supervisor_bounds_one_child_and_filters_ambient_credentials(
    arguments, monkeypatch, failure
):
    calls = []
    report = {
        "status": "deployment_verified",
        "deployment_uid": UID,
        "generation": 2,
        "spec_sha256": "a" * 64,
        "pod_uids": ["pod-0", "pod-1"],
        "registry_manifest_digest": DIGEST,
        "elapsed_seconds": 1.0,
        "smoke_verified": True,
        "automatic_rollback": False,
    }
    monkeypatch.setenv("HTTP_PROXY", "http://untrusted.example")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/untrusted")
    monkeypatch.setenv("JENKINS_SERVER_COOKIE", "synthetic-cookie")

    def command(argv: list[str], environment: dict[str, str], deadline: float) -> CommandResult:
        calls.append((argv, environment, deadline))
        if failure == "timeout":
            # Model cache left by a child killed before its own finally block runs.
            Path(environment["HOME"], "synthetic-child-cache").write_text("synthetic")
            raise TimeoutError("RELEASE_COMMAND_TIMEOUT_OUTCOME_UNKNOWN")
        if failure == "exit":
            return CommandResult(
                2,
                dumps(
                    {
                        "status": "failed",
                        "code": "DEPLOYMENT_PATCH_REJECTED_INSPECT_MANUALLY",
                        "operator_inspection_required": True,
                    }
                ).encode(),
            )
        if failure == "wrong_result":
            report["unexpected_private_payload"] = "must not return"
        return CommandResult(0, dumps(report).encode())

    monkeypatch.setattr("scripts.release_execute.run_command", command)
    if failure == "none":
        assert supervise(arguments) == report
    else:
        with raises((RuntimeError, TimeoutError)):
            supervise(arguments)
    assert len(calls) == 1
    argv, environment, deadline = calls[0]
    assert "--child" in argv and "--deadline" in argv and deadline == arguments.deadline
    assert argv[argv.index("--directory") + 1] == environment["HOME"]
    assert "HTTP_PROXY" not in environment and "GOOGLE_APPLICATION_CREDENTIALS" not in environment
    assert environment["JENKINS_SERVER_COOKIE"] == "synthetic-cookie"
    assert not Path(environment["HOME"]).exists() and Path(arguments.key).exists()


def test_expired_budget_starts_no_request(transport, monkeypatch):
    connection = client()
    monkeypatch.setattr("scripts.release_http.monotonic", lambda: connection.deadline + 1)
    with raises(TimeoutError, match="BUDGET_EXCEEDED"):
        connection.get_deployment()
    assert transport["calls"] == []


@mark.parametrize(
    "endpoint",
    [
        "http://synthetic.gke.goog",
        "https://untrusted.example",
        "https://synthetic.gke.goog/path",
        "https://user@synthetic.gke.goog",
    ],
)
def test_endpoint_rejects_plaintext_arbitrary_authority_and_paths(endpoint):
    with raises(ValueError, match="ENDPOINT_INVALID"):
        DeploymentClient(endpoint, "synthetic-token", monotonic() + 30)
