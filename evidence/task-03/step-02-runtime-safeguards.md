# Step 3.2 — Health and runtime safeguards

- **Date:** 2026-10-22 UTC; ARM64 check completed at 06:19:59, AMD64 at 06:20:05.
- **Branch:** `task-03/step-02-runtime-safeguards`.
- **Manifest revision:** The commit introducing this note contains the verified
  manifest; retrieve it with
  `git log -1 --diff-filter=A --format=%H -- evidence/task-03/step-02-runtime-safeguards.md`.
- **Baseline:** Reviewed Step 3.1 (`d87d2c5`) was merged and pushed to `main` before
  this branch was created. No application code or dependency changes were made.
- **Image:** Unchanged published 0.2.0 index
  `sha256:48ee0ef91737fd2ee1d2efea93cf9a94e840eec6908bde6ed3af7afede884e99`,
  built from source `ada935d033cd13f85e5e4adfed2d1e9ac449f6f8`.

## Implemented configuration

The Deployment now declares:

- Startup/readiness/liveness HTTP probes on `/health`, named port `http`.
- Startup: period 2 s, timeout 2 s, 30 failures; readiness: 5 s, 2 s, 2 failures;
  liveness: 10 s, 2 s, 3 failures. Each needs one successful probe.
- CPU/memory requests `100m`/`128Mi`, limits `500m`/`256Mi`.
- Numeric non-root UID/GID 10001, filesystem group 10001, RuntimeDefault seccomp,
  no privilege escalation, all capabilities dropped, and a read-only root filesystem.
- Service-account token automount disabled; writable memory-backed `/tmp` capped at 16 MiB.
- Two replicas with RollingUpdate, zero unavailable and one surge pod; five seconds
  minimum readiness for Deployment availability, 600-second progress deadline, and
  30-second termination grace.

The [runtime policy](../../docs/runbooks/runtime-safeguards.md) documents reasons,
probe semantics, surge/termination capacity, QoS, provisional sizing, and limitations.
These are not production sizing, a zero-downtime guarantee, or an automatic rollback policy.

## Local manifest checks

The base and demo overlay both rendered successfully with local Kustomize. Parsed
checks verified all four resource kinds, namespace/selector/port consistency,
unchanged image digest and settings defaults, ConfigMap/volume references, and every
probe, resource, security, and rollout value above. The Service remains internal
ClusterIP and does not enable routing to unready pods.

Reproduce the demo checks from the repository root using kubectl and the host's
existing Ruby standard-library safe YAML loader (no project dependency was added):

```sh
mkdir -p reports
kubectl kustomize deploy/kubernetes/overlays/demo > reports/step32-demo.yaml
ruby -ryaml -rjson -e 'puts JSON.generate(YAML.parse_stream(STDIN.read).children.map { |doc| stream = Psych::Nodes::Stream.new; stream.children << doc; YAML.safe_load(stream.to_yaml) })' \
  < reports/step32-demo.yaml > reports/step32-demo.json
uv run --locked python - reports/step32-demo.json \
  < evidence/task-03/step-02/manifest-check.py.txt
```

These assert the intended configuration, not Kubernetes API schema/admission validity.
**No cluster was contacted and no resources were applied.**

## Actual constrained-container checks

The previously published platform digest references were resolved to their existing
local image IDs; no image was rebuilt, pulled, or published in this step. Each
matched its recorded release config digest and source-revision label. ARM64 ran
natively in Docker Desktop's Linux VM; AMD64 used emulation on the ARM64 host.

Each owned loopback-only container used 0.5 CPU and 256 MiB memory limits, no swap,
UID/GID 10001, read-only root storage, dropped capabilities, no-new-privileges, the
Docker daemon's built-in seccomp profile, and a 16 MiB writable tmpfs. Real checks
verified:

- 25 sequential accepted transactions, a zero-amount rejection, a malformed numeric
  amount rejection, and healthy HTTP response after both rejection cases.
- Actual PID 1 UID/GID 10001, `NoNewPrivs: 1`, `Seccomp: 2`, and zero effective,
  permitted, bounding, and ambient capabilities.
- Read-only root mount through `statvfs`, temporary-file write/read/removal, and
  16 MiB temporary filesystem capacity with group 10001.
- Cgroup v2 CPU quota `50000 100000` (0.5 CPU), memory maximum `268435456` bytes,
  and no recorded OOM or OOM-kill events.
- Exit 0 on graceful stop, no OOM kill, and independent confirmation that the owned
  container was removed afterward.

| Platform | Local startup observation | Observed cgroup memory peak | Local shutdown observation |
| --- | --- | --- | --- |
| ARM64 | 2.61 s | 84.77 MiB | 0.44 s |
| Emulated AMD64 | 4.06 s | 111.05 MiB | 0.52 s |

Times include Docker CLI/polling overhead. Memory peaks include the inspection
process and charged cache, not just API RSS. These are short smoke observations,
not a workload benchmark or proof of sufficient production capacity.

The [runtime harness](step-02/runtime-check.py.txt) requires local Docker with cgroup v2
and a compatible native architecture or emulation. Example using the already-pulled
ARM64 image (the harness never pulls automatically):

```sh
reference=yuenshingyan/finsecure-pay@sha256:fa11c7014e86747717d3eb6a2df121581cc66bce011e83456d2c7870d81ad3eb
uv run --locked python - "$reference" < evidence/task-03/step-02/runtime-check.py.txt
```

For AMD64, use platform digest
`sha256:66ade57348103ac7fbcd01f323f6c01469f6a1e2c441196612942c2dcfb1e245`.
The local tmpfs ownership and seccomp setup are Docker compatibility checks, not
proof of Kubernetes `fsGroup`, emptyDir lifecycle, RuntimeDefault profile identity,
service-account mounting, resource requests/scheduling, or cluster swap policy.

## Application verification and artifacts

Ruff lint/format and package builds passed. **210 application tests passed** in
0.50 seconds, with 125/125 measured lines and 28/28 branch outcomes. The existing
Starlette/HTTPX deprecation warning was not suppressed. There is no coverage threshold
or claim of exhaustive tests; this step did not change application behavior.

- [Rendered demo manifests](step-02/step32-demo.yaml)
- [Parsed manifest-check results](step-02/step32-manifest-checks.json)
- [ARM64 runtime results](step-02/step32-runtime-arm64.json)
- [AMD64 runtime results](step-02/step32-runtime-amd64.json)
- [Lint/test/package output](step-02/step32-verification.txt)

Artifacts preserve actual results; repository-home paths in test output were replaced
with `<repository>` and trailing whitespace trimmed. No credentials or customer data
were captured. Kubernetes probe actions, restarts, readiness routing, rollout behavior,
server-side validation, and actual pod security/mounts remain Step 3.3 checks after
provider/access/budget approval. No namespace admission-enforcement policy or cloud
resource was introduced. Final review and merge of this branch remain pending.
