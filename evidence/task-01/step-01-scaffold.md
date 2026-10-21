# Step 1.1 — Scaffold verification

- **Date:** 2026-10-21 UTC; live HTTP/package checks at 14:07:22 UTC.
- **Branch:** `task-01/step-01-scaffold`.
- **Revision:** The commit introducing this evidence file contains the verified
  application/configuration. Retrieve it with
  `git log -1 --format=%H -- evidence/task-01/step-01-scaffold.md`.
- **Environment:** macOS ARM64, Python 3.14.7, uv 0.9.21.
- **Scope:** Local installation, application startup, scaffold tests, and packaging
  only. No transaction validation, container, CI, or cloud validation is claimed.

## Commands and observed results

Run commands from the repository root. These are recorded execution results, not
an assertion that the remaining Task 1 requirements are complete.

| Check | Command/procedure | Observed result |
| --- | --- | --- |
| Clean installation | Create a new temporary directory; set `UV_PROJECT_ENVIRONMENT` to its `venv` path; run `uv sync --locked` | Installed 26 packages into the fresh environment |
| Clean environment import | In that environment, run `uv run --locked python -c 'from finsecure_pay.main import create_app; print(create_app().title)'` | `FinSecure Pay` |
| Project environment | `uv sync --locked` | Successful |
| Lint | `uv run --locked ruff check .` | `All checks passed!` |
| Formatting | `uv run --locked ruff format --check .` | Successful; no formatting changes required |
| Scaffold tests | `uv run --locked pytest` | 2 passed, 1 warning |
| Build | `uv build` | Created wheel and source archive for version 0.1.0 |
| Live schema | Start Uvicorn with the application factory on a dynamically allocated loopback port; GET `/openapi.json` | HTTP 200; title `FinSecure Pay`, version `0.1.0` |
| Live docs | GET `/docs` on the same server | HTTP 200 |
| Shutdown | Terminate the test-owned Uvicorn process after checks | Application shutdown complete |
| Package inspection | Inspect source archive and wheel using Python `tarfile` and `zipfile` | Wheel includes `finsecure_pay/main.py`; source archive excludes `instructions.html`, `AGENTS.md`, `.git`, and `.venv` |

The temporary clean environment was removed after verification. The local
`.venv` and `dist/` artifacts are ignored, not committed.

## Test output excerpt

```text
collected 2 items

tests/integration/test_application.py .. [100%]

2 passed, 1 warning in 0.01s
```

The tests verify OpenAPI metadata and separate application instances. They do not
test `/health` or `/validate`, which have not been implemented.

## Known warning

```text
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

This is an upstream warning from the locked testing stack, not a failed test.
It remains visible. No suppression or replacement dependency was introduced.
Review compatibility before a future dependency update.

## Reproduce the live check manually

In one terminal:

```sh
uv run --locked uvicorn finsecure_pay.main:create_app --factory --host 127.0.0.1 --port 8000
```

In another:

```sh
curl --fail --silent --show-error http://127.0.0.1:8000/openapi.json
curl --fail --silent --show-error --output /dev/null --write-out '%{http_code}\n' http://127.0.0.1:8000/docs
```

Stop the server with Ctrl-C. This manual reproduction uses port 8000; the recorded
automated check used an OS-assigned port to avoid conflicts with other processes.
