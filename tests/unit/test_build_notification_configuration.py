"""Static contract checks complement, but do not replace, native Jenkins execution."""

from json import loads
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_notification_overlay_changes_only_controller_and_named_network():
    config = loads((ROOT / "ops/jenkins/notifications.compose.yaml").read_text())
    assert set(config["services"]) == {"controller"}
    controller = config["services"]["controller"]
    assert set(controller) == {"environment", "volumes", "networks"}
    assert controller["networks"] == ["default", "notification"]
    assert controller["volumes"] == ["./notifications.yaml:/etc/jenkins/notifications.yaml:ro"]
    assert controller["environment"]["FINSECURE_CI_NOTIFICATIONS"] == "true"
    assert "-Dmail.smtp.writetimeout=60000" in controller["environment"]["JENKINS_JAVA_OPTS"]
    assert config["networks"] == {
        "notification": {"external": True, "name": "finsecure-monitoring_notification"}
    }


def test_base_jcasc_explicitly_bridges_only_notification_flag_with_false_default():
    base = (ROOT / "ops/jenkins/jenkins.yaml").read_text()
    assert (
        "  globalNodeProperties:\n"
        "    - envVars:\n"
        "        env:\n"
        "          - key: FINSECURE_CI_NOTIFICATIONS\n"
        '            value: "${FINSECURE_CI_NOTIFICATIONS:-false}"\n'
    ) in base
    optional = loads((ROOT / "ops/jenkins/notifications.yaml").read_text())
    assert "jenkins" not in optional
    controller = (ROOT / "ops/jenkins/controller.Dockerfile").read_text()
    assert "COPY --chown=jenkins:jenkins jenkins.yaml /usr/share/jenkins/jenkins.yaml" in controller
    assert (
        "image: finsecure-jenkins-controller:step-04-03-policy"
        in (ROOT / "ops/jenkins/compose.yaml").read_text()
    )


def test_smtp_configuration_is_local_without_credentials_or_extra_configuration():
    config = loads((ROOT / "ops/jenkins/notifications.yaml").read_text())
    assert config == {
        "unclassified": {
            "mailer": {
                "smtpHost": "mailpit",
                "smtpPort": "1025",
                "useSsl": False,
                "useTls": False,
                "charset": "UTF-8",
            }
        }
    }


def test_pipeline_notifies_after_artifact_attempt_and_never_swallows_cancellation():
    pipeline = (ROOT / "Jenkinsfile").read_text()
    notification = pipeline.split("        cleanup {", 1)[1]
    assert "env.FINSECURE_CI_NOTIFICATIONS ?: 'false'" in notification
    assert "notify == 'true'" in notification
    assert "catchInterruptions: false" in notification
    assert "buildResult: 'UNSTABLE'" in notification
    assert "timeout(time: 180, unit: 'SECONDS')" in notification
    assert "from: 'finsecure-ci@example.test'" in notification
    assert "mail to: 'finsecure-operator@example.test'" in notification
    assert "mimeType: 'text/plain'" in notification
    assert "Result before notification:" in notification
    assert "no SMTP delivery attempted" in notification
    assert "retry(" not in notification and "attach" not in notification


def test_notification_uses_explicitly_persisted_checkout_revision():
    pipeline = (ROOT / "Jenkinsfile").read_text()
    checkout = pipeline.split("stage('Checkout')", 1)[1].split("stage('Locked dependencies')", 1)[0]
    notification = pipeline.split("        cleanup {", 1)[1]
    assert checkout.index("checkout scm") < checkout.index("env.FINSECURE_SOURCE_REVISION = sh(")
    assert "script: 'git rev-parse HEAD', returnStdout: true" in checkout
    assert ").trim()" in checkout
    assert "${env.FINSECURE_SOURCE_REVISION ?: 'unavailable'}" in notification
    assert "env.GIT_COMMIT" not in notification


def test_container_uses_safe_logging_configuration_without_raw_access_logs():
    dockerfile = (ROOT / "Dockerfile").read_text()
    assert '"--no-access-log", "--log-config", "/app/logging.json"' in dockerfile
    config = loads((ROOT / "src/finsecure_pay/observability/logging.json").read_text())
    assert config["root"]["level"] == "INFO"
    assert config["disable_existing_loggers"] is False
    assert config["formatters"] == {
        "safe_json": {"()": "finsecure_pay.observability.logging.JsonEventFormatter"}
    }
