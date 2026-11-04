import com.cloudbees.groovy.cps.NonCPS
import hudson.FilePath
import hudson.model.Result
import java.nio.file.LinkOption

/** Controller-owned delivery contracts; never use producer artifacts as deployment approval. */
class FinsecureDelivery {
    static final String UID = 'aadc396b-cf58-4929-96d1-0e225d8b4256'
    static final String INITIAL_SPEC = '158af9a81aa2cf64a3252a974a3627f3f6134c5f1cbf0a9e1178550bff3b39bb'

    @NonCPS
    static Map read(FilePath workspace, String scratchName, String phase, Map candidate) {
        FinsecureCandidateSelection.require(phase in ['prepare', 'preflight', 'publish', 'deploy'],
            'RELEASE_PHASE_INVALID')
        FilePath file = FinsecureWorkerVerification.scratch(workspace, scratchName).child(phase + '.json')
        FinsecureCandidateSelection.require(file.exists() && !file.isDirectory() && file.readLink() == null &&
            file.length() > 0 && file.length() <= 1024 * 1024, 'RELEASE_PHASE_REPORT_INVALID')
        InputStream input = file.read()
        Map report
        try { report = FinsecureCandidateSelection.parseReport(input) }
        finally { input.close() }
        FinsecureCandidateSelection.require(report.revision == candidate.revision &&
            report.image_id == candidate.image_id && report.archive_sha256 == candidate.archive_sha256,
            'RELEASE_PHASE_IDENTITY_CHANGED')
        Map statuses = [prepare: 'prepared', preflight: 'preflight_verified',
            publish: 'verified', deploy: 'deployment_verified']
        FinsecureCandidateSelection.require(report.status == statuses[phase], 'RELEASE_PHASE_NOT_VERIFIED')
        if (phase == 'preflight') {
            FinsecureCandidateSelection.require(report.local_manifest_digest instanceof String &&
                report.local_manifest_digest ==~ /sha256:[a-f0-9]{64}/, 'RELEASE_LOCAL_DIGEST_INVALID')
        }
        if (phase in ['publish', 'deploy']) {
            FinsecureCandidateSelection.require(report.registry_manifest_digest instanceof String &&
                report.registry_manifest_digest ==~ /sha256:[a-f0-9]{64}/, 'RELEASE_REGISTRY_DIGEST_INVALID')
        }
        if (phase == 'deploy') { validateDeployment(report) }
        return report
    }

    @NonCPS
    static void validateDeployment(Map report) {
        FinsecureCandidateSelection.require(report.status == 'deployment_verified' && report.deployment_uid == UID &&
            report.smoke_verified instanceof Boolean && report.smoke_verified &&
            report.automatic_rollback instanceof Boolean && !report.automatic_rollback &&
            report.spec_sha256 instanceof String && report.spec_sha256 ==~ /[a-f0-9]{64}/ &&
            report.pod_uids instanceof List && report.pod_uids.size() == 2 &&
            report.pod_uids.every { it instanceof String && !it.isEmpty() } &&
            report.pod_uids.toSet().size() == 2, 'RELEASE_DEPLOYMENT_PROOF_INVALID')
    }

    @NonCPS
    static Map baseline(def run) {
        def previous = run.previousSuccessfulBuild
        if (previous == null) { return [uid: UID, spec_sha256: INITIAL_SPEC] }
        FinsecureCandidateSelection.require(!previous.isBuilding() && previous.result == Result.SUCCESS &&
            previous.parent.fullName == 'finsecure-release/delivery' &&
            previous.execution?.script?.contains('// FINSECURE_DELIVERY_CONTRACT_V1') &&
            previous.artifactManager.class.name == 'jenkins.model.StandardArtifactManager',
            'RELEASE_BASELINE_PROVENANCE_INVALID')
        def root = previous.artifactManager.root()
        def file = root.child('deploy.json')
        FinsecureCandidateSelection.require(root.supportIsDescendant() && root.isDescendant('deploy.json') &&
            file.isFile() && file.readLink() == null && file.length() > 0 && file.length() <= 1024 * 1024,
            'RELEASE_BASELINE_REPORT_INVALID')
        InputStream input = file.open(LinkOption.NOFOLLOW_LINKS)
        Map report
        try { report = FinsecureCandidateSelection.parseReport(input) }
        finally { input.close() }
        validateDeployment(report)
        return [uid: UID, spec_sha256: report.spec_sha256]
    }
}
