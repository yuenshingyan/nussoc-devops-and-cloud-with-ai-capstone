# Evidence index

Store only reviewed, sanitized evidence from actual execution here. Task 1 has
application, test, package-installation, and public source-access evidence.
Task 2 has image-build, execution, versioned registry publication, and anonymous
pull/access evidence for ARM64 and AMD64. Task 3 has locally verified configuration
and manifest candidates, not cloud-deployment evidence.

| Task | Directory | Status |
| --- | --- | --- |
| 1 — Application and Git | [task-01](task-01/) | Complete and merged |
| 2 — Containerisation | [task-02](task-02/) | Complete; reviewed and merged locally |
| 3 — Kubernetes and cloud | [task-03](task-03/) | Step 3.1 locally verified; 0.2.0 publication/digest pinning and review pending |
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
- [Step 2.1 — Container definition and build](task-02/step-01-dockerfile.md): pinned
  multi-stage build, non-root configuration, final filesystem inspection, and the
  documented Docker Desktop metadata-timeout workaround.
- [Step 2.2 — Container execution](task-02/step-02-container-validation.md): actual
  non-root PID 1, loopback HTTP checks, clean shutdown/removal, and a missing-image
  failure check.
- [Step 2.3 — Image publication](task-02/step-03-image-publication.md): public Docker Hub
  version/commit tags, ARM64/AMD64 manifests, smoke tests before and after registry
  pulls, and anonymous digest/provenance verification.
- [Step 3.1 — Configurable policy and Kubernetes manifests](task-03/step-01-manifests.md):
  210 passing tests, local Kustomize checks, and ARM64 0.2.0 container checks with
  default/custom/invalid settings. No image publication or cluster execution yet.

For each artifact, record the requirement demonstrated, timestamp, command or
procedure, actual result, commit, applicable image digest, and artifact path or
accessible external link. Redact secrets and personal information before adding
files. Keep large generated reports in CI artifact storage where practical.
