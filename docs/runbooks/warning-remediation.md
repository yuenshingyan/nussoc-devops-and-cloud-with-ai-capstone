# Warning remediation — reviewed-scope investigation

## Status

On 28 October 2026 the user approved publishing Step 5.2's evidence follow-up and
investigating warning remediation, including HTTPX2. The evidence follow-up is
published as `b7006b9`. Following user approval, the test-client migration on
`chore/warning-remediation` was merged and published as `8f1e598`. Normal automatic
SCM-triggered Jenkins build #10 succeeded at that revision on 28 October 2026.

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
warning filter/suppression was introduced.

### Post-merge Jenkins verification

Normal build #10 loaded its Jenkinsfile from SCM at `8f1e598`, installed HTTPX2 and
httpcore2 2.16.0 plus truststore 0.10.5, and passed all 410 tests without a pytest
warning summary. Ruff, packaging, source/dependency gates and the fresh image gate
passed. All 33 downloaded artifacts were verified against their manifests and the
scanned image identity. No manual build or polling request was sent.

[Verification record](../../evidence/task-05/warning-remediation/scm/verification.json),
[sanitized console](../../evidence/task-05/warning-remediation/scm/console.txt),
[test output](../../evidence/task-05/warning-remediation/scm/tests.txt), and
[image gate](../../evidence/task-05/warning-remediation/scm/image-security-summary.json).
The retained GET-only observer records the pre-push baseline (#9, completed SUCCESS)
and validates source/lock/report/archive hashes. Known live credentials were checked
before saving artifacts. Binary exports remain outside Git.

This verifies the new lock in Linux Jenkins and a freshly built/scanned ARM64 image;
it does not claim an additional container runtime smoke test, registry publication,
or deployment. The pip-audit recommendation remains visible as described below.

[Local verification output](../../evidence/task-05/warning-remediation/local-checks.txt).

## pip-audit recommendation: initial experiment and subsequent implementation

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

That initial experiment did not change the scanner or prove hash-value enforcement.
The user subsequently approved implementation on `chore/hashed-dependency-audit`.
A negative probe discovered that pip-audit with `--disable-pip` accepts incorrect hashes;
the implementation adds an explicit lock-hash comparison. See the
[implementation and verification record](hashed-dependency-audit.md). It is not yet
merged or CI-verified. The original implementation checklist was:

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
