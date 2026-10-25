# Source and runtime dependency security scans

## Approved policy and scope

Step 5.1 adds **Bandit 1.9.4**, **pip-audit 2.10.1**, and directly declared
**defusedxml 0.7.1** as development dependencies. Version ranges are in `pyproject.toml`;
exact resolutions/hashes are in `uv.lock`. Existing runtime package versions are unchanged.
The application image still installs only runtime dependencies, not these tools.

- Ruff remains the earlier code-check stage. Bandit scans every Python file under
  `src/finsecure_pay/`, `scripts/`, and `ops/jenkins/`, including operational helpers.
  Tests, generated reports, historical evidence copies, dependencies, and non-Python
  configuration are not Bandit targets. This is not an infrastructure/security audit.
- Report **all** Bandit findings. **MEDIUM/HIGH severity at any confidence** blocks;
  LOW findings remain visible but do not block. Severity and confidence are different
  fields; a static finding is not proof of exploitability.
- Export exact runtime pins using `uv export --locked --offline --no-dev --no-emit-project`.
  The local project is not a third-party PyPI dependency. Development/build dependencies,
  Python itself, OS packages, and other platforms' dependencies are not audited by this gate.
- pip-audit uses PyPI's vulnerability service with `--no-deps --disable-pip --strict`:
  no fresh dependency resolution, package execution/installation, automatic upgrade,
  ignored advisory, or skipped dependency is accepted. The report must contain every
  exact exported package/version once. **Any known advisory blocks**, even without a
  severity score or available fix. Advisory counts are occurrences across packages.
- Only public package names/versions are sent for advisory lookup, not application
  source or credentials. HTTPS certificate verification is not disabled. Each scan owns
  a fresh temporary HTTP cache, removed on completion; it does not reuse the pip cache.
  Advisory availability/freshness still depends on the remote service.
- No automatic exceptions or retries. Bandit `--ignore-nosec` prevents inline comments
  from silently disabling this gate. There is no skip list or baseline suppression.
  A future exception requires a separately reviewed policy/code change and rationale.

## Running and interpreting the gate

From the repository root:

```sh
uv sync --locked
uv run --locked python scripts/security_scan.py
```

The Jenkins **Security scans** stage runs after tests/report publication and before
**Package** and **Local image export**. Its five-minute limit is in addition to the
existing global fifteen-minute pipeline limit (after agent allocation). Locally, scanner
subprocesses share a **300-second monotonic budget**. PyPI requests have a **15-second
socket timeout**. These are execution limits, not an uptime or laptop-suspend SLA.
There are no new background tasks or process retries.

Exit codes: **0** complete passing gate; **1** complete report with blocking findings;
**2** handled execution/report error. An unexpected exception or interrupted run also
fails the build; an initial `incomplete` summary is never a pass. A pipeline-level timeout
may interrupt the writer, so retain partial diagnostics and inspect the actual build result.

Both scanners are attempted within the shared budget, including after source findings.
Missing/malformed reports, skipped files/dependencies, unexpected tool exit status,
inventory mismatches, or export errors cannot become successful results. The strict pin
parser supports the current lock's plain canonical package names and exact versions;
new markers, URLs, editable requirements, or other syntax fail closed until reviewed.
Bandit's documented `./` file prefix is normalized only for inventory comparison.

The gate replaces only its eight named reports under `reports/`. Jenkins starts with a
clean workspace; previous build artifacts are not overwritten. The pipeline's existing
always-archive allowlist retains available reports on scan failure/abort:

- `security-summary.json`: status, counts, UTC times, elapsed seconds, source inventory/
  hashes and lock hash. A passing source result may have Bandit exit **1** due solely to
  reported LOW findings; the severity policy—not an unconditional exit-code override—decides.
- `security-tools.txt`, `security-export.txt`, `runtime-requirements.txt`.
- `bandit.json`, `bandit.txt`, `pip-audit.json`, `pip-audit.txt`.

A completed successful pipeline now archives **25** allowlisted artifacts, including these
8 reports. Raw scanner output can contain source fragments/advisory descriptions: review
and scan for secrets before curating it into Git. Do not archive caches or entire workspaces.

## Actual findings and remediation

The initial real scan found **12 MEDIUM-severity, HIGH-confidence B314 findings** at XML parser
calls in four Jenkins tools, plus 17 LOW findings. No transaction API source was changed.
The user approved directly declaring `defusedxml` (already a pip-audit transitive dependency)
and replacing these parsers rather than suppressing findings. XML construction still uses
standard-library ElementTree; parsing now rejects entity declarations/external entities.
Regression cases cover internal entities and synthetic file/network entity declarations
through the public demo-configuration helper; normal job XML remains supported.

After remediation: **0 MEDIUM/HIGH, 17 LOW findings**, **14 audited runtime dependencies,
0 known advisories**, and **316 passing host tests**. These are dated observations, not a
permanent vulnerability-free guarantee. LOW findings remain reported; they include
subprocess imports/calls (B404/B603), executable lookup through the trusted operator/agent
PATH (B607), operational assertions (B101), and XML construction imports (B405). They were not silently suppressed.

Known unsuppressed warnings: Starlette's existing HTTPX deprecation, plus pip-audit's
recommendation to hash requirement exports. The advisory-only export is intentionally
plain exact pins; installations still use the hashed `uv.lock` via locked uv execution.
The scan records the lock hash and cross-checks all audited names/versions. This does not
replace installed-byte/image verification or claim package authenticity from advisory lookup.

An initial gate validation rejected Bandit's `./` paths despite complete results; the
validator was corrected narrowly and regression-tested. It failed closed before the fix.
No tool finding, timeout, or scanner failure was converted to success to work around it.

## Jenkins verification and review boundary

Local host checks are complete. Before merge, a manual sandboxed review job uses the
candidate Jenkinsfile plus a documented checkout wrapper: public reviewed main is cloned,
then an exact **local Git bundle** is fetched/checked out on the owned agent. The bundle
is transferred by the host operator, not published or served over a new network endpoint.
Record both base and candidate revisions plus bundle/pipeline hashes. This is candidate
execution, **not** a normal Jenkinsfile-from-SCM run from a published feature branch.

The separate failure review restores only the four original XML-parsing source files
immediately before the scan, without running that old helper code. Bandit should then
block on the genuine original findings while JUnit/coverage and scan reports remain
available. This is not the later HIGH/CRITICAL vulnerable-image demonstration or a claim
about registry/deployment/credential gates, which do not exist here.

Both live candidate runs completed on 25 October 2026:

- `finsecure-ci-scan-review-success-20261025074032` #1: **SUCCESS**, 316 tests, 0 blocking
  findings, 25 downloaded artifacts and verified package/image hashes/configuration.
- `finsecure-ci-scan-review-blocked-20261025074130` #1: **FAILURE**, 316 tests passed before
  restoration; the scanner found 12 MEDIUM and 19 LOW findings, exiting 1. Package and
  Local image export were skipped; all 15 pre-package/report artifacts remained available.
  Dependency auditing still passed. No old helper was executed or packaged.

Both jobs are disabled with history preserved. The exact owned agent bundle was removed
only after checking its hash and agent idleness; main's polling/job and the disabled Step
4.4 demo are unchanged. See the [evidence](../../evidence/task-05/step-01-source-scans.md).
Synthetic process-boundary tests cover scanner errors/timeouts, malformed/partial reports,
missing dependencies and stale outputs; no live advisory-service outage was induced.

After approval, implementation `893e764` and evidence follow-up `76b0f7d` were merged
and atomically published to main/the step branch. Normal **finsecure-ci #6** then ran
with an SCM cause, loaded Jenkinsfile from Git at `76b0f7d`, passed all **316 tests**,
and passed the real scan gate (17 LOW, no MEDIUM/HIGH; 14 dependencies, no known advisories).
All **25** artifacts were downloaded; scan inventory/source/lock hashes, package checksums,
and exported image identity were verified. See the
[post-merge evidence](../../evidence/task-05/step-01-scm-verification.md).
Trivy/image scans, release credentials, registry/cloud delivery, and full Step 5.4
demonstrations remain pending. No exported image was loaded/smoke-tested in this step;
earlier runtime evidence belongs to its own exact image.
