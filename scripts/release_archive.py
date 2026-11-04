"""Validate bounded BuildKit Docker/OCI export bytes without extracting or running them."""

from gzip import GzipFile
from hashlib import sha256
from json import loads
from math import isfinite
from pathlib import Path
from re import fullmatch
from tarfile import TarFile
from time import monotonic
from typing import BinaryIO

from scripts.image_scan import unique_object

MIB = 1024 * 1024
ARCHIVE_LIMIT = 64 * MIB
JSON_LIMIT = MIB
MEMBER_LIMIT = 64
LAYER_LIMIT = 256 * MIB
EXPANDED_LIMIT = 512 * MIB


def reject_constant(value: str) -> None:
    """Do not accept JavaScript NaN/Infinity extensions as JSON numbers."""
    raise ValueError("NONFINITE_JSON")


def finite_float(text: str) -> float:
    """Reject finite-looking JSON literals that overflow the runtime's numeric range."""
    value = float(text)
    if not isfinite(value):
        raise ValueError("NONFINITE_JSON")
    return value


def strict_json(data: bytes) -> object:
    """Require UTF-8 and unique keys, without normalizing identifiers or tolerating suffixes."""
    if len(data) > JSON_LIMIT:
        raise ValueError("JSON_LIMIT_EXCEEDED")
    return loads(
        data.decode("utf-8"),
        object_pairs_hook=unique_object,
        parse_constant=reject_constant,
        parse_float=finite_float,
    )


class BoundedReader:
    """Borrow a stream; bound consumed bytes/time and hash them without taking ownership."""

    def __init__(self, stream: BinaryIO, limit: int, deadline: float) -> None:
        self.stream = stream
        self.limit = limit
        self.deadline = deadline
        self.count = 0
        self.digest = sha256()

    def read(self, size: int = -1) -> bytes:
        if monotonic() >= self.deadline:
            raise TimeoutError("ARCHIVE_BUDGET_EXCEEDED")
        if size < 0:
            size = self.limit - self.count + 1
        data = self.stream.read(min(size, self.limit - self.count + 1))
        self.count += len(data)
        if self.count > self.limit:
            raise ValueError("ARCHIVE_EXPANSION_LIMIT")
        self.digest.update(data)
        return data


def inspect_release_archive(
    path: Path, revision: str, tag: str, image_id: str, deadline: float
) -> dict:
    """Bind blob hashes, OCI descriptors and expanded layer diff IDs to one AMD64 config."""
    blobs = {}
    documents = {}
    seen = set()
    expanded = 0
    with path.open("rb") as raw, GzipFile(fileobj=raw) as compressed:
        bounded = BoundedReader(compressed, ARCHIVE_LIMIT, deadline)
        with TarFile.open(fileobj=bounded, mode="r|") as archive:
            for member in archive:
                name = member.name
                if name in seen or len(seen) >= MEMBER_LIMIT:
                    raise ValueError("AMBIGUOUS_ARCHIVE_MEMBERS")
                seen.add(name)
                if member.isdir() and name in {"blobs", "blobs/sha256"}:
                    continue
                blob = fullmatch(r"blobs/sha256/([a-f0-9]{64})", name)
                if (
                    not member.isfile()
                    or not 0 < member.size <= ARCHIVE_LIMIT
                    or not (blob or name in {"manifest.json", "index.json", "oci-layout"})
                ):
                    raise ValueError("UNSAFE_ARCHIVE_MEMBER")
                with archive.extractfile(member) as stream:
                    # A buffered peek distinguishes gzip layers without rewinding the outer tar.
                    prefix = stream.read(2)
                    if prefix == b"\x1f\x8b":
                        if not blob:
                            raise ValueError("UNEXPECTED_COMPRESSED_METADATA")
                        reader = PrefixReader(prefix, stream)
                        hashing = BoundedReader(reader, member.size, deadline)
                        layer_hash = sha256()
                        layer_size = 0
                        with GzipFile(fileobj=hashing) as layer:
                            while chunk := layer.read(65536):
                                layer_size += len(chunk)
                                expanded += len(chunk)
                                if layer_size > LAYER_LIMIT or expanded > EXPANDED_LIMIT:
                                    raise ValueError("LAYER_EXPANSION_LIMIT")
                                if monotonic() >= deadline:
                                    raise TimeoutError("ARCHIVE_BUDGET_EXCEEDED")
                                layer_hash.update(chunk)
                        if hashing.count != member.size or hashing.digest.hexdigest() != blob[1]:
                            raise ValueError("LAYER_BLOB_HASH_MISMATCH")
                        blobs[name] = {
                            "size": member.size,
                            "diff_id": "sha256:" + layer_hash.hexdigest(),
                        }
                    else:
                        if member.size > JSON_LIMIT:
                            raise ValueError("JSON_LIMIT_EXCEEDED")
                        data = prefix + stream.read(JSON_LIMIT + 1)
                        if len(data) != member.size or (
                            blob and sha256(data).hexdigest() != blob[1]
                        ):
                            raise ValueError("JSON_BLOB_HASH_MISMATCH")
                        documents[name] = strict_json(data)
                        if blob:
                            blobs[name] = {"size": member.size}
            # Consume the gzip footer and reject nonzero trailing tar content/oversized padding.
            while chunk := archive.fileobj.read(65536):
                if any(chunk):
                    raise ValueError("ARCHIVE_TRAILING_CONTENT")
    manifest = documents.get("manifest.json")
    index = documents.get("index.json")
    if documents.get("oci-layout") != {"imageLayoutVersion": "1.0.0"}:
        raise ValueError("INVALID_OCI_LAYOUT")
    if not isinstance(manifest, list) or len(manifest) != 1 or not isinstance(manifest[0], dict):
        raise ValueError("INVALID_DOCKER_MANIFEST")
    if (
        not isinstance(index, dict)
        or type(index.get("schemaVersion")) is not int
        or index["schemaVersion"] != 2
    ):
        raise ValueError("INVALID_OCI_INDEX")
    if index.get("mediaType") != "application/vnd.oci.image.index.v1+json":
        raise ValueError("INVALID_OCI_INDEX_TYPE")
    descriptors = index.get("manifests")
    if not isinstance(descriptors, list) or len(descriptors) != 1:
        raise ValueError("AMBIGUOUS_OCI_INDEX")
    descriptor = descriptors[0]
    if descriptor.get("platform") != {"architecture": "amd64", "os": "linux"}:
        raise ValueError("WRONG_OCI_PLATFORM")
    oci_name = descriptor_name(descriptor, "application/vnd.oci.image.manifest.v1+json", blobs)
    oci = documents.get(oci_name)
    if (
        not isinstance(oci, dict)
        or type(oci.get("schemaVersion")) is not int
        or oci["schemaVersion"] != 2
    ):
        raise ValueError("INVALID_OCI_MANIFEST")
    if oci.get("mediaType") != "application/vnd.oci.image.manifest.v1+json":
        raise ValueError("INVALID_OCI_MANIFEST_TYPE")
    config_name = descriptor_name(
        oci.get("config", {}), "application/vnd.oci.image.config.v1+json", blobs
    )
    if config_name != "blobs/sha256/" + image_id.removeprefix("sha256:"):
        raise ValueError("CONFIG_ID_MISMATCH")
    config = documents.get(config_name)
    if (
        not isinstance(config, dict)
        or config.get("os") != "linux"
        or config.get("architecture") != "amd64"
    ):
        raise ValueError("WRONG_CONFIG_PLATFORM")
    settings = config.get("config", {})
    if (
        settings.get("User") != "10001:10001"
        or settings.get("Labels", {}).get("org.opencontainers.image.revision") != revision
    ):
        raise ValueError("CONFIG_IDENTITY_MISMATCH")
    layers = oci.get("layers")
    if not isinstance(layers, list) or not layers:
        raise ValueError("MISSING_OCI_LAYERS")
    names = [
        descriptor_name(item, "application/vnd.oci.image.layer.v1.tar+gzip", blobs)
        for item in layers
    ]
    if len(set(names)) != len(names) or any("diff_id" not in blobs[name] for name in names):
        raise ValueError("INVALID_OCI_LAYERS")
    if config.get("rootfs") != {
        "type": "layers",
        "diff_ids": [blobs[name]["diff_id"] for name in names],
    }:
        raise ValueError("LAYER_DIFF_IDS_MISMATCH")
    if (
        manifest[0].get("RepoTags") != [tag]
        or manifest[0].get("Config") != config_name
        or manifest[0].get("Layers") != names
    ):
        raise ValueError("MANIFEST_IDENTITY_MISMATCH")
    if set(blobs) != {config_name, oci_name, *names}:
        raise ValueError("UNREFERENCED_ARCHIVE_BLOB")
    return {
        "image_id": image_id,
        "platform": "linux/amd64",
        "layers": len(names),
        "expanded_layer_bytes": expanded,
        "archive_oci_manifest_digest": descriptor["digest"],
    }


class PrefixReader:
    """Borrow a forward-only stream and put back the two format-detection bytes."""

    def __init__(self, prefix: bytes, stream: BinaryIO) -> None:
        self.prefix = prefix
        self.stream = stream

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            raise ValueError("UNBOUNDED_LAYER_READ")
        prefix, self.prefix = self.prefix[:size], self.prefix[size:]
        return prefix + self.stream.read(size - len(prefix))


def descriptor_name(descriptor: dict, media_type: str, blobs: dict) -> str:
    """Require a descriptor to refer to one already-hashed regular blob of the exact size."""
    if not isinstance(descriptor, dict) or not set(descriptor) <= {
        "mediaType",
        "digest",
        "size",
        "annotations",
        "platform",
    }:
        raise ValueError("INVALID_OCI_DESCRIPTOR_FIELDS")
    digest = descriptor.get("digest")
    if (
        descriptor.get("mediaType") != media_type
        or not isinstance(digest, str)
        or not fullmatch(r"sha256:[a-f0-9]{64}", digest)
    ):
        raise ValueError("INVALID_OCI_DESCRIPTOR")
    name = "blobs/sha256/" + digest.split(":")[1]
    if (
        name not in blobs
        or type(descriptor.get("size")) is not int
        or descriptor["size"] != blobs[name]["size"]
    ):
        raise ValueError("OCI_DESCRIPTOR_SIZE_MISMATCH")
    return name
