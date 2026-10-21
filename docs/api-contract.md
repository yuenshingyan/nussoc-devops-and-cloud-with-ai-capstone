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

## POST /validate

Validates a synthetic transaction without transferring money or performing I/O.
The following fields and rules are project design choices approved for Step 1.3;
the assignment itself does not prescribe a payload schema.

### Request

Send `Content-Type: application/json` and a JSON object with exactly these five
required fields. All values must be strings; values are not silently coerced,
trimmed, case-folded, or Unicode-normalized.

```json
{
  "transaction_id": "txn_001",
  "sender_id": "account_001",
  "recipient_id": "account_002",
  "amount": "125.50",
  "currency": "SGD"
}
```

| Field | Syntactic requirements |
| --- | --- |
| `transaction_id` | 1–64 ASCII letters, digits, underscores, or hyphens |
| `sender_id` | Same identifier syntax; case-sensitive |
| `recipient_id` | Same identifier syntax; case-sensitive |
| `amount` | 1–32 characters; plain decimal string matching `-?[0-9]+(\.[0-9]+)?` in full |
| `currency` | Exactly three uppercase ASCII letters |

Amount strings may contain a leading minus sign, which allows the business rules
to report negative amounts as rejected transactions. Leading zeros are accepted.
Do not send a leading plus sign, exponent notation, whitespace, `NaN`, infinity,
a leading/trailing decimal point, Unicode digits, or a JSON number. Nulls and
unknown fields are rejected rather than ignored.

### Business rules

| Order | Rule | Rejection code |
| --- | --- | --- |
| 1 | Amount must be strictly greater than zero | `AMOUNT_NOT_POSITIVE` |
| 2 | Amount must be at most 10,000, inclusive | `AMOUNT_LIMIT_EXCEEDED` |
| 3 | Currency must be SGD, USD, or HKD | `UNSUPPORTED_CURRENCY` |
| 4 | Amount must have at most two fractional digits | `AMOUNT_PRECISION_EXCEEDED` |
| 5 | Sender and recipient identifiers must differ | `SAME_ACCOUNT` |

The amount limit applies separately in each supported currency. No currency
conversion is performed. Monetary values are compared with `Decimal`, without a
floating-point intermediate or rounding. Fractional digit counts include trailing
zeros: `"1.00"` is accepted, but `"1.000"` is rejected. Negative zero is rejected.
The precision check applies even when the currency is unsupported.

These defaults are currently constants in `services/validation.py`. Runtime
configuration will be introduced when needed for the Kubernetes configuration step;
no undocumented environment overrides are implemented now.

### Accepted transaction — HTTP 200

```json
{"valid":true,"errors":[]}
```

### Business-rule rejection — HTTP 200

```json
{"valid":false,"errors":["AMOUNT_NOT_POSITIVE"]}
```

Both outcomes mean the request was successfully evaluated. Return every applicable
error code, once each, in the order shown in the table. `valid` is true if and only
if `errors` is empty. Errors are codes, not copied request values.
For example, amount `"10000.001"`, currency `"EUR"`, and identical accounts yield:

```json
{
  "valid": false,
  "errors": [
    "AMOUNT_LIMIT_EXCEEDED",
    "UNSUPPORTED_CURRENCY",
    "AMOUNT_PRECISION_EXCEEDED",
    "SAME_ACCOUNT"
  ]
}
```

### Malformed JSON or request schema — HTTP 422

Missing fields, unknown fields, incorrect types, invalid identifier/currency syntax,
and malformed or overlong amount strings do not reach business validation.
For example, a JSON number instead of an amount string returns:

```json
{
  "detail": [
    {
      "loc": ["body", "amount"],
      "type": "string_type",
      "msg": "Invalid request value. Check the API contract."
    }
  ]
}
```

`detail` contains schema error metadata only. `type` is the framework's error code;
`msg` is a fixed safe message. Locations name only documented fields. Unknown field
names and malformed JSON locations use `["body"]`, since arbitrary keys may contain
sensitive input. Do not return raw input, parser context, exception text, or stack
traces. Multiple schema errors may be reported; their order is not guaranteed.
HTTP/transport errors outside JSON/schema validation may use framework responses.

### Example call

```sh
curl --fail --silent --show-error http://127.0.0.1:8000/validate \
  --header 'Content-Type: application/json' \
  --data '{"transaction_id":"txn_001","sender_id":"account_001","recipient_id":"account_002","amount":"125.50","currency":"SGD"}'
```

### Scope and limitations

- No authentication is implemented at this stage; use synthetic data and local
  loopback access. This is not a production payment-processing service.
- No balance checks, account-existence checks, duplicate-transaction detection,
  persistence, or external calls are performed.
- Repeating a request repeats validation; `transaction_id` is a required identifier,
  not an idempotency or deduplication mechanism.
- Only POST is supported; GET `/validate` returns HTTP 405.
- External exposure and operational safeguards remain later deployment steps.
