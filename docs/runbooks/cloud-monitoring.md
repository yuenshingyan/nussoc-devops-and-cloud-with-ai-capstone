# GKE monitoring demonstration without new cloud resources

Prometheus, Grafana, Alertmanager and Mailpit run in the **existing local Docker stack**.
Prometheus scrapes the public GKE API at `35.198.197.186:80`. Native GKE metrics provide
CPU/memory observations for both nodes and both application Pods; Cloud Logging contains
actual structured validation outcomes. No cloud monitoring PVCs or new collectors were created.

## Start the reviewed cloud-target profile

The existing Grafana secret volume and Mailpit service must already exist. Do not recreate
Mailpit during recording: its current inbox contains the demonstrated notifications.

```sh
docker compose -f ops/monitoring/compose.yaml \
  -f ops/monitoring/grafana.compose.yaml -f ops/monitoring/alerts.compose.yaml \
  -f ops/monitoring/cloud.compose.yaml config --quiet

docker compose -f ops/monitoring/compose.yaml \
  -f ops/monitoring/grafana.compose.yaml -f ops/monitoring/alerts.compose.yaml \
  -f ops/monitoring/cloud.compose.yaml up -d --no-deps --no-build --pull never \
  prometheus grafana alertmanager
```

- Grafana: `http://127.0.0.1:3000/d/finsecure-pay-local/local-metrics`.
- Prometheus targets: `http://127.0.0.1:9090/targets`.
- Mailpit: `http://127.0.0.1:8025/`.
- Preserve the existing password; never put it into commands, slides or recordings.

The cloud overlay disables automatic startup of the old local application. It reuses the
existing 24-hour/256 MB Prometheus retention and existing local persistence volumes.

## Observed alert and recovery

An operator temporarily pointed the scrape at port **81**, leaving the application and port
80 unchanged. The cloud-scoped rule fired and Alertmanager delivered actual FIRING and
RESOLVED messages to Mailpit. The target was restored to port 80; scrape health and alert
recovery were verified. API health checks passed at observation points. This demonstrates
**monitoring-path failure**, not an application outage or payment failure.

The first attempt exposed a hard-coded local target in the original rule. It was cancelled,
the original target restored, and the cloud-specific rule corrected. That failed attempt is
retained. Native promtool cases now cover healthy cloud targets, pending/firing and recovery.
Do not replay the disruption merely to open the existing evidence.

## Interpretation limits

A public load-balancer scrape is **not complete per-Pod monitoring**. Counter samples can
come from different serving Pods; do not interpret the dashboard as reliable aggregate
throughput, an SLO or a load benchmark. Native GKE metrics independently cover both nodes
and Pods. Per-Pod scrape discovery would be needed for production-quality aggregation.
Mailpit proves local SMTP receipt, not external email. The proposed GKE-hosted monitoring
volumes remain unimplemented and conditional on confirmed trial credit.

[Actual evidence and screenshots](../../evidence/task-06/cloud-observability.md).
