# Architecture and design-document traceability

[Complete horizontal architecture — dark HTML](full-architecture.html) shows delivery,
target cloud requests and observability in three horizontal lanes. It is self-contained
and includes zoom controls. Amber paths remain deferred, not provisioned infrastructure.

Step 7.1 published as `355ae88`: [four-page PDF](../../submission/design-document.pdf),
[editable HTML](../../submission/design-document.html), [diagram](end-to-end.svg).
The PDF is a design document, not the later Step 7.3 presentation.

| Diagram component / design claim | Implementation or evidence |
| --- | --- |
| HTTP boundary, schemas and pure validation | `src/finsecure_pay/api/`, `schemas/`, `services/`; [API contract](../api-contract.md) |
| Trusted main, controller and Python agent | `ops/jenkins/compose.yaml`, `jenkins.yaml`, `ci-job.groovy`; [local Jenkins](../runbooks/local-jenkins.md) |
| Locked tests, package and artifact flow | Root `Jenkinsfile`, `uv.lock`; [application CI](../runbooks/application-ci.md) |
| Rootless builder and image archive | `ops/jenkins/compose.yaml`, root `Dockerfile`; [builder](../runbooks/local-image-builder.md) |
| Source/dependency gate | `scripts/security_scan.py`; [policy](../runbooks/source-security.md) |
| Image gate and identity binding | `scripts/image_scan.py`, `scripts/image_archive.py`; [policy](../runbooks/image-security.md) |
| Exact gated application runtime | [Step 6.5 candidate evidence](../../evidence/task-06/step-05-notifications-logging.md), not a runtime claim for #27/#28 |
| Prometheus/Grafana | `ops/monitoring/compose.yaml`, `grafana.compose.yaml`, `prometheus/`, `grafana/`; [dashboard evidence](../../evidence/task-06/step-02-dashboard.md) |
| Alertmanager/Mailpit | `ops/monitoring/alerts.compose.yaml`, `alertmanager/`; [actual outage/receipt evidence](../../evidence/task-06/step-04-alert-demonstration.md) |
| Sanitized JSON stderr | `src/finsecure_pay/observability/logging.py`, `logging.json`; [logging contract](../runbooks/notifications-logging.md) |
| Jenkins SMTP | Root `Jenkinsfile`, `ops/jenkins/notifications.compose.yaml`, `notifications.yaml`; [SCM #27 receipt](../../evidence/task-06/step-05-fix-scm-verification.md) |
| Registry release versus deferred CI promotion | [Historical release](../runbooks/image-publication.md); no publishing stage in current Jenkinsfile |
| Managed Kubernetes — deferred | `deploy/kubernetes/base/`; [runtime safeguards and limits](../runbooks/runtime-safeguards.md); manifests are not a live cluster |
| Centralized cloud logs — deferred | No implementation; requires provider, access, retention and cost approval |
| AI-assisted triage — proposal only | Scope in `PLAN.md` Step 7.2; no deployed assistant or remediation service |

## Proposed AI use case

[Step 7.2 advisory incident triage](ai-assisted-triage.md) describes a possible integration,
not another deployed diagram component. It includes a synthetic example, risk controls,
evaluation criteria and decisions required before implementation.

## Reading the diagram

Solid arrows show implemented local paths, not a claim that every service is running
at once. The application, Prometheus, Grafana and Alertmanager are normally stopped
after demonstrations. The Python agent and rootless builder share one diagram box to
save space but are separate containers. The combined monitoring box means Grafana
queries Prometheus, not that Grafana scrapes the application. Dashed paths are deferred.

The SVG is readable independently and is embedded in PDF page 2. Text remains
selectable in the PDF. Rendering and page review are recorded in
[Step 7.1 evidence](../../evidence/task-07/step-01-design-document.md).
