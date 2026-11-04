from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_ci_export_and_scan_explicitly_select_amd64():
    pipeline = (ROOT / "Jenkinsfile").read_text()
    assert "PLATFORM=linux/amd64" in pipeline
    assert "--opt platform=linux/amd64" in pipeline
    assert "--platform linux/amd64" in pipeline
    assert "linux/arm64" not in pipeline


def test_amd64_artifact_remains_after_all_existing_gates_without_release_credentials():
    pipeline = (ROOT / "Jenkinsfile").read_text()
    assert pipeline.index("stage('Tests')") < pipeline.index("stage('Security scans')")
    assert pipeline.index("stage('Security scans')") < pipeline.index("stage('Local image export')")
    assert pipeline.index("stage('Image security gate')") < pipeline.index(
        "archiveArtifacts artifacts: 'images/finsecure-pay.tar.gz'"
    )
    assert "agent { label 'python' }" in pipeline
    assert "withCredentials" not in pipeline
    assert "timeout(time: 30, unit: 'MINUTES')" in pipeline
