# Step 4.2 — Application CI, published reports, and packages

This is the historical pre-merge verification record. Step 4.2 was subsequently approved,
merged/published as `8deecec`, and verified through the normal SCM-loaded job with 230 tests;
see the [post-merge follow-up](step-02-scm-verification.md). Statements below about pending
SCM execution describe the pre-merge checkpoint, not the current project status.

## Scope and provenance

- Branch: `task-04/step-02-build-test-package`, based on reviewed/published `6837068`.
- Verification: **22 October 2026 UTC**, local Docker Desktop Linux ARM64 agent.
- Application checkout in the review builds:
  **`683706803dd011c1b90e74ac67d1c691898194df`** (published `main`).
- Final candidate Jenkinsfile SHA-256:
  **`bc125564989157f36ca7e1a4ef258a61200c627283a7e0caf8bc4512b4f3ba56`**.
- Configuration source is the commit containing this record; exact file hashes are in
  [configuration-sha256.txt](step-02/configuration-sha256.txt).
- Controller image ID:
  `sha256:ca8fcd71b20493a8bce991d61d25aea603c78be9ca73b999064f01d28cda6e3c`.
- Agent image ID remains:
  `sha256:b9b74be7149028770bd7e137aa8397d48416ba7bf52c5d36f05f52d64ba87883`.

The success review job executed the unchanged candidate Jenkinsfile body, preceded
only by a pinned Git `scm` definition. The failure job inserted one explicit `exit 37`
after the test command. Their distinct executed-script hashes are recorded separately.
**Neither review job loaded its Jenkinsfile from Git.** The normal `finsecure-ci`
SCM definition is registered, but its first execution requires approved merge/publication.
No application source, dependency lock, or image release was changed by this step.
No source branch/image was published and no cloud resource was created during verification.

## Actual pipeline results

| Observation | Success review | Isolated failure review |
| --- | --- | --- |
| Job, build | `finsecure-ci-review-success-20261022090940`, #1 | `finsecure-ci-review-failure-20261022091005`, #1 |
| Jenkins result | **SUCCESS** | **FAILURE**, intended exit 37 |
| Checkout | Exact reviewed revision above, on `finsecure-python` | Same |
| Locked dependencies and Ruff | Passed | Passed |
| pytest | **221 passed**, no failures/skips | **221 passed**, then shell failure injected |
| Published JUnit API | 221 pass / 0 fail / 0 skip | 221 pass / 0 fail / 0 skip |
| Coverage publication | Accessible | Accessible despite failed build |
| Executable line coverage | 125/125, 100% | Same |
| Branch outcomes | 28/28, 100% | Same |
| Coverage quality gate | INACTIVE; none configured | Same |
| Package stage | Wheel and source distribution built/archived | Explicitly skipped due to earlier failure |
| Artifact download | Both packages and reports retrieved | Reports retrieved; no packages/checksum manifest |
| Package integrity | SHA-256 matched archived manifest; wheel/tar contents readable | Not applicable |
| Review job after verification | Disabled; history/artifacts retained | Same |

The source revision contains 210 application tests plus 11 Step 4.1 helper tests.
The Step 4.2 working branch adds nine verifier regressions: **230 tests passed locally**.
Those nine unmerged tests were not present in the pre-merge agent checkout. The normal
post-merge CI run must verify the new revision and its actual test count.

Only line and branch metrics are claimed as 100%. The Coverage plugin also reports
file/class coverage 66.67%, package coverage 80%, and module coverage 100%; the full
API summaries are retained. These derived metrics are not a new acceptance threshold.
The existing Starlette/HTTPX deprecation warning remains unsuppressed in host and CI runs.

## Package artifacts

The successful build stores `dist/finsecure_pay-0.2.0-py3-none-any.whl` and
`dist/finsecure_pay-0.2.0.tar.gz`, with Jenkins fingerprints and an independently
checked SHA-256 manifest. See [packages.sha256](step-02/packages.sha256) and
[success-verification.json](step-02/success-verification.json) for exact downloaded
hashes/sizes. These are Jenkins artifacts, not Docker registry publications or signed
attestations. The existing build-backend version range prevents a general claim of
bit-for-bit rebuild reproducibility.

## Infrastructure and local checks

- All **73** installed plugin versions matched the full pin list; all were active/enabled.
- Controller has zero executors; the separate agent has one executor and is online.
- Both services remain non-privileged, drop capabilities, prohibit privilege escalation,
  and use named volumes rather than host bind/socket mounts. No OOM was observed.
- The normal SCM job's class, main-branch selection, and Jenkinsfile path were checked
  through the API; it has not run yet.
- A separate fresh-home controller registered both jobs on first startup, with checkout
  polling present before any build. Its container and anonymous home volume were then
  confirmed removed. The original controller/secret volumes were not deleted.
- Host Ruff lint/format, **230 pytest cases**, application coverage, wheel/sdist build,
  and Compose configuration validation passed.

## Corrections and limitations

1. The initial verifier looked for `totalCount` on the JUnit report API. Actual fields
   are `passCount`, `failCount`, and `skipCount`; the parser was fixed and tested against
   missing/invalid/failing/skipped counts. The already successful build was inspected
   again rather than retrying its tests.
2. The Coverage publisher initially used its default Java source-search path. The final
   candidate explicitly supplies the Python source directory and UTF-8; both final review
   runs used that configuration.
3. Initial early-JCasC seeding wrote the SCM job to disk but left it absent from the
   live API registry. Job DSL now runs from an administrator-owned post-initialization
   hook; bootstrap verifies job visibility. A fresh-home first-start test demonstrated
   the corrected behavior, not merely a restart that reused existing job files.
4. A proposed dynamic `scm` trigger DSL failed during the first fresh-home checks.
   Explicit trigger XML replaced it; fresh startup and the working controller both
   confirmed the poll schedule. See the [actual failure excerpt](step-02/initial-seed-error.txt).
5. Jenkins startup duplicate-admin-index and JNLP-metadata deprecation diagnostics remain
   documented. The actual agent uses WebSocket `-url`/`-name`; no secret/user data was
   deleted or warnings suppressed to hide these diagnostics.

The exit-37 probe tests failure-path report retention and package blocking. It is **not**
the required later failing-test, vulnerability-gate, or release/deployment-blocking
exercise. No image delivery, notifications, managed Kubernetes, or cloud integration
is implemented here. The complete source-triggered pipeline is not yet demonstrated.

## Evidence and reproduction

- [Success console](step-02/success-console.txt), [failure console](step-02/failure-console.txt).
- [Success verification](step-02/success-verification.json),
  [failure verification](step-02/failure-verification.json): actual artifacts and hashes.
- JUnit API summaries: [success](step-02/success-junit-api-summary.json),
  [failure](step-02/failure-junit-api-summary.json).
- Coverage API responses: [success](step-02/success-coverage-api.json),
  [failure](step-02/failure-coverage-api.json).
- [Runtime inventory](step-02/runtime.json), [plugin inventory](step-02/installed-plugins.json),
  [fresh-controller check](step-02/fresh-controller.json), and [host checks](step-02/local-checks.txt).
- [Plugin image build](step-02/controller-plugin-build.txt),
  [final controller build](step-02/controller-final-build.txt).
- Recorded runtime/fresh-state harnesses: [runtime](step-02/check-runtime.py.txt),
  [fresh controller](step-02/check-fresh-controller.py.txt). They ran from the repository
  root with `PYTHONPATH=ops/jenkins uv run --locked python reports/<script>.py`.

See the [application CI runbook](../../docs/runbooks/application-ci.md) for commands,
local authenticated report URLs, queue/cancellation limits, and required post-merge
verification. Generated binaries/full JUnit exports remain in Jenkins and ignored local
storage. Curated text replaces host repository prefixes with `<repository>` and normalizes
trailing build-log whitespace; credentials and raw Jenkins home are not evidence.

**Review gate fulfilled:** approved merge/publication and the normal Pipeline-from-SCM
verification are recorded in the follow-up above. No later implementation step has started.
