# Runtime safeguards — Step 3.2

These are **demo starting values**, configured in
`deploy/kubernetes/base/deployment.yaml`. They have been rendered and checked locally;
compatibility of the unchanged 0.2.0 image was tested with Docker limits/security
settings. Kubernetes admission, scheduling, probes, restarts, rollout behavior, and
volume permissions remain unverified until the approved cluster deployment.

## Probe policy

All three probes use HTTP GET `/health` on the container's named `http` port (8000).
The kubelet addresses the pod, not the ClusterIP Service. HTTP probes evaluate status
codes, not the JSON body; the separate local smoke checks also assert the body.

| Probe | Period | Timeout | Consecutive failures | Successes | Intended effect |
| --- | --- | --- | --- | --- | --- |
| Startup | 2 s | 2 s | 30 | 1 | Allow roughly 60 seconds of failed probing before restarting the container |
| Readiness | 5 s | 2 s | 2 | 1 | Mark the container unready and remove the pod from ready Service endpoints |
| Liveness | 10 s | 2 s | 3 | 1 | Restart a persistently unresponsive container |

Readiness and liveness checks remain disabled until the startup probe succeeds.
No extra initial delay is needed.
Image pulls and scheduling occur outside the startup-probe allowance. Probe timing
is approximate, not a wall-clock SLA; execution time, kubelet scheduling, and readiness
probe acceleration can affect observation times. A success resets consecutive failures.

Readiness failure **does not restart** a container, and existing connections may
persist after endpoint readiness changes. Startup/liveness failure can
restart the container under the Deployment pod's default `Always` restart policy;
this is not the same as replacing a deleted pod. The Deployment handles missing-pod
replacement, which will be demonstrated separately in Step 3.4.

The application has no external runtime dependency, validates its configuration
before serving, and `/health` checks whether it can serve HTTP. Using that endpoint
for current readiness and liveness is intentional. Business-rule rejections and
schema errors must not make it unhealthy. If external dependencies are added,
revisit readiness separately rather than tying liveness to their availability.

## Resources and writable storage

| Resource | Per-container request | Per-container limit |
| --- | --- | --- |
| CPU | `100m` (0.1 CPU) | `500m` (0.5 CPU) |
| Memory | `128Mi` | `256Mi` |

Requests influence scheduling and resource shares/eviction decisions; they are not
application performance guarantees. CPU limits can throttle work. Memory exhaustion
can result in an OOM kill and restart. Requests differ from limits, so this is a
Burstable workload, not Guaranteed QoS.

The settings provide a small demo allocation with headroom over the observed local
smoke runs. They are **not production sizing**: only 25 sequential accepted requests,
a business rejection, a malformed request, and health checks were exercised per
architecture. Measure concurrency, latency, throttling, and memory under representative
load during observability work before claiming capacity or changing the policy.

A memory-backed `emptyDir` is mounted at `/tmp` with `sizeLimit: 16Mi`. Its contents
consume memory; it is not an extra allocation beyond the container's memory limit.
It is temporary, survives a container restart within the same pod, and is removed
with the pod. The application does not use it as transaction persistence. No other
writable application volume is introduced. Container logs remain on stdout/stderr.

Two steady-state containers request `200m` CPU and `256Mi` memory in total. Three
non-terminating containers during an ordinary surge request `300m` and `384Mi`;
their combined limits are 1.5 CPU and `768Mi`. Terminating pods can temporarily add
resource use beyond that count. These figures exclude system components and other
workloads; account for them when approving cluster size and cost.

## Runtime security

- Pod UID/GID `10001:10001` and `runAsNonRoot: true`, matching the image's numeric user.
- `fsGroup: 10001` for writable volume access; actual kubelet ownership behavior
  must be checked after deployment.
- Pod seccomp profile `RuntimeDefault`.
- Container `allowPrivilegeEscalation: false`, all Linux capabilities dropped,
  and a read-only root filesystem.
- `automountServiceAccountToken: false`: this API needs no Kubernetes API credentials.
- Linux-only node selector; the image remains pinned to the published two-platform digest.

These are workload-level restrictions, not a claim of namespace-level Pod Security
Admission enforcement. No namespace enforcement labels, RBAC grants, network-policy
isolation, authentication, or vulnerability gate were added in this step. Confirm
cluster admission policies and runtime behavior during Step 3.3. Use synthetic data
only; this is not a production payment service.

## Rolling updates and shutdown

- Two desired replicas remain unchanged.
- `RollingUpdate`, `maxUnavailable: 0`, `maxSurge: 1`: keep the desired available
  count during a normal rollout while allowing one additional non-terminating pod.
  Insufficient surge capacity can stall an update instead of taking down an old pod.
- `minReadySeconds: 5`: a new pod must remain ready for five seconds before the
  Deployment counts it as available. This does **not** delay Service routing after
  readiness first succeeds.
- `progressDeadlineSeconds: 600`: report a stalled rollout after the configured
  lack-of-progress interval. This is not a total rollout duration guarantee, and
  Kubernetes does not automatically roll back a failed Deployment.
- `terminationGracePeriodSeconds: 30`: allow the existing Uvicorn SIGTERM handling
  to exit before forced termination. No pre-stop hook or assumed load-balancer drain
  delay has been added.

The zero-unavailable setting is not an SLA or protection against node loss,
unrelated crashes, evictions, or concurrent configuration mistakes. No disruption
budget, cross-node placement guarantee, custom revision-retention policy, or automatic
rollback is introduced here. Graceful local exit does not prove zero dropped requests
through a future external load balancer.

## Verification and remaining checks

From the repository root, without contacting a cluster:

```sh
kubectl kustomize deploy/kubernetes/base
kubectl kustomize deploy/kubernetes/overlays/demo
```

The [Step 3.2 evidence](../../evidence/task-03/step-02-runtime-safeguards.md) preserves
parsed-field checks and a release-specific Docker compatibility harness. Both ARM64
and emulated AMD64 passed under a 0.5 CPU / 256 MiB cap, with non-root PID 1, read-only
root storage, writable bounded temporary storage, no-new-privileges, zero capabilities,
seccomp filtering, no OOM events, and clean exit/removal.

Docker checks do not simulate Kubernetes resource requests or readiness routing.
Docker's built-in seccomp profile is not necessarily identical to the managed
runtime's default profile. The local check explicitly sets tmpfs ownership and
turns off swap; it does not validate Kubernetes `fsGroup`, service-account mounting,
emptyDir lifecycle, or cluster swap policy.

After provider/access/budget approval, Step 3.3 must validate server-side schema and
admission, actual pod security/mounts, Running/Ready status, rollout completion,
resource observations, and probe events. Obtain confirmation before any disruptive
failure injection or recovery demonstration. Do not apply these manifests now.
