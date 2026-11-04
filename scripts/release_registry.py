"""Private Docker Hub client profiles and strict readback checks; no upload or authorization."""

from base64 import b64encode
from collections.abc import Iterator
from contextlib import contextmanager
from hashlib import sha256
from json import dumps
from math import isfinite
from os import fchmod, fstat, getuid
from pathlib import Path
from re import fullmatch
from stat import S_IMODE, S_ISREG
from tempfile import TemporaryDirectory
from time import monotonic

from scripts.release_archive import strict_json
from scripts.release_command import run_command
from scripts.release_credentials import validate_token
from scripts.release_input import private_directory

REPOSITORY = "docker.io/yuenshingyan/finsecure-pay"
AUTHORITY = "https://index.docker.io/v1/"
USERNAME = "yuenshingyan"
MANIFEST_TYPE = "application/vnd.docker.distribution.manifest.v2+json"
CONFIG_TYPE = "application/vnd.docker.container.image.v1+json"
LAYER_TYPE = "application/vnd.docker.image.rootfs.diff.tar.gzip"
COOKIES = ("JENKINS_NODE_COOKIE", "JENKINS_SERVER_COOKIE")
JSON_LIMIT = 1024 * 1024


def require(allowed: bool, code: str) -> None:
    """Raise fixed error codes without disclosing provider or credential content."""
    if not allowed:
        raise ValueError(code)


def private_token(path: Path) -> str:
    """Read only a canonical owned private binding; never trim or expose its value."""
    try:
        require(path.is_absolute() and path.resolve() == path, "REGISTRY_CREDENTIAL_INVALID")
        info = path.lstat()
        require(
            S_ISREG(info.st_mode)
            and S_IMODE(info.st_mode) in {0o400, 0o600}
            and info.st_uid == getuid()
            and info.st_nlink == 1
            and 0 < info.st_size <= 4096,
            "REGISTRY_CREDENTIAL_INVALID",
        )
        with path.open("rb") as stream:
            require(fstat(stream.fileno()) == info, "REGISTRY_CREDENTIAL_INVALID")
            raw = stream.read(4097)
            final = fstat(stream.fileno())
            require(
                len(raw) == info.st_size
                and (final.st_size, final.st_mtime_ns, final.st_ctime_ns)
                == (info.st_size, info.st_mtime_ns, info.st_ctime_ns),
                "REGISTRY_CREDENTIAL_INVALID",
            )
        token = raw.decode("ascii")
        validate_token(token)
    except OSError, ValueError:
        raise ValueError("REGISTRY_CREDENTIAL_INVALID") from None
    return token


@contextmanager
def registry_profile(
    bound_file: Path, parent: Path, inherited_environment: dict[str, str]
) -> Iterator[dict[str, str]]:
    """Own a short-lived private profile, not the borrowed Jenkins-bound credential.

    Only Jenkins process-tree cookies survive from the inherited environment. Proxy,
    cloud-auth, alternate Docker config/helper and certificate overrides are not inherited.
    Callers must never log profile contents or unvalidated command stdout. Cleanup failure
    is a release failure and requires operator inspection, not another publish attempt.
    """
    private_directory(parent)
    require(
        type(inherited_environment) is dict
        and all(
            type(key) is str and type(value) is str for key, value in inherited_environment.items()
        ),
        "REGISTRY_ENVIRONMENT_INVALID",
    )
    token = private_token(bound_file)
    require(
        not any(token in value for value in inherited_environment.values()),
        "REGISTRY_SECRET_IN_ENVIRONMENT",
    )
    with TemporaryDirectory(dir=parent, prefix="registry-") as temporary:
        directory = Path(temporary)
        directory.chmod(0o700)
        config = {
            "auths": {AUTHORITY: {"auth": b64encode((USERNAME + ":" + token).encode()).decode()}}
        }
        with (directory / "config.json").open("x", encoding="utf-8") as output:
            fchmod(output.fileno(), 0o600)
            output.write(dumps(config))
        environment = {
            key: inherited_environment[key] for key in COOKIES if key in inherited_environment
        }
        environment.update(
            HOME=str(directory),
            DOCKER_CONFIG=str(directory),
            TMPDIR=str(directory),
            PATH="/usr/local/bin:/usr/bin:/bin",
        )
        yield environment


def digest_string(value: object) -> bool:
    """Accept only canonical lowercase SHA-256 image digests without normalization."""
    return type(value) is str and fullmatch(r"sha256:[a-f0-9]{64}", value) is not None


def manifest_readback(
    body: bytes, reported_digest: str, expected_local_digest: str, expected_image_id: str
) -> dict:
    """Bind exact readback bytes to trusted local crane/config identities, not a server claim.

    The caller must obtain bytes/digest from the fixed authenticated registry and must not
    derive expected values from that same response. This function performs no network I/O
    and does not establish tag immutability, origin authentication or release eligibility.
    """
    require(
        digest_string(expected_local_digest) and digest_string(expected_image_id),
        "REGISTRY_EXPECTED_IDENTITY_INVALID",
    )
    require(type(body) is bytes and 0 < len(body) <= JSON_LIMIT, "REGISTRY_MANIFEST_SIZE_INVALID")
    require(
        reported_digest == expected_local_digest
        and "sha256:" + sha256(body).hexdigest() == expected_local_digest,
        "REGISTRY_MANIFEST_IDENTITY_MISMATCH",
    )
    try:
        manifest = strict_json(body)
    except ValueError, UnicodeError, RecursionError:
        raise ValueError("REGISTRY_MANIFEST_JSON_INVALID") from None
    require(
        type(manifest) is dict
        and set(manifest) == {"schemaVersion", "mediaType", "config", "layers"}
        and type(manifest["schemaVersion"]) is int
        and manifest["schemaVersion"] == 2
        and manifest["mediaType"] == MANIFEST_TYPE,
        "REGISTRY_MANIFEST_SCHEMA_INVALID",
    )
    layers = manifest["layers"]
    require(type(layers) is list and 1 <= len(layers) <= 64, "REGISTRY_MANIFEST_LAYERS_INVALID")
    for index, descriptor in enumerate([manifest["config"], *layers]):
        require(
            type(descriptor) is dict
            and set(descriptor) == {"mediaType", "size", "digest"}
            and descriptor["mediaType"] == (CONFIG_TYPE if index == 0 else LAYER_TYPE)
            and type(descriptor["size"]) is int
            and 0 < descriptor["size"] <= (JSON_LIMIT if index == 0 else 64 * 1024 * 1024)
            and digest_string(descriptor["digest"]),
            "REGISTRY_DESCRIPTOR_INVALID",
        )
    require(
        len({item["digest"] for item in layers}) == len(layers),
        "REGISTRY_MANIFEST_DUPLICATE_LAYER",
    )
    require(
        sum(item["size"] for item in [manifest["config"], *layers]) <= 64 * 1024 * 1024,
        "REGISTRY_MANIFEST_TOTAL_SIZE_INVALID",
    )
    require(manifest["config"]["digest"] == expected_image_id, "REGISTRY_CONFIG_IDENTITY_MISMATCH")
    return manifest


def config_readback(body: bytes, manifest: dict, expected_image_id: str, revision: str) -> None:
    """Check config bytes/runtime after manifest_readback succeeds; not a smoke test."""
    require(
        digest_string(expected_image_id)
        and type(revision) is str
        and fullmatch(r"[a-f0-9]{40}", revision) is not None,
        "REGISTRY_EXPECTED_IDENTITY_INVALID",
    )
    require(type(body) is bytes and 0 < len(body) <= JSON_LIMIT, "REGISTRY_CONFIG_SIZE_INVALID")
    require(
        type(manifest) is dict
        and type(manifest.get("config")) is dict
        and manifest["config"].get("digest") == expected_image_id
        and type(manifest["config"].get("size")) is int
        and manifest["config"]["size"] == len(body)
        and type(manifest.get("layers")) is list
        and 1 <= len(manifest["layers"]) <= 64
        and "sha256:" + sha256(body).hexdigest() == expected_image_id,
        "REGISTRY_CONFIG_IDENTITY_MISMATCH",
    )
    try:
        config = strict_json(body)
    except ValueError, UnicodeError, RecursionError:
        raise ValueError("REGISTRY_CONFIG_JSON_INVALID") from None
    require(type(config) is dict, "REGISTRY_CONFIG_SCHEMA_INVALID")
    runtime = config.get("config")
    rootfs = config.get("rootfs")
    require(
        config.get("architecture") == "amd64"
        and config.get("os") == "linux"
        and type(runtime) is dict
        and runtime.get("User") == "10001:10001"
        and type(runtime.get("Labels")) is dict
        and runtime["Labels"].get("org.opencontainers.image.revision") == revision
        and type(rootfs) is dict
        and rootfs.get("type") == "layers"
        and type(rootfs.get("diff_ids")) is list
        and len(rootfs["diff_ids"]) == len(manifest["layers"])
        and all(digest_string(value) for value in rootfs["diff_ids"]),
        "REGISTRY_CONFIG_RUNTIME_MISMATCH",
    )


def readback_image(
    bound_file: Path,
    parent: Path,
    inherited_environment: dict[str, str],
    revision: str,
    expected_local_digest: str,
    expected_image_id: str,
    deadline: float,
) -> dict:
    """Read the fixed SHA tag once, then its pinned manifest/config using one shared budget.

    No upload, command relaunch, arbitrary registry or automatic rollback is supported.
    Pinned crane's internal retries remain permitted inside the caller's remaining budget.
    The tag check is point-in-time, not a claim that registry tags cannot later change.
    """
    require(
        type(revision) is str
        and fullmatch(r"[a-f0-9]{40}", revision) is not None
        and digest_string(expected_local_digest)
        and digest_string(expected_image_id),
        "REGISTRY_EXPECTED_IDENTITY_INVALID",
    )
    require(
        type(deadline) is float and isfinite(deadline) and 0 < deadline - monotonic() <= 600,
        "REGISTRY_BUDGET_INVALID",
    )
    tag = REPOSITORY + ":sha-" + revision + "-amd64"
    reference = REPOSITORY + "@" + expected_local_digest
    with registry_profile(bound_file, parent, inherited_environment) as environment:
        reported = run_command(["/usr/local/bin/crane", "digest", tag], environment, deadline)
        require(reported.returncode == 0, "REGISTRY_DIGEST_COMMAND_FAILED")
        require(
            reported.stdout == (expected_local_digest + "\n").encode("ascii"),
            "REGISTRY_TAG_IDENTITY_MISMATCH",
        )
        response = run_command(
            ["/usr/local/bin/crane", "manifest", reference], environment, deadline
        )
        require(response.returncode == 0, "REGISTRY_MANIFEST_COMMAND_FAILED")
        # Crane v0.22.1 prints these JSON bytes unchanged, unlike its newline-delimited digest.
        manifest = manifest_readback(
            response.stdout, expected_local_digest, expected_local_digest, expected_image_id
        )
        config = run_command(["/usr/local/bin/crane", "config", reference], environment, deadline)
        require(config.returncode == 0, "REGISTRY_CONFIG_COMMAND_FAILED")
        config_readback(config.stdout, manifest, expected_image_id, revision)
    return {
        "status": "verified",
        "reference": reference,
        "tag": tag,
        "registry_manifest_digest": expected_local_digest,
        "image_id": expected_image_id,
        "revision": revision,
        "platform": "linux/amd64",
        "layers": len(manifest["layers"]),
        "publishing_authorized": False,
    }
