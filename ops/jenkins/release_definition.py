"""Assemble reviewed local release code, never code from CI artifacts or fetched Git data."""

from base64 import b64encode
from hashlib import sha256
from pathlib import Path
from stat import S_ISREG

from bootstrap import ROOT

HELPERS = (
    "release-job.groovy",
    "release-source.groovy",
    "release-transfer.groovy",
    "release-preparation.groovy",
    "release-verification.groovy",
)
TOOLS = (
    "scripts/release_artifacts.py",
    "scripts/release_archive.py",
    "scripts/image_scan.py",
    "scripts/security_scan.py",
    "ops/jenkins/image_archive.py",
)
SELECTION_BOUNDARY = "// No node, credential binding, upstream trigger, artifact execution"
FILE_LIMIT = 1024 * 1024
CHUNK_SIZE = 16000


def source_bytes(root: Path, name: str) -> bytes:
    """Read one bounded regular local source, rejecting links and paths outside the review root."""
    path = root.resolve() / name
    info = path.lstat()
    if (
        path.resolve() != path
        or not path.is_relative_to(root.resolve())
        or not S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or not 0 < info.st_size <= FILE_LIMIT
    ):
        raise ValueError("RELEASE_LOCAL_SOURCE_INVALID")
    data = path.read_bytes()
    if len(data) != info.st_size:
        raise ValueError("RELEASE_LOCAL_SOURCE_CHANGED")
    return data


def encoded_expression(data: bytes) -> str:
    """Avoid JVM constant-string limits without interpolating source text into Groovy."""
    if not data or len(data) > FILE_LIMIT:
        raise ValueError("RELEASE_TOOL_SIZE_INVALID")
    text = b64encode(data).decode("ascii")
    chunks = [
        "'" + text[offset : offset + CHUNK_SIZE] + "'" for offset in range(0, len(text), CHUNK_SIZE)
    ]
    return "[" + ",".join(chunks) + "].join('')"


def verifier_bundle(root: Path) -> str:
    """Embed only fixed reviewed tooling, with independent post-write hash readback."""
    sources = []
    hashes = []
    for name in TOOLS:
        data = source_bytes(root, name)
        sources.append("'" + name + "':" + encoded_expression(data))
        hashes.append("'" + name + "':'" + sha256(data).hexdigest() + "'")
    return (
        "class FinsecureVerifierBundle {\n"
        "    static final Map SOURCES = [" + ",".join(sources) + "].asImmutable()\n"
        "    static final Map HASHES = [" + ",".join(hashes) + "].asImmutable()\n"
        """
    @NonCPS
    static void install(FilePath scratch) {
        FilePath tools = scratch.child('tools')
        FinsecureCandidateSelection.require(!tools.exists(), 'RELEASE_TOOL_DIRECTORY_EXISTS')
        tools.mkdirs()
        tools.chmod(0700)
        ['scripts', 'ops', 'ops/jenkins'].each { String name ->
            tools.child(name).mkdirs()
            tools.child(name).chmod(0700)
        }
        SOURCES.each { String name, String encoded ->
            FilePath target = tools.child(name)
            FinsecureArtifactTransfer.writeControl(target, Base64.decoder.decode(encoded))
            InputStream input = target.read()
            try {
                byte[] actual = input.readNBytes(1024 * 1024 + 1)
                String hash = MessageDigest.getInstance('SHA-256')
                    .digest(actual).encodeHex().toString()
                FinsecureCandidateSelection.require(
                    actual.length <= 1024 * 1024 && hash == HASHES[name],
                    'RELEASE_TOOL_HASH_MISMATCH')
            } finally { input.close() }
        }
    }
}
"""
    )


def assemble_definition(root: Path = ROOT) -> str:
    """Build a verification-only definition from fixed local inputs, with no release actions."""
    imports = set()
    bodies = []
    for name in HELPERS:
        source = source_bytes(root, "ops/jenkins/" + name).decode("utf-8")
        if name == "release-job.groovy":
            if source.count(SELECTION_BOUNDARY) != 1:
                raise ValueError("RELEASE_SELECTION_BOUNDARY_INVALID")
            source = source.split(SELECTION_BOUNDARY, 1)[0]
        lines = source.splitlines()
        imports.update(line for line in lines if line.startswith("import "))
        bodies.append("\n".join(line for line in lines if not line.startswith("import ")))
    flow = source_bytes(root, "ops/jenkins/release-flow.groovy").decode("utf-8")
    return "\n\n".join(["\n".join(sorted(imports)), *bodies, verifier_bundle(root), flow])
