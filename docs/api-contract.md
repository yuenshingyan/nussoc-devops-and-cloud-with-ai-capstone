# API contract

## GET /health

Reports that the application is running and can serve an HTTP request. This is an
application liveness signal, not a transaction-validation result or a check of
external systems. It requires no authentication, request body, or parameters.
Do not expose secrets, infrastructure details, or customer data in the response.

### Request

```sh
curl --fail --silent --show-error http://127.0.0.1:8000/health
```

### Successful response

- HTTP status: `200 OK`
- Content type: `application/json`
- Body:

```json
{"status":"healthy"}
```

`status` is required and has the literal string value `healthy`. There are no
timestamps or changing instance details in this response. Clients must inspect the
HTTP response rather than assume a reachable process is always healthy: if the
process is stopped or cannot serve requests, no successful response is guaranteed.

Only `GET` is supported. For example, `POST /health` returns HTTP 405. Framework
method-error responses are not business-validation results.

### Operational scope

The current application has no external runtime dependencies. Do not treat this
endpoint as a dependency-aware readiness check. Kubernetes probe configuration and
any additional readiness semantics will be defined during Task 3.

## POST /validate — pending

This endpoint is not implemented. Before Step 1.3, agree on the transaction fields,
validation rules, currency precision, limits, rejection responses, and HTTP status
codes. See [PLAN.md](../PLAN.md) for the required approval checkpoint.
