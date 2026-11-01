# Step 6.5 — Approved local remediation

Status: **implemented and locally verified; review/publication pending**. Main remains
`f4b2c5c`, normal CI #26. Its original incomplete email is preserved unchanged.

## Revision propagation

The checkout stage now explicitly saves `git rev-parse HEAD` in
`env.FINSECURE_SOURCE_REVISION`; cleanup reads that value instead of relying on
`env.GIT_COMMIT`. Failure before checkout retains the `unavailable` fallback. No
recipient, timeout, failure policy, dependency, application or image configuration changed.

- Ruff lint/format, **655 host tests**, and package build passed.
- Native validation accepted the complete modified Jenkinsfile.
- An owned manual probe used the actual modified checkout block and cleanup block,
  binding `scm` to a public Git checkout at `f4b2c5c`. It did **not** inject a revision
  into the environment. The Python-agent checkout read the actual Git HEAD; agentless
  cleanup delivered a SUCCESS email with that exact revision.
- A separate controlled pre-checkout failure delivered FAILURE with `unavailable`.
  Both jobs were disabled. Two real receipts exported; success screenshot inspected.
- These inline probes are not automatic SCM CI, full application gates or new image
  evidence. Automatic verification of the published fix remains pending.

## One controller recreation

The user approved one bounded recreation. Queue empty, agent idle/online, source
configuration hash and exact controller image verified first. Five existing emails
were exported. The private rollback backup remained mode 0600, UID/GID 1000, in its
existing volume; contents were not exported.

Only the controller was targeted, with `--force-recreate --no-deps --no-build --pull never`.
The same image `sha256:1cb8838d10c58513bb35c137637954533b744777e1f1d237448fd4f444918d41`
was reused. Controller/agent readiness returned within the 180-second bound. The
notification file is readable again and its hash matches the host. Full notification
boundary verification passed, including anonymous-access denial and credential checks.

The observer then failed its strict environment **array equality** assertion. This
failure is retained. The original environment array was held only in process memory,
so an order-only explanation cannot be proven. No second recreation or retry occurred.
A separate read-only reconciliation confirmed the current environment **map** exactly
matches the pinned image defaults plus rendered Compose; plugin inventory and resource
limits match the previously reviewed bridge baseline. This does not retrospectively
prove equality of the lost old array. The subsequent two delivered probe messages
also verify actual post-recreation opt-in and SMTP operation.

No caches/volumes were pruned, resources increased, dependencies/plugins changed or
cloud resources contacted. Jenkins/Mailpit remain running, main still #26, queue empty
and agent idle. Browser/profile removed. Inbox now contains seven messages; receipts
are exported. No application container was started for this remediation.

## Publication precaution

Do not switch through an older checkout that removes a live bound configuration file.
For the next approved publication, verify `main` is an ancestor of the reviewed step
HEAD, advance its ref without changing the working tree, and push that exact revision.
Only switch branches when both refs have identical trees. Do not move the bind to a
new deployment-copy design without review or weaken its file/hash verification.

## Evidence

[Host checks](step-05-remediation/host-checks.txt),
[native probe results](step-05-remediation/probe-results.json),
[success receipt](step-05-remediation/checkout.eml),
[failure receipt](step-05-remediation/before_checkout.eml),
[screenshot](step-05-remediation/notification.png),
[original recreation diagnostic](step-05-remediation/recreation-observer.txt),
[read-only reconciliation](step-05-remediation/reconciliation.json),
[manifest](step-05-remediation/SHA256SUMS).
