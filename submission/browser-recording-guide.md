# Revised browser recording

**Watch `submission/demo-browser-recording.mp4`** — about **11:16**, 1920×1080,
12 fps, silent H.264 MP4, with burned-in captions. An optional SRT is supplied.
The previous `demo-walkthrough.mp4` is preserved unchanged.

This revision uses actual Chrome screencast footage and scripted browser interactions,
not inserted screenshot slides. It includes fresh Swagger requests, native Jenkins
navigation, artifact inspection, current Grafana queries and retained alert messages.
Historical runs, rollback records and cloud-log observations are explicitly labelled.
No deployment, vulnerable-image build, failing test or outage was rerun for filming.

Authentication and recorder setup are off camera. The edit joins usable sections of
three takes at normal speed; failed recorder attempts and the less-readable first cut
remain in ignored operator reports. Native browser pretty-printing makes the actual
deployment JSON readable without changing its values.

## Chapters

| Time | Content |
| --- | --- |
| 00:00–00:16 | Live browser • public API documentation |
| 00:16–00:38 | Live API • health check |
| 00:38–01:05 | Live API • valid synthetic transaction |
| 01:05–01:25 | Live API • Zero amount |
| 01:25–01:45 | Live API • Same sender and recipient |
| 01:45–02:06 | Live API • Excess fractional precision |
| 02:06–02:26 | Live API • Wrong input type |
| 02:26–02:46 | Live API • Unknown request field |
| 02:46–03:06 | Live API • Restore a valid request |
| 03:06–03:35 | Reviewed source • exact API contract |
| 03:35–03:56 | Reviewed source • pure business rules |
| 03:56–04:22 | Reviewed source • container build and runtime |
| 04:22–04:50 | Reviewed source • CI gate ordering |
| 04:50–05:17 | Historical Jenkins #39 • successful normal SCM run |
| 05:17–05:42 | Historical Jenkins #39 • pipeline steps |
| 05:42–06:07 | Historical Jenkins #39 • console and downstream trigger |
| 06:07–06:37 | Historical delivery #3 • independent release worker |
| 06:37–06:57 | Historical delivery #3 • actual deployed-image proof |
| 06:57–07:21 | Historical failure #37 • real failed-test block |
| 07:21–07:54 | Historical failure #38 • image-security gate |
| 07:54–08:23 | Historical operator rollback • verified result |
| 08:23–08:50 | Live Grafana • cloud API observations |
| 08:50–09:10 | Historical alert • actual FIRING email |
| 09:10–09:28 | Historical alert • actual RESOLVED email |
| 09:28–09:52 | Historical cloud observations • native resource metrics |
| 09:52–10:13 | Historical Cloud Logging • sanitized event evidence |
| 10:13–10:34 | Architecture • current trust boundaries |
| 10:34–10:58 | AI triage • proposal only |
| 10:58–11:15 | Finish • evidence and access |

## Review and submission

- Watch the full new video for pacing and readability; chapter-frame inspection is not
  a substitute for your full review.
- Confirm silent/captioned format is accepted and be ready to explain the implementation.
- Upload the MP4 separately: it is intentionally Git-ignored. No upload was performed.
- The existing 10-slide presentation and four-page design PDF remain available.
- Continue manual credit/access oversight; see the [closeout checklist](../docs/runbooks/assessment-closeout.md).
