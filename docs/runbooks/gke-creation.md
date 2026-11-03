# Approved GKE creation procedure

Scope: the user approved the resource/access profile in
[`deploy/infrastructure/gke-proposal.md`](../../deploy/infrastructure/gke-proposal.md).
No paid-billing upgrade is authorized. The application is synthetic-data-only HTTP;
monitoring installation, disruption demonstrations and cloud CI credentials are separate.

## Pre-creation checks

- Confirm the dedicated selected project and user-confirmed Free Trial account. Never
  infer trial status from `billingEnabled`. Keep account/project identifiers private.
- Recheck technical quotas, version availability, existing clusters and subnet overlap.
  Stop rather than changing region, node size/count or exposure to resolve a failure.
- The final check found no existing cluster and no CIDR overlap. IAM was enabled;
  Cloud Resource Manager and Cloud Billing APIs were subsequently enabled for the node
  role grant and SGD tariff lookup. No paid upgrade is part of those API activations.
- The GKE auth plugin 0.5.20 was installed into SDK 591.0.0. SDK installation refreshed
  its own virtual environment; project dependency pins were not changed.
- Live Google SKU lookup now works: SGD/core-hour `0.034517917`, SGD/GiB-RAM-hour
  `0.004625519`, standard disk SGD/GiB-month `0.056441`. For two 2-vCPU/8-GiB nodes,
  384 hours of compute is approximately **S$81.44**; 60 GiB boot disks add approximately
  **S$1.78** using a 730-hour month. These are not the entire bill: load balancing, IPs,
  monitoring disks, traffic/logs, potential management fees, taxes and contingency remain
  within the **provisional S$225 planning envelope**, not an enforced cap or full quote.

## Reproducible one-time creation

Run from the repository root only after the checks above. `PROJECT_ID` is supplied
locally, not stored in this repository. The script deliberately rejects other project
name patterns and requires explicit approval. It is not an idempotent reconciliation
engine: on any partial failure inspect the actual cloud state before continuing.
Do not blindly rerun, automatically delete resources, or silently retry creation.

```sh
APPROVE_GKE_CREATION=trial-only PROJECT_ID="$PROJECT_ID" \
  bash deploy/infrastructure/create-gke.sh
```

Capture stdout/stderr in private operator storage outside Git: IAM output and SDK
responses contain account identifiers. Never commit raw logs or kubeconfigs. The
one-time script creates a custom network, subnet, dedicated keyless node identity,
its one approved project role, and starts asynchronous creation of the fixed zonal
cluster. No billing commands, key export, autoscaler or cleanup is present.

The operator wrapper bounds the command process to 600 seconds; cluster operation
observation has a separate 20-minute deadline with read-only polling. If either
expires, inspect rather than issuing another create request. A timeout does not prove
that server-side creation stopped. Do not automatically cancel or delete resources.

## Operator credentials and deployment

Keep kubeconfig under `~/.config/finsecure-pay/gke/`, directory mode 0700 and file mode
0600. Use an isolated `KUBECONFIG`, not a replacement for the user's global kubeconfig.
The SDK plugin directory must be on the operator process's PATH; no credentials enter
Jenkins or Git. For this Homebrew host it is `/opt/homebrew/share/google-cloud-sdk/bin`.

After verifying the actual cluster profile, node identity and control-plane settings:

```sh
gcloud container clusters get-credentials finsecure-pay-demo \
  --project="$PROJECT_ID" --zone=asia-southeast1-a --dns-endpoint
kubectl apply -f deploy/kubernetes/overlays/demo/namespace.yaml
kubectl apply --dry-run=server -k deploy/kubernetes/overlays/gke
kubectl apply -k deploy/kubernetes/overlays/gke
kubectl -n finsecure-pay rollout status deployment/finsecure-pay --timeout=600s
```

The commands above require the explicitly isolated `KUBECONFIG` and plugin PATH in
the calling environment. Verify that context points to the approved cluster before
applying. Render locally first; bootstrap only the namespace, then server-side dry run
precedes workload/Service apply. A dry-run namespace is not persisted for following
namespaced resources; the first attempt exposed this ordering issue and is preserved.
The overlay
preserves the base security/probe/resource configuration, selects AMD64 and pins the
published 0.3.0 digest. Only the application Service becomes a single IPv4 LoadBalancer;
port 80 is inherited from the base. Other overlays and historical image pins are unchanged.

Observe the external IP for up to 15 minutes; stop and inspect if it remains pending.
Verify two Ready nodes and two Running/Ready application pods, actual image digests,
non-root identity, health/validation behavior, safe JSON logs and external HTTP access.
Public health readiness is observed for at most 120 seconds, with five-second polling
and ten-second HTTP phase timeouts. Business-case checks run once after readiness;
failures are not automatically retried. Use only synthetic data. Do not treat a public
`/health` response alone as proof of
all validation, pod recovery, automatic rollout or CI deployment-gate requirements.

## Actual deployment

On 3 November the cluster reached RUNNING. Two Ready AMD64 E2 nodes each host one
Running/Ready application pod, with zero observed restarts. The live 0.3.0 image digest
matches the published release. Non-root UID, root filesystem read-only flags and zero
effective capabilities were checked inside both containers.

Public health: **http://35.198.197.186/health**. Accepted/rejected/invalid synthetic
requests, OpenAPI 0.3.0 and metrics access passed. Ten actual JSON application entries
were read back from Cloud Logging. No cloud dashboard, Prometheus deployment, alerts,
pod deletion or new-version rollout demonstration has been performed in this step.

The resource census found two VMs, two 30 GB standard boot disks, one external TCP/80
forwarding rule, no Cloud NAT/router, and no user-managed node service-account keys.
A first firewall observer incorrectly counted a generated DENY rule as an ALLOW rule;
corrected action-aware inspection confirmed one public allow rule, scoped to the LB IP
and TCP/80, without changing any firewall rule. This is configuration inspection, not
a penetration test or a guarantee about every possible network path.

See [deployment evidence](../../evidence/task-03/step-03-managed-deployment.md).

## Retention and teardown

Review trial credit daily. Keep the approved availability window through 18 November;
review teardown on 19 November after grading/evidence checks. This is not scheduled
automation. No paid upgrade is permitted to preserve availability after trial exhaustion.
