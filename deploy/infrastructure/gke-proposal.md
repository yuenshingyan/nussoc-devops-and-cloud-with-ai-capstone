# GKE resource proposal — approval required before creation

This is a proposed resource inventory, **not applied infrastructure**. On 3 November
2026 the dedicated project was created, linked to the sole visible open billing
account and selected locally. Four APIs were enabled with permission. No cluster,
VM, load balancer or published application release has been created by this preparation.

## Verified inputs

- Billing API currency: **SGD**. User-reported unused credit: **S$385**, expiry
  2 February 2027, account state Free Trial. Only currency/open state were independently
  read from the API; credit balance, expiry and trial status remain user-confirmed.
- Singapore remaining quota: total regional CPUs 100, E2 CPUs 24, global CPUs 12.
  Six CPUs cover the proposed four-CPU baseline plus one two-CPU upgrade node.
- Regional disk quota: 2,048 GB unused; in-use IP quota: eight unused; static-address
  quota: eight unused. These are snapshots, not capacity reservations or a complete
  assertion that every service-specific quota will allow deployment.
- GKE server configuration lists Regular-channel default `1.36.4-gke.2046003` in
  `asia-southeast1-a`. Recheck supported version/capacity immediately before creation.
- Google Cloud CLI 591.0.0 supports DNS access with IP control-plane access disabled.

## Proposed resources and access

| Resource | Proposed setting |
| --- | --- |
| Cluster | `finsecure-pay-demo`, zonal Standard in `asia-southeast1-a`; node locations restricted to that one zone |
| Nodes | Exactly two `e2-standard-2` nodes, COS_CONTAINERD; no Spot, autoscaling or node auto-provisioning |
| Node boot disks | 30 GB `pd-standard` per node (60 GB total; up to 90 GB during one-node upgrade surge), rather than implicit 100 GB balanced disks |
| Upgrade policy | Regular channel; auto-repair/auto-upgrade; maximum surge one, maximum unavailable zero; not blue/green upgrades or extra node pools |
| Network | Dedicated custom-mode VPC `finsecure-pay-demo`; regional subnet `finsecure-pay-singapore`, nodes `10.40.0.0/24`, Pods `10.44.0.0/20`, Services `10.48.0.0/24`; verify no overlap before creation |
| Node connectivity | Public node addresses for outbound image downloads without a Cloud NAT gateway; **no general public SSH/RDP firewall rules**. Public node IPs are a demo cost trade-off, not private-node production hardening |
| Control plane | DNS-based endpoint, IAM-authenticated; disable public/private IP endpoint access. Do not silently fall back to an unrestricted IP endpoint |
| Node identity | Dedicated keyless service account with `roles/container.defaultNodeServiceAccount`; no Editor role. Enable Workload Identity Federation for GKE; application Pod token automount remains disabled |
| Kubernetes client | Operator's local SDK credentials and GKE auth plugin; no service-account key export and no mounting operator credentials into Jenkins |
| Application | Two replicas, existing health/readiness/security/resource settings; newly gated AMD64 image pinned by digest. Existing historical image pin is not the proposed release |
| External access | One IPv4 external passthrough LoadBalancer, **HTTP port 80 only**, for synthetic demo requests; no domain or certificate purchase. Public `/metrics` exposes bounded synthetic operational counters, not a confidential endpoint |
| Admin interfaces | Prometheus, Grafana and Alertmanager remain ClusterIP; authenticated operator port-forward access. No public Jenkins/Grafana/Prometheus endpoints |
| Metrics | Existing self-hosted Prometheus/Grafana; Google system metrics only. Disable Managed Service for Prometheus and automatic workload monitoring to avoid unplanned ingestion |
| Logs | Google system/workload logs; retain safe application JSON without raw requests. Standard default logging retention/allowances are not a spend cap; review volumes and export sanitized evidence |
| Monitoring storage | Plan two 5 GiB standard-disk PVCs, one each for Prometheus/Grafana. Confirm storage class/reclaim policy before applying monitoring workloads; no automatic claim expansion |

HTTP is deliberately **not** production financial security. No real customer,
payment-card, credential or transaction data may be sent. If TLS is required, agree
a different ingress/certificate plan before exposure; do not use an unapproved DNS
service, certificate workaround or domain purchase. Network and IAM details above
require explicit approval before resources or grants are created.

The monitoring rows describe later deferred monitoring work; they are included for
whole-window costing, not implemented in this checkpoint. Cloud CI deployment identity,
RBAC and rollback remain separate deferred contracts. Manual cluster setup will not
prove automatic SCM-to-cloud deployment or a deployment-blocking security gate.

## Budget and availability

- Target window: 3–19 November (384 hours); availability through grading on 18 November.
- Use **S$225 as a provisional planning envelope**, not an enforced cap or price quote.
  It includes two nodes, 60 GB boot disks, up to 10 GiB monitoring disks, one load
  balancer, node public IPs, modest traffic/logs, and contingency for a management fee
  if the eligible zonal-cluster credit is unavailable or already consumed elsewhere.
- Previous compute estimate was about US$0.0827/node-hour, **not a newly verified
  account-currency tariff**. The authenticated Compute SKU catalog request was denied;
  do not label that estimate as a live Google quote or infer an exchange rate from
  the trial-credit amount. Verify the Console's current estimate before creation.
- Google documents a US$74.40 monthly management credit for an eligible zonal Standard
  cluster; this does not cover worker nodes, disks or networking. Do not assume other
  projects have left the entire allowance unused.
- Budget alerts, if later configured, do not stop spending. No paid-account upgrade
  is authorized. Free Trial exhaustion may shut workloads down and break evaluator
  access; do not upgrade to preserve availability without revisiting the user's hard
  no-out-of-pocket constraint.
- Review account status/remaining credit before creation and daily during retention.
  This is an operator checklist, not implemented scheduled automation.
- On 19 November, review grading status, export evidence and delete approved project
  resources only after teardown confirmation. Account for PVC disks, addresses and
  load-balancer resources; project creation is not an automatic deletion schedule.

## Release preparation

Proposed version **0.3.0** includes the already implemented metrics/logging and hardened
runtime. Package version, lockfile's local-project version, OpenAPI metadata and Docker
label are updated together; dependency pins and transaction request/response schemas
are unchanged. Publication is not authorized by preparing a candidate.

Build from a committed source archive; record the source revision and tested image ID.
First verify Linux AMD64 under local emulation, then run the unchanged source/image
security gates on that exact candidate. Do not claim emulated testing proves actual
GKE-node behavior. Publish only after review, without replacing historical 0.1.0/0.2.0
images. Update Kubernetes version labels and image digest only after publication and
anonymous pull verification. Preserve unsuccessful attempts and stop on gate failures.

The first local AMD64 candidate (`33d4770`) built and passed the container smoke test.
The image gate rejected its architecture during input validation: the current validator
explicitly accepts only ARM64. No vulnerability scan ran. Supporting an explicitly
selected AMD64 target needs approval, tests, and a new gated candidate; accepting any
architecture automatically is not proposed. The failed attempt is retained as evidence.

Host storage was 4.2 GiB free before preparation, while the Docker backing filesystem
had about 10.5 GiB free. They are separate constraints. Check both before builds/scans;
do not prune shared caches or retained diagnostic databases to make room without approval.

## Official references

- [Trial charging and expiry](https://cloud.google.com/signup-faqs)
- [GKE pricing and management allowance](https://cloud.google.com/kubernetes-engine/pricing)
- [Network isolation / DNS endpoint](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/latest/network-isolation)
- [Node service accounts](https://docs.cloud.google.com/kubernetes-engine/security/configure-node-service-accounts)
- [VPC pricing](https://cloud.google.com/vpc/network-pricing)
- [Observability pricing](https://cloud.google.com/products/observability/pricing)
