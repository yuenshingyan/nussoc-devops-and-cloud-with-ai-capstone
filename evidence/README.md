# Evidence index

Store only reviewed, sanitized evidence from actual execution here. Task 1 has
application, test, package-installation, and public source-access evidence.
Task 2 onward remains pending.

| Task | Directory | Status |
| --- | --- | --- |
| 1 — Application and Git | [task-01](task-01/) | Steps 1.1–1.5 verified; Step 1.5 documentation pending merge |
| 2 — Containerisation | [task-02](task-02/) | Pending |
| 3 — Kubernetes and cloud | [task-03](task-03/) | Pending |
| 4 — CI/CD | [task-04](task-04/) | Pending |
| 5 — DevSecOps | [task-05](task-05/) | Pending |
| 6 — Observability | [task-06](task-06/) | Pending |
| 7 — Documentation and demonstration | [task-07](task-07/) | Pending |

## Recorded evidence

- [Step 1.1 — Scaffold verification](task-01/step-01-scaffold.md): clean install,
  lint/format checks, scaffold tests, packaging, and real local HTTP requests.
- [Step 1.2 — Health endpoint verification](task-01/step-02-health.md): API contract
  tests, lint/format checks, packaging, and live GET/POST requests.
- [Step 1.3 — Transaction validation verification](task-01/step-03-validation.md):
  54 unit/API cases, build checks, and live accepted/rejected/malformed requests.
- [Step 1.4 — Expanded tests and reports](task-01/step-04-tests.md): 167 passing cases,
  100% measured line/branch coverage, parsed XML reports, and sanitized run artifacts.
- [Step 1.5 — Packaging and publication](task-01/step-05-source-publication.md):
  clean wheel/source-distribution installs, live HTTP checks, actual branch pushes,
  and anonymous GitHub access.

For each artifact, record the requirement demonstrated, timestamp, command or
procedure, actual result, commit, applicable image digest, and artifact path or
accessible external link. Redact secrets and personal information before adding
files. Keep large generated reports in CI artifact storage where practical.
