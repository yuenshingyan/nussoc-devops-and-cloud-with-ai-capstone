# Step 4.3 cloud delivery — credential and authorization preflight

Date: 4 November 2026. This is preparation, **not a completed release pipeline**.

The operator approved the isolated release-agent approach and personally created/saved
a dedicated Docker Hub token using the terminal-only helper. No token was pasted into
chat or added to Git. Existing Docker Desktop credentials were not reused.

## Actual read-only checks

- Credential directory mode 0700; one operator-owned regular token file, mode 0600.
  Symlink/writable-ancestor checks passed; the file was opened without following links.
- Docker authentication returned 200 and granted the requested repository `pull,push`
  scope. The issued bearer token successfully read the existing 0.3.0 manifest (200),
  whose digest matched the deployed release.
- **No upload occurred.** Other-repository/DELETE permissions of the underlying PAT
  were not independently established. Jenkins has not received the token.
- The predefined Google `roles/container.clusterViewer` was inspected: cluster
  connect/get/list and project get/list, not workload administration.
- The application had two available replicas and the expected non-root/seccomp/
  no-escalation/drop-all-capabilities settings. Its namespace had **no Pod Security
  Admission labels**. No cloud resources, credentials or authorizations were changed.

## Candidate safeguards, not live configuration

A restricted-v1.36 namespace admission patch and a namespaced deployer Role are prepared.
The Role is not part of the application overlay and has not been installed or bound.
Enforcing the namespace policy requires explicit approval before activation. Existing
security settings appear compatible, but actual positive/negative server-side Pod dry
runs are still required. No new Pod may be created by those checks.

Offline `kubectl kustomize` comparison confirmed the only application-overlay difference
is the six namespace Pod Security labels. Deployment, ConfigMap and Service render
identically. This is not server admission verification.

**825 host tests**, Ruff lint/format and packaging passed, including 13 new static
policy-contract cases. These tests are not a substitute for Google authorization or
Kubernetes admission checks.

Restricted Pod Security prevents classes of privileged workload configuration; it does
not limit Deployment patches to image-only updates, guarantee application availability,
or prevent access to namespace Secrets through an altered workload. Keep unrelated
sensitive resources out of the application namespace and release credentials out of
untrusted jobs. See the [design/setup runbook](../../docs/runbooks/cloud-delivery.md).

## Evidence

- [Registry check](step-03-cloud-preparation/registry-access.json)
- [Authorization preflight](step-03-cloud-preparation/authorization-preflight.json)
- [Offline overlay comparison](step-03-cloud-preparation/namespace-policy-render.json)
- [Host checks](step-03-cloud-preparation/host-checks.txt)
- [Checksums](step-03-cloud-preparation/SHA256SUMS)

Release agent/tool installation, Google service account/key/IAM/RBAC setup, Jenkins
credential import, AMD64 Jenkins build/gate and automatic publishing/deployment remain
pending. No paid upgrade, key-policy relaxation, cluster modification or disruption was
performed during this preflight.
