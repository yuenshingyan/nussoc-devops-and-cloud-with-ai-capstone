"""Create the fixed, disabled verification Pipeline; never enable, approve or run it."""

from argparse import ArgumentParser
from hashlib import sha256
from html import escape
from json import dumps

from bootstrap import BASE_URL, admin_password
from defusedxml.ElementTree import fromstring
from httpx2 import BasicAuth, Client
from release_definition import assemble_definition
from release_store import DESCRIPTION
from verify_release import check_policy

JOB = "/job/finsecure-release/job/delivery"
JOB_DESCRIPTION = "Owned FinSecure delivery selection; publishing and deployment disabled."


def job_xml(script: str) -> str:
    """Serialize fixed code with no parameters/triggers and serialized, disabled execution."""
    return (
        "<flow-definition><description>" + JOB_DESCRIPTION + "</description>"
        "<keepDependencies>false</keepDependencies><properties>"
        "<org.jenkinsci.plugins.workflow.job.properties.DisableConcurrentBuildsJobProperty/>"
        "<org.jenkinsci.plugins.workflow.job.properties.DisableResumeJobProperty/>"
        '</properties><definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition">'
        "<script>" + escape(script) + "</script><sandbox>false</sandbox></definition>"
        "<triggers/><disabled>true</disabled></flow-definition>"
    )


def verify_definition(content: bytes, script: str, *, resume_disabled: bool = True) -> None:
    """Match fixed source; the explicit legacy profile is only for older read-only checkpoints."""
    if type(resume_disabled) is not bool:
        raise ValueError("RELEASE_RESUME_PROFILE_INVALID")
    root = fromstring(content)
    definition = root.find("definition")
    properties = root.find("properties")
    triggers = root.find("triggers")
    serial_name = "org.jenkinsci.plugins.workflow.job.properties.DisableConcurrentBuildsJobProperty"
    trigger_name = "org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty"
    resume_name = "org.jenkinsci.plugins.workflow.job.properties.DisableResumeJobProperty"
    allowed = (
        {serial_name, trigger_name, resume_name} if resume_disabled else {serial_name, trigger_name}
    )
    resume = properties.find(resume_name) if properties is not None else None
    serial = properties.find(serial_name) if properties is not None else None
    scheduled = properties.find(trigger_name) if properties is not None else None
    if (
        root.tag != "flow-definition"
        or root.findtext("description") != JOB_DESCRIPTION
        or root.findtext("disabled") != "true"
        or definition is None
        or definition.get("class") != "org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition"
        or definition.findtext("sandbox") != "false"
        or definition.findtext("script") != script
        or properties is None
        or len({item.tag for item in properties}) != len(properties)
        or any(item.tag not in allowed for item in properties)
        or (resume_disabled and (resume is None or len(resume) != 0))
        or serial is None
        or serial.findtext("abortPrevious") not in {None, "false"}
        or (triggers is not None and len(triggers) != 0)
        or (
            scheduled is not None
            and (scheduled.find("triggers") is None or len(scheduled.find("triggers")) != 0)
        )
    ):
        raise ValueError("RELEASE_JOB_DEFINITION_MISMATCH")


def create_disabled_job(client: Client, script: str) -> dict:
    """Create once in the existing owned folder; stop on ambiguous responses, without retries."""
    check_policy(client)
    folder = client.get(BASE_URL + "/job/finsecure-release/api/json")
    folder.raise_for_status()
    if folder.json().get("description") != DESCRIPTION:
        raise ValueError("RELEASE_FOLDER_NOT_OWNED")
    existing = client.get(BASE_URL + JOB + "/api/json")
    if existing.status_code != 404:
        raise ValueError("RELEASE_JOB_EXISTS_OR_UNCERTAIN")
    crumb_response = client.get(BASE_URL + "/crumbIssuer/api/json")
    crumb_response.raise_for_status()
    crumb = crumb_response.json()
    response = client.post(
        BASE_URL + "/job/finsecure-release/createItem",
        params={"name": "delivery"},
        content=job_xml(script),
        headers={crumb["crumbRequestField"]: crumb["crumb"], "Content-Type": "application/xml"},
    )
    if response.status_code not in {200, 201, 302}:
        raise RuntimeError("RELEASE_JOB_CREATION_UNCERTAIN")
    installed = client.get(BASE_URL + JOB + "/config.xml")
    installed.raise_for_status()
    verify_definition(installed.content, script)
    return {
        "job": "finsecure-release/delivery",
        "disabled": True,
        "sandbox": False,
        "serialized": True,
        "resume_disabled": True,
        "triggers": [],
        "script_sha256": sha256(script.encode("utf-8")).hexdigest(),
        "publishing_implemented": False,
        "deployment_implemented": False,
    }


def main() -> None:
    """Require explicit consent; keep script approval and worker startup out of this helper."""
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--approve-disabled-release-job", action="store_true")
    if not parser.parse_args().approve_disabled_release_job:
        parser.error("Explicit approval for the disabled non-sandboxed definition is required")
    script = assemble_definition()
    with Client(
        auth=BasicAuth("admin", admin_password()),
        timeout=20,
        trust_env=False,
        follow_redirects=False,
    ) as client:
        print(dumps(create_disabled_job(client, script), indent=2))


if __name__ == "__main__":
    main()
