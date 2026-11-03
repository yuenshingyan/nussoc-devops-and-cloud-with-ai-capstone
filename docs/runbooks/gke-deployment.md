# GKE deployment preparation — project ready, no cluster

Status: the dedicated project is active, linked to the selected billing account, and
four approved APIs are enabled. Google Cloud CLI 591.0.0 and browser authentication
are available; the live technical preflight passed on 3 November. No cluster, VM or
load balancer has been created. Existing Kubernetes manifests remain unchanged.
The [concrete resource proposal](../../deploy/infrastructure/gke-proposal.md) requires
approval before provisioning; neither document authorizes deployment.

## Agreed constraints

- Provider direction: Google Kubernetes Engine; Singapore region `asia-southeast1`.
- No out-of-pocket charges and **no upgrade to paid billing**. A budget alert is not
  a spending cap. Stop if the necessary resources require an upgrade.
- User reports Free Trial, zero of **S$385** credits used, expiry **2 February 2027**.
  The billing API independently confirms SGD; credit balance, expiry and trial state
  remain user-reported. No paid-account upgrade has been requested.
- Do not provision before **3 November 2026**. Submission is 4 November; support
  reported grading within 14 days from that date. Plan availability through
  18 November, with teardown planned for 19 November after status/evidence checks.
  This is a precaution, not a hosting duration explicitly required by the rubric.
- Prepare a silent demonstration; no model or AI inference service is needed.
- No credential, project ID, billing identifier or kubeconfig belongs in Git or chat.

## Proposed shape — awaiting final resource/access review

| Item | Proposed direction / unresolved issue |
| --- | --- |
| Cluster | One **zonal Standard** GKE cluster; not a regional cluster with multiplied node count |
| Region / zone | Singapore; zone must be explicitly selected, not silently defaulted |
| Nodes | Two `e2-standard-2` nodes (2 vCPUs / 8 GiB each); no additional Jenkins/build nodes |
| Capacity check | Four vCPUs for steady state; preflight checks six free vCPUs to allow one extra node of upgrade headroom. This does not configure upgrades or autoscaling |
| Application | Two replicas; existing pure-validation contract and non-root/read-only settings |
| Registry / CI | Reuse public Docker Hub and existing local Jenkins; no cloud Jenkins VM or new registry by default |
| Monitoring | Existing Prometheus/Grafana stack in cluster if approved; centralized Cloud Logging collection must be scoped and cost checked |
| Exposure | External application access required; public/private control-plane access, TLS, source restrictions and admin access must be agreed before configuring a LoadBalancer/Ingress |
| Persistence | Size/type of boot and monitoring disks must be included in the final price calculation |
| Budget | Prior estimate about US$85–100 for 384 hours, with US$150 planning reserve; not a quote, spending cap, currency conversion or guarantee of trial eligibility |

Do not deploy a default regional cluster or leave an unspecified autoscaler maximum.
The proposed VM type being listed does not guarantee current zonal capacity. Free-tier
allowances can be shared with other resources and must not be double-counted.

## Actual work sequence

1. Run the technical preflight once an operator-authenticated Google Cloud CLI exists.
   The helper does not install the CLI, log in, enable APIs or change billing.
2. Resolve any disabled APIs or missing permissions by separate approval; rerun only
   after the cause is understood. Record missing quota metrics as unknown, not unlimited.
3. Verify trial account status, credit currency/balance/expiry and quota applicability.
   The ordinary billing-info API does **not** prove these facts; the helper cannot
   honestly certify that deployment is free.
4. Agree the exact zone, cluster/network exposure, disk/logging policy and resource
   inventory, then calculate the full 3–19 November cost against remaining credit.
5. Prepare a newly gated AMD64 release (or approved multi-architecture release) with
   current metrics/logging before switching the manifest image. Publish only with approval.
6. On/after 3 November, with explicit authorization, enable needed APIs and provision
   the approved resources. No create/apply commands are supplied as already-approved
   operations in this preparation checkpoint.
7. Verify two Running/Ready application pods, image identity, actual probes and external
   health/validation. Capture sanitized evidence. Pod-deletion/recovery is the separate
   Step 3.4 demonstration and needs its own confirmation.
8. Complete cloud CI delivery/security gates and observability as their deferred steps;
   do not claim local archive gating proves cloud deployment blocking.
9. Capture the final video and evidence; monitor credits/usage during retention. Export
   records before teardown and check for remaining disks/IPs/buckets afterward.

## Image compatibility blocker already identified

`deploy/kubernetes/base/deployment.yaml` still pins the historical public **0.2.0
multi-platform index**. It is not the later logging/metrics candidate image. Current
local Jenkins exports are ARM64, while the proposed E2 nodes are **AMD64**.

Do not silently deploy an ARM64-only archive to E2 nodes, use an ungated rebuild, or
present the old 0.2.0 image as containing later observability features. Keep the current
pin unchanged until an approved compatible release passes its gates and is published.
A local 0.3.0 AMD64 candidate from `33d4770` was subsequently built and smoke-tested
under emulation. The image gate stopped at input validation because its current archive
validator explicitly requires ARM64. No vulnerability scan, push or deployment occurred.
That failure remains in [live preparation evidence](../../evidence/task-03/step-03-gke-live-preparation.md).
The subsequently approved explicit-platform change preserves the ARM64 default and
all identity checks. Fresh AMD64 candidate `4b243e2` passed runtime smoke and the actual
image gate with zero reported vulnerabilities. All 770 host tests and source gates
passed. See [gate follow-up](../../evidence/task-03/step-03-amd64-gate.md).
The exact image was subsequently published with approval as AMD64-only `0.3.0`,
with anonymous pull and post-pull smoke verified. See the
[release record](image-publication.md). Cluster approval, deployment manifest updates
and native GKE execution remain pending.

## Technical preflight behavior

Implementation: `scripts/gke_preflight.py`, invoked with existing locked development
dependencies (HTTPX2 is already in the project). Google Cloud CLI is a separate operator
prerequisite. It was absent at the initial checkpoint and is now installed (591.0.0).
Homebrew also installed OpenSSL 4 and updated CA certificates; post-install checks
passed (704 tests, lint, formatting and packaging).

From the repository root, after separately approved SDK setup and browser sign-in,
supply the project and zone locally:

```sh
uv run --locked python scripts/gke_preflight.py \
  --project "$PROJECT_ID" --zone "$GKE_ZONE"
```

Do not paste an access token. The helper obtains one from the existing local SDK session,
keeps it in memory, and sends it only to fixed Google HTTPS APIs. It disables redirects
and environment proxies. It performs seven GET requests on a complete path:

- Compute Engine and Kubernetes Engine service enablement state.
- Project billing-enabled state (not trial status).
- Regional and project/global CPU quota metadata.
- The selected zone's `e2-standard-2` shape.
- Readable GKE server configuration.

Token retrieval has a **30-second subprocess limit**. HTTP operations use 30-second
connect/read/write/pool timeouts, with no automatic retry. These HTTP inactivity/phase
timeouts are not a total wall-clock deadline for a slowly streaming response; no overall
preflight stopwatch is implemented. Authentication refresh may occur through the SDK;
no resource mutation or API
activation is performed. The SDK's raw output, server errors, project and billing IDs
are not printed. Missing/invalid SDK credentials or API errors produce fixed failure
codes. Missing quota fields and insufficient headroom require review and exit 2.
Even exit 0 returns `deployment_authorized: false` and explicitly leaves trial-credit
verification unconfirmed. No provisioning function exists in this helper.

## Verification limits

Unit tests exercise Google/SDK boundaries with synthetic fixtures; they are not live
quota, billing, capacity or entitlement proof. An offline CLI check demonstrates the
initial missing-SDK failure path without contacting a cloud account. Subsequent authorized
live checks passed: regional CPU headroom 100, E2 headroom 24, global headroom 12;
SGD billing currency; unused regional disk/IP quotas. Quota is not reserved capacity.
AMD64 image release is complete. Final exposure/resource approval, deployment manifest
updates and cluster provisioning remain pending.
