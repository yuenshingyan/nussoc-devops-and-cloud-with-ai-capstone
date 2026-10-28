# Step 5.4 — Actual isolated image blocking and remediation

**28 October 2026 UTC.** The user approved the two local manual runs and bounded
cleanup in the [scope](../../docs/runbooks/security-demonstration.md).
Job: `finsecure-security-demo-20261028144809`.
Both runs checked out **`43d6771faff9d269697f64cb70a87080d224f23c`**, the reviewed
application/lock/gate baseline. These are **sandboxed inline manual demonstrations**,
not normal Pipeline-from-SCM or SCM-trigger evidence.

## Actual results

| Build | Dockerfile configuration | Tests on Jenkins agent | Image gate | Result | Artifacts | Image archived |
| --- | --- | ---: | --- | --- | ---: | --- |
| #1 | Pinned Python 3.14.9/Bookworm candidate | 503 passed | 61 HIGH, 2 CRITICAL; wrapper exit 1 | FAILURE | 32 | No |
| #2 | Exact production Python 3.14.9/Alpine Dockerfile | 503 passed | No known findings; wrapper exit 0 | SUCCESS | 33 | Yes |

Both passed Ruff, source/runtime dependency gates and packaging. Bandit retained
21 LOW findings, no MEDIUM/HIGH; all 14 locked runtime dependencies were audited.
No pytest/audit warnings occurred. Coverage remained 125/125 lines and 28/28 branch
outcomes, without a coverage gate. Tests ran on the Jenkins agent, not inside the
completed application images.

[Blocked verification](step-04/blocked/verification.json),
[blocked console](step-04/blocked/console.txt),
[remediated verification](step-04/remediated/verification.json), and
[remediated console](step-04/remediated/console.txt).

## Real vulnerability block

The first run used the recorded historical Debian candidate with its base ARG set
to pinned Python 3.14.9/Bookworm. The complete
[effective Dockerfile](step-04/blocked-Dockerfile.txt) was checksum-checked immediately
before image export. Application, dependency lock and gate code remained unchanged.
The source label means the reviewed application baseline **plus the documented
Dockerfile override**, not an unmodified production Dockerfile.

Trivy returned a complete report with 2 UNKNOWN, 91 LOW, 99 MEDIUM, **61 HIGH and
2 CRITICAL occurrences**. Trivy's report-generation exit was 0; the real wrapper
applied policy and returned **1**, failing Jenkins before image archival. This was
not an integrity/scanner error or a synthetic finding.

Examples from the actual report (both have no listed fixed version):

| Advisory | Package | Installed version | Severity | Severity source |
| --- | --- | --- | --- | --- |
| CVE-2025-7458 | libsqlite3-0 | 3.40.1-2+deb12u2 | CRITICAL | nvd |
| CVE-2023-45853 | zlib1g | 1:1.2.13.dfsg-1 | CRITICAL | nvd |

All blocking advisory/package records are in the verification JSON; the
[complete scan](step-04/blocked/reports/trivy.json) and
[gate summary](step-04/blocked/reports/image-security-summary.json) preserve the
full context. Counts are package finding occurrences, not distinct vulnerabilities
or demonstrated exploits. Previous vendor/SBOM caveats still apply; no vendor-status
exception, ignored finding or altered severity was introduced.

The complete scan took a fresh official database whose age at scan start was about
1 hour 49 minutes. Its source/report/archive bindings were verified:

- Image ID: `sha256:b590bbfdeb56e0701c9dbb7611d0eb0f363114e9ea245f1aec6cf1019ef387db`.
- Archive SHA-256: `9794d71a9f9686aa671010494276a1c1060e8c24f493ad0722507a81682900f9`.
- Dockerfile SHA-256: `29cfcbb1bbe188905493b8b725634a7050e5d564c43877b97b13d6e8de19c698`.

Packages/reports were retained, but the artifact inventory contained **no image**.
The completed vulnerable image was never downloaded from Jenkins, loaded, started,
smoke-tested, published or deployed. Building necessarily executed base-image build
instructions; this is not a claim that no base-image process ran during construction.

## Remediation and successful gate

The second run restored the exact production Dockerfile from the same Git revision.
The [remediation diff](step-04/remediation.diff) switches the digest-pinned base to
Alpine and uses its equivalent non-root account setup. Whole pip/ensurepip removal
and the locked application are preserved. This re-demonstrates the remediation
already adopted in Step 5.2; it is **not** a new production fix or dependency upgrade.

The [effective restored Dockerfile](step-04/remediated-Dockerfile.txt) matches Git.
The fresh [complete scan](step-04/remediated/reports/trivy.json) reported no findings
at any severity, and the [gate](step-04/remediated/reports/image-security-summary.json)
passed. DB age at scan start was about 1 hour 50 minutes.

- Image ID: `sha256:d6d48bc918cd53193bee441aeb21a835f2caf400b4bffc0efb2fbbce49dff209`.
- Archive SHA-256: `564c1fd4567419db7bf37447d8ecadd7ba5ac7e6110d801222d4c0c9877980da`.
- Dockerfile SHA-256: `8e3037664ee1abe0ff135898535bac09f11d4e86d802ef86a19d98c849f29347`.

All 33 artifacts were downloaded and checksum-recorded. The archive was inspected
without loading it, confirming image/config identity, source label, platform and
non-root user. Source-file hashes and the lock-bound dependency export were checked
against the reviewed revision. Image report hashes and DB ages were also checked.
No application runtime smoke test was performed in this step; earlier runtime tests
remain separate evidence for their exact images. Zero findings is time-bound.

## Provenance, preservation and cleanup

The [operator harness](step-04/demo-harness.py.txt) and submitted
[blocked](step-04/blocked-pipeline.groovy.txt)/
[remediated](step-04/remediated-pipeline.groovy.txt) wrapper texts are retained with
hashes in the verification records. They use public exact-revision checkout and
only the documented checkout/assertion/Dockerfile wrapper changes. No Git bundle,
vulnerable public branch or new infrastructure was created. Each case ran exactly
once, manually; there were no retries.

The [cleanup record](step-04/cleanup.json) and
[procedure](step-04/cleanup-harness.py.txt) confirm:

- The single demo job is disabled with no triggers and exactly two retained builds.
- The remediation run's normal `deleteDir` checkout removed the earlier blocked
  workspace export. The remaining workspace archive matched the passing SHA-256;
  only that file was manually removed, leaving its images directory empty.
- The passing archived image remains downloadable and its checksum was rechecked.
  Host review downloads remain local outside Git. No binary archive is committed.
- Normal main CI remained at build **#15**, and its archived image manifest matches
  the [pre-demo baseline](step-04/main-before.json).
- Named volumes, build history and the shared BuildKit cache were preserved. That
  cache can retain layers from the controlled build; complete erasure is not claimed.

Known live Jenkins credential values were checked privately before saving artifacts.
Only reviewed text/JSON reports were curated; raw console credential values would
have been redacted. No credential, permission, agent/controller image or normal-job
configuration change was made.

## Final local checks and limits

[Host checks](step-04/host-checks.txt): Ruff lint/format, **503 tests with `-W error`**,
wheel/source build and source/runtime scans passed. The separate
[operator credential-boundary check](step-04/operator-boundaries.json) also passed.
Application/tool source and lock are unchanged from the reviewed baseline; this
step adds only scope/runbook/evidence files.

The approved local demonstration is verified; its branch/evidence were subsequently
reviewed, merged and published as `d76b713`. This proves **image-archival blocking and subsequent remediation**, not
registry/deployment blocking or cloud rollout. Those stages are not implemented.
No image push/deployment, cloud spending, credential rotation or later task occurred.
