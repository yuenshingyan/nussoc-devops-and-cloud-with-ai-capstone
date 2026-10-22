# Application settings (0.2.0)

Version 0.2.0 adds two optional, non-secret environment settings. Unset variables
retain the approved defaults. An explicitly empty or invalid value fails application
creation/startup; it never silently falls back. Unrelated environment variables are
ignored. No additional settings library or dependency was added.

| Environment variable | Default | Accepted values |
| --- | --- | --- |
| `FINSECURE_MAX_TRANSACTION_AMOUNT` | `10000` | Positive plain decimal string, at most 32 characters and two fractional digits; no sign, exponent, whitespace, NaN, or infinity |
| `FINSECURE_SUPPORTED_CURRENCIES` | `SGD,USD,HKD` | Nonempty comma-separated subset of `SGD`, `USD`, `HKD`; exact uppercase names, no duplicates, whitespace, or empty entries |

The amount limit is inclusive, applies in each enabled currency's own units, and
can be raised or lowered. It is parsed and compared with `Decimal`, never float.
Trailing fractional zeros count toward the two-digit limit. Currency configuration
enables/disables the existing supported currencies; it does **not** add arbitrary
currencies or currency-specific precision rules. Two-decimal precision and all
other validation rules remain unchanged. Adding another currency requires a
separately reviewed policy change.

## Local example

```sh
FINSECURE_MAX_TRANSACTION_AMOUNT=100 \
FINSECURE_SUPPORTED_CURRENCIES=USD \
uv run --locked uvicorn finsecure_pay.main:create_app --factory --host 127.0.0.1 --port 8000
```

With these settings, USD `100.00` is accepted, USD `100.01` returns
`AMOUNT_LIMIT_EXCEEDED`, and SGD `50` returns `UNSUPPORTED_CURRENCY`, assuming the
other fields are valid. Request/response shapes, error ordering, and HTTP statuses
are unchanged. `/health` remains independent of transaction outcomes.

[`.env.example`](../../.env.example) lists defaults for reference. The application
**does not automatically read `.env` files**. Export variables explicitly or use
Docker/Kubernetes environment injection. Do not store secrets in this example.

## Ownership and startup

`create_app()` loads validated, frozen settings into that application's state.
The HTTP dependency passes the settings to the pure validation service, which does
not read environment variables or perform I/O. Multiple applications in one process
can have different settings snapshots. Environment changes after construction do
not alter an existing application; restart it to change its policy.

Invalid settings produce a fixed startup error naming the settings to check,
without echoing invalid values. The server does not start with a partially valid
policy. This is a startup failure, not an HTTP 422 response to a transaction.

## Containers and Kubernetes

The published **0.1.0 image ignores these new settings**. Do not use it to claim
configurable transaction validation. The 0.2.0 candidate must be published and
verified before cloud deployment.

For a locally built 0.2.0 image:

```sh
docker run --rm --read-only --cap-drop=ALL \
  --security-opt=no-new-privileges:true \
  --tmpfs=/tmp:rw,noexec,nosuid,size=16m \
  --publish=127.0.0.1:8000:8000 \
  --env-file deploy/kubernetes/base/configmap.env \
  finsecure-pay:0.2.0-local
```

Stop with Ctrl-C. Port 8000 must be free. The committed ConfigMap input contains
only the default amount limit and currency allowlist. See the
[Kubernetes manifests runbook](kubernetes-manifests.md) for generated configuration
names and rollout considerations.
