"""Phase bridge for the fixed Jenkins delivery definition; never execute producer-supplied code."""

from argparse import ArgumentParser, Namespace
from datetime import UTC, datetime
from json import dumps
from os import environ, fchmod
from pathlib import Path
from re import fullmatch
from sys import executable
from tempfile import TemporaryDirectory
from time import monotonic

from scripts.release_archive import strict_json
from scripts.release_artifacts import object_file, verify_artifacts
from scripts.release_command import run_command
from scripts.release_execute import supervise
from scripts.release_http import remaining
from scripts.release_input import prepare_crane_tar, private_directory
from scripts.release_publication import publication_preflight, push_prepared
from scripts.release_registry import COOKIES, require

PHASES = ("init", "prepare", "preflight", "publish", "deploy")


def save(path: Path, document: dict) -> None:
    """Create one private report/journal without overwriting an earlier attempt."""
    with path.open("x", encoding="utf-8") as stream:
        fchmod(stream.fileno(), 0o600)
        stream.write(dumps(document, allow_nan=False))


def identity(root: Path) -> dict:
    """Bind actions to the controller receipt and successful independent verifier report."""
    context = object_file(root / "control/receipt.json")["context"]
    report = object_file(root / "verification.json")
    require(
        report.get("status") == "verified" and report.get("publishing_authorized") is False,
        "RELEASE_VERIFICATION_REQUIRED",
    )
    result = {}
    for name in ("revision", "image_id", "archive_sha256"):
        require(report.get(name) == context.get(name), "RELEASE_PHASE_IDENTITY_CHANGED")
        result[name] = context[name]
    return result


def child_phase(arguments: Namespace) -> dict:
    """Run one phase under the parent's shared deadline and owned profile directory."""
    require(arguments.phase in PHASES[1:], "RELEASE_CHILD_PHASE_INVALID")
    root = Path(arguments.root)
    deadline = object_file(root / "budget.json")["deadline"]
    remaining(deadline)
    original = identity(root)
    profiles = Path(arguments.profiles)
    private_directory(profiles)
    if arguments.phase in {"prepare", "publish", "deploy"}:
        # Re-evaluate raw gate timestamps, rather than reuse an ageing success boolean.
        verify_artifacts(root / "input", root / "control", datetime.now(UTC))
        remaining(deadline)
    if arguments.phase == "prepare":
        directory = root / "publication-input"
        directory.mkdir(mode=0o700)
        result = prepare_crane_tar(
            root / "input/images/finsecure-pay.tar.gz",
            directory,
            original["archive_sha256"],
            deadline,
        )
    else:
        prepared = object_file(root / "prepare.json")
        require(prepared.get("status") == "prepared", "RELEASE_PREPARATION_REQUIRED")
        require(
            all(prepared.get(key) == value for key, value in original.items()),
            "RELEASE_PHASE_IDENTITY_CHANGED",
        )
        tar = root / "publication-input/image.tar"
        key = Path(arguments.credential)
        if arguments.phase == "preflight":
            digest = publication_preflight(
                tar,
                prepared["tar_sha256"],
                original["revision"],
                key,
                profiles,
                dict(environ),
                deadline,
            )
            result = {"status": "preflight_verified", "local_manifest_digest": digest}
        else:
            preflight = object_file(root / "preflight.json")
            require(
                all(preflight.get(key) == value for key, value in original.items()),
                "RELEASE_PHASE_IDENTITY_CHANGED",
            )
            require(preflight.get("status") == "preflight_verified", "RELEASE_PREFLIGHT_REQUIRED")
            digest = preflight["local_manifest_digest"]
            if arguments.phase == "publish":
                result = push_prepared(
                    tar,
                    prepared["tar_sha256"],
                    original["revision"],
                    digest,
                    original["image_id"],
                    key,
                    profiles,
                    dict(environ),
                    deadline,
                )
            else:
                published = object_file(root / "publish.json")
                require(
                    published.get("status") == "verified"
                    and published.get("registry_manifest_digest") == digest
                    and all(published.get(key) == value for key, value in original.items()),
                    "RELEASE_REGISTRY_PROOF_REQUIRED",
                )
                result = supervise(
                    Namespace(
                        key=str(key),
                        directory=str(profiles),
                        uid=arguments.uid,
                        spec_sha256=arguments.spec_sha256,
                        digest=digest,
                        deadline=deadline,
                    )
                )
    return {**result, **original}


def phase(arguments: Namespace) -> dict:
    """Journal each mutation before launch and supervise the full phase, not just crane."""
    root = Path(arguments.root)
    private_directory(root)
    if arguments.phase == "init":
        require(0 < arguments.remaining_ms <= 600000, "RELEASE_BUDGET_INVALID")
        save(root / "budget.json", {"deadline": monotonic() + arguments.remaining_ms / 1000})
        return {"status": "initialized"}
    require(not (root / (arguments.phase + ".json")).exists(), "RELEASE_PHASE_ALREADY_RECORDED")
    deadline = object_file(root / "budget.json")["deadline"]
    remaining(deadline)
    if arguments.phase in {"publish", "deploy"}:
        save(
            root / (arguments.phase + "-attempt.json"),
            {
                "status": "started",
                "started_at_utc": datetime.now(UTC).isoformat(),
                **identity(root),
            },
        )
    with TemporaryDirectory(dir=root, prefix="phase-profile-") as temporary:
        environment = {key: environ[key] for key in COOKIES if key in environ}
        environment.update(HOME=temporary, TMPDIR=temporary, PATH="/usr/local/bin:/usr/bin:/bin")
        command = [
            executable,
            "-I",
            "-B",
            "-c",
            "from sys import argv,path; from runpy import run_module; "
            'path.insert(0,argv.pop(1)); run_module("scripts.release_worker",run_name="__main__")',
            str(Path(__file__).resolve().parents[1]),
            "--child",
            "--phase",
            arguments.phase,
            "--root",
            str(root),
            "--profiles",
            temporary,
            "--credential",
            arguments.credential,
            "--uid",
            arguments.uid,
            "--spec-sha256",
            arguments.spec_sha256,
        ]
        result = run_command(command, environment, deadline)
        document = strict_json(result.stdout)
        require(type(document) is dict, "RELEASE_PHASE_RESULT_INVALID")
        if result.returncode:
            code = document.get("code")
            if type(code) is str and fullmatch(r"[A-Z][A-Z_]{1,127}", code):
                raise RuntimeError(code)
            raise RuntimeError("RELEASE_PHASE_FAILED_INSPECT_OUTCOME_MANUALLY")
    save(root / (arguments.phase + ".json"), document)
    return document


def main() -> int:
    """Emit safe phase results; never relaunch an uncertain external action."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=PHASES, required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--remaining-ms", type=int, default=0)
    parser.add_argument("--profiles", default="")
    parser.add_argument("--credential", default="")
    parser.add_argument("--uid", default="")
    parser.add_argument("--spec-sha256", default="")
    parser.add_argument("--child", action="store_true")
    arguments = parser.parse_args()
    try:
        result = child_phase(arguments) if arguments.child else phase(arguments)
    except Exception as error:
        message = str(error)
        code = message if fullmatch(r"[A-Z][A-Z_]{1,127}", message) else "RELEASE_PHASE_FAILED"
        print(dumps({"status": "failed", "code": code, "operator_inspection_required": True}))
        return 2
    print(dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
