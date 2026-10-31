# Step 6.3 — Local alerts and SMTP receiver

Implemented on `task-06/step-03-alert-configuration`, based on reviewed/published
`c27a2e8`. Merged/published as `dcab1c5`; normal SCM build #21 passed 584 tests, all gates
and 33 artifact checks. See the [SCM follow-up](../../evidence/task-06/step-03-scm-verification.md).
See [execution evidence](../../evidence/task-06/step-03-alert-configuration.md).

## Approved scope

The user approved a one-minute failed/missing application scrape alert, evaluated
every 15 seconds, with recovery notification. The user selected **Mailpit local SMTP
receipt**, not Gmail delivery. No Google account, passwords, external SMTP account,
cloud resources or Python dependencies are required. No alert-trigger demonstration
or Jenkins notification configuration is included in this step.

Task 6 requires a triggered alert, received notification evidence, and Jenkins email
or an approved equivalent. Mailpit can receive actual SMTP messages locally; it is not
internet email delivery. The rubric does not explicitly name Mailpit as accepted.
Do not claim grading approval, production delivery or Gmail receipt.

## Configuration and semantics

- Optional `ops/monitoring/alerts.compose.yaml` adds Alertmanager 0.34.2 and Mailpit
  1.32.0, with official multi-platform image digests pinned. Both ran on ARM64.
  No independent image signature or complete third-party vulnerability scan is claimed.
- Prometheus uses `alerts-prometheus.yaml` only with this overlay. Original metrics-only
  and Grafana-only configurations remain independent. Scrape jobs/intervals are preserved.
- `FinSecureApplicationScrapeUnavailable` tests the exact local target
  `job="finsecure-pay", instance="application:8000"`: `up == 0` or `absent(up)`.
  The explicit labels keep the alert identity stable across failed-to-missing samples.
- `for: 1m` starts when Prometheus first evaluates the condition as true. Scrape timing,
  staleness/lookback and evaluation timing mean this is not an exact wall-clock outage
  SLA. Brief failures do not fire. A successful scrape clears the condition at the next
  evaluation; there is no extra hold-open period.
- Prometheus cannot detect its own complete outage through this rule. This is a local
  single-target rule, not managed-cluster or end-to-end payment health monitoring.
- Routing explicitly retains conventional Alertmanager timings: initial group wait
  **30 seconds**, group interval **5 minutes**, repeat interval **4 hours**. Resolved
  emails are enabled but may wait for the group interval; recovery email is not immediate.
  There is no custom retry loop: vendor notification retry behavior remains in effect.
- Sender `finsecure-alerts@example.test`, recipient `finsecure-operator@example.test`.
  These are reserved synthetic addresses, not real Gmail accounts. SMTP uses
  `mailpit:1025` with no authentication/TLS on the dedicated local container network.
  This is deliberately local test transport, never an external SMTP configuration.

## Boundaries and inbox lifetime

Both new services run as UID/GID 65534, with read-only roots, dropped capabilities,
no-new-privileges, 0.5 CPU and 256 MiB memory each, without additional swap.

Mailpit publishes **only `127.0.0.1:8025`**. SMTP is not published to the host.
Alertmanager publishes **only `127.0.0.1:9093`**. These unauthenticated local UIs assume
one trusted operator; do not expose them publicly. Mailpit restricts HTTP Host values
and SMTP recipients, disables version checking and reverse-DNS lookup, and has no
relay/forwarding configuration. No private credentials are mounted into either service.

The dedicated notification network is a regular bridge, not an egress-denial boundary.
An initial `internal: true` network prevented Docker Desktop from publishing the inbox
port. It was replaced only after stopping/removing the two owned new containers;
Alertmanager's named data volume and all existing volumes were preserved. No other
project network was changed. The final design permits normal bridge egress, but does
not configure any external mail destination or forwarder.

Alertmanager retains its own named state volume. Mailpit uses its native temporary
SQLite inbox in a **64 MiB `/tmp` tmpfs**. The inbox disappears when Mailpit stops.
Its vendor default of at most 500 messages remains; this is not a disk-capacity or
production retention promise. In Step 6.4, export reviewed message evidence and capture
the actual inbox **before stopping**. No automatic backup/recovery policy is introduced.

## Operate from the repository root

Check Docker capacity and ports 8000, 9090, 9093 and 8025 first. Do not stop Jenkins
or increase Docker allocation. Use the exact gated application tag from the
[metrics runbook](metrics.md); this preflight reused verified build #18, with unchanged
application source and lockfile, not a new application image.

```sh
docker compose -f ops/monitoring/compose.yaml -f ops/monitoring/alerts.compose.yaml config --quiet
docker compose -f ops/monitoring/compose.yaml -f ops/monitoring/alerts.compose.yaml up --detach --no-build application prometheus alertmanager mailpit
```

Use <http://127.0.0.1:9090/alerts>, <http://127.0.0.1:9093>, and
<http://127.0.0.1:8025>. Grafana need not run for this step. Its retained stopped
container may produce Compose's orphan warning; **do not remove it**.

Allow at most 120 seconds for readiness, polling every 2 seconds with 5-second HTTP
request timeouts. Require both a live application metrics response and a completed,
healthy rule evaluation; stale `up=1` alone does not prove the restarted app is ready.

For ordinary cleanup, stop Prometheus first so teardown does not manufacture an outage:

```sh
docker compose -f ops/monitoring/compose.yaml -f ops/monitoring/alerts.compose.yaml stop --timeout 30 prometheus
docker compose -f ops/monitoring/compose.yaml -f ops/monitoring/alerts.compose.yaml stop --timeout 30 application alertmanager mailpit
```

Do not delete volumes, use `--remove-orphans`, or globally prune. Stop all owned services
on verification failure too, and record nonzero exits rather than treating them as success.

## Verification and remaining work

- 584 host tests passed with warnings treated as errors; Ruff lint/format, build and
  source/dependency gates passed. Bandit: 29 LOW, no MEDIUM/HIGH; 15 runtime dependencies
  audited with no known advisories. Application code and dependencies did not change.
- `promtool check config`, `amtool check-config` and real `promtool test rules` passed.
  Six scenarios cover healthy, sustained failed, missing, short failure, recovery and
  failed-to-stale transitions. These synthetic rule tests are not a real outage demo.
- Live Prometheus loaded the rule, reported it healthy/inactive and discovered Alertmanager.
  Alertmanager loaded the local receiver. SMTP EHLO, MAIL FROM and RCPT TO returned 250;
  RSET canceled the envelope, without DATA. This verifies receiver acceptance, **not
  notification receipt**. Mailpit's API was accessible through its loopback port.
- The first rule-test helper lacked writable temporary storage; a bounded tmpfs fixed it.
  The first runtime attempt exposed the internal-network port problem. A later observer
  asserted rule readiness without first waiting for evaluation; its early cleanup left
  the application at exit 137, **not OOM**. The exact failed rule field and termination
  cause were not established. Those failures are retained. The observer was corrected to wait
  for actual application readiness and rule evaluation, rather than ignoring failed checks.
- Final verification stopped all four services with exit 0 and no OOM. Prometheus emitted
  its normal graceful-stop WARN. Grafana remained stopped and its previously documented
  diagnostics are not resolved by this work. Jenkins was not stopped/reconfigured.

Step 6.4 still requires separate approval of a bounded interruption, actual firing and
recovery email receipt, timestamps and browser evidence. Step 6.5 separately covers
Jenkins notifications and logs. No delivery evidence is claimed in Step 6.3.

References: [Alertmanager configuration](https://prometheus.io/docs/alerting/latest/configuration/),
[Mailpit runtime settings](https://mailpit.axllent.org/docs/configuration/runtime-options/),
[Alertmanager release](https://github.com/prometheus/alertmanager/releases/tag/v0.34.2),
[Mailpit release](https://github.com/axllent/mailpit/releases/tag/v1.32.0).
