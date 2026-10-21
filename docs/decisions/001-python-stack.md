# ADR 001 — Python application stack

## Decision

Use Python 3.14, FastAPI, Pydantic, uv, pytest, and HTTPX for this capstone.
Use Uvicorn to serve the ASGI application and Hatchling as the packaging backend.
Use Ruff for formatting, linting, and import sorting.

## Context and justification

The assignment recommends Spring Boot, Maven, and JUnit but permits equivalent
application/build/testing tools with justification. The author is familiar with
Python rather than Java. Using a familiar language supports understanding and
explaining the implementation during the individual demonstration.

- **FastAPI** supplies HTTP routing and OpenAPI documentation in place of Spring Boot.
- **Pydantic** supplies typed request/response models and explicit boundary validation.
- **uv and Hatchling** provide dependency/environment management and Python packaging
  in place of Maven. Commit `uv.lock`; use locked installs to reproduce runtime and
  development dependency versions.
- **pytest and HTTPX** provide unit/API tests in place of JUnit. pytest supports
  JUnit-compatible reports for Jenkins; pytest-cov supports later coverage reporting.
- **Python 3.14** is already available locally (3.14.7 at initial verification).
  The project targets that minor version; `.python-version` and `requires-python`
  must remain consistent. Containers and Jenkins agents must use the same minor line.

Jenkins remains the CI/CD tool; no alternative CI/CD approval is assumed.

## Design

Use the `src/` layout and an application factory so tests can create independent
application instances. Keep HTTP handlers, schema validation, transaction rules,
and instrumentation in separate packages. No database is needed to validate a
transaction. Monetary arithmetic will use `Decimal` with an agreed API contract.

## Consequences and limitations

- The dependency lock covers application/development packages; the build backend is
  declared with a version range and resolved in an isolated build environment.
- Python version changes require dependency and build verification.
- The locked Starlette TestClient currently warns that its HTTPX integration is
  deprecated. Preserve that warning and review client compatibility when updating
  dependencies; do not silently suppress it or add an unapproved replacement.
- At Step 1.1 only the application factory and automatic documentation routes exist.
  Business endpoints, security scans, and cloud execution are future steps.
