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
`/` and `/validate` still return 404. No environment variables or credentials
are required yet, so there is no `.env.example`.

## Check and test

```sh
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
```

The tests verify schema metadata, independent application instances, and the
health endpoint's response, allowed method, and published schema. They are not
transaction-rule tests; those will be added with `/validate`.

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
