# Build the application container

## Design

- Use digest-pinned, multi-platform Python 3.14.7 slim-bookworm and uv 0.9.21 images.
- The uv stage supplies the build executable. The builder installs locked runtime
  dependencies and the application into `/opt/venv` with
  `uv sync --locked --no-dev --no-editable`.
- The runtime stage uses the same Python base and copies only that environment.
  It does not copy the uv executable, build workspace, or development dependencies.
  The official Python base still includes its own standard packaging utilities.
- Run as numeric UID/GID `10001:10001`. Installed application files remain root-owned
  and are not writable by the runtime user.
- Start Uvicorn directly with exec-form `CMD`, listening on container port 8000.
  `EXPOSE` is metadata: it does not publish a port on the host.
- `.dockerignore` uses an allowlist for the manifests, README, and application
  source, with additional exclusions for generated files and sensitive local files.
- Do not put credentials in build arguments or copy local secret files into images.

The base-image digests and runtime dependency lock improve repeatability. They do
not establish that an image is vulnerability-free. The isolated packaging backend
still resolves from its declared version range; security scans and gates are Task 5.

## Build

From the project root with Docker Desktop/Engine running:

```sh
docker build --progress=plain --tag finsecure-pay:task-02-step-01 .
docker image inspect finsecure-pay:task-02-step-01 \
  --format '{{.Id}} {{.Os}}/{{.Architecture}} user={{.Config.User}}'
```

Expect the configured user to be `10001:10001`, not root. This tag is a local
step-specific build tag, not the versioned registry release planned in Step 2.3.
The initial verified build targets `linux/arm64` on the current Apple Silicon
machine. The upstream image indexes also include AMD64, but an AMD64 application
build has not been verified. Select the cloud node/image architecture before publishing.

Keep Docker context outside `.venv`, evidence, and raw build/test reports. Rebuild
after application or dependency changes. Update base-image digests deliberately and
rerun verification; do not silently substitute `latest`.

## Docker Desktop metadata timeout workaround (macOS)

On the initial machine, the normal Docker configuration timed out while reading
both public registries. Direct registry HTTP requests worked. The same image lookup
and build succeeded with an empty temporary Docker configuration and the same
Docker Desktop daemon. This points to the credential-helper/configuration path;
it does not identify the exact internal helper failure.

For **public-image pulls only**, a temporary configuration can isolate this issue
without deleting or changing saved credentials:

```sh
(
  set -eu
  endpoint=$(docker context inspect desktop-linux --format '{{.Endpoints.docker.Host}}')
  scratch=$(mktemp -d)
  trap 'rm -rf "$scratch"' EXIT
  DOCKER_CONFIG="$scratch" DOCKER_HOST="$endpoint" \
    /Applications/Docker.app/Contents/Resources/cli-plugins/docker-buildx build \
    --load --progress=plain --tag finsecure-pay:task-02-step-01 .
)
```

This command uses the Docker Desktop plugin path on macOS; other environments
should use their normal Docker setup. Anonymous pulls may be rate-limited. Do not
use the empty configuration for private registries or authenticated pushes. Repair
or approve changes to the normal credential setup separately if publishing needs it.
No global Docker settings were modified during verification.

## Step boundaries

Step 2.1 verifies image construction, configured user, and filesystem contents.
Application execution, actual process identity, port mapping, endpoint requests,
and shutdown behavior are covered by the [Step 2.2 execution runbook](container-execution.md).
Docker/Kubernetes health-probe decisions
will be validated in their appropriate steps. Registry publication is Step 2.3.

See [Step 2.1 evidence](../../evidence/task-02/step-01-dockerfile.md) for actual build
results and limitations.
