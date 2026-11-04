# Cloud delivery — live integrated release

## Current verified operation

Normal SCM build **#39** automatically triggered **delivery #3**, which passed exact image
publication, independent registry readback, conditional image-only deployment, rollout and
four synthetic smoke cases. The live application is **0.4.0** with two verified ready Pods.
[Evidence, retained failures, release blocks and controlled rollback](../../evidence/task-04/step-03-live-delivery.md).

The enabled job uses fixed approved code, native SUCCESS upstream triggering, scheduling
policy v2, serialization and disabled resume. Original-candidate checks occur before writes.
The next release takes its approved spec baseline from the previous successful delivery's
archived deployment report; it does not approve arbitrary live drift. Existing SHA tags and
uncertain outcomes require inspection, not automatic repush, rebase or rollback.

Public health readiness requires ten consecutive healthy observations one second apart,
each bounded by five seconds and the original ten-minute release budget. Then the strict
smoke suite runs once. Readiness observations do not repeat image pushes, PATCHes or validation
POSTs. Full live restart/cancellation/concurrency fault demonstrations remain unverified.

## Historical setup record (superseded by the live result above)

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
or rollback. The later approved crane-internal retry exception is recorded below; it does
not permit whole-release retries. Publishing/deployment remains disabled through review.

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

## Supersession guard candidate — 4 November 2026

The working `release-job.groovy` now rejects a candidate unless its build number is
exactly the source job's latest build and the source job has no queued build. Newer
failed, running or successful builds supersede it even when their Git SHA is identical.
Missing/invalid ordering data fails closed. Selection checks local ordering both before
artifact reads and after the current-main lookup.

The new `recheck(releaseRun, expected)` helper repeats full authoritative selection,
including current GitHub main, then compares the complete selected candidate map.
Callers must preserve the original selection unchanged and keep verification outputs
separate. This helper is intended for immediately before **each** future external
action; it is not yet wired to publishing/deployment, which remain absent. These are
point-in-time checks, not an atomic transaction across Jenkins, GitHub and Kubernetes.

Native checks passed ten ordering rejection cases, three newer/same-SHA status cases,
nine candidate-identity rejection cases and the existing selection/parser cases. Actual
main #33 was rejected as superseded by #34 through both selection and `recheck`; #34
still failed the AMD64 requirement. No source build was queued or modified. Synthetic
queue/state cases do not prove concurrent Pipeline execution. All 1,062 host tests,
Ruff, packaging and source/dependency gates passed.

**This candidate is not installed.** The installed job still has script SHA-256
`78192f53c275bf58d8e8def12ed097c133bcff7b7c3541b2136938bbc9a800cf`, remains disabled,
never built and pending approval. There are zero approved scripts. Keep this distinction
when checking the live definition: it intentionally differs from the new working file.
No job update, script approval, worker startup, upload or cloud mutation occurred.
See [supersession evidence](../../evidence/task-04/step-03-release-supersession.md).

## Trusted source acquisition and preparation candidate — 4 November 2026

`release-source.groovy` now acquires an immutable archive from the fixed public
`codeload.github.com/yuenshingyan/nussoc-devops-and-cloud-with-ai-capstone/tar.gz/<sha>`
endpoint. Only a lowercase 40-character commit SHA is accepted. Requests use HTTPS,
no proxy, no redirects, no added credentials, and five-second connect/read limits.
The source authority is GitHub over TLS plus the independently selected revision;
this is not independent commit-signature verification or reproducible-build attestation.

The controller uses its already-bundled Ant 1.10.18 tar reader. Nothing is checked out,
extracted, installed or executed. It hashes exactly the Python paths in the existing
scan scope and retains only `uv.lock` and `pyproject.toml` as data. It rejects path
escapes, duplicates, links, GNU sparse/unsupported entries and missing required inputs.
Git's optional global header must be the single exact commit-comment record before
any tree entry. The gzip stream is drained to check completion/checksum and trailing
content. Read and skip counters apply to compressed and expanded streams.

Explicit caps are 32 MiB compressed, 64 MiB expanded, 4,096 tree entries, 200 scanned
Python files, 1 MiB per selected file, and 8 MiB total selected bytes. The preparation
caller supplies a 120-second cooperative budget. As with the earlier helpers, blocked
I/O/DNS cancellation and the complete Pipeline wall-clock limit are not proved.

Actual acquisition of published `19b4486` read 1,492 tree entries and 245,380 selected
bytes in an observed 1.68 seconds. All 30 Python hashes and both metadata hashes matched
independent local Git objects for that exact revision. Seventeen archive fixture cases,
three stream-limit/deadline cases and four invalid-revision cases passed. Earlier failures
(unavailable Commons Compress, ambiguous Ant `file` property, then the Git global header)
are retained. The fixes use existing Ant APIs and exact format checks, not new dependencies
or relaxed source identity checks.

`release-preparation.groovy` composes selection, snapshot acquisition, revision/lock binding,
a fresh authoritative recheck, and controller-owned artifact transfer. Its returned result
still requires worker verification and does not authorize publishing. The eventual fixed
Pipeline must bundle reviewed verifier code separately; it must never execute fetched
Git source. The operation owner remains responsible for its new scratch directory.

Native composition checks rejected mismatched snapshot revision/lock and invalid build
identity. Actual #33 and #34 were rejected at selection as superseded and ARM64,
respectively, before preparation. A context-construction fixture used synthetic image
identity and is not evidence of an eligible main release. **No positive full preparation
or Pipeline run is claimed.** All 1,064 host tests, Ruff, build and source/dependency gates
passed. The installed job remains the older disabled/unbuilt/pending-approval definition;
no worker startup or cloud mutation occurred. See
[source evidence](../../evidence/task-04/step-03-release-source.md).

## Fixed verification Pipeline candidate — 4 November 2026

`release_definition.py` assembles the reviewed local helper classes and
`release-flow.groovy`, removing only the explicitly delimited legacy selection-only
body. It embeds five fixed verifier modules as bounded base64 chunks plus SHA-256 hashes.
Local source links, non-regular files, path escapes and oversized inputs are rejected.
No fetched Git code or upstream artifact code is used as executable tooling.

The candidate selects current main before requesting the release node, rechecks after
allocation, prepares authoritative inputs, confirms the original candidate, and writes
reviewed tooling with hash readback. It runs isolated Python (`-I -B`) against data-only
inputs with a private umask. The controller then checks the verifier's exact result
schema/identity/bounds and rechecks candidate eligibility. Only `verification.json` is
archived, with symlink following disabled. Cleanup targets a new random owned scratch
subdirectory, never the whole shared workspace. Ordinary archive/cleanup failures do
not hide a primary failure; interruptions propagate. Finally the candidate always stops
with `RELEASE_DISABLED_PUBLISHING_AND_DEPLOYMENT_NOT_IMPLEMENTED`.

The definition declares a ten-minute enclosing timeout and a two-minute verifier timeout,
without retries. New job XML also requires `DisableResumeJobProperty` alongside serialized
execution without aborting predecessors. These are candidate declarations: real timeout,
cancellation, restart and cleanup behavior remains unproved. A restart can leave owned
scratch; no automatic recovery or cleanup claim is made. The creation helper still refuses
an existing job and does not approve, enable or update it. For read-only checks of the
older installed source only, `verify_definition(..., resume_disabled=False)` selects the
explicit legacy schema; new creation always requires disabled resumption.

Jenkins' actual CPS transformer compiled the assembled definition. Native result checks
accepted a historical worker-result fixture and rejected 21 altered results; that fixture
is not a new freshness check. A wrong-node call was rejected. Five bundled tools were
written and hash/mode checked in a new **controller-local** temporary directory, then
removed; existing tool directories were rejected. This is not worker-remoting execution.
Fourteen plain-Groovy recording-DSL cases checked control-flow/failure handling, not the
Jenkins Pipeline engine. Two failed attempts are retained: a missing class-boundary
newline, then an observer that incorrectly tried to initialize an ownerless CPS script.
The corrected observer compiles classes without running the Pipeline body.

All 1,083 host tests, Ruff, packaging, source/dependency gates and secret-boundary checks
passed. The installed job remains the exact older disabled/unbuilt definition; its script
approval remains pending, with zero approved scripts. Scheduling v1 still excludes delivery.
No release worker startup, job update, approval, trigger, upload or cloud mutation occurred.
See [Pipeline candidate evidence](../../evidence/task-04/step-03-release-pipeline.md).

## Image-only patch planner and uploader blocker — 4 November 2026

`scripts/release_deployment.py` now provides pure planning and response-check functions,
not a network client or authorization gate. The caller must supply the independently
approved Deployment UID and full-spec SHA-256 from trusted control state, and a manifest
digest whose registry provenance has been separately verified. Computing the approval
hash from the same unreviewed GET would defeat this check. The hash encoding deliberately
matches existing checkpoint `json.dumps(spec, sort_keys=True)` UTF-8 output; non-JSON
values, coerced keys and non-finite numbers are rejected.

The fixed target is `apps/v1` Deployment `finsecure-pay` in namespace `finsecure-pay`,
with one container named `api`. The existing and proposed images must be digest-pinned
in `docker.io/yuenshingyan/finsecure-pay`. Deleting/paused or malformed targets and any
spec drift are rejected. UID/resource-version strings remain opaque and case-sensitive.
The generated JSON Patch tests UID, resourceVersion, generation, container name and old
image, then performs **one replace of the image field**. Nothing patches labels,
annotations, replicas, resources or security settings. In particular, version labels are
not silently updated; a future version-label change needs a separately agreed approach.

Response checking requires the same target/UID, a changed opaque resourceVersion,
generation incremented by one, and exactly the expected full spec. This checks an API
response's spec, not a completed rollout, readiness, stable managed metadata or HTTP smoke.
A mismatch can describe an already-applied write: stop for inspection, never automatically
rollback. An unchanged image is rejected, not interpreted as proof of previous success.
A conflict must not automatically re-read/rebase/retry. No executor implements these actions yet.

All 57 planner cases and all 1,140 host tests passed, together with Ruff, packaging,
source/dependency and secret-boundary checks. One actual read-only Deployment GET matched
the previously reviewed UID/spec hash. Its patch and response cases used a **synthetic
registry digest entirely in memory**; no PATCH or server dry-run was sent.

**Uploader policy blocker:** the existing pinned crane binary reports `v0.22.1`, and its
`push --help` advertises no retry-disable flag. Those commands ran in temporary, removed,
network-disabled/credential-free containers, not the stopped release-agent service.
Version-tagged upstream `pkg/v1/remote/options.go` enables retry transport/default backoff;
`pkg/v1/remote/write.go` wraps blob and manifest upload paths in `retry.Retry`. This is a
source review, not registry fault injection. Omitting Jenkins `retry` does not disable
these internal retries on selected transient failures. At that checkpoint the original
no-automatic-retry policy remained in force and upload was not wired. The subsequent
explicit approval and bounded-command verification below resolve the policy choice,
not the still-pending production uploader integration.
See [planner and retry evidence](../../evidence/task-04/step-03-release-deployment.md).

## Approved crane retry exception and bounded execution — 4 November 2026

The user approved retaining crane with bounded internal retries rather than building a
custom registry client. **Only pinned crane's internal retries are permitted**, within the
remaining ten-minute release budget. No Jenkins/shell retry loop, command relaunch,
automatic Kubernetes patch retry/rebase, or automatic rollback is authorized. A nonzero
exit, output limit or timeout stops delivery for inspection: an external write may already
have been accepted. No fixed global HTTP-attempt count is asserted across all client paths.

`scripts/release_command.py` runs one fixed administrator-owned argv, without a shell,
under a caller-owned worker-local monotonic deadline no more than 600 seconds away.
The caller must use the remaining release budget, not restart it for each command or pass
another machine's monotonic timestamp. Both pipes are drained with a combined 1 MiB limit;
provider stderr is discarded, not logged. The owned process group is killed and reaped on
exit/failure/timeout, including descendants. Stdout remains bounded, untrusted data for
subsequent validation. The helper does not authorize a release, create credentials, or
implement the uploader. Real Jenkins cancellation/restart behavior remains pending.

Actual crane 0.22.1 fault injection ran in a temporary, network-disabled, credential-free
container against a synthetic loopback registry. One invocation made three POST attempts
under HTTP 503 responses, then exited nonzero after about 4.17 seconds. A second invocation
with a 0.8-second budget made one POST and was stopped after about 0.81 seconds. These are
observations for this fixture, not a universal attempt count or wall-clock SLA. No external
registry was contacted and no application image was executed. The first fixture used an
outer-gzipped tar and failed with `unexpected EOF` before registry requests; switching only
the synthetic fixture to an uncompressed Docker tar reached the intended fault path.
Production artifact preparation must explicitly handle this format without rebuilding or
changing the verified image; it is not implemented by this probe.

All 24 command tests and all 1,164 host tests passed, along with Ruff, build, existing gates
and secret-boundary checks. LOW findings increased from 43 to 45: Bandit B404/B603 report
subprocess import/invocation. They remain visible, without suppression; no blocking findings
and 15 clean runtime dependencies. Failed fixture/diagnostic attempts remain retained.

The user reports remote pushes unavailable. No Git push was attempted and no cause is
assumed. Do not replace authoritative main/SCM checks with local fixtures to bypass this
blocker. Local checks cannot establish a genuine automatically triggered release.
The existing disabled job, script approvals, scheduling policy and cloud remain unchanged.
See [retry evidence](../../evidence/task-04/step-03-release-retries.md).

## Verified crane input preparation — 4 November 2026

After the user's explicit push request, feature branch `task-04/step-03-container-delivery`
was published through `0ac68c1`, with the remote SHA verified. This resolves that feature-
publication attempt, not main merge or normal SCM release eligibility. Main remains at
`19b4486`/#34 ARM64; no authority check is replaced with a local fixture.

`scripts/release_input.py` now materializes the exact already-gated compressed artifact as
`image.tar` in a caller-owned private directory. It requires the expected compressed SHA-256,
canonical private owned paths, a regular single-link private source and a worker-local
remaining deadline. Both compressed and expanded tar limits are 64 MiB. Bytes are streamed
through gzip checksum/completion checks, hashed, and checked for source mutation; no tar
members are extracted to the filesystem and no image is rebuilt or executed. Output is
created exclusively with mode 0600. Existing files/links are not overwritten or removed;
new partial output is removed on failure, or a safe cleanup-failure note preserves the
primary error. Full image/gate/eligibility verification remains a prerequisite, not a
claim made by this materializer.

Actual pinned crane checked the retained manual AMD64 candidate in an isolated no-network,
no-credentials container. Compressed input was 21,435,786 bytes; prepared tar 21,542,912
bytes. `crane validate --tarball` ran without `--fast`; local `crane digest --tarball` also
passed. An independent Docker-manifest reconstruction from the same tar config and all
nine compressed layer blobs matched crane's digest. This confirms format/byte correspondence,
not a fresh scan, normal-main eligibility, application execution or registry publication.

The local crane manifest digest is
`sha256:a5fc5aad54f4aa7d8a93154f2c63b704bbde36a8fb552547ac7ccc3c39ff4cb0`;
the exported OCI manifest remains
`sha256:27ee6d5d4d5a4af23079d2310ca208c5bb4bd6989231fb858934ff9bfb791099`.
They are different representations of the verified config/layer bytes, **not interchangeable
registry evidence**. Future push/readback must verify the actual published manifest.

All 28 input cases and 1,192 total host tests passed, along with Ruff, packaging, existing
source/dependency gates and secret-boundary checks (45 LOW, zero blocking, 15 clean runtime
dependencies). Owned temporary data was removed. The release-agent service stayed stopped;
job definition/approval/policy and cloud remained unchanged. The helper is not yet bundled
or wired into the installed Pipeline. Host free space measured 3.6 GiB before and 2.7 GiB
at closure, while Docker backing remained 7.6 GiB; the cause of host growth is unestablished.
Review headroom before further storage-intensive execution; no shared-cache pruning was
performed. See [input evidence](../../evidence/task-04/step-03-release-input.md).

## Private registry profile and readback adapter — 4 November 2026

`scripts/release_registry.py` accepts only the trusted Docker Hub file binding supplied by
fixed controller code. `registry_profile` checks the canonical owned private single-link
binding without trimming its opaque value. It creates a private 0700 temporary directory
and mode-0600 Docker config for `https://index.docker.io/v1/`, user `yuenshingyan`. The
binding remains caller-owned and is never overwritten/deleted. Only Jenkins process-tree
cookies survive from the inherited environment; HOME/DOCKER_CONFIG/TMPDIR and PATH are
explicit. Ambient proxy, cloud auth, alternate Docker config/helpers and CA overrides are
not inherited. The token cannot already appear in inherited environment values. Profile
contents and unvalidated command stdout must never be logged. Normal/error cleanup is
verified; hard-kill/restart cleanup and credential privilege remain separate concerns.

`readback_image` performs three distinct bounded crane invocations: read the fixed
`docker.io/yuenshingyan/finsecure-pay:sha-<revision>-amd64` tag digest, then read the manifest
and config using the exact digest-pinned reference. Each gets the same worker-local
remaining deadline; there is no relaunch/retry loop. A failure stops the sequence and closes
the profile. Pinned crane internal retries remain permitted within the shared budget.
The tag observation is point-in-time, not server-enforced tag immutability.

The trusted expected digest must come from local crane interpretation of the already-gated
archive, and expected config ID/revision from the original verified candidate—not from the
registry response. Raw manifest/config bytes are hashed without trimming/reformatting.
Crane v0.22.1's [digest command](https://github.com/google/go-containerregistry/blob/v0.22.1/cmd/crane/cmd/digest.go)
prints a newline; its [manifest](https://github.com/google/go-containerregistry/blob/v0.22.1/cmd/crane/cmd/manifest.go)
and [config](https://github.com/google/go-containerregistry/blob/v0.22.1/cmd/crane/cmd/config.go)
commands print raw bytes without adding a newline. Source inspection established this CLI
contract; real registry transport has not yet been exercised here. Strict JSON checks reject
duplicates, malformed/foreign descriptors, excess bounds and wrong config identity/platform/
user/revision. This reads manifest/config, not every remote layer blob; rollout and smoke
checks remain necessary. Successful readback still returns `publishing_authorized:false`.

All 67 focused and 1,259 total host cases passed, with Ruff/build/security/secret boundaries
(45 LOW, zero blocking, 15 clean dependencies). Actual pinned crane resolved a **synthetic**
credential from the profile with external networking disabled; no raw credential result was
published. Normal/error cleanup and borrowed-binding preservation passed. Small retained
local config/manifest fixtures passed, but were **not registry responses**. The integrated
three-command adapter used mocked process boundaries in tests. No real registry credential use,
upload, fresh image scan, application execution or Pipeline execution is claimed.

Installed job/approval/scheduling and cloud stayed unchanged. No large archive copies or
image builds occurred. Host storage nevertheless fell from 2.7 to 1.8 GiB; Docker backing
remained 7.6 GiB. Host VM/swap currently occupies 5 GiB, but there is no causal baseline.
No caches/volumes/diagnostics were pruned. Review headroom before storage-intensive work.
See [registry evidence](../../evidence/task-04/step-03-release-registry.md).

## Publication primitives — 4 November 2026

`scripts/release_publication.py` separates `publication_preflight` from `push_prepared`.
The former rehashes the exact private prepared tar, runs full local crane validation/digest,
and requires a successful bounded tag listing with the intended SHA tag absent. An existing
tag—including one left by an earlier uncertain publication—requires manual inspection.
It is not treated as an automatic retry/resume opportunity.

The fixed controller must first independently verify the archive/config/revision binding,
then run preflight, then recheck the **original candidate immediately before the write stage**.
`push_prepared` rehashes the prepared tar and invokes crane push once. A failed/timed-out
push can still have accepted remote writes; stop for inspection, never relaunch or roll back
automatically. Exit-zero output is ignored as proof; the existing digest-pinned manifest/
config readback must subsequently succeed. Every command receives the same remaining
worker-local deadline. The approved internal-crane retry exception remains unchanged.

These are trusted-controller primitives, not self-authorizing APIs. Tag absence is an
observation, not an atomic reservation or server-enforced immutability guarantee against
other writers. No image is rebuilt. The installed Pipeline still does not call these helpers.
20 focused cases and 1,279 total host tests passed. Actual pinned crane read the public
repository's tag-list framing without stored credentials; no push or image readback occurred.
See [publication evidence](../../evidence/task-04/step-03-release-publication-code.md).

Approved host uv-cache cleanup recovered space to 2.9 GiB, with 2.8 GiB at closure. Docker
backing remains 7.6 GiB. No reports, diagnostics or Docker data were pruned. Do not infer
adequate headroom for all future image/DB operations from these measurements. Monitoring
volume provisioning remains conditional on explicit confirmation of sufficient trial credit.

## Remaining verification

Actual publication/readback integration/proof and deployment execution;
reviewed installation/scheduling
and actual execution of the fixed Pipeline with an eligible normal-main AMD64 build;
reviewed publication and
normal SCM AMD64 proof; real downstream triggering, serialization, timeout/cancellation
and restart behavior; immutable upload identity; deployment failure/rollout/smoke checks
and retained failure reports. Full delivery is pending until all of these run successfully.
