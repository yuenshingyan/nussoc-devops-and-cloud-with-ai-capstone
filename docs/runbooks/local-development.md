# Local development

Run commands from the `capstone/` repository root. Install uv if it is not already
available. This project targets Python 3.14; uv uses `.python-version` to select it.
On the initial development machine, Python 3.14.7 and uv 0.9.21 were available.

## Install

```sh
uv sync --locked
```

This creates a project-local `.venv`, installs the application in editable mode,
and installs development dependencies from `uv.lock`. Activation is unnecessary
when using `uv run`. On a machine without Python 3.14, uv may download a compatible
interpreter. Do not install project dependencies into system Python.

## Start

```sh
uv run --locked uvicorn finsecure_pay.main:create_app --factory --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` for Swagger UI or inspect the schema:

```sh
curl --fail --silent --show-error http://127.0.0.1:8000/openapi.json
```

The schema's `info` contains the title `FinSecure Pay` and version `0.1.0`.
Stop the server with Ctrl-C. Local development binds only to loopback by default.

Check application liveness:

```sh
curl --fail --silent --show-error http://127.0.0.1:8000/health
```

Expect HTTP 200 with `{"status":"healthy"}`. This checks the application itself,
not external dependencies. See the [API contract](../api-contract.md).
The root `/` still returns 404. No environment variables or credentials are
required yet, so there is no `.env.example`.

## Validate a transaction

```sh
curl --include --silent --show-error http://127.0.0.1:8000/validate \
  --header 'Content-Type: application/json' \
  --data '{"transaction_id":"txn_001","sender_id":"account_001","recipient_id":"account_002","amount":"125.50","currency":"SGD"}'
```

Expect HTTP 200 with `{"valid":true,"errors":[]}`. Change `amount` to `"0"` to
get HTTP 200 with `{"valid":false,"errors":["AMOUNT_NOT_POSITIVE"]}`. Change it to
the JSON number `125.50` (without quotes) to get HTTP 422 with safe schema-error
metadata. Exact rules, bounds, and error codes are in the API contract.
Use synthetic data only. This endpoint does not transfer money or check balances.

## Check and test

```sh
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
```

The tests cover application construction, health responses, pure transaction rules,
and the validation API's accepted/rejected/malformed cases. Additional coverage
and Jenkins-compatible reporting are planned for Step 1.4.

The locked Starlette version currently emits a deprecation warning for HTTPX-based
`TestClient`. Tests pass; the warning is not suppressed. Revisit the testing-client
integration when updating dependencies.

## Build

```sh
uv build
```

The wheel and source archive are created in ignored `dist/`. Hatchling is the
Python packaging backend; uv handles environment management and invokes the build.

## Dependency changes

Edit `pyproject.toml`, run `uv lock` and `uv sync --locked`, review the lockfile
changes, and rerun checks. Commit both dependency declarations and lockfile.
Routine development and CI should use `--locked` so an outdated lockfile fails
rather than being silently rewritten.
