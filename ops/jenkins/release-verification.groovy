import com.cloudbees.groovy.cps.NonCPS
import hudson.FilePath
import jenkins.model.Jenkins

/** Trusted worker boundary and result contract; no credential lookup or release authority. */
class FinsecureWorkerVerification {
    @NonCPS
    static FilePath scratch(FilePath workspace, String name) {
        def computer = Jenkins.get().getNode('finsecure-release')?.toComputer()
        FinsecureCandidateSelection.require(computer != null && computer.online &&
            computer.channel != null && workspace.channel == computer.channel,
            'RELEASE_VERIFICATION_WRONG_NODE')
        FinsecureCandidateSelection.require(workspace.remote.startsWith('/home/jenkins/agent/') &&
            !workspace.remote.split('/').any { it == '.' || it == '..' } &&
            name != null && name ==~ /release-data-[a-f0-9]{32}/, 'RELEASE_SCRATCH_PATH_INVALID')
        return workspace.child(name)
    }

    @NonCPS
    static String allocate(FilePath workspace) {
        String name = 'release-data-' + UUID.randomUUID().toString().replace('-', '')
        FinsecureCandidateSelection.require(!scratch(workspace, name).exists(), 'RELEASE_SCRATCH_EXISTS')
        return name
    }

    @NonCPS
    static Map validate(Map report, Map candidate) {
        Set keys = ['status', 'publishing_authorized', 'revision', 'archive_sha256',
            'database_age_seconds', 'verified_files', 'source_findings', 'image_id', 'platform',
            'layers', 'expanded_layer_bytes', 'archive_oci_manifest_digest'] as Set
        FinsecureCandidateSelection.require(report.keySet() == keys && report.status == 'verified' &&
            report.publishing_authorized instanceof Boolean && !report.publishing_authorized,
            'RELEASE_VERIFIER_RESULT_INVALID')
        FinsecureCandidateSelection.require(report.revision == candidate.revision &&
            report.archive_sha256 == candidate.archive_sha256 && report.image_id == candidate.image_id &&
            report.platform == 'linux/amd64', 'RELEASE_VERIFIER_IDENTITY_MISMATCH')
        FinsecureCandidateSelection.require(report.verified_files instanceof Integer && report.verified_files == 21 &&
            report.layers instanceof Integer && report.layers > 0 && report.layers <= 64 &&
            report.expanded_layer_bytes instanceof Integer && report.expanded_layer_bytes > 0 &&
            report.expanded_layer_bytes <= 512 * 1024 * 1024 &&
            report.database_age_seconds instanceof Number && report.database_age_seconds >= 0 &&
            report.database_age_seconds <= 86400, 'RELEASE_VERIFIER_BOUNDS_INVALID')
        FinsecureCandidateSelection.require(report.archive_oci_manifest_digest instanceof String &&
            report.archive_oci_manifest_digest ==~ /sha256:[a-f0-9]{64}/,
            'RELEASE_VERIFIER_MANIFEST_INVALID')
        def findings = report.source_findings
        FinsecureCandidateSelection.require(findings instanceof Map &&
            findings.keySet() == (['LOW', 'MEDIUM', 'HIGH', 'blocking_findings'] as Set) &&
            findings.LOW instanceof Integer && findings.LOW >= 0 &&
            FinsecureCandidateSelection.zero(findings.MEDIUM) &&
            FinsecureCandidateSelection.zero(findings.HIGH) &&
            FinsecureCandidateSelection.zero(findings.blocking_findings), 'RELEASE_VERIFIER_FINDINGS_INVALID')
        return report
    }

    @NonCPS
    static Map readResult(FilePath workspace, String name, Map candidate) {
        FilePath file = scratch(workspace, name).child('verification.json')
        FinsecureCandidateSelection.require(file.exists() && !file.isDirectory() && file.readLink() == null &&
            file.length() > 0 && file.length() <= 1024 * 1024, 'RELEASE_VERIFIER_OUTPUT_INVALID')
        InputStream input = file.read()
        try { return validate(FinsecureCandidateSelection.parseReport(input), candidate) }
        finally { input.close() }
    }

    @NonCPS
    static boolean reportExists(FilePath workspace, String name) {
        FilePath file = scratch(workspace, name).child('verification.json')
        return file.exists() && !file.isDirectory() && file.readLink() == null &&
            file.length() > 0 && file.length() <= 1024 * 1024
    }

    @NonCPS
    static void cleanup(FilePath workspace, String name) {
        FilePath directory = scratch(workspace, name)
        if (directory.exists()) { directory.deleteRecursive() }
        FinsecureCandidateSelection.require(!directory.exists(), 'RELEASE_SCRATCH_CLEANUP_FAILED')
    }
}
