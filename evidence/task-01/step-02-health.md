# Step 1.2 — Health endpoint verification

- **Date:** 2026-10-21 UTC; live HTTP verification at 14:10:26 UTC.
- **Branch:** `task-01/step-02-health`, created from the reviewed scaffold on `main`.
- **Revision:** The commit introducing this file contains the verified implementation.
  Retrieve it with `git log -1 --format=%H -- evidence/task-01/step-02-health.md`.
- **Environment:** macOS ARM64, Python 3.14.7, uv 0.9.21.
- **Contract:** [GET /health](../../docs/api-contract.md).

## Checks and actual results

Commands ran from the repository root.

| Check | Command/procedure | Observed result |
| --- | --- | --- |
| Lint | `uv run --locked ruff check .` | All checks passed |
| Formatting | `uv run --locked ruff format --check .` | Passed without changes |
| Tests | `uv run --locked pytest` | 5 passed, 1 warning |
| Packaging | `uv build` | Wheel and source archive built successfully |
| Live GET | Run Uvicorn with the application factory on an OS-assigned loopback port; request `/health` | HTTP 200, `application/json`, `{"status":"healthy"}` |
| Live unsupported method | POST `/health` to the same process | HTTP 405; `Allow: GET` |
| Cleanup | Terminate the test-owned Uvicorn process | Clean application shutdown |

The three new endpoint tests check the response contract, rejected POST method,
and OpenAPI's required `status` field with the literal value `healthy`. The two
existing application-factory tests also pass.

## Test output excerpt

```text
collected 5 items

tests/integration/test_application.py ..
tests/integration/test_health_api.py ...

5 passed, 1 warning in 0.03s
```

The existing Starlette/HTTPX TestClient deprecation warning remains visible. No
new dependency or warning suppression was introduced.

## Reproduction

Start the application in one terminal:

```sh
uv run --locked uvicorn finsecure_pay.main:create_app --factory --host 127.0.0.1 --port 8000
```

In another terminal:

```sh
curl --include --fail --silent --show-error http://127.0.0.1:8000/health
curl --include --silent --show-error --request POST http://127.0.0.1:8000/health
```

Expect HTTP 200 and `{"status":"healthy"}` for GET; expect HTTP 405 for POST.
Stop the server with Ctrl-C. These manual commands use port 8000, whereas the
recorded automated run used a dynamically assigned port to avoid collisions.

## Limits

This is a local application-liveness check, not a test of cloud readiness or
external dependencies. `/validate`, container execution, and Kubernetes probes
remain future work. No remote publication or cloud operations were performed.
