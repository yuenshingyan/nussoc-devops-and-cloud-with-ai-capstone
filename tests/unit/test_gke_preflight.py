"""Read-only preflight contracts; Google and SDK boundaries are mocked, never contacted."""

from pathlib import Path
from runpy import run_path
from subprocess import CompletedProcess, TimeoutExpired
from typing import Any
from unittest.mock import Mock

from httpx2 import Client, MockTransport, ReadTimeout, Request, Response
from pytest import MonkeyPatch, fixture, mark, raises


@fixture
def helpers() -> dict[str, Any]:
    return run_path(str(Path(__file__).resolve().parents[2] / "scripts/gke_preflight.py"))


@mark.parametrize("project", ["x", "UPPER-project", "bad/project", "bad\nproject", "-project-x"])
def test_invalid_projects_are_rejected_before_access(helpers, project):
    with raises(helpers["PreflightError"], match="INVALID_PROJECT_ID"):
        helpers["validate_target"](project, "asia-southeast1-a")


@mark.parametrize("zone", ["us-central1-a", "asia-southeast2-a", "asia-southeast1-a/extra", ""])
def test_preflight_rejects_zones_outside_agreed_region(helpers, zone):
    with raises(helpers["PreflightError"], match="INVALID_ZONE"):
        helpers["validate_target"]("synthetic-project", zone)


@mark.parametrize("value", [True, "8", None, -1, float("nan"), float("inf"), 10**400])
def test_invalid_quota_numbers_fail_closed(helpers, value):
    with raises(helpers["PreflightError"], match="QUOTA_RESPONSE_INVALID"):
        helpers["quota_remaining"](
            {"quotas": [{"metric": "CPUS", "limit": value, "usage": 0}]}, "CPUS"
        )


def test_missing_quota_is_unknown_not_unlimited(helpers):
    assert helpers["quota_remaining"]({"quotas": []}, "CPUS") is None


def test_duplicate_quota_is_rejected(helpers):
    quota = {"metric": "CPUS", "limit": 8, "usage": 0}
    with raises(helpers["PreflightError"], match="QUOTA_RESPONSE_INVALID"):
        helpers["quota_remaining"]({"quotas": [quota, quota]}, "CPUS")


@mark.parametrize("usage,expected", [(0, 8), (2, 6), (8, 0), (9, -1), (1.5, 6.5)])
def test_quota_remaining_accounts_for_current_usage(helpers, usage, expected):
    assert (
        helpers["quota_remaining"](
            {"quotas": [{"metric": "CPUS", "limit": 8, "usage": usage}]}, "CPUS"
        )
        == expected
    )


def response_for(request: Request, remaining: int = 6, omit_family: bool = False) -> Response:
    """Return synthetic Google metadata; request method is part of the public contract."""
    assert request.method == "GET"
    path = request.url.path
    if request.url.host == "serviceusage.googleapis.com":
        return Response(200, json={"state": "ENABLED"})
    if request.url.host == "cloudbilling.googleapis.com":
        return Response(200, json={"billingEnabled": True, "billingAccountName": "not-for-export"})
    if path.endswith("/regions/asia-southeast1"):
        metrics = ["CPUS"] if omit_family else ["CPUS", "E2_CPUS"]
        return Response(
            200,
            json={"quotas": [{"metric": m, "limit": 8, "usage": 8 - remaining} for m in metrics]},
        )
    if "/machineTypes/" in path:
        return Response(200, json={"guestCpus": 2, "memoryMb": 8192})
    if path.endswith("/serverConfig"):
        return Response(200, json={"validMasterVersions": ["synthetic-version"]})
    assert path.endswith("/projects/synthetic-project")
    return Response(200, json={"quotas": [{"metric": "CPUS_ALL_REGIONS", "limit": 8, "usage": 0}]})


@mark.parametrize(
    "remaining,expected", [(6, "technical_checks_passed"), (5, "quota_review_required")]
)
def test_technical_check_requires_upgrade_headroom_but_never_authorizes_deployment(
    helpers, remaining, expected
):
    calls: list[str] = []

    def handler(request: Request) -> Response:
        calls.append(str(request.url))
        return response_for(request, remaining)

    with Client(transport=MockTransport(handler)) as client:
        report = helpers["check_target"](client, "synthetic-project", "asia-southeast1-a")
    assert len(calls) == 7
    assert report["status"] == expected
    assert report["deployment_authorized"] is False
    assert report["trial_credit_currency_expiry_verified_by_this_tool"] is False
    assert "synthetic-project" not in str(report)
    assert "not-for-export" not in str(report)


def test_missing_family_quota_requires_review(helpers):
    def handler(request: Request) -> Response:
        return response_for(request, omit_family=True)

    with Client(transport=MockTransport(handler)) as client:
        report = helpers["check_target"](client, "synthetic-project", "asia-southeast1-a")
    assert report["status"] == "quota_review_required"
    assert report["cpu_headroom"]["regional_e2_cpus"] is None


def test_disabled_api_does_not_enable_or_continue(helpers):
    calls = []

    def handler(request: Request) -> Response:
        calls.append(request.method)
        return Response(200, json={"state": "DISABLED"})

    with Client(transport=MockTransport(handler)) as client:
        with raises(helpers["PreflightError"], match="REQUIRED_API_NOT_ENABLED"):
            helpers["check_target"](client, "synthetic-project", "asia-southeast1-a")
    assert calls == ["GET"]


@mark.parametrize("status", [301, 302, 401, 403, 429, 500])
def test_http_failures_never_forward_credentials_or_disclose_response(helpers, status):
    calls = []

    def handler(request: Request) -> Response:
        calls.append(request.method)
        return Response(
            status, text="synthetic-private-data", headers={"Location": "https://invalid.test"}
        )

    with Client(transport=MockTransport(handler), follow_redirects=True) as client:
        with raises(helpers["PreflightError"]) as caught:
            helpers["read_json"](client, "https://compute.googleapis.com/synthetic")
    assert str(caught.value) == "GOOGLE_READ_DENIED_OR_UNAVAILABLE"
    assert calls == ["GET"]


@mark.parametrize("body", [b"not json", b"[]", b"null"])
def test_invalid_google_json_is_rejected(helpers, body):
    with Client(transport=MockTransport(lambda request: Response(200, content=body))) as client:
        with raises(helpers["PreflightError"], match="GOOGLE_RESPONSE_INVALID"):
            helpers["read_json"](client, "https://compute.googleapis.com/synthetic")


@mark.parametrize(
    "path_suffix,payload,code",
    [
        ("/billingInfo", {"billingEnabled": False}, "BILLING_NOT_ENABLED"),
        ("/billingInfo", {"billingEnabled": "true"}, "BILLING_NOT_ENABLED"),
        ("/e2-standard-2", {"guestCpus": 4, "memoryMb": 8192}, "MACHINE_SHAPE_UNEXPECTED"),
        ("/e2-standard-2", {"guestCpus": 2, "memoryMb": "8192"}, "MACHINE_SHAPE_UNEXPECTED"),
        ("/serverConfig", {"validMasterVersions": []}, "GKE_VERSION_RESPONSE_INVALID"),
        ("/serverConfig", {"validMasterVersions": [None]}, "GKE_VERSION_RESPONSE_INVALID"),
    ],
)
def test_unusable_google_metadata_blocks_preflight(helpers, path_suffix, payload, code):
    def handler(request: Request) -> Response:
        if request.url.path.endswith(path_suffix):
            return Response(200, json=payload)
        return response_for(request)

    with Client(transport=MockTransport(handler)) as client:
        with raises(helpers["PreflightError"], match=code):
            helpers["check_target"](client, "synthetic-project", "asia-southeast1-a")


def test_network_timeout_is_not_retried_or_disclosed(helpers):
    calls = []

    def handler(request: Request) -> Response:
        calls.append(request.method)
        raise ReadTimeout("synthetic private diagnostic", request=request)

    with Client(transport=MockTransport(handler)) as client:
        with raises(helpers["PreflightError"], match="^GOOGLE_READ_FAILED$"):
            helpers["read_json"](client, "https://compute.googleapis.com/synthetic")
    assert calls == ["GET"]


def test_missing_sdk_does_not_attempt_install_or_login(monkeypatch: MonkeyPatch):
    command = Mock()
    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setattr("subprocess.run", command)
    helpers = run_path(str(Path(__file__).resolve().parents[2] / "scripts/gke_preflight.py"))
    with raises(helpers["PreflightError"], match="GCLOUD_NOT_INSTALLED"):
        helpers["access_token"]()
    command.assert_not_called()


@mark.parametrize(
    "output,code", [("", 0), ("token with whitespace", 0), ("private-token", 1), ("badé", 0)]
)
def test_bad_token_result_is_not_disclosed(monkeypatch: MonkeyPatch, output, code):
    monkeypatch.setattr("shutil.which", lambda name: "/synthetic/gcloud")
    command = Mock(return_value=CompletedProcess([], code, output, "private SDK error"))
    monkeypatch.setattr("subprocess.run", command)
    helpers = run_path(str(Path(__file__).resolve().parents[2] / "scripts/gke_preflight.py"))
    with raises(helpers["PreflightError"], match="^TOKEN_UNAVAILABLE$"):
        helpers["access_token"]()
    assert command.call_args.args[0] == ["/synthetic/gcloud", "auth", "print-access-token"]
    assert command.call_args.kwargs["timeout"] == 30


def test_token_timeout_is_bounded_without_retry(monkeypatch: MonkeyPatch):
    monkeypatch.setattr("shutil.which", lambda name: "/synthetic/gcloud")
    command = Mock(side_effect=TimeoutExpired("private", 30))
    monkeypatch.setattr("subprocess.run", command)
    helpers = run_path(str(Path(__file__).resolve().parents[2] / "scripts/gke_preflight.py"))
    with raises(helpers["PreflightError"], match="^TOKEN_UNAVAILABLE$"):
        helpers["access_token"]()
    assert command.call_count == 1
