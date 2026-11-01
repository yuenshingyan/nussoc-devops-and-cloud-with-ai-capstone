# Step 6.5 — Local notifications and structured logs

Status: **scope approved; candidate implemented, live verification blocked**. Branch:
`task-06/step-05-notifications-logging`, from published `ab36eb5`.

632 host tests, Ruff checks, package build and source/dependency gates passed. A real
host Uvicorn subprocess produced privacy-safe JSON for synthetic requests. Native
Jenkins Pipeline validation passed. The first controller activation failed the exact
notification-file mount check after controller/agent readiness. The safety handler
restored the baseline controller and stopped Mailpit. Baseline boundaries passed;
normal CI remains at #25. The actual failing mount metadata was not captured before
rollback; isolated bind probes did not reproduce the mismatch. Do not infer a cause
or loosen the check. An additional diagnostic restart was approved and captured an exact-source mismatch:
Docker Desktop reported the same path with `/host_mnt` prefixed. The unchanged check
rejected it and the controller was rolled back again. See the
[diagnostic evidence and proposed narrow correction](../../evidence/task-06/step-05-diagnostic.md).
Accepting that exact Docker Desktop representation plus mounted-file hash verification,
and one further activation, require approval. No boundary check has been relaxed.
See also the [original checkpoint](../../evidence/task-06/step-05-checkpoint.md).

No Jenkins email receipt or gated candidate-container log proof is claimed yet.
The Mailer descriptor's `mailpit:1025` settings persisted in Jenkins home, but the
controller notification opt-in and extra network/mount were removed on rollback.
Restoring Compose does not restore every persisted Jenkins setting.

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
  builder, memory/CPU limits, controller image and loopback HTTP binding.
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
local evidence. SMTP write timeout is configured but live notification cancellation
and error behavior remain to be verified.

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

After a gated candidate container has been verified, local troubleshooting uses:

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
