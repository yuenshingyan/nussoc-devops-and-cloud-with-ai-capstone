# FinSecure Pay

A Python/FastAPI transaction-validation API and cloud-native DevOps capstone.

## Status

Task 1, Step 1: Python/FastAPI scaffold with locked dependencies, application-factory
checks, and local development instructions. `/health` and `/validate` are not yet
implemented. Container, pipeline, and cloud work remain pending.
See [PLAN.md](PLAN.md) for ordered steps and branch names.

## Quick start

Prerequisites: uv and Python 3.14 (uv can install the interpreter if needed).
Run from this repository's root:

```sh
uv sync --locked
uv run --locked uvicorn finsecure_pay.main:create_app --factory --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` or request `/openapi.json`. Stop with Ctrl-C.
The root `/` returns 404; no business routes have been added yet.

```sh
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
uv build
```

See the [local development runbook](docs/runbooks/local-development.md) and
[Python stack decision](docs/decisions/001-python-stack.md).

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

- Remaining Task 1: health and validation endpoints, transaction tests, configuration
  examples when needed, and source publication. No environment settings or secrets
  are needed for the initial scaffold.
- Task 2: `Dockerfile`, `.dockerignore`, and container smoke tests.
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
