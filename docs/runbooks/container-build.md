# Build the application container

## Design

- Use digest-pinned, multi-platform Python 3.14.9 Alpine 3.24 and uv 0.9.21 images.
  Step 5.2 adoption changes the application image from glibc to musl; the Jenkins agent
  and host development Python are unchanged. Retest native dependency compatibility.
- The uv stage supplies the build executable. The builder installs locked runtime
  dependencies and the application into `/opt/venv` with
  `uv sync --locked --no-dev --no-editable`.
- The runtime stage uses the same Python base and copies only that environment.
  It does not copy the uv executable, build workspace, or development dependencies.
  Remove the entire inherited pip installation and ensurepip module/bundled wheels from
  the runtime filesystem, not just their SBOMs. Runtime package installation is not needed.
  The builder still installs the locked environment with uv; OS inventories are retained.
- Run as numeric UID/GID `10001:10001`. Installed application files remain root-owned
  and are not writable by the runtime user.
- Start Uvicorn directly with exec-form `CMD`, listening on container port 8000.
  `EXPOSE` is metadata: it does not publish a port on the host.
- `.dockerignore` uses an allowlist for the manifests, README, and application
  source, with additional exclusions for generated files and sensitive local files.
- Do not put credentials in build arguments or copy local secret files into images.

The base-image digests and runtime dependency lock improve repeatability. They do
not establish that an image is vulnerability-free. The isolated packaging backend
still resolves from its declared version range. Step 5.2 adds the
[image gate](image-security.md); its reviewed/publication status is tracked there.

## Build

From the project root with Docker Desktop/Engine running:

```sh
docker build --progress=plain --tag finsecure-pay:task-02-step-01 .
docker image inspect finsecure-pay:task-02-step-01 \
  --format '{{.Id}} {{.Os}}/{{.Architecture}} user={{.Config.User}}'
```

Expect the configured user to be `10001:10001`, not root. This tag is a local
step-specific build tag, not the versioned registry release.
The initial Step 2.1 build verified only `linux/arm64` on Apple Silicon. Step 2.3
subsequently built, tested, and published both ARM64 and AMD64; see the
[image publication runbook](image-publication.md). AMD64 execution was emulated.
Select the managed-cluster node architecture explicitly before cloud deployment.

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
No global Docker settings were modified during verification. After the user
corrected the Docker Hub login, Step 2.3 builds and pushes succeeded with the normal
authenticated configuration; the temporary workaround was not needed for that release.

## Step boundaries

Step 2.1 verifies image construction, configured user, and filesystem contents.
Application execution, actual process identity, port mapping, endpoint requests,
and shutdown behavior are covered by the [Step 2.2 execution runbook](container-execution.md).
Docker/Kubernetes health-probe decisions
will be validated in their appropriate steps. Registry publication is Step 2.3.

See [Step 2.1 evidence](../../evidence/task-02/step-01-dockerfile.md) for actual build
results and limitations.
