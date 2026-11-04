// FINSECURE_DELIVERY_CONTRACT_V1
// The reviewed assembler alone may change this constant; there are no job parameters.
final boolean FINSECURE_MUTATIONS_ENABLED = false

def deliveryPhase(String phase, long remainingMillis = 0L, Map baseline = [:]) {
    withEnv(['FINSECURE_RELEASE_PHASE=' + phase,
             'FINSECURE_REMAINING_MS=' + remainingMillis.toString(),
             'FINSECURE_BASELINE_UID=' + (baseline.uid ?: ''),
             'FINSECURE_BASELINE_SPEC=' + (baseline.spec_sha256 ?: '')]) {
        sh '''#!/bin/sh
set -eu
umask 077
python -I -B -c 'from sys import argv,path; from runpy import run_module; path.insert(0,argv.pop(1)); run_module("scripts.release_worker",run_name="__main__")' \
    "$FINSECURE_RELEASE_SCRATCH/tools" --phase "$FINSECURE_RELEASE_PHASE" \
    --root "$FINSECURE_RELEASE_SCRATCH" --remaining-ms "$FINSECURE_REMAINING_MS" \
    --credential "${FINSECURE_RELEASE_KEY:-}" \
    --uid "$FINSECURE_BASELINE_UID" --spec-sha256 "$FINSECURE_BASELINE_SPEC"
'''
    }
}

timeout(time: 10, unit: 'MINUTES') {
    long started = System.nanoTime()
    def expected
    stage('Select current main') {
        expected = FinsecureCandidateSelection.select(currentBuild.rawBuild)
    }
    node('release') {
        def workspace = getContext(hudson.FilePath)
        String scratchName = null
        def primaryFailure = null
        try {
            stage('Prepare trusted inputs') {
                FinsecureCandidateSelection.recheck(currentBuild.rawBuild, expected)
                scratchName = FinsecureWorkerVerification.allocate(workspace)
                def scratch = FinsecureWorkerVerification.scratch(workspace, scratchName)
                def prepared = FinsecureReleasePreparation.prepare(currentBuild.rawBuild, scratch)
                FinsecureCandidateSelection.confirmSelection(expected, prepared.candidate)
                FinsecureVerifierBundle.install(scratch)
            }
            withEnv(['FINSECURE_RELEASE_SCRATCH=' +
                     FinsecureWorkerVerification.scratch(workspace, scratchName).remote]) {
                long remainingMillis = 600000L - ((System.nanoTime() - started) / 1000000L).longValue()
                deliveryPhase('init', remainingMillis)
                stage('Verify without release credentials') {
                    timeout(time: 2, unit: 'MINUTES') {
                    sh '''#!/bin/sh
set -eu
umask 077
python -I -B -c 'from sys import argv,path; from runpy import run_module; path.insert(0,argv.pop(1)); run_module("scripts.release_artifacts",run_name="__main__")' \
    "$FINSECURE_RELEASE_SCRATCH/tools" --input "$FINSECURE_RELEASE_SCRATCH/input" \
    --control "$FINSECURE_RELEASE_SCRATCH/control" > "$FINSECURE_RELEASE_SCRATCH/verification.json"
'''
                    }
                    FinsecureWorkerVerification.readResult(workspace, scratchName, expected)
                    deliveryPhase('prepare')
                    FinsecureDelivery.read(workspace, scratchName, 'prepare', expected)
                }
                def preflight
                stage('Publication preflight') {
                    FinsecureCandidateSelection.recheck(currentBuild.rawBuild, expected)
                    withCredentials([file(credentialsId: 'finsecure-dockerhub', variable: 'FINSECURE_RELEASE_KEY')]) {
                        deliveryPhase('preflight')
                    }
                    preflight = FinsecureDelivery.read(workspace, scratchName, 'preflight', expected)
                }
                if (!FINSECURE_MUTATIONS_ENABLED) {
                    currentBuild.result = 'NOT_BUILT'
                    echo 'RELEASE_VERIFIED_MUTATIONS_DISABLED'
                    return
                }
                stage('Publish exact gated image') {
                    FinsecureCandidateSelection.recheck(currentBuild.rawBuild, expected)
                    withCredentials([file(credentialsId: 'finsecure-dockerhub', variable: 'FINSECURE_RELEASE_KEY')]) {
                        deliveryPhase('publish')
                    }
                    def published = FinsecureDelivery.read(workspace, scratchName, 'publish', expected)
                    FinsecureCandidateSelection.require(published.registry_manifest_digest ==
                        preflight.local_manifest_digest, 'RELEASE_PUBLICATION_IDENTITY_CHANGED')
                }
                stage('Deploy and verify rollout') {
                    def baseline = FinsecureDelivery.baseline(currentBuild.rawBuild)
                    FinsecureCandidateSelection.recheck(currentBuild.rawBuild, expected)
                    withCredentials([file(credentialsId: 'finsecure-gke-deployer', variable: 'FINSECURE_RELEASE_KEY')]) {
                        deliveryPhase('deploy', 0L, baseline)
                    }
                    def deployed = FinsecureDelivery.read(workspace, scratchName, 'deploy', expected)
                    FinsecureCandidateSelection.require(deployed.registry_manifest_digest ==
                        preflight.local_manifest_digest, 'RELEASE_DEPLOYMENT_IDENTITY_CHANGED')
                }
            }
        } catch (Exception failure) {
            primaryFailure = failure
            throw failure
        } finally {
            if (scratchName != null) {
                try {
                    if (FinsecureWorkerVerification.scratch(workspace, scratchName).exists()) {
                        dir(scratchName) {
                            archiveArtifacts artifacts: 'verification.json,prepare.json,preflight.json,publish.json,deploy.json,*-attempt.json',
                                allowEmptyArchive: true, fingerprint: false, followSymlinks: false
                        }
                    }
                } catch (Exception archiveFailure) {
                    if (archiveFailure instanceof InterruptedException || primaryFailure == null) {
                        primaryFailure = archiveFailure
                        throw archiveFailure
                    }
                    echo 'RELEASE_REPORT_ARCHIVE_FAILED'
                } finally {
                    try { FinsecureWorkerVerification.cleanup(workspace, scratchName) }
                    catch (Exception cleanupFailure) {
                        if (cleanupFailure instanceof InterruptedException || primaryFailure == null) {
                            throw cleanupFailure
                        }
                        echo 'RELEASE_SCRATCH_CLEANUP_FAILED_INSPECT_MANUALLY'
                    }
                }
            }
        }
    }
}
