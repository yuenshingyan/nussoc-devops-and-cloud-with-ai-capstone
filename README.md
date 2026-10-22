# FinSecure Pay

A Python/FastAPI transaction-validation API and cloud-native DevOps capstone.

## Status

Tasks 1–2 are reviewed and merged locally: application endpoints, test/package
verification, public source, and public ARM64/AMD64 release 0.1.0.
Step 3.1 adds configurable validation policy and draft Kubernetes resources;
210 tests pass. Version 0.2.0 image publication, server-side manifest validation,
runtime safeguards, and all cloud deployment remain pending.

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
docker pull yuenshingyan/finsecure-pay:0.1.0
uv run --locked python scripts/smoke_test.py --image yuenshingyan/finsecure-pay:0.1.0
```

Version `0.1.0` and commit tag `sha-dec0da0` point to the same multi-platform release.
ARM64 and AMD64 passed smoke tests before publication and after pulling their
registry digests; AMD64 was tested under emulation, not on a native cloud node.
See the [image publication runbook](docs/runbooks/image-publication.md) for the
immutable deployment digest, source revision, and exact evidence. This demo release
has not yet passed the security scans planned for Task 5; use synthetic data only.

The published 0.1.0 release has fixed rules and does not consume the new environment
settings. Version 0.2.0 must be separately published and verified; it is not available
from the registry as part of this step yet.

## Kubernetes configuration

```sh
kubectl kustomize deploy/kubernetes/overlays/demo
```

This renders a namespace, two-replica Deployment, internal ClusterIP Service, and
content-hashed ConfigMap without contacting a cluster. The draft image reference
is 0.2.0, pending publication and digest pinning. **Do not apply these manifests yet:**
probes, resource limits, and pod security settings remain Step 3.2. See the
[Kubernetes runbook](docs/runbooks/kubernetes-manifests.md).

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
- Task 3.1: configuration/manifests implemented; 0.2.0 publication and review pending.
- Remaining Task 3: runtime safeguards, provider-specific infrastructure, deployment, and recovery.
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
