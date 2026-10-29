# Step 6.1 — Local instrumentation and actual Prometheus collection

**Later status:** merged/published as `cc25ae3`; normal SCM build #17 verified.
See the [follow-up](step-01-scm-verification.md). The dated record below preserves
the original candidate execution and its then-pending publication status.

**28 October 2026 UTC.** Approved local subset implemented at
`2328b9c58274f3a1b988445a513ef7fa1844f58c`, on `task-06/step-01-metrics`.
**Not merged/published; normal SCM proof remains pending.** Managed-cluster pod/node
monitoring is still deferred. The [contract/runbook](../../docs/runbooks/metrics.md)
distinguishes implemented local controls from later tasks.

## Implementation and host checks

- Per-application Prometheus registry; HTTP request counts, monotonic duration
  histogram, unhandled exceptions, and accepted/rejected/invalid validation outcomes.
- Bounded labels, no bodies/arbitrary paths/identifiers as labels, no service-layer
  instrumentation or transaction/API-contract changes beyond additive GET `/metrics`.
- Exact metrics path excluded from traffic measurement; cancellation/errors propagate.
  Standard Linux process collection uses the same isolated registry.
- `prometheus-client>=0.26,<0.27`, locked at 0.26.0 with no required extras. No other
  runtime package version changed. Prometheus server 3.15.1 has a pinned ARM64-capable
  official Quay image; `promtool` accepted the actual configuration.
- **538 tests passed** on the host, including 35 new metrics cases. The separate
  warnings-as-errors run passed. Ruff lint/format and wheel/source build passed.
- Application coverage: **194/194 lines, 37/38 branch outcomes**; no coverage gate.
- Source gate passed: 21 LOW Bandit findings, no MEDIUM/HIGH. All **15** runtime
  dependencies audited with no known advisories. No pytest/audit warning suppression.

[Initial checks](step-01/step61-initial-checks.txt),
[final checks](step-01/final-checks.txt),
[configuration validation](step-01/step61-promtool.txt),
[official index](step-01/step61-prometheus-index.txt), and
[platform manifest metadata](step-01/step61-prometheus-index.json).
The Prometheus runtime version was also checked via its actual build-info API.
These are registry digest/version checks, not an independent signature verification.

## Candidate Jenkins and exact-image gate

Manual sandboxed inline job
`finsecure-ci-metrics-review-success-20261028154656`, build **#1**, succeeded.
It checked out public main `d76b713`, verified a locally transferred Git bundle's
SHA-256, fetched the exact unpublished candidate, and detached at `2328b9c`.
The application pipeline/gates were unchanged; only the explicit candidate-checkout
wrapper differed. No branch was published to run it and no new agent privileges,
mounts or credentials were added.

- **538 tests passed**; source/runtime scans, packaging and exact ARM64 image gate passed.
- Fresh Trivy report contained **zero known findings at every severity**; 15 runtime
  dependencies plus the application were checked in the image inventory.
- All **33 artifacts** were downloaded and verified. Source/lock/report hashes,
  package manifests and image identity were checked.
- Source revision: `2328b9c58274f3a1b988445a513ef7fa1844f58c`.
- Image ID: `sha256:f11d1f52e2a8eb3d45d879d5332874249d4f33e40a8af10f8e073a1fd003d50a`.
- Archive SHA-256: `0c3c2f198e05063df39279dff980b0aedf351c7b6a55bccb97908fa806dc6562`.

[Transport provenance](step-01/step61-gate-candidate.json),
[CI verification](step-01/ci/verification.json),
[sanitized console](step-01/ci/console.txt),
[image gate](step-01/ci/reports/image-security-summary.json), and
[complete scan](step-01/ci/reports/trivy.json).

This is **candidate execution, not normal Pipeline-from-SCM/SCM-trigger evidence**.
The application-specific gate does not establish vulnerability coverage for the
separate Prometheus server image or the entire monitoring stack. Findings remain
time-bound. AMD64 metrics execution was not tested.

## Real local collection from that exact image

The operator checksum-verified and loaded the same passing Jenkins archive, tagged
its verified image ID `finsecure-pay:metrics-local`, and checked the source label.
No separately rebuilt image was substituted. The monitoring project/data volume
were absent and ports 8000/9090 were free before startup. The separate Compose
project used only loopback host bindings and its own network/data volume.

[Image load](step-01/step61-image-load.txt),
[startup](step-01/step61-start.txt), and
[runtime boundary checks](step-01/live/runtime.json).

Real readiness/target observation was bounded to 120 seconds with 5-second HTTP
calls. Exactly **60 synthetic requests**, without retries, were sent over about
**60.65 seconds**. Prometheus observed the following exact changes:

| Observation | Delta |
| --- | ---: |
| Health GET 2xx | 20 |
| Validation POST 2xx | 30 |
| Validation POST 4xx | 10 |
| Accepted outcomes | 20 |
| Rejected outcomes | 10 |
| Invalid outcomes | 10 |
| HTTP request count | 60 |
| Histogram observation count | 60 |

Both application and Prometheus scrape targets had `up == 1`, no last scrape error,
15-second intervals and 5-second timeouts. Application process CPU increased from
2.36 to 2.98 seconds; resident memory was **57,389,056 bytes**. The measured ASGI
latency sum was approximately **0.192 seconds across 60 requests**, not an SLO,
client-delivery measurement or load test. Prometheus self-metrics included 877 head
series at observation time. These values are actual measurements, not defaults.

[Live verification](step-01/live/verification.json),
[PromQL/before/after values](step-01/live/queries.json),
[target API data](step-01/live/targets.json),
[actual exposition](step-01/live/metrics.txt),
[response examples](step-01/live/responses.json), and
[Prometheus build info](step-01/live/prometheus-build.json).

Application and Prometheus ran as UID 10001 and 65534 respectively, with read-only
roots, dropped capabilities, no-new-privileges and the approved CPU/memory limits.
Only Prometheus had the read-only configuration bind and its own writable data
volume; neither received Docker socket or Jenkins-secret access.
Prometheus reported configured retention as `1d` and `256MiB` (the CLI value is
`256MB`). Retention does not cap head/WAL/compaction disk overhead.

## Cleanup and warnings

Both monitoring services were stopped with a 30-second grace allowance and exited
**0**, without OOM. Their containers and the named TSDB volume remain for deliberate
reuse; no data/volume prune occurred. The only observed Prometheus WARN line was
its expected graceful-shutdown signal notice. No application warning/error lines
were observed; no filter was added to hide warnings.

The candidate Jenkins job is disabled with exactly one retained build. After
confirming agent/queue idleness, the operator verified hashes and removed only the
owned agent bundle and review-workspace image archive. Archived reports/image
remain; host downloads/local image tags and shared BuildKit cache remain outside Git.
Normal main stayed at build **#16** and its archived image manifest was rechecked
unchanged. Jenkins services were not stopped/reconfigured. Its separate
credential-boundary verifier also passed afterward.

[Cleanup record](step-01/live/cleanup.json),
[stop output](step-01/live/stop.txt),
[Prometheus shutdown warning](step-01/live/prometheus-warnings.txt), and
[final Jenkins boundary check](step-01/step61-final-boundaries.txt).

Historical procedures: [candidate review](step-01/review-harness.py.txt),
[live verification](step-01/verify-live.py.txt), and
[cleanup](step-01/cleanup-harness.py.txt). Only the success mode of the reused review
harness ran here; its unused comparison mode is not authorized or claimed as tested
in this step. These files record historical operations, not instructions to rerun
disabled jobs after their bundle was removed.

## Remaining limits

No registry publication, deployment, cloud spending, managed-cluster metrics,
Grafana dashboard, alert/notification or structured/centralized logging work was
performed. Public release 0.2.0 and Kubernetes pins are unchanged. The monitoring
services are stopped, not claimed to remain available. Review/merge/publication and
normal SCM verification of this local subset remain pending.

All 44 retained procedure/result files have a verified
[SHA-256 manifest](step-01/SHA256SUMS). Evidence was checked against current Jenkins
credential values; none were present. Host repository paths were normalized in
selected text logs. Existing locked dependency versions and candidate code/config
identity were rechecked after the documentation-only changes.
