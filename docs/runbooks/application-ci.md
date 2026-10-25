# Application CI

Step 5.1 adds a Security scans stage between Tests and Package, with 8 additional
allowlisted reports (25 artifacts on success). It is reviewed, merged, published, and
verified through normal SCM-triggered build #6 at `76b0f7d` (316 tests, passing scans).
See the [source-security policy and verification](source-security.md).
Historical Step 4.2/4.3 results below retain their original revisions/counts.

Step 4.2's normal SCM-loaded run is complete. Step 4.3's local image-export addition is
also merged and verified: normal build #2 at `ab538a2` passed 245 tests and produced a
smoke-tested image. See the [builder runbook](local-image-builder.md) for operation.

## What runs

`Jenkinsfile` defines a declarative pipeline on the non-root `python` agent:

1. **Checkout:** clean the job's own workspace and `checkout scm`; record the source
   commit, interpreter/tool versions, and lockfile SHA-256.
2. **Locked dependencies:** `uv sync --locked` with the agent's Python 3.14.7/uv 0.9.21.
3. **Code checks:** locked Ruff lint and formatting checks.
4. **Tests:** `./scripts/test.sh`, then publish pytest's JUnit XML and Cobertura-format
   coverage XML using Jenkins JUnit/Coverage plugins.
5. **Security scans:** run locked Bandit and runtime dependency auditing; block on
   MEDIUM/HIGH source findings, any known dependency advisory, or scanner/report errors.
   Retain all available scan reports, including LOW findings, under the five-minute limit.
6. **Package:** `uv build`; require one nonempty wheel and source distribution; record
   SHA-256 checksums and archive/fingerprint both packages.
7. **Local image export (Step 4.3 local subset):** BuildKit builds Linux ARM64, exports a
   compressed Docker archive, and records source/image metadata and SHA-256. No push/load
   or deployment occurs in the pipeline. Only successful exports are archived.

Bash `pipefail` preserves command failures when output is captured with `tee`.
Missing/malformed reports fail publication; the two publishers are attempted independently
via `try/finally`. Coverage recording is explicitly enabled for failed builds. There is
**no coverage threshold**, no automatic failed-test retry, and no warning suppression.
JUnit instability also skips later stages. Application coverage excludes operational scripts.

Only named reports, the two package patterns, and the exact successful image archive
are archived, not `.venv`, caches,
credentials, Git internals, or the complete workspace. The global `always` post action
archives available diagnostic reports even when an earlier stage fails; allowing an empty
archive there accommodates failures before reports exist, not a successful missing-report
test stage. Test-report publication itself remains strict.

Coverage source lookup explicitly targets `src/finsecure_pay` with UTF-8. Colored source
copies are not retained (`NEVER`). The UI's derived class/file/package percentages are
not the same as executable line/branch coverage; do not describe every metric as 100%.
GitHub Checks publishing is disabled deliberately: these are local Jenkins reports, not
external status updates. No GitHub write credential is installed.

Runtime/dev dependencies are locked. The existing build-backend range
`hatchling>=1.27,<2` is not an exact build-environment lock, so do not claim bit-for-bit
rebuild guarantees. Jenkins fingerprints aid traceability; package downloads are also
checked against SHA-256, not treated as signed attestations.

## Job setup and triggering

Follow [local Jenkins setup](local-jenkins.md) to build/start the controller and agent.
The reviewed Step 4.4 configuration uses `finsecure-jenkins-controller:step-04-04` with the same
**73 pinned plugins**, moving polling to application CI. Step 4.3 updates the agent to `step-04-03` and adds a separate rootless builder;
Step 4.2 originally ran with the Step 4.1 agent. No plugin change is required here.

The trusted image's `seed-jobs.groovy` runs Job DSL after Jenkins has loaded its job
registry. JCasC still configures security/controller/agent settings, but does not create
jobs during early adaptation. The `.override` reference-file suffix updates only this
owned hook in persistent Jenkins home. Bootstrap checks that both configured jobs are
visible through the API; a running HTTP server alone is not success.

A real disposable controller with a fresh anonymous home registered both jobs on its
first startup, including checkout polling before any build. Its container/home were
removed afterward, without resetting the working controller. This catches the earlier
case where the new job existed on disk but was absent from the live registry. The setup
job's poll/concurrency properties are also seeded explicitly, not only installed by its
next Pipeline run. A dynamic Job DSL `scm` trigger alias proved unsupported; the final
seed uses the persisted trigger XML structure and was checked on fresh state.

`ops/jenkins/ci-job.groovy` creates **finsecure-ci**, a Pipeline-from-SCM job reading
`Jenkinsfile` from public, trusted `main`. It runs only published code and now includes
the approved local image-export stage.

Step 4.4 configures `H/5 * * * *` application SCM polling in trusted Job DSL, not in
Jenkinsfile. The checkout-only job is now manual; inline candidate jobs remain manual.
A separately approved demo branch/job demonstrated three SCM-triggered builds, including
one real pytest failure that skipped packages/image export and recovery after its revert.
See the [trigger/gate runbook](ci-trigger-gate.md). Publishing/deployment gates remain
pending. No untrusted PR/fork builds are enabled.

Builds of each job are serialized. The top-level 15-minute timeout begins after its
agent is allocated (it does not bound that initial queue wait). Git clone/fetch is
configured for two minutes. The review verifier polls for at most 20 minutes including
queue time, without retrying builds. If the client disconnects or times out, inspect and
explicitly cancel its owned queued/running build: disabling a job does not cancel existing
work. Jenkins owns the workflow; a verification-client error is not proof it stopped.

## Pre-merge verification without source publication

To avoid pushing unreviewed changes, `ops/jenkins/verify_ci.py` creates a sandboxed,
manual, uniquely named **local review job**. For its success case, it prepends only a
Git `scm` definition pinned to an explicitly selected published commit, followed by the
unchanged candidate Jenkinsfile. The production job instead receives `scm` from Jenkins.
Both candidate-file and executed-script hashes are recorded, so these are not conflated.

Historical Step 4.2 example (use the builder runbook for the current candidate):

```sh
uv run --locked python ops/jenkins/verify_ci.py \
  --source-revision 683706803dd011c1b90e74ac67d1c691898194df \
  --expected-tests 221
```

That recorded base revision had 221 tests; nine then-unmerged verifier regressions
brought the Step 4.2 local suite to 230. The subsequent normal SCM run passed all 230.
Pre-merge agent checkouts do not include unmerged tests. Step 4.3 had 245 local tests
versus 230 in its review checkout; its post-merge normal SCM run passed all 245.

The verifier follows its own queue item, checks the exact source/agent, reads actual
JUnit and Coverage APIs, downloads all listed artifacts, verifies package hashes and
archive structure, and rejects unexpected artifact paths or known live credentials.
Reports/downloads go under ignored `reports/<job-name>/`. Review jobs are disabled
when inspection finishes; their build history/artifacts remain available. They are not
silently deleted. Review retention/cleanup deliberately remains manual until assessment
needs are resolved; monitor local disk usage and stop idle services when not needed.

If only result inspection fails, `--existing-job <name>` inspects the matching single
completed review build without rerunning it. The saved job script must still match the
candidate/source exactly. An initial verifier expected `totalCount` on the JUnit report
API; that endpoint instead exports `passCount`, `failCount`, and `skipCount`. The verifier
was corrected and regression-tested; the already successful Jenkins build was inspected
again rather than retrying its tests.

## Report preservation on failure

```sh
uv run --locked python ops/jenkins/verify_ci.py \
  --source-revision 683706803dd011c1b90e74ac67d1c691898194df \
  --expected-tests 221 --fail-after-tests
```

This explicit option alters **only an isolated review job's copy** of the script: it
inserts `exit 37` immediately after the real test command. The committed Jenkinsfile,
application source, and tests remain passing. Verification requires the intended exit
37, published passing test/coverage reports, and no package artifacts. This demonstrates
failure-path report retention and package blocking, **not** a real failing test, a security
gate, or blocked image/cloud delivery. Step 4.4's separate real pytest demonstration
now verifies local package/image-export blocking, not publishing or deployment.

## Inspect actual reports

Sign in at <http://127.0.0.1:8080/> using the private credentials from the setup runbook.
Recorded final review jobs (build **1** each):

- Success: `finsecure-ci-review-success-20261022090940`.
- Intended failure: `finsecure-ci-review-failure-20261022091005`.

Open the build's **Console Output**, **Test Result**, **Application coverage**, and
**Artifacts** pages. Authenticated API paths are:

```text
/job/<job>/1/testReport/api/json
/job/<job>/1/coverage/api/json
/job/<job>/1/artifact/reports/junit.xml
/job/<job>/1/artifact/reports/coverage.xml
```

The success run also has the wheel, source distribution, and `reports/packages.sha256`.
These are local-only URLs requiring this machine and authentication, not externally
hosted evaluator links. Curated console/API summaries and package hashes are preserved
in the [evidence record](../../evidence/task-04/step-02-build-test-package.md); binaries
and large generated reports stay in Jenkins/local ignored storage.

## Verified SCM-loaded job and future runs

Following approved merge/publication, **finsecure-ci build #1** loaded the Jenkinsfile
from Git at `8deececf496ceb817f8965782e4481c37ea9531b` and passed all 230 tests. Test/coverage
APIs and downloaded package hashes were verified. See the
[post-merge evidence](../../evidence/task-04/step-02-scm-verification.md) and the local
[build page](http://127.0.0.1:8080/job/finsecure-ci/1/).

For a later manual run, open **finsecure-ci → Build Now**. Confirm its
console says the Jenkinsfile was obtained from Git, the checkout matches published
`main`, all 245 currently expected tests run, reports are accessible, and both packages
are downloadable with matching hashes. Record the actual revision/build separately;
pre-merge review jobs alone do not prove the SCM loading path.
If source changes again, use that revision's actual expected count rather than treating
245 as a permanent pipeline threshold. Step 4.3's completed
[SCM build #2](../../evidence/task-04/step-03-scm-verification.md) additionally verified
the image artifact and its host-side smoke results.

The merged Step 4.3 subset adds local container build/export only. Registry push,
vulnerability scans, notifications, and managed-cluster stages remain unimplemented.
Cloud-dependent work remains deferred under `PLAN.md`.

References: [JUnit step](https://www.jenkins.io/doc/pipeline/steps/junit/),
[Coverage step](https://www.jenkins.io/doc/pipeline/steps/coverage/),
[Pipeline syntax/timeouts](https://www.jenkins.io/doc/book/pipeline/syntax/),
[post-initialization hooks](https://www.jenkins.io/doc/book/managing/groovy-hook-scripts/).

Known diagnostics remain visible: Starlette's HTTPX deprecation warning, Jenkins's
agent-JNLP metadata endpoint deprecation warning (the actual agent uses WebSocket
`-url`/`-name`), and a Jenkins startup duplicate-admin-index warning. Authentication and
credential/history preservation work; no user directories were deleted to hide warnings.
