# Step 4.2 — Approved publication and normal SCM-loaded execution

## Publication

Following user approval, `main` was fast-forwarded and pushed atomically with
`task-04/step-02-build-test-package` to GitHub at:

**`8deececf496ceb817f8965782e4481c37ea9531b`**

`git ls-remote` confirmed both remote refs at that revision. This follow-up evidence
commit changes documentation only; it is not the application/pipeline revision tested
by the build below. Pre-merge review builds remain documented in the
[original checkpoint](step-02-build-test-package.md).

## Real SCM-loaded execution

- Verified **22 October 2026, 09:26:21 UTC**.
- Job: **finsecure-ci**, build **1**, result **SUCCESS**.
- Trigger: manual authenticated API request, not a detected Git change.
- Actual job configuration: `CpsScmFlowDefinition`, `*/main`, script path `Jenkinsfile`.
- Console explicitly reports **“Obtained Jenkinsfile from git”** and the public repository.
- Checkout and `SOURCE_REVISION` both match the exact published revision above.
- Jenkinsfile SHA-256:
  `bc125564989157f36ca7e1a4ef258a61200c627283a7e0caf8bc4512b4f3ba56`.
- Execution took place on the separate **finsecure-python** agent, not the controller.
- Python **3.14.7**, uv **0.9.21**, Git **2.39.5** were recorded by the pipeline.
- Locked dependencies, Ruff lint/format, tests, and packaging all passed.
- **230 passed, 0 failed, 0 skipped**: 210 application tests and 20 operational-helper
  regressions, now all present in the published checkout.
- JUnit and Coverage plugin APIs were retrieved successfully, as were all 11 archived
  report/package files.
- Application coverage: **125/125 lines**, **28/28 branch outcomes**. No threshold or
  quality gate was added; the Coverage plugin reports `INACTIVE`.
- The existing Starlette/HTTPX deprecation warning remains visible.

## Downloaded packages

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `finsecure_pay-0.2.0-py3-none-any.whl` | 12080 | `13353d93c1c3ca1df7400485e6271d85ada17a0d44e423ecced405147aa9bd7a` |
| `finsecure_pay-0.2.0.tar.gz` | 160837 | `189aa431b67fdd79457d24d6f9853073d9ac4722a5811f75198493b9664e437c` |

Both hashes matched the downloaded pipeline checksum manifest. Wheel/source archives
were readable and contained the expected application module. Artifact hashes differ
from the pre-merge review builds because this run checked out a different source
revision; no bit-for-bit reproducibility or signed attestation is claimed.

## Evidence

- [Actual console](step-02-scm/console.txt).
- [Machine-readable verification and all artifact hashes](step-02-scm/verification.json).
- [JUnit API summary](step-02-scm/junit-api-summary.json),
  [Coverage API response](step-02-scm/coverage-api.json).
- [Pipeline build metadata](step-02-scm/build-metadata.txt),
  [downloaded package manifest](step-02-scm/packages.sha256).
- [Executed verification harness](step-02-scm/check-scm.py.txt), run from the repository
  root as `PYTHONPATH=ops/jenkins uv run --locked python reports/check-step42-scm.py`.
  It manually starts one build; rerunning it starts another build and is not needed to
  inspect this evidence. No automatic retry or existing job reconfiguration was used.

Local authenticated links (not externally hosted evaluator URLs):

- [Build](http://127.0.0.1:8080/job/finsecure-ci/1/)
- [Tests](http://127.0.0.1:8080/job/finsecure-ci/1/testReport/)
- [Coverage](http://127.0.0.1:8080/job/finsecure-ci/1/coverage/)
- [Artifacts](http://127.0.0.1:8080/job/finsecure-ci/1/artifact/)

Package binaries/full generated JUnit XML remain in Jenkins and ignored local storage.
The helper checks downloaded files for known live Jenkins credentials before writing;
console content is sanitized. No raw credentials or Jenkins home exports are included.

## Scope boundary

This closes Step 4.2's normal SCM-loading follow-up. It does **not** prove automatic
source-change triggering, a real failing-test release gate, registry publication,
container delivery, security scanning, or managed Kubernetes deployment. No image was
published and no cloud resource was created. Later steps remain separately approved.
