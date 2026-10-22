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
    }
    post {
        always {
            // Exact allowlist: never archive environments, credentials, caches, or the workspace.
            archiveArtifacts artifacts: 'reports/build-metadata.txt,reports/dependencies.txt,reports/lint.txt,reports/format.txt,reports/tests.txt,reports/junit.xml,reports/coverage.xml,reports/package.txt,reports/packages.sha256',
                             allowEmptyArchive: true
        }
    }
}
