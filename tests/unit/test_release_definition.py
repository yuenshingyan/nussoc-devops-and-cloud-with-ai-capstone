from base64 import b64decode
from hashlib import sha256
from os import link, mkfifo
from pathlib import Path
from re import findall
from runpy import run_path

from pytest import MonkeyPatch, fixture, mark, raises

ROOT = Path(__file__).resolve().parents[2]


@fixture
def helpers(monkeypatch: MonkeyPatch) -> dict:
    monkeypatch.syspath_prepend(str(ROOT / "ops/jenkins"))
    return run_path(str(ROOT / "ops/jenkins/release_definition.py"))


def test_definition_is_deterministic_and_has_separate_class_boundaries(helpers):
    script = helpers["assemble_definition"]()
    assert script == helpers["assemble_definition"]()
    assert "}class " not in script
    assert "RELEASE_DISABLED_ARTIFACT_TRANSFER_AND_DEPLOYMENT_NOT_IMPLEMENTED" not in script
    assert "RELEASE_DISABLED_PUBLISHING_AND_DEPLOYMENT_NOT_IMPLEMENTED" in script
    imports = [line for line in script.splitlines() if line.startswith("import ")]
    assert imports == sorted(set(imports))


def test_definition_contains_only_reviewed_tool_bytes_and_hashes(helpers):
    bundle = helpers["verifier_bundle"](ROOT)
    entries = findall(r"'([^']+\.py)':\[([^\]]+)\]\.join\(''\)", bundle)
    assert {name for name, _ in entries} == set(helpers["TOOLS"])
    for name, expression in entries:
        chunks = findall(r"'([^']+)'", expression)
        assert all(len(chunk) <= helpers["CHUNK_SIZE"] for chunk in chunks)
        decoded = b64decode("".join(chunks), validate=True)
        assert decoded == (ROOT / name).read_bytes()
        assert sha256(decoded).hexdigest() in bundle


def test_flow_verifies_and_rechecks_before_disabled_stop(helpers):
    flow = (ROOT / "ops/jenkins/release-flow.groovy").read_text()
    operations = [
        "FinsecureCandidateSelection.select(",
        "node('release')",
        "FinsecureReleasePreparation.prepare(",
        "FinsecureCandidateSelection.confirmSelection(",
        "FinsecureVerifierBundle.install(",
        "python -I -B",
        "FinsecureWorkerVerification.readResult(",
        "stage('Recheck candidate after verification')",
        "FinsecureWorkerVerification.cleanup(",
        "RELEASE_DISABLED_PUBLISHING_AND_DEPLOYMENT_NOT_IMPLEMENTED",
    ]
    assert [flow.index(value) for value in operations] == sorted(
        flow.index(value) for value in operations
    )
    assert "timeout(time: 10, unit: 'MINUTES')" in flow
    assert "timeout(time: 2, unit: 'MINUTES')" in flow
    assert "followSymlinks: false" in flow
    assert "umask 077" in flow
    for forbidden in ("withCredentials(", "retry(", "deleteDir(", "kubectl ", "crane "):
        assert forbidden not in flow


@mark.parametrize("size", [1, 16001, 1024 * 1024])
def test_encoding_round_trips_without_large_jvm_constants(helpers, size):
    data = b"x" * size
    expression = helpers["encoded_expression"](data)
    chunks = findall(r"'([^']+)'", expression)
    assert max(map(len, chunks)) <= 16000
    assert b64decode("".join(chunks), validate=True) == data


@mark.parametrize("size", [0, 1024 * 1024 + 1])
def test_encoding_rejects_empty_or_oversized_source(helpers, size):
    with raises(ValueError, match="TOOL_SIZE_INVALID"):
        helpers["encoded_expression"](b"x" * size)


@mark.parametrize("kind", ["symlink", "parent_symlink", "hardlink", "fifo", "empty", "large"])
def test_local_source_rejects_unsafe_file_types_and_sizes(helpers, tmp_path, kind):
    source = tmp_path / "source.py"
    other = tmp_path / "other.py"
    other.write_bytes(b"reviewed")
    name = "source.py"
    if kind == "symlink":
        source.symlink_to(other)
    elif kind == "parent_symlink":
        directory = tmp_path / "original"
        directory.mkdir()
        (directory / "source.py").write_bytes(b"reviewed")
        (tmp_path / "linked").symlink_to(directory, target_is_directory=True)
        name = "linked/source.py"
    elif kind == "hardlink":
        link(other, source)
    elif kind == "fifo":
        mkfifo(source)
    else:
        source.write_bytes(b"" if kind == "empty" else b"x" * (1024 * 1024 + 1))
    with raises(ValueError, match="LOCAL_SOURCE_INVALID"):
        helpers["source_bytes"](tmp_path, name)


def test_local_source_accepts_exact_size_limit(helpers, tmp_path):
    source = tmp_path / "source.py"
    source.write_bytes(b"x" * (1024 * 1024))
    assert helpers["source_bytes"](tmp_path, "source.py") == source.read_bytes()


def test_local_source_rejects_escape_from_review_root(helpers, tmp_path):
    folder = tmp_path / "review"
    folder.mkdir()
    (tmp_path / "outside.py").write_bytes(b"not reviewed")
    with raises(ValueError, match="LOCAL_SOURCE_INVALID"):
        helpers["source_bytes"](folder, "../outside.py")


@mark.parametrize("count", [0, 2])
def test_assembly_rejects_ambiguous_selection_boundary(helpers, monkeypatch, count):
    state = helpers["assemble_definition"].__globals__
    marker = helpers["SELECTION_BOUNDARY"]
    monkeypatch.setitem(state, "source_bytes", lambda root, name: (marker * count).encode())
    with raises(ValueError, match="SELECTION_BOUNDARY_INVALID"):
        helpers["assemble_definition"]()
