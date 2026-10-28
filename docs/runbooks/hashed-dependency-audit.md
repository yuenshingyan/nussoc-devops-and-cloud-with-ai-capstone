# Hashed dependency audit — local implementation and verification

## Scope and status

The user approved this change after the HTTPX2 migration and its evidence follow-up
were merged/published. Branch: `chore/hashed-dependency-audit`, based on reviewed
`main` at `5d743b9`. **Local implementation verified; merge/publication and Jenkins
verification remain pending.** No application, dependency, Dockerfile or lockfile
change is included. No later assignment task has started.

## Export and validation contract

The existing locked/offline runtime export retains its scope and report filename,
but no longer passes `--no-hashes`. The accepted format is deliberately narrow:

- Each canonical package name and exact version starts a line ending in space plus
  backslash. One or more indented `--hash=sha256:` lines follow.
- Hash lines have four leading spaces and exactly 64 lowercase hexadecimal digits.
  Intermediate lines end in space plus backslash; the final hash does not.
- Package names must be unique. Hashes must be unique within each package block.
- Every package/version must identify exactly one entry in `uv.lock`. The exported
  hash set must equal the complete SHA-256 set from that entry's sdist and wheels.
- Empty/incomplete blocks, plain unhashed pins, malformed/incorrect/partial/extra
  hashes, non-exact requirements, URLs, markers, editable requirements, comments,
  blank lines and other pip options are rejected. LF and CRLF are accepted.

The hash-aware parser is `hashed_runtime_pins(text, lock)`. The image scanner's
`runtime_pins(text)` remains plain-pin-only. Existing report names and JSON summary
fields are unchanged; consumers of the source requirement text must use the new
parser with the corresponding parsed lock. Historical observers remain historical.

pip-audit now uses `--require-hashes` rather than `--no-deps`; `--disable-pip`,
`--strict`, PyPI advisory service, the owned temporary cache, 15-second request
timeout and shared 300-second scan budget remain unchanged. All exact pins must
still appear once in the report. Any advisory blocks; skipped dependencies and
scanner/report errors fail closed. No new dependencies, retries, exemptions or
warning filters were introduced.

## Important negative-test discovery

The first real probe disproved an assumption: **pip-audit 2.10.1 with
`--require-hashes --disable-pip` accepts a syntactically valid all-zero hash**.
It reported no advisories and returned 0 for the pinned annotated-doc probe.
Its pre-resolved dependency path checks hash presence, not artifact hash values.
The initial experiment failed its `assert process.returncode != 0`; that failure
was investigated rather than hidden or treated as proof of a passing hash gate.

This is why the implemented parser compares the exported hashes directly with
`uv.lock` before invoking pip-audit. Both the retained all-zero-hash probe and a
modified real export are rejected by that check. A skipped-dependency/hash-error
report is also covered as a fail-closed regression, but is not presented as the
observed upstream behaviour.

This establishes consistency with the reviewed lock, **not authenticity or verification
of downloaded/installed package bytes**. A malicious lock change requires source
review; it is not detected by comparing an export with that same changed lock.
Locked installation and image checks remain separate controls.

## Actual checks on 28 October 2026

- Ruff lint and formatting checks passed.
- `uv run --locked pytest -W error`: **446 passed**, no warnings (36 new cases).
- Wheel/source distribution build passed.
- Full local source/runtime security gate passed: 19 LOW Bandit findings, no
  MEDIUM/HIGH, all 14 runtime dependencies audited, no known advisories.
- pip-audit output contains no hash recommendation; no diagnostic was suppressed.
- Isolated real hashed `requests==2.19.1` advisory probe returned 1 with **10
  advisory occurrences**. Its report passed the same complete-inventory result
  validator. The package was never installed, imported, run, packaged or deployed.
- The incorrect-hash probe returned 0 upstream; the new lock validator rejects it.
  It also rejects a single modified hash in the actual runtime export.
- `git diff --check` passed. Initial Ruff line-length failures were corrected by
  formatting before the final passing checks.

Tests cover exact pins, multiple artifact hashes, LF/CRLF, duplicate packages/hashes,
missing/invalid/unmatched lock entries, partial/mismatched hash sets, malformed
exports, skipped/partial/error audit reports and timeouts. Mocked process-boundary
tests establish exit 0/1/2 behaviour and prevent audit invocation after an invalid
export; the live advisory probes are separate from those mocks.

## Evidence and limitations

[Local checks](../../evidence/task-05/hashed-dependency-audit/local-checks.txt),
[source summary](../../evidence/task-05/hashed-dependency-audit/security-summary.json),
[hashed export](../../evidence/task-05/hashed-dependency-audit/runtime-requirements.txt),
[runtime audit](../../evidence/task-05/hashed-dependency-audit/pip-audit.json),
[audit output](../../evidence/task-05/hashed-dependency-audit/pip-audit.txt), and
[probe verification](../../evidence/task-05/hashed-dependency-audit/probes.json).

The original probe script is retained as `original-probes.py.txt` with its failed
assertion and earlier parser signature; it is historical, not a current rerun
instruction. `verify-probes.py.txt` validates those retained reports and the new
lock checks. Probe directories retain requirement text, raw advisory reports and
diagnostics. No binaries, caches, credentials or vulnerable installations are saved.

These results are **not** a Jenkins blocked-build demonstration, a live service-outage
test, or verification of a new image/deployment. Jenkins verification remains pending;
prior CI evidence belongs to prior revisions. Security findings are time-bound.
