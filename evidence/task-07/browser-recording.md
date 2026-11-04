# Revised demonstration — actual browser recording

**Local video:** `submission/demo-browser-recording.mp4` — **11:16 rounded**
(675.667 seconds), 1920×1080, 12 fps, silent H.264 MP4. The previous slideshow-style
`demo-walkthrough.mp4` is preserved unchanged. Both videos are Git-ignored and require
separate upload after review.

This revision records actual Chrome viewport updates using `Page.startScreencast`, with
scripted browser input, scrolling and native text selection. It is not assembled from
inserted still-image slides. Usable footage from three takes is joined at normal speed;
recorder setup, failed recorder attempts and redundant inspection time are excluded.
No application response or Jenkins console text was fabricated or replaced. Chrome's
native Pretty print checkbox formats the existing deployment JSON without changing values.

## Actual content and checks

- Eight fresh Swagger requests: health and valid validation, zero amount, same account,
  excess precision, wrong numeric type, unknown field and restored valid input.
  Their actual statuses and parsed responses were checked against the documented cases.
- Real navigation through retained Jenkins #39/#3 success, #37 test failure and #38
  security-block results, including native artifacts and test/pipeline views.
- Current Grafana queries, retained firing/resolved emails, published historical
  rollback/resource/log records, source code, architecture and the AI proposal.
- Historical operations are explicitly labelled; deployments, failures, vulnerable
  builds and outages were **not rerun** to create footage.
- Native encoding/inspection confirmed one 1920×1080 video track, 12 fps, no audio,
  29 chapters and successful decoding of a sample from every chapter.
- The edit uses 1,350 captured browser frames and 105 recorded action markers, with no
  inserted slides or slowed playback. Longest interval between retained browser-frame
  updates was about 9.3 seconds; this is a capture statistic, not a claimed UI latency.
- Native encoder compilation and final execution produced no warnings or errors.
  The copied deliverable's SHA-256 matched the encoded source.

Authentication occurred before capture, using stdin and isolated browser profiles.
Profiles were removed. Personal browser windows, credentials and private cloud identifiers
were not part of the planned recording surface. Raw operator diagnostics remain ignored.

Earlier recorder failures involved a Swagger table-header selector, text selection, and a
browser-search helper; none was an application failure. The less-readable initial JSON
view was replaced with an actual native pretty-print interaction. Earlier takes and the
first edit remain in `reports/browser-recording/`; they were not silently recast as success.

[Verification and reviewed frames](browser-recording/) ·
[chapter guide](../../submission/browser-recording-guide.md) ·
[optional subtitles](../../submission/browser-recording-captions.srt) ·
[video checksum](../../submission/browser-recording.sha256).

Full student playback review, silent-format acceptance and external upload remain pending.
This is actual browser interaction footage, **not a claim that historical CI/deployment
operations executed live during filming**. Application code was unchanged; application
unit tests were not rerun for this media-only revision.
