# Actual GKE observability and notification evidence

The existing **local** Prometheus/Grafana/Alertmanager/Mailpit stack observed the real GKE
public API. No GKE-hosted monitoring deployment, new cloud volume or new paid service is
claimed. The reviewed profile is `ops/monitoring/cloud.compose.yaml`.

Verified observations:

- The cloud endpoint was scraped successfully; five authenticated provisioned Grafana
  queries returned numeric data. A real browser screenshot is retained, not a rendered mock.
- A bounded dashboard batch sent 60 synthetic requests: 40 HTTP 200 and 20 HTTP 422.
- Native GKE metrics returned actual CPU/memory observations for both nodes and both
  application Pods. Private resource identifiers were omitted from the published sample.
- Actual Cloud Logging validation events include accepted, rejected and invalid outcomes;
  only approved event fields and timestamps were retained, not private cloud resource labels.
- A deliberate scrape-port change to **81** caused the cloud-scoped alert and an actual
  FIRING email. Port **80** was restored, the alert became inactive and a RESOLVED email
  arrived. API health samples were successful; no application outage was induced.

The initial attempt reused a rule hard-coded to the old local application. Its mismatched
alert is retained and is **not counted as cloud alert proof**. The corrected cloud rule passed
native promtool tests for healthy targets, pending/firing and recovery, then the real
cloud-scoped notification/recovery demonstration passed.

## Limits

The dashboard samples a load-balanced endpoint. It is not a reliable aggregate across both
Pods: counters can alternate between serving processes. Native GKE resource metrics separately
cover both Pods/nodes. No throughput benchmark, SLO or production-grade per-Pod discovery is
claimed. Mailpit proves local SMTP delivery, not Gmail or another external provider.

[Checksummed records and actual screenshots](cloud-observability/) ·
[Operational profile and interpretation](../../docs/runbooks/cloud-monitoring.md).
