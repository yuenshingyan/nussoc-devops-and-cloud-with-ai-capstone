from hashlib import sha256
from json import dumps
from pathlib import Path
from time import monotonic

from pytest import fixture, mark, raises

from scripts.release_command import CommandResult
from scripts.release_publication import check_inputs, publication_preflight, push_prepared
from scripts.release_registry import CONFIG_TYPE, LAYER_TYPE, MANIFEST_TYPE, readback_image

REVISION = "a" * 40


@fixture
def inputs(tmp_path: Path) -> tuple[Path, str, Path, Path, bytes, bytes, str, str]:
    parent = tmp_path.resolve()
    parent.chmod(0o700)
    tar = parent / "image.tar"
    tar.write_bytes(b"synthetic tar; native format validation is mocked at the process boundary")
    tar.chmod(0o600)
    checksum = sha256(tar.read_bytes()).hexdigest()
    key = parent / "binding"
    key.write_text("synthetic-not-a-provider-credential")
    key.chmod(0o600)
    config = dumps(
        {
            "architecture": "amd64",
            "os": "linux",
            "config": {
                "User": "10001:10001",
                "Labels": {"org.opencontainers.image.revision": REVISION},
            },
            "rootfs": {"type": "layers", "diff_ids": ["sha256:" + "b" * 64]},
        }
    ).encode()
    image_id = "sha256:" + sha256(config).hexdigest()
    manifest = dumps(
        {
            "schemaVersion": 2,
            "mediaType": MANIFEST_TYPE,
            "config": {"mediaType": CONFIG_TYPE, "size": len(config), "digest": image_id},
            "layers": [{"mediaType": LAYER_TYPE, "size": 128, "digest": "sha256:" + "c" * 64}],
        }
    ).encode()
    digest = "sha256:" + sha256(manifest).hexdigest()
    return tar, checksum, key, parent, config, manifest, image_id, digest


def test_preflight_never_pushes_and_does_not_reset_budget(inputs, monkeypatch):
    tar, checksum, key, parent, _, _, _, digest = inputs
    calls = []
    outputs = iter([b"", (digest + "\n").encode(), b"0.3.0\nlatest\n"])
    deadline = monotonic() + 30

    def command(argv: list[str], environment: dict[str, str], budget: float) -> CommandResult:
        calls.append((argv, environment, budget))
        return CommandResult(0, next(outputs))

    monkeypatch.setitem(publication_preflight.__globals__, "run_command", command)
    assert publication_preflight(tar, checksum, REVISION, key, parent, {}, deadline) == digest
    assert [call[0][1] for call in calls] == ["validate", "digest", "ls"]
    assert "--fast" not in calls[0][0]
    assert calls[-1][0][-1] == "docker.io/yuenshingyan/finsecure-pay"
    assert all(call[2] == deadline for call in calls)
    assert all(not Path(call[1]["DOCKER_CONFIG"]).exists() for call in calls)
    assert key.exists() and tar.exists()


@mark.parametrize(
    "listing",
    [
        b"\n",
        b"tag",
        b"tag\r\n",
        b"tag\ntag\n",
        b"bad tag\n",
        b"x" * 129 + b"\n",
        ("sha-" + REVISION + "-amd64\n").encode(),
    ],
)
def test_preflight_rejects_invalid_listing_or_existing_target(inputs, monkeypatch, listing):
    tar, checksum, key, parent, _, _, _, digest = inputs
    outputs = iter([b"", (digest + "\n").encode(), listing])

    def command(argv: list[str], environment: dict[str, str], budget: float) -> CommandResult:
        return CommandResult(0, next(outputs))

    monkeypatch.setitem(publication_preflight.__globals__, "run_command", command)
    with raises(ValueError, match="PUBLICATION_TAG_"):
        publication_preflight(tar, checksum, REVISION, key, parent, {}, monotonic() + 30)
    assert sorted(path.name for path in parent.iterdir()) == ["binding", "image.tar"]


@mark.parametrize("stage", [0, 1, 2])
def test_preflight_nonzero_exit_stops_without_relaunch(inputs, monkeypatch, stage):
    tar, checksum, key, parent, _, _, _, digest = inputs
    calls = []

    def command(argv: list[str], environment: dict[str, str], budget: float) -> CommandResult:
        index = len(calls)
        calls.append(argv)
        return CommandResult(
            1 if index == stage else 0, (digest + "\n").encode() if index == 1 else b""
        )

    monkeypatch.setitem(publication_preflight.__globals__, "run_command", command)
    with raises(ValueError, match="PUBLICATION_"):
        publication_preflight(tar, checksum, REVISION, key, parent, {}, monotonic() + 30)
    assert len(calls) == stage + 1


def test_push_ignores_untrusted_success_output_and_requires_actual_readback_logic(
    inputs, monkeypatch
):
    tar, checksum, key, parent, config, manifest, image_id, digest = inputs
    calls = []
    outputs = iter([b"untrusted push success claim", (digest + "\n").encode(), manifest, config])
    deadline = monotonic() + 30

    def command(argv: list[str], environment: dict[str, str], budget: float) -> CommandResult:
        calls.append((argv, budget))
        return CommandResult(0, next(outputs))

    monkeypatch.setitem(push_prepared.__globals__, "run_command", command)
    monkeypatch.setitem(readback_image.__globals__, "run_command", command)
    result = push_prepared(tar, checksum, REVISION, digest, image_id, key, parent, {}, deadline)
    assert [call[0][1] for call in calls] == ["push", "digest", "manifest", "config"]
    assert all(call[1] == deadline for call in calls)
    assert calls[0][0][-1] == "docker.io/yuenshingyan/finsecure-pay:sha-" + REVISION + "-amd64"
    assert result["registry_manifest_digest"] == digest
    assert result["publishing_authorized"] is False
    assert sorted(path.name for path in parent.iterdir()) == ["binding", "image.tar"]


@mark.parametrize("failure", ["exit", "timeout"])
def test_uncertain_push_stops_without_readback_relaunch_or_rollback(inputs, monkeypatch, failure):
    tar, checksum, key, parent, _, _, image_id, digest = inputs
    calls = []

    def command(argv: list[str], environment: dict[str, str], budget: float) -> CommandResult:
        calls.append(argv)
        if failure == "timeout":
            raise TimeoutError("RELEASE_COMMAND_TIMEOUT_OUTCOME_UNKNOWN")
        return CommandResult(1, b"untrusted provider detail")

    monkeypatch.setitem(push_prepared.__globals__, "run_command", command)
    with raises((ValueError, TimeoutError), match="OUTCOME_UNKNOWN"):
        push_prepared(tar, checksum, REVISION, digest, image_id, key, parent, {}, monotonic() + 30)
    assert len(calls) == 1
    assert sorted(path.name for path in parent.iterdir()) == ["binding", "image.tar"]


def test_successful_push_followed_by_failed_readback_does_not_repush_or_delete(inputs, monkeypatch):
    tar, checksum, key, parent, _, _, image_id, digest = inputs
    calls = []

    def command(argv: list[str], environment: dict[str, str], budget: float) -> CommandResult:
        calls.append(argv)
        return CommandResult(0, b"not trusted as registry proof")

    monkeypatch.setitem(push_prepared.__globals__, "run_command", command)
    monkeypatch.setitem(readback_image.__globals__, "run_command", command)
    with raises(ValueError, match="REGISTRY_TAG_IDENTITY_MISMATCH"):
        push_prepared(tar, checksum, REVISION, digest, image_id, key, parent, {}, monotonic() + 30)
    assert [call[1] for call in calls] == ["push", "digest"]
    assert sorted(path.name for path in parent.iterdir()) == ["binding", "image.tar"]


def test_changed_tar_is_rejected_before_any_command(inputs, monkeypatch):
    tar, checksum, key, parent, _, _, image_id, digest = inputs
    tar.write_bytes(b"changed")

    def command(argv: list[str], environment: dict[str, str], budget: float) -> CommandResult:
        raise AssertionError("No command may run")

    monkeypatch.setitem(push_prepared.__globals__, "run_command", command)
    with raises(ValueError, match="TAR_CHANGED"):
        push_prepared(tar, checksum, REVISION, digest, image_id, key, parent, {}, monotonic() + 30)


@mark.parametrize("deadline", [True, 0.0, float("inf"), float("nan")])
def test_invalid_budget_is_rejected(inputs, deadline):
    tar, checksum, *_ = inputs
    with raises(ValueError, match="BUDGET_INVALID"):
        check_inputs(tar, checksum, REVISION, deadline)
