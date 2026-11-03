"""Read-only GKE technical preflight; never authorizes deployment or paid billing."""

from argparse import ArgumentParser
from datetime import UTC, datetime
from json import dumps
from math import isfinite
from re import fullmatch
from shutil import which
from subprocess import SubprocessError, run
from typing import Any

from httpx2 import Client, HTTPError

REGION = "asia-southeast1"
MACHINE_TYPE = "e2-standard-2"
REQUIRED_CPUS = 6  # Two proposed nodes plus one node of upgrade headroom; not provisioning.
READ_TIMEOUT_SECONDS = 30


class PreflightError(RuntimeError):
    """A safe failure code, never a raw SDK/network error or credential value."""


def validate_target(project: str, zone: str) -> None:
    """Reject unsafe project values and targets outside the proposed Singapore scope."""
    if fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", project) is None:
        raise PreflightError("INVALID_PROJECT_ID")
    if zone not in {f"{REGION}-a", f"{REGION}-b", f"{REGION}-c"}:
        raise PreflightError("INVALID_ZONE")


def access_token() -> str:
    """Borrow the operator's existing gcloud login; never log in or enable APIs."""
    executable = which("gcloud")
    if executable is None:
        raise PreflightError("GCLOUD_NOT_INSTALLED")
    try:
        result = run(
            [executable, "auth", "print-access-token"],
            capture_output=True,
            text=True,
            timeout=READ_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, SubprocessError) as error:
        raise PreflightError("TOKEN_UNAVAILABLE") from error
    token = result.stdout.strip()
    if result.returncode != 0 or fullmatch(r"[A-Za-z0-9._~+/-]+=*", token) is None:
        raise PreflightError("TOKEN_UNAVAILABLE")
    return token


def read_json(client: Client, url: str) -> dict[str, Any]:
    """Read fixed Google endpoints without redirects or raw error disclosure."""
    try:
        response = client.get(url, follow_redirects=False)
    except HTTPError as error:
        raise PreflightError("GOOGLE_READ_FAILED") from error
    if response.status_code != 200:
        raise PreflightError("GOOGLE_READ_DENIED_OR_UNAVAILABLE")
    try:
        data = response.json()
    except ValueError as error:
        raise PreflightError("GOOGLE_RESPONSE_INVALID") from error
    if not isinstance(data, dict):
        raise PreflightError("GOOGLE_RESPONSE_INVALID")
    return data


def quota_remaining(data: dict[str, Any], metric: str) -> float | None:
    """Extract finite quota headroom; missing metrics require review, not assumptions."""
    quotas = data.get("quotas")
    if not isinstance(quotas, list) or any(not isinstance(item, dict) for item in quotas):
        raise PreflightError("QUOTA_RESPONSE_INVALID")
    matches = [item for item in quotas if item.get("metric") == metric]
    if not matches:
        return None
    if len(matches) != 1:
        raise PreflightError("QUOTA_RESPONSE_INVALID")
    limit, usage = matches[0].get("limit"), matches[0].get("usage")
    for value in (limit, usage):
        if type(value) not in (int, float) or value < 0:
            raise PreflightError("QUOTA_RESPONSE_INVALID")
        try:
            finite = isfinite(value)
        except OverflowError as error:
            raise PreflightError("QUOTA_RESPONSE_INVALID") from error
        if not finite:
            raise PreflightError("QUOTA_RESPONSE_INVALID")
    return limit - usage


def check_target(client: Client, project: str, zone: str) -> dict[str, Any]:
    """Check technical prerequisites only; strip account, project and billing identifiers."""
    validate_target(project, zone)
    for service in ("compute.googleapis.com", "container.googleapis.com"):
        state = read_json(
            client, f"https://serviceusage.googleapis.com/v1/projects/{project}/services/{service}"
        )
        if state.get("state") != "ENABLED":
            raise PreflightError("REQUIRED_API_NOT_ENABLED")
    billing = read_json(
        client, f"https://cloudbilling.googleapis.com/v1/projects/{project}/billingInfo"
    )
    if billing.get("billingEnabled") is not True:
        raise PreflightError("BILLING_NOT_ENABLED")
    base = f"https://compute.googleapis.com/compute/v1/projects/{project}"
    region = read_json(client, f"{base}/regions/{REGION}")
    global_quotas = read_json(client, base)
    machine = read_json(client, f"{base}/zones/{zone}/machineTypes/{MACHINE_TYPE}")
    versions = read_json(
        client,
        f"https://container.googleapis.com/v1/projects/{project}/locations/{zone}/serverConfig",
    )
    available_versions = versions.get("validMasterVersions")
    if not isinstance(available_versions, list) or not available_versions:
        raise PreflightError("GKE_VERSION_RESPONSE_INVALID")
    if any(not isinstance(value, str) or not value for value in available_versions):
        raise PreflightError("GKE_VERSION_RESPONSE_INVALID")
    if (
        type(machine.get("guestCpus")) is not int
        or machine["guestCpus"] != 2
        or type(machine.get("memoryMb")) is not int
        or machine["memoryMb"] != 8192
    ):
        raise PreflightError("MACHINE_SHAPE_UNEXPECTED")
    headroom = {
        "regional_cpus": quota_remaining(region, "CPUS"),
        "regional_e2_cpus": quota_remaining(region, "E2_CPUS"),
        "global_cpus": quota_remaining(global_quotas, "CPUS_ALL_REGIONS"),
    }
    sufficient = all(value is not None and value >= REQUIRED_CPUS for value in headroom.values())
    return {
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "status": "technical_checks_passed" if sufficient else "quota_review_required",
        "region": REGION,
        "zone": zone,
        "machine_type": MACHINE_TYPE,
        "cpu_headroom": headroom,
        "required_cpu_headroom": REQUIRED_CPUS,
        "required_apis_enabled": True,
        "billing_enabled": True,
        "gke_server_config_readable": True,
        "machine_shape_matches": True,
        "deployment_authorized": False,
        "trial_credit_currency_expiry_verified_by_this_tool": False,
        "limitations": [
            "Billing enabled does not establish a free-trial account or remaining credit.",
            "A listed machine type and quota do not guarantee zonal capacity or creation rights.",
            "Missing quota metrics require review; this tool does not treat them as unlimited.",
            "Address, disk and other quotas need checking against the approved final network plan.",
            "No resource creation, API enablement, IAM change or paid upgrade is performed.",
        ],
    }


def main() -> int:
    """Print a bounded safe report; fail closed without traceback or SDK output."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project", required=True, help="Project ID supplied locally, not committed"
    )
    parser.add_argument(
        "--zone", required=True, help="Explicit Singapore zone; no default selection"
    )
    args = parser.parse_args()
    try:
        validate_target(args.project, args.zone)
        token = access_token()
        with Client(
            headers={"Authorization": f"Bearer {token}"},
            timeout=READ_TIMEOUT_SECONDS,
            trust_env=False,
            follow_redirects=False,
        ) as client:
            report = check_target(client, args.project, args.zone)
    except PreflightError as error:
        print(dumps({"status": "blocked", "code": str(error), "deployment_authorized": False}))
        return 2
    print(dumps(report, indent=2))
    return 0 if report["status"] == "technical_checks_passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
