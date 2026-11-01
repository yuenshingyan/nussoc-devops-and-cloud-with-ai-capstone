# Step 6.5 — Candidate implementation and rolled-back activation

Status: **partial, unpublished; Jenkins receipt and gated-container verification pending**.
The approved local scope is in the [runbook](../../docs/runbooks/notifications-logging.md).
No cloud collection, registry publication, additional plugin or dependency was added.

## Implemented candidate

- Allowlisted JSON application events and Uvicorn configuration; raw access logging
  replaced with bounded route/method/status/duration events. Outcomes contain only
  accepted/rejected/invalid plus documented rejection codes. No bodies or identifiers.
- Optional controller-only SMTP network/configuration overlay using existing Mailer
  and Mailpit. Pipeline cleanup sends a plain-text result only with explicit opt-in.
  Ordinary delivery failure cannot turn a failed build green; interruptions propagate.
- Exact opt-in mount/network boundary checks, without relaxing baseline verification.

## Actual checks

- **632 tests passed**, including a real Uvicorn subprocess with accepted, rejected,
  invalid and unknown-path requests; JSON parsing and synthetic-secret absence checked.
- Locked Ruff lint/format checks and `uv build` passed.
- Source/dependency gates passed; see retained summary for actual findings.
- Jenkins' native Declarative validator accepted the candidate Jenkinsfile.
- Installed Mailer bytecode confirms 60000 ms connect/read limits and inherited JVM
  property defaults. It does not prove completed SMTP delivery or cancellation.
- Before activation: approximately 10 GiB host free and 14 GiB Docker VM free; controller,
  agent and builder running, main #25, empty queue and idle agent.

The initial new outcome test exposed incorrect introspection of a Python `type` alias:
`get_args(alias)` returned no codes. Reading `alias.__value__` fixed this; regression
cases cover every documented rejection code. A subsequent real-process test initially
expected exit zero, but Uvicorn re-raises the operator-requested SIGTERM outside PID 1.
The corrected test requires `-SIGTERM` **and** completed application shutdown; forced
kill is not accepted. Both initial failures are retained, not counted as passes.

## Failed activation and recovery

1. Started only existing Mailpit; applied the controller overlay without rebuilding
   the controller image, modifying the agent/builder or increasing resources.
2. Controller became accessible and its existing agent reconnected. Mailpit inbox was
   empty. No notification job or SMTP send ran.
3. `verify(notifications=True)` failed with
   `notification_configuration_mount_invalid`. The exact offending mount metadata was
   not exported before rollback; the predicate covers missing/duplicate mount, wrong
   type, writable mode or source mismatch. **The cause is not established.**
4. The safety handler restored the baseline Compose controller and stopped Mailpit.
   Baseline secret/isolation checks passed afterward. Agent is online/idle, queue
   empty, main remains #25, monitoring stopped, and notification opt-in absent.
5. Mailer's non-secret `mailpit:1025` configuration persisted in Jenkins home. The
   rollback restored runtime configuration, not every Jenkins persisted setting.
   No SMTP authentication is configured. No credentials were rotated.
6. Separate `/bin/true`/unstarted bind probes produced the expected read-only source
   and destination. They did not reproduce or diagnose the controller failure. Probe
   containers and their newly created anonymous volumes were removed; shared named
   volumes, caches and history were preserved.

Another controller activation is **not** authorized by the original one-activation
budget. Request approval for one diagnostic restart, capture safe mount metadata
before validation/rollback, and keep the strict boundary checks. Do not claim the
notification environment is active or messages were received.

## Evidence and remaining work

[Manifest](step-05-checkpoint/SHA256SUMS) covers reviewed records, host checks,
source-gate summary, native validator output, bytecode, activation observer/commands,
bind probes and final state. Known credential values were checked before export.
Repository and temporary directory prefixes are sanitized in text records; test data
are synthetic. The retained activation script documents the actual attempt, not a
reusable repair command.

Pending: diagnostic controller activation; actual candidate-job success/failure emails
and inspected inbox; disabled/error/cancellation policy checks; full candidate Jenkins
image gates and exact exported-image log collection; cleanup/evidence and review.
Host tests and mocks are not substitutes for those checks. No merge or publication.
