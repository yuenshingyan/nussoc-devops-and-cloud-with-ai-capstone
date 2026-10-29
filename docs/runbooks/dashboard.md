# Step 6.2 — Local Grafana dashboard

**Merged/published as `f61cb4f`; normal SCM build #19 passed 578 tests, all gates
and 33 artifact checks.** See the [SCM follow-up](../../evidence/task-06/step-02-scm-verification.md). Work is on `task-06/step-02-dashboard`, based on reviewed main
`5e53c5f`. All three monitoring services are now stopped, with data and credentials
preserved. See [actual evidence](../../evidence/task-06/step-02-dashboard.md).

## Scope and configuration

Grafana 13.3.0 uses the existing Prometheus service. Its official ARM64-capable image
is pinned in `ops/monitoring/grafana.compose.yaml` to index digest
`sha256:488984b716c0862639f91a698adbe2862677a5a07bad42da5f03f3030883b205`.
Release, digest/platform metadata and actual runtime version were verified. This
is not an independent signature verification or a complete third-party image scan.

The overlay is optional: the original metrics-only Compose file remains unchanged.
Provisioning/overlay files use the JSON subset of YAML so deterministic tests require
no additional parser dependency. Dashboard JSON is under
`ops/monitoring/grafana/dashboards/`; Grafana's native file provider reads its password.
No application code, metrics contract, dependency versions or Kubernetes pins changed.

| Setting | Approved local value |
| --- | --- |
| Project/network | Existing `finsecure-monitoring`, separate from Jenkins |
| Host binding | `127.0.0.1:3000` only; no public listener/tunnel |
| Runtime identity | UID/GID 472, read-only root, all capabilities dropped, no-new-privileges |
| Resources | 0.5 CPU, 512 MiB memory, no additional swap, 16 MiB temporary space |
| Dashboard/config | Read-only binds; individual provisioning files preserve unused vendor directories |
| Grafana database | Owned named volume `finsecure-monitoring_grafana-data` |
| Secret volume | External, purpose-labelled `finsecure-monitoring-grafana-secrets`, read-only in Grafana |
| Authentication | One trusted local operator (`admin`), unique generated password, no anonymous dashboard access |
| Data source | Read-only provisioning, server-side `http://prometheus:9090`, 15-second scrape interval hint, 5-second query timeout |
| Dashboard | Last 15 minutes, 15-second refresh, reset-aware 2-minute rate windows |
| Readiness/query observation | 120 seconds per phase; 2-second polling, 5-second HTTP timeouts |
| Stop allowance | 30 seconds, preserving all named data/secret volumes |

Analytics reporting, update/news checks, external plugin preinstallation and Grafana
alerting are disabled for this scope. No external notification/identity service,
Grafana plugin installation, cloud resources or managed-cluster monitoring is included.
The administrative operator remains trusted; provisioned resources rejecting UI
persistence is not a security boundary against an administrator.

## Credential ownership and recovery boundary

The operator's host credential is at
`~/.config/finsecure-pay/monitoring/grafana-admin-password`, mode **0400**, inside a
private **0700** directory. It stays owned by the operator, not container UID 472.
The initial host bind-mount ownership attempt failed safely on Docker Desktop; the
[historical failure](../../evidence/task-06/step-02-preflight.md) is retained.
The user approved the replacement Linux secret-volume design.

`scripts/monitoring_credentials.py init` preserves the existing host value. For a new
installation it generates a value only when neither existing data nor a secret volume
requires recovery. A labelled, empty Linux volume is initialized through **stdin**,
not arguments/environment, by a network-isolated helper with only CHOWN added.
The volume directory is mode 0700 and its regular single-link password file is mode
0400, both UID/GID 472. Helpers are removed after their operations. No host file is
chowned, and no Jenkins file/volume is mounted into these helpers.

`verify` reads existing state only and checks ownership, internal permissions and
exact host/volume agreement without printing either value. Missing, foreign or
mismatched state fails closed; no automatic rotation, reseeding, chmod repair or
recovery guess is performed. Docker operations have 30-second bounds. If a Docker
failure leaves ambiguous helper state, inspect only the owned
`finsecure.purpose=grafana-credential` helpers; do not globally prune or rerun blindly.

The native `$__file{...}` setting avoids putting the password in Grafana's environment;
this was checked against both container configuration and the running server environment.
Authentication to protected APIs was separately tested: matching files alone does not
prove agreement with an existing Grafana database. The initial-admin setting is not
an automatic password-rotation mechanism.

These are local plaintext stores, not encrypted provider secret management. Anyone
with Docker-daemon access is trusted. Never commit databases/passwords, put values in
command arguments or screenshots, or paste credentials into chat.

## Start, inspect and stop

Run from the repository root. First check Docker capacity and that ports 8000, 9090
and 3000 are available. Do not stop Jenkins, change Docker allocation, take over
another process or overwrite an unowned volume to resolve conflicts.

Load/tag an **exact verified application archive** as described in the
[metrics runbook](metrics.md). This demonstration used normal SCM build #18's archive
at `5e53c5f`, not a fresh application rebuild. Image/source/manifest identity was checked.
Pull the pinned Grafana image before invoking the helper, which never pulls implicitly:

```sh
docker pull grafana/grafana:13.3.0@sha256:488984b716c0862639f91a698adbe2862677a5a07bad42da5f03f3030883b205
uv run --locked python scripts/monitoring_credentials.py init
uv run --locked python scripts/monitoring_credentials.py verify
docker compose -f ops/monitoring/compose.yaml -f ops/monitoring/grafana.compose.yaml config --quiet
docker compose -f ops/monitoring/compose.yaml -f ops/monitoring/grafana.compose.yaml up --detach --no-build
```

Open <http://127.0.0.1:3000/d/finsecure-pay-local/local-metrics> and sign in locally as
`admin`, using the password from the private host file. Do not display the password
in evidence. The helper CLI prints only status, never the value.

Grafana's health/login/static resources are publicly readable on loopback by design.
Unauthenticated dashboard navigation redirects to login; protected dashboard and
data-source APIs returned 401 in verification. This is not a claim that every Grafana
HTTP route requires authentication, or that loopback HTTP is suitable for production.

Use **both files** to operate the full stack; the metrics-only file does not manage
Grafana. After verification:

```sh
docker compose -f ops/monitoring/compose.yaml -f ops/monitoring/grafana.compose.yaml stop --timeout 30
```

Do not use `--remove-orphans`, `down --volumes` or global prune. Preserve the Grafana
and Prometheus data volumes plus the external secret volume. No backup/recovery or
production retention guarantee is introduced.

## Dashboard interpretation

| Panel | Meaning |
| --- | --- |
| Request rate | Sum of HTTP counter rates in requests/second; metrics scrapes excluded |
| Mean ASGI handling latency | Rate of duration sum divided by rate of count; seconds displayed in an appropriate unit, not client delivery latency |
| Validation outcomes | Rates grouped by accepted/rejected/invalid; rejection is not a server failure |
| Application process memory | Resident memory in MiB, not pod/node memory or a container limit |
| Application scrape health | Prometheus `up`, not business success or Kubernetes readiness |

Missing/stale samples are not converted to successful/zero measurements. Idle rate
windows can have undefined mean latency. Panels do not reuse a stale last-non-null
latency. The 2-minute rates are not equal to the 1-minute traffic generator's send rate;
scrape timing, series creation and extrapolation affect the displayed values.
No SLO, alert threshold or load/capacity benchmark is implied.

## Actual verification and remaining warnings

- 578 host tests passed, including 40 dashboard/credential cases. Locked lint/format,
  warnings-as-errors tests, report generation, build and source/dependency gates passed.
  No application test threshold or extra dependency was introduced.
- An authenticated real Grafana queried all five panels. Protected APIs returned 401
  without credentials; provisioning and data-source health were verified.
- Exactly 60 synthetic application requests were sent once: 20 health, 20 accepted,
  10 rejected and 10 invalid. Actual Prometheus deltas matched all counts.
- The reviewed screenshot visibly shows 0.533 requests/second, 2.918 ms mean handling
  latency, 55.15 MiB process memory, UP and outcome-rate curves at capture time.
  These are measurements, not defaults. The isolated Chrome session logged out;
  its process and private profile were removed. Existing Chrome/Node were used.
- Log review found two missing-directory provisioning errors caused by the original
  whole-directory mount. Individual file mounts fixed them; a regression assertion
  and real authenticated startup/provisioning recheck passed. No more synthetic
  health/validation requests were generated; metrics probes and infrastructure checks continued. The screenshot remains evidence of the first successful
  panel run, not a new traffic run after that mount correction.
- Vendor security-header deprecation, search-discovery warnings and a shutdown
  context-cancellation ERROR remain recorded. The first startup also emitted migration
  warnings. No logger suppression, security-header weakening or speculative feature
  toggle was used to hide them. Chrome emitted native macOS display-link/allocator
  diagnostics despite producing the reviewed screenshot; those are retained too.
- The final three services stopped with exit 0, no OOM. Data/secret volumes and the
  unchanged host credential remain. Jenkins services were not stopped/reconfigured;
  its credential-boundary check passed. Normal SCM verification subsequently passed
  in build #19; it did not rerun the Grafana demo or resolve vendor/browser diagnostics.
  Alerts, delivery and centralized logs remain
  later steps with their own policies and approval.
