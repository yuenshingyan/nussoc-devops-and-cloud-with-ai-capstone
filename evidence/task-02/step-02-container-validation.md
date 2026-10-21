# Step 2.2 — Local container execution and endpoint verification

- **Date:** 2026-10-21 UTC; final successful smoke test at 14:50:56 UTC.
- **Branch:** `task-02/step-02-container-validation`.
- **Revision:** The commit introducing this file contains the verified smoke script.
  Retrieve it with `git log -1 --format=%H -- evidence/task-02/step-02-container-validation.md`.
- **Application image:** The unchanged Step 2.1 ARM64 image, built from the inputs
  committed in `f3449db`. No application code or dependency versions changed here.

## Actual runtime results

Executed from the repository root:

```sh
uv run --locked python scripts/smoke_test.py
```

| Property | Observed result |
| --- | --- |
| Image tag | `finsecure-pay:task-02-step-01` |
| Image ID | `sha256:fffeface88beac332683cfbf3ed9beeeda468e95155aaa245129d5b23f1bba78` |
| Platform | `linux/arm64` |
| Host binding | `127.0.0.1:51005` to container port 8000 |
| Actual PID 1 identity | Real/effective/saved/filesystem UID and GID all 10001 |
| Root filesystem | Read-only |
| Linux capabilities | All dropped |
| Privilege escalation | `no-new-privileges:true` |
| Temporary filesystem | `/tmp`, 16 MiB, writable, `noexec`, `nosuid` |
| Graceful shutdown | Exit code 0; no OOM kill |
| Cleanup | Owned container removed; independently confirmed absent from `docker container ls --all` |

The loopback endpoint is historical, not a currently running service. No host port
remains published by this smoke test.

## HTTP checks

All checks were real requests through the published Docker port, not mocked calls
or FastAPI TestClient requests.

| Case | HTTP status | Observed body |
| --- | --- | --- |
| GET `/health` | 200 | `{"status":"healthy"}` |
| Valid POST `/validate` | 200 | `{"valid":true,"errors":[]}` |
| Zero-amount POST `/validate` | 200 | `{"valid":false,"errors":["AMOUNT_NOT_POSITIVE"]}` |
| Numeric rather than string amount | 422 | Safe `string_type` detail for `body.amount`, with no echoed input |

The baseline request used synthetic `txn_001`, distinct `account_001`/
`account_002` identifiers, amount `"125.50"`, and currency `"SGD"`.

## Failure handling and local tag recovery

Initial runs failed before container creation because Docker could not resolve the
local step tag. The previously recorded image ID was still inspectable. The tag
was restored to that exact ID with `docker tag`; subsequent runs passed. The
underlying reason for the tag lookup failure was not established. No image pull,
rebuild, remote registry change, or global Docker configuration change was needed.

A separate deliberate missing-image check used the nonexistent all-zero SHA256
reference. The script returned nonzero, created no container, and emitted no success
JSON. This confirms it does not silently pull an image or report success on lookup
failure. Other failure paths have not been exhaustively fault-injected.

Once a container ID is known, the script attempts cleanup in `finally`. An
uncatchable interruption or inaccessible Docker daemon can still require manual
cleanup of the printed owned container ID; no unrelated resources are pruned.

## Other verification

- Ruff lint and formatting checks passed.
- 167 application unit/API tests passed in 0.39 seconds, with the existing
  Starlette/HTTPX TestClient deprecation warning.
- Measured application coverage remained 72/72 lines and 14/14 branch outcomes.
  This measurement covers `src/finsecure_pay`, not the operational smoke script.
- `uv build` produced the wheel and source archive successfully.

## Evidence and reproduction

- [Actual smoke-test JSON](step-02/smoke-result.json), preserved from the final
  successful script output without changing result values.
- [Container execution runbook](../../docs/runbooks/container-execution.md), including
  the exact runtime restrictions, deadlines, manual diagnostics, and cleanup steps.

Only local execution was performed. No registry login/push, cloud deployment,
external payment operation, vulnerability scan, or AMD64 execution is claimed.
