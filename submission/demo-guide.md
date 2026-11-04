# Silent demonstration walkthrough

Local file: `submission/demo-walkthrough.mp4` — **12 minutes 35 seconds**,
1920×1080 H.264 MP4, 21 scenes, no audio track. Captions are burned in;
`demo-captions.srt` is also supplied. The video is excluded from Git and must be
uploaded separately after review.

This is a timed evidence walkthrough using actual UI captures, native reports and
observed API responses, **not a continuous live replay**. Do not describe it as one.
Silent-format acceptance remains unconfirmed. The student must review the whole video,
confirm the submission format and be able to explain the implementation.

No additional outage, vulnerable deployment or rollback was performed for the recording.
No new cloud monitoring resources were provisioned. The initial delivery failures and
explicit, nonautomatic rollback remain visible.

## Timeline

| Time | Scene | Caption / interpretation |
| --- | --- | --- |
| 00:00–00:25 | Purpose and scope | Actual recorded results and UI captures. This is a silent evidence walkthrough, not a fresh live replay. Pause as needed. |
| 00:25–01:05 | Strict transaction-validation contract | No money moves. Five strings are required; Decimal money and pure business rules are tested independently from HTTP handling. |
| 01:05–01:45 | Actual public HTTP responses | Synthetic requests only: health, valid payment validation, business rejection and malformed numeric amount. Public HTTP is unencrypted. |
| 01:45–02:20 | Automatic main-to-cloud delivery | Representative normal SCM #39 passed 1,349 tests and all gates. Native upstream triggering started delivery #3 without a manual release button. |
| 02:20–02:50 | Actual Jenkins source provenance | Retained Jenkins #39 console: Started by an SCM change. This is a real browser capture, not a recreated console. |
| 02:50–03:20 | Actual CI result and downstream trigger | The clean main run completed successfully. Test and scan reports remain native Jenkins artifacts; release authority is separate from source execution. |
| 03:20–03:50 | Actual downstream cause | Delivery #3 records the native upstream cause from finsecure-ci #39. Selection and independent verification precede scoped release credentials. |
| 03:50–04:40 | Actual successful delivery | The exact gated image was published, read back and deployed. Two ready owned Pods and four smoke checks passed; delivery finished SUCCESS in 104.780 seconds. |
| 04:40–05:20 | Actual failed-test release block | Isolated native Replay #37: one deliberate assertion failed; 1,348 tests passed. No package/image artifacts and no new delivery run followed. |
| 05:20–06:00 | Actual security release block | Isolated native Replay #38 found 38 HIGH and 2 CRITICAL findings in a pinned Debian base. The image was withheld, never published or deployed. |
| 06:00–06:30 | Actual blocked image-security artifact | Selected fields from Jenkins #38's native artifact. The scan completed; 38 HIGH + 2 CRITICAL findings blocked release. Other severities remain visible. |
| 06:30–07:05 | Cloud runtime and Pod recovery | Two GKE nodes and two replicas. Earlier approved Pod deletion recovered in 16.1373 seconds with 21/21 healthy samples; this is not an SLA or node-failure test. |
| 07:05–07:50 | Retained failures and controlled recovery | Delivery #2 failed public smoke after mutation and remains FAILURE. Inspection preceded explicit rollback; a fresh revision later completed normal delivery #3. |
| 07:50–08:20 | Actual rollback verification | Selected native operator-record fields: one conditional PATCH restored known-good 0.3.0 and the approved spec. This was not automatic rollback. |
| 08:20–09:05 | Actual Grafana cloud-API observations | Existing local Grafana/Prometheus observe the GKE public API. Load-balancer samples are not complete per-Pod metrics or reliable aggregate throughput. |
| 09:05–09:40 | Actual cloud-scoped FIRING notification | A deliberate scrape-port failure—not an API outage—produced this real Mailpit message. Initial rule mismatch was retained and corrected. |
| 09:40–10:05 | Actual RESOLVED notification | Port 80 was restored, scraping recovered and Mailpit received RESOLVED. API health samples stayed successful. This proves local SMTP, not external email. |
| 10:05–10:45 | Actual native resources and centralized logs | Separate observations: native GKE node/Pod CPU-memory and allowlisted Cloud Logging events. Private resource labels are omitted; no new monitoring volumes were created. |
| 10:45–11:20 | Trust boundaries and current architecture | Source and release execution are isolated. Fixed reviewed tools verify immutable input; conditional mutation and original-candidate checks limit release authority. |
| 11:20–12:00 | AI advisory triage proposal | A proposal only: sanitized evidence, cited summaries and human review. No model, autonomous remediation or measured AI benefit is claimed. |
| 12:00–12:35 | Evidence, limitations and evaluator access | Review the linked evidence and public synthetic API. Silent-format acceptance and final submission remain the student's responsibility; preserve access through 18 November. |

[Actual lessons, future decisions and post-assessment teardown checklist](../docs/runbooks/assessment-closeout.md).

## Submission checks

- Play the complete MP4 at full resolution; pause on evidence as needed.
- Confirm whether silent/captioned format is accepted; add your own narration or live
  recording if required. Do not claim acceptance has already been confirmed.
- Upload the video separately with the ten-slide presentation and four-page design PDF.
- Use the public repository and synthetic API links, not loopback Jenkins/Grafana URLs,
  as remote evaluator entry points. Never share credentials or raw cloud exports.
- Keep agreed demo access available through 18 November; review cleanup separately
  on 19 November. Manually check remaining trial credit.
