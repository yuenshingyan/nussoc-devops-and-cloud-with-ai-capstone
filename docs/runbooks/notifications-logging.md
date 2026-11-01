# Step 6.5 — Local notifications and structured logs

Status: **approved local subset verified; review/merge/publication pending**.
Branch: `task-06/step-05-notifications-logging`, from published `ab36eb5`.

654 host tests, Ruff checks, package build and source/dependency gates passed. A real
host Uvicorn subprocess produced privacy-safe JSON. After two documented rollbacks,
the approved exact Docker Desktop path alternative and mounted-file hash verification
passed live activation. Read-only/network/privilege checks remain enforced.

The initial five-case native matrix verified success/failure delivery, disabled behavior
and encoding-error handling with explicit isolated-job opt-in. Its discovery that
Docker env did not automatically become Pipeline env is retained in the
[earlier results](../../evidence/task-06/step-05-local-delivery.md).

The subsequently approved base-JCasC bridge now exposes the single notification flag
with a false default. Local controller `step-06-05` was rebuilt from unchanged pins;
all 73 reference plugin archives were byte-identical, runtime plugin inventory and
resource limits unchanged. One approved recreation passed. A new native probe inherited
true in both agentless and Python-agent contexts without environment overrides and
received another real email (inbox total three). See [bridge evidence](../../evidence/task-06/step-05-environment-bridge.md).

Full candidate CI at `1a1f4a3` passed 654 tests, existing gates and 33 artifact checks,
then delivered a real email. Its exact gated image produced verified JSON logs and
matching metrics for bounded synthetic traffic and was removed after exit 0. Native
notification timeout/operator-abort probes both ended ABORTED without sending mail;
these inserted a wait before SMTP, not a blocked-socket experiment. See the
[completed local verification](../../evidence/task-06/step-05-notifications-logging.md).

Jenkins and Mailpit remain running, all eight owned review/probe jobs disabled, normal
CI still #25 on its old published Jenkinsfile. Other monitoring services are stopped.
No cloud collection or Gmail delivery claim.

The old controller image and a private 0600 root-configuration backup inside its
existing home volume are retained through review; no private configuration was exported.
The false default is regression-tested, but a live profile-off restart was not performed.
Next: review before merge/publication, then verify the new normal SCM build and its
notification. Main's old Jenkinsfile does not yet include the new notification hook.

While the overlay is active, run boundary checks with:

```sh
uv run --locked python ops/jenkins/verify_secrets.py --notifications
```

The baseline mode intentionally rejects the extra configuration mount. Compose
rollback alone does not restore every persisted Jenkins setting. Historical failures:
[initial checkpoint](../../evidence/task-06/step-05-checkpoint.md) and
[diagnostic activation](../../evidence/task-06/step-05-diagnostic.md).

Step 6.4 is published. Automatic SCM build #25 passed 584 tests, all gates and
33 artifact checks. That build did not demonstrate Jenkins email delivery.

## Scope and approval

Reuse the installed Jenkins Mailer and Pipeline Basic Steps plugins instead of
adding Email Extension. Use the existing pinned Mailpit receiver, not Gmail or an
external SMTP provider. No new dependencies, cloud resources or registry publication.
This is a local subset: centralized cloud logging remains pending, not implemented
by Docker log access. The assignment allows notification alternatives; instructor
acceptance of local Mailpit delivery is not established.

The following scope was approved. The remaining live work must preserve these limits.

### Jenkins notification delivery

- Add an optional, reproducible Jenkins notification Compose overlay and supplementary
  JCasC configuration. Preserve the existing authentication, secret volumes, agent,
  builder, memory/CPU limits and loopback HTTP binding. The later approved controller
  rebuild changed base JCasC only, using the same pinned base and byte-identical plugins.
- Attach **only the controller** to the existing Mailpit notification bridge. This
  changes network reachability: services on that bridge can reach the controller's
  authenticated HTTP listener internally. Do not attach the agent or builder.
  SMTP remains unpublished; do not expose an additional host port.
- Recreate the controller once while Jenkins is idle to apply the overlay. Preserve
  all history and credentials. Stop if the queue is nonempty or a build is running.
  Allow up to 180 seconds for controller readiness and agent reconnection; on failure,
  collect diagnostics and restore the previous controller configuration. Do not prune,
  rotate credentials, increase resources or reset Docker.
- Use `mailpit:1025`, with no SMTP authentication or TLS on this local bridge. No
  external relay, forwarding, commit-author recipient expansion or Gmail credentials.
- Sender: `finsecure-ci@example.test`. Sole recipient:
  `finsecure-operator@example.test` (already permitted by Mailpit).
- Send one plain-text result message per opted-in completed CI build, after artifact
  publication attempts. Include only job/build identity, source revision when known,
  pre-notification build result and the local Jenkins build link. No logs, environment
  dumps, request bodies or attachments. Label the result as pre-notification so a
  delivery failure cannot make the message's status misleading.
- Make notification opt-in explicit in the notification-enabled controller's job
  environment. Baseline Jenkins without that overlay must not attempt SMTP delivery;
  disabled notification status must be visible, not reported as delivery success.
- One send attempt, no automatic retries. Use a 180-second Pipeline notification
  budget, 60-second SMTP connect/read limits and 60-second write limit. Verify the
  installed Mailer's actual timeout behavior: retained installed-plugin bytecode
  confirms the system-property defaults and hard-coded 60-second connect/read limits.
  Upstream Mailer
  source overrides connect/read properties to 60000 ms, so setting smaller JVM
  properties alone is not proof of smaller timeouts. Pipeline cancellation alone is
  not proof that a blocked socket has closed.
- An ordinary notification error makes an otherwise successful build UNSTABLE and
  emits a visible diagnostic; it never improves an existing failed/unstable result.
  User cancellation and timeout interruptions propagate rather than being swallowed.
  Preserve artifact and security gates unchanged.
- Keep Mailpit running while CI notifications are enabled. Its existing temporary
  inbox disappears on stop: export evidence before cleanup and do not promise durable
  email retention. Prometheus, Alertmanager and Grafana need not run for Jenkins mail.

### Application logging contract

Use standard Python logging and a fixed INFO threshold, with no new environment
setting. Emit UTF-8 JSON lines to the container's standard stream. Define the
formatter and instrumentation in `src/finsecure_pay/observability/`; keep services
free of logging I/O. Do not change the API request/response contract.

Every application event has `timestamp` (timezone-aware UTC ISO 8601), `level`
(standard logging level name) and `event` (a fixed event name). Additional fields:

| Event | Level | Fields |
| --- | --- | --- |
| `http_request_completed` | INFO | `route`, `method`, `status_class`, `duration_seconds` |
| `http_request_failed` | ERROR | Same fields, plus `error_code=UNEXPECTED_ERROR` |
| `http_request_cancelled` | INFO | Same fields; cancellation still propagates |
| `validation_outcome` | INFO | `outcome`, `codes` |

- Route values: `/health`, `/validate`, or `other`; method: `GET`, `POST`, or `OTHER`.
  Status classes: `1xx` through `5xx`, `no_response`, or `other`, matching metrics.
- Duration uses a monotonic clock and seconds. Do not use wall-clock subtraction.
- Validation outcomes: `accepted`, `rejected`, `invalid`. Codes contain only existing
  documented business-rejection codes; use `INVALID_REQUEST` for schema-invalid input
  and an empty list for acceptance. Do not log validation messages or field locations.
- Exclude routine `/metrics` access events, as with request metrics. Preserve exception
  propagation and cancellation; do not buffer request or response bodies for logging.
- No transaction/user IDs, addresses, headers, query strings, arbitrary paths, body
  values, exception messages, source-line contents or secrets. No correlation IDs or
  tracing. Replace Uvicorn's raw access log with these privacy-safe events.
- Server diagnostics must retain severity and safe event/error identification without
  raw caller-controlled message/exception text. Document the concrete server-event
  mapping and privacy exclusions during implementation; do not silently drop warnings.
  Configuration/startup failures must still fail startup.

### Verification and cleanup

1. Recheck host and Docker VM capacity, idle Jenkins, existing secrets, volumes and
   network ownership before changing services. Retain previous configuration/state.
2. Add deterministic tests for JSON shape, UTC timestamps, finite event fields,
   accepted/rejected/invalid requests, exceptions, cancellation and absence of synthetic
   sensitive markers. Verify existing metrics and API behavior remain unchanged.
3. Run locked Ruff lint/format checks, all tests, packaging and existing security gates.
4. Validate SMTP configuration and real receipt using an isolated candidate job, not
   a fabricated inbox entry. Exercise success and a controlled failure in that job;
   do not introduce a failing test or vulnerable artifact into the baseline. Confirm
   the disabled-notification and notification-error paths without failing normal CI.
5. Obtain a gated candidate image and capture real JSON logs for bounded synthetic
   accepted, rejected and invalid requests. Use log event/time ordering, not invented
   correlation IDs, to relate the isolated requests to the records.
6. Export raw local emails, parsed log evidence, inspected Mailpit screenshots, exact
   image/source provenance and timestamped state. Scan exports for known credentials
   and synthetic sensitive markers; hash the reviewed evidence. Keep diagnostics.
7. Stop the owned application and disable the candidate job after verification. Keep
   Jenkins and its opted-in Mailpit receiver operational. Preserve volumes/history;
   do not start the alert stack or repeat the application-outage demonstration.
8. Commit and pause for review before source publication. Update local Docker log
   commands. Document `kubectl logs` as **unexecuted until a cluster exists**; cloud
   collection, centralized queries and retention require separate provider approval.

## References

- [Mailer plugin](https://plugins.jenkins.io/mailer/)
- [Pipeline Basic Steps](https://www.jenkins.io/doc/pipeline/steps/workflow-basic-steps/)
- [Upstream Mailer source](https://github.com/jenkinsci/mailer-plugin/blob/master/src/main/java/hudson/tasks/Mailer.java)

Upstream source is design input; the retained installed-plugin bytecode is separate
local evidence. SMTP write timeout is configured. Native encoding-error handling and Pipeline
interruption propagation were verified; cancellation of an already-blocked SMTP
socket was not exercised.

## Reproducing the local profile

Follow [base Jenkins setup](local-jenkins.md) and [receiver setup](alerts.md) first.
These are operator commands, not commands to rerun against a busy controller. Check
capacity, queue/agent idleness and existing volume/network ownership. Obtain approval
before another controller recreation and preserve a private rollback configuration.
Do not prune caches, delete shared volumes or increase resources.

From the repository root, with the pinned receiver image and reviewed controller image
already available:

```sh
# Start only the existing local receiver; do not manufacture an application outage.
docker compose -f ops/monitoring/compose.yaml -f ops/monitoring/alerts.compose.yaml \
  up -d --no-deps --pull never mailpit
# Applies the optional profile; recreates the controller if its configuration changed.
docker compose -f ops/jenkins/compose.yaml -f ops/jenkins/notifications.compose.yaml \
  up -d --no-deps --no-build --pull never controller
uv run --locked python ops/jenkins/verify_secrets.py --notifications
```

The existing local controller image can be built from the reviewed source using
`docker compose -f ops/jenkins/compose.yaml build controller`, after capacity checks
and rebuild approval. Compare pinned/plugin inventory before replacement. Wait up to
180 seconds for controller readiness and agent reconnection; investigate/roll back on
failure. Do not call an HTTP 200 alone proof of configuration or notification delivery.

Inspect actual mail at `http://127.0.0.1:8025/`. Export raw messages before stopping
Mailpit; its tmpfs inbox is not durable. Successful email from an inline review job is
not proof of an automatic SCM-triggered notification. After approved publication,
verify the normal build's revision, SCM cause, gates and matching received message.

For an approved shutdown, first recreate the controller using **base Compose only**
with the new `step-06-05` image; its base JCasC defines the flag's false default. Verify
the effective job setting and baseline boundaries before stopping Mailpit. This
profile-off sequence was not executed during the one-recreation bridge test. Restoring
an older image alone is not guaranteed to clear persisted global/Mailer properties.
Never stop an active CI receiver and silently accept resulting delivery failures.

## Logging implementation and troubleshooting

`JsonEventFormatter` accepts only the fixed event fields above. Unknown runtime/server
messages remain visible as `runtime_diagnostic` or `server_diagnostic` at their original
standard severity, with `UNCLASSIFIED_MESSAGE`. Exception records use `UNEXPECTED_ERROR`.
Known Uvicorn startup/shutdown, invalid-HTTP and unsupported-upgrade templates map to
fixed codes in `SERVER_MESSAGES`. Raw message arguments and exception text are omitted
for privacy, not silently discarded as warnings. This reduces diagnostic detail;
unknown messages need investigation using reviewed synthetic reproductions, not raw
customer-data logging. No application settings or HTTP contracts changed.

The real-process test reserves an ephemeral loopback socket, allows ten seconds for
startup, uses one-second HTTP timeouts, and allows five seconds for graceful shutdown
before kill-and-wait (five seconds). A forced kill fails the test. Uvicorn re-raises
SIGTERM outside PID 1 after logging completed shutdown; that host subprocess's expected
return code is `-SIGTERM`, not a container exit-status claim.

The exact candidate container was verified and removed after export. For a running
owned application container, local troubleshooting uses:

```sh
docker logs --since 5m --timestamps <owned-application-container>
```

Docker's timestamp prefix is transport metadata; application JSON has its own UTC
`timestamp`. Correlate a bounded synthetic request by its request window and event
order. Do not claim unique per-request correlation under concurrent traffic.

Future cluster commands (not executed; no cluster or cloud log collector configured):

```sh
kubectl -n <approved-namespace> logs deployment/<approved-deployment> --all-pods=true --since=5m --timestamps
kubectl -n <approved-namespace> logs <pod> --previous --timestamps
```

Cloud collection, provider queries, retention and evaluator access remain pending.
