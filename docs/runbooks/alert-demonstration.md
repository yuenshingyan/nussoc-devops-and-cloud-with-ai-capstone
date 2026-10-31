# Step 6.4 — Actual local alert and recovery email

Completed on `task-06/step-04-alert-demonstration`, based on reviewed/published
`b06aa03`. Review/merge/publication remain pending. See the
[actual evidence and screenshots](../../evidence/task-06/step-04-alert-demonstration.md).

## Scope and bounded trigger

The user approved continuing the local demonstration. Only the owned application
container was stopped. Jenkins, Grafana, unrelated containers and cloud resources
were not used as failure targets. No load generator or transaction requests were used.
The existing [Step 6.3 configuration](alerts.md) was unchanged.

Before starting, check host/Docker capacity and loopback ports 8000, 9090, 9093 and
8025. This run had about 11 GiB host free space; do not infer unlimited capacity from
successful recovery. Preserve existing volumes and failed-build evidence.

Start only application, Prometheus, Alertmanager and Mailpit with the alerts overlay.
Require a real application `/metrics` response, `up=1`, healthy/inactive rule,
no active Alertmanager alerts and an empty inbox. Baseline readiness is bounded to
120 seconds with 2-second polling and 5-second HTTP request timeouts.

The single trigger was:

```sh
docker compose -f ops/monitoring/compose.yaml -f ops/monitoring/alerts.compose.yaml stop --timeout 30 application
```

Observe for at most 150 seconds, then request restoration with a 30-second command
budget whether or not delivery succeeds. Do not repeatedly trigger the outage to hide
failure. Restoration belongs in a `finally` path. A normal restore uses:

```sh
docker compose -f ops/monitoring/compose.yaml -f ops/monitoring/alerts.compose.yaml start application
```

Confirm metrics access, `up=1` and healthy/inactive rule within 120 seconds of restart.
Allow up to 420 seconds for the resolved email because the existing notification group
interval is five minutes. These are observation bounds, not a production SLA or a
guarantee that Docker can restore a damaged service within a deadline.

## Actual result

On 31 October 2026 UTC, the restart was requested after **122.22 seconds**. Healthy
scraping and an inactive rule were observed within **153 seconds** of the initial stop
request. A real firing email and a real resolved email arrived in Mailpit. Exactly two
messages were present before cleanup. The app was restored before waiting for recovery
email delivery; it was not held down for the entire notification interval.

The browser showed both messages and their native HTML bodies. The raw `.eml` messages,
message metadata, measured `up` samples, pending/firing/recovered rule states,
Alertmanager observations and screenshots are retained in the evidence bundle.
The screenshots show stored notifications after recovery, not current live outage state.
Browser times use the host's UTC+08 display; raw email headers and the evidence timeline
use UTC. The isolated browser and its temporary profile were removed.

This proves **actual local SMTP receipt**, not Gmail/internet delivery or instructor
approval of Mailpit. No email was manually injected, no alert was POSTed into
Alertmanager, and no screenshot/chart data was fabricated. The interruption exercised
the failed-scrape (`up=0`) branch; missing-series behavior remains covered by Step 6.3
rule tests rather than a separate live disruption here.

## Evidence before cleanup

Mailpit's inbox is temporary. Export both messages and capture the real UI before
stopping it. Do not replace actual receipts with constructed MIME examples. Check the
message subjects, sender/recipient, received timestamps and matching alert labels.

After recovery, capture the inactive rule/no active alert state, then stop Prometheus
first and the other owned services second, using the [existing cleanup commands](alerts.md).
This avoids generating an unintended alert during teardown. Preserve named volumes;
do not remove Grafana's stopped container or use global prune.

This run stopped all four services with exit 0 and no OOM. Jenkins remained at build
#24, its queue empty, and its separate credential-boundary check passed. Grafana stayed
stopped. No image was published or cloud resource deployed. The already-gated build #18
application image was reused with unchanged application source/lock, not substituted
with the later #24 archive.

## Checks and remaining observations

584 host tests passed with warnings treated as errors; Ruff lint/format and package
build passed. Application, dependencies and monitoring configuration were unchanged,
so no new behavior tests or new image scan were required for this documentation/evidence
step. Main build #24's earlier SCM result is distinct from this actual demo execution.

Compose's retained-Grafana orphan warning, Prometheus's graceful-stop WARN and Chrome's
native allocator/display-link diagnostics remain recorded. Collected service logs cover
the demonstration and cleanup, not every earlier startup line. The native email UI
shows an HTML Check score of 37%; the default template visibly rendered, but broad
email-client compatibility was not established. Default template links use container
hostnames and are not claimed usable from the host browser; use the documented loopback
Prometheus/Alertmanager addresses instead. No template, logger or security setting was
changed just to remove these observations.

The historical scripts in evidence document the one actual run. They are not approval
to rerun it automatically. Jenkins email notification and structured/centralized logs
remain Step 6.5; this demonstration does not claim those features are implemented.
