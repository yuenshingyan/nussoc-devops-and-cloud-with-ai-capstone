"""Verify exported metadata without extracting archives or starting containers."""

from hashlib import sha256
from io import BytesIO
from json import dumps
from pathlib import Path
from runpy import run_path
from tarfile import SYMTYPE, TarFile, TarInfo
from typing import Any

from pytest import fixture, mark, raises

REVISION = "a" * 40
TAG = "finsecure-pay-ci:synthetic-build"


@fixture
def archive_helpers() -> dict[str, Any]:
    return run_path(str(Path(__file__).resolve().parents[2] / "ops/jenkins/image_archive.py"))


@fixture
def image_config() -> dict:
    return {
        "os": "linux",
        "architecture": "arm64",
        "config": {
            "User": "10001:10001",
            "Labels": {"org.opencontainers.image.revision": REVISION},
        },
    }


def write_image(directory: Path, config: dict, tags: list[str]) -> tuple[Path, str]:
    """Create a tiny synthetic Docker export with no filesystem layers."""
    data = dumps(config).encode()
    digest = "sha256:" + sha256(data).hexdigest()
    path = directory / "image.tar.gz"
    with TarFile.open(path, mode="w:gz") as archive:
        for name, content in [
            ("manifest.json", dumps([{"Config": "config.json", "RepoTags": tags}]).encode()),
            ("config.json", data),
        ]:
            member = TarInfo(name)
            member.size = len(content)
            archive.addfile(member, BytesIO(content))
    return path, digest


def test_image_identity_matches_export_metadata(archive_helpers, image_config, tmp_path):
    path, digest = write_image(tmp_path, image_config, [TAG])
    assert archive_helpers["inspect_image_archive"](path, REVISION, TAG, digest) == {
        "image_id": digest,
        "platform": "linux/arm64",
        "local_tag": TAG,
    }
    assert sorted(item.name for item in tmp_path.iterdir()) == ["image.tar.gz"]


@mark.parametrize("digest", ["bad-digest", "sha256:" + "0" * 64])
def test_wrong_digest_is_rejected(archive_helpers, image_config, tmp_path, digest):
    path, _ = write_image(tmp_path, image_config, [TAG])
    with raises(RuntimeError, match="digest"):
        archive_helpers["inspect_image_archive"](path, REVISION, TAG, digest)


@mark.parametrize("tags", [[], ["other:tag"], [TAG, "extra:tag"]])
def test_unexpected_image_tags_are_rejected(archive_helpers, image_config, tmp_path, tags):
    path, digest = write_image(tmp_path, image_config, tags)
    with raises(RuntimeError, match="tag differs"):
        archive_helpers["inspect_image_archive"](path, REVISION, TAG, digest)


@mark.parametrize("change", ["platform", "identity", "revision"])
def test_wrong_image_properties_are_rejected(archive_helpers, image_config, tmp_path, change):
    if change == "platform":
        image_config["architecture"] = "amd64"
    elif change == "identity":
        image_config["config"]["User"] = "0:0"
    else:
        image_config["config"]["Labels"]["org.opencontainers.image.revision"] = "b" * 40
    path, digest = write_image(tmp_path, image_config, [TAG])
    with raises(RuntimeError):
        archive_helpers["inspect_image_archive"](path, REVISION, TAG, digest)


@mark.parametrize("kind", ["missing", "duplicate", "symlink", "oversized"])
def test_unsafe_json_members_are_rejected(archive_helpers, tmp_path, kind):
    path = tmp_path / "members.tar.gz"
    with TarFile.open(path, "w:gz") as archive:
        if kind == "symlink":
            member = TarInfo("manifest.json")
            member.type = SYMTYPE
            member.linkname = "/outside/synthetic-private-file"
            archive.addfile(member)
        elif kind != "missing":
            data = b"x" * 1048577 if kind == "oversized" else b"{}"
            for _ in range(2 if kind == "duplicate" else 1):
                member = TarInfo("manifest.json")
                member.size = len(data)
                archive.addfile(member, BytesIO(data))
    with TarFile.open(path, "r:gz") as archive, raises(RuntimeError, match="regular JSON"):
        archive_helpers["read_archive_json"](archive, "manifest.json")
