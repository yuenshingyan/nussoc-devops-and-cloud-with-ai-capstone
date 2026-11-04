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

**Additional verified setup:** the ARM64 release worker was built and exercised, and both
existing credentials were imported into the release folder. Real Jenkins file-binding
probes and read-only registry/GKE access passed. The subsequent scheduling guard passed
live allow/deny tests. The worker is now deliberately stopped and diagnostic jobs are
disabled. See the checkpoints below.

**Partially implemented:** the fixed, disabled `finsecure-release/delivery` definition
now performs candidate-selection checks. It has never built and its non-sandboxed script
is pending approval. Separate controller-transfer and independent-verification helpers
now pass host tests and a real administrator-owned remoting probe; they are not yet
wired into this Pipeline. Registry upload and cloud deployment remain unimplemented.
The feature-branch Jenkinsfile now exports
and scans AMD64 explicitly. A manual Jenkins candidate passed 961 tests and all gates;
its AMD64 archive was independently verified. Normal main #34 remains the earlier
ARM64 build until reviewed publication and a new SCM run. Neither pipeline publishes
or deploys yet.

The operator has saved the dedicated Docker Hub token. A read-only check on
4 November verified the private file metadata, received an authenticated registry
token granting the requested repository pull/push actions, and read the existing
0.3.0 manifest with the expected digest. That initial check attempted no upload or
Jenkins import; the later import and binding probes are recorded below.
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
production release job has received this credential yet. The owned read-only diagnostic
job has used a temporary file binding; its files were removed afterward.

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

## Release worker and credential checkpoint — verified, worker stopped

The opt-in `ops/jenkins/release.compose.yaml` worker is ARM64; it will publish a separately
built AMD64 archive without running or rebuilding it. `release-agent.Dockerfile` pins
Python and Jenkins remoting image digests plus checksums for crane 0.22.1, kubectl 1.36.4
and the standalone GKE auth plugin archive dated `20261016073856` (its binary reports
`Kubernetes v37.0.0-12-g05550ad15`). The actual image build and tool version checks passed. APK packages are repository-resolved, not individually version-locked;
this is not a vulnerability scan or complete reproducible-build claim for the worker.
No Google SDK or personal login is installed. Pip/ensurepip are removed.

The worker uses UID 1000, one exclusive executor, a read-only root, all capabilities
dropped, no-new-privileges, 0.5 CPU and 512 MiB. Its workspace, temporary storage and
remoting-secret volumes are separate from the source worker/controller. No host bind,
Docker/BuildKit socket or public port is attached. The existing 1 GiB disk-space monitor
threshold was retained: an initial 64 MiB tmpfs made Jenkins mark the node offline, so
only this worker's temporary storage moved to a dedicated disk-backed volume. That
volume has no independent quota and shares Docker's backing storage; check host and
Docker headroom separately. Private client subdirectories are mode 0700.

`release_bootstrap.py` creates a distinct remoting credential volume and refuses to
replace an existing/ambiguous volume. `release_store.py` imports the existing private
files into `finsecure-release` using multipart file credentials, after a synthetic
import/hash round trip and removal. It refuses to replace existing credentials.
`finsecure-ci` cannot resolve either folder credential; operator comparison matched
both private source files. File-credential GLOBAL scope here means the containing
folder, not Jenkins' root store. Administrators still have full authority.

`scripts/release_cluster.py` validates the dedicated service-account identity, removes
inherited Google/SDK/Kubernetes configuration overrides, obtains ADC directly through
the plugin, and discovers the fixed cluster through Google's API. It refuses redirects,
proxies and non-GKE DNS endpoints. It writes a private, token-free kubeconfig with an
exec credential provider. Auth subprocesses have a 30-second limit, discovery requests
20 seconds, and probe kubectl calls 30 seconds with 20-second request limits. These are
read-only probe budgets, not a deployment/rollback timeout policy.

The operator-controlled `finsecure-release/verify-boundaries` Pipeline has no SCM or
upstream trigger. Its successful #4 used both real file bindings on the release worker:
registry pull/push token scope and the existing image digest were verified without
upload; the deployed application had two available replicas and Secret listing was
forbidden. Both bound files and owned client directories were removed, reports archived,
and workspace cleaned. This was not an automatic SCM release. Preserve #1 ABORTED
(disk monitor), #2 SUCCESS (earlier client path), and #3 FAILURE (inherited setgid).

The source gate separately blocked B108 on the initial hardcoded temporary path.
Client state now lives inside the job workspace's cleanup boundary. A fresh directory
can inherit setgid there; the caller clears inherited bits on that new owned directory
before the existing strict mode-0700 check. No supplied directory is repaired and no
security suppression/threshold change was added. Fixed failure-code reporting does not
expose provider messages. Regression tests cover inherited permissions and safe errors.

**Historical boundary gap at this checkpoint:** EXCLUSIVE labels are scheduling
preferences, not job access control. Folder credential scope alone does not stop another
Pipeline requesting this node and leaving code to observe a later binding. The worker
was stopped with SIGTERM (exit 143), diagnostic job disabled and queue empty. The
subsequent scheduling guard below closes this executor-assignment gap; it does not make
Jenkins a complete sandbox or enable production delivery.

Read-only operator checks, when the reviewed worker is intentionally online:

```sh
PYTHONPATH=ops/jenkins uv run --locked python ops/jenkins/verify_release.py
PYTHONPATH=ops/jenkins uv run --locked python ops/jenkins/verify_secrets.py --notifications
```

The first check intentionally fails while the worker is stopped. It checks runtime
mounts against the reviewed Compose contract, resource/privilege settings, known-secret
absence from process arguments/environment, remoting identity and folder scope. It
reads Linux proc metadata rather than relying on incompatible Alpine `ps` options.

See [checkpoint evidence](../../evidence/task-04/step-03-release-agent.md). No key/token
was recreated or rotated; no upload, Deployment patch or cloud resource change occurred.
Normal SCM history remains #34; all 73 plugin versions and notification bindings were
preserved. This checkpoint is not yet merged/published.

## Trusted-job scheduling guard — installed and live-tested

`ops/jenkins/release-policy.groovy` installs a controller-owned `QueueTaskDispatcher`
through the pinned controller image's startup directory. It uses the queued task's
actual owner Job and actual node name, not caller-supplied labels or parameters.
Version 1 allows only `finsecure-release/verify-boundaries` and
`finsecure-release/verify-scheduling` onto `finsecure-release`. Unknown ownership and
other jobs are denied. Release-folder executor tasks are denied all other nodes.
Pipeline flyweight orchestration remains possible on the controller without allocating
a worker workspace. Duplicate registrations are rejected; owner-resolution exceptions
produce a fixed denial rather than exposing exception details.

The installed Jenkins/plugin APIs compiled the policy and passed ten decision cases.
After idle controller recreation, all 73 plugin versions, main #34 and source-worker
operation were preserved. Five real Pipeline cases passed verification:

| Actual assignment requested | Observed outcome |
| --- | --- |
| Allowlisted diagnostic → release worker | SUCCESS; shell step ran |
| Root-level source probe → release worker | Queued with JOB_DENIED; never assigned |
| Unapproved release-folder job → release worker | Queued with JOB_DENIED; never assigned |
| Allowlisted release job → source worker | Queued with WRONG_NODE; never assigned |
| Root-level source probe → source worker | SUCCESS; shell step ran |

In each denied case the target worker was online and idle; the real queue reason and
actual PlaceholderTask owner were inspected, then that owned probe was explicitly
stopped (ABORTED). This is not merely an offline-node or label-mismatch test. No probe
bound release credentials. All four diagnostic jobs, including the earlier binding job,
are disabled; the release worker is stopped again, source worker online and queue empty.
See [scheduling evidence](../../evidence/task-04/step-03-release-scheduling.md).

`verify_release.py` now requires the active guard and exact version-1 allowlist. The
one-time `release_bootstrap.py` performs that policy preflight before any Docker command
or secret-volume creation. It still refuses to replace existing resources; do not rerun
it to resume this existing worker.

**Operational restart rule:** stop the release worker before recreating/restarting the
controller, and require a successful policy preflight before starting the worker again.
Startup-script failure does not itself shut down Jenkins; merely finding its script on
disk is not sufficient. The opt-in worker has no restart policy. Administrators and
reviewed job definitions remain trusted; this is not a multitenant security guarantee.
Retest on controller/plugin upgrades. Do not enable arbitrary folder jobs or run scripts
from upstream artifacts. Production release selection, credentials usage and artifact
validation remain separate controls. A future production job needs a reviewed explicit
allowlist/preflight update; version 1 authorizes no production delivery job.

## AMD64 candidate CI — verified, not published

Candidate `dc7ffe5a2884f8aeb833f9befd0f1be30d608739` changed the export platform,
metadata and scanner argument together to `linux/amd64`. Scanner/archive helper
ARM64 defaults remain available; current CI verification explicitly selects AMD64
and rejects both summary and raw-report platform mismatches. Existing test, source,
dependency, image identity/freshness/severity gates and timeout budgets are unchanged.

Manual `finsecure-ci-amd64-review-20261104041956` #1 passed **961 tests**, all gates
and **33 verified artifacts**. Trivy reported zero findings at every severity; database
age at completion was approximately 10,412 seconds, inside the existing 86,400-second
policy. The exact archive and config identities are recorded in the
[evidence](../../evidence/task-04/step-03-amd64-ci.md), not as registry manifest digests.

The operator wrapper checked out public base `19b4486`, verified a local Git bundle
hash, and checked out the exact unpublished candidate. Existing stages were retained;
notification provenance was set to the verified candidate. Local Mailpit received the
matching SUCCESS notification. This is a real manual candidate pipeline, not normal
SCM triggering or external email receipt. Tests ran on the ARM64 source worker;
BuildKit targeted AMD64 using available emulation. The candidate application image
was not started or deployed; no native GKE runtime result is claimed for it.

The candidate job is disabled; release worker remains stopped; normal main remains
#34. Host free storage was about 3.2 GiB and Docker backing storage 7.6 GiB. Review
headroom before another image build; do not prune shared caches or retained scanner
diagnostics without approval.

## Fixed release selection — installed disabled, not a working deployment pipeline

The operator approved a fixed administrator-owned, non-sandboxed controller definition
rather than putting Jenkins admin credentials on the worker or relaxing sandbox rules
globally. The agreed policy is one release at a time, a ten-minute overall Jenkins
budget, current-main successful AMD64 artifacts only, and no automatic release retries
or rollback. Publishing/deployment must remain disabled through verification and review.

`ops/jenkins/release-job.groovy` implements only the first selection stage. It requires
one authoritative upstream cause for `finsecure-ci`, the fixed Git repository and
`*/main` SCM definition, a completed SUCCESS run, native JUnit counts without failures
or skips, and the recorded Git revision/branch. The installed Git plugin records
`refs/remotes/origin/main`; other spellings are not silently normalized. A fixed HTTPS
GitHub request checks the current main SHA with no credentials, proxy or redirects and
five-second connect/read limits. Source/image gate summaries must report the required
passing policy and consistent revision, AMD64 platform, lock and digest shapes.

Fixed report names are read on the controller with a one-MiB limit and owned stream
cleanup. Malformed JSON details are not echoed. **These are selection checks, not full
artifact authentication:** strict artifact parsing, checksum inventory, actual archive
bytes/config identity and database freshness at release time still require verification.
The returned candidate explicitly marks artifact verification required and deployment
disabled. The Pipeline always stops before delivery, even after a positive selection.
It has no worker allocation, credential binding, upload or deployment command.

`release_job.py` creates this job once in the existing owned folder, with no parameters
or triggers, disabled, serialized without aborting an active predecessor, and with an
exact script match check. It refuses an existing/uncertain job rather than replacing it.
The installed non-sandboxed definition remains **pending script approval**; global script
approvals/signature permissions were unchanged. The scheduling guard remains version 1
and does not allow this job onto the release worker. No image rebuild was needed.

Native controller checks compiled the exact script, accepted a clearly synthetic
main-authority fixture around the real candidate reports, and passed 28 rejection cases,
three bounded-parser cases and absent/manual-cause checks. A simulated upstream envelope
around real main #34 exercised the actual SCM/JUnit/artifact APIs and rejected its ARM64
image. This was not a genuine downstream trigger or Pipeline-body execution. The job
has never built; the ten-minute cancellation behavior has not been demonstrated.

See [selection evidence](../../evidence/task-04/step-03-release-selection.md). The next
checkpoint below verifies separate transfer/validation helpers. They must be integrated
before any credential binding, followed by immutable upload and image-only deployment.
Recheck current main immediately before external actions; a selection-time observation
alone cannot make GitHub and Kubernetes updates atomic. Do not approve/enable this
incomplete definition as a release pipeline.

## Artifact-transfer and verification checkpoint — 4 November 2026

`ops/jenkins/release-transfer.groovy` is a fixed administrator-owned helper, not upstream
code. It reads 21 fixed files through the completed run's standard artifact manager and
writes them through Jenkins remoting to the release worker. It rejects another node,
an existing destination, source links/escapes, missing files and oversized streams.
It hashes bytes during transfer and creates the control receipt last. It never gives
Jenkins admin credentials to the worker, follows artifact download URLs, or binds the
registry/GKE credentials. The operation owner removes its newly allocated scratch
folder after verification; borrowed streams remain the caller's responsibility, and
owned streams close on failure.

`scripts/release_artifacts.py` independently verifies those hashes and sizes, strict
JSON, source hashes against trusted Git snapshots, lock-bound exports, raw Bandit and
dependency results, and raw image results. It rejects boolean counts, duplicate JSON
keys, nonfinite numbers, missing/extra inputs and unsafe filesystem entries. It checks
UTC ordering and DB freshness both at the report timestamp and the release clock;
the existing 86,400-second maximum age is unchanged. Runtime packages must match the
locked export plus the project. LOW source findings remain visible; the policy is not
weakened. The verifier always returns `publishing_authorized: false`.

`scripts/release_archive.py` reads without extracting or running the image. It verifies
one Docker/OCI export, every referenced blob hash/descriptor, the AMD64 non-root
configuration and revision, matching Docker/OCI layer references, and each expanded
layer's diff ID against the configuration. Its returned **archive OCI manifest digest
is not evidence of a published registry manifest**.

These helpers use explicit defensive limits: 1 MiB per report/control/JSON input,
64 MiB for the compressed archive and outer tar stream, 64 visible archive members,
256 MiB expanded per layer and 512 MiB expanded across layers. Transfer and verification
each have a 120-second cooperative check budget inside the proposed ten-minute release
budget. Expired-budget checks are tested; **blocked-I/O cancellation and the complete
Pipeline's wall-clock timeout are not yet demonstrated**. No background transfer or
automatic retry was introduced. The receipt, source snapshots and verifier code must
come from the trusted controller, not the upstream artifact inventory.

Actual verification used the retained manual AMD64 candidate #1 at `dc7ffe5`, not a
normal main build or eligible downstream release. The operator supplied exact local
Git-object snapshots for that revision. The controller transferred 21,615,108 bytes;
the constrained ARM64 worker verified 21 files and nine layers. This was byte inspection,
not AMD64 image execution. The worker rejected changed bytes and a synthetic future
release clock, then reverified restored inputs. The failed first observer compilation
(JVM string-literal limit) and subsequent successful probes are retained. The final
probe used the exact recorded helper hashes after adding the DB/report-time cross-check.

All 1,060 host tests, Ruff checks, package build and existing source/dependency gates
passed (43 LOW, zero blocking source findings; 15 dependencies clean). The pytest
configuration now explicitly includes the repository root for direct tooling imports;
application wheel contents and dependencies are unchanged.

The owned worker scratch folder was removed, the worker stopped without OOM, and the
queue was empty. The installed release definition remains unchanged, disabled and never
built; policy version 1 still excludes it. Main remains #34 and the cloud application's
Deployment specification and Pod identities remain unchanged, with two Ready replicas
and public health 200. See [artifact evidence](../../evidence/task-04/step-03-release-artifacts.md).

## Remaining verification

Trusted production Git-snapshot acquisition and Pipeline integration; rejection of newer
builds including the same revision; action-time main checks; reviewed publication and
normal SCM AMD64 proof; real downstream triggering, serialization, timeout/cancellation
and restart behavior; immutable upload identity; deployment failure/rollout/smoke checks
and retained failure reports. Full delivery is pending until all of these run successfully.
