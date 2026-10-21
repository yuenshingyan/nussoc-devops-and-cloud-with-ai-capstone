# Step 1.5 — Packaging and GitHub publication verification

- **Date:** 2026-10-21 UTC.
- **Branch:** `task-01/step-05-source-publication`.
- **Verified application/test commit:** `277e44b4009410742027bea92654b8e5fdb54d63`.
- **Environment:** macOS ARM64, Python 3.14.7, uv 0.9.21.
- **Scope:** Recheck approved application/tests, validate installed packages, publish
  reviewed source, and verify public evaluator access. This step adds documentation
  and evidence, not application behavior or dependency changes.

## Build and tests

Executed before documentation changes in this step:

```sh
uv run --locked ruff check .
uv run --locked ruff format --check .
./scripts/test.sh
uv build
```

- Lint/format checks passed.
- 167 tests passed in 0.40 seconds, with the existing Starlette/HTTPX deprecation warning.
- Coverage remained 72/72 executable lines and 14/14 branch outcomes.
- Built `finsecure_pay-0.1.0-py3-none-any.whl` and `finsecure_pay-0.1.0.tar.gz`.

Hashes of the exact artifacts tested from the application/test commit above:

```text
f608544036df2170eec7c9d623e374cec50de514b8de15d2cf454c7f04da2120  finsecure_pay-0.1.0-py3-none-any.whl
5d6624c190398570db518ad6ecf9e2afe1141eed285f73c801f4ae37778f4397  finsecure_pay-0.1.0.tar.gz
```

A later rebuild containing changed README/documentation files may have different
hashes; these identify the actual tested artifacts, not all future version-0.1.0 builds.

## Isolated installation and HTTP checks

Exported runtime dependencies with `uv export --locked --no-dev --no-emit-project`
and installed them with `uv pip sync --require-hashes` into two newly created
virtual environments. Installed each built artifact with `--no-deps` into its
respective environment; neither was installed in editable mode.

| Check | Wheel | Source distribution |
| --- | --- | --- |
| Fresh runtime dependencies | 14 installed | 14 installed |
| Application version | 0.1.0 | 0.1.0 |
| `uv pip check` | 15 compatible packages | 15 compatible packages |
| Application import location | Inside fresh environment | Inside fresh environment |
| GET `/health` | HTTP 200, healthy | HTTP 200, healthy |
| POST `/validate`, amount `"125.50"` | HTTP 200, valid | HTTP 200, valid |
| POST `/validate`, amount `"0"` | HTTP 200, `AMOUNT_NOT_POSITIVE` | HTTP 200, `AMOUNT_NOT_POSITIVE` |
| POST `/validate`, numeric amount `125.50` | HTTP 422, safe `string_type` detail | HTTP 422, safe `string_type` detail |
| Process cleanup | Clean shutdown | Clean shutdown |

Wheel checks started at **14:24:46 UTC** and source-distribution checks at
**14:24:48 UTC**. Servers ran with Python isolated mode (`-I`) from a temporary
working directory, using OS-assigned loopback ports. Import paths were asserted
to belong to the temporary environment, not the checkout. Temporary environments
were removed after verification.

Package manifests were inspected: required application code was present, the
source distribution included `uv.lock`, and both artifacts excluded local agent/
assignment files, `.git`, `.venv`, `.env`, `.coverage`, and raw `reports/` paths.
This file-path inspection is not a substitute for the later security scans.

## Actual publication

The user approved publication to the configured repository. Executed:

```sh
git push --atomic -u origin main \
  task-01/step-01-scaffold task-01/step-02-health \
  task-01/step-03-validation task-01/step-04-tests
git ls-remote --heads origin
```

The push succeeded without force-pushing. Remote heads matched:

| Branch | Commit |
| --- | --- |
| `main` | `277e44b4009410742027bea92654b8e5fdb54d63` |
| `task-01/step-01-scaffold` | `08493b854e7bdd461e3abd11145695833b59c182` |
| `task-01/step-02-health` | `e9f1bf2976f20084c65a81ef67df842090257c6f` |
| `task-01/step-03-validation` | `f08bb632cc87a9ce9deccbdc8984e9720e673b23` |
| `task-01/step-04-tests` | `277e44b4009410742027bea92654b8e5fdb54d63` |

## Anonymous evaluator access

At **14:25:19 UTC**, HTTP requests without an Authorization header or browser-cookie
session verified:

- GitHub repository API: HTTP 200; `private: false`.
- [Public main branch](https://github.com/yuenshingyan/nussoc-devops-and-cloud-with-ai-capstone/tree/main): HTTP 200.
- Raw `src/finsecure_pay/main.py`, `pyproject.toml`, and
  `evidence/task-01/step-04/junit.xml` at commit `277e44b4009410742027bea92654b8e5fdb54d63`:
  HTTP 200; bytes matched local tracked files exactly.

The default branch was still `task-01/step-01-scaffold`. No repository setting was
changed. Use the explicit `main` link for assessment until a change of default
branch is approved. This establishes public access from the verification network,
not a guarantee about an evaluator's separate network restrictions.

## Limits and reproduction

- This evidence captures reviewed application/test source already published on
  `main`; the Step 1.5 documentation itself remains subject to review before merge.
- No API cloud deployment, container push, or Python package-index upload occurred.
- The build backend resolves from its declared version range; runtime dependencies
  were locked and hash-checked.
- Follow the [publication runbook](../../docs/runbooks/source-publication.md) to
  reproduce clean artifact installation and HTTP checks.
