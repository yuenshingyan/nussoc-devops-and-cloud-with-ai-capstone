# Final silent evidence walkthrough

**Local deliverable:** `submission/demo-walkthrough.mp4` — **12:35**, 1920×1080,
H.264 MP4, 21 scenes, no audio track, 7,692,217 bytes. The video is intentionally
excluded from Git; upload it separately after review. Its SHA-256 is recorded in
[verification metadata](final-video/video-verification.json) and
[submission/demo-video.sha256](../../submission/demo-video.sha256).

The [timed guide](../../submission/demo-guide.md) and
[subtitle file](../../submission/demo-captions.srt) accompany burned-in captions.
The recording is a timed **evidence walkthrough**, not a continuous live replay.
It combines actual retained Jenkins UI captures, native security/rollback records,
actual public HTTP observations, the actual dashboard and alert messages, and the
reviewed presentation. No browser console text was recreated or substituted.

## Verification actually performed

- Native AVFoundation encoding completed without compiler/runtime warnings.
- Native asset inspection confirmed 755 seconds, one 1920×1080 video track and zero audio tracks.
- Every one of the 21 scenes was decoded at its expected timestamp.
- Contact-sheet review and selected full-resolution frames checked orientation,
  captions, layout and the actual security-block artifact. This is not a claim of
  full 12:35 human playback review.
- Actual synthetic HTTP captures returned health 200, valid 200, zero-amount rejection
  200 and malformed numeric-amount 422; public OpenAPI version was 0.4.0.
- The preceding documentation publication completed automatic normal CI #42 and
  delivery #6 successfully. No demonstration fault was rerun to create the recording.

[Checksummed verification, selected frames and HTTP observations](final-video/).
Full local render/decoder records and earlier drafts remain under `reports/final-video/`.
The initial preview decoder used approximate seek; exact timestamp extraction replaced
it before final verification. No application or deployment behavior changed in this step.

## Remaining human/submission actions

The student must review the entire video, confirm whether silent format is accepted,
explain the implementation, and upload the files. None of those actions is claimed as
completed. External upload was not performed. Trial credit and continued evaluator access
still require manual oversight; cleanup remains separately reviewed for 19 November.
