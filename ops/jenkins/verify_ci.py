"""Verify the candidate Jenkinsfile locally without publishing an unreviewed source branch."""

from argparse import ArgumentParser
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from json import dumps, loads
from re import fullmatch
from tarfile import TarFile
from time import monotonic, sleep
from urllib.parse import urlencode
from urllib.request import Request
from xml.etree.ElementTree import Element, SubElement, fromstring, tostring
from zipfile import ZipFile

from bootstrap import BASE_URL, ROOT, Jenkins, admin_password


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
        f"Owned Step 4.2 review; candidate {candidate_hash}; source {source_revision}; "
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
