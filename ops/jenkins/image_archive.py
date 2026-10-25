"""Inspect an owned Docker-export artifact without extracting files or loading Docker."""

from hashlib import sha256
from json import loads
from pathlib import Path
from re import fullmatch
from tarfile import TarFile


def read_archive_json(archive: TarFile, name: str) -> bytes:
    """Read one small, unique regular JSON member; reject links and ambiguous entries."""
    members = [member for member in archive.getmembers() if member.name == name]
    if len(members) != 1 or not members[0].isfile() or not 0 < members[0].size <= 1048576:
        raise RuntimeError("Expected one regular JSON member of at most 1 MiB")
    with archive.extractfile(members[0]) as source:
        return source.read()


def inspect_image_archive(
    path: Path, revision: str, tag: str, config_digest: str
) -> dict[str, str]:
    """Check one ARM64 application image against its build metadata before operator loading."""
    if not fullmatch(r"sha256:[a-f0-9]{64}", config_digest):
        raise RuntimeError("Invalid image configuration digest")
    with TarFile.open(path, mode="r:gz") as archive:
        manifest = loads(read_archive_json(archive, "manifest.json"))
        if not isinstance(manifest, list) or len(manifest) != 1:
            raise RuntimeError("Expected exactly one exported image")
        if manifest[0].get("RepoTags") != [tag]:
            raise RuntimeError("Exported image tag differs from this build")
        config = read_archive_json(archive, manifest[0]["Config"])
    digest = "sha256:" + sha256(config).hexdigest()
    if digest != config_digest:
        raise RuntimeError("Image configuration digest does not match BuildKit metadata")
    data = loads(config)
    if (data.get("os"), data.get("architecture")) != ("linux", "arm64"):
        raise RuntimeError("Expected the explicitly selected linux/arm64 platform")
    if data["config"].get("User") != "10001:10001":
        raise RuntimeError("Exported image must use the application non-root identity")
    if data["config"].get("Labels", {}).get("org.opencontainers.image.revision") != revision:
        raise RuntimeError("Exported image source label does not match the checkout")
    return {"image_id": digest, "platform": "linux/arm64", "local_tag": tag}
