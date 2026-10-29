# FinSecure Pay

A Python/FastAPI transaction-validation API and cloud-native DevOps capstone.

## Status

Tasks 1–2 and Steps 3.1–3.2 are reviewed, merged, and published. Kubernetes resources
pin public ARM64/AMD64 release 0.2.0; 210 application tests pass. Local Jenkins setup
and repository checkout are reviewed and merged in Step 4.1. Step 4.2 is merged:
`finsecure-ci` build #1 loaded its Jenkinsfile from Git at `8deecec`, passed **230 tests**,
published test/coverage reports, and archived verified wheel/source packages.
Step 4.3's approved local subset is merged as `ab538a2`: normal SCM-loaded build #2
passed **245 tests** and exported a rootless-built ARM64 image. Its downloaded archive
passed checksum, identity, HTTP, shutdown, and cleanup checks.
Step 4.4's local polling/test-gate subset is reviewed, merged, and published: the isolated
public demo produced automatic passing, real failing-test, and recovered builds. Its job
is disabled and branch head passing. Normal SCM-triggered build #4 at `2f30e7e` passed
**260 tests** with verified packages/image export; see the
[post-merge evidence](evidence/task-04/step-04-scm-verification.md).
Cloud work is deferred
for budget approval while feasible local work proceeds toward **4 November** submission.
Kubernetes execution and all dependent cloud verification remain pending.

Step 5.1 is reviewed, merged, and published. Normal SCM-triggered build #6 at `76b0f7d`
passed **316 tests**, Bandit source gates, and pip-audit of 14 locked runtime dependencies.
XML parser remediation cleared 12 MEDIUM findings; 17 LOW findings remain reported.
Separate candidate runs verified real scan blocking; normal CI exported 25 verified artifacts.
See the [source-security runbook](docs/runbooks/source-security.md) and
[post-merge evidence](evidence/task-05/step-01-scm-verification.md).

Step 5.2 is **reviewed, merged, published, and SCM-verified**: normal automatic build
#8 at `3d3aaa6` passed 410 tests, source/dependency/image gates, and verification of
33 downloaded artifacts. See the [post-merge evidence](evidence/task-05/step-02-scm-verification.md).
The implementation history follows: verified Trivy tooling was installed,
while an operator preflight found 70 HIGH and 6 CRITICAL image finding occurrences.
The approved policy would block that image. Approved candidate testing found that updated
Debian bases still block, while Python 3.14.9/Alpine 3.24 candidates report no known findings
and each pass 316 tests plus runtime checks on ARM64 and emulated AMD64. The user approved
Alpine adoption; the root Dockerfile now uses that base with pip/ensurepip removed. The
local candidate Jenkinsfile gates image archival on fresh fail-closed scans, with a
30-minute global budget. Three candidate Jenkins runs each passed **410 tests**, verifying
a passing image, real vulnerability blocking and a fail-closed input error. The passing
export also passed operator runtime checks. Subsequent merge/publication and normal SCM
proof are recorded above. See the [gate evidence](evidence/task-05/step-02-image-gates.md) and
[image-security checkpoints](docs/runbooks/image-security.md).

**Evaluator source link:** [reviewed application on main](https://github.com/yuenshingyan/nussoc-devops-and-cloud-with-ai-capstone/tree/main).
GitHub now defaults to `main`. See the
[publication runbook](docs/runbooks/source-publication.md) for verified links and details.
See [PLAN.md](PLAN.md) for the approved budget-aware sequence, deferred requirements,
and branch names.

The subsequent warning-remediation changes are merged and SCM-verified: HTTPX2
removed the test-client deprecation, and lock-bound hashed auditing removed the
pip-audit recommendation. Normal build #12 at `12ebb9c` passed **446 tests** without
pytest/audit warnings, all security gates, and 33 artifact checks. See the
[verification record](docs/runbooks/hashed-dependency-audit.md).

Step 5.3's approved local credential-boundary subset is merged/published as
`1ace992`: automatic build #14 passed **503 tests**, all security gates, and 33
artifact checks. The separate read-only operator check also passed. Live rotation
and registry/cloud credential controls remain deferred. See the
[post-merge evidence](evidence/task-05/step-03-scm-verification.md).

Step 5.4's approved local demonstration is reviewed, merged and published as `d76b713`: two manual
runs each passed **503 tests**. The Debian comparison produced a real 61 HIGH/2 CRITICAL
image block with no archived image; restoring the production Alpine Dockerfile passed
with no known findings. The demo job is disabled and its workspace image archives are
removed; no image was run, published or deployed. See the
[demonstration evidence](evidence/task-05/step-04-security-demonstration.md).
Step 6.1's local metrics scope is merged, published and SCM-verified:
538 host/candidate Jenkins tests passed, the exact candidate image passed its gate,
and real Prometheus scrapes recorded 60 synthetic requests plus process metrics.
The demo services are stopped with data preserved. Normal SCM build #17 passed
538 tests and all gates; [follow-up evidence](evidence/task-06/step-01-scm-verification.md)
distinguishes its archive from the earlier live-demo image. See the [runbook](docs/runbooks/metrics.md) and
[actual evidence](evidence/task-06/step-01-metrics.md).

Step 6.2's authenticated local Grafana dashboard is merged/published as `f61cb4f`:
578 host and normal SCM tests passed, real five-panel queries and a browser screenshot
were captured after 60 synthetic requests. The approved secret-volume correction
preserved the existing password. Services are stopped with data/secrets retained.
See the [setup and known warnings](docs/runbooks/dashboard.md) and
[actual dashboard evidence](evidence/task-06/step-02-dashboard.md). Normal SCM build
#19 verified all gates and 33 artifacts; see the
[follow-up evidence](evidence/task-06/step-02-scm-verification.md).

## Quick start

Prerequisites: uv and Python 3.14 (uv can install the interpreter if needed).
Run from this repository's root:

```sh
uv sync --locked
uv run --locked uvicorn finsecure_pay.main:create_app --factory --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` or request `/openapi.json`. Stop with Ctrl-C.
The root `/` returns 404. Check application liveness from another terminal:

```sh
curl --fail --silent --show-error http://127.0.0.1:8000/health
# {"status":"healthy"}
```

This checks application liveness, not external dependencies.

In the current source, `GET /metrics` exposes Prometheus text on the same
local port. It is omitted from OpenAPI and must not be treated as a public endpoint.
See the [local monitoring setup and limits](docs/runbooks/metrics.md) before starting
the separate Docker application/Prometheus demo; do not bind another app to port
8000 while the development server is already using it.

Validate a synthetic transaction:

```sh
curl --fail --silent --show-error http://127.0.0.1:8000/validate \
  --header 'Content-Type: application/json' \
  --data '{"transaction_id":"txn_001","sender_id":"account_001","recipient_id":"account_002","amount":"125.50","currency":"SGD"}'
# {"valid":true,"errors":[]}
```

Amounts must be strings, not JSON numbers. Business-rule rejections return HTTP 200
with `valid: false`; malformed request schemas return HTTP 422. See the
[API contract](docs/api-contract.md) for rules, error codes, and limitations.

```sh
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
uv build
```

Generate the complete test and coverage reports with `./scripts/test.sh`.
Outputs are `reports/junit.xml` and `reports/coverage.xml` (ignored by Git).
JUnit XML is a report format; all tests run in Python with pytest.

See the [local development runbook](docs/runbooks/local-development.md) and
[Python stack decision](docs/decisions/001-python-stack.md).

Version 0.2.0 supports optional `FINSECURE_MAX_TRANSACTION_AMOUNT` and
`FINSECURE_SUPPORTED_CURRENCIES` environment settings. Defaults remain `10000` and
`SGD,USD,HKD`; currency configuration selects a nonempty subset of those currencies.
Invalid settings fail startup. See the [settings contract](docs/runbooks/application-settings.md)
and [`.env.example`](.env.example). The application does not auto-load `.env` files.

## Container build

```sh
docker build --progress=plain --tag finsecure-pay:0.2.0-local .
```

The image uses locked runtime dependencies and runs as UID/GID `10001:10001`.
See the [container build runbook](docs/runbooks/container-build.md), including the
local Docker Desktop credential-helper workaround.

Run the local image smoke test:

```sh
uv run --locked python scripts/smoke_test.py --image finsecure-pay:0.2.0-local
```

It uses a loopback-only port, checks the actual non-root process and HTTP responses,
then stops/removes its test container. See the
[execution runbook](docs/runbooks/container-execution.md). No image is pulled or
published by this script.

## Published container

**[Docker Hub: yuenshingyan/finsecure-pay](https://hub.docker.com/r/yuenshingyan/finsecure-pay)**

```sh
docker pull yuenshingyan/finsecure-pay:0.2.0
uv run --locked python scripts/smoke_test.py --image yuenshingyan/finsecure-pay:0.2.0
```

Version `0.2.0` and commit tag `sha-ada935d` point to the same multi-platform release.
ARM64 and AMD64 passed default/custom-policy and invalid-startup checks before publication
and after pulling their
registry digests; AMD64 was tested under emulation, not on a native cloud node.
See the [image publication runbook](docs/runbooks/image-publication.md) for the
immutable deployment digest, source revision, and exact evidence. This demo release
has not yet passed the security scans planned for Task 5; use synthetic data only.

The earlier 0.1.0 release remains unchanged: its fixed rules do not consume these
environment settings. Use 0.2.0 for configurable validation.

## Kubernetes configuration

```sh
kubectl kustomize deploy/kubernetes/overlays/demo
```

This renders a namespace, two-replica Deployment, internal ClusterIP Service, and
content-hashed ConfigMap without contacting a cluster. The image is pinned to the
verified 0.2.0 multi-platform digest. Startup/readiness/liveness probes, resource limits,
non-root/read-only security settings, and rolling-update policy are configured.
**Do not apply these manifests yet:** provider, budget, access, and exposure approval
are still required. See the [Kubernetes runbook](docs/runbooks/kubernetes-manifests.md)
and [runtime policy](docs/runbooks/runtime-safeguards.md) for values and verification limits.

## Local Jenkins

```sh
docker compose -f ops/jenkins/compose.yaml build
uv run --locked python ops/jenkins/bootstrap.py
```

Open `http://127.0.0.1:8080/` as `admin`. The bootstrap prints the protected local
password-file **path**, never its value. Do not paste credentials into chat or Git.
The controller runs no builds; a separate non-root Python agent checks out trusted
`main`. SCM polling is configured without exposing a public webhook or Docker socket.
This URL is local only, not an evaluator-accessible hosted service.

Step 4.2 adds `finsecure-ci`: checkout, locked installation, Ruff, pytest/JUnit,
application coverage, and wheel/source-distribution artifacts. Both pre-merge review
runs and the normal post-merge SCM-loaded job have been verified. See the
[application CI runbook](docs/runbooks/application-ci.md) for verified runs, reports,
manual triggering and recorded SCM runs. Step 4.4 moves five-minute polling to
application CI and retains checkout as a manual diagnostic; see the
[trigger/gate demonstration](docs/runbooks/ci-trigger-gate.md). Step 4.3's verified local subset adds a separate
rootless builder and local image archive; see [local image building](docs/runbooks/local-image-builder.md).
Registry publishing and cloud deployment remain unimplemented.

See the [Jenkins runbook](docs/runbooks/local-jenkins.md) for credential handling,
verification, troubleshooting, resource limits, and non-destructive shutdown.

## Repository structure

```text
src/finsecure_pay/       Application package
  api/                  HTTP endpoint handlers
  schemas/              Request and response models
  services/             Transaction validation rules
  observability/        Structured logging and metrics
tests/
  unit/                 Isolated business-rule and configuration tests
  integration/          API integration tests
deploy/
  kubernetes/base/       Shared application manifests
  kubernetes/overlays/demo/  Demo-specific Kubernetes configuration
  infrastructure/       Managed-cloud provisioning configuration
ops/
  jenkins/              Local controller/agent/builder images, Compose, bootstrap and verification
  monitoring/prometheus/    Metrics collection and alert rules
  monitoring/grafana/dashboards/  Dashboard definitions
  monitoring/alertmanager/  Alert routing configuration
  logging/              Centralized logging configuration
  security/             Scanner policies and remediation guidance
scripts/
  test.sh               Full pytest run with JUnit XML and coverage reports
  smoke_test.py         Local container execution, HTTP checks, and cleanup
  demos/                Controlled demonstration scripts
docs/
  architecture/         Diagram sources
  decisions/            Architecture decision records
  runbooks/             Setup, deployment, troubleshooting, and teardown
evidence/task-01..07/    Reviewed evidence for each assignment task
submission/             Final presentation and design-document deliverables
```

Empty directories use `.gitkeep` files so Git preserves the intended layout.
Remove a placeholder when its directory receives real content.

## Files to add during implementation

- Tasks 1–2: complete; published image 0.1.0 remains unchanged.
- Task 3.1: configuration/manifests and 0.2.0 publication reviewed and merged.
- Task 3.2: runtime settings reviewed and merged; Kubernetes execution pending.
- Remaining Task 3: provider-specific infrastructure, deployment, and recovery (deferred).
- Task 4.1: local Jenkins and checkout reviewed, merged, and published.
- Task 4.2: reviewed, merged, published, and verified through the normal SCM-loaded job.
- Task 4.3: local builder/export subset reviewed, merged, and verified through SCM build #2.
  Registry publication and Kubernetes delivery remain deferred; the full step is incomplete.
- Task 4.4: local source-trigger/test-gate subset reviewed, merged, published, and SCM-verified.
  Demo branch reverted/passing and job disabled; publishing/deployment gates remain pending.
- Remaining Task 4: registry/cloud delivery, full release-gate proof, rollout/rollback.
- Task 5.1: reviewed, merged, published, and verified through normal SCM build #6
  (316 tests, passing scans, 25 artifacts); 17 LOW Bandit findings remain reported.
- Task 5.2: Alpine/image gate implemented and locally verified with passing, vulnerability-
  blocked and error cases (410 tests each). Merged/published; normal SCM build #8 passed
  410 tests and all gates, with 33 verified artifacts.
- Task 5.3: approved local boundary-check subset merged/SCM-verified; rotation and
  registry/cloud credential controls remain deferred.
- Task 5.4: local image-archival block/remediation demonstration reviewed, merged and
  published as `d76b713`. Registry/deployment-blocking proof remains deferred.
- Task 6.1: local instrumentation/Prometheus merged and SCM-verified (build #17,
  538 tests, passing gates and 33 artifacts), with earlier real 60-request/process
  collection evidence. Managed-cluster monitoring and later observability steps deferred.
- Remaining Tasks 5–6: deferred security controls and cloud release-gate proof,
  monitoring/logging, alert delivery and notifications.
- Task 7: Design document, architecture diagram, AI use case, and presentation.

Do not add empty executable configuration files as if they were working artifacts.

## Workflow and safety

Work on one dedicated branch per step, verify changes, and pause for review
before merging into `main`. Do not commit secrets or raw sensitive exports.
The original assignment HTML and local agent guide are stored outside this repository;
do not copy them into published artifacts.
No external resources should be created or published without confirmation.
