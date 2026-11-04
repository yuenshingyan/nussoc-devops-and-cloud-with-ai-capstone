# Cloud delivery — approved approach, setup in progress

Step 4.3 resumes from published `19b4486` on
`task-04/step-03-container-delivery`. Automatic main build #34 passed 781 tests,
all existing gates and 33 artifacts. Step 3.4 evidence is published; its deletion
must not be repeated by this work.

## Approved direction and current limits

The operator approved an isolated local Jenkins release agent, registry-upload/GKE
client tools, a Docker Hub CI token and a dedicated least-privilege Google deployer
service account using a service-account key held in Jenkins credentials.

**Implemented and live-verified:** dedicated Google deployer, one private JSON key,
project cluster-discovery grant and namespaced Role/RoleBinding. Six allowed and ten
denied access reviews passed using that identity; an actual Secret-list request was
forbidden. Application state remained unchanged. See
[deployer evidence](../../evidence/task-04/step-03-deployer-identity.md).

**Not yet implemented:** release agent, release jobs, registry upload, Jenkins credential
import or cloud deployment stages. The current Jenkinsfile
still exports/scans ARM64 and has no publishing/deployment stage. Read-only inspection
confirmed the existing BuildKit worker advertises AMD64 support; this is not yet an
actual AMD64 Jenkins build/gate result.

The operator has saved the dedicated Docker Hub token. A read-only check on
4 November verified the private file metadata, received an authenticated registry
token granting the requested repository pull/push actions, and read the existing
0.3.0 manifest with the expected digest. No upload or Jenkins import was attempted.
This does not independently establish the PAT's permissions on other repositories,
whether it also permits deletion, or whether an actual push will succeed.

## Operator action: create the Docker Hub CI token

1. Sign into Docker Hub as the owner of the existing `yuenshingyan/finsecure-pay`
   repository. Open account settings → Personal access tokens.
2. Create a dedicated token named `finsecure-ci-demo`, with **Read & Write**, not Delete.
   Prefer repository restriction if the available account supports it. Otherwise record
   that the personal token can affect other writable repositories: Jenkins must enforce
   a fixed destination, but that is not a provider-side repository permission boundary.
3. Choose the shortest available expiration covering availability through **18 November**.
   Plan explicit revocation on **19 November**, after grading. Do not upgrade the account
   or buy a plan to obtain a token; stop if the permitted token is unavailable.
4. In a local interactive terminal, run from `capstone/`:

   ```sh
   uv run --locked python scripts/release_credentials.py
   ```

   Paste the new token only into the hidden terminal prompt—not chat, a shell command,
   an environment variable, source files or a screenshot. The helper refuses non-terminal
   input and an echoing password-prompt fallback. Clear your clipboard afterward.
5. The fixed file is `~/.config/finsecure-pay/release/dockerhub-ci-token`, mode 0600,
   inside a mode-0700 directory. Existing files are never overwritten or rotated.
   Unsafe directory permissions/symlinks fail rather than being silently repaired.
   A failed write can leave a private partial file; inspect locally rather than retrying
   blindly. Do not print the token while troubleshooting.
6. Tell the coding assistant only that local setup completed. Do not paste the token.

No Docker Desktop credentials are read or reused by this helper. It makes no network
requests, creates no Google key and does not change Jenkins or the deployment.

## Release design boundaries

- Keep existing test/build jobs free of release credentials. Use a separate release
  job/folder and agent with its own workspace and remoting credential. Existing folder
  and downstream-build plugins are present; no plugin upgrade is currently proposed.
- No Docker socket, BuildKit socket, personal gcloud directory or operator kubeconfig
  on the release agent. No privileged container, additional cloud VM, node-count change,
  paid billing upgrade or public Jenkins endpoint.
- Only trusted, reviewed main builds may release. Check upstream completion/result,
  exact source revision, gates and artifact identity independently. Do not execute
  scripts taken from arbitrary upstream artifacts with release credentials available.
- Build AMD64, scan the selected AMD64 archive and publish **that exact gated image**
  without rebuilding. Use immutable commit-addressed tags; never overwrite existing
  semantic-version tags or publish a deliberately vulnerable image.
- Grant the deployer only cluster discovery/connection and namespace-scoped access
  needed to inspect and patch the existing application Deployment. No project Editor,
  Owner, cluster-admin, Secret reads, pod exec, IAM administration or node operations.
  Verify actual positive and negative permissions before enabling delivery.
- Store credentials in the restricted release folder. Use file credentials/private
  temporary client directories; never put token/key contents in argv, logs or reports.
  Disable release jobs until identity, gate and isolation tests pass.
- A Google service-account key is **long-lived until revoked**; this design is not
  keyless and does not create automatic expiry. If Google policy blocks creation,
  preserve the failure and stop: do not weaken policy or upgrade billing.
- Preserve existing keys/credentials; the new deployer is separate from the keyless
  node service account. Record key/token revocation and credential-store removal for
  the 19 November review. No cleanup schedule has been installed.

Before introducing live release operations, record the exact tool/image pins, agent
resource limits, credential/job/node boundaries, IAM/RBAC permissions, release
serialization, stale-build policy, timeouts and failure/rollback behavior in this
runbook and verify them. No retry or automated rollback contract is established here.

## Namespace admission prerequisite — applied and live-verified

Initial read-only inspection found no Pod Security Admission labels on `finsecure-pay`.
The existing pod/container security contexts use non-root UID 10001, RuntimeDefault
seccomp, no privilege escalation and all capabilities dropped; two replicas remain
available. These observations are not a complete live admission test.

Deployment `patch` permission can change the entire pod template, not just its image.
RBAC alone cannot constrain which template fields change. Before granting that
permission, the operator explicitly approved enforcing the **restricted v1.36** Pod
Security Standard in this application namespace. On 4 November at 01:41 UTC, exactly
one UID/resource-version-preconditioned namespace patch applied the six labels. The
GKE namespace patch adds
`enforce`, `audit` and `warn` labels, each pinned to v1.36. It leaves the demo overlay,
application Deployment, Service and ConfigMap unchanged. Review this version pin
when the managed cluster moves to a newer minor version.

Activation applied **only the namespace labels**, not the whole application overlay.
A compatible Pod was accepted in a server-side dry run; privileged, host-network and
host-path variants were each rejected with `restricted:v1.36` policy violations.
No probe Pod was created. Original Pod UIDs remained Ready, two replicas remained
available, Deployment/Service/ConfigMap contents were unchanged and public health
returned 200. The initial preflight failed before mutation because it requested an
unhashed ConfigMap name; the corrected harness used the live Deployment reference.
See [activation evidence](../../evidence/task-04/step-03-namespace-admission.md).
Further policy changes or repeated probes require their own reviewed scope.
Pod Security enforcement applies to Pods; acceptance of a Deployment dry run alone
would not prove its future Pods pass admission. Preserve rejection evidence and stop
on unexpected results, rather than relaxing the policy.

`deploy/kubernetes/delivery/role.yaml` is deliberately separate from the application
overlay. It is now installed and bound to the dedicated Google deployer identity. It permits patch/get/watch of the named
Deployment, read-only Pods/ReplicaSets in this namespace and get of the named Service.
It grants no direct Secret reads, exec, create/delete, node or RBAC operations.
The predefined Google `roles/container.clusterViewer` was inspected read-only and
contains cluster connect/get/list plus project get/list—not workload administration.
Do not claim this Google role limits metadata visibility to one cluster.

**Remaining authority:** restricted Pod Security is not an image allowlist or a complete
sandbox. A deployment writer can still change application code/configuration, interrupt
availability and mount Secrets available in its namespace. Keep unrelated workloads,
privileged service accounts and sensitive Secrets out of this namespace. Direct Secret
API denial is not a guarantee against indirect access through a modified workload.
Only reviewed main release code should hold this credential. Provider grants, role
binding and actual positive/negative service-account tests are now verified. No Jenkins
job has received this credential yet.

## Approved deployer bootstrap execution contract

The one-time operator bootstrap created `finsecure-gke-deployer` in the already-selected
capstone project, granted only `roles/container.clusterViewer` at project scope, created
the reviewed namespaced Role and a User RoleBinding for that Google service-account
email, then created one JSON key outside Git. It refuses an existing account, Role,
RoleBinding, key file or execution record instead of replacing/retrying setup.

All SDK/Kubernetes command output remains in a new private mode-0700 setup directory;
files use mode 0600. Each subprocess has at most 60 seconds (Kubernetes requests also
use 20 seconds), within a 600-second overall observation budget. There is one 120-second
wait after the IAM grant for propagation. There are no wrapper retries. The SDK may
perform internal transport retries; an unsuccessful/ambiguous mutation stops setup
for inspection, without automatic rollback or credential replacement.

The new key is activated only in a separate temporary-purpose SDK configuration and
kubeconfig, never the operator's normal profile. Credential override environment
variables are removed from that probe environment. Verify the active identity, actual
cluster/deployment read access, positive and negative self-access reviews, and a direct
forbidden Secret-list request. No image patch or workload execution is part of setup.
Compare application state before/after and verify public health. Remove the owned probe
SDK/token-cache/kubeconfig directory after checks; retain the private original key for
later Jenkins import. On failure retain private diagnostics and inspect partial cloud
state before any further action. A successful setup does not enable Jenkins delivery.

### Actual bootstrap outcome and retained credentials

All five creation/grant commands succeeded once. The immediate key listing was empty,
so setup stopped rather than creating another key. After one 120-second propagation
wait, the existing key appeared. That read-only verification then stopped because GKE
returned `no - reason` while the original checker expected exactly `no`. The corrected
parser has 14 regression cases and rejects CLI errors/contradictory results. A separate
read-only final verification passed all 16 access reviews and the actual denied Secret
list. No grant was widened and no key was replaced. Both failed records are retained.

The key remains at `~/.config/finsecure-pay/release/gke-deployer.json`, mode 0600.
Owned probe SDK profiles, token caches and kubeconfigs were removed. Private diagnostic
outputs remain outside Git in `release/deployer-setup`, `release/deployer-verification`
and `release/deployer-final-verification`. Do not print or copy those raw files into
submission evidence. The ordinary operator profile/kubeconfig was not replaced.

### Credential teardown — future approval, not performed

At the planned 19 November review, after grading: disable release jobs first, remove
the application's `finsecure-deployer` RoleBinding/Role, revoke the recorded Google key
and Docker Hub token, remove the deployer's project IAM binding/service account, then
remove its Jenkins credentials and private local key. Confirm every actual outcome;
deleting a key alone does not promise immediate invalidation of previously issued
access tokens. Do not affect `finsecure-gke-node` until the separate cluster teardown.
There is still no automatic key expiry, rotation, revocation or scheduled cleanup.

## Remaining verification

Actual AMD64 CI build and scan; tool supply-chain checks; isolated agent provisioning;
credential import and Jenkins isolation checks; trusted-main
release selection; immutable upload identity; healthy rollout and smoke checks; retained
failure reports. Full delivery is pending until all of these run successfully.
