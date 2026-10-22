"""Regression checks for the standalone CLI; Docker and entropy are external boundaries."""

from collections.abc import Iterator
from io import BytesIO
from os import umask
from pathlib import Path
from runpy import run_path
from subprocess import CompletedProcess
from typing import Any
from unittest.mock import Mock
from urllib.error import HTTPError
from urllib.request import Request

from pytest import MonkeyPatch, fixture, raises


@fixture
def bootstrap_helpers(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> Iterator[tuple[dict[str, Any], Mock, Path]]:
    monkeypatch.setenv("HOME", str(tmp_path))
    docker = Mock(return_value=CompletedProcess([], 1, "", "no such volume"))
    monkeypatch.setattr("subprocess.run", docker)
    monkeypatch.setattr("secrets.token_urlsafe", Mock(return_value="x" * 43))
    monkeypatch.setattr("time.sleep", Mock())
    previous_umask = umask(0o077)
    try:
        helpers = run_path(str(Path(__file__).resolve().parents[2] / "ops/jenkins/bootstrap.py"))
        yield helpers, docker, tmp_path / ".config/finsecure-pay/jenkins/admin-password"
    finally:
        umask(previous_umask)


def test_verification_does_not_create_a_missing_password(bootstrap_helpers):
    helpers, docker, password_file = bootstrap_helpers
    with raises(RuntimeError, match="password is missing"):
        helpers["admin_password"]()
    assert not password_file.exists()
    docker.assert_not_called()


def test_bootstrap_refuses_to_replace_existing_volume_credentials(bootstrap_helpers):
    helpers, docker, password_file = bootstrap_helpers
    docker.return_value = CompletedProcess([], 0, "[]", "")
    with raises(RuntimeError, match="recover the password privately"):
        helpers["admin_password"](create=True)
    assert not password_file.exists()
    assert docker.call_count == 1


def test_fresh_bootstrap_creates_a_private_password(bootstrap_helpers):
    helpers, docker, password_file = bootstrap_helpers
    assert helpers["admin_password"](create=True) == "x" * 43
    assert password_file.read_text() == "x" * 43
    assert password_file.stat().st_mode & 0o777 == 0o600
    assert password_file.parent.stat().st_mode & 0o777 == 0o700
    assert docker.call_count == 1


def test_existing_private_password_is_preserved(bootstrap_helpers):
    helpers, docker, password_file = bootstrap_helpers
    password_file.parent.mkdir(parents=True, mode=0o700)
    password_file.write_text("s" * 43)
    assert helpers["admin_password"](create=True) == "s" * 43
    assert password_file.read_text() == "s" * 43
    docker.assert_not_called()


def test_readable_by_others_password_is_rejected(bootstrap_helpers):
    helpers, _, password_file = bootstrap_helpers
    password_file.parent.mkdir(parents=True, mode=0o700)
    password_file.write_text("s" * 43)
    password_file.chmod(0o644)
    with raises(RuntimeError, match="password file must be private"):
        helpers["admin_password"]()


def test_password_symlink_is_rejected(bootstrap_helpers):
    helpers, _, password_file = bootstrap_helpers
    password_file.parent.mkdir(parents=True, mode=0o700)
    target = password_file.parent / "synthetic-target"
    target.write_text("s" * 43)
    password_file.symlink_to(target)
    with raises(RuntimeError, match="not a symlink"):
        helpers["admin_password"]()
    assert target.read_text() == "s" * 43


def test_unrelated_data_volume_is_not_reconfigured(bootstrap_helpers):
    helpers, docker, password_file = bootstrap_helpers
    docker.return_value = CompletedProcess([], 0, '[{"Labels": {}}]', "")
    with raises(RuntimeError, match="expected project label"):
        helpers["start"]()
    assert not password_file.exists()
    assert docker.call_count == 1


def test_existing_controller_home_requires_credential_recovery(bootstrap_helpers):
    helpers, docker, password_file = bootstrap_helpers
    docker.return_value = CompletedProcess(
        [], 0, '[{"Labels": {"com.docker.compose.project": "finsecure-jenkins"}}]', ""
    )
    with raises(RuntimeError, match="password is missing"):
        helpers["start"]()
    assert not password_file.exists()
    assert docker.call_count == 2


def test_docker_inspection_failure_does_not_create_a_password(bootstrap_helpers):
    helpers, docker, password_file = bootstrap_helpers
    docker.return_value = CompletedProcess([], 1, "", "Cannot connect to the Docker daemon")
    with raises(RuntimeError, match="Unable to check"):
        helpers["admin_password"](create=True)
    assert not password_file.exists()


def test_startup_waits_for_user_and_api_initialization(bootstrap_helpers, monkeypatch):
    helpers, docker, _ = bootstrap_helpers
    docker.side_effect = [CompletedProcess([], 0, "owned-container", "")] + [
        CompletedProcess([], 0, "true", "")
    ] * 4
    client = helpers["Jenkins"]("synthetic-password")
    responses = [
        HTTPError("http://127.0.0.1:8080/api/json", code, "Not ready", {}, None)
        for code in [401, 403, 500]
    ] + [BytesIO(b'{"numExecutors": 0}')]
    monkeypatch.setattr(client.opener, "open", Mock(side_effect=responses))
    assert client.wait("/api/json", "numExecutors", 0, 5, "controller") == {"numExecutors": 0}


def test_authenticated_redirect_is_not_followed(bootstrap_helpers):
    helpers, _, _ = bootstrap_helpers
    response = BytesIO(b"synthetic redirect body")
    with raises(RuntimeError, match="credentials were not forwarded"):
        helpers["NoRedirect"]().redirect_request(
            Request("http://127.0.0.1:8080/"),
            response,
            302,
            "Found",
            {},
            "https://example.invalid/",
        )
    assert response.closed
