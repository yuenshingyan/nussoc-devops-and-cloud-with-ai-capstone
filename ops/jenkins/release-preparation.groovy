import com.cloudbees.groovy.cps.NonCPS
import hudson.FilePath
import jenkins.model.Jenkins

/** Controller-owned composition. Prepare only data; never bind credentials or authorize delivery. */
class FinsecureReleasePreparation {
    @NonCPS
    static Map controlContext(Map candidate, Map snapshot) {
        FinsecureCandidateSelection.require(candidate.revision == snapshot.revision &&
            candidate.lock_sha256 == snapshot.lock_sha256, 'RELEASE_SOURCE_SNAPSHOT_MISMATCH')
        FinsecureCandidateSelection.require(candidate.upstream_build instanceof Integer &&
            candidate.upstream_build > 0, 'RELEASE_BUILD_INVALID')
        return [upstream_job:'finsecure-ci', upstream_build:candidate.upstream_build,
            revision:candidate.revision,
            local_tag:'finsecure-pay-ci:jenkins-finsecure-ci-' + candidate.upstream_build,
            image_id:candidate.image_id, archive_sha256:candidate.archive_sha256,
            lock_sha256:snapshot.lock_sha256, pyproject_sha256:snapshot.pyproject_sha256,
            source_sha256:snapshot.source_sha256]
    }

    @NonCPS
    static Map prepare(def releaseRun, FilePath destination) {
        Map candidate = FinsecureCandidateSelection.select(releaseRun)
        Map snapshot = FinsecureSourceSnapshot.acquire(candidate.revision,
            System.nanoTime() + 120000000000L)
        Map context = controlContext(candidate, snapshot)
        // The public-source fetch can outlive the candidate's eligibility.
        FinsecureCandidateSelection.recheck(releaseRun, candidate)
        def upstream = Jenkins.get().getItemByFullName('finsecure-ci')
            .getBuildByNumber(candidate.upstream_build)
        Map transfer = FinsecureArtifactTransfer.copy(upstream, destination, context,
            snapshot.lock, snapshot.project, System.nanoTime() + 120000000000L)
        // Verifier code must be bundled in the reviewed controller definition, not fetched Git data.
        // The operation owner must verify on the worker and clean up its new scratch directory.
        return [candidate:candidate, transfer:transfer, artifact_verification_required:true,
                publishing_authorized:false]
    }
}
