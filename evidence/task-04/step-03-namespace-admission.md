# Step 4.3 — restricted namespace admission activated

Executed with explicit operator approval, **4 November 2026, 01:41 UTC**.

## Actual change

Exactly one JSON Patch updated the `finsecure-pay` namespace, guarded by its captured
UID and resource version. Only six labels were added: enforce/audit/warn `restricted`,
with each version pinned to `v1.36`. Existing namespace labels were preserved.
No application overlay was reapplied, Deployment patched, Pod deleted, Google key
created, IAM/RBAC grant installed or billing setting changed.

## Actual server-side admission checks

All four requests used `kubectl create --dry-run=server`. No test Pod was persisted.

| Pod template | Actual result |
| --- | --- |
| Existing application template | Accepted, CLI exit 0 |
| Privileged container | Rejected, exit 1, restricted:v1.36 violation |
| Host networking | Rejected, exit 1, restricted:v1.36 violation |
| Host-path volume | Rejected, exit 1, restricted:v1.36 violation |

The harness checked each expected reason in the server's error, not merely a generic
failure exit. Tests ran under the operator identity, avoiding confusion between a
missing deployer RBAC permission and an admission rejection. No incompatible workload
was run, even temporarily. A final namespace-wide Pod list contained no probe Pod.

## Availability and unchanged objects

- Same original application Pod UIDs, Running/Ready before and after.
- Two available Deployment replicas before and after.
- Deployment UID, generation and spec unchanged.
- Service UID/spec and ConfigMap UID/data unchanged.
- Public health returned 200 with the healthy body before and after.

These are before/after observations, not a continuous availability guarantee.
No claim is made about new-version rollout or deployer-account authorization.

## Preserved preflight failure

The first preflight requested `finsecure-pay-config` instead of the Kustomize-generated
ConfigMap name. It stopped with **zero namespace patch attempts** and no Pod probes.
The corrected harness discovers the reference from the live Deployment. The failed
record is preserved separately; it was not an ambiguous mutation or repeated patch.
The successful execution issued one namespace patch and four server dry runs.

## Verification and limits

825 host tests, Ruff lint/format and packaging passed. The exact executed harness also
passed Ruff lint/format. Static configuration checks and offline rendering were already
verified in the [preparation evidence](step-03-cloud-preparation.md).

Restricted admission prevents specified privileged workload configurations. It does not
make Deployment patch access image-only, prevent an application outage, or guarantee
that namespace Secrets cannot be mounted by a modified workload. The planned deployer
identity, role binding, credential import and release agent remain unimplemented.

## Artifacts

- [Activation/probe results](step-03-namespace-admission/namespace-activation.json)
- [Preserved preflight failure](step-03-namespace-admission/preflight-failure.json)
- [Exact executed harness](step-03-namespace-admission/activate-namespace-policy.py.txt)
- [Host checks](step-03-namespace-admission/host-checks.txt)
- [Checksums](step-03-namespace-admission/SHA256SUMS)

The archived harness is historical execution evidence, not permission to repeat changes.
