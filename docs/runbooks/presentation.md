# Final presentation and recording materials

- [Presentation PDF](../../submission/presentation.pdf): **10 landscape slides**.
- [Editable presentation](../../submission/presentation.html).
- [Design PDF](../../submission/design-document.pdf): **4 A4 pages**.
- [Current architecture](../architecture/presentation-flow.svg).

Both documents now describe actual GKE delivery and observations rather than the earlier
pre-cloud plan. Chrome rendered the PDFs in an isolated profile; DOM overflow checks and
native PDF page-count checks passed. Initial design-page overflow was corrected before the
final render. Existing divergent presentation-branch work was preserved; this update uses
`task-07/step-03-presentation-final` from reviewed main.

## Ten-slide sequence

1. Purpose, synthetic-only boundary and verified capabilities.
2. Strict API contract and Python-stack alternatives.
3. Real GKE deployment, safeguards and historical Pod recovery.
4. Automatic normal SCM #39 → delivery #3.
5. Real failed-test #37 and security-block #38 demonstrations.
6. Retained delivery failures, explicit rollback and fresh successful release.
7. Actual cloud-API monitoring, native resources, logs and notification limits.
8. Current source-to-runtime architecture and trust boundaries.
9. AI advisory triage proposal; no deployed model or measured benefit.
10. Acceptance evidence, limitations and evaluator access.

The Jenkins UI captures are actual retained runs, not a fresh replay. Do not create another
outage, failing build, vulnerable artifact or rollback merely for recording. Public API
requests must use synthetic data only. Never open credentials, raw cloud exports, kubeconfigs
or personal Google-account pages in the recording.

Silent-format acceptance remains unconfirmed. Review the final recording and the assignment
requirements before submission; do not claim that a generated walkthrough is a live replay.
