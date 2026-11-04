"""Supervise the fixed deployment/rollout/smoke phase; callable only by trusted release control."""

from argparse import ArgumentParser, Namespace
from json import dumps
from os import environ
from pathlib import Path
from re import fullmatch
from sys import executable
from tempfile import TemporaryDirectory

from scripts.release_archive import strict_json
from scripts.release_cluster import (
    adc_token,
    client_environment,
    cluster_endpoint,
    credential_project,
)
from scripts.release_command import run_command
from scripts.release_http import DeploymentClient, remaining
from scripts.release_input import private_directory
from scripts.release_registry import COOKIES
from scripts.release_rollout import deploy_and_wait
from scripts.release_smoke import verify_service, verify_smoke


def execute_child(arguments: Namespace) -> dict:
    """Own a private ADC profile; borrow the fixed Jenkins GKE file binding without deleting it."""
    remaining(arguments.deadline)
    parent = Path(arguments.directory)
    private_directory(parent)
    key = Path(arguments.key)
    project = credential_project(key)
    with TemporaryDirectory(dir=parent, prefix="deployment-client-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        environment = client_environment(key, directory)
        token = adc_token(environment)
        endpoint = cluster_endpoint(project, token)
        client = DeploymentClient(endpoint, token, arguments.deadline)
        verify_service(client.get_service())
        result = deploy_and_wait(client, arguments.uid, arguments.spec_sha256, arguments.digest)
        verify_service(client.get_service())
        verify_smoke(arguments.deadline)
        remaining(arguments.deadline)
        result.update(status="deployment_verified", smoke_verified=True)
    return result


def supervise(arguments: Namespace) -> dict:
    """Bound the entire child group, including ADC, discovery, DNS, PATCH and smoke I/O.

    An interruption can follow an accepted external mutation. No child relaunch, automatic
    rollback or interpretation of an unchanged image as recovery is supported. Controller
    candidate recheck/registry verification must precede invoking this mutation phase.
    """
    parent = Path(arguments.directory)
    private_directory(parent)
    remaining(arguments.deadline)
    with TemporaryDirectory(dir=parent, prefix="deployment-supervisor-") as temporary:
        environment = {key: environ[key] for key in COOKIES if key in environ}
        environment.update(HOME=temporary, TMPDIR=temporary, PATH="/usr/local/bin:/usr/bin:/bin")
        command = [
            executable,
            "-I",
            "-B",
            "-c",
            "from sys import argv,path; from runpy import run_module; "
            'path.insert(0,argv.pop(1)); run_module("scripts.release_execute",run_name="__main__")',
            str(Path(__file__).resolve().parents[1]),
            "--child",
            "--key",
            arguments.key,
            "--directory",
            temporary,
            "--uid",
            arguments.uid,
            "--spec-sha256",
            arguments.spec_sha256,
            "--digest",
            arguments.digest,
            "--deadline",
            str(arguments.deadline),
        ]
        result = run_command(command, environment, arguments.deadline)
        try:
            document = strict_json(result.stdout)
        except ValueError, RecursionError:
            raise RuntimeError("DEPLOYMENT_CHILD_RESULT_INVALID_INSPECT_OUTCOME_MANUALLY") from None
        if result.returncode != 0:
            # Preserve only a complete safe child failure code, never raw diagnostics.
            if (
                type(document) is dict
                and document.get("status") == "failed"
                and document.get("operator_inspection_required") is True
                and type(document.get("code")) is str
                and fullmatch(r"[A-Z][A-Z_]{1,127}", document["code"]) is not None
            ):
                raise RuntimeError(document["code"])
            raise RuntimeError("DEPLOYMENT_CHILD_FAILED_INSPECT_OUTCOME_MANUALLY")
        if (
            type(document) is not dict
            or set(document)
            != {
                "status",
                "deployment_uid",
                "generation",
                "spec_sha256",
                "pod_uids",
                "registry_manifest_digest",
                "elapsed_seconds",
                "smoke_verified",
                "automatic_rollback",
            }
            or document.get("status") != "deployment_verified"
            or document.get("deployment_uid") != arguments.uid
            or document.get("registry_manifest_digest") != arguments.digest
            or document.get("smoke_verified") is not True
            or document.get("automatic_rollback") is not False
            or type(document.get("generation")) is not int
            or document["generation"] <= 1
            or type(document.get("spec_sha256")) is not str
            or fullmatch(r"[a-f0-9]{64}", document["spec_sha256"]) is None
            or type(document.get("pod_uids")) is not list
            or len(document["pod_uids"]) != 2
            or not all(type(uid) is str and bool(uid) for uid in document["pod_uids"])
            or len(set(document["pod_uids"])) != 2
            or type(document.get("elapsed_seconds")) not in {int, float}
            or not 0 <= document["elapsed_seconds"] <= 600
        ):
            raise RuntimeError("DEPLOYMENT_CHILD_RESULT_INVALID_INSPECT_OUTCOME_MANUALLY")
    return document


def main() -> int:
    """Emit only bounded safe results, never credentials, raw cloud objects or tracebacks."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--child", action="store_true", help="Internal supervised child mode")
    for name in ("key", "directory", "uid", "spec-sha256", "digest"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--deadline", type=float, required=True)
    arguments = parser.parse_args()
    try:
        result = execute_child(arguments) if arguments.child else supervise(arguments)
    except Exception as error:
        message = str(error)
        code = message if fullmatch(r"[A-Z][A-Z_]{1,127}", message) else "DEPLOYMENT_PHASE_FAILED"
        print(dumps({"status": "failed", "code": code, "operator_inspection_required": True}))
        return 2
    print(dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
