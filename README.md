# FinSecure Pay

A Python/FastAPI transaction-validation API and cloud-native DevOps capstone.

## Status

Directory structure only. The application, dependency configuration, tests,
container image, pipeline, and cloud resources have not been implemented yet.
See [PLAN.md](PLAN.md) for ordered steps and branch names.

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

- Task 1: `pyproject.toml`, `uv.lock`, `.python-version`, `.env.example`,
  application modules, tests, and local development instructions.
- Task 2: `Dockerfile`, `.dockerignore`, and container smoke tests.
- Task 3: Kubernetes manifests and provider-specific infrastructure setup.
- Task 4: `Jenkinsfile` and pipeline setup instructions.
- Tasks 5–6: Security policies, monitoring/logging configuration, and demo scripts.
- Task 7: Design document, architecture diagram, AI use case, and presentation.

Do not add empty executable configuration files as if they were working artifacts.

## Workflow and safety

Work on one dedicated branch per step, verify changes, and pause for review
before merging into `main`. Do not commit secrets or raw sensitive exports.
The original `instructions.html` is local reference material and is ignored by Git.
No external resources should be created or published without confirmation.
