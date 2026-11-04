"""Prepare bounded Docker tar bytes from a verified gzip archive, without extraction or rebuild."""

from gzip import GzipFile
from hashlib import sha256
from math import isfinite
from os import fchmod, fstat, getuid
from pathlib import Path
from re import fullmatch
from stat import S_IMODE, S_ISDIR, S_ISREG
from time import monotonic
from typing import BinaryIO

LIMIT = 64 * 1024 * 1024
CHUNK = 65536


def require(allowed: bool, code: str) -> None:
    """Raise a fixed safe error, never provider content or private paths."""
    if not allowed:
        raise ValueError(code)


def check_deadline(deadline: float) -> None:
    """Use the caller's worker-local deadline, never a fresh budget per read."""
    if monotonic() >= deadline:
        raise TimeoutError("RELEASE_INPUT_TIMEOUT")


def private_directory(path: Path) -> None:
    """Require canonical private directories owned by this process user."""
    require(path.is_absolute() and path.resolve() == path, "RELEASE_INPUT_DIRECTORY_INVALID")
    info = path.lstat()
    require(
        S_ISDIR(info.st_mode) and S_IMODE(info.st_mode) == 0o700 and info.st_uid == getuid(),
        "RELEASE_INPUT_DIRECTORY_INVALID",
    )


class HashedReader:
    """Borrow the compressed input; count and hash every byte consumed by gzip."""

    def __init__(self, stream: BinaryIO, deadline: float) -> None:
        self.stream = stream
        self.deadline = deadline
        self.count = 0
        self.hash = sha256()

    def read(self, size: int = -1) -> bytes:
        check_deadline(self.deadline)
        maximum = LIMIT - self.count + 1
        size = min(maximum, CHUNK if size < 0 else size)
        data = self.stream.read(size)
        self.count += len(data)
        require(self.count <= LIMIT, "RELEASE_INPUT_COMPRESSED_LIMIT")
        self.hash.update(data)
        return data


def prepare_crane_tar(
    source: Path, directory: Path, expected_archive_sha256: str, deadline: float
) -> dict:
    """Create only directory/image.tar from the exact already-gated compressed artifact.

    Full artifact verification, current-candidate eligibility and release authorization are
    caller responsibilities. This function checks gzip integrity, byte identity and bounds,
    not image policy. It never extracts tar members or executes their contents. The caller
    owns successful output cleanup; newly created partial output is removed on failure.
    """
    require(
        type(expected_archive_sha256) is str
        and fullmatch(r"[a-f0-9]{64}", expected_archive_sha256) is not None,
        "RELEASE_INPUT_DIGEST_INVALID",
    )
    require(type(deadline) is float and isfinite(deadline), "RELEASE_INPUT_BUDGET_INVALID")
    require(0 < deadline - monotonic() <= 600, "RELEASE_INPUT_BUDGET_INVALID")
    private_directory(source.parent)
    private_directory(directory)
    require(source.is_absolute() and source.resolve() == source, "RELEASE_INPUT_SOURCE_INVALID")
    info = source.lstat()
    require(
        S_ISREG(info.st_mode)
        and S_IMODE(info.st_mode) in {0o400, 0o600}
        and info.st_uid == getuid()
        and info.st_nlink == 1
        and 0 < info.st_size <= LIMIT,
        "RELEASE_INPUT_SOURCE_INVALID",
    )
    target = directory / "image.tar"
    created = False
    try:
        with source.open("rb") as raw:
            opened = fstat(raw.fileno())
            require(opened == info, "RELEASE_INPUT_SOURCE_CHANGED")
            reader = HashedReader(raw, deadline)
            output_hash = sha256()
            count = 0
            with target.open("xb") as output:
                created = True
                fchmod(output.fileno(), 0o600)
                with GzipFile(fileobj=reader, mode="rb") as expanded:
                    while data := expanded.read(min(CHUNK, LIMIT - count + 1)):
                        check_deadline(deadline)
                        count += len(data)
                        require(count <= LIMIT, "RELEASE_INPUT_TAR_LIMIT")
                        output.write(data)
                        output_hash.update(data)
                require(count > 0 and reader.count == info.st_size, "RELEASE_INPUT_SIZE_INVALID")
                require(
                    reader.hash.hexdigest() == expected_archive_sha256,
                    "RELEASE_INPUT_HASH_MISMATCH",
                )
                final = fstat(raw.fileno())
                require(
                    (final.st_size, final.st_mtime_ns, final.st_ctime_ns)
                    == (opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns),
                    "RELEASE_INPUT_SOURCE_CHANGED",
                )
                check_deadline(deadline)
        return {
            "status": "prepared",
            "archive_sha256": expected_archive_sha256,
            "tar_sha256": output_hash.hexdigest(),
            "compressed_bytes": reader.count,
            "tar_bytes": count,
            "publishing_authorized": False,
        }
    except BaseException as error:
        if created:
            try:
                target.unlink()
            except OSError:
                # Preserve the primary failure while making incomplete cleanup explicit.
                error.add_note("RELEASE_INPUT_PARTIAL_CLEANUP_FAILED_INSPECT_OWNED_DIRECTORY")
        raise
