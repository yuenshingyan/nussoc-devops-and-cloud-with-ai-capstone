from pathlib import Path

from yaml import safe_load

ROOT = Path(__file__).resolve().parents[2]


def release_service() -> dict:
    return safe_load((ROOT / "ops/jenkins/release.compose.yaml").read_text())["services"][
        "release-agent"
    ]


def test_release_worker_has_only_its_own_workspace_and_remoting_secret():
    service = release_service()
    assert service["volumes"] == [
        "release-workspace:/home/jenkins/agent",
        "release-agent-secrets:/run/secrets:ro",
        "release-temp:/tmp",
    ]
    assert service["command"] == [
        "-url",
        "http://controller:8080/",
        "-name",
        "finsecure-release",
        "-secret",
        "@/run/secrets/agent_secret",
        "-webSocket",
    ]
    assert not service.get("ports") and not service.get("privileged", False)


def test_release_worker_is_read_only_and_resource_bounded():
    service = release_service()
    assert service["read_only"] is True
    assert service["cap_drop"] == ["ALL"]
    assert not service.get("cap_add")
    assert service["security_opt"] == ["no-new-privileges:true"]
    assert service["cpus"] == 0.5
    assert service["mem_limit"] == "512m"
    assert not service.get("tmpfs")
    assert "release-temp:/tmp" in service["volumes"]
    jcasc = safe_load((ROOT / "ops/jenkins/jenkins.yaml").read_text())
    node = next(
        n["permanent"]
        for n in jcasc["jenkins"]["nodes"]
        if n["permanent"]["name"] == "finsecure-release"
    )
    assert "nodeProperties" not in node  # No per-node weakening of disk-space thresholds.


def test_release_credentials_are_not_container_environment_or_mounts():
    service = release_service()
    assert service["environment"] == {
        "JENKINS_JAVA_OPTS": "-Xms32m -Xmx128m",
        "JENKINS_AGENT_WORKDIR": "/home/jenkins/agent",
    }
    assert all("gcloud" not in mount and "docker.sock" not in mount for mount in service["volumes"])


def test_release_worker_is_an_opt_in_service():
    base = safe_load((ROOT / "ops/jenkins/compose.yaml").read_text())
    assert "release-agent" not in base["services"]
    overlay = safe_load((ROOT / "ops/jenkins/release.compose.yaml").read_text())
    assert set(overlay["services"]) == {"release-agent"}
    assert overlay["volumes"]["release-agent-secrets"] == {
        "external": True,
        "name": "finsecure-jenkins-release-agent-secrets",
    }


def test_release_tool_downloads_are_architecture_and_checksum_pinned():
    source = (ROOT / "ops/jenkins/release-agent.Dockerfile").read_text()
    assert 'test "$TARGETARCH" = arm64' in source
    assert source.count("| sha256sum -c -") == 3
    assert "go-containerregistry_Linux_arm64.tar.gz" in source
    assert "v1.36.4/bin/linux/arm64/kubectl" in source
    assert "gke-gcloud-auth-plugin-linux-arm-20261016073856" in source
    assert "898c0cff975f898a33e8c4580bdafb0e7c02c7faa33374e946762f97c4ab7110" in source
    assert "9f53cf95d4bebfe313cd61741d75971b4cd34194fdf00780d754611d22a03528" in source
    assert "0ecf44450ee6063bf19dd166a103ee6df4a9034455c2abce626e6eea657d73fb" in source
    assert "USER jenkins" in source and "VOLUME " not in source
    assert "gcloud components install" not in source
