# Step 6.3 — Local alert configuration and receiver preflight

**Later status:** merged/published as `dcab1c5`; normal SCM build #21 verified.
See the [follow-up](step-03-scm-verification.md). The candidate record below preserves
its original execution and then-pending publication status.

Implemented on `task-06/step-03-alert-configuration`, from reviewed/published
`c27a2e8`. **Review, merge/publication and normal SCM verification pending.**
The user approved the one-minute/15-second alert and chose local Mailpit instead of
Gmail delivery. No account credentials were requested or installed.

## Actual successful checks

- 584 host tests passed with warnings treated as errors; Ruff lint/format and package
  build passed. Source gate: 29 LOW Bandit findings, zero MEDIUM/HIGH. All 15 runtime
  dependencies audited, no known advisories. No application/dependency changes.
- Real `promtool` validated the configuration and six synthetic rule scenarios:
  healthy, failed, absent, brief failure, recovery and failed-to-stale continuity.
  `amtool check-config` accepted the email receiver and route. Compose validation passed.
- Actual running Prometheus reported the rule healthy and inactive with duration 60
  seconds and discovered Alertmanager. Alertmanager loaded the Mailpit route.
- Mailpit's API was reachable via the loopback-published port and its inbox was empty.
  A network-scoped helper completed SMTP EHLO, MAIL FROM and RCPT TO (all 250), then
  RSET. **No DATA, actual alert email or received-notification evidence is claimed.**
- Runtime checks verified nonroot users, read-only roots, dropped capabilities,
  no-new-privileges, loopback-only published ports and unpublished SMTP. Mailpit was
  connected only to the dedicated notification bridge.
- Final cleanup stopped Prometheus first, then the other three services. All four
  exited 0, without OOM. Grafana stayed stopped; its data/secret volumes and the
  Prometheus/Alertmanager volumes remain. Mailpit's temporary inbox disappears on stop.

[Live verification](step-03/verification.json), [rule observations](step-03/rules.json),
[Alertmanager discovery](step-03/alertmanagers.json),
[SMTP acceptance](step-03/smtp-preflight.txt), [cleanup](step-03/cleanup.json),
[host checks](step-03/host-checks.txt), [rule tests](step-03/rule-tests.txt),
[Prometheus config check](step-03/prometheus-config.txt),
[Alertmanager config check](step-03/alertmanager-config.txt), and
[source/dependency gate](step-03/security-summary.json).

## Preserved failures and limitations

1. Initial rule-test execution failed because its read-only helper had no writable
   temporary storage. A bounded 64 MiB `/tmp` tmpfs fixed it without making the root
   writable. [Original output](step-03/rule-tests-initial-failure.txt).
2. The initial internal-only notification network prevented Docker Desktop from
   exposing Mailpit's UI port. Readiness timed out. All four services then stopped
   cleanly. [First-run logs](step-03/initial-start/mailpit-logs.txt) and
   [first cleanup](step-03/initial-start/cleanup.json) are retained.
3. After correcting that network, the observer asserted rule state/health/duration
   before explicitly waiting for a completed rule evaluation. That assertion failed;
   the original API payload was not retained, so its precise failing field is not
   established. Early cleanup stopped the application with **137, OOM false**. Its
   exact termination cause is not established. [Actual state](step-03/second-start/application-state.json)
   and [logs](step-03/second-start/application-logs.txt) are retained.
4. The observer was corrected to require a real application `/metrics` response and
   completed healthy/inactive rule evaluation, within a 120-second bound. Assertions
   were not removed or suppressed. Final verification and clean shutdown passed.
5. Compose reported the retained stopped Grafana container as an orphan; it was not
   removed. Prometheus logged its graceful-stop WARN. Previously documented Grafana
   and Chrome diagnostics are not resolved by this work.

The final notification network is a **regular bridge with normal egress**, not an
outbound firewall. Only the inbox UI is loopback-published; SMTP remains unpublished.
No external mail relay/forwarding is configured. This is trusted-local synthetic test
mail, not internet/Gmail delivery, a production security design or evaluator approval.
The inbox's ephemeral lifetime is explicit; export actual message evidence before
stopping in Step 6.4. No backups or production retention policy are claimed.

## Provenance and boundaries

Official release APIs selected Alertmanager 0.34.2 and Mailpit 1.32.0. Pull outputs
retain immutable index digests; the actual ARM64 runtime image IDs are in verification.
The application reused the exact already-gated main build #18 image, ID
`sha256:8f5bd152a3acc4af31baac013d262e8de3fbe60a53d15638f8908d6c1b430e29`.
Its source/lock remained unchanged. No new application image was built, loaded or
published for this step. No full vulnerability/signature assurance is claimed for
third-party Alertmanager/Mailpit images.

No deliberate interruption, actual notification delivery, Jenkins reconfiguration,
registry publication or cloud deployment was performed. Step 6.4 and Step 6.5 remain
separate work. See the [runbook](../../docs/runbooks/alerts.md) for exact routing delays,
shutdown ordering, data lifetime and reproduction commands.

[Historical bounded verifier](step-03/verify-live.py.txt) and
[checked source hashes](step-03/checked-source-hashes.json) distinguish executable
configuration from captured observations. [SHA-256 manifest](step-03/SHA256SUMS)
protects the retained evidence files; large images remain outside Git.
