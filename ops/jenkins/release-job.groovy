import com.cloudbees.groovy.cps.NonCPS
import groovy.json.JsonOutput
import groovy.json.JsonSlurperClassic
import hudson.model.Cause
import hudson.model.Result
import hudson.plugins.git.GitSCM
import hudson.plugins.git.util.BuildData
import hudson.tasks.junit.TestResultAction
import jenkins.model.Jenkins
import org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition

// Fixed administrator-owned code. Nothing supplied by an upstream artifact is executed.
class FinsecureCandidateSelection {
    static final String REPOSITORY = 'https://github.com/yuenshingyan/nussoc-devops-and-cloud-with-ai-capstone.git'
    static final String HEAD_URL = 'https://api.github.com/repos/yuenshingyan/nussoc-devops-and-cloud-with-ai-capstone/git/ref/heads/main'
    static final int REPORT_LIMIT = 1024 * 1024

    @NonCPS
    static void require(boolean condition, String code) {
        if (!condition) { throw new IllegalStateException(code) }
    }

    @NonCPS
    static boolean zero(Object value) {
        value instanceof Integer && value == 0
    }

    @NonCPS
    static Map parseReport(InputStream stream) {
        // The caller owns the stream; all acquisition sites below close it.
        byte[] bytes = stream.readNBytes(REPORT_LIMIT + 1)
        require(bytes.length <= REPORT_LIMIT, 'RELEASE_REPORT_TOO_LARGE')
        def data
        try {
            data = new JsonSlurperClassic().parseText(new String(bytes, 'UTF-8'))
        } catch (RuntimeException ignored) {
            throw new IllegalStateException('RELEASE_REPORT_INVALID')
        }
        require(data instanceof Map, 'RELEASE_REPORT_NOT_OBJECT')
        return data
    }

    @NonCPS
    static Map report(def run, String name) {
        // Only fixed names from this reviewed script may reach this helper.
        def stream = run.artifactManager.root().child(name).open()
        try { return parseReport(stream) } finally { stream.close() }
    }

    @NonCPS
    static String currentMain() {
        def connection = new URL(HEAD_URL).openConnection(Proxy.NO_PROXY)
        connection.instanceFollowRedirects = false
        connection.connectTimeout = 5000
        connection.readTimeout = 5000
        connection.setRequestProperty('Accept', 'application/vnd.github+json')
        connection.setRequestProperty('User-Agent', 'finsecure-release-selection')
        try {
            require(connection.responseCode == 200, 'RELEASE_MAIN_LOOKUP_FAILED')
            def stream = connection.inputStream
            Map data
            try { data = parseReport(stream) } finally { stream.close() }
            require(data.object instanceof Map && data.object.type == 'commit', 'RELEASE_MAIN_INVALID')
            require(data.object.sha instanceof String && data.object.sha ==~ /[a-f0-9]{40}/, 'RELEASE_MAIN_INVALID')
            return data.object.sha
        } finally { connection.disconnect() }
    }

    @NonCPS
    static void validateLatest(Object selected, Object latest, Object queued) {
        require(selected instanceof Integer && selected > 0 &&
            latest instanceof Integer && latest > 0 && queued instanceof Boolean,
            'RELEASE_BUILD_ORDER_INVALID')
        // A newer failed/running build also supersedes this candidate, even at the same SHA.
        require(selected == latest, 'RELEASE_SUPERSEDED_BUILD')
        require(!queued, 'RELEASE_SOURCE_BUILD_QUEUED')
    }

    @NonCPS
    static void requireLatest(def job, def run) {
        validateLatest(run.number, job.lastBuild?.number, job.isInQueue())
    }

    @NonCPS
    static void confirmSelection(Map expected, Map observed) {
        require(expected != null && observed != null && expected.equals(observed),
            'RELEASE_CANDIDATE_CHANGED')
    }

    @NonCPS
    static void recheck(def releaseRun, Map expected) {
        // Call immediately before each external action, not just before binding credentials.
        // Re-read native provenance, gate identities and current GitHub main; never retry.
        confirmSelection(expected, select(releaseRun))
    }

    @NonCPS
    static Map validate(Map provenance, Map source, Map image, String head) {
        require(provenance.job == 'finsecure-ci', 'RELEASE_UPSTREAM_JOB_DENIED')
        require(provenance.build instanceof Integer && provenance.build > 0, 'RELEASE_BUILD_INVALID')
        require(provenance.building == false && provenance.result == 'SUCCESS', 'RELEASE_UPSTREAM_NOT_SUCCESS')
        require(provenance.repository == REPOSITORY && provenance.branch == 'refs/remotes/origin/main', 'RELEASE_SOURCE_NOT_MAIN')
        require(provenance.revision instanceof String && provenance.revision ==~ /[a-f0-9]{40}/, 'RELEASE_REVISION_INVALID')
        require(provenance.revision == head, 'RELEASE_STALE_REVISION')
        require(provenance.tests instanceof Integer && provenance.tests > 0 &&
            zero(provenance.failures) && zero(provenance.skipped), 'RELEASE_TESTS_NOT_PASSING')
        require(source.status == 'passed' && source.bandit instanceof Map &&
            source.dependencies instanceof Map, 'RELEASE_SOURCE_GATE_INVALID')
        require(source.bandit.status == 'passed' && zero(source.bandit.HIGH) &&
            zero(source.bandit.MEDIUM) && zero(source.bandit.blocking_findings), 'RELEASE_SOURCE_GATE_INVALID')
        require(source.dependencies.status == 'passed' && zero(source.dependencies.blocking_findings) &&
            source.dependencies.dependencies_audited instanceof Integer &&
            source.dependencies.dependencies_audited > 0, 'RELEASE_DEPENDENCY_GATE_INVALID')
        require(image.status == 'passed' && image.source_revision == provenance.revision &&
            zero(image.blocking_findings) && image.end_of_life == false &&
            image.temporary_cache_removed == true, 'RELEASE_IMAGE_GATE_INVALID')
        require(image.expected_platform == 'linux/amd64' && image.platform == 'linux/amd64', 'RELEASE_PLATFORM_DENIED')
        require(image.severities instanceof Map && zero(image.severities.HIGH) &&
            zero(image.severities.CRITICAL), 'RELEASE_IMAGE_GATE_INVALID')
        require(image.archive_sha256 instanceof String && image.archive_sha256 ==~ /[a-f0-9]{64}/,
            'RELEASE_ARCHIVE_ID_INVALID')
        require(image.image_id instanceof String && image.image_id ==~ /sha256:[a-f0-9]{64}/,
            'RELEASE_IMAGE_ID_INVALID')
        require(source.lock_sha256 instanceof String && source.lock_sha256 ==~ /[a-f0-9]{64}/ &&
            source.lock_sha256 == image.lock_sha256, 'RELEASE_LOCK_MISMATCH')
        return [upstream_build:provenance.build, revision:provenance.revision,
            platform:'linux/amd64', archive_sha256:image.archive_sha256, image_id:image.image_id,
            lock_sha256:image.lock_sha256, tag:'sha-' + provenance.revision + '-amd64',
            artifact_verification_required:true, deployment_enabled:false]
    }

    @NonCPS
    static Map select(def releaseRun) {
        def causes = releaseRun.causes
        require(causes.size() == 1 && causes[0] instanceof Cause.UpstreamCause,
            'RELEASE_UPSTREAM_CAUSE_REQUIRED')
        def cause = causes[0]
        require(cause.upstreamProject == 'finsecure-ci' && cause.upstreamUrl == 'job/finsecure-ci/',
            'RELEASE_UPSTREAM_JOB_DENIED')
        def job = Jenkins.get().getItemByFullName('finsecure-ci')
        require(job != null && job.definition instanceof CpsScmFlowDefinition,
            'RELEASE_SOURCE_JOB_INVALID')
        def definition = job.definition
        require(definition.scriptPath == 'Jenkinsfile' && definition.scm instanceof GitSCM,
            'RELEASE_SOURCE_JOB_INVALID')
        def scm = definition.scm
        require(scm.userRemoteConfigs.size() == 1 && scm.userRemoteConfigs[0].url == REPOSITORY &&
            scm.branches.collect { it.name } == ['*/main'], 'RELEASE_SOURCE_JOB_INVALID')
        def run = job.getBuildByNumber(cause.upstreamBuild)
        require(run != null && !run.building && run.result == Result.SUCCESS, 'RELEASE_UPSTREAM_NOT_SUCCESS')
        requireLatest(job, run)
        def data = run.getActions(BuildData.class)
        require(data.size() == 1 && data[0].remoteUrls == ([REPOSITORY] as Set), 'RELEASE_GIT_DATA_INVALID')
        def revision = data[0].lastBuiltRevision
        require(revision != null && revision.branches.collect { it.name } == ['refs/remotes/origin/main'],
            'RELEASE_GIT_DATA_INVALID')
        def tests = run.getAction(TestResultAction.class)
        require(tests != null, 'RELEASE_TESTS_NOT_PASSING')
        Map provenance = [job:job.fullName, build:run.number, building:run.building,
            result:run.result.toString(), repository:REPOSITORY, branch:'refs/remotes/origin/main',
            revision:revision.sha1String, tests:tests.totalCount, failures:tests.failCount,
            skipped:tests.skipCount]
        Map candidate = validate(provenance, report(run, 'reports/security-summary.json'),
            report(run, 'reports/image-security-summary.json'), currentMain())
        // Local state can change while reports or GitHub are being read.
        requireLatest(job, run)
        return candidate
    }
}

// No node, credential binding, upstream trigger, artifact execution or release action yet.
// A successful selection is NOT sufficient release authorization: bytes/freshness remain unchecked.
timeout(time: 10, unit: 'MINUTES') {
    stage('Select trusted main candidate') {
        def candidate = FinsecureCandidateSelection.select(currentBuild.rawBuild)
        echo JsonOutput.toJson(candidate)
    }
    error('RELEASE_DISABLED_ARTIFACT_TRANSFER_AND_DEPLOYMENT_NOT_IMPLEMENTED')
}
