"""Observe real SCM-triggered demo builds; never push Git, trigger, or retry a build."""

from argparse import ArgumentParser
from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
from json import dumps, loads
from re import fullmatch
from time import monotonic, sleep
from xml.etree.ElementTree import Element, SubElement, tostring

from bootstrap import ROOT, Jenkins, admin_password
from defusedxml.ElementTree import fromstring
from image_archive import inspect_image_archive

DEMO_JOB = "finsecure-ci-gate-demo"
DEMO_BRANCH = "demo/step-04-04-ci-gate"
JOB_PATH = "/job/" + DEMO_JOB + "/"
REPOSITORY = "https://github.com/yuenshingyan/nussoc-devops-and-cloud-with-ai-capstone.git"
SCM_CAUSE = "hudson.triggers.SCMTrigger$SCMTriggerCause"


def demo_job_xml(normal_config: bytes) -> bytes:
    """Copy only the trusted SCM definition into a manual seed job, without credentials."""
    definition = fromstring(normal_config).find("definition")
    if definition is None or definition.get("class") != (
        "org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition"
    ):
        raise RuntimeError("Expected a Pipeline-from-SCM definition")
    urls = definition.findall(".//userRemoteConfigs/hudson.plugins.git.UserRemoteConfig/url")
    branches = definition.findall(".//branches/hudson.plugins.git.BranchSpec/name")
    if (
        len(urls) != 1
        or urls[0].text != REPOSITORY
        or len(branches) != 1
        or branches[0].text != "*/main"
        or definition.findtext("scriptPath") != "Jenkinsfile"
        or any(item.text for item in definition.findall(".//credentialsId"))
    ):
        raise RuntimeError("Unexpected SCM source, script, or credentials")
    root = Element("flow-definition")
    SubElement(root, "description").text = (
        "Owned Step 4.4 trusted-branch gate demonstration. Manual seed, then SCM polling. "
        "No registry/cloud credentials or delivery. Never merge demo history into main."
    )
    SubElement(root, "properties")
    copied = deepcopy(definition)
    copied.find(".//branches/hudson.plugins.git.BranchSpec/name").text = "*/" + DEMO_BRANCH
    root.append(copied)
    SubElement(root, "disabled").text = "false"
    return tostring(root, encoding="utf-8")


def require_scm_cause(build: dict) -> list[dict]:
    """Reject manual, timer-only, mixed, or absent causes as automatic-SCM evidence."""
    causes = [cause for action in build.get("actions", []) for cause in action.get("causes", [])]
    if not causes or any(cause.get("_class") != SCM_CAUSE for cause in causes):
        raise RuntimeError("Build was not exclusively triggered by an SCM change")
    return causes


def require_test_counts(report: dict, passed: int, failed: int) -> None:
    """Require exact, non-coerced JUnit counts, with no skipped tests."""
    counts = [report.get(key) for key in ["passCount", "failCount", "skipCount"]]
    if any(type(value) is not int or value < 0 for value in counts):
        raise RuntimeError("JUnit counts are missing or invalid")
    if counts != [passed, failed, 0]:
        raise RuntimeError("JUnit counts do not match the controlled demonstration")


def inspect_build(
    client: Jenkins, number: int, revision: str, passed: int, failed: int, *, automatic: bool
) -> dict:
    """Check source/cause, real pytest results, downstream artifacts, and image identity."""
    base = JOB_PATH + str(number) + "/"
    build = loads(client.request(base + "api/json"))
    if build["building"] or build["result"] != ("FAILURE" if failed else "SUCCESS"):
        raise RuntimeError("Build has not completed with the expected result")
    causes = (
        require_scm_cause(build)
        if automatic
        else [cause for action in build["actions"] for cause in action.get("causes", [])]
    )
    secret = (
        fromstring(client.request("/computer/finsecure-python/jenkins-agent.jnlp"))
        .find(".//argument")
        .text
    )
    sensitive = [admin_password(), secret, client.authorization, client.authorization[6:]]
    console = client.request(base + "consoleText").decode()
    for value in sensitive:
        console = console.replace(value, "<redacted>")
    out = ROOT / "reports" / f"step44-demo-{number}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "console.txt").write_text(console, encoding="utf-8")
    if (
        "Obtained Jenkinsfile from git" not in console
        or "SOURCE_REVISION=" + revision not in console
        or "Running on finsecure-python" not in console
    ):
        raise RuntimeError("SCM-loaded script, exact checkout, or agent not confirmed")
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
        "reports/buildkit-workers.txt",
        "reports/image-metadata.txt",
        "reports/image-build.txt",
        "reports/buildkit-image.json",
        "reports/image.sha256",
        "images/finsecure-pay.tar.gz",
        "dist/finsecure_pay-0.2.0-py3-none-any.whl",
        "dist/finsecure_pay-0.2.0.tar.gz",
    }
    artifacts = {}
    for artifact in build["artifacts"]:
        name = artifact["relativePath"]
        if name not in allowed:
            raise RuntimeError("Unexpected artifact path")
        content = client.request(base + "artifact/" + name)
        if any(value.encode() in content for value in sensitive):
            raise RuntimeError("Live credential in artifact; refusing to save")
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        artifacts[name] = {"bytes": len(content), "sha256": sha256(content).hexdigest()}
    tests = loads(client.request(base + "testReport/api/json"))
    require_test_counts(tests, passed, failed)
    coverage = loads(client.request(base + "coverage/api/json"))
    report = fromstring((out / "reports/coverage.xml").read_bytes())
    if report.attrib["lines-covered"] != "125" or report.attrib["branches-covered"] != "28":
        raise RuntimeError("Unexpected application coverage")
    image = None
    if failed:
        expected = {
            "reports/" + name
            for name in [
                "build-metadata.txt",
                "dependencies.txt",
                "lint.txt",
                "format.txt",
                "tests.txt",
                "junit.xml",
                "coverage.xml",
            ]
        }
        if set(artifacts) != expected:
            raise RuntimeError("Failure did not block package/image stages cleanly")
        junit = fromstring((out / "reports/junit.xml").read_bytes())
        failures = [case for case in junit.iter("testcase") if case.find("failure") is not None]
        if len(failures) != 1 or failures[0].get("name") != "test_ci_demo_health_contract":
            raise RuntimeError("Failure was not the isolated real pytest case")
        if "script returned exit code 1" not in console:
            raise RuntimeError("Expected pytest failure exit status")
        for stage in ["Package", "Local image export"]:
            if f'Stage "{stage}" skipped due to earlier failure(s)' not in console:
                raise RuntimeError("Downstream stage skip was not confirmed")
    else:
        if set(artifacts) != allowed:
            raise RuntimeError("Successful build is missing expected artifacts")
        for manifest, prefix in [("packages.sha256", "dist/"), ("image.sha256", "images/")]:
            actual = {}
            for line in (out / "reports" / manifest).read_text().splitlines():
                digest, name = line.split("  ", 1)
                if name in actual:
                    raise RuntimeError("Duplicate checksum entry")
                actual[name] = digest
            if actual != {
                name: data["sha256"] for name, data in artifacts.items() if name.startswith(prefix)
            }:
                raise RuntimeError("Downloaded artifact checksum mismatch")
        metadata = loads((out / "reports/buildkit-image.json").read_bytes())
        image = inspect_image_archive(
            out / "images/finsecure-pay.tar.gz",
            revision,
            f"finsecure-pay-ci:jenkins-{DEMO_JOB}-{number}",
            metadata["containerimage.config.digest"],
        )
    (out / "junit-api-summary.json").write_text(
        dumps(
            {
                key: tests[key]
                for key in [
                    "passCount",
                    "failCount",
                    "skipCount",
                    "duration",
                    "empty",
                ]
            },
            indent=2,
        )
        + "\n"
    )
    (out / "coverage-api.json").write_text(dumps(coverage, indent=2) + "\n")
    record = {
        "verified_at_utc": datetime.now(UTC).isoformat(),
        "job": DEMO_JOB,
        "build": number,
        "source_revision": revision,
        "result": build["result"],
        "causes": causes,
        "scm_trigger_verified": automatic,
        "pipeline_from_scm_verified": True,
        "passed": passed,
        "failed": failed,
        "skipped": 0,
        "artifacts": artifacts,
        "image_export": image,
        "publishing_or_deployment": "not implemented",
    }
    (out / "verification.json").write_text(dumps(record, indent=2) + "\n")
    return record


def observe(revision: str, after_build: int, passed: int, failed: int) -> dict:
    """Wait up to 20 minutes for the next SCM build; GET only, no poll/build endpoints."""
    if (
        not fullmatch(r"[a-f0-9]{40}", revision)
        or after_build < 1
        or passed < 1
        or failed not in {0, 1}
    ):
        raise ValueError("Expected a full revision, prior seed build, and controlled test counts")
    client = Jenkins(admin_password())
    deadline = monotonic() + 1200
    while monotonic() < deadline:
        builds = loads(client.request(JOB_PATH + "api/json"))["builds"]
        candidates = [build for build in builds if build["number"] > after_build]
        if len(candidates) > 1:
            raise RuntimeError(
                "Unexpected extra builds; inspect rather than selecting a passing retry"
            )
        if candidates:
            number = candidates[0]["number"]
            if not loads(client.request(JOB_PATH + str(number) + "/api/json"))["building"]:
                return inspect_build(client, number, revision, passed, failed, automatic=True)
        sleep(3)
    raise TimeoutError("SCM observation timed out; inspect queue/build and restore the demo branch")


def main() -> None:
    """Observe the fixed owned demo job without causing source changes or builds."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--after-build", type=int, required=True)
    parser.add_argument("--passed", type=int, required=True)
    parser.add_argument("--failed", type=int, choices=[0, 1], default=0)
    arguments = parser.parse_args()
    print(
        dumps(
            observe(arguments.revision, arguments.after_build, arguments.passed, arguments.failed),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
