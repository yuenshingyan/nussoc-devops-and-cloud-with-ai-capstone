# FinSecure Pay

A Python/FastAPI transaction-validation API and cloud-native DevOps capstone.

## Status

Task 1 is complete and merged: application endpoints, 167 passing tests,
JUnit/coverage reports, clean package-installation checks, and public GitHub access.
Task 2.1 adds a multi-stage, non-root Docker image definition. Container execution,
registry publication, pipeline, and cloud work remain pending.

**Evaluator source link:** [reviewed application on main](https://github.com/yuenshingyan/nussoc-devops-and-cloud-with-ai-capstone/tree/main).
GitHub now defaults to `main`. See the
[publication runbook](docs/runbooks/source-publication.md) for verified links and details.
See [PLAN.md](PLAN.md) for ordered steps and branch names.

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

## Container build

```sh
docker build --progress=plain --tag finsecure-pay:task-02-step-01 .
```

The image uses locked runtime dependencies and runs as UID/GID `10001:10001`.
See the [container build runbook](docs/runbooks/container-build.md), including the
local Docker Desktop credential-helper workaround. Running and publishing the
image remain separate steps.

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
  jenkins/              Jenkins setup documentation
  monitoring/prometheus/    Metrics collection and alert rules
  monitoring/grafana/dashboards/  Dashboard definitions
  monitoring/alertmanager/  Alert routing configuration
  logging/              Centralized logging configuration
  security/             Scanner policies and remediation guidance
scripts/
  test.sh               Full pytest run with JUnit XML and coverage reports
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

- Task 1: complete. No application environment settings or secrets are needed yet.
- Remaining Task 2: container execution/smoke tests and versioned registry publication.
- Task 3: Kubernetes manifests and provider-specific infrastructure setup.
- Task 4: `Jenkinsfile` and pipeline setup instructions.
- Tasks 5–6: Security policies, monitoring/logging configuration, and demo scripts.
- Task 7: Design document, architecture diagram, AI use case, and presentation.

Do not add empty executable configuration files as if they were working artifacts.

## Workflow and safety

Work on one dedicated branch per step, verify changes, and pause for review
before merging into `main`. Do not commit secrets or raw sensitive exports.
The original assignment HTML and local agent guide are stored outside this repository;
do not copy them into published artifacts.
No external resources should be created or published without confirmation.
