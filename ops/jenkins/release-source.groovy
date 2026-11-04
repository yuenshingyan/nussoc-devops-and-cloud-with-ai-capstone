import com.cloudbees.groovy.cps.NonCPS
import java.security.MessageDigest
import java.util.zip.GZIPInputStream
import org.apache.tools.tar.TarInputStream

/** Owned wrapper chain: count reads and skips, and close the underlying stream with the owner. */
class FinsecureSnapshotStream extends FilterInputStream {
    final long limit
    final long deadline
    long consumed = 0

    FinsecureSnapshotStream(InputStream source, long limit, long deadline) {
        super(source)
        this.limit = limit
        this.deadline = deadline
    }

    @NonCPS
    void check(int count) {
        if (count > 0) { consumed += count }
        FinsecureSourceSnapshot.require(consumed <= limit, 'SOURCE_STREAM_LIMIT')
        FinsecureSourceSnapshot.checkBudget(deadline)
    }

    @Override @NonCPS
    int read() {
        check(0)
        int value = super.read()
        check(value == -1 ? 0 : 1)
        return value
    }

    @Override @NonCPS
    int read(byte[] buffer, int offset, int length) {
        check(0)
        int count = super.read(buffer, offset, (int)Math.min((long)length, limit - consumed + 1L))
        check(count)
        return count
    }

    @Override @NonCPS
    long skip(long amount) {
        byte[] buffer = new byte[8192]
        long skipped = 0
        while (skipped < amount) {
            int count = read(buffer, 0, (int)Math.min((long)buffer.length, amount - skipped))
            if (count == -1) { break }
            FinsecureSourceSnapshot.require(count > 0, 'SOURCE_EMPTY_READ')
            skipped += count
        }
        return skipped
    }
}

/** Fetch immutable public Git source, independently of upstream artifacts; never execute it. */
class FinsecureSourceSnapshot {
    static final String REPOSITORY_NAME = 'nussoc-devops-and-cloud-with-ai-capstone'
    static final String ARCHIVE_URL = 'https://codeload.github.com/yuenshingyan/nussoc-devops-and-cloud-with-ai-capstone/tar.gz/'
    static final int FILE_LIMIT = 1024 * 1024
    static final long COMPRESSED_LIMIT = 32L * FILE_LIMIT
    static final long EXPANDED_LIMIT = 64L * FILE_LIMIT
    static final int ENTRY_LIMIT = 4096
    static final int SOURCE_LIMIT = 200

    @NonCPS
    static void require(boolean allowed, String code) {
        if (!allowed) { throw new IllegalStateException(code) }
    }

    @NonCPS
    static void checkBudget(long deadline) {
        require(!Thread.currentThread().isInterrupted(), 'SOURCE_INTERRUPTED')
        require(System.nanoTime() < deadline, 'SOURCE_BUDGET_EXCEEDED')
    }

    @NonCPS
    static String prefix(String revision) {
        require(revision != null && revision ==~ /[a-f0-9]{40}/, 'SOURCE_REVISION_INVALID')
        return REPOSITORY_NAME + '-' + revision + '/'
    }

    @NonCPS
    static boolean scanned(String name) {
        return name.endsWith('.py') &&
            ['src/finsecure_pay/', 'scripts/', 'ops/jenkins/'].any { name.startsWith(it) }
    }

    @NonCPS
    static String relativeName(String name, boolean directory, String prefix) {
        require(name != null && name.startsWith(prefix), 'SOURCE_ARCHIVE_PREFIX_INVALID')
        String relative = name.substring(prefix.length())
        if (directory && relative.endsWith('/')) { relative = relative.substring(0, relative.length() - 1) }
        if (directory && relative == '') { return '' }
        require(relative.length() <= 512 && relative ==~ /[A-Za-z0-9_.-]+(?:\/[A-Za-z0-9_.-]+)*/ &&
                !relative.split('/').any { it == '.' || it == '..' }, 'SOURCE_PATH_INVALID')
        return relative
    }

    @NonCPS
    static Map readArchive(TarInputStream archive, String revision, long deadline) {
        String expectedPrefix = prefix(revision)
        Set<String> seen = [] as Set
        Map hashes = [:]
        Map controls = [:]
        byte[] buffer = new byte[65536]
        long selectedBytes = 0
        boolean gitHeaderSeen = false
        def entry
        while ((entry = archive.nextEntry) != null) {
            checkBudget(deadline)
            if (entry.isGlobalPaxHeader()) {
                // GitHub's Git archive adds exactly one commit-comment record before the tree.
                require(!gitHeaderSeen && seen.isEmpty() && entry.name == 'pax_global_header' &&
                        entry.size == 52, 'SOURCE_GIT_HEADER_INVALID')
                byte[] header = archive.readNBytes(52)
                require(new String(header, 'UTF-8') == '52 comment=' + revision + '\n',
                        'SOURCE_GIT_HEADER_INVALID')
                gitHeaderSeen = true
                continue
            }
            String name = relativeName(entry.name, entry.isDirectory(), expectedPrefix)
            require(seen.add(name) && seen.size() <= ENTRY_LIMIT, 'SOURCE_DUPLICATE_OR_EXCESS_ENTRIES')
            require(!entry.symbolicLink && !entry.link && !entry.isGNUSparse() &&
                    (entry.isDirectory() || entry.isFile()), 'SOURCE_UNSUPPORTED_ENTRY')
            require(entry.size >= 0 && entry.size <= EXPANDED_LIMIT, 'SOURCE_MEMBER_LIMIT')
            if (entry.isDirectory()) {
                require(entry.size == 0, 'SOURCE_DIRECTORY_DATA')
                continue
            }
            boolean control = name in ['uv.lock', 'pyproject.toml']
            boolean selected = control || scanned(name)
            if (selected) {
                require(entry.size <= FILE_LIMIT, 'SOURCE_FILE_LIMIT')
                selectedBytes += entry.size
                require(selectedBytes <= 8L * FILE_LIMIT, 'SOURCE_SELECTED_BYTES_LIMIT')
            }
            MessageDigest digest = selected ? MessageDigest.getInstance('SHA-256') : null
            ByteArrayOutputStream bytes = control ? new ByteArrayOutputStream() : null
            long size = 0
            try {
                int count
                while ((count = archive.read(buffer)) != -1) {
                    checkBudget(deadline)
                    require(count > 0, 'SOURCE_EMPTY_READ')
                    size += count
                    require(size <= entry.size, 'SOURCE_MEMBER_SIZE_MISMATCH')
                    if (selected) { digest.update(buffer, 0, count) }
                    if (control) { bytes.write(buffer, 0, count) }
                }
                require(size == entry.size, 'SOURCE_MEMBER_SIZE_MISMATCH')
                if (selected) {
                    String hash = digest.digest().encodeHex().toString()
                    if (control) { controls[name] = [bytes:bytes.toByteArray(), sha256:hash] }
                    else {
                        hashes[name] = hash
                        require(hashes.size() <= SOURCE_LIMIT, 'SOURCE_FILE_COUNT_LIMIT')
                    }
                }
            } finally { bytes?.close() }
        }
        require(controls.keySet() == (['uv.lock', 'pyproject.toml'] as Set) && !hashes.isEmpty(),
                'SOURCE_REQUIRED_FILES_MISSING')
        return [revision:revision, source_sha256:hashes,
                lock_sha256:controls['uv.lock'].sha256, pyproject_sha256:controls['pyproject.toml'].sha256,
                lock:controls['uv.lock'].bytes, project:controls['pyproject.toml'].bytes,
                archive_entries:seen.size(), selected_bytes:selectedBytes]
    }

    @NonCPS
    static Map acquire(String revision, long deadline) {
        prefix(revision)
        checkBudget(deadline)
        def connection = new URL(ARCHIVE_URL + revision).openConnection(Proxy.NO_PROXY)
        connection.instanceFollowRedirects = false
        connection.connectTimeout = 5000
        connection.readTimeout = 5000
        connection.setRequestProperty('Accept-Encoding', 'identity')
        connection.setRequestProperty('User-Agent', 'finsecure-source-snapshot')
        InputStream owned = null
        try {
            require(connection.responseCode == 200, 'SOURCE_HTTP_STATUS_INVALID')
            require(connection.contentLengthLong <= COMPRESSED_LIMIT, 'SOURCE_STREAM_LIMIT')
            owned = connection.inputStream
            owned = new FinsecureSnapshotStream(owned, COMPRESSED_LIMIT, deadline)
            owned = new GZIPInputStream(owned)
            def expanded = new FinsecureSnapshotStream(owned, EXPANDED_LIMIT, deadline)
            owned = expanded
            // One-record buffering keeps trailing bytes visible to the final drain.
            owned = new TarInputStream(owned, 512, 512, 'UTF-8')
            Map snapshot = readArchive((TarInputStream)owned, revision, deadline)
            // Finish the gzip stream so truncated responses or invalid checksums cannot pass.
            byte[] remainder = new byte[8192]
            int count
            while ((count = expanded.read(remainder)) != -1) {
                checkBudget(deadline)
                require(count > 0, 'SOURCE_EMPTY_READ')
                for (int i = 0; i < count; i++) {
                    require(remainder[i] == 0, 'SOURCE_TRAILING_CONTENT')
                }
            }
            checkBudget(deadline)
            return snapshot
        } finally {
            try { owned?.close() } finally { connection.disconnect() }
        }
    }
}
