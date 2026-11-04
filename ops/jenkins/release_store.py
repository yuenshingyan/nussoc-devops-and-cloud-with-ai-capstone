"""Import dedicated file credentials into an owned Jenkins folder, never global scope."""

from argparse import ArgumentParser
from hashlib import sha256
from json import dumps, loads
from os import getuid
from pathlib import Path
from runpy import run_path
from stat import S_IMODE, S_ISREG

from bootstrap import BASE_URL, ROOT, admin_password
from httpx2 import BasicAuth, Client

FOLDER = "finsecure-release"
DESCRIPTION = "FinSecure Pay trusted release scope; no untrusted jobs."
PREFIX = "/job/finsecure-release/credentials/store/folder/domain/_"
PROBE_ID = "finsecure-file-import-probe"
FILES = {"finsecure-dockerhub": "dockerhub-ci-token", "finsecure-gke-deployer": "gke-deployer.json"}
# Administrator-only introspection: no secret literals or values are printed by this script.
# Digests are compared privately by the caller, never emitted in the final report.
INSPECT = """
import jenkins.model.Jenkins
import com.cloudbees.plugins.credentials.CredentialsProvider
import org.jenkinsci.plugins.plaincredentials.FileCredentials
import hudson.security.ACL
import java.security.MessageDigest
import groovy.json.JsonOutput
def folder = Jenkins.get().getItemByFullName('finsecure-release')
def source = Jenkins.get().getItemByFullName('finsecure-ci')
assert folder != null && source != null
def ids = ['finsecure-file-import-probe','finsecure-dockerhub','finsecure-gke-deployer']
def scoped = CredentialsProvider.lookupCredentialsInItemGroup(
    FileCredentials.class, folder, ACL.SYSTEM2, [])
def outside = CredentialsProvider.lookupCredentialsInItem(
    FileCredentials.class, source, ACL.SYSTEM2, [])
def files = [:]
scoped.findAll { ids.contains(it.id) }.each { credential ->
    def digest = credential.content.withCloseable { stream ->
        MessageDigest.getInstance('SHA-256').digest(stream.bytes).encodeHex().toString()
    }
    files[credential.id] = [fileName: credential.fileName, sha256: digest]
}
def visible = outside.findAll { ids.contains(it.id) }.collect { it.id }
println JsonOutput.toJson([files:files, source_visible:visible])
"""


class ReleaseStore:
    """Borrow a loopback-only client; do not follow redirects or log response bodies."""

    def __init__(self, client: Client) -> None:
        self.client = client
        response = client.get(BASE_URL + "/crumbIssuer/api/json")
        if response.status_code != 200:
            raise RuntimeError("JENKINS_AUTHENTICATION_FAILED")
        crumb = response.json()
        self.headers = {crumb["crumbRequestField"]: crumb["crumb"]}

    def post(self, path: str, *, headers: dict[str, str] | None = None, **kwargs: object) -> None:
        """Make one local mutation request; ambiguous outcomes require inspection."""
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("INVALID_JENKINS_PATH")
        response = self.client.post(
            BASE_URL + path, headers={**self.headers, **(headers or {})}, **kwargs
        )
        if response.status_code not in {200, 201, 302}:
            raise RuntimeError("JENKINS_STORE_OPERATION_FAILED")

    def ensure_new_folder(self) -> None:
        """Refuse an existing folder rather than taking ownership of its contents."""
        response = self.client.get(BASE_URL + "/job/" + FOLDER + "/api/json")
        if response.status_code != 404:
            raise RuntimeError("FOLDER_EXISTS_OR_CANNOT_BE_CHECKED")
        xml = (
            "<com.cloudbees.hudson.plugins.folder.Folder>"
            "<description>" + DESCRIPTION + "</description><properties/>"
            "</com.cloudbees.hudson.plugins.folder.Folder>"
        )
        self.post(
            "/createItem?name=" + FOLDER,
            content=xml.encode(),
            headers={"Content-Type": "application/xml"},
        )

    def snapshot(self) -> dict:
        """Compare content and provider visibility without exporting credential values."""
        response = self.client.post(
            BASE_URL + "/scriptText", headers=self.headers, data={"script": INSPECT}
        )
        if response.status_code != 200:
            raise RuntimeError("STORE_SCOPE_CHECK_FAILED")
        try:
            value = loads(response.text)
            if not isinstance(value, dict) or value.get("source_visible") != []:
                raise ValueError("Unexpected visibility")
            files = value["files"]
            if not isinstance(files, dict):
                raise ValueError("Unexpected credential metadata")
            return files
        except ValueError, KeyError, TypeError:
            raise RuntimeError("STORE_SCOPE_CHECK_FAILED") from None

    def import_file(self, credential_id: str, filename: str, contents: bytes) -> None:
        """Submit bytes as a multipart file, not embedded Groovy or a process argument."""
        if credential_id not in {PROBE_ID, *FILES} or not 0 < len(contents) <= 16384:
            raise ValueError("INVALID_RELEASE_CREDENTIAL")
        expected_filename = "synthetic.txt" if credential_id == PROBE_ID else FILES[credential_id]
        if filename != expected_filename:
            raise ValueError("INVALID_RELEASE_CREDENTIAL_FILENAME")
        if credential_id in self.snapshot():
            raise RuntimeError("CREDENTIAL_EXISTS_NO_REPLACEMENT")
        payload = {
            "credentials": {
                "scope": "GLOBAL",
                "id": credential_id,
                "description": "Dedicated demo release file; review revocation 19 November",
                "$class": "org.jenkinsci.plugins.plaincredentials.impl.FileCredentialsImpl",
                "stapler-class": "org.jenkinsci.plugins.plaincredentials.impl.FileCredentialsImpl",
                "file": "file0",
            }
        }
        self.post(
            PREFIX + "/createCredentials",
            data={"json": dumps(payload)},
            files={"file0": (filename, contents, "application/octet-stream")},
        )
        result = self.snapshot().get(credential_id)
        if result != {"fileName": filename, "sha256": sha256(contents).hexdigest()}:
            raise RuntimeError("IMPORTED_FILE_CONTENT_OR_SCOPE_MISMATCH")


def private_file(path: Path) -> bytes:
    """Read only a bounded private regular file; no symlink or hardlink credential input."""
    info = path.lstat()
    if (
        not S_ISREG(info.st_mode)
        or S_IMODE(info.st_mode) not in {0o400, 0o600}
        or info.st_uid != getuid()
        or info.st_nlink != 1
        or not 0 < info.st_size <= 16384
    ):
        raise ValueError("UNSAFE_CREDENTIAL_FILE")
    return path.read_bytes()


def main() -> None:
    """Create one owned folder and import files only after a synthetic round-trip test."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--approve-release-store", action="store_true")
    if not parser.parse_args().approve_release_store:
        parser.error("Explicit release credential import approval is required")
    directory = run_path(str(ROOT / "scripts/release_credentials.py"))["private_directory"]()
    values = {key: private_file(directory / name) for key, name in FILES.items()}
    with Client(
        auth=BasicAuth("admin", admin_password()),
        timeout=20,
        trust_env=False,
        follow_redirects=False,
    ) as client:
        store = ReleaseStore(client)
        store.ensure_new_folder()
        if store.snapshot():
            raise RuntimeError("OWNED_CREDENTIAL_IDS_ALREADY_VISIBLE")
        store.import_file(PROBE_ID, "synthetic.txt", b"finsecure-synthetic-file-import-probe")
        store.post(PREFIX + "/credential/" + PROBE_ID + "/doDelete")
        if store.snapshot():
            raise RuntimeError("SYNTHETIC_CREDENTIAL_NOT_REMOVED")
        for credential_id, filename in FILES.items():
            store.import_file(credential_id, filename, values[credential_id])
        if set(store.snapshot()) != set(FILES):
            raise RuntimeError("UNEXPECTED_FINAL_CREDENTIAL_IDS")
    print(
        dumps(
            {
                "folder": FOLDER,
                "file_credentials_imported": sorted(FILES),
                "content_hashes_match_private_sources": True,
                "source_job_credential_lookup_denied": True,
                "synthetic_probe_removed": True,
                "release_jobs_created_or_enabled": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
