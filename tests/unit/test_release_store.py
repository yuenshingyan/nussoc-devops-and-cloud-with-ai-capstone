from hashlib import sha256
from json import loads
from pathlib import Path
from runpy import run_path
from types import SimpleNamespace
from unittest.mock import Mock

from pytest import MonkeyPatch, fixture, mark, raises

ROOT = Path(__file__).resolve().parents[2]


@fixture
def helpers(monkeypatch: MonkeyPatch) -> dict:
    monkeypatch.syspath_prepend(str(ROOT / "ops/jenkins"))
    return run_path(str(ROOT / "ops/jenkins/release_store.py"))


@fixture
def store(helpers: dict) -> tuple:
    client = Mock()
    client.get.return_value = SimpleNamespace(
        status_code=200,
        json=lambda: {"crumbRequestField": "Jenkins-Crumb", "crumb": "synthetic-crumb"},
    )
    client.post.return_value = SimpleNamespace(status_code=302)
    return helpers["ReleaseStore"](client), client


def test_new_folder_uses_xml_and_preserves_crumb(store):
    instance, client = store
    client.get.return_value = SimpleNamespace(status_code=404)
    instance.ensure_new_folder()
    request = client.post.call_args
    assert request.args[0] == "http://127.0.0.1:8080/createItem?name=finsecure-release"
    assert request.kwargs["headers"] == {
        "Jenkins-Crumb": "synthetic-crumb",
        "Content-Type": "application/xml",
    }
    assert b"com.cloudbees.hudson.plugins.folder.Folder" in request.kwargs["content"]


@mark.parametrize("status", [200, 401, 403, 500])
def test_existing_or_unverifiable_folder_is_not_modified(store, status):
    instance, client = store
    client.get.return_value = SimpleNamespace(status_code=status)
    with raises(RuntimeError):
        instance.ensure_new_folder()
    client.post.assert_not_called()


def test_credential_file_uses_multipart_and_folder_store(store):
    instance, client = store
    value = b"synthetic-token"
    instance.snapshot = Mock(
        side_effect=[
            {},
            {
                "finsecure-dockerhub": {
                    "fileName": "dockerhub-ci-token",
                    "sha256": sha256(value).hexdigest(),
                }
            },
        ]
    )
    instance.import_file("finsecure-dockerhub", "dockerhub-ci-token", value)
    request = client.post.call_args
    assert "/job/finsecure-release/credentials/store/folder/" in request.args[0]
    payload = loads(request.kwargs["data"]["json"])
    assert payload["credentials"]["file"] == "file0"
    assert value.decode() not in request.kwargs["data"]["json"]
    assert request.kwargs["files"]["file0"] == (
        "dockerhub-ci-token",
        value,
        "application/octet-stream",
    )


def test_existing_credential_is_never_replaced(store):
    instance, client = store
    instance.snapshot = Mock(return_value={"finsecure-dockerhub": {}})
    with raises(RuntimeError, match="CREDENTIAL_EXISTS"):
        instance.import_file("finsecure-dockerhub", "dockerhub-ci-token", b"synthetic")
    client.post.assert_not_called()


@mark.parametrize(
    ("identifier", "filename", "value"),
    [
        ("unrelated", "key", b"x"),
        ("finsecure-dockerhub", "other", b"x"),
        ("finsecure-dockerhub", "dockerhub-ci-token", b""),
        ("finsecure-dockerhub", "dockerhub-ci-token", b"x" * 16385),
    ],
)
def test_invalid_import_is_rejected_before_network(store, identifier, filename, value):
    instance, client = store
    with raises(ValueError):
        instance.import_file(identifier, filename, value)
    client.post.assert_not_called()


@mark.parametrize(
    "body",
    [
        '{"source_visible":["finsecure-dockerhub"],"files":{}}',
        '{"source_visible":[],"files":[]}',
        "controller error",
    ],
)
def test_scope_or_metadata_failure_does_not_expose_response(store, body):
    instance, client = store
    client.post.return_value = SimpleNamespace(status_code=200, text=body)
    with raises(RuntimeError, match="^STORE_SCOPE_CHECK_FAILED$"):
        instance.snapshot()


def test_import_digest_mismatch_fails_closed(store):
    instance, _ = store
    instance.snapshot = Mock(
        side_effect=[
            {},
            {"finsecure-dockerhub": {"fileName": "dockerhub-ci-token", "sha256": "wrong"}},
        ]
    )
    with raises(RuntimeError, match="CONTENT_OR_SCOPE_MISMATCH"):
        instance.import_file("finsecure-dockerhub", "dockerhub-ci-token", b"synthetic")


@mark.parametrize("mode", [0o644, 0o640, 0o777])
def test_private_file_rejects_exposed_modes(helpers, tmp_path, mode):
    path = tmp_path / "key"
    path.write_bytes(b"synthetic")
    path.chmod(mode)
    with raises(ValueError, match="UNSAFE_CREDENTIAL_FILE"):
        helpers["private_file"](path)
