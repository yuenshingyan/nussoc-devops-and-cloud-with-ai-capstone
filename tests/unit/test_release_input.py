from gzip import compress
from hashlib import sha256
from os import link
from pathlib import Path
from stat import S_IMODE
from time import monotonic

from pytest import fixture, mark, raises

from scripts.release_input import prepare_crane_tar


@fixture
def inputs(tmp_path: Path) -> tuple[Path, Path, bytes]:
    root = tmp_path.resolve()
    root.chmod(0o700)
    destination = root / "output"
    destination.mkdir(mode=0o700)
    source = root / "image.tar.gz"
    raw = b"synthetic tar bytes; image validation is a separate gate"
    source.write_bytes(compress(raw, mtime=0))
    source.chmod(0o600)
    return source, destination, raw


def prepare(inputs: tuple[Path, Path, bytes]) -> dict:
    source, directory, _ = inputs
    return prepare_crane_tar(
        source, directory, sha256(source.read_bytes()).hexdigest(), monotonic() + 5
    )


def test_materialization_preserves_exact_bytes_without_extracting(inputs):
    source, directory, raw = inputs
    before = source.read_bytes()
    result = prepare(inputs)
    assert result == {
        "status": "prepared",
        "archive_sha256": sha256(before).hexdigest(),
        "tar_sha256": sha256(raw).hexdigest(),
        "compressed_bytes": len(before),
        "tar_bytes": len(raw),
        "publishing_authorized": False,
    }
    assert (directory / "image.tar").read_bytes() == raw
    assert S_IMODE((directory / "image.tar").stat().st_mode) == 0o600
    assert source.read_bytes() == before
    assert list(directory.iterdir()) == [directory / "image.tar"]


def test_digest_mismatch_removes_partial_output(inputs):
    source, directory, _ = inputs
    with raises(ValueError, match="HASH_MISMATCH"):
        prepare_crane_tar(source, directory, "f" * 64, monotonic() + 5)
    assert list(directory.iterdir()) == []


@mark.parametrize("damage", ["truncate", "checksum", "trailing", "empty"])
def test_invalid_gzip_removes_partial_output(inputs, damage):
    source, directory, _ = inputs
    original = source.read_bytes()
    if damage == "truncate":
        data = original[:-3]
    elif damage == "checksum":
        data = original[:-8] + bytes([original[-8] ^ 1]) + original[-7:]
    elif damage == "trailing":
        data = original + b"non-gzip-trailing-data"
    else:
        data = compress(b"", mtime=0)
    source.write_bytes(data)
    with raises((OSError, EOFError, ValueError)):
        prepare(inputs)
    assert list(directory.iterdir()) == []


def test_existing_output_is_never_overwritten_or_removed(inputs):
    _, directory, _ = inputs
    (directory / "image.tar").write_bytes(b"existing owned elsewhere")
    with raises(FileExistsError):
        prepare(inputs)
    assert (directory / "image.tar").read_bytes() == b"existing owned elsewhere"


def test_existing_output_symlink_is_not_followed_or_removed(inputs):
    source, directory, _ = inputs
    before = source.read_bytes()
    (directory / "image.tar").symlink_to(source)
    with raises(FileExistsError):
        prepare(inputs)
    assert (directory / "image.tar").is_symlink()
    assert source.read_bytes() == before


@mark.parametrize("mode", [0o644, 0o660, 0o777])
def test_source_must_be_private(inputs, mode):
    source, _, _ = inputs
    source.chmod(mode)
    with raises(ValueError, match="SOURCE_INVALID"):
        prepare(inputs)


def test_source_symlink_is_rejected(inputs):
    source, directory, raw = inputs
    other = source.parent / "linked.gz"
    other.symlink_to(source)
    with raises(ValueError, match="SOURCE_INVALID"):
        prepare((other, directory, raw))


def test_source_hardlink_is_rejected(inputs):
    source, _, _ = inputs
    link(source, source.parent / "linked.gz")
    with raises(ValueError, match="SOURCE_INVALID"):
        prepare(inputs)


@mark.parametrize("which", ["source", "destination"])
def test_parent_directories_must_be_private(inputs, which):
    source, directory, _ = inputs
    (source.parent if which == "source" else directory).chmod(0o755)
    with raises(ValueError, match="DIRECTORY_INVALID"):
        prepare(inputs)


@mark.parametrize("digest", [None, True, "a" * 63, "A" * 64])
def test_digest_is_not_coerced(inputs, digest):
    source, directory, _ = inputs
    with raises(ValueError, match="DIGEST_INVALID"):
        prepare_crane_tar(source, directory, digest, monotonic() + 5)


@mark.parametrize("deadline", [True, float("nan"), float("inf"), 0.0])
def test_invalid_budget_creates_no_output(inputs, deadline):
    source, directory, _ = inputs
    with raises(ValueError, match="BUDGET_INVALID"):
        prepare_crane_tar(source, directory, sha256(source.read_bytes()).hexdigest(), deadline)
    assert not (directory / "image.tar").exists()


def test_expanded_bytes_cannot_exceed_limit(inputs, monkeypatch):
    source, directory, _ = inputs
    source.write_bytes(compress(b"x" * 1025, mtime=0))
    monkeypatch.setitem(prepare_crane_tar.__globals__, "LIMIT", 1024)
    with raises(ValueError, match="TAR_LIMIT"):
        prepare(inputs)
    assert not (directory / "image.tar").exists()


def test_exact_expanded_limit_is_accepted(inputs, monkeypatch):
    source, directory, _ = inputs
    source.write_bytes(compress(b"x" * 1024, mtime=0))
    monkeypatch.setitem(prepare_crane_tar.__globals__, "LIMIT", 1024)
    assert prepare(inputs)["tar_bytes"] == 1024
    assert (directory / "image.tar").read_bytes() == b"x" * 1024


def test_deadline_during_read_removes_owned_output(inputs, monkeypatch):
    source, directory, _ = inputs
    clock = iter([0.0, 0.0, 2.0])
    monkeypatch.setitem(prepare_crane_tar.__globals__, "monotonic", lambda: next(clock))
    with raises(TimeoutError, match="INPUT_TIMEOUT"):
        prepare_crane_tar(source, directory, sha256(source.read_bytes()).hexdigest(), 1.0)
    assert not (directory / "image.tar").exists()


def test_oversized_compressed_input_is_rejected_before_output(inputs, monkeypatch):
    _, directory, _ = inputs
    monkeypatch.setitem(prepare_crane_tar.__globals__, "LIMIT", 1)
    with raises(ValueError, match="SOURCE_INVALID"):
        prepare(inputs)
    assert not (directory / "image.tar").exists()


def test_cleanup_failure_preserves_primary_error_with_safe_note(inputs, monkeypatch):
    source, directory, _ = inputs

    def failed_unlink(path: Path) -> None:
        raise OSError("synthetic private diagnostic")

    monkeypatch.setattr(Path, "unlink", failed_unlink)
    with raises(ValueError, match="HASH_MISMATCH") as caught:
        prepare_crane_tar(source, directory, "f" * 64, monotonic() + 5)
    assert caught.value.__notes__ == [
        "RELEASE_INPUT_PARTIAL_CLEANUP_FAILED_INSPECT_OWNED_DIRECTORY"
    ]
    assert (directory / "image.tar").exists()
