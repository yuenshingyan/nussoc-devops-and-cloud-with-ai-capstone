# Image security — Step 5.2 preflight checkpoint

**Partial implementation, not a completed Jenkins image gate.** The user approved the
policy below and tool installation. Verified Trivy is installed on the local ARM64 agent;
the current image's real operator-side preflight produced blocking findings. Application
base changes and exceptions have not been made. Jenkinsfile is still unchanged from
Step 5.1: its 15-minute global limit and image-archiving behavior have not yet been replaced.

## Approved policy to implement

- Pin Trivy **0.76.1** and verify its release signatures before installing it. Use
  Cosign **3.1.4** for verification, not as an application/runtime dependency.
- Scan the exact exported archive for OS/library vulnerabilities without loading it or
  accessing a Docker daemon. Report all severities; block HIGH/CRITICAL including unfixed
  findings. Unsupported/end-of-life OS, scanner errors and incomplete scans also block.
- No ignore lists or automatic exceptions. Existing source/dependency gates remain intact.
- Obtain the vulnerability DB only from `ghcr.io/aquasecurity/trivy-db:2`, using a new
  temporary cache each build. Require an aware UTC UpdatedAt within the preceding
  24 hours; no stale-cache or mirror fallback. No automatic job retries.
- Allow five minutes for DB download and five minutes for scanning; the future pipeline
  global timeout will be 30 minutes. Keep package archiving unchanged; archive the image
  only after its image gate passes. Retain available scan diagnostics on failure.
- No registry publication/cloud deployment, automatic base-image changes, or bypasses.
  If the existing image blocks, report findings and agree remediation first.

## Actual tool verification and installation

Trivy's historical supply-chain compromise is documented in the
[official advisory](https://github.com/aquasecurity/trivy/security/advisories/GHSA-69fq-xp46-6x23).
Do not use mutable `latest` tags or treat checksums alone as independent provenance proof.

The operator downloaded assets from the immutable official
[Trivy v0.76.1](https://github.com/aquasecurity/trivy/releases/tag/v0.76.1) and
[Cosign v3.1.4](https://github.com/sigstore/cosign/releases/tag/v3.1.4) releases, with
HTTPS-only redirects, 15-second connect limits and 300-second download limits:

1. Match asset SHA-256 values against official GitHub release metadata, and the Trivy
   archive against the release checksum file.
2. Before executing Cosign, use the existing **GitHub CLI 2.95.0** to verify its immutable
   release-asset attestation. Verify Trivy's release-asset attestation independently too.
3. Use verified Cosign to verify Trivy's Sigstore bundle with the exact issuer
   `https://token.actions.githubusercontent.com` and identity
   `https://github.com/aquasecurity/trivy/.github/workflows/reusable-release.yaml@refs/tags/v0.76.1`.
4. Pin the verified Linux ARM64 archive digest in the agent Dockerfile. Extract only its
   unique regular `trivy` member, and verify the installed binary digest against that member.

The build uses the verified archive SHA-256:
`e174dff2a6dba5e3ae41f8d0537a6324405bd08132497340304c6b20e0f16a1f`.
The installed binary SHA-256 is
`b422130ea54e53e142e65c838662e48919ce9c3f23f17d80066b43e70550cb85`.
Agent image `finsecure-jenkins-agent:step-05-02` is
`sha256:f51d2a954718ca4b6948e8bde555d77fdf326b3715d08cff28531c8714fe2fe9`.
The build explicitly rejects non-ARM64 targets; this does not add AMD64 CI support.

Cosign remains an ignored local verification binary, not a globally installed package or
application-image component. Agent/controller credentials, named volumes and history were
preserved. UID 1000, dropped capabilities, no-new-privileges and volume-only mounts remain;
there is no new host socket, privileged container, published port, or cloud service.

The existing stack was already stopped (exit 255) when the first API check ran. The check
failed before an agent rebuild/replacement. The owned controller/builder were restarted,
then the agent was built and replaced while idle. Its reconnection, binary digest and
credential preservation were verified. The shutdown cause was not established.

## Actual preflight result

On **25 October 2026**, the operator scanned the exact downloaded image from normal
`finsecure-ci` **#7**, source `6c762936a51a95834f1320a2383869c2aef1a230`, on the agent.
The image was not loaded or run. Its archive checksum and Trivy-reported configuration
image ID matched the previously verified export:
`sha256:577738d786429e319a04472d99a0c031c5eb49f70055d89d9e1785af988dcdac`.

The DB download took approximately **32 seconds**, scanning approximately **4 seconds**.
DB UpdatedAt was `2026-10-25T12:57:48.463991102Z`, approximately 1 hour 41 minutes old.
The temporary archive/cache/configuration directory was removed after results were captured.
The scan used one worker, explicit vulnerability-only scanning, offline dependency analysis,
no Java DB update, an empty Docker credential directory and empty explicit config/ignore files.

Results: **70 HIGH, 6 CRITICAL, 111 MEDIUM, 100 LOW, 4 UNKNOWN finding occurrences**.
The 76 blocking occurrences cover **29 distinct advisory IDs**; **63 occurrences have no
listed fix**. These are findings, not demonstrated exploits or 76 distinct CVEs.

Trivy's raw exit was **0** because this was an all-severity report-generation preflight;
it does **not** mean the approved policy passed. That policy **would block this image**.
No Jenkins gate or successful image-security release has been demonstrated yet.

The scanner identified Debian 12.15, 97 OS packages and 34 Python-package records. The
Python findings include certifi, msgpack, setuptools and urllib3 records attributed to an
embedded SBOM in a base-image layer, not simply the 14 application runtime pins audited
in Step 5.1. Trivy explicitly warned that third-party SBOM data may be inaccurate and that
some severities came from other vendors. Retain those caveats and investigate package
presence/reachability and vendor status; do not silently remove SBOMs to hide findings.

## Next decision

Do not change the application Dockerfile or weaken the policy based only on a scanner count.
First agree candidate remediation scope: updated digest-pinned Python 3.14 base images,
possibly a newer Debian variant, and removal of genuinely unnecessary runtime packaging
tools. Preserve the API contract and reverify runtime behavior/platforms when changed.
A newer base is not guaranteed to clear every finding, especially those without fixes.

Evidence: [tool verification and initial findings](../../evidence/task-05/step-02-preflight.md).
Pipeline integration, automated error/report validation, passing-image demonstration and
normal SCM verification remain pending. Current public release images were not individually
rescanned, replaced or published by this preflight.
