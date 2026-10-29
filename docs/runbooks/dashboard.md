# Step 6.2 — Local Grafana dashboard and blocked setup checkpoint

**Initial scope approved; implementation in progress, live verification blocked.**
Branch `task-06/step-02-dashboard` starts from reviewed/published `5e53c5f`.
Provisioning/dashboard files and an optional Compose overlay are written. The official
Grafana 13.3.0 ARM64 image was downloaded, but Grafana has **not started**.
The original CHOWN-only host-file plan failed its real Docker Desktop check. The
replacement secret-volume approach below needs approval before implementation.
See [actual preflight evidence](../../evidence/task-06/step-02-preflight.md).

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

## Initially approved local access and resource controls

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

## Approved dashboard

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

## Verification and cleanup

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

## Actual checkpoint and proposed correction

Official release API identified [Grafana 13.3.0](https://github.com/grafana/grafana/releases/tag/v13.3.0),
newer than the search index result. Its multi-platform Docker index is pinned at
`sha256:488984b716c0862639f91a698adbe2862677a5a07bad42da5f03f3030883b205`;
ARM64 availability and image UID 472 were checked. No independent image-signature
or complete third-party vulnerability-scan claim is made.

The overlay is separate from `compose.yaml`, so existing metrics-only commands do
not require Grafana credentials. New YAML provisioning/overlay files use the JSON
subset of YAML, allowing deterministic tests without adding a YAML dependency.
The native Grafana `$__file{...}` provider reads the password without exporting its
value into the server environment. Protected dashboard/data-source APIs must require
authentication; Grafana's public health/login resources remain loopback-only.

Host lint/format, 572 tests (34 new), package build and source/dependency gates passed.
Bandit reported 26 LOW findings and no MEDIUM/HIGH; all 15 runtime dependencies
passed auditing. Chrome and Node are already available; no browser dependency was
installed. Unit tests are not proof of Docker Desktop ownership semantics.

The real helper returned `chown: /secret: Permission denied`. It had only CHOWN
capability, no network, a read-only root and only the intended host secret file mounted.
No extra capability or relaxed permission was tried. The generated credential remains
unchanged: operator-owned UID 501/GID 20, mode 0400, under its private 0700 directory.
Both attempted helpers were removed. No Grafana data volume or service was created.
Existing monitoring services were not started; no screenshots/live dashboard proof exist.

**Proposed correction — approval required:**

1. Keep the existing host credential operator-owned, mode 0400, beneath the private
   0700 directory. Preserve its value; do not regenerate or rotate it.
2. Create a dedicated, purpose-labelled external Docker secret volume,
   `finsecure-monitoring-grafana-secrets`, separate from Grafana's database volume.
3. Initialize only that new owned volume through stdin using a network-isolated,
   read-only-root helper with CHOWN as its only added capability. Inside the Linux
   volume, set directory mode 0700 and file mode 0400, both UID/GID 472. No host
   file is chowned or mounted into this helper. Never print the input value.
4. Mount the secret volume read-only at `/run/secrets` in Grafana. Refuse unowned
   volumes, missing credentials on an existing installation, or host/volume content
   mismatches. Verify identity and permissions before startup; no automatic replacement.
5. Keep all other approved resource, authentication, verification and cleanup limits.
   Preserve this secret volume on normal shutdown; this is local plaintext storage,
   not encrypted secret management or a cloud provider control.

Do not use the current credential initializer as a working setup procedure on this
host. It is a fail-closed, documented checkpoint until the correction is approved
and actually verified. Application code and metrics contracts are unchanged.
