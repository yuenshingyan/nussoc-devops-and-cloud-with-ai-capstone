// Verification-only candidate. No credential binding, upload, deployment or automatic retry.
timeout(time: 10, unit: 'MINUTES') {
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
            stage('Verify without release credentials') {
                withEnv(['FINSECURE_RELEASE_SCRATCH=' +
                         FinsecureWorkerVerification.scratch(workspace, scratchName).remote]) {
                    timeout(time: 2, unit: 'MINUTES') {
                        sh '''#!/bin/sh
set -eu
umask 077
python -I -B -c 'from sys import argv,path; from runpy import run_module; path.insert(0,argv.pop(1)); run_module("scripts.release_artifacts",run_name="__main__")' \
    "$FINSECURE_RELEASE_SCRATCH/tools" \
    --input "$FINSECURE_RELEASE_SCRATCH/input" \
    --control "$FINSECURE_RELEASE_SCRATCH/control" \
    > "$FINSECURE_RELEASE_SCRATCH/verification.json"
'''
                    }
                }
                FinsecureWorkerVerification.readResult(workspace, scratchName, expected)
            }
            stage('Recheck candidate after verification') {
                FinsecureCandidateSelection.recheck(currentBuild.rawBuild, expected)
            }
        } catch (Exception failure) {
            primaryFailure = failure
            throw failure
        } finally {
            if (scratchName != null) {
                try {
                    if (FinsecureWorkerVerification.reportExists(workspace, scratchName)) {
                        archiveArtifacts artifacts: scratchName + '/verification.json',
                            allowEmptyArchive: false, fingerprint: false, followSymlinks: false
                    }
                } catch (Exception archiveFailure) {
                    if (archiveFailure instanceof InterruptedException) {
                        primaryFailure = archiveFailure
                        throw archiveFailure
                    }
                    if (primaryFailure == null) { primaryFailure = archiveFailure; throw archiveFailure }
                    echo 'RELEASE_VERIFICATION_REPORT_ARCHIVE_FAILED'
                } finally {
                    try {
                        FinsecureWorkerVerification.cleanup(workspace, scratchName)
                    } catch (Exception cleanupFailure) {
                        if (cleanupFailure instanceof InterruptedException) { throw cleanupFailure }
                        if (primaryFailure == null) { throw cleanupFailure }
                        echo 'RELEASE_SCRATCH_CLEANUP_FAILED_RETAINED_FOR_OPERATOR'
                    }
                }
            }
        }
    }
    error('RELEASE_DISABLED_PUBLISHING_AND_DEPLOYMENT_NOT_IMPLEMENTED')
}
