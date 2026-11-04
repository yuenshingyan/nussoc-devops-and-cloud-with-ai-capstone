# Step 4.3 — trusted-job scheduling verification

## Result

On 4 November 2026, the controller-owned release scheduling guard was built, installed
through controller recreation, and exercised with real Pipeline queue items. This
continues `f416f7b` on `task-04/step-03-container-delivery`; implementation revision is
recorded in Git history. Review/merge/publication remain pending.

- The installed Jenkins/plugin APIs compiled the guard and passed **10 decision cases**.
  The installed Pipeline PlaceholderTask owner API was verified, not assumed from
  upstream documentation alone.
- **Five live cases** verified two allowed assignments and three denied assignments.
  Denials were observed with the target node online and idle, the real queue reason,
  and the actual PlaceholderTask owner. The denied runs never entered a worker and
  were explicitly stopped as ABORTED; this is the expected outcome, not a passing
  application build or a test/security release gate.
- **942 host tests**, Ruff lint/format and packaging passed. Source/dependency gates
  passed: Bandit **43 LOW / 0 MEDIUM / 0 HIGH**, 15 runtime dependencies with no
  vulnerabilities. LOW findings remain visible; no suppression/threshold change.
- Existing source/notification and extended release boundary checks passed. The
  extended check verified the active guard, worker constraints, remoting identity,
  retained folder credentials and denied source-job lookup.
- Main remains **#34 SUCCESS**. All **73 plugin versions** were preserved. The image
  and persisted startup-script hashes matched the reviewed source; the runtime guard
  remained active after the worker was stopped.

## Actual Pipeline cases

| Job / build | Requested node label | Observed result |
| --- | --- | --- |
| `finsecure-release/verify-scheduling` #1 | release | SUCCESS; assigned release worker, shell step ran |
| `release-scheduling-source-probe` #1 | release | JOB_DENIED; never assigned; stopped ABORTED |
| `finsecure-release/verify-unapproved` #1 | release | JOB_DENIED; never assigned; stopped ABORTED |
| `finsecure-release/verify-scheduling` #2 | python | WRONG_NODE; never assigned; stopped ABORTED |
| `release-scheduling-source-probe` #2 | python | SUCCESS; assigned source worker, shell step ran |

The root-level probe uses the same Pipeline task type as normal source CI, without
changing or triggering `finsecure-ci`. The exact `finsecure-ci` name was also checked
in the compiled decision matrix. No live probe bound registry/deployer credentials.
No production release job is in the version-1 allowlist.

## Policy and limits

`release-policy.groovy` is administrator-owned startup code copied into the pinned
controller image. It checks actual owner Job and node names; label expressions and
parameters cannot grant access. Only the two named diagnostic jobs can acquire the
release worker. Release-folder executor tasks cannot acquire other nodes. Unknown
ownership on the release worker is denied; owner-resolution exceptions return a
fixed denial. Controller flyweight orchestration remains allowed without a workspace.

The verifier requires the active version and exact allowlist. One-time worker bootstrap
now performs that preflight before Docker commands or secret-volume creation. A
regression test proves a missing policy prevents bootstrap mutations. Existing resource
replacement remains prohibited; no credentials or secret volumes were recreated.

This is not a general Jenkins sandbox or protection against administrators. Startup
script errors do not terminate Jenkins automatically. The operational rule is to stop
the release worker before controller restart/recreation and verify the active policy
before starting it. Production trusted-main selection, upstream artifact validation,
credential usage and deployment failure policy are still pending controls.

## Retained failures

- Initial controller build could not COPY the new script because the narrow Docker
  build-context allowlist omitted it. Build stopped before controller recreation.
  Added only that file to the allowlist and a regression assertion; corrected build
  succeeded without changing plugins or base-image pins.
- First probe observer used the base Compose helper to wait for the opt-in release
  service. That helper could not resolve the service. No probe jobs/builds had been
  created; the owned worker was explicitly stopped. Waiting now checks the actual
  named container/API and is inside the cleanup boundary.
- The corrected observer retained the first successful allowed run, then stopped on
  a malformed root-job creation URL. Cleanup disabled its owned job and stopped the
  worker. The corrected continuation checked existing ownership/state, preserved
  that success, and ran only the four remaining cases. No blind retry or overwritten
  build history. Initial lint formatting was also corrected before activation.

## Final state and evidence

All four diagnostic jobs (including the earlier binding job) are disabled. Release
worker stopped with SIGTERM, **exit 143**, no OOM; source worker online; queue empty.
The read-only cloud snapshot matched the preceding checkpoint: unchanged Deployment
UID/generation/spec and Ready Pod UIDs; **two available replicas**, public health **200**.
No image upload, deployment or cloud provisioning was attempted.

[Bundle](step-03-release-scheduling/) includes compiled cases, live queue observations,
consoles, failed attempts, online boundary results, host checks, image/source identities
and final state. Credential-free operator procedures are retained as historical
artifacts, not instructions to rerun mutations. Host paths are sanitized where present.
[SHA256SUMS](step-03-release-scheduling/SHA256SUMS) covers the bundle. Raw credentials,
private project/account identifiers and SDK output are excluded.

See the [runbook](../../docs/runbooks/cloud-delivery.md#trusted-job-scheduling-guard--installed-and-live-tested).
Automatic AMD64 CI, immutable upload and GKE deployment remain unimplemented.
