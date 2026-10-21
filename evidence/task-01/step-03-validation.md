# Step 1.3 — Transaction validation verification

- **Date:** 2026-10-21 UTC; live HTTP checks at 14:17:08 UTC.
- **Branch:** `task-01/step-03-validation`, based on the reviewed health endpoint.
- **Revision:** The commit introducing this evidence file contains the verified code.
  Retrieve it with `git log -1 --format=%H -- evidence/task-01/step-03-validation.md`.
- **Environment:** macOS ARM64, Python 3.14.7, uv 0.9.21.
- **Contract:** [POST /validate](../../docs/api-contract.md).

## Implementation and scope

- Strict Pydantic request syntax with five required string fields and no extra fields.
- Pure business rules using `Decimal`; no rounding, external I/O, or transfers.
- HTTP 200 for evaluated transactions, with `valid` and ordered error codes.
- HTTP 422 for malformed JSON/schema with redacted error metadata.
- Existing health behavior retained; no new dependencies introduced.

## Checks and actual results

Commands ran from the repository root.

| Check | Command | Observed result |
| --- | --- | --- |
| Lint | `uv run --locked ruff check .` | All checks passed |
| Formatting | `uv run --locked ruff format --check .` | Passed without further changes |
| Unit/API tests | `uv run --locked pytest` | 54 passed, 1 warning |
| Packaging | `uv build` | Version 0.1.0 wheel and source archive built successfully |

The suite contains 15 business-rule unit cases, 34 transaction API cases, and the
5 existing application/health cases. Tests cover accepted currencies, amount
limits, non-positive amounts, precision (including trailing zeros), same-account
rejection, combined errors, case-sensitive identifiers, malformed types/syntax,
missing/unknown fields, safe error responses, method handling, and OpenAPI metadata.

Test summary excerpt:

```text
collected 54 items
54 passed, 1 warning in 0.14s
```

The pre-existing Starlette/HTTPX TestClient deprecation warning remains visible.
No warning suppression was added. Coverage and JUnit reports are deferred to Step 1.4.

## Live HTTP results

Started Uvicorn with the application factory on an OS-assigned loopback port.
Sent real HTTP requests using Python's standard-library HTTP client. All cases
were asserted against the expected status and body, then the owned server process
was terminated and shut down cleanly.

The baseline synthetic request was:

```json
{"transaction_id":"txn_001","sender_id":"account_001","recipient_id":"account_002","amount":"125.50","currency":"SGD"}
```

Observed results:

| Case | Change from baseline | HTTP status | Response |
| --- | --- | --- | --- |
| Health | GET `/health` | 200 | `{"status":"healthy"}` |
| Accepted | None | 200 | `{"valid":true,"errors":[]}` |
| Business rejection | `amount: "0"` | 200 | `{"valid":false,"errors":["AMOUNT_NOT_POSITIVE"]}` |
| Malformed amount | `amount: 125.50` as a JSON number | 422 | Safe `string_type` error at `body.amount` |
| Multiple rejections | `amount: "10000.001"`, `currency: "EUR"`, `recipient_id: "account_001"` | 200 | Ordered limit, currency, precision, and same-account errors |

Actual malformed-request body:

```json
{"detail":[{"loc":["body","amount"],"type":"string_type","msg":"Invalid request value. Check the API contract."}]}
```

Actual multiple-rejection body:

```json
{"valid":false,"errors":["AMOUNT_LIMIT_EXCEEDED","UNSUPPORTED_CURRENCY","AMOUNT_PRECISION_EXCEEDED","SAME_ACCOUNT"]}
```

## Reproduce

Use the start and request commands in the
[local development runbook](../../docs/runbooks/local-development.md). Apply the
request changes in the table above to reproduce each result. Stop Uvicorn with
Ctrl-C. Use synthetic data only.

No cloud resources, registry publication, repository push, authentication,
balance verification, or duplicate-transaction detection are claimed by this step.
