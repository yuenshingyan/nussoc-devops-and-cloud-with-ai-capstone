# Step 4.3 — release-worker and credential checkpoint

## Outcome and scope

4 November 2026, final state observed at **03:31:33 UTC**. Work is on
`task-04/step-03-container-delivery`, based on deployer checkpoint `52f0cb4`.
Implementation revision is recorded by this file's Git history; source hashes are
in the adjacent bundle. Review/merge/publication remain pending.

- Built and exercised the separate ARM64 release worker, with pinned image/tool inputs.
  It has crane, kubectl and standalone ADC authentication, not the Google SDK or a
  personal login. [Tool output](step-03-release-agent/tool-versions.txt) and
  [local image identities](step-03-release-agent/images.json) are retained.
- Recreated the idle controller with the additional node definition. Existing source
  agent/history, notification bindings and all **73 plugin versions** were preserved.
- Created a separate remoting-secret volume and imported the two existing private files
  into the release folder. A synthetic file round trip/removal preceded real imports.
  Private hash comparisons matched; `finsecure-ci` lookup was denied. No token/key
  creation, replacement or rotation occurred in this checkpoint.
- Actual manually triggered `finsecure-release/verify-boundaries` **#4 SUCCESS** used
  both Jenkins file bindings on the release worker. Registry pull/push token scope and
  the existing 0.3.0 digest were verified **without upload**. The deployer read two
  available replicas and was forbidden to list Secrets. Both bound files were removed,
  private client state cleaned and workspace deleted. Three sanitized reports archived.
- Existing and new read-only operator boundary checks passed while the worker was
  online. Runtime mounts, privileges, resources, remoting identity and known-secret
  absence from arguments/environment were checked. Folder scope is not admin isolation.
- **936 host tests**, Ruff lint/format and wheel/sdist build passed. The source gate
  passed: **43 LOW, 0 MEDIUM, 0 HIGH** Bandit findings; all **15 runtime dependencies**
  audited with no vulnerabilities. Bandit exits 1 for retained LOW findings; the existing
  gate correctly accepts them. No suppression or threshold change was introduced.

This is **not** an automatic SCM run, AMD64 CI artifact build, registry push, deployment
or cloud release-gate demonstration. The release-worker image itself has not received
an image vulnerability scan. Current application image and normal SCM build #34 remain
unchanged; host tests here must not be attributed to #34.

## Retained failures and corrections

1. Diagnostic **#1 ABORTED**: the initial 64 MiB temporary filesystem put the node below
   Jenkins' existing 1 GiB free-space threshold. The Pipeline waited before any credential
   binding. Its first observer timed out and disabled the job but did not stop the waiting
   build; an explicit owned-build stop then cleared the queue. Temporary storage moved
   to its own disk-backed volume; the monitor threshold was not lowered.
2. Diagnostic **#2 SUCCESS** proved initial bindings. A subsequent host source scan
   blocked B108 on the hardcoded temporary-directory path. That blocked report and
   exact earlier probe source are retained. Client state moved inside the job workspace
   so workspace cleanup also owns it.
3. Diagnostic **#3 FAILURE** rejected a freshly created client directory. A read-only
   diagnostic identified `UNSAFE_CLIENT_DIRECTORY`; a separate live metadata check
   observed UID/owner 1000, a directory rather than symlink, and mode **02700** inherited
   from the workspace. The initial standalone diagnostic had an argv setup error before
   authentication; correcting its argv produced the retained failure code. The caller
   now explicitly clears inherited bits only on its new directory. Strict validation of
   supplied directories remains unchanged. A real-filesystem regression test reproduces
   inherited setgid and verifies cleanup. Known failure codes are allowlisted; unknown
   provider details remain hidden. Corrected Jenkins **#4 passed**.
4. The first new operator boundary check could not use Alpine's incompatible `ps`
   options. Its failure is retained. The checker now reads Linux proc arguments and
   environment, tolerates only processes disappearing during inspection, and rejects
   permission/format failures. Regression and actual checks passed.

Initial lint/format errors were corrected before live execution. Failed attempts were
not relabelled or removed; each subsequent diagnostic followed a specific correction,
not an automatic retry policy.

## Safe stopping point and remaining boundary

**EXCLUSIVE labels do not restrict which jobs may request a node.** Folder credential
scope prevents direct lookup from the source job, but cannot alone prevent a different
Pipeline from leaving code on this worker to observe a later credential binding.
A trusted-job scheduling guard and actual negative scheduling tests remain required.

Consequently, after verification the diagnostic job was disabled and the idle release
worker **stopped with SIGTERM, exit 143**. No OOM; queue empty; source worker remained
online. Volumes/credentials are retained, not pruned. There is no production release
job. Do not restart for release use until scheduling restrictions and trusted-main
artifact selection are reviewed and verified. This is not a complete cross-job sandbox.

The final read-only cloud snapshot matched the deployer checkpoint: same Deployment
UID, generation 1, spec hash and two Ready Pod UIDs; two available replicas, public
health **200**. No cloud provisioning, image upload or Deployment mutation was attempted.
Host free storage was about **4.4 GiB**, Docker backing storage **8.8 GiB**; these are
separate observations, not storage quotas. No cache or evidence was pruned.

## Evidence and reproduction boundaries

[Bundle](step-03-release-agent/) contains final state, online boundary checks, all four
Jenkins diagnostic outcomes, sanitized reports/consoles, source gate reports, exact
credential-free probe harnesses and source hashes. Host paths are sanitized where
present. [SHA256SUMS](step-03-release-agent/SHA256SUMS) covers bundle files. Raw private
SDK/key/import material remains outside Git; do not export it.

Read-only checker commands and implementation details are in the
[runbook](../../docs/runbooks/cloud-delivery.md#release-worker-and-credential-checkpoint--verified-worker-stopped).
The release checker intentionally fails while the worker is stopped. Historical
bootstrap/probe scripts mutate local Jenkins state: do not rerun them as verification.
Next work remains inside Step 4.3: scheduling protection, trusted-main gated AMD64
artifact selection, immutable upload and deployment with explicit operational budgets.
