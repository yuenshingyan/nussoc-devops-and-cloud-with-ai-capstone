# Step 5.1 — Normal SCM-triggered scan gate verification

Following approval, implementation `893e764` and its evidence follow-up
**`76b0f7dd02e835ed69469dcfa208b8d85f1101ed`** were fast-forward merged and atomically
published to main and `task-05/step-01-source-dependency-scans`. The original-code
restoration used only for the candidate failure probe was **not** merged.

## Actual normal build

**finsecure-ci #6 SUCCESS**, verified **25 October 2026 07:56:13 UTC**.
The prior completed main build was #5; queue was empty and polling configured before
publication. Build #6's sole cause is `hudson.triggers.SCMTrigger$SCMTriggerCause`.
The observer used GET requests only—no manual build, forced polling, or retry.

The console records `Obtained Jenkinsfile from git`, the exact published revision above,
and execution on `finsecure-python`. Jenkinsfile SHA-256:
`06e324d4fd3e2b300ff7173b2bc8a939db74eb8998f051198f2c53d125c0b96b`.
Unlike the pre-merge jobs, this used **normal Pipeline-from-SCM**, without a local bundle,
checkout wrapper, or restored files.

- **316 passed, 0 failed, 0 skipped.** Ruff, packaging, and local image export succeeded.
- Bandit scanned **22 Python files**, reporting **17 LOW, 0 MEDIUM, 0 HIGH**. The gate
  passed under the approved policy; LOW findings were retained, not suppressed.
- pip-audit queried the real PyPI service for **14 exact locked runtime dependencies**:
  **zero known advisories returned**, no skips or automatic fixes. This is a dated result.
- The gate's inventory and every source hash match the published Git tree; the lock hash
  matches both Git and the build metadata. Downloaded raw reports were revalidated against
  gate counts/exit statuses and the complete exported pin set.
- Application coverage: **125/125 executable lines, 28/28 branch outcomes**. Coverage
  quality gate remains **INACTIVE**, separate from the new security acceptance policy.
- All **25** allowlisted artifacts were downloaded. Wheel/sdist hashes matched the manifest
  and included the application; image archive checksum/configuration/digest, non-root user,
  ARM64 platform, exact revision label and unique build tag were verified.

### Exported image (not a release)

| Field | Verified value |
| --- | --- |
| Archive | `images/finsecure-pay.tar.gz`, 47,141,398 bytes |
| SHA-256 | `8cd52de7fa121f41e589d01f6b9238d2efbfa7537c0ce9f299390857ad87cb11` |
| Configuration image ID | `sha256:c397c6dfb6f18c7f263004b44e7eafa45fbeb6152a96242322f7a0e1a34070a3` |
| Local tag | `finsecure-pay-ci:jenkins-finsecure-ci-6` |
| Platform | `linux/arm64` |

This image was **not loaded, smoke-tested, scanned with Trivy, published, or deployed**
in this follow-up. Source/dependency scan success is not an image-security attestation.
Existing public releases and their earlier runtime evidence remain distinct.

## Evidence and retained limitations

- [Actual sanitized console](step-01-scm/console.txt).
- [Verification, SCM cause, scan provenance, all artifact hashes](step-01-scm/verification.json).
- [Scan summary](step-01-scm/security-summary.json), [Bandit findings](step-01-scm/bandit.json),
  [dependency results](step-01-scm/pip-audit.json), [exact pins](step-01-scm/runtime-requirements.txt),
  and [tool versions](step-01-scm/security-tools.txt).
- [JUnit summary](step-01-scm/junit-api-summary.json), [Coverage API](step-01-scm/coverage-api.json).
- [Before-publication baseline](step-01-scm/before.json) and
  [executed GET-only observer](step-01-scm/check-main.py.txt), run with
  `PYTHONPATH=ops/jenkins uv run --locked python reports/check-step51-main.py`.
- [Pre-merge successful and genuinely blocked scan runs](step-01-source-scans.md).

The observer allows 20 minutes and rejects extra builds rather than selecting a successful
retry. Both Step 5.1 review jobs remain disabled; the Step 4.4 demo remains disabled with
four retained builds. Credentials, history and normal main polling were not reconfigured.
The [local build URL](http://127.0.0.1:8080/job/finsecure-ci/6/) requires this machine and
authentication; it is not an externally hosted evaluator endpoint. Binary downloads/raw
test XML remain in Jenkins/ignored `reports/step51-main-6/`. Curated text normalizes trailing
whitespace; known live credential values are checked privately before publication.

Unsuppressed warnings remain: Starlette/HTTPX deprecation, pip-audit's recommendation for
hashed requirement exports, and existing BuildKit optional-feature notices. The exact-pin
advisory lookup is tied to the hashed lock; installations use locked uv, without weakening
TLS or silently accepting scanner errors. See the [policy](../../docs/runbooks/source-security.md).

**Status:** Step 5.1 is reviewed, merged, published, and normally SCM-verified. This
follow-up is documentation/evidence only, not the source revision executed by #6.
Image scanning, release credentials, registry/cloud delivery, and the later HIGH/CRITICAL
vulnerability demonstration remain pending. No Step 5.2 implementation has started.
