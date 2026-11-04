from argparse import Namespace
from json import loads
from pathlib import Path
from runpy import run_path

from pytest import raises

from scripts.release_worker import phase, save


def arguments(root: Path, name: str) -> Namespace:
    return Namespace(
        root=str(root), phase=name, remaining_ms=30000, credential="", uid="", spec_sha256=""
    )


def test_phase_budget_cannot_be_renewed(tmp_path):
    root = tmp_path.resolve()
    root.chmod(0o700)
    assert phase(arguments(root, "init")) == {"status": "initialized"}
    before = (root / "budget.json").read_bytes()
    with raises(FileExistsError):
        phase(arguments(root, "init"))
    assert (root / "budget.json").read_bytes() == before


def test_uncertain_publication_cannot_be_relaunched_in_same_workspace(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    root.chmod(0o700)
    phase(arguments(root, "init"))
    (root / "control").mkdir(mode=0o700)
    context = {"revision": "a" * 40, "image_id": "sha256:" + "b" * 64, "archive_sha256": "c" * 64}
    save(root / "control/receipt.json", {"context": context})
    save(
        root / "verification.json",
        {"status": "verified", "publishing_authorized": False, **context},
    )
    calls = []

    def command(argv: list[str], environment: dict[str, str], deadline: float) -> None:
        calls.append(environment["HOME"])
        Path(environment["HOME"], "partial-client-cache").write_text("synthetic")
        raise TimeoutError("RELEASE_COMMAND_TIMEOUT_OUTCOME_UNKNOWN")

    monkeypatch.setattr("scripts.release_worker.run_command", command)
    with raises(TimeoutError):
        phase(arguments(root, "publish"))
    assert loads((root / "publish-attempt.json").read_text())["revision"] == context["revision"]
    assert not Path(calls[0]).exists()
    with raises(FileExistsError):
        phase(arguments(root, "publish"))
    assert len(calls) == 1


def test_delivery_assembly_is_explicit_and_dry_by_default(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root / "ops/jenkins"))
    helper = run_path(str(root / "ops/jenkins/release_definition.py"))
    dry = helper["assemble_definition"](delivery=True)
    live = helper["assemble_definition"](delivery=True, mutations=True)
    marker = "final boolean FINSECURE_MUTATIONS_ENABLED = "
    assert marker + "false" in dry and marker + "true" in live
    assert dry.replace(marker + "false", marker + "true") == live
    assert "finsecure-dockerhub" in live and "finsecure-gke-deployer" in live
    assert "retry(" not in live
    flow = (root / "ops/jenkins/release-delivery-flow.groovy").read_text()
    assert flow.index("Verify without release credentials") < flow.index("withCredentials(")
    assert flow.count("FinsecureCandidateSelection.recheck(") == 4
    assert "*-attempt.json" in flow and "followSymlinks: false" in flow
