# Design document — local rendering and review

The Step 7.1 deliverable is [submission/design-document.pdf](../../submission/design-document.pdf)
with editable [HTML](../../submission/design-document.html) and a standalone
[SVG architecture diagram](../architecture/end-to-end.svg). It is four A4 pages,
not the Step 7.3 slide deck. [Traceability](../architecture/README.md) maps the diagram
to implementation and evidence; dashed paths are deferred work.

## Reproduce on the verified macOS host

Use the existing system Chrome, Python 3 and Swift/PDFKit. No Python dependency,
browser extension or cloud service is added. Run from the repository root:

```sh
mkdir -p reports/step71
python3 evidence/task-07/step-01/render.py.txt
cp evidence/task-07/step-01/inspect.swift.txt reports/step71/inspect.swift
swift reports/step71/inspect.swift
```

Rendering uses a temporary isolated Chrome profile, local files, disabled background
services and a 60-second subprocess limit. The profile is removed on completion.
PDFKit checks exactly four pages and writes per-page PNG/text to ignored reports.
Chrome and PDFKit are host tools, not CI application dependencies; other platforms
need a separately verified renderer. No cross-renderer byte-identity claim is made.

Review every rendered page for clipping, readable labels, complete footers and the
implemented/deferred distinction. Confirm the PDF's architecture matches the SVG and
verify paths in the traceability table. Preserve failures rather than presenting an
unreviewed render as final. The first draft rendered six pages; layout was corrected.
Native Chrome diagnostics are retained in evidence, not silently discarded.

Before submission, refresh baseline commit/build references if implementation changes.
Do not relabel an earlier image demonstration as evidence for a later build. Do not
claim managed-cloud deployment, log collection or an AI service merely because a
proposal appears in this document.
