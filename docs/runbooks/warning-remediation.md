# Warning remediation — reviewed-scope investigation

## Status

On 28 October 2026 the user approved publishing Step 5.2's evidence follow-up and
investigating warning remediation, including HTTPX2. The evidence follow-up is
published as `b7006b9`. This separate `chore/warning-remediation` branch contains
a test-client dependency migration; review/merge/publication remain pending.

## Starlette test-client deprecation: fixed locally

The installed Starlette 1.9.0 metadata declares `httpx2>=2.0.0` for its full extra.
Its TestClient imports HTTPX2 first and warns when falling back to HTTPX.
The package links to [HTTPX2](https://pypi.org/project/httpx2/) and its
[Pydantic-maintained source](https://github.com/pydantic/httpx2).

Replace the direct development dependency `httpx>=0.28,<0.29` with
`httpx2>=2.16,<3`, locked at 2.16.0. The lock replaces httpcore with httpcore2 and
adds truststore. Its conditional Emscripten dependency httpx2-jsfetch is resolved
but not installed on this macOS host. These are development-only changes.
The 14 exported runtime names/versions are identical before and after migration.
Application code, API contract, Dockerfile and scanner policies are unchanged.

Actual local checks:

- `uv sync --locked`: passed.
- `uv run --locked ruff check .`: passed.
- `uv run --locked ruff format --check .`: passed.
- `uv run --locked pytest -W error`: **410 passed**, with no warnings.
- `uv build`: wheel and source distribution built.
- `uv run --locked python scripts/security_scan.py`: source/runtime gates passed.
- `git diff --check`: passed.

The existing integration suite exercises the real TestClient. Treating warnings as
errors in this verification command demonstrates the deprecation is removed; no
warning filter/suppression was introduced. Jenkins and container verification of
this new lock remain pending. Previous image-scan evidence is not evidence for a
new image built from this branch.

[Local verification output](../../evidence/task-05/warning-remediation/local-checks.txt).

## pip-audit recommendation: experiment passed; integration deferred

The current scanner intentionally exports plain exact pins, passes `--no-deps`
and disables pip. The installed pip-audit emits its hash recommendation whenever
`--no-deps` is present. This warning is not a vulnerability finding.

A separate local experiment exported the same locked runtime requirements with
uv's default hashes and invoked pip-audit with `--require-hashes --disable-pip
--strict --vulnerability-service pypi`, omitting `--no-deps`. The actual command
completed within a 300-second outer bound and used a 15-second advisory timeout.
All 14 exact pins were audited, with no known findings and no warning. The existing
`dependency_result` validator confirmed complete dependency/version coverage.

[Experiment output](../../evidence/task-05/warning-remediation/hashed-audit.txt) and
[report](../../evidence/task-05/warning-remediation/hashed-audit.json).

This has NOT changed the production scanner. A separate implementation must:

1. Define and strictly validate the hash-bearing export format; continue rejecting
   URLs, editable requirements, markers, duplicates, missing hashes and pip options.
2. Preserve exact lock/inventory coverage and fail-closed report handling.
3. Use `--require-hashes` instead of `--no-deps`, retaining disabled pip and current
   policy/time budgets; test invalid hashes and scanner failures.
4. Keep the image scanner's plain-pin input contract explicit and update report
   consumers, tests and documentation together.
5. Verify real passing/blocked/error outcomes before claiming CI integration.

No additional dependency is needed for hashed uv exports. Historical evidence is
not rewritten to hide its warnings.

## Historical pip root-user warning: no suppression

The image builder installs into a controlled image layer as root, then the final
runtime runs as UID/GID 10001 and excludes pip/ensurepip. The warning concerns the
build-time install, not evidence that the running service is root. No Dockerfile
change or `--root-user-action=ignore` suppression is included here.
