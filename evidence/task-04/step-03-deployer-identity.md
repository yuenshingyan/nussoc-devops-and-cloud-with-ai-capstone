# Step 4.3 — dedicated deployer identity verified

Date: **4 November 2026, 01:49–01:56 UTC**. Operator-approved setup, not a release.

## Actual setup

Exactly one successful command for each of:

1. Create the dedicated `finsecure-gke-deployer` service account.
2. Grant project `roles/container.clusterViewer` (cluster connect/get/list and project
   get/list). Comparison confirmed all unrelated project IAM bindings were preserved.
3. Create the reviewed `finsecure-deployer` Role in `finsecure-pay`.
4. Bind that Role to the Google service-account email as a Kubernetes User principal.
5. Create one user-managed JSON key in the existing private credential directory.

No Owner/Editor/cluster-admin role, service-account impersonation grant, policy
relaxation, API activation or paid billing upgrade was introduced. The keyless node
service account was not changed. Account/project/key identifiers and raw SDK output
remain private, outside Git. The new credential is long-lived until revoked, not an
automatically expiring key.

## Actual access verification

An isolated SDK configuration authenticated using the new key. Its active account
matched the intended deployer, and a separate kubeconfig connected to the existing
cluster's DNS endpoint. The identity successfully read the actual Deployment UID.

Self-access reviews verified **six allowed** operations:

- Get, patch and watch the named application Deployment.
- List Pods and ReplicaSets in the application namespace.
- Get the named application Service.

They verified **ten denied** operations:

- Get Secrets; exec into Pods; directly create or delete Pods.
- Patch the Service, another Deployment, or a Deployment in another namespace.
- Patch nodes; create RoleBindings; change the namespace policy.

An **actual Secret-list request was forbidden**, in addition to the access reviews.
No image or Deployment patch was attempted: the patch permission check was a self-access
review, not a rollout. Direct Secret API denial does not prevent a deployment writer
from mounting Secrets in its namespace; the limits documented in the runbook still apply.

Before/after snapshots matched: Deployment UID/generation/spec hash, both Ready Pod
UIDs and two available replicas. Public health returned 200 with the healthy body.
Owned probe SDK profiles, token caches and kubeconfigs were removed. The private key
remains mode 0600 for later Jenkins import; no Jenkins job received it in this step.

## Two preserved verification failures

- Initial setup stopped after key creation: the immediate user-managed-key listing
  was empty. All five mutations had already succeeded. No creation/grant was repeated.
- A separate read-only follow-up waited 120 seconds and found the existing key, then
  passed all six allowed checks. It stopped on the first denial because GKE printed
  `no - reason`, while the harness expected exactly `no`.
- A corrected parser accepts that single-line denial format only with exit code 1;
  errors, contradictions and unexpected output still fail. Fourteen regression cases
  cover these distinctions. A final read-only verification passed all checks without
  changing permissions, recreating the key or repeating the propagation wait.

These were failed verification attempts, not failed or repeated deployments.

## Verification and remaining work

839 host tests, Ruff lint/format and packaging passed. All three archived operator
harnesses passed their explicit Ruff checks. No application behavior or dependency
changed. Release-agent provisioning, credential import/isolation, AMD64 CI build/gate,
registry upload and automatic deployment remain pending. Planned revocation is subject
to the 19 November review, not an installed cleanup schedule.

[Setup and cleanup guidance](../../docs/runbooks/cloud-delivery.md).

Artifacts in [step-03-deployer](step-03-deployer/):

- `setup-result.json`: successful mutations followed by the early key-list failure.
- `initial-verification.json`: read-only propagation follow-up and denial-parser failure.
- `final-verification.json`: actual identity/access/availability results.
- `setup-deployer.py.txt`, `verify-deployer.py.txt`, `verify-deployer-final.py.txt`:
  exact executed code, not permission to rerun setup.
- `host-checks.txt`, `SHA256SUMS`.

The harnesses used fixed private local paths. Raw logs and credentials are intentionally
not part of this evidence bundle; review them only locally without printing secret data.
