# Step 1.4 — Expanded tests and machine-readable reports

- **Date:** 2026-10-21 UTC; generated artifact verification completed at 14:22:00 UTC.
- **Branch:** `task-01/step-04-tests`, based on the reviewed transaction implementation.
- **Revision:** The commit introducing this file contains the verified test changes.
  Retrieve it with `git log -1 --format=%H -- evidence/task-01/step-04-tests.md`.
- **Environment:** macOS ARM64, Python 3.14.7, uv 0.9.21.
- **Scope:** Tests, report configuration, a test-running script, and documentation.
  No application behavior or dependency versions changed.

## Results

| Measure | Observed result |
| --- | --- |
| Total test cases | 167 passed |
| Unit/schema cases | 70 |
| API/integration cases | 97 |
| Failures / errors / skipped | 0 / 0 / 0 |
| Executable lines covered | 72 / 72 (100%) |
| Branch outcomes covered | 14 / 14 (100%) |
| Warnings | 1 pre-existing Starlette/HTTPX TestClient deprecation warning |

Coverage is informational. No percentage gate was introduced. The application is
small, and 100% execution coverage does not prove exhaustive input correctness,
security, or production readiness. The previous 54-case suite already had full
execution coverage; this step adds meaningful boundary and contract cases rather
than claiming the percentage alone establishes correctness.

## Added test coverage

- Every identifier field at 1 and 64 characters, plus overlong and malformed input.
- No trimming, case-folding, or Unicode normalization of opaque identifiers.
- All required fields rejecting nulls, numbers, booleans, arrays, and objects.
- Missing bodies, non-object JSON bodies, and all required fields missing together.
- Accepted amount boundaries for each supported currency.
- Negative-zero variants, extra fractional digits, and trailing zeros.
- 32-character decimal strings, including values just above/below the amount limit.
- Exact comparisons even with a deliberately low local Decimal context precision.
- Multiple business rejections returned in the documented order.
- No mutation of a supplied request, no hidden deduplication, and no failed-request
  state leaking into the following successful request.
- OpenAPI required-field/type constraints and safe errors that do not echo input.

## Commands and checks

From the repository root:

```sh
uv run --locked ruff check .
uv run --locked ruff format --check .
bash -n scripts/test.sh
./scripts/test.sh
uv build
```

All checks succeeded. The final report-generating run invoked the script from the
parent directory as `./capstone/scripts/test.sh`, additionally verifying that it
resolves the project root independently of the caller's working directory.

The script invokes pytest with JUnit XML and coverage output. JUnit is the **report
format**, not a Java test runtime. No Java/JUnit installation was used.

```sh
uv run --locked pytest \
  --junitxml=reports/junit.xml \
  --cov=finsecure_pay \
  --cov-report=term-missing \
  --cov-report=xml:reports/coverage.xml
```

The XML files were parsed after execution. The JUnit suite totals matched its 167
individual test cases and contained no failure/error elements. Coverage XML recorded
72/72 lines and 14/14 branch outcomes, and each reported source filename resolved
to a real repository-relative file.

## Preserved evidence

- [JUnit-compatible XML](step-04/junit.xml)
- [Cobertura-compatible coverage XML](step-04/coverage.xml)
- [Pytest console output](step-04/test-output.txt)

Raw, regeneratable reports remain in ignored `reports/`. These selected evidence
copies preserve actual test outcomes and coverage data. The JUnit machine hostname
was removed and XML whitespace reformatted; absolute project paths in console
output were replaced with `<project-root>`. The coverage XML already used relative
source paths and was copied unchanged. Test names, outcomes, counts, durations,
and warning text were not altered.

The warning remains visible and unsuppressed. Jenkins ingestion and failed-test
pipeline blocking have **not** been demonstrated; those remain Task 4. No remote
publication or cloud operation was performed during this step.
