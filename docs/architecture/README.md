# Architecture and design-document traceability

The [current verified flow](presentation-flow.svg) and updated
[four-page design document](../../submission/design-document.pdf) cover the real GKE
application, automatic delivery and cloud observations. The [presentation](../../submission/presentation.pdf)
is a separate ten-slide walkthrough.

| Component | Implementation / actual evidence |
| --- | --- |
| API, schemas and pure rules | `src/finsecure_pay/`; [contract](../api-contract.md) |
| Normal main CI, tests and gates | `Jenkinsfile`; [actual #39 → delivery #3](../../evidence/task-04/step-03-live-delivery.md) |
| Rootless builder, no host Docker socket | `ops/jenkins/compose.yaml`; [builder runbook](../runbooks/local-image-builder.md) |
| Fixed release authority and isolation | `release_definition.py`, `release-delivery-flow.groovy`, scheduling policy v2; [delivery runbook](../runbooks/cloud-delivery.md) |
| Exact artifact publication and conditional deployment | `scripts/release_*.py`; [verified manifests, runtime image and rollout](../../evidence/task-04/step-03-live-delivery/) |
| Live GKE / Pod recovery | [deployment](../../evidence/task-03/step-03-managed-deployment.md), [recovery](../../evidence/task-03/step-04-recovery.md) |
| Real test/security release blocks and rollback | [native Replay cases and controlled rollback](../../evidence/task-04/step-03-live-delivery.md) |
| Locally hosted cloud-API monitoring | `ops/monitoring/cloud.compose.yaml`; [actual dashboard and mail](../../evidence/task-06/cloud-observability.md) |
| Native GKE resources and Cloud Logging | [reviewed resource metrics and allowlisted events](../../evidence/task-06/cloud-observability/) |
| AI-assisted triage | [proposal only](ai-assisted-triage.md); no model or autonomous remediation deployed |

## Interpretation and historical material

Solid paths in the current diagram are implemented. Prometheus/Grafana/Alertmanager/Mailpit
are local; GKE metrics/logging are cloud-native. The public load-balancer scrape is not
complete per-Pod monitoring and must not be treated as reliable aggregate throughput.
The AI box is a proposal, not a runtime service.

The [older dark horizontal design](full-architecture.html) is retained as a **historical
pre-cloud planning view**. Its deferred paths are not current status. Use the current flow
and evidence links above for the final demonstration. Earlier design publication `355ae88`
and its historical limitations remain in Git history.
