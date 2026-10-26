# Image security — Step 5.2 checkpoints

**Local candidate implementation; review/publication and normal SCM verification pending.**
The user approved the policy, verified tooling, candidate experiments, and adoption of the
tested musl-based Alpine option. The root Dockerfile now uses that pinned base with whole
pip/ensurepip removal. Jenkinsfile now has a 30-minute global limit and an image gate
between export and image archival. This does not authorize registry/cloud delivery.
Implementation `e920cb5` passed local candidate Jenkins verification: 410 tests in each
run; Alpine passed with 33 artifacts, the controlled Debian comparison blocked 61 HIGH /
2 CRITICAL with 32 artifacts and no image, and an invalid-checksum probe returned error 2
with reports/packages but no image. See [actual evidence](../../evidence/task-05/step-02-image-gates.md).
These were unpublished inline candidate jobs, not normal SCM-loaded/triggered proof.

## Approved policy

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

## Approved remediation study and next decision

The user approved testing updated digest-pinned Python 3.14 bases and removal of genuinely
unnecessary runtime packaging tools. The operator tested Python 3.14.9 candidates with the
entire pip installation and ensurepip module/bundled wheels removed, not just their SBOMs.
The dependency lock and API contract were unchanged; OS package inventories were retained.

- Debian 12.15: 61 HIGH / 2 CRITICAL occurrences remain.
- Debian 13.7: 44 HIGH / 0 CRITICAL remain.
- Alpine 3.24.3: no known findings at any severity on ARM64 or AMD64, with 30 OS packages
  and 15 Python package records identified on each. Fresh DB/cache used for every scan.
- Each Alpine architecture passed **316 tests**, using the candidate's installed
  application/runtime packages with separate locked development tools and no test network.
  HTTP smoke/security/shutdown and 0.5 CPU / 256 MiB local safeguard checks also passed.
  AMD64 execution was emulated; no Kubernetes or rootless Jenkins build is implied.

**Approved adoption, now in the root Dockerfile:** Python 3.14.9/Alpine 3.24 at index
`sha256:dbeb11d16bb95c3a7e3c25c842cb9f20cbc8c18f8be0461a4a0dcc861ad386a0`,
plus the tested whole-tool removal and equivalent non-root account setup. This changes
**glibc to musl** for the application builder/runtime, not the Jenkins agent. Future
native dependencies must retain musllinux wheel/runtime compatibility. Zero reported
findings are time-bound scanner results, not a guarantee of no vulnerabilities.

Evidence: [tool verification and initial findings](../../evidence/task-05/step-02-preflight.md)
and [candidate comparison/compatibility](../../evidence/task-05/step-02-remediation.md).
The previous checkpoint's pending-adoption statements are historical, superseded by the
subsequent approval. Public release images were not individually rescanned, replaced or
published by these experiments.

## Gate implementation and report contract

Run only on the verified ARM64 agent after exporting this checkout's image:

```sh
uv run --locked python -m scripts.image_scan \
  --revision "$(git rev-parse HEAD)" --tag "finsecure-pay-ci:${BUILD_TAG}"
```

`scripts/image_scan.py` verifies the export checksum, unique image/config, source label,
ARM64 platform and UID/GID 10001. It checks the installed Trivy binary against the verified
release digest, exports runtime pins offline from the lock, then uses separate temporary
configuration/ignore/Docker-config/cache paths. `TRIVY_*` environment overrides are removed.
No tool update, ignore rule, VEX override or registry credentials are supplied.

The database operation has a shared 300-second budget including tool/version and locked-pin
export; scanning has a separate 300-second budget. Freshness is checked before and after
scanning. A successful download never permits fallback to another database. The wrapper
returns **0 passed, 1 HIGH/CRITICAL or EOL policy block, 2 handled execution/identity/report
error**. Unexpected exceptions also fail the shell stage; an incomplete summary is not a pass.
Trivy itself generates an all-severity report with exit code 0, except `--exit-on-eol 2`;
the wrapper validates that result and applies the actual severity policy.

Validation requires schema/tool identity, a fresh report timestamp, matching image identity,
and complete nonempty OS/Python inventories. Current supported scope is Alpine 3.24 and
Debian 12/13 (including controlled comparison cases); other families/releases fail closed
pending review. The pinned scanner's EOL result is enforced independently. Every locked
runtime dependency and the project must appear at the expected version in `/opt/venv`.
Additional identified packages are still scanned, not ignored. Inventory completeness is
relative to the expected OS/Python targets; it does not establish detection of every
unidentified embedded component or complete coverage of the source-built CPython
interpreter/standard library. No exploitability or vulnerability-free claim is made.
Findings must name an inventoried
package; Debian epoch/release fields are reassembled without discarding version identity.
Unknown severity names, duplicate JSON keys, modified/ignored findings, missing reports,
scanner failures, changed inputs and stale/future databases fail closed.

Eight new allowlisted artifacts are attempted from pipeline `post/always`:
`image-security-summary.json`, `image-security-tools.txt`, `image-security-export.txt`,
`image-runtime-requirements.txt`, `trivy-db.json`, `trivy-db.txt`, `trivy.json`, `trivy.txt`
(all under `reports/`). The summary binds available reports by SHA-256 and identifies the
exact input archive/source/lock. Early failures may have only partial diagnostics.
Package archival remains before image building; image archival occurs only after the
wrapper exits 0. The blocked image can remain in its isolated review workspace/builder
cache, but is not a downloadable image artifact or a deployed workload. Existing manual
retention rules still apply. The three verified review workspace image archives were
subsequently removed with identity/hash checks; build history and BuildKit cache remain.
Completed calls clean their temporary scanner directory; forcible process/container
termination may leave an owned directory under `/tmp/finsecure-image-scan-*`. Inspect it
only while the agent is idle before explicit removal; never reuse it as a fallback cache. Normal success now has 33 artifacts; a complete vulnerability
block retains 32 (including packages and reports, excluding the image).

The exact passing Jenkins ARM64 export was also loaded by the operator and passed HTTP,
security, shutdown and constrained-runtime checks. No scanner daemon access, public image
release or cloud deployment was added. Normal main remains at build #7 until approval.

Tests exercise severity/fix boundaries, EOL, unsupported OS, timestamps, inventory gaps,
version identity, binary/archive integrity, scanner errors/timeouts, stale outputs and
cleanup. External tools are mocked only in unit tests; live Jenkins evidence is separate.
No automatic retries, vulnerability exceptions or coverage threshold were introduced.
