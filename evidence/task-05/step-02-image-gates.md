# Step 5.2 — Image gate implementation and candidate Jenkins verification

**26 October 2026 UTC.** Implementation:
**`e920cb57eeda98bbb0c222a690c27a38505e0028`**, on
`task-05/step-02-image-security-gates`. **Local review only; not merged or published.**
The user approved adopting the tested Python 3.14.9/Alpine 3.24 base and whole pip/ensurepip
removal, then completing the previously approved fail-closed image gate.

## Implemented scope

- Root Dockerfile now uses the approved multi-platform Alpine index
  `sha256:dbeb11d16bb95c3a7e3c25c842cb9f20cbc8c18f8be0461a4a0dcc861ad386a0`.
  The application builder/runtime change to musl; the Jenkins agent remains unchanged.
  Runtime pip, its vendored code, and the ensurepip module/bundled wheels are removed.
  Application code, API contract, dependency versions and `uv.lock` are unchanged.
- `scripts/image_scan.py` binds the scan to the exact Docker export, source label, config
  digest, platform, user and lock. It verifies the pinned Trivy executable, uses fresh
  per-run official-GHCR database/cache/configuration, and validates complete OS/Python
  inventories, findings, timestamps and tool/report identity. See the
  [full policy/report contract](../../docs/runbooks/image-security.md).
- HIGH/CRITICAL, including unfixed findings, or EOL returns 1. Handled scanner, identity,
  input or report errors return 2. Only a complete pass returns 0. No suppressions,
  stale fallback, automatic job retries or release credentials were introduced.
- Jenkins global budget is 30 minutes. The image gate runs after local export and before
  image archival, with five-minute database and scan budgets. Package archival remains
  unchanged. Eight new report names are allowlisted in pipeline `post/always`.
- `verify_ci.py` recognizes and binds the new reports to the archived image/source/lock.
  **94 new regression cases**, for **410 total tests**, cover policy boundaries, complete
  reports, stale outputs, versions, failures/timeouts and diagnostic retention.

The initial parser comparison correctly failed closed on real Debian reports whose
package epoch/upstream/release are separate fields. The parser now reassembles those
fields explicitly, with regression coverage; no vulnerability was discarded to fix this.

## Actual Jenkins results

These were **manual, sandboxed inline candidate jobs**, not normal Pipeline-from-SCM or
SCM-trigger evidence. Each checked out public main `6c76293`, verified the transferred
local Git bundle checksum, fetched the unpublished candidate, detached at `e920cb5`, and
confirmed its revision. Candidate and executed-wrapper hashes are recorded separately.
No branch publication was needed. [Transport provenance](step-02-gates/candidate.json).

| Job (each build #1) | Result | Tests | Image gate | Artifacts | Image archived |
|---|---|---:|---|---:|---|
| `finsecure-ci-image-review-success-20261026113827` | SUCCESS | 410 passed | passed, no known findings | 33 | yes |
| `finsecure-ci-image-review-blocked-20261026114149` | FAILURE | 410 passed | 61 HIGH / 2 CRITICAL, exit 1 | 32 | no |
| `finsecure-ci-image-review-error-20261026114904` | FAILURE | 410 passed | invalid checksum, exit 2 | 25 | no |

All three passed source gates: **19 LOW, no MEDIUM/HIGH**; 14 locked runtime dependencies
had no known advisories returned. Coverage remained **125/125 lines and 28/28 branch
outcomes**, with no coverage threshold. The two extra LOW findings relative to Step 5.1
are the new subprocess import/use; LOW findings remain visible, not suppressed.

### Passing candidate

The exact candidate Jenkinsfile built/exported with the existing rootless BuildKit worker,
then scanned that archive on the non-root agent without Docker daemon access. Trivy
identified **Alpine 3.24.3, 30 OS packages and 15 Python package records**. Every locked
runtime pin and the application were present. No known findings at any severity were
reported. DB age was approximately **4 hours 25 minutes**, within the approved 24 hours;
the complete image gate took approximately **42 seconds**.

- Image ID: `sha256:9007cf91a9090b2bec035267e6ec9663a7f7bb9577aafc5b201f1230159ec1d4`.
- Archive SHA-256: `2710de69812fea63a68e6ee6d6e4d9f192606ce92e43d7e6f9325f6bcd215629`.
- [Verified build/artifact record](step-02-gates/success/verification.json),
  [console](step-02-gates/success/console.txt),
  [gate summary](step-02-gates/success/reports/image-security-summary.json),
  [complete Trivy report](step-02-gates/success/reports/trivy.json).

This is a time-bound scan result, not proof of vulnerability-free software.

### Real vulnerability-blocked comparison

After the same tests, source scans and packaging, the isolated review wrapper replaced
**only its workspace Dockerfile** with the recorded Debian runtime candidate, setting its
base to pinned Python 3.14.9/Bookworm. It retained whole pip/ensurepip removal. The
Dockerfile checksum was checked and printed before export; the exact override is recorded
in the [verification record](step-02-gates/blocked/verification.json). Application/source
scanner files were unchanged and their hashes were checked against the candidate commit.
The image's source label denotes that application baseline plus this documented override,
not an unmodified candidate Dockerfile.

The actual scanner reported **61 HIGH, 2 CRITICAL, 99 MEDIUM, 91 LOW, 2 UNKNOWN
occurrences**. All 63 blocking occurrences lack listed fixes. Trivy's report-generation
exit was 0; the validated wrapper returned **1**, failing Jenkins before image archival.
The image was **never loaded, run, published or deployed**. Source packages and all
available diagnostics remained archived as required.

- [Console](step-02-gates/blocked/console.txt),
  [gate summary](step-02-gates/blocked/reports/image-security-summary.json),
  [complete Trivy report](step-02-gates/blocked/reports/trivy.json).
- The earlier [vendor/SBOM caveats](step-02-remediation.md) still apply: scanner findings
  are not proof of exploitability. No vendor-status exception or ignore rule was used.

### Actual fail-closed input-error path

A third isolated wrapper changed `reports/image.sha256` to `invalid-checksum` after the
normal Alpine export. The real gate rejected that input with **exit 2**, retaining its
error summary and the earlier reports/packages but **no image artifact**. It did not
reach database download or Trivy execution, and created no fake scanner findings.

This proves the pipeline's error/nonzero archival boundary for a real integrity error;
**it is not a live database-outage or scanner-crash demonstration**. Those error/timeout
branches are covered by mocked external-tool tests.
[Record](step-02-gates/error/verification.json),
[console](step-02-gates/error/console.txt),
[error summary](step-02-gates/error/reports/image-security-summary.json).

## Exact passing export: operator runtime checks

After gate success, the operator downloaded, checksum-verified and loaded **that exact
passing Jenkins archive** into local Docker. This is a separate operator check, not a
Docker socket added to Jenkins or automatic deployment.

- [Load output](step-02-gates/operator-image-load.txt) and
  [runtime/tool inspection](step-02-gates/operator-runtime-tools.json): Python 3.14.9,
  musl pydantic-core, no pip/ensurepip/uv in the runtime.
- [HTTP smoke checks](step-02-gates/operator-image-smoke.json): health, accepted transaction,
  business rejection and schema rejection; actual PID 1 UID/GID 10001, read-only root,
  dropped capabilities, no-new-privileges, loopback-only HTTP, clean shutdown, removal.
- [Constrained runtime](step-02-gates/operator-image-constrained.json): 0.5 CPU, 256 MiB,
  no extra swap, 16 MiB writable `/tmp`, seccomp and zero capabilities; 25 accepted
  requests, rejection/health checks, no OOM, shutdown exit 0 and container removal.

This exact Jenkins image is **ARM64 only**. The previous independent Alpine candidate
study passed 316 application/tool tests and runtime checks on ARM64 and emulated AMD64;
that is separate evidence, not a claim that Jenkins built/scanned this new image on AMD64.
No Kubernetes execution, cloud exposure, load test or latency SLA is implied.

## Final host checks

[Host output](step-02-gates/host-checks.txt) and
[final verification](step-02-gates/final-checks.json): **410 tests**, Ruff lint/format,
wheel/sdist build, Compose validation and source/runtime dependency gates passed.
All 23 scanned source files remain identical to the verified implementation; the lock is
unchanged from main. Known live credentials were checked privately against 498 files,
and changed-document links were checked. Existing Starlette/HTTPX deprecation and
pip-audit hash-export recommendation remain visible, as does pip's root-user warning
in the runtime-image build. No blanket warning suppression was added.

## Preservation, corrections and pending review

[Cleanup/preservation record](step-02-gates/cleanup.json): all three jobs are disabled
with exactly one retained build each. The hash-checked agent bundle and each job's verified
workspace image archive were removed after verification. Archived reports/history remain;
the passing downloadable image was rechecked. Named volumes and BuildKit cache were not
pruned. Host review downloads and the loaded passing image remain local. Main is still
**#7**, and its archived image checksum was independently rechecked unchanged.

The first success observer attempted an unavailable `wfapi/describe` endpoint (404) after
the build had already succeeded. It was corrected to use console stage markers and actual
artifacts/reports, then inspected **the same #1 without rebuilding or installing a plugin**.
[Original observer error](step-02-gates/initial-observer-error.txt).

Reproduction/provenance: [success/blocked wrapper](step-02-gates/review-harness.py.txt),
[input-error wrapper](step-02-gates/error-harness.py.txt). These are retained historical
procedures, not instructions to rerun disabled jobs after their bundle was removed.
Verification hashes refer to original CI artifacts; limited text/colour/whitespace
normalization is recorded in [normalizations](step-02-gates/normalizations.json).
Binaries, database contents, image exports and package archives are not committed.

**Still pending:** approval to merge/publish this step, then a normal SCM-loaded/triggered
main build. Registry publication, Kubernetes delivery and the separate later security
steps remain deferred. Existing public release tags were not replaced or individually
rescanned; they must not be described as passing this new gate. Step 5.2's local checks
are not completion of the separate Step 5.4 demonstration or the deferred release pipeline.
