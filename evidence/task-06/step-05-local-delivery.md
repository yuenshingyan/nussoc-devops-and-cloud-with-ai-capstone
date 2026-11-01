# Step 6.5 — Verified mount correction and real Jenkins mail

Status: **partial, unpublished**. The approved narrow Docker Desktop correction is
implemented and its one authorized activation passed. Real Jenkins messages were
received with explicit isolated-job opt-in. Normal CI opt-in wiring remains incomplete.

## Mount correction and checks

The verifier still requires the exact destination, a read-only bind, expected named
volumes, approved networks, UID, capabilities and credential boundaries. It accepts
only the original source or that exact source prefixed with `/host_mnt` when
`docker info` identifies **Docker Desktop**. It does not generally normalize paths.
The mounted configuration SHA-256 must match the host file, which is read again to
reject changes during verification.

- **653 host tests passed**, including new exact-path, non-Desktop, unrelated-path,
  writable/extra-mount and digest/change rejection cases.
- Locked Ruff lint/format checks, `uv build` and source/dependency gates passed.
  Bandit retained 29 LOW findings, no MEDIUM/HIGH; 15 runtime dependencies audited
  with no blocking findings. No new dependency or plugin.
- Activation passed after the controller and existing agent became ready. The mounted
  configuration hash was
  `ac001dffddf34fb074ca4d86f62c46ecb292675d9d6a715ac6137b50b954d702`.
- Native Jenkinsfile validation and post-activation boundary verification passed.
  Host/VM free space before activation was approximately 10/14 GiB respectively.

[Activation/check records](step-05-path-fix/SHA256SUMS).

## Actual delivery and native failure handling

Owned manual job `finsecure-notification-review-20261101065903` used the candidate
Jenkinsfile's actual cleanup block in an isolated notification-only Pipeline. Its
explicit Pipeline environment opt-in is a deliberate difference from normal CI.

| Build | Controlled case | Actual result | Inbox total |
| --- | --- | --- | --- |
| 1 | Successful synthetic stage, mail enabled | SUCCESS | 1 |
| 2 | Deliberately failed synthetic stage, mail enabled | FAILURE | 2 |
| 3 | Mail explicitly disabled | SUCCESS | 2 |
| 4 | Successful stage, invalid mail charset | UNSTABLE | 2 |
| 5 | Failed stage, invalid mail charset | FAILURE | 2 |

The invalid charset caused a **real native mail-step encoding exception**, not a
mocked build result. It verifies ordinary notification-error handling, not a network
outage, blocked SMTP socket, timeout or user-abort scenario. No automatic retries.

Exactly two completed SMTP messages arrived from `finsecure-ci@example.test` to
`finsecure-operator@example.test`. Raw messages, API metadata, executed scripts,
console output and inspected native Mailpit screenshots are retained:

- [Success email](step-05-mail/success.eml) / [screenshot](step-05-mail/success.png)
- [Failure email](step-05-mail/failure.eml) / [screenshot](step-05-mail/failure.png)
- [Results](step-05-mail/results.json) / [manifest](step-05-mail/SHA256SUMS)

These inline jobs did not check out application source or run application/image gates;
`Revision: unavailable` is accurate. They have operator-trigger provenance, not SCM
provenance. UI dates use UTC+08; raw/API times and Jenkins build timestamps retain
execution timing. This is local SMTP receipt, not Gmail/internet delivery or proof of
instructor acceptance of this receiver.

## Preserved failures and remaining wiring issue

1. The first isolated harness placed `agent none` and `options` on the same Groovy
   line, producing a compilation failure before any mail attempt. The production
   Jenkinsfile had already passed native validation. The corrected harness uses
   separate lines and validates each generated script before execution.
2. The next job completed SUCCESS but correctly logged notifications disabled; its
   observer failed because it expected a message. The Docker controller variable
   alone was **not** visible in Pipeline environment. A separate read-only probe on
   the real Python agent confirmed the same absence. Do not present this as successful
   automatic CI opt-in.
3. Explicit opt-in in the isolated job allowed the five-case matrix above. It proves
   real delivery and failure handling, but does not repair normal CI configuration.

Both earlier job histories, scripts, failed observations and the agent probe are
retained. All four owned jobs are disabled, including the context probe. Chrome was
closed and its isolated profile removed; native browser diagnostics are retained.

## Current state and next decision

Main remains build #25; queue empty; agent online/idle. Jenkins controller, agent,
builder and Mailpit remain running. Other monitoring/application services are stopped.
No registry/cloud work or source publication occurred. Mailpit's temporary inbox is
not durable across stop/recreation; exports preserve both messages.

Proposed next fix, **not implemented or authorized yet**: explicitly bridge the
controller opt-in into Jenkins' job environment through JCasC. Put the bridge in the
base JCasC configuration with a false default, not only in the optional file: otherwise
an enabled global property could persist when the overlay is removed. This requires a
new local controller image with the same pinned base/plugins and one controller
recreation. Retain the old image for rollback, preserve volumes/resources, and add no
plugin or dependency. Test the effective job environment before claiming opt-in works.

Still pending: that wiring correction; cancellation/timeout verification; full candidate
Jenkins gates and exact exported-image logging; final evidence/review. The 653 host
tests are not a candidate CI/image result. Centralized cloud logging remains deferred.

Text exports replace repository/temporary path prefixes and the closed browser debugger
endpoint. Raw emails and screenshots are unchanged; known credentials were checked
before export. Hash manifests cover the curated records.
