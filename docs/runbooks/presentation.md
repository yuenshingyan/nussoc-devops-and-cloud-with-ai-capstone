# Presentation — PDF and evidence audit

The user's selected format is PDF. [submission/presentation.pdf](../../submission/presentation.pdf)
contains **10 landscape slides**, with editable [HTML](../../submission/presentation.html).
It is separate from the four-page design document. The deck is ready for review,
not a claim that deferred cloud requirements or the Step 7.4 rehearsal are complete.

## Coverage of all seven tasks

| Task | Slides | Evidence and qualification |
| --- | --- | --- |
| 1 — Application/Git | 1–2 | Strict API contract, pure validation, reviewed branches; [tests](../../evidence/task-01/step-04-tests.md) |
| 2 — Containers | 3 | Historical public multi-platform images; [0.2.0 publication](../../evidence/task-03/step-01-image-publication.md) |
| 3 — Kubernetes/cloud | 3, 9 | [Manifests](../../evidence/task-03/step-01-manifests.md) and safeguards only; no running managed cluster |
| 4 — CI/CD | 4–5, 9 | [SCM #27](../../evidence/task-06/step-05-fix-scm-verification.md), [real failing test](../../evidence/task-04/step-04-trigger-gate.md); no CI registry/deployment stage |
| 5 — Security | 5, 9 | [Blocked vulnerable image](../../evidence/task-05/step-04-security-demonstration.md); no vulnerable artifact executed; full cloud credential controls deferred |
| 6 — Observability | 6–7, 9 | Real dashboard, [alert receipts](../../evidence/task-06/step-04-alert-demonstration.md), [exact-image logs](../../evidence/task-06/step-05-notifications-logging.md); local scope only |
| 7 — Design/AI/lessons | 7–8, 10 | Design PDF, architecture, AI proposal and actual lessons; timed demonstration remains Step 7.4 |

## Core test-case audit

| Assignment case | Current disposition |
| --- | --- |
| Run unit tests | Verified as part of 655 passing unit/integration/configuration tests in normal CI |
| Controlled failing test; deployment does not proceed | Partial: actual pytest failure prevented packaging/image export. Deployment itself is not configured |
| Container /health returns healthy | Verified on historical releases and exact gated local demonstration images |
| At least two application pods running and Ready | Missing: manifests are not managed-cluster execution evidence |
| New version rollout completes | Missing: no live Kubernetes rollout |
| Delete/restart pod; Kubernetes recreates it | Missing: local container recovery is not a pod self-healing test |
| HIGH/CRITICAL finding blocks release | Partial: actual image-archival gate blocked the artifact; no registry/deployment path to verify |
| Monitoring condition fires and notifies | Verified locally with actual firing/resolved Mailpit receipts; not internet delivery |

These gaps are visible on slide 9. Do not mark them complete because they appear in a
presentation, substitute a local restart for Kubernetes behavior, or manufacture
cluster screenshots. Provider/access/budget and disruptive operations require approval.

## Sources, image handling and links

Slide 4 displays a **message-panel crop** of the actual published #27 Mailpit screenshot;
no pixel text was substituted. Its raw message, full screenshot and build reports are
linked. Slide 6 uses the actual Step 6.2 Grafana screenshot, including its original
values; it is not a benchmark. Its JSON-log excerpt copies selected fields from the
candidate `1a1f4a3` record, not from the later CI image. Slide 7's simplified SVG groups
separate services for readability; see the detailed architecture for full boundaries.

Most links pin published source `1b4b4df` so evidence does not silently change under the
deck. All 13 distinct external URLs returned HTTP 200 without authentication during
review. This establishes current reachability, not permanent access or successful
cloud operation. Local Jenkins/Grafana/Mailpit endpoints are not evaluator links.
Raw CI reports remain in Jenkins/ignored local reports; curated public evidence is the
evaluator entry point. Baseline #30 observation is retained with this step's evidence.

## Reproduce the PDF on the verified host

Use the already installed system Chrome, Python 3 and Swift/PDFKit, from repository root:

```sh
mkdir -p reports/step73
python3 evidence/task-07/step-03/render.py.txt
cp evidence/task-07/step-03/inspect.swift.txt reports/step73/inspect.swift
swift reports/step73/inspect.swift
```

Chrome renders only local HTML/assets with an isolated temporary profile and a bounded
60-second subprocess. The profile is removed afterwards. PDFKit asserts ten pages and
exports page PNG/text for visual inspection. Review all ten pages; page count alone
does not detect clipping. The first message crop caused grid overflow; the layout was
corrected and the affected slide re-rendered and inspected. Native Chrome diagnostics
remain in evidence. No new dependency or service was installed.

Before final submission, review the PDF and the remaining gaps with the user. Do not
upload automatically. Rehearsal, timing, final evaluator access arrangements and any
cloud completion belong to separately approved work.
