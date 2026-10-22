# FinSecure Pay

A Python/FastAPI transaction-validation API and cloud-native DevOps capstone.

## Status

Tasks 1–2 and Steps 3.1–3.2 are reviewed, merged, and published. Kubernetes resources
pin public ARM64/AMD64 release 0.2.0; 210 application tests pass. Local Jenkins setup
and repository checkout are reviewed and merged in Step 4.1. Step 4.2 is merged:
`finsecure-ci` build #1 loaded its Jenkinsfile from Git at `8deecec`, passed **230 tests**,
published test/coverage reports, and archived verified wheel/source packages.
Cloud work is deferred
for budget approval while feasible local work proceeds toward **4 November** submission.
Kubernetes execution and all dependent cloud verification remain pending.

**Evaluator source link:** [reviewed application on main](https://github.com/yuenshingyan/nussoc-devops-and-cloud-with-ai-capstone/tree/main).
GitHub now defaults to `main`. See the
[publication runbook](docs/runbooks/source-publication.md) for verified links and details.
See [PLAN.md](PLAN.md) for the approved budget-aware sequence, deferred requirements,
and branch names.

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
manual triggering, and the post-merge check. No image/cloud delivery stages exist yet.

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
  jenkins/              Local controller/agent images, Compose, JCasC, bootstrap and verification
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
- Remaining Task 4: container delivery, source-change/failed-test proof, rollout/rollback.
- Tasks 5–6: Security policies, monitoring/logging configuration, and demo scripts.
- Task 7: Design document, architecture diagram, AI use case, and presentation.

Do not add empty executable configuration files as if they were working artifacts.

## Workflow and safety

Work on one dedicated branch per step, verify changes, and pause for review
before merging into `main`. Do not commit secrets or raw sensitive exports.
The original assignment HTML and local agent guide are stored outside this repository;
do not copy them into published artifacts.
No external resources should be created or published without confirmation.
