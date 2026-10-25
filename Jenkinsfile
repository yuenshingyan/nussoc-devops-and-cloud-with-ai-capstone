pipeline {
    agent { label 'python' }
    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        skipStagesAfterUnstable()
        timeout(time: 15, unit: 'MINUTES')
    }
    stages {
        stage('Checkout') {
            steps {
                deleteDir()
                checkout scm
                sh '''#!/usr/bin/env bash
set -euo pipefail
mkdir -p reports
{
    printf 'SOURCE_REVISION='
    git rev-parse HEAD
    python --version
    uv --version
    git --version
    sha256sum uv.lock
} > reports/build-metadata.txt
cat reports/build-metadata.txt
'''
            }
        }
        stage('Locked dependencies') {
            steps {
                sh '''#!/usr/bin/env bash
set -euo pipefail
uv sync --locked 2>&1 | tee reports/dependencies.txt
'''
            }
        }
        stage('Code checks') {
            steps {
                sh '''#!/usr/bin/env bash
set -euo pipefail
uv run --locked ruff check . 2>&1 | tee reports/lint.txt
uv run --locked ruff format --check . 2>&1 | tee reports/format.txt
'''
            }
        }
        stage('Tests') {
            steps {
                sh '''#!/usr/bin/env bash
set -euo pipefail
./scripts/test.sh 2>&1 | tee reports/tests.txt
'''
            }
            post {
                always {
                    script {
                        // Attempt both publishers even if one rejects a missing/malformed report.
                        try {
                            junit testResults: 'reports/junit.xml',
                                  allowEmptyResults: false,
                                  skipPublishingChecks: true
                        } finally {
                            recordCoverage tools: [[parser: 'COBERTURA', pattern: 'reports/coverage.xml']],
                                           id: 'coverage', name: 'Application coverage',
                                           enabledForFailure: true, failOnError: true,
                                           sourceCodeRetention: 'NEVER', sourceCodeEncoding: 'UTF-8',
                                           sourceDirectories: [[path: 'src/finsecure_pay']],
                                           skipPublishingChecks: true, qualityGates: []
                        }
                    }
                }
            }
        }
        stage('Package') {
            steps {
                sh '''#!/usr/bin/env bash
set -euo pipefail
uv build 2>&1 | tee reports/package.txt
set -- dist/*.whl
test "$#" -eq 1 && test -s "$1"
set -- dist/*.tar.gz
test "$#" -eq 1 && test -s "$1"
sha256sum dist/*.whl dist/*.tar.gz > reports/packages.sha256
'''
                archiveArtifacts artifacts: 'dist/*.whl,dist/*.tar.gz',
                                 allowEmptyArchive: false, fingerprint: true
            }
        }
        stage('Local image export') {
            options { timeout(time: 10, unit: 'MINUTES') }
            steps {
                sh '''#!/usr/bin/env bash
set -euo pipefail
mkdir -p images
revision=$(git rev-parse HEAD)
[[ "$BUILD_TAG" =~ ^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$ ]]
image_name="finsecure-pay-ci:${BUILD_TAG}"
# Never borrow registry credentials from a persistent agent home.
export DOCKER_CONFIG
DOCKER_CONFIG=$(mktemp -d)
trap 'rm -rf -- "$DOCKER_CONFIG"' EXIT
buildctl --version > reports/buildkit-workers.txt
buildctl --addr=unix:///run/buildkit/buildkitd.sock --timeout=5 debug workers --verbose >> reports/buildkit-workers.txt
printf 'SOURCE_REVISION=%s\\nLOCAL_TAG=%s\\nPLATFORM=linux/arm64\\n' "$revision" "$image_name" > reports/image-metadata.txt
timeout --signal=TERM --kill-after=15s 9m \
    buildctl --addr=unix:///run/buildkit/buildkitd.sock --timeout=5 build \
    --frontend=dockerfile.v0 --local context=. --local dockerfile=. \
    --opt platform=linux/arm64 --opt "label:org.opencontainers.image.revision=$revision" \
    --output "type=docker,name=$image_name,dest=images/finsecure-pay.tar" \
    --metadata-file reports/buildkit-image.json --progress=plain \
    2>&1 | tee reports/image-build.txt
test -s images/finsecure-pay.tar
gzip -n -1 images/finsecure-pay.tar
sha256sum images/finsecure-pay.tar.gz > reports/image.sha256
'''
                archiveArtifacts artifacts: 'images/finsecure-pay.tar.gz',
                                 allowEmptyArchive: false, fingerprint: true
            }
        }
    }
    post {
        always {
            // Exact allowlist: never archive environments, credentials, caches, or the workspace.
            archiveArtifacts artifacts: 'reports/build-metadata.txt,reports/dependencies.txt,reports/lint.txt,reports/format.txt,reports/tests.txt,reports/junit.xml,reports/coverage.xml,reports/package.txt,reports/packages.sha256,reports/buildkit-workers.txt,reports/image-metadata.txt,reports/image-build.txt,reports/buildkit-image.json,reports/image.sha256',
                             allowEmptyArchive: true
        }
    }
}
