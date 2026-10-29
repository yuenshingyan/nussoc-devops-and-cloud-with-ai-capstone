# Step 6.2 — Proposed local Grafana dashboard

**Proposal only.** Branch `task-06/step-02-dashboard` starts from reviewed/published
`5e53c5f`. Grafana is not installed, configured or running by this document.
Approve the access controls and operational values below before implementation.

## Scope

Add Grafana to the existing `finsecure-monitoring` project, using its Prometheus
service as a provisioned, server-side data source. Commit provisioning files and
dashboard JSON under `ops/monitoring/grafana/`; do not change the application,
metric contract, published image tags or Kubernetes pins.

Use an exact gate-verified application archive, checking its source/image identity
before starting the demo. Preserve the existing Prometheus volume and settings.
Historical candidate scrapes are not evidence of new Grafana panels working.

No alert rules, notifications, external plugins, cloud resources or managed-cluster
metrics are included. Application process memory must not be labelled pod/node memory.

## Proposed local access and resource controls

- Bind Grafana only to `127.0.0.1:3000`. Fail on port conflicts; no tunnels/public ports.
- Select an official supported ARM64-capable Grafana release, verify its provenance
  and immutable image digest, and record the version before adding configuration.
- Run as non-root with a read-only root, dropped capabilities and no-new-privileges.
  Proposed limit: 0.5 CPU, 512 MiB memory, no additional swap, and 16 MiB temporary
  space. Keep configuration/dashboard mounts read-only and use a separate owned
  named Grafana data volume. Confirm image-specific writable-path requirements
  before implementation; do not silently weaken these controls.
- Use one authenticated local operator account; **anonymous access disabled**.
  Generate a unique password outside Git and pass it through file-backed configuration,
  not Compose literals, command-line arguments, reports or committed environment files.
  Proposed storage: an operator-owned private directory (0700) and password file
  (0400) owned by the verified Grafana container UID. If ownership needs adjustment,
  use a one-shot, network-isolated helper with only CHOWN capability and only the
  newly owned secret file mounted; never change Jenkins files or unrelated paths.
  The trusted operator can read it through a read-only container helper, captured
  in memory rather than emitted into reports/chat. Verify modes and UID before use.
  No default password or reuse of Jenkins credentials. No OAuth, external identity
  service or SMTP. Secret creation/ownership changes are part of this approval request.
- Do not grant Grafana or the application access to Jenkins secrets, the Docker socket,
  host process namespace or another project's volumes. Data/secret persistence is
  local, not a claim of encrypted storage or provider secret management.
- Disable reporting/update checks and avoid external plugin installation. Authentication
  and dashboard provisioning must work without an external application service.
- Check Docker capacity first. Do not stop Jenkins or increase Docker allocation to
  fit Grafana; stop and ask if the existing resources are insufficient.

The authenticated operator is trusted, as with the existing single-operator local
Jenkins setup. This is not a shared-user or production Grafana security design.
Provisioned dashboards should reject UI persistence of edits; change their tracked
JSON instead. An administrative account is not a read-only security boundary.

## Proposed dashboard

Default time range: last 15 minutes. Refresh: 15 seconds. Rate window: 2 minutes.
Scope application selectors to `job="finsecure-pay"`; avoid identifier variables
or arbitrary user-controlled label dimensions.

| Panel | Measurement and interpretation |
| --- | --- |
| Request rate | Sum of HTTP counter rates, in requests/second; metrics scrapes are already excluded |
| Mean ASGI handling latency | Rate of histogram sum divided by rate of count, in seconds; not client delivery latency |
| Validation outcomes | Counter rates grouped by accepted/rejected/invalid; business rejection is not a server failure |
| Application process memory | Resident memory bytes displayed in MiB; not container limit, pod memory or node usage |
| Application scrape health | Actual Prometheus `up` for the application target; not business success or Kubernetes readiness |

Use reset-aware PromQL rates. Do not replace missing/stale data with success or
fabricated zero latency. An idle request window can legitimately have undefined
mean latency. No SLO, alert threshold or performance-capacity claim is introduced.

## Proposed verification and cleanup

- Validate provisioning/dashboard structure and selectors against the metric contract.
  Run configured repository checks for any executable changes; documentation alone
  does not require a new application test run.
- Confirm actual Grafana version, authenticated health/data-source access, provisioning,
  and rejection of unauthenticated dashboard/API access. Never record passwords,
  session cookies, Authorization headers or authentication responses in evidence.
- Readiness and scrape observation: maximum 120 seconds per phase, polling every
  2 seconds with 5-second HTTP timeouts. Do not automatically retry failed traffic.
- Generate at most 60 synthetic requests over about one minute: 20 health, 20
  accepted, 10 rejected and 10 invalid. Record actual counter deltas and query data.
- Confirm at least request rate and mean latency visibly render from real Prometheus
  data. Save dashboard JSON and reviewed dashboard-only browser screenshots. API
  success or static JSON is not visual verification. Check available browser tooling
  first; ask before adding dependencies. If screenshots cannot be captured, report
  that check as pending rather than fabricating images or using unrelated screen data.
- Save sanitized source/image/config identities, panel/query results, screenshots and
  cleanup status under `evidence/task-06/`. Do not commit Grafana databases or secrets.
- Stop only owned monitoring services with a 30-second graceful-stop allowance.
  Preserve existing and newly owned named data volumes; no global prune, credential
  rotation, unrelated service shutdown or deletion of retained evidence.

After verification, commit and pause for review before merge/publication. Step 6.3
alert policy and delivery require their own approval and branch.
