# Step 6.1 — Local metrics contract and verification

## Status and approval boundary

**Approved local subset implemented and verified; review/merge/publication and
normal SCM verification remain pending.** Candidate `2328b9c` passed 538 Jenkins
tests and the real image gate. Its exact exported image was used for actual local
Prometheus collection. The demo services are now stopped, with data preserved.
See [actual evidence](../../evidence/task-06/step-01-metrics.md).
Branch: `task-06/step-01-metrics`, from reviewed/published `main` at `d76b713`.
Step 5.4's local demonstration evidence is merged and published.

The user approved this endpoint/metric contract, the `prometheus-client` runtime
dependency and the local monitoring values. The runtime client is locked at 0.26.0
with range `>=0.26,<0.27`; it has no required extra dependencies. Prometheus is pinned
to official release 3.15.1 and its ARM64-capable multi-platform index digest. Existing `/health`
and `/validate` request/response contracts and business rules remain unchanged.
No database, additional business service, public image release or cloud deployment
is included. Grafana, alerts, notifications and structured logging remain their
later steps; existing scaffold directories do not mean those tools are configured.

## Approved scope

1. Add explicit Prometheus instrumentation in `src/finsecure_pay/observability/` and
   the `/metrics` HTTP route in `src/finsecure_pay/api/`. Use ASGI-level middleware
   without buffering/parsing request bodies for HTTP measurements.
2. Use the maintained `prometheus-client` library, with a reviewed version range
   and committed uv resolution. Do not add an auto-instrumentation framework or
   other new Python dependency. Check its provenance/compatibility and run actual
   dependency/image gates; do not assume a new dependency is vulnerability-free.
3. Run a separate local Docker Compose application/Prometheus demo. Prometheus
   scrapes the actual application and itself, not mocked series.
4. Collect application process CPU/memory metrics inside the Linux application
   container. These are **process metrics, not managed-cluster pod/node metrics**.
   Kubernetes infrastructure monitoring remains deferred until cloud approval.

## GET /metrics contract

- HTTP 200, Prometheus text exposition using the client's documented text content
  type (`text/plain; version=1.0.0; charset=utf-8` for locked client 0.26.0); no request
  body or authentication for this **loopback-only local demo**.
- GET only. Unsupported methods retain framework method-error behaviour (405);
  no changes to existing route methods. The route is excluded from OpenAPI to keep
  the transaction API documentation focused; exclusion is not access control.
- No transaction IDs, account IDs, amounts, currencies, request bodies, headers,
  raw query strings, exception messages or arbitrary URL paths in metric labels.
- No separate exporter HTTP listener or background task in the application.
- Metrics reset on process restart. Use an independent registry per application
  instance; tests/app factories must not share counters or duplicate registrations.
- Support the current **single Uvicorn worker per container** only. Multi-worker
  aggregation and process-shared storage are not introduced or implied.
- Do not expose `/metrics` publicly in a later cloud deployment. Decide scrape
  access/network controls before external routing; a same-port endpoint has no
  inherent private-path protection.

## Metric names and semantics

| Metric | Type | Labels | Meaning |
| --- | --- | --- | --- |
| `finsecure_http_requests_total` | Counter | `route`, `method`, `status_class` | One observation per finished/terminated HTTP ASGI invocation, excluding the exact `/metrics` path |
| `finsecure_http_request_duration_seconds` | Histogram | `route`, `method` | Monotonic elapsed ASGI handling time, including unsuccessful invocations |
| `finsecure_http_exceptions_total` | Counter | `route`, `method` | Unhandled non-cancellation exceptions escaping the instrumented application call; re-raised unchanged |
| `finsecure_validation_outcomes_total` | Counter | `outcome` | Exactly one accepted/rejected business evaluation, or one schema-invalid POST `/validate` request |

Bounded label values:

- `route`: `/health`, `/validate`, `other`. Exact case-sensitive path comparison;
  no unknown path is copied into a label. Redirect/trailing-slash and documentation
  paths fall into `other` unless their exact path is one of the two listed values.
- `method`: `GET`, `POST`, `OTHER`. Unrecognized method strings are never labels.
- `status_class`: `1xx`, `2xx`, `3xx`, `4xx`, `5xx`, `other`, `no_response`.
  Use the status observed in ASGI response-start. If none is observed, use
  `no_response`; do not invent a delivered HTTP status. If headers were sent before
  an exception/cancellation, retain their observed class.
- `outcome`: `accepted`, `rejected`, `invalid`. A business rejection stays HTTP 200
  under the existing contract. Multiple rule failures count as one rejected
  evaluation. Request-validation errors count as one invalid request, not one per
  field error. Only POST `/validate` contributes to this metric; 404/405 requests
  and unexpected failures do not become validation outcomes.

Count outcomes in API/observability code, not the pure transaction service. Do not
parse response bodies to infer outcomes or retain input to build metrics. An outcome
means evaluation occurred, not that the response was delivered to the client.

4xx/5xx errors are visible through the request counter's status class. Exceptions
are a separate signal: outer framework error handling may send a response after an
inner instrumentation call failed, and exceptions can occur after response-start.
Do not blindly sum 5xx and exception counts as if they were disjoint. Cancellation
must propagate unchanged; record elapsed handling/request termination in `finally`
but do not count cancellation as an application exception or manufacture a response.
No change to existing error responses is authorized by this scope.

Exclude **all methods on the exact `/metrics` path** from application request,
duration and exception metrics so scraping does not inflate traffic/latency/error
statistics. `/metrics/` is not that exact path and follows the bounded `other` rule.

Histogram finite buckets, in seconds:
`0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5`, plus the automatic `+Inf`
bucket. These are demonstration measurement boundaries, **not an SLO or alert
threshold**. Histogram sum/count/bucket and library-created companion series are
expected; elapsed-time floating point is unrelated to Decimal monetary arithmetic.

Register only the explicitly chosen application metrics and the client's standard
process collector with the `finsecure` namespace on this registry. Linux process
CPU and resident memory are required in real demo verification; other supported
standard process series may be present. Do not expose default global collectors,
PID labels or arbitrary host metadata. Unsupported local-host process series must
not be claimed as verified; the actual process check targets Linux Docker.

## Approved local monitoring values

- Compose project: `finsecure-monitoring`, separate from Jenkins and its volumes.
  Application and Prometheus share only the demo network; no Docker socket, host
  process namespace, registry/cloud credentials or privileged containers.
- Application: build the current source locally under a distinct local-only tag;
  do not replace any published release tag or change Kubernetes pins. Keep the
  current release version metadata until a separately agreed versioned release.
  Host binding `127.0.0.1:8000`, container port 8000. Fail on a port conflict rather
  than taking over an existing process or silently choosing another port.
- Retain the application's established non-root/read-only/dropped-capability
  safeguards, 0.5 CPU/256 MiB limit and 16 MiB writable `/tmp` for this demo.
- Prometheus: select and verify an official ARM64-capable release and immutable
  image digest before committing configuration. Run non-root with dropped
  capabilities/no-new-privileges, 0.5 CPU/512 MiB limit, and loopback host port 9090.
  Use a read-only repository configuration mount and a separate named data volume.
  These are demo limits, not production sizing. No public listener/tunnel.
  Check available Docker resources before starting; if insufficient, stop and ask
  rather than changing Docker's memory allocation or stopping Jenkins.
- Scrape application `/metrics` and Prometheus itself every **15 seconds**, with a
  **5-second scrape timeout**. Use static target/job labels; no service discovery
  or Kubernetes API access yet. No alert rules or remote-write destination.
- Local TSDB retention: **24 hours or 256 MB**, whichever retention condition
  applies. This is not a hard disk cap: head/WAL and compaction overhead also use
  disk. Preserve the owned data volume on normal stop/down; no automatic pruning
  or backup/retention guarantee is introduced.
- Operator readiness observation: at most **120 seconds**, polling every **2
  seconds**, each HTTP request bounded to **5 seconds**. Retry readiness observations
  only, not failing tests/builds. Use owned client/process cleanup; no background
  traffic generator left running. Startup failure must be reported without deleting
  volumes or restarting unrelated Jenkins services.

These operational values are implemented in `ops/monitoring/compose.yaml` and
`ops/monitoring/prometheus/prometheus.yaml` and were verified in real containers.
Prometheus reports the configured `256MB` flag as `256MiB`; its retention duration
is reported as `1d`. Neither is a hard disk-usage cap.

## Local operation

Prerequisites: Docker/Compose, available loopback ports 8000/9090, and enough Docker
memory for the existing Jenkins services plus the demo. Do not stop unrelated
services or overwrite unowned volumes to resolve conflicts. This setup is local
only; do not add public bindings or credentials.

Use the **exact image archive that passed the candidate/application image gate**.
Verify its SHA-256 against the archived manifest and its image ID/source label
against the gate record before tagging it `finsecure-pay:metrics-local`. The retained
candidate is an unpublished branch build, not the current public release. Public
release 0.2.0 and its Kubernetes pin remain unchanged and do not have this endpoint.

After setting `verified_archive` to that local archive path and `verified_image_id`
to its verified SHA-256 image/config ID:

```sh
docker load --input "$verified_archive"
docker tag "$verified_image_id" finsecure-pay:metrics-local
docker compose -f ops/monitoring/compose.yaml config --quiet
```

The application has `pull_policy: never`, and this Compose file does not build it
implicitly. A separate local rebuild is a different artifact and needs its own gate
verification; do not claim the retained scan proves that image passed. Prometheus
uses the pinned official image from the configuration. Never reuse a blocked archive.

Validate the static configuration with the pinned image before first startup:

```sh
docker run --rm --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges:true --user 65534:65534 \
  --entrypoint /bin/promtool \
  --volume "$PWD/ops/monitoring/prometheus/prometheus.yaml:/etc/prometheus/prometheus.yml:ro" \
  quay.io/prometheus/prometheus:v3.15.1@sha256:fa3302279710be2f21a8301ec17a8b4f2301fd829bd113839b3b6b02b6f191a2 \
  check config /etc/prometheus/prometheus.yml
```

After these checks pass, start only the monitoring project:

```sh
docker compose -f ops/monitoring/compose.yaml up --detach --no-build
```

The application exposes <http://127.0.0.1:8000/metrics>. Prometheus is at
<http://127.0.0.1:9090/>; inspect targets and query, for example:

```promql
up{job="finsecure-pay"}
sum by (outcome) (finsecure_validation_outcomes_total{job="finsecure-pay"})
sum by (route) (rate(finsecure_http_requests_total{job="finsecure-pay"}[2m]))
finsecure_process_resident_memory_bytes{job="finsecure-pay"}
```

Generate only bounded synthetic traffic; counters are not expected to increase
without requests. Rate queries need multiple scrapes; empty/zero results before
traffic are not evidence of failed collection. Stored process/app series may become
stale after shutdown; they are not proof a stopped application is still available.

Stop only this project, allowing up to 30 seconds for graceful shutdown:

```sh
docker compose -f ops/monitoring/compose.yaml stop --timeout 30
```

This preserves containers and `finsecure-monitoring_prometheus-data`. Do not use
`down --volumes` or global prune. No backup or automatic recovery is promised.

## Actual local verification

- Official client [0.26.0](https://pypi.org/project/prometheus-client/0.26.0/) and
  Prometheus [3.15.1](https://github.com/prometheus/prometheus/releases/tag/v3.15.1)
  were selected. The [official installation documentation](https://prometheus.io/docs/prometheus/latest/installation/)
  identifies Quay as a project image registry. Index/platform digest and runtime
  version were checked; no independent signature-verification claim is made.
- 538 host and candidate Jenkins tests passed. Application coverage was 194/194
  lines and 37/38 branch outcomes, with no coverage threshold. Ruff/build/source
  gates passed; all 15 runtime dependencies audited with no known advisories.
- Candidate image gate passed with no known findings. All 33 artifacts verified.
  The exact ARM64 archive was loaded for collection; no separately rebuilt image
  was substituted. Prometheus server version/config/runtime were verified; the
  application-specific Trivy gate is not a scan of the entire monitoring stack.
- Actual 60-request sequence over about 61 seconds yielded exactly 20 health,
  20 accepted, 10 rejected and 10 invalid outcomes, with 60 request and histogram
  observations. Both scrape targets were up. CPU increased and resident memory
  was positive; Prometheus self-series were observed.
- Both services ran non-root, read-only, capability-dropped, on the separate
  monitoring network with loopback ports and configured CPU/memory limits.
- Both stopped with exit 0 and no OOM. Data volume/history retained. The only
  observed Prometheus warning was its graceful-shutdown signal notice; no
  application warning/error lines were observed. No warning was suppressed.
- Candidate Jenkins job disabled after one retained build; its checksum-identified
  workspace image and transfer bundle removed while idle. Jenkins main build #16
  and its image manifest remained unchanged; Jenkins was not stopped/reconfigured.

This is a local single-worker ARM64 verification, not a load test, latency SLO,
AMD64 compatibility test, Grafana dashboard, alert, notification, centralized log
pipeline or managed-cluster metric verification. Historical harnesses in evidence
record that run, not permission to rerun disabled jobs or removed bundles.

## Verification policy and evidence

- Deterministic unit/API tests: accepted/rejected/invalid outcomes, multiple-rule
  rejection, health, 404/405 and arbitrary paths/methods, metrics exclusion, registry
  isolation, response-status handling, exception/cancellation propagation and
  durations. Assert metric deltas and invariants, not brittle exact timings.
- Verify synthetic identifiers, unknown field names, query values and exception
  messages never appear in metric output. No real payment/customer data.
- Run locked lint/format/full tests/build plus source/dependency gates. The updated
  runtime dependency/image must pass real image scanning before claiming that gate.
- Validate Prometheus configuration with the pinned image's `promtool`; use real
  local application/process metrics and Prometheus query/target APIs for evidence.
- Bounded verification traffic: at most 60 synthetic requests over about one minute
  (20 health, 20 accepted, 10 rejected, 10 invalid), no automatic traffic retries.
  Per-request timeout 5 seconds. Wait at most 120 seconds for matching scraped
  counter/histogram changes; record actual measurements, not expected numbers.
- Verify application scrape `up == 1`, request/outcome deltas, histogram observations,
  process CPU/memory and Prometheus self-metrics. No Grafana/dashboard/alert claim.
- Capture sanitized commands, source/image/config digests, real responses/queries,
  tests and cleanup status. Keep large/generated artifacts outside Git unless
  selected for reviewed evidence. Stop only owned demo services after verification,
  preserving named data; no Jenkins shutdown or image publishing.

Full Step 6.1 remains incomplete until required managed-cluster pod/node metrics
are implemented and actually scraped. This approved scope covers its feasible local subset.
