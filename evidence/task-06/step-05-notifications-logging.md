# Step 6.5 — Verified local notifications and structured logs

Status: **approved local subset verified; review/merge/publication pending**. Cloud
centralized collection and cluster troubleshooting remain deferred, not implemented.

## Candidate CI and provenance

Owned manual job `finsecure-ci-logging-review-20261101081204` build #1 ran candidate
`1a1f4a3be0424ac7c0f62549d2ce3820c37fcbd0` and finished **SUCCESS**:

- 654 tests passed, no skips/failures; lint, formatting, packaging and existing
  source/dependency/image gates passed; **33 downloaded artifacts verified**.
- Coverage measured 267/270 lines (98.89%) and 54/58 branches (93.10%). Coverage gates
  remained INACTIVE; no numerical threshold was introduced.
- Bandit: 29 LOW, no MEDIUM/HIGH; 15 runtime dependencies audited, no blocking findings.
- Image scan: zero known findings at every severity, not end-of-life; existing report,
  image identity, database-age, lock and checksum checks passed. Temporary scan cache
  was removed by the existing gate; older diagnostic databases were untouched.
- The normal cleanup hook inherited the JCasC opt-in and delivered an actual success
  email with the candidate revision. Raw message and inspected screenshot retained.

This was **not automatic SCM CI**: the wrapper checked out published base `ab36eb5`,
verified a local Git bundle, fetched the candidate and checked out its exact commit.
It updated `GIT_COMMIT` to that verified candidate so the email did not incorrectly
name the initial base checkout. Application checks, gates and notification logic were
otherwise unchanged; no Dockerfile override or deliberate vulnerable artifact.

Image archive SHA-256:
`f75a0abb3ad4598195c24c17651d7db39e3885b4e51ed0f805a4ba2a086da682`

Image ID:
`sha256:e7afa26d5f7bead9b3f47bb44ad79a6243c80c90343d92b28580b31dbfe668fb`

[Verification](step-05-ci/verification.json), [artifact hashes](step-05-ci/artifact-hashes.json),
[console](step-05-ci/console.txt), [email](step-05-ci/notification.eml),
[screenshot](step-05-ci/notification.png), [manifest](step-05-ci/SHA256SUMS).
Package/image binaries remain in Jenkins artifact storage and ignored operator reports,
not Git. The 33-artifact verification record includes their hashes; this Git evidence
bundle contains the reviewed reports and evidence, not all binaries.

## Exact gated-image logging

The above archive was hash-checked, loaded and run **by image ID**. It was not replaced
with an older monitoring image or rebuilt locally. The owned test container had UID
10001:10001, read-only root, ALL capabilities dropped, no-new-privileges, 0.5 CPU,
256 MiB RAM/no extra swap, a bounded `/tmp` tmpfs and loopback-only port 8000.

Actual requests: health readiness, one accepted validation, one negative-amount
rejection, one schema-invalid numeric amount, one unknown path and one metrics read.

- 16 JSON records parsed successfully, with timezone-aware UTC timestamps.
- Five HTTP access events; `/metrics` excluded as designed.
- Exactly one accepted/rejected/invalid outcome in both logs and metrics.
- Rejection code `AMOUNT_NOT_POSITIVE`; malformed-input code `INVALID_REQUEST`.
- Synthetic identifier/header/query/path markers were absent from logs and metrics.
- Each validation outcome/completion and unknown-path completion fell within its
  sequential recorded request window **without clock tolerance**. No correlation ID,
  concurrency-tracing, load-performance or SLO claim.
- Container stopped gracefully, exit 0/no OOM, and was removed after export.

[JSON log](step-05-live/application.jsonl), [request windows](step-05-live/request-windows.json),
[timestamp links](step-05-live/timestamp-links.json), [runtime](step-05-live/runtime.json),
[verification](step-05-live/verification.json), [cleanup](step-05-live/cleanup.json),
[manifest](step-05-live/SHA256SUMS).

## Native notification interruption checks

Both owned manual probes used the actual cleanup block and its unchanged 180-second
notification timeout, inserting only a controlled 240-second wait **before** `mail`.

| Probe | Actual result | Whole-build duration | SMTP entered? |
| --- | --- | --- | --- |
| Notification timeout | ABORTED | 181.199 seconds | No |
| Operator abort during notification wait | ABORTED | 2.189 seconds | No |

This verifies that interruptions propagate through `catchError(catchInterruptions:false)`
instead of becoming UNSTABLE or SUCCESS. It is **not** a blocked-SMTP-socket experiment
or proof of JavaMail resource cancellation under a network stall. Inbox stayed at four.

The abort POST was accepted by Jenkins, but the observer rejected its HTTP redirect
and exited with a diagnostic. Credentials were not forwarded and redirect protection
was not weakened. A separate read-only inspection of the **same existing build** then
confirmed ABORTED, the operator-abort console marker, no SMTP entry and disabled job.
No retry/retrigger occurred. The original observer failure is retained alongside the
verified outcome.

[Results](step-05-interruptions/results.json),
[timeout console](step-05-interruptions/timeout-console.txt),
[abort console](step-05-interruptions/operator_abort-console.txt),
[original observer diagnostic](step-05-interruptions/observer.txt),
[manifest](step-05-interruptions/SHA256SUMS).

Earlier native delivery, disabled, encoding-error and failure-preservation cases are
in the [local delivery evidence](step-05-local-delivery.md). The approved same-pins
controller rebuild and inherited opt-in are in the [bridge evidence](step-05-environment-bridge.md).

## Cleanup, warnings and limits

All eight owned review/probe jobs are disabled. Queue empty, agent online/idle, normal
main still #25. Jenkins controller/agent/builder and Mailpit remain running; other
monitoring/application services remain stopped. Mailpit holds four messages; all
receipts used as evidence are exported. Browser/profile removed. The owned agent bundle
and redundant workspace image archive were hash-checked before deletion; Jenkins/host
archives, shared caches, diagnostic databases, volumes and history remain intact.
Old controller image and private volume-local rollback configuration remain retained
through review. No credentials, secret contents or private backup were exported.

[Final state](step-05-completion/verification.json) / [manifest](step-05-completion/SHA256SUMS).

Trivy's third-party-SBOM warnings and native browser diagnostics remain visible. The
application retains one INFO `UNCLASSIFIED_MESSAGE` for an unmapped server startup
message rather than exporting its free-form text; see the logging privacy contract.
No unexpected application warning/error appeared in the captured JSON stream.

Local SMTP is not Gmail/internet delivery or instructor acceptance. The live profile-off
restart remains unperformed; the false default is encoded and regression-tested. Cloud
collection, retention, provider queries and actual `kubectl logs` remain pending. No
source push, registry publication, cloud deployment or additional controller restart
occurred during this verification. Subsequent documentation commits do not change the
identity of the candidate that was built and run.
