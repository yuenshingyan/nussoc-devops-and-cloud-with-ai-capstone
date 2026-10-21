# Run and validate the container locally

## Automated smoke test

Prerequisites: Docker Desktop/Engine running, uv, the project dependencies, and the
local image from [Step 2.1](container-build.md). From the repository root:

```sh
uv run --locked python scripts/smoke_test.py
```

To test another explicitly chosen local reference:

```sh
uv run --locked python scripts/smoke_test.py --image finsecure-pay:task-02-step-01
```

The script resolves the supplied tag to an immutable local image ID. It never pulls
an image, so a missing local image is an error rather than permission to download
or run an unrelated remote image. Build it first if necessary. If only its tag is
missing, verify the known image ID against build evidence before restoring the tag.

### What it checks

1. Create and start a uniquely identified container from the resolved image ID.
2. Publish container port 8000 on an OS-assigned **127.0.0.1** host port only.
3. Wait for HTTP 200 and `{"status":"healthy"}` from `/health`.
4. Read `/proc/1/status` to check the actual PID 1 UID/GID values are all 10001.
5. POST synthetic accepted, business-rejected, and malformed-amount requests.
6. Stop with a 10-second graceful-shutdown window; require exit code 0 and no OOM kill.
7. Remove only the owned test container and print a JSON result after cleanup succeeds.

No volume mounts, registry login, image push, cloud services, or real customer data
are involved. Docker's default local bridge networking is used, but the host's
published port is restricted to loopback. HTTP requests bypass host proxy settings.

### Runtime restrictions

- Read-only root filesystem.
- All Linux capabilities dropped.
- `no-new-privileges` enabled.
- A 16 MiB writable `/tmp` tmpfs with `noexec` and `nosuid`.
- Non-root identity from the Dockerfile; the script does not override it.

These are local verification settings, not a complete production security policy.
The smoke test does not perform vulnerability scanning or set cloud resource limits.

### Deadlines and cleanup

- Docker commands have a 30-second timeout by default.
- Health startup polling has a 30-second monotonic deadline. Its Docker inspect and
  HTTP calls are bounded by the remaining time; each HTTP call is at most 2 seconds.
- Only the startup GET health check is retried, at intervals up to 0.2 seconds.
  Business POST requests are sent once each, without automatic retries.
- Any failed check exits nonzero. Once the container ID is known, a `finally` block
  attempts to remove that owned container, including on ordinary interruptions.
- The container ID is printed to stderr immediately after creation. If the process
  is forcibly killed or the daemon becomes unreachable, automatic cleanup cannot
  be guaranteed. Inspect and remove **that ID only** once Docker is available;
  do not prune unrelated containers or images.

To save results without masking failures in a pipeline:

```sh
mkdir -p reports
set -o pipefail
uv run --locked python scripts/smoke_test.py | tee reports/container-smoke.json
```

A JSON result is written only after all checks and cleanup succeed. Check the exit
status; do not mistake an empty or stale file for successful evidence. The captured
loopback URL is historical after the script removes its container.

## Manual troubleshooting

For interactive inspection, use a separate local container and remove it afterward:

```sh
container=$(docker run --detach --pull=never \
  --read-only --cap-drop=ALL --security-opt=no-new-privileges:true \
  --tmpfs=/tmp:rw,noexec,nosuid,size=16m \
  --publish=127.0.0.1:8000:8000 finsecure-pay:task-02-step-01)
docker logs "$container"
curl --fail --silent --show-error http://127.0.0.1:8000/health
# Use the /validate examples in docs/api-contract.md for transaction checks.
docker stop --timeout=10 "$container"
docker rm "$container"
```

If host port 8000 is in use, choose another host port and adjust the curl URL.
The automated test avoids this collision by requesting an OS-assigned port.
Manual commands do not install a cleanup trap: if a check fails, still stop/remove
only the container you created. Use synthetic data only and keep logs sanitized.

See [Step 2.2 evidence](../../evidence/task-02/step-02-container-validation.md) for
actual execution and cleanup results. See the [image publication runbook](image-publication.md)
for Step 2.3's public registry release and digest-pinned pull commands.
