# Step 4.1 — Local Jenkins setup and repository checkout

## Scope and identity

- Branch: `task-04/step-01-jenkins-setup`, based on reviewed `b70c576`.
- Configuration source: the commit containing this record; exact file hashes are in
  [configuration-sha256.txt](step-01/configuration-sha256.txt).
- Verification date: **22 October 2026 UTC**; machine-readable checks include timestamps.
- Environment: macOS ARM64 host, Docker Desktop Linux ARM64 VM, Docker Engine 29.6.1,
  Compose v5.2.0, approximately 4 GiB VM memory.
- Jenkins: **2.580.1 LTS**, Java 21, 63 installed plugins matching the full pinned list.
- Checked-out application/source revision: **`b70c5769c95f28ba543844d3bca7ab8b853c7163`**, the
  published, reviewed `main` at verification time. This was not a checkout of this then-unmerged
  Jenkins setup branch, nor an application test run in Jenkins.

No cloud provider/account/cluster was contacted and no cloud resources were provisioned
by this step. No image or source branch was published as part of this verification.
The existing application release 0.2.0 and Kubernetes digest were not changed.

## Actual results

| Check | Actual result |
| --- | --- |
| Controller and agent image builds | Passed locally; no registry publication |
| Jenkins controller | Zero executors; authenticated API; only host port `127.0.0.1:8080` |
| Agent | Online over WebSocket; one `python` executor; UID 1000 |
| Service boundaries | No host bind/Docker-socket mounts; dropped capabilities and no-new-privileges configured; recorded limits 1 CPU/1 GiB each |
| Authentication/CSRF | Anonymous API GET returned 403; password-authenticated POST without crumb returned 403 and did not create a build |
| Secret separation | Read-only, separate secret volumes; controller password absent from agent; neither secret appeared in container-inspection data |
| Plugin inventory | All 63 installed versions matched `plugins.txt`; all active/enabled |
| Checkout build 1 | Explicitly **ABORTED before checkout**, after the initial agent temporary-disk issue |
| Checkout builds 2 and 3 | **SUCCESS**, on `finsecure-python`, at the exact published revision above |
| Tool checks in Jenkins | Git 2.39.5, uv 0.9.21, Python 3.14.7, Temurin Java 21.0.12.1 |
| Restart/repeated bootstrap | Controller/agent recovered; password, agent secret, and build history preserved; checkout build 3 passed after restart |
| Triggering | `H/5 * * * *` SCM polling configured; these successful builds were manually triggered |
| Local Ruff | Lint and formatting passed |
| Local pytest | **221 passed**, zero failures/errors/skips: 210 application cases plus 11 operational-helper regressions |
| Application coverage | 125/125 executable lines and 28/28 branch outcomes; this measurement excludes operational scripts |
| Local packaging | Wheel and source distribution built successfully |
| Compose validation | Passed |

The pre-existing Starlette/HTTPX TestClient deprecation warning remains visible and
unsuppressed. There is no coverage threshold or automatic failed-test retry policy.
The helper regression cases mock only external boundaries (Docker, entropy, HTTP,
waiting) and use synthetic temporary credential files; they do not contact real Docker/Jenkins.
The separate runtime checks above exercised the real services.

## Artifacts and commands

- [Final local checks](step-01/checks.txt): Ruff, all 221 tests, application coverage,
  packaging, Compose validation, and whitespace checks.
- [Initial successful image builds](step-01/agent-and-controller-build.txt) and
  [final controller build](step-01/controller-final-build.txt).
- [Build 1, aborted](step-01/checkout-1-aborted.txt), [build 2](step-01/checkout-2.txt),
  and [build 3 after restart](step-01/checkout-3.txt): sanitized Jenkins console output.
- [Checkout/runtime summary](step-01/verification.json): exact source revision and
  local controller/agent image IDs, including build 3's result.
- [Authentication, plugin, secret and restart checks](step-01/runtime-checks.json).
- [Installed plugin inventory](step-01/installed-plugins.json), compared with all pins.
- [Recorded runtime-check harness](step-01/check-runtime.py.txt): release-specific
  check script, not installed application tooling. It restarts only idle, owned services.
- [Selected initial failure excerpts](step-01/setup-failure-excerpts.txt).

Normal reproduction follows the [local Jenkins runbook](../../docs/runbooks/local-jenkins.md):

```sh
docker compose --progress plain -f ops/jenkins/compose.yaml build
uv run --locked python ops/jenkins/bootstrap.py
uv run --locked python ops/jenkins/verify.py \
  --expected-revision b70c5769c95f28ba543844d3bca7ab8b853c7163
```

That SHA is historical; when public `main` changes, resolve its new SHA as described
in the runbook. Do not expect a later checkout to match an old revision automatically.
The recorded restart harness was executed from the repository root with
`PYTHONPATH=ops/jenkins uv run --locked python reports/check-step41-runtime.py`;
its reviewed source is preserved above. Logs were checked for the live credential
values and sanitized before inclusion; host repository prefixes are replaced with
`<repository>` in local check/build output; trailing build-log whitespace was normalized.
Raw Jenkins home, secrets, sessions,
configuration exports, and credentials are not evidence artifacts.

## Corrections made during setup

1. uv 0.9.21 could not download Python 3.14.7. The final agent uses the pinned official
   Python base and copies the official Java/remoting runtime; no interpreter downgrade.
2. The pinned Jenkins rejected obsolete `excludeClientIPFromCrumb`. Using the supported
   `standard: {}` retained CSRF protection, subsequently checked with a real denied POST.
3. Reinitializing UID-1000/read-only secret files required `FOWNER` in the short-lived
   initialization helper. It was not granted to either long-running service.
4. Jenkins quarantined the initial agent because its 128 MiB `/tmp` tmpfs fell below
   the default 1 GiB disk monitor threshold. Disk-backed container temporary storage
   fixed this without disabling monitors. Build 1 was aborted; builds 2 and 3 succeeded.
5. A restart probe initially treated a transient initialization/API-authentication response
   as terminal. Bounded readiness polling and regression tests now cover initialization;
   an actual restart and subsequent checkout passed. No application build/test was retried.
6. Bootstrap refuses unrelated data/secret volumes and does not silently regenerate a
   missing password when controller state or a secret volume already exists. Verification
   itself never creates a missing password. Redirect responses are closed and not followed.

## Limits and review gate

This is **not** a Jenkins application CI/CD success, an Internet webhook demonstration,
a vulnerability scan, a Docker publication, Kubernetes execution, or cloud deployment.
No Jenkinsfile/application test or packaging stage exists yet; those are Step 4.2.
No source change was published to demonstrate automatic triggering (Step 4.4).
The local URL requires this machine and is not an evaluator-accessible hosted endpoint.
Security gates and cloud-dependent work remain explicitly pending under the revised plan.

Step 4.1 is ready for user review; do not merge or continue without approval.
