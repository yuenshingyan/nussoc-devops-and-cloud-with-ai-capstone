from base64 import b64decode
from copy import deepcopy
from hashlib import sha256
from json import dumps, loads
from os import link
from pathlib import Path
from stat import S_IMODE
from time import monotonic

from pytest import fixture, mark, raises

from scripts.release_command import CommandResult
from scripts.release_registry import (
    AUTHORITY,
    CONFIG_TYPE,
    LAYER_TYPE,
    MANIFEST_TYPE,
    USERNAME,
    config_readback,
    manifest_readback,
    private_token,
    readback_image,
    registry_profile,
)

TOKEN = "synthetic-token-not-valid-at-any-provider"
REVISION = "a" * 40


@fixture
def binding(tmp_path: Path) -> tuple[Path, Path]:
    parent = tmp_path.resolve()
    parent.chmod(0o700)
    key = parent / "bound-file"
    key.write_text(TOKEN)
    key.chmod(0o600)
    return key, parent


def test_profile_is_private_scoped_and_preserves_only_process_cookies(binding):
    key, parent = binding
    inherited = {
        "JENKINS_NODE_COOKIE": "synthetic-node-cookie",
        "JENKINS_SERVER_COOKIE": "synthetic-server-cookie",
        "HTTP_PROXY": "http://invalid.example",
        "DOCKER_CONFIG": "/not-the-reviewed-profile",
        "DOCKER_AUTH_CONFIG": "unreviewed",
        "GOOGLE_APPLICATION_CREDENTIALS": "/not-the-deployer",
        "SSL_CERT_FILE": "/unreviewed-cert",
        "PATH": "/unreviewed-bin",
    }
    with registry_profile(key, parent, inherited) as environment:
        profile = Path(environment["DOCKER_CONFIG"])
        assert profile.parent == parent
        assert S_IMODE(profile.stat().st_mode) == 0o700
        config = profile / "config.json"
        assert S_IMODE(config.stat().st_mode) == 0o600
        data = loads(config.read_text())
        assert set(data) == {"auths"}
        assert set(data["auths"]) == {AUTHORITY}
        assert b64decode(data["auths"][AUTHORITY]["auth"]).decode() == USERNAME + ":" + TOKEN
        assert set(environment) == {
            "HOME",
            "DOCKER_CONFIG",
            "TMPDIR",
            "PATH",
            "JENKINS_NODE_COOKIE",
            "JENKINS_SERVER_COOKIE",
        }
        assert environment["HOME"] == environment["TMPDIR"] == str(profile)
        assert environment["PATH"] == "/usr/local/bin:/usr/bin:/bin"
        assert environment["JENKINS_NODE_COOKIE"] == inherited["JENKINS_NODE_COOKIE"]
        assert environment["JENKINS_SERVER_COOKIE"] == inherited["JENKINS_SERVER_COOKIE"]
        assert all(TOKEN not in value for value in environment.values())
    assert not profile.exists()
    assert key.read_text() == TOKEN


def test_profile_is_removed_when_operation_fails(binding):
    key, parent = binding
    with raises(RuntimeError, match="synthetic failure"):
        with registry_profile(key, parent, {}) as environment:
            profile = Path(environment["HOME"])
            raise RuntimeError("synthetic failure")
    assert not profile.exists()
    assert key.exists()


def test_secret_in_inherited_environment_is_rejected_before_profile_creation(binding):
    key, parent = binding
    with raises(ValueError, match="SECRET_IN_ENVIRONMENT"):
        with registry_profile(key, parent, {"UNRELATED": "prefix" + TOKEN}):
            raise AssertionError("Profile must not be yielded")
    assert list(parent.iterdir()) == [key]


@mark.parametrize(
    "value", [b"", b"a" * 4097, b"trailing\n", b"bad token", b"bad\x00token", b"\xff"]
)
def test_token_is_never_trimmed_or_coerced(binding, value):
    key, _ = binding
    key.write_bytes(value)
    with raises(ValueError, match="^REGISTRY_CREDENTIAL_INVALID$"):
        private_token(key)


@mark.parametrize("environment", [None, [], {"key": 1}, {1: "value"}])
def test_profile_rejects_invalid_environment(binding, environment):
    key, parent = binding
    with raises(ValueError, match="ENVIRONMENT_INVALID"):
        with registry_profile(key, parent, environment):
            raise AssertionError("Profile must not be yielded")
    assert list(parent.iterdir()) == [key]


def test_profile_parent_must_be_private(binding):
    key, parent = binding
    parent.chmod(0o755)
    with raises(ValueError, match="DIRECTORY_INVALID"):
        with registry_profile(key, parent, {}):
            raise AssertionError("Profile must not be yielded")


def test_maximum_token_length_is_accepted(binding):
    key, _ = binding
    key.write_text("t" * 4096)
    assert private_token(key) == "t" * 4096


@mark.parametrize("mode", [0o644, 0o660, 0o777])
def test_credential_must_be_private(binding, mode):
    key, _ = binding
    key.chmod(mode)
    with raises(ValueError, match="CREDENTIAL_INVALID"):
        private_token(key)


@mark.parametrize("kind", ["symlink", "hardlink"])
def test_credential_links_are_rejected(binding, kind):
    key, parent = binding
    other = parent / "linked"
    if kind == "symlink":
        other.symlink_to(key)
    else:
        link(key, other)
    with raises(ValueError, match="CREDENTIAL_INVALID"):
        private_token(other)


@fixture
def documents() -> tuple[bytes, dict]:
    config = {
        "architecture": "amd64",
        "os": "linux",
        "config": {
            "User": "10001:10001",
            "Labels": {"org.opencontainers.image.revision": REVISION},
        },
        "rootfs": {"type": "layers", "diff_ids": ["sha256:" + "b" * 64]},
    }
    body = dumps(config).encode()
    manifest = {
        "schemaVersion": 2,
        "mediaType": MANIFEST_TYPE,
        "config": {
            "mediaType": CONFIG_TYPE,
            "size": len(body),
            "digest": "sha256:" + sha256(body).hexdigest(),
        },
        "layers": [{"mediaType": LAYER_TYPE, "size": 128, "digest": "sha256:" + "c" * 64}],
    }
    return body, manifest


def check_manifest(manifest: dict, image_id: str | None = None) -> dict:
    body = dumps(manifest).encode()
    digest = "sha256:" + sha256(body).hexdigest()
    return manifest_readback(body, digest, digest, image_id or manifest["config"]["digest"])


def test_exact_readback_accepts_independently_supplied_identities(documents):
    config, manifest = documents
    original = deepcopy(manifest)
    parsed = check_manifest(manifest)
    assert parsed == manifest
    assert config_readback(config, parsed, manifest["config"]["digest"], REVISION) is None
    assert manifest == original


@mark.parametrize("which", ["body", "reported", "expected", "config"])
def test_manifest_rejects_identity_mismatch(documents, which):
    _, manifest = documents
    body = dumps(manifest).encode()
    digest = "sha256:" + sha256(body).hexdigest()
    with raises(ValueError, match="MISMATCH"):
        manifest_readback(
            body + b" " if which == "body" else body,
            "sha256:" + "f" * 64 if which == "reported" else digest,
            "sha256:" + "e" * 64 if which == "expected" else digest,
            "sha256:" + "d" * 64 if which == "config" else manifest["config"]["digest"],
        )


@mark.parametrize(
    "change",
    [
        "version",
        "media",
        "extra",
        "zero_layers",
        "excess_layers",
        "urls",
        "bool_size",
        "negative_size",
        "foreign",
        "bad_digest",
    ],
)
def test_manifest_rejects_malformed_shape_even_in_synthetic_matching_hash_fixture(
    documents, change
):
    _, manifest = documents
    if change == "version":
        manifest["schemaVersion"] = True
    elif change == "media":
        manifest["mediaType"] = "application/vnd.oci.image.index.v1+json"
    elif change == "extra":
        manifest["unexpected"] = True
    elif change == "zero_layers":
        manifest["layers"] = []
    elif change == "excess_layers":
        manifest["layers"] *= 65
    elif change == "urls":
        manifest["layers"][0]["urls"] = ["https://invalid.example"]
    elif change == "bool_size":
        manifest["layers"][0]["size"] = True
    elif change == "negative_size":
        manifest["layers"][0]["size"] = -1
    elif change == "foreign":
        manifest["layers"][0]["mediaType"] = "foreign"
    else:
        manifest["layers"][0]["digest"] = "sha256:" + "C" * 64
    with raises(ValueError, match="REGISTRY_"):
        check_manifest(manifest)


@mark.parametrize("body", [b'{"key":1,"key":2}', b'{"value":NaN}', b"{} trailing", b"\xff"])
def test_manifest_json_is_strict(body):
    digest = "sha256:" + sha256(body).hexdigest()
    with raises(ValueError, match="JSON_INVALID"):
        manifest_readback(body, digest, digest, "sha256:" + "a" * 64)


@mark.parametrize("change", ["bytes", "size", "architecture", "os", "user", "revision", "diff_ids"])
def test_config_readback_rejects_wrong_identity_or_runtime(documents, change):
    body, manifest = documents
    config = loads(body)
    if change == "bytes":
        body += b" "
    elif change == "size":
        manifest["config"]["size"] = True
    else:
        if change == "architecture":
            config["architecture"] = "arm64"
        elif change == "os":
            config["os"] = "windows"
        elif change == "user":
            config["config"]["User"] = "0:0"
        elif change == "revision":
            config["config"]["Labels"]["org.opencontainers.image.revision"] = "f" * 40
        else:
            config["rootfs"]["diff_ids"] = []
        body = dumps(config).encode()
        manifest["config"]["size"] = len(body)
        manifest["config"]["digest"] = "sha256:" + sha256(body).hexdigest()
    with raises(ValueError, match="REGISTRY_CONFIG_"):
        config_readback(body, manifest, manifest["config"]["digest"], REVISION)


def test_readback_uses_fixed_tag_then_pinned_reference_and_shared_deadline(
    binding, documents, monkeypatch
):
    key, parent = binding
    config, manifest = documents
    body = dumps(manifest).encode()
    digest = "sha256:" + sha256(body).hexdigest()
    deadline = monotonic() + 30
    calls = []
    outputs = iter([(digest + "\n").encode(), body, config])

    def command(argv: list[str], environment: dict[str, str], budget: float) -> CommandResult:
        calls.append((argv, environment, budget))
        assert Path(environment["DOCKER_CONFIG"], "config.json").is_file()
        return CommandResult(0, next(outputs))

    monkeypatch.setitem(readback_image.__globals__, "run_command", command)
    result = readback_image(
        key, parent, {}, REVISION, digest, manifest["config"]["digest"], deadline
    )
    assert result["status"] == "verified"
    assert result["publishing_authorized"] is False
    assert [call[0] for call in calls] == [
        [
            "/usr/local/bin/crane",
            "digest",
            "docker.io/yuenshingyan/finsecure-pay:sha-" + REVISION + "-amd64",
        ],
        ["/usr/local/bin/crane", "manifest", "docker.io/yuenshingyan/finsecure-pay@" + digest],
        ["/usr/local/bin/crane", "config", "docker.io/yuenshingyan/finsecure-pay@" + digest],
    ]
    assert all(call[2] == deadline for call in calls)
    assert all(not Path(call[1]["DOCKER_CONFIG"]).exists() for call in calls)
    assert key.read_text() == TOKEN


@mark.parametrize("stage", [0, 1, 2])
@mark.parametrize("failure", ["exit", "bytes", "timeout"])
def test_readback_failure_stops_without_command_relaunch_and_cleans_profile(
    binding, documents, monkeypatch, stage, failure
):
    key, parent = binding
    config, manifest = documents
    body = dumps(manifest).encode()
    digest = "sha256:" + sha256(body).hexdigest()
    calls = []
    outputs = [(digest + "\n").encode(), body, config]

    def command(argv: list[str], environment: dict[str, str], budget: float) -> CommandResult:
        index = len(calls)
        calls.append((argv, environment))
        if index == stage:
            if failure == "timeout":
                raise TimeoutError("RELEASE_COMMAND_TIMEOUT_OUTCOME_UNKNOWN")
            return CommandResult(1 if failure == "exit" else 0, TOKEN.encode())
        return CommandResult(0, outputs[index])

    monkeypatch.setitem(readback_image.__globals__, "run_command", command)
    with raises((ValueError, TimeoutError)) as caught:
        readback_image(
            key, parent, {}, REVISION, digest, manifest["config"]["digest"], monotonic() + 30
        )
    assert TOKEN not in str(caught.value)
    assert len(calls) == stage + 1
    assert all(not Path(call[1]["DOCKER_CONFIG"]).exists() for call in calls)
    assert list(parent.iterdir()) == [key]


@mark.parametrize("deadline", [True, 0.0, float("inf"), float("nan")])
def test_readback_rejects_invalid_budget_before_profile_creation(binding, documents, deadline):
    key, parent = binding
    _, manifest = documents
    with raises(ValueError, match="BUDGET_INVALID"):
        readback_image(
            key, parent, {}, REVISION, "sha256:" + "a" * 64, manifest["config"]["digest"], deadline
        )
    assert list(parent.iterdir()) == [key]


@mark.parametrize("change", ["duplicate", "total", "config_size", "layer_size"])
def test_manifest_enforces_existing_archive_bounds(documents, change):
    _, manifest = documents
    if change == "duplicate":
        manifest["layers"] *= 2
    elif change == "total":
        manifest["layers"][0]["size"] = 64 * 1024 * 1024
    elif change == "config_size":
        manifest["config"]["size"] = 1024 * 1024 + 1
    else:
        manifest["layers"][0]["size"] = 64 * 1024 * 1024 + 1
    with raises(ValueError, match="REGISTRY_"):
        check_manifest(manifest)


@mark.parametrize("body", [b"", b"x" * (1024 * 1024 + 1)])
def test_manifest_rejects_empty_or_oversized_response_before_json_parsing(body):
    digest = "sha256:" + sha256(body).hexdigest()
    with raises(ValueError, match="SIZE_INVALID"):
        manifest_readback(body, digest, digest, "sha256:" + "a" * 64)


def test_readback_does_not_accept_an_arbitrary_repository_in_revision(binding, documents):
    key, parent = binding
    _, manifest = documents
    with raises(ValueError, match="EXPECTED_IDENTITY_INVALID"):
        readback_image(
            key,
            parent,
            {},
            "untrusted.example/image",
            "sha256:" + "a" * 64,
            manifest["config"]["digest"],
            monotonic() + 30,
        )
    assert list(parent.iterdir()) == [key]
