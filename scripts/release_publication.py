"""Fixed-repository publication primitives for trusted, independently verified release inputs."""

from hashlib import sha256
from math import isfinite
from os import fstat, getuid
from pathlib import Path
from re import fullmatch
from stat import S_IMODE, S_ISREG
from time import monotonic

from scripts.release_command import run_command
from scripts.release_input import check_deadline, private_directory
from scripts.release_registry import (
    REPOSITORY,
    digest_string,
    readback_image,
    registry_profile,
    require,
)


def check_inputs(tar: Path, expected_sha256: str, revision: str, deadline: float) -> None:
    """Rehash the exact prepared tar; its expected hash must come from verified preparation."""
    require(
        type(deadline) is float and isfinite(deadline) and 0 < deadline - monotonic() <= 600,
        "PUBLICATION_BUDGET_INVALID",
    )
    require(
        type(expected_sha256) is str
        and fullmatch(r"[a-f0-9]{64}", expected_sha256) is not None
        and type(revision) is str
        and fullmatch(r"[a-f0-9]{40}", revision) is not None,
        "PUBLICATION_IDENTITY_INVALID",
    )
    private_directory(tar.parent)
    require(tar.is_absolute() and tar.resolve() == tar, "PUBLICATION_TAR_INVALID")
    info = tar.lstat()
    require(
        S_ISREG(info.st_mode)
        and S_IMODE(info.st_mode) in {0o400, 0o600}
        and info.st_uid == getuid()
        and info.st_nlink == 1
        and 0 < info.st_size <= 64 * 1024 * 1024,
        "PUBLICATION_TAR_INVALID",
    )
    checksum = sha256()
    with tar.open("rb") as source:
        require(fstat(source.fileno()) == info, "PUBLICATION_TAR_CHANGED")
        count = 0
        while data := source.read(65536):
            check_deadline(deadline)
            count += len(data)
            require(count <= info.st_size, "PUBLICATION_TAR_CHANGED")
            checksum.update(data)
        final = fstat(source.fileno())
    require(
        count == info.st_size
        and (final.st_size, final.st_mtime_ns, final.st_ctime_ns)
        == (info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        and checksum.hexdigest() == expected_sha256,
        "PUBLICATION_TAR_CHANGED",
    )
    check_deadline(deadline)


def publication_preflight(
    tar: Path,
    expected_sha256: str,
    revision: str,
    bound_file: Path,
    parent: Path,
    inherited_environment: dict[str, str],
    deadline: float,
) -> str:
    """Validate local bytes and observe tag absence; never authorize a subsequent write.

    The controller must already have verified the archive/config/revision binding, and
    must recheck the original candidate after this preflight, immediately before invoking
    push_prepared. A tag listing is not an atomic create-if-absent reservation.
    """
    check_inputs(tar, expected_sha256, revision, deadline)
    # Full artifact verification precedes credential binding in the controller workflow.
    # Crane only reads the reviewed tar here; it does not execute its application image.
    with registry_profile(bound_file, parent, inherited_environment) as environment:
        validation = run_command(
            ["/usr/local/bin/crane", "validate", "--tarball", str(tar)], environment, deadline
        )
        require(validation.returncode == 0, "PUBLICATION_LOCAL_VALIDATION_FAILED")
        local = run_command(
            ["/usr/local/bin/crane", "digest", "--tarball", str(tar)], environment, deadline
        )
        require(
            local.returncode == 0
            and fullmatch(rb"sha256:[a-f0-9]{64}\n", local.stdout) is not None,
            "PUBLICATION_LOCAL_DIGEST_FAILED",
        )
        listing = run_command(["/usr/local/bin/crane", "ls", REPOSITORY], environment, deadline)
        require(listing.returncode == 0, "PUBLICATION_TAG_LIST_FAILED")
        require(
            not listing.stdout or listing.stdout.endswith(b"\n"),
            "PUBLICATION_TAG_LIST_INVALID",
        )
        tags = listing.stdout.split(b"\n")[:-1] if listing.stdout else []
        require(
            all(fullmatch(rb"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", tag) for tag in tags)
            and len(set(tags)) == len(tags),
            "PUBLICATION_TAG_LIST_INVALID",
        )
        require(
            ("sha-" + revision + "-amd64").encode() not in tags,
            "PUBLICATION_TAG_ALREADY_EXISTS_INSPECT_MANUALLY",
        )
    check_inputs(tar, expected_sha256, revision, deadline)
    return local.stdout[:-1].decode("ascii")


def push_prepared(
    tar: Path,
    expected_sha256: str,
    revision: str,
    expected_local_digest: str,
    expected_image_id: str,
    bound_file: Path,
    parent: Path,
    inherited_environment: dict[str, str],
    deadline: float,
) -> dict:
    """Push once after trusted controller preflight/recheck; inspect any uncertain outcome.

    This is a mutation primitive, not an authorization API. Call only from the reviewed
    fixed Pipeline after independent verification, successful preflight and an action-time
    recheck. It does not enforce registry-side tag immutability against other writers.
    No shell retry/relaunch, deletion, retagging or automatic rollback is performed.
    """
    require(
        digest_string(expected_local_digest) and digest_string(expected_image_id),
        "PUBLICATION_IDENTITY_INVALID",
    )
    check_inputs(tar, expected_sha256, revision, deadline)
    tag = REPOSITORY + ":sha-" + revision + "-amd64"
    with registry_profile(bound_file, parent, inherited_environment) as environment:
        result = run_command(["/usr/local/bin/crane", "push", str(tar), tag], environment, deadline)
        require(result.returncode == 0, "PUBLICATION_PUSH_FAILED_OUTCOME_UNKNOWN_INSPECT_MANUALLY")
    # Even successful push output is not registry proof. Never deploy before readback passes.
    return readback_image(
        bound_file,
        parent,
        inherited_environment,
        revision,
        expected_local_digest,
        expected_image_id,
        deadline,
    )
