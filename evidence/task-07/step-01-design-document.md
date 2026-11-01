# Step 7.1 — Design document and architecture

Status: local documentation complete; review/merge/publication pending.
Branch `task-07/step-01-design-document` starts at published `040ac4c`.

- [Four-page PDF](../../submission/design-document.pdf) is under `submission/` with
  editable HTML; [SVG diagram](../../docs/architecture/end-to-end.svg) and
  [component traceability](../../docs/architecture/README.md) are under `docs/architecture/`.
- Covers the API contract, stack alternatives, source-to-artifact/deferred-deployment
  flow, isolation, security gates, metrics/logs/alerts, recovery, rollback limits and
  an explicitly proposed AI use case. Step 7.2's detailed AI design is not implemented.
- Actual PDFKit page count is **4**. All pages were visually reviewed; first-render
  six-page overflow and initial diagram label crowding were corrected. The final
  PDF retains selectable text and the embedded diagram.
- Publication follow-up #28 verification and its raw notification are retained here
  as baseline evidence. They are not a build of this new documentation branch.
- No application, dependency, CI, service lifecycle, credential or infrastructure
  change. No new tests are required for this documentation-only step. Existing host
  checks are recorded separately when executed; no new native CI build was triggered.
- Rendering used installed Chrome and Swift/PDFKit, without adding packages. Native
  browser diagnostics remain in the retained log. No cloud resources or external
  publishing were used.

See [rendering instructions](../../docs/runbooks/design-document.md),
[verification record](step-01/verification.json) and [manifest](step-01/SHA256SUMS).
Source commit and runtime-image provenance in older evidence remain unchanged.
