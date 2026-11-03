# Step 3.3 — managed GKE deployment verified

Date: **3 November 2026**. The user explicitly approved the fixed Singapore profile,
public HTTP for synthetic data, private admin interfaces, provisional S$225 planning
envelope and **no paid upgrade**. This is actual deployment evidence, not a scaffold.

**Live health:** http://35.198.197.186/health  
**API docs:** http://35.198.197.186/docs

HTTP is unencrypted. Never send customer/card data or credentials. The API validates
synthetic transactions; it does not transfer money. Running resources consume trial
credit. Trial state/remaining credit are user-confirmed, not independently API-certified.

## Reproducible implementation and checks

Creation/overlay commit: `2b2afee5ac6ce4572f7832d7b6adcca81a266738` (local pending review).

- `deploy/infrastructure/create-gke.sh`: one-time creation with explicit project/approval
  guards, fixed region/node count/disks, keyless node identity and asynchronous cluster
  creation. No paid upgrade, service-account key export, deletion or script retry.
- `deploy/kubernetes/overlays/gke/`: reuses the demo/base resources, pins the published
  0.3.0 digest, selects AMD64 and exposes only the application's TCP/80 IPv4 Service.
  Base/demo historical pins remain unchanged.
- Shell syntax and local rendered-resource checks passed. The final host suite passed
  **781 tests**, plus Ruff lint/format and packaging. Source gates passed with 31 LOW
  Bandit findings retained, zero MEDIUM/HIGH and 15 runtime dependencies audited without
  blocking findings. No dependency pins or application behavior changed in this step.
- The initial suite had one failing approval-guard test (777 passed). Bash 3.2 did not
  apply `errexit` to the compound conditional as assumed. Explicit conditional exits
  fixed it; approval/project rejection and partial SDK failure tests now pass. All SDK
  calls in these tests were fake executables; no cloud resources were created by tests.
- Published source/automatic #32 predates these files and tested 770 cases, not 781.
  No new automatic SCM build is claimed for this local infrastructure checkpoint.

## Supporting setup and price evidence

The SDK's GKE auth plugin 0.5.20 was installed at SDK 591.0.0; it refreshed the SDK's
own virtual environment, not project dependencies. IAM API was already enabled.
Cloud Resource Manager and Cloud Billing APIs were enabled for the approved node-role
grant and tariff verification. These were additional to the four earlier approved APIs.
No billing-account upgrade, key creation or extra compute service was requested.

The earlier catalog denial was retained. With the required billing API enabled and
an explicit quota project, seven pages of the Google Compute SKU catalog were read:

- E2 core: **S$0.034517917 / core-hour**.
- E2 RAM: **S$0.004625519 / GiB-hour**.
- Standard disk: **S$0.056441 / GiB-month**.
- Two 2-vCPU / 8-GiB nodes for 384 hours: approximately **S$81.44 compute**.
- 60 GiB boot disks for the same interval: approximately **S$1.78** using a 730-hour month.

These are verified component tariffs, not a complete invoice estimate. Load balancing,
public IPs, possible management fees, traffic/logs, monitoring storage, taxes and
contingency are additional. S$225 remains a planning envelope, **not a spending cap**.
No exchange rate was inferred from the trial-credit amount. Credit monitoring is manual.

## Actual cluster and resource verification

The creation script completed successfully, then its single CREATE_CLUSTER operation
was observed read-only until DONE; the cluster reached RUNNING. No repeated create
request, automatic resource cleanup or paid upgrade was used.

- Cluster `finsecure-pay-demo`, **zonal Standard**, `asia-southeast1-a` only.
- Regular channel, observed version `1.36.4-gke.2046003`; standard edition, no fleet.
- One pool, exactly **two e2-standard-2** nodes; auto-repair/upgrade enabled, maximum
  surge one and unavailable zero. Autoscaling and node auto-provisioning disabled.
- Actual census: two Running VMs, two **30 GB pd-standard** boot disks, one external
  TCP/80 forwarding rule. No Cloud Router/NAT or monitoring PVC disks were created.
- Custom VPC/subnet and non-overlapping node/Pod/Service ranges match the approved plan.
- IP-based control-plane access disabled. Operator credentials use the IAM/DNS endpoint,
  TLS verification and the SDK plugin. Kubernetes token/certificate DNS access disabled.
- Dedicated node account has only `roles/container.defaultNodeServiceAccount` among
  project bindings for that principal, with **zero user-managed keys**. Workload Identity
  and GKE metadata mode verified. No operator credentials were placed in Jenkins.
- Google monitoring components: SYSTEM only; Managed Prometheus disabled. Auto-monitoring
  scope NONE was requested; its API configuration was empty. System/workload logs enabled.
- Private raw SDK output/kubeconfig remain outside Git. Private directory 0700; kubeconfig
  0600. The user's global kubeconfig was not replaced.

## Namespace dry-run ordering and firewall observer correction

The first server-side dry run could not validate namespaced resources because its
simulated Namespace creation did not persist. Diagnostics contained only the expected
namespace-not-found errors. The operator created only the approved namespace, repeated
server validation successfully, then applied the overlay and awaited rollout readiness.
This was a diagnosed ordering correction, not an unexplained passing retry.

The first resource-boundary observer counted all public ingress rules, including a
GKE-generated **DENY** rule, and failed its one-rule assertion. Action-aware inspection
then confirmed one public **ALLOW** rule scoped to the load-balancer IP and TCP/80.
No firewall rules were changed. No public SSH/RDP allow rules were present on the
cluster network. Google health-check rules are limited to provider health-check CIDRs.
This is configuration inspection, not a penetration test or exhaustive network audit.

## Native runtime and external HTTP results

- Two Ready **native AMD64** nodes, each hosting one Running/Ready application pod.
- Both pods had zero observed restarts; their runtime image references matched:
  `docker.io/yuenshingyan/finsecure-pay@sha256:1fc3362f15ba91f4161b8fccab644631ccc0733e9b9675bb7e2cb88e7aea5b4c`.
- Both containers verified UID 10001, read-only root filesystem flags, zero effective
  capabilities and successful creation/closure of an owned temporary file under `/tmp`.
- Public health returned 200/healthy on the first readiness observation.
- Synthetic accepted transaction returned 200/valid; zero amount returned 200 with
  `AMOUNT_NOT_POSITIVE`; numeric amount returned the expected safe HTTP 422 response.
- Public OpenAPI reported 0.3.0; public metrics returned FinSecure instrumentation.
  A single load-balanced metrics response is not an aggregate of both pod registries.
- 92 actual Pod JSON log records were captured without synthetic request identifiers.
  Ten actual application JSON entries were also read back from Cloud Logging, with
  project/account metadata removed from the curated samples. Samples were health events;
  they are not a claim of end-to-end correlation or verified cloud alert delivery.

## Limits and remaining steps

No pod deletion, node failure, new-version rollout, rollback or automatic SCM-to-cloud
deployment demonstration occurred. Cloud Prometheus/Grafana/Alertmanager and their
persistence/notification paths remain uninstalled. Successful initial readiness does
not prove self-healing under disruption. Those operations need their own step/review.

The approved planning window remains availability through **18 November**, teardown
review **19 November** after evidence/grading checks. There is no automatic teardown
or spending cap. Review credits daily; do not upgrade to paid billing if credits run out.

Artifacts: [manifest](step-03-deployment/SHA256SUMS),
[creation record](step-03-deployment/creation.json),
[operation observation](step-03-deployment/creation-observation.json),
[profile](step-03-deployment/profile-verification.json),
[nodes](step-03-deployment/nodes.json),
[native/public runtime](step-03-deployment/runtime-verification.json),
[resource boundaries](step-03-deployment/resource-boundaries.json),
[initial firewall observer](step-03-deployment/firewall-inspection.json),
[initial namespace dry run](step-03-deployment/initial-server-dry-run.json),
[apply steps](step-03-deployment/application-steps.json),
[Pod logs](step-03-deployment/application.jsonl),
[Cloud Logging samples](step-03-deployment/cloud-log-samples.json),
[pricing](step-03-deployment/compute-pricing-live.json),
[cost calculation](step-03-deployment/cost-calculation.json),
[host checks](step-03-deployment/host-checks.txt),
[initial failing test](step-03-deployment/initial-host-checks.txt).
