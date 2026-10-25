# Step 5.1 — Source/runtime dependency scans and gate

> Historical pre-merge checkpoint. Implementation `893e764` and follow-up `76b0f7d`
> were subsequently approved, merged/published, and verified through automatic main
> build #6 (316 tests, passing scans, 25 artifacts). The
> [post-merge evidence](step-01-scm-verification.md) supersedes pending-review statements
> below without changing these candidate runs' provenance.

## Scope and actual implementation

Verified **25 October 2026 UTC** on `task-05/step-01-source-dependency-scans`.
Implementation **`893e764943c7c7ba38173291354fbcbf691a9fa0`** is local and unmerged.
Public main remains **`dfa0cc010744baafe3f8d7cf601b608e643faf37`**; the step branch has
not been published. Normal main CI still has the previous pipeline and 260-test suite.

The user approved the scan scope/failure policy and, after seeing actual findings,
explicitly approved direct use of defusedxml in Jenkins tooling. The
[runbook](../../docs/runbooks/source-security.md) defines exact scope, network/time limits,
report contracts, severity interpretation, warnings, and remediation workflow.

- Locked development tools: **Bandit 1.9.4**, **pip-audit 2.10.1**, **defusedxml 0.7.1**.
  Existing dependency versions and application runtime requirements are unchanged.
- Bandit scans all **22 Python files** under application, scripts, and Jenkins tooling.
  All findings are reported; MEDIUM/HIGH at any confidence blocks. No suppressions,
  excluded rule IDs, or comparison baseline were introduced; nosec is ignored.
- Exactly **14 runtime dependencies** are exported/audited. No pip resolution/install,
  automatic fix, ignored advisory, or skipped package is accepted. Any advisory blocks.
- The five-minute Security scans stage precedes Package and Local image export.
  Always-archived diagnostics include eight new allowlisted reports. Scanner/report errors
  cannot be accepted as a passing gate; a partial initial summary says `incomplete`.

## Initial findings and remediation

The [initial real Bandit report](step-01/initial-bandit.json) contains **12 MEDIUM,
HIGH-confidence B314 findings** and 17 LOW findings. All MEDIUM locations were XML
parsers in `bootstrap.py`, `verify.py`, `verify_ci.py`, and `verify_trigger.py` under
`ops/jenkins/`. These are scanner findings, not a claim that exploitation was demonstrated.

Their imports now use defusedxml's parser; XML construction remains standard-library
ElementTree where needed. Regression tests reject internal and file/network entity
declarations through the public job-configuration helper. No transaction API behavior,
request/response contract, application dependency, or deployed artifact was changed.

The final source scan reports **0 MEDIUM, 0 HIGH, 17 LOW**. Retained LOW rule counts:
B404=3, B603=6, B607=4, B405=2, B101=2. The approved policy allows these but does not hide
or declare them remediated. See [actual findings](step-01/success-bandit.json).
Both the [initial](step-01/initial-pip-audit.json) and
[candidate](step-01/success-pip-audit.json) dependency audits returned zero known advisories
for the 14 exact runtime pins. This is time-sensitive, not proof of universal absence of flaws.

## Real candidate Jenkins execution — no publication

A Git bundle containing the unpublished implementation was transferred to the existing
owned agent by the host operator. It was written exclusively to a unique `/tmp/` path,
not bind-mounted, served, or published. Its SHA-256 was verified on transfer and again
inside each review checkout before use. Public main was cloned first, providing the
bundle prerequisite; shell Git then fetched the bundle and checked out the exact candidate.

The manual sandboxed jobs used candidate Jenkinsfile plus this explicit checkout wrapper.
The failure case additionally restored four original files immediately before scanning.
Candidate and executed script hashes, base/candidate revisions, source-file hashes, and
bundle digest are recorded. **These jobs do not prove normal Jenkinsfile-from-SCM loading**
of the unpublished implementation, nor automatic triggering of this new pipeline.

| Review job, build 1 | Actual result | Tests | Scan result | Artifact/gate result |
| --- | --- | --- | --- | --- |
| `finsecure-ci-scan-review-success-20261025074032` | SUCCESS | 316 pass, 0 fail/skip | 17 LOW; zero blocking findings/advisories | 25 artifacts downloaded; package/image checksums and image configuration verified |
| `finsecure-ci-scan-review-blocked-20261025074130` | FAILURE | 316 pass, 0 fail/skip, before restoration | 12 MEDIUM + 19 LOW; dependency audit still passes | Scan exit 1; Package and Local image export skipped; 15 pre-package/report artifacts retained |

Both runs used the real Python agent and real PyPI advisory service. Application executable
coverage remained **125/125 lines, 28/28 branch outcomes**; quality gate **INACTIVE**.

### Meaning of the blocked run

The isolated wrapper used `git show` to restore the four original parser files from
reviewed main **after tests and before scanning**. That deliberately changes the scan input,
not the recorded candidate commit. Each scanned file hash was compared against the expected
candidate or restored-base Git blob. Bandit statically inspected the original code; none of
those old helpers was executed. No vulnerable dependency was added and no resulting image
or package was created. The implementation branch remains remediated.

This is a real source-finding gate, not forged scanner JSON, a fake exit code, or a failed
pytest case. It does **not** satisfy the later separate HIGH/CRITICAL vulnerable-image or
release/deployment demonstration. There are no publication/deployment stages to test yet.

## Tests, diagnostics, cleanup, and limitations

**316 host tests passed**, including 56 additions: XML entity rejection, strict runtime
exports, severity/confidence policy, skipped/missing/inconsistent reports, nonzero tool
errors, timeouts/shared budget, stale-output removal, continued dependency checking after
source findings, and verifier lock/report checks. External processes are mocked in those
unit cases; no live advisory-service outage was induced. Real success/finding-block results
are separately documented above.

Ruff lint/format, package build, and Compose validation passed. The new development lock
retains all previously resolved package versions. Host and agent use Python 3.14.7.
Known unsuppressed diagnostics include Starlette's existing HTTPX deprecation, pip-audit's
recommendation to hash requirements, and existing BuildKit optional-feature notices.
The advisory-only plain pin export is tied to the hashed lock; installations remain locked.

An initial report validator failed closed on Bandit's `./` filename prefixes; a narrow
normalization fix and regression test corrected it. An explicit `/dev/null` INI caused a
configuration warning and was removed: explicit file targets do not discover directory INI
files in this pinned Bandit version. An operator readiness check initially requested too
shallow a Jenkins API response; an explicit field query established the agent was idle
before bundle transfer. These were corrected, not retried as failing application builds.

Both review jobs were disabled with histories/artifacts retained. The owned agent bundle
was removed after its digest and agent idleness were checked. Host bundle/binary downloads
remain ignored local files. Main polling remains `H/5 * * * *`; its latest build is still #5.
The Step 4.4 demo remains disabled with four builds. No registry/cloud credentials, pushes,
resource provisioning, or deployment commands were introduced. No new exported image was
loaded/smoke-tested in this step; earlier runtime proof is image/revision-specific.

## Curated evidence

- [Success console](step-01/success-console.txt), [verification and all hashes](step-01/success-verification.json),
  [gate summary](step-01/success-security-summary.json).
- [Blocked console](step-01/blocked-console.txt), [verification](step-01/blocked-verification.json),
  [gate summary](step-01/blocked-security-summary.json), [actual blocking findings](step-01/blocked-bandit.json).
- [Candidate/bundle provenance](step-01/candidate.json), [executed harness](step-01/check-ci.py.txt),
  [cleanup/status checks](step-01/cleanup.json), [implementation hashes](step-01/configuration-sha256.txt).
- [Final host checks](step-01/host-checks.txt), [final host scan summary](step-01/host-security-summary.json).
  All implementation hashes match the Jenkins-tested commit; 306 repository text/source
  artifacts were checked privately against known live credentials, and changed-document
  links were verified before commit.
- Both runs' JUnit/Coverage APIs, tool versions, exact requirements and scanner diagnostics
  are retained in [step-01/](step-01/); binaries and raw generated test XML remain in
  Jenkins/ignored local storage. Known live credentials are checked privately before commit.

The harness ran as `PYTHONPATH=ops/jenkins uv run --locked python reports/check-step51-ci.py
success` and `... blocked`. It follows each invocation's queue item, never a racy last-build
selection. An explicit `--existing-job` inspects an exact matching script without triggering
another run. The local authenticated Jenkins URLs are not hosted evaluator links. Curated
text replaces the host repository path with `<repository>` and normalizes trailing whitespace.

**Review gate:** approve before merging/publishing. Then verify the normal SCM-triggered
pipeline with 316 tests and 25 artifacts. Image scanning, full release/deployment blocking,
secret-management expansion, and Step 5.4's separate demonstration remain pending.
