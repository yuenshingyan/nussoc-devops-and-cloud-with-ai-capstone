# Step 2.1 — Container definition and build verification

- **Date:** 2026-10-21 UTC; final image inspection at 14:40:08 UTC.
- **Branch:** `task-02/step-01-dockerfile`.
- **Revision:** The commit introducing this evidence contains the verified Dockerfile
  and build inputs. Retrieve it with
  `git log -1 --format=%H -- evidence/task-02/step-01-dockerfile.md`.
- **Host:** macOS ARM64; Docker Desktop 4.81.0, Docker Engine 29.6.1.
- **Build target:** `linux/arm64`.

## Approved repository housekeeping

Step 1.5 was merged into `main` and pushed. Following explicit approval, GitHub's
default branch was changed to `main` and verified through repository metadata.
Repository visibility remained public. The Docker implementation is a separate
step branch; no image was published to a registry.

## Definition

- Multi-stage image with digest-pinned Python 3.14.7 slim-bookworm and uv 0.9.21.
- Locked runtime installation using `uv sync --locked --no-dev --no-editable`.
- Runtime stage receives `/opt/venv`, not the builder workspace or uv executable.
- Numeric non-root user `10001:10001`, exec-form Uvicorn command, port 8000 metadata.
- `.dockerignore` allowlist excludes tests, evidence, local environments, raw reports,
  Git metadata, and other files not required to package the application.

Public registry responses confirmed both pinned multi-platform index digests:

```text
Python: sha256:82bc3c539b8813ada9d68c63b40158fa002f7f33de9bf3312a3dfdc0620dff56
uv:     sha256:15f68a476b768083505fe1dbfcc998344d0135f0ca1b8465c4760b323904f05a
```

Those indexes include ARM64 and AMD64 images. Only the ARM64 application build was
verified here; index availability is not evidence of an AMD64 application test.

## Actual build results and environment issue

The initial normal-config `docker build` failed with `DeadlineExceeded` while
fetching metadata from both public registries. Buildx image inspection also timed
out. Direct host HTTP registry access succeeded.

An image lookup and then the full build succeeded using an empty temporary
`DOCKER_CONFIG`, the existing Docker Desktop daemon endpoint, and the installed
Docker Desktop Buildx plugin. This bypassed use of saved credentials for public
pulls without modifying global configuration or deleting credentials. It points
to the credential-helper/configuration path, not a confirmed internal root cause.
The temporary directory was removed afterward.

With that same temporary configuration:

- Buildx `build --check --progress=plain .`: **no warnings found**.
- Buildx `build --load --progress=plain --tag finsecure-pay:task-02-step-01 .`:
  **successful**, with 15 runtime distributions installed.
- Final build context reported **58.72 kB** transferred.

The exact workaround and normal build commands are in the
[container build runbook](../../docs/runbooks/container-build.md).

## Final image inspection

| Property | Observed result |
| --- | --- |
| Local tag | `finsecure-pay:task-02-step-01` |
| Image ID | `sha256:fffeface88beac332683cfbf3ed9beeeda468e95155aaa245129d5b23f1bba78` |
| Platform | `linux/arm64` |
| Local uncompressed size | 157,936,439 bytes |
| Configured runtime user | `10001:10001` |
| Working directory | `/app` |
| Exposed container port | `8000/tcp` |

The image ID is a local image identifier, **not a published registry manifest digest**.

A temporary container was created but never started. Its filesystem was exported
for inspection, and both the container and exported archive were removed afterward.
Assertions confirmed:

- An `app` account with UID/GID 10001 exists in `/etc/passwd`.
- The virtual environment contains 15 runtime distributions including the application.
- pytest, pytest-cov, Ruff, HTTPX, and coverage development distributions are absent
  from that environment.
- The uv executable and `/build` workspace are absent from the final filesystem.
- Selected application modules are owned by root with no group/other write bits.

This verifies image configuration and contents, **not the identity of a running
application process**. Actual container execution and endpoint tests are Step 2.2.

## Other verification

- `uv run --locked ruff check .`: passed.
- `uv run --locked ruff format --check .`: passed.
- `./scripts/test.sh`: 167 passed, 1 existing Starlette/HTTPX deprecation warning.
- Measured coverage remains 72/72 lines and 14/14 branch outcomes.
- `uv build`: wheel and source archive built successfully.

## Preserved evidence

- [Initial failed build](step-01/initial-build-failure.txt)
- [Dockerfile build checks](step-01/dockerfile-check.txt)
- [Final successful build](step-01/build-output.txt)
- [Image/filesystem inspection](step-01/image-inspection.json)

Build logs are retained from actual executions with Docker Desktop dashboard links
removed and trailing whitespace trimmed. No Docker application process was started,
no host port was published,
and no container image push, vulnerability scan, or cloud deployment is claimed.
