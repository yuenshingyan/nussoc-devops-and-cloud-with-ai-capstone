import com.cloudbees.groovy.cps.NonCPS
import groovy.json.JsonOutput
import hudson.FilePath
import hudson.model.Result
import hudson.model.Run
import java.nio.file.LinkOption
import java.security.MessageDigest
import jenkins.model.Jenkins

/** Trusted controller helper only. Copy data, never upstream code or credentials.
 * The caller owns the new scratch directory and its cleanup. Source eligibility and
 * trusted Git snapshots must be established separately before this helper is called.
 */
class FinsecureArtifactTransfer {
    static final long SMALL_LIMIT = 1024L * 1024L
    static final long IMAGE_LIMIT = 64L * SMALL_LIMIT
    static final List<String> FILES = [
        'reports/security-summary.json', 'reports/security-tools.txt',
        'reports/security-export.txt', 'reports/runtime-requirements.txt',
        'reports/bandit.json', 'reports/bandit.txt',
        'reports/pip-audit.json', 'reports/pip-audit.txt',
        'reports/image-security-summary.json', 'reports/image-security-tools.txt',
        'reports/image-security-export.txt', 'reports/image-runtime-requirements.txt',
        'reports/trivy-db.json', 'reports/trivy-db.txt', 'reports/trivy.json', 'reports/trivy.txt',
        'reports/build-metadata.txt', 'reports/image-metadata.txt',
        'reports/buildkit-image.json', 'reports/image.sha256', 'images/finsecure-pay.tar.gz'
    ].asImmutable()

    @NonCPS
    static void require(boolean allowed, String code) {
        if (!allowed) { throw new IllegalStateException(code) }
    }

    @NonCPS
    static void checkBudget(long deadlineNanos) {
        require(!Thread.currentThread().isInterrupted(), 'TRANSFER_INTERRUPTED')
        require(System.nanoTime() < deadlineNanos, 'TRANSFER_BUDGET_EXCEEDED')
    }

    @NonCPS
    static Map copyStream(InputStream source, OutputStream destination, long limit, long deadlineNanos) {
        // Borrow both streams; the caller always closes them, including after partial writes.
        MessageDigest digest = MessageDigest.getInstance('SHA-256')
        byte[] buffer = new byte[65536]
        long size = 0
        while (true) {
            checkBudget(deadlineNanos)
            int count = source.read(buffer)
            if (count == -1) { break }
            require(count > 0, 'TRANSFER_EMPTY_READ')
            size += count
            require(size <= limit, 'TRANSFER_SIZE_LIMIT')
            destination.write(buffer, 0, count)
            digest.update(buffer, 0, count)
        }
        checkBudget(deadlineNanos)
        return [size: size, sha256: digest.digest().encodeHex().toString()]
    }

    @NonCPS
    static void writeControl(FilePath path, byte[] data) {
        require(data.length > 0 && data.length <= SMALL_LIMIT, 'CONTROL_SIZE_LIMIT')
        OutputStream output = path.write()
        try { output.write(data) } finally { output.close() }
        path.chmod(0600)
    }

    @NonCPS
    static Map copy(Run upstream, FilePath destination, Map trustedContext,
                    byte[] trustedLock, byte[] trustedProject, long deadlineNanos) {
        checkBudget(deadlineNanos)
        require(upstream != null && !upstream.isBuilding() && upstream.result == Result.SUCCESS,
                'TRANSFER_SOURCE_NOT_COMPLETE_SUCCESS')
        require(trustedContext.upstream_job == upstream.parent.fullName &&
                trustedContext.upstream_build == upstream.number, 'TRANSFER_RUN_IDENTITY_MISMATCH')
        def computer = Jenkins.get().getNode('finsecure-release')?.toComputer()
        require(computer != null && computer.online && computer.channel != null &&
                destination.channel == computer.channel, 'TRANSFER_WRONG_NODE')
        require(destination.remote.startsWith('/home/jenkins/agent/') &&
                !destination.remote.split('/').any { it == '..' || it == '.' }, 'TRANSFER_UNSAFE_DESTINATION')
        require(!destination.exists(), 'TRANSFER_DESTINATION_EXISTS')
        require(upstream.artifactManager.class.name == 'jenkins.model.StandardArtifactManager',
                'TRANSFER_ARTIFACT_MANAGER_UNSUPPORTED')
        def root = upstream.artifactManager.root()
        require(root.supportIsDescendant(), 'TRANSFER_DESCENDANT_CHECK_UNAVAILABLE')
        for (String directory : ['reports', 'images']) {
            def child = root.child(directory)
            require(child.isDirectory() && child.readLink() == null && root.isDescendant(directory),
                    'TRANSFER_UNSAFE_SOURCE_DIRECTORY')
        }
        destination.mkdirs()
        destination.chmod(0700)
        for (String directory : ['input', 'input/reports', 'input/images', 'control']) {
            destination.child(directory).mkdirs()
            destination.child(directory).chmod(0700)
        }
        Map inventory = [:]
        for (String name : FILES) {
            checkBudget(deadlineNanos)
            def artifact = root.child(name)
            long limit = name.startsWith('images/') ? IMAGE_LIMIT : SMALL_LIMIT
            require(root.isDescendant(name) && artifact.isFile() && artifact.readLink() == null &&
                    artifact.length() >= 0 && artifact.length() <= limit, 'TRANSFER_INVALID_ARTIFACT')
            long expectedSize = artifact.length()
            FilePath target = destination.child('input/' + name)
            InputStream source = artifact.open(LinkOption.NOFOLLOW_LINKS)
            try {
                OutputStream output = target.write()
                try {
                    inventory[name] = copyStream(source, output, limit, deadlineNanos)
                } finally { output.close() }
            } finally { source.close() }
            target.chmod(0600)
            require(inventory[name].size == expectedSize && artifact.length() == expectedSize,
                    'TRANSFER_SOURCE_SIZE_CHANGED')
        }
        writeControl(destination.child('control/uv.lock'), trustedLock)
        writeControl(destination.child('control/pyproject.toml'), trustedProject)
        checkBudget(deadlineNanos)
        // The receipt is produced last by trusted code, not copied from the upstream archive.
        byte[] receipt = JsonOutput.toJson([
            schema_version: 1, context: trustedContext, artifacts: inventory
        ]).getBytes('UTF-8')
        writeControl(destination.child('control/receipt.json'), receipt)
        return [files: inventory.size(), bytes: inventory.values().sum { it.size },
                receipt_sha256: MessageDigest.getInstance('SHA-256').digest(receipt).encodeHex().toString()]
    }
}
