"""Verify the candidate Jenkinsfile locally without publishing an unreviewed source branch."""

from argparse import ArgumentParser
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from json import dumps, loads
from pathlib import Path
from re import fullmatch
from tarfile import TarFile
from time import monotonic, sleep
from urllib.parse import urlencode
from urllib.request import Request
from xml.etree.ElementTree import Element, SubElement, tostring
from zipfile import ZipFile

from bootstrap import BASE_URL, ROOT, Jenkins, admin_password
from defusedxml.ElementTree import fromstring
from image_archive import inspect_image_archive


def post(client: Jenkins, path: str, body: bytes, content_type: str) -> bytes:
    """Send an authenticated local POST with a session-bound crumb."""
    crumb = loads(client.request("/crumbIssuer/api/json"))
    return client.request(
        path,
        data=body,
        headers={crumb["crumbRequestField"]: crumb["crumb"], "Content-Type": content_type},
    )


def job_xml(script: str, description: str) -> bytes:
    """Create only a sandboxed manual review job; no credentials or triggers are installed."""
    root = Element("flow-definition")
    SubElement(root, "description").text = description
    SubElement(root, "keepDependencies").text = "false"
    SubElement(root, "properties")
    definition = SubElement(
        root, "definition", {"class": "org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition"}
    )
    SubElement(definition, "script").text = script
    SubElement(definition, "sandbox").text = "true"
    SubElement(root, "triggers")
    SubElement(root, "disabled").text = "false"
    return tostring(root, encoding="utf-8")


def run_build(client: Jenkins, job_path: str) -> int:
    """Follow this invocation's queue item, not a racy lastBuild/nextBuildNumber guess."""
    crumb = loads(client.request("/crumbIssuer/api/json"))
    request = Request(
        BASE_URL + job_path + "build",
        data=b"",
        headers={"Authorization": client.authorization, crumb["crumbRequestField"]: crumb["crumb"]},
    )
    with client.opener.open(request, timeout=10) as response:
        location = response.headers["Location"]
    if not location.startswith(BASE_URL + "/queue/item/"):
        raise RuntimeError("Unexpected queue origin; refusing authenticated follow-up")
    queue_path = location.removeprefix(BASE_URL)
    if not fullmatch(r"/queue/item/[0-9]+/", queue_path):
        raise RuntimeError("Unexpected queue path")
    deadline = monotonic() + 1200
    number = None
    while monotonic() < deadline:
        item = loads(client.request(queue_path + "api/json"))
        if item.get("cancelled"):
            raise RuntimeError("Review build was cancelled")
        if "executable" in item:
            number = item["executable"]["number"]
            break
        sleep(2)
    if number is not None:
        while monotonic() < deadline:
            result = loads(client.request(f"{job_path}{number}/api/json"))
            if not result["building"]:
                return number
            sleep(2)
    raise TimeoutError("Review build timed out; inspect/cancel the owned queue/build explicitly")


def require_passing_tests(report: dict, expected_tests: int) -> int:
    """JUnit's testReport API exposes pass/fail/skip counts, not totalCount."""
    counts = [report.get(key) for key in ["passCount", "failCount", "skipCount"]]
    if any(type(value) is not int or value < 0 for value in counts):
        raise RuntimeError("JUnit API returned missing or invalid counts")
    total = sum(counts)
    if total != expected_tests or report["failCount"] or report["skipCount"]:
        raise RuntimeError("Published JUnit result does not match the expected passing suite")
    return total


SECURITY_ARTIFACTS = {
    "reports/" + name
    for name in (
        "security-summary.json",
        "security-tools.txt",
        "security-export.txt",
        "runtime-requirements.txt",
        "bandit.json",
        "bandit.txt",
        "pip-audit.json",
        "pip-audit.txt",
    )
}


def require_security_reports(output: Path, artifacts: set[str], skipped: bool) -> dict | None:
    """Require a complete passing gate, or no scan outputs after an earlier test failure."""
    if skipped:
        if SECURITY_ARTIFACTS.intersection(artifacts):
            raise RuntimeError("Security scans ran after the injected test failure")
        return None
    if not SECURITY_ARTIFACTS.issubset(artifacts):
        raise RuntimeError("Security scan artifacts are missing")
    report = loads((output / "reports/security-summary.json").read_text(encoding="utf-8"))
    if report.get("status") != "passed" or any(
        report.get(tool, {}).get("status") != "passed"
        or type(report[tool].get("blocking_findings")) is not int
        or report[tool]["blocking_findings"] != 0
        for tool in ("bandit", "dependencies")
    ):
        raise RuntimeError("Security gate is not a complete passing result")
    metadata = (output / "reports/build-metadata.txt").read_text(encoding="utf-8")
    if report.get("lock_sha256", "missing") + "  uv.lock" not in metadata.splitlines():
        raise RuntimeError("Scanned lock does not match the build metadata")
    return report


IMAGE_SECURITY_ARTIFACTS = {
    "reports/" + name
    for name in (
        "image-security-summary.json",
        "image-security-tools.txt",
        "image-security-export.txt",
        "image-runtime-requirements.txt",
        "trivy-db.json",
        "trivy-db.txt",
        "trivy.json",
        "trivy.txt",
    )
}


def require_image_security_reports(
    output: Path, artifacts: set[str], skipped: bool, revision: str
) -> dict | None:
    """Bind a complete passing image gate to its downloaded reports, archive and source."""
    if skipped:
        if IMAGE_SECURITY_ARTIFACTS.intersection(artifacts):
            raise RuntimeError("Image security ran after an earlier failed stage")
        return None
    if not IMAGE_SECURITY_ARTIFACTS.issubset(artifacts):
        raise RuntimeError("Image security reports are missing")
    report = loads((output / "reports/image-security-summary.json").read_text())
    if (
        report.get("status") != "passed"
        or report.get("source_revision") != revision
        or type(report.get("blocking_findings")) is not int
        or report["blocking_findings"] != 0
        or report.get("end_of_life") is not False
        or report.get("temporary_cache_removed") is not True
    ):
        raise RuntimeError("Image security gate is not a complete pass for this source")
    checksums = report.get("report_sha256")
    names = {name.removeprefix("reports/") for name in IMAGE_SECURITY_ARTIFACTS}
    names.remove("image-security-summary.json")
    if not isinstance(checksums, dict) or set(checksums) != names:
        raise RuntimeError("Image security report checksum inventory is incomplete")
    for name, digest in checksums.items():
        if sha256((output / "reports" / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError("Image security report checksum mismatch")
    archive = output / "images/finsecure-pay.tar.gz"
    if not archive.is_file() or sha256(archive.read_bytes()).hexdigest() != report.get(
        "archive_sha256"
    ):
        raise RuntimeError("Image scan does not match the archived image")
    metadata = (output / "reports/build-metadata.txt").read_text()
    if report.get("lock_sha256", "missing") + "  uv.lock" not in metadata.splitlines():
        raise RuntimeError("Image scan lock differs from the build")
    raw = loads((output / "reports/trivy.json").read_text())
    if raw.get("Metadata", {}).get("ImageID") != report.get("image_id"):
        raise RuntimeError("Image scan/report identity mismatch")
    return report


def verify(
    source_revision: str,
    expected_tests: int,
    fail_after_tests: bool,
    existing_job: str | None = None,
) -> dict:
    """Run the exact candidate (or one explicitly altered failure probe) against reviewed Git."""
    if not fullmatch(r"[a-f0-9]{40}", source_revision) or expected_tests <= 0:
        raise ValueError("A full source Git SHA and positive expected test count are required")
    candidate = (ROOT / "Jenkinsfile").read_text(encoding="utf-8")
    candidate_hash = sha256(candidate.encode()).hexdigest()
    script = candidate
    if fail_after_tests:
        command = "./scripts/test.sh 2>&1 | tee reports/tests.txt\n"
        if script.count(command) != 1:
            raise RuntimeError("Failure probe no longer matches the reviewed test command")
        script = script.replace(command, command + "exit 37 # isolated post-test failure probe\n")
    # Only this review wrapper supplies scm. Production receives it from Pipeline-from-SCM.
    prefix = (
        "def scm = [$class: 'GitSCM', branches: [[name: '" + source_revision + "']], "
        "userRemoteConfigs: [[url: 'https://github.com/yuenshingyan/"
        "nussoc-devops-and-cloud-with-ai-capstone.git']], "
        "extensions: [[$class: 'CloneOption', timeout: 2]]]\n"
    )
    script = prefix + script
    expects_image = "stage('Local image export')" in candidate
    expects_security = "stage('Security scans')" in candidate
    expects_image_security = "stage('Image security gate')" in candidate
    mode = "failure" if fail_after_tests else "success"
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    job_name = existing_job or f"finsecure-ci-review-{mode}-{stamp}"
    if not fullmatch(r"finsecure-ci-review-" + mode + r"-[0-9]{14}", job_name):
        raise ValueError("Only a matching owned review-job name may be inspected")
    job_path = "/job/" + job_name + "/"
    password = admin_password()
    client = Jenkins(password)
    secret = (
        fromstring(client.request("/computer/finsecure-python/jenkins-agent.jnlp"))
        .find(".//argument")
        .text
    )
    sensitive = [
        password,
        secret,
        client.authorization,
        client.authorization.removeprefix("Basic "),
    ]
    description = (
        f"Owned local pipeline review; candidate {candidate_hash}; source {source_revision}; "
        f"mode {mode}. No release stages."
    )
    if existing_job:
        config = fromstring(client.request(job_path + "config.xml"))
        if config.findtext("definition/script") != script:
            raise RuntimeError("Existing job does not match this candidate and source revision")
        builds = loads(client.request(job_path + "api/json"))["builds"]
        if len(builds) != 1 or builds[0]["number"] != 1:
            raise RuntimeError("Expected exactly one existing review build")
    else:
        post(
            client,
            "/createItem?" + urlencode({"name": job_name}),
            job_xml(script, description),
            "application/xml",
        )
    print("Inspecting" if existing_job else "Created", "local review job:", job_name, flush=True)
    try:
        number = 1 if existing_job else run_build(client, job_path)
        build_path = job_path + str(number) + "/"
        build = loads(client.request(build_path + "api/json"))
        console = client.request(build_path + "consoleText").decode()
        for value in sensitive:
            if value:
                console = console.replace(value, "<redacted>")
        output = ROOT / "reports" / job_name
        output.mkdir(parents=True, exist_ok=True)
        (output / "console.txt").write_text(console, encoding="utf-8")
        expected_result = "FAILURE" if fail_after_tests else "SUCCESS"
        if build["result"] != expected_result:
            raise RuntimeError("Unexpected review result; inspect its sanitized console report")
        if (
            "SOURCE_REVISION=" + source_revision not in console
            or "Running on finsecure-python" not in console
        ):
            raise RuntimeError("Source revision or agent identity was not confirmed")
        if fail_after_tests and "script returned exit code 37" not in console:
            raise RuntimeError("Failure was not the intended isolated post-test probe")
        artifacts = {}
        allowed = {
            "reports/build-metadata.txt",
            "reports/dependencies.txt",
            "reports/lint.txt",
            "reports/format.txt",
            "reports/tests.txt",
            "reports/junit.xml",
            "reports/coverage.xml",
            "reports/package.txt",
            "reports/packages.sha256",
        }
        image_files = {
            "images/finsecure-pay.tar.gz",
            "reports/buildkit-workers.txt",
            "reports/image-metadata.txt",
            "reports/image-build.txt",
            "reports/buildkit-image.json",
            "reports/image.sha256",
        }
        if expects_image:
            allowed.update(image_files)
        if expects_security:
            allowed.update(SECURITY_ARTIFACTS)
        if expects_image_security:
            allowed.update(IMAGE_SECURITY_ARTIFACTS)
        for artifact in build["artifacts"]:
            name = artifact["relativePath"]
            package = fullmatch(r"dist/finsecure_pay-[A-Za-z0-9_.+-]+\.(whl|tar\.gz)", name)
            if name not in allowed and not package:
                raise RuntimeError("Unexpected archived artifact outside the allowlist")
            content = client.request(build_path + "artifact/" + name)
            if any(value and value.encode() in content for value in sensitive):
                raise RuntimeError("Live credential found in an artifact; refusing to save it")
            target = output / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            artifacts[name] = {"bytes": len(content), "sha256": sha256(content).hexdigest()}
        security = (
            require_security_reports(output, set(artifacts), fail_after_tests)
            if expects_security
            else None
        )
        image_security = (
            require_image_security_reports(
                output, set(artifacts), fail_after_tests, source_revision
            )
            if expects_image_security
            else None
        )
        tests = loads(client.request(build_path + "testReport/api/json"))
        total = require_passing_tests(tests, expected_tests)
        coverage = loads(client.request(build_path + "coverage/api/json"))
        (output / "junit-api.json").write_text(dumps(tests, indent=2) + "\n")
        (output / "coverage-api.json").write_text(dumps(coverage, indent=2) + "\n")
        xml = fromstring((output / "reports/coverage.xml").read_bytes())
        if (
            coverage["projectStatistics"].get("loc") != xml.attrib["lines-valid"]
            or coverage["qualityGates"]["overallResult"] != "INACTIVE"
        ):
            raise RuntimeError("Coverage UI disagrees with the report or has unexpected gates")
        packages = [name for name in artifacts if name.startswith("dist/")]
        if fail_after_tests:
            if packages or "reports/packages.sha256" in artifacts:
                raise RuntimeError("Packages were created after the injected test-stage failure")
        else:
            if len(packages) != 2:
                raise RuntimeError("Expected one wheel and one source distribution")
            checksums = {}
            for line in (output / "reports/packages.sha256").read_text().splitlines():
                digest, name = line.split("  ", 1)
                if name in checksums:
                    raise RuntimeError("Duplicate package checksum entry")
                checksums[name] = digest
            if checksums != {name: artifacts[name]["sha256"] for name in packages}:
                raise RuntimeError("Downloaded package checksum mismatch")
            wheel = next(name for name in packages if name.endswith(".whl"))
            source = next(name for name in packages if name.endswith(".tar.gz"))
            with ZipFile(output / wheel) as archive:
                assert "finsecure_pay/main.py" in archive.namelist()
            with TarFile.open(
                fileobj=BytesIO((output / source).read_bytes()), mode="r:gz"
            ) as archive:
                assert any(
                    name.endswith("/src/finsecure_pay/main.py") for name in archive.getnames()
                )
        image = None
        if expects_image:
            if fail_after_tests:
                if image_files.intersection(artifacts):
                    raise RuntimeError("Image export ran after the injected test-stage failure")
            else:
                if not image_files.issubset(artifacts):
                    raise RuntimeError("Missing image export artifacts")
                archive_name = "images/finsecure-pay.tar.gz"
                expected_checksum = artifacts[archive_name]["sha256"] + "  " + archive_name + "\n"
                if (output / "reports/image.sha256").read_text() != expected_checksum:
                    raise RuntimeError("Downloaded image archive checksum mismatch")
                tag = f"finsecure-pay-ci:jenkins-{job_name}-{number}"
                expected_metadata = (
                    f"SOURCE_REVISION={source_revision}\nLOCAL_TAG={tag}\nPLATFORM=linux/arm64\n"
                )
                if (output / "reports/image-metadata.txt").read_text() != expected_metadata:
                    raise RuntimeError("Image export provenance does not match this build")
                metadata = loads((output / "reports/buildkit-image.json").read_bytes())
                image = inspect_image_archive(
                    output / archive_name,
                    source_revision,
                    tag,
                    metadata["containerimage.config.digest"],
                )
        record = {
            "verified_at_utc": datetime.now(UTC).isoformat(),
            "job": job_name,
            "build": number,
            "result": build["result"],
            "source_revision": source_revision,
            "candidate_jenkinsfile_sha256": candidate_hash,
            "executed_script_sha256": sha256(script.encode()).hexdigest(),
            "review_mode": mode,
            "pipeline_from_scm_verified": False,
            "test_count": total,
            "coverage_ui": coverage["projectStatistics"],
            "test_failures": tests["failCount"],
            "coverage_xml": {
                key: xml.attrib[key]
                for key in ["lines-covered", "lines-valid", "branches-covered", "branches-valid"]
            },
            "artifacts": artifacts,
            "image_export": image,
            "security_scans": security,
            "image_security": image_security,
        }
        (output / "verification.json").write_text(dumps(record, indent=2) + "\n")
        return record
    finally:
        # Preserve review history, but prevent accidental later rebuilds of inline candidates.
        config = fromstring(client.request(job_path + "config.xml"))
        disabled = config.find("disabled")
        if disabled is None:
            disabled = SubElement(config, "disabled")
        disabled.text = "true"
        post(client, job_path + "config.xml", tostring(config), "application/xml")


def main() -> None:
    """Create one owned review job; do not publish source, images, or cloud resources."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--expected-tests", required=True, type=int)
    parser.add_argument("--fail-after-tests", action="store_true")
    parser.add_argument(
        "--existing-job", help="Inspect one matching completed review build without rerunning it"
    )
    arguments = parser.parse_args()
    print(
        dumps(
            verify(
                arguments.source_revision,
                arguments.expected_tests,
                arguments.fail_after_tests,
                arguments.existing_job,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
