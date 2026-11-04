# Step 4.3 — fixed release selection, installed disabled

## Implemented and verified

The operator approved the fixed administrator-owned, non-sandboxed controller approach,
without worker-held Jenkins admin credentials or global sandbox relaxations. The agreed
operational direction remains serialized releases, a ten-minute overall budget, current
main SUCCESS/AMD64 artifacts, and no automatic release retries or rollback.

`finsecure-release/delivery` was created **disabled**, with no parameters or triggers,
serialized execution and the exact checked-out source-file contents. Its definition has **never
built**. Global approved script hashes were unchanged; the new script is **pending
approval**. Its administrator-level authority still requires code review before use.
The release worker remains stopped and scheduling guard version 1 still excludes this
job. No image/controller rebuild, credential import or rotation was performed.

Implemented code checks authoritative upstream cause, fixed source job/repository/main
SCM definition, completed SUCCESS, native JUnit results, Git BuildData and the current
GitHub main revision. It checks source/image summary policy, AMD64, revision consistency,
lock identity and digest shapes. Fixed report paths have one-MiB read bounds and owned
stream cleanup; malformed JSON details are replaced by a fixed error. GitHub lookup is
credential-free HTTPS with redirects/proxies disabled and five-second connect/read limits.

These are **candidate-selection checks, not full artifact authentication**. Every result
states that artifact verification is required and deployment is disabled. The Pipeline
always stops before delivery, including after a positive selection. There is no worker
allocation, credential binding, artifact transfer, registry upload or deployment command.

## Actual checks

- **975 host tests**, Ruff lint/format, wheel/sdist build and Python source/dependency
  gates passed. Bandit retained **43 LOW / 0 MEDIUM / 0 HIGH** findings; 15 runtime
  dependencies audited without vulnerabilities. No suppression or policy weakening.
- Native Jenkins compilation tested the exact Groovy source, a positive fixture using
  real candidate reports but **synthetic main authority**, **28 rejection cases**, three
  bounded-parser cases, and absent/manual-cause rejection. No Pipeline body was run.
- A simulated upstream envelope around real `finsecure-ci` **#34** exercised actual
  source-job, Git/JUnit and artifact APIs plus live main lookup. Its ARM64 artifact was
  rejected with **`RELEASE_PLATFORM_DENIED`**. This was not a genuine downstream trigger
  and does not prove an eligible production release.
- Installed definition was read back and matched: disabled, non-sandboxed, no trigger,
  serialized without aborting a predecessor, exact script hash, no build history.
  Existing source/notification boundary checks passed.

The first native observer expected JSON but received an assertion failure. A subsequent
read-only diagnostic retained the error: Git BuildData uses **`refs/remotes/origin/main`**,
not the initially assumed `origin/main`. The code now requires the observed canonical
form exactly; a regression case rejects the other spelling. No grant/gate was widened.
The initial observer failure and branch-shape diagnostic remain retained.

## Limits and remaining implementation

Do not approve/enable this incomplete definition as a release pipeline. The ten-minute
Jenkins timeout is declared, not cancellation-tested. Serialization is configured, not
demonstrated with concurrent production builds. Still required:

1. Controller-owned bounded artifact transfer; strict parsing and complete checksum
   inventory; archive/config identity and database freshness at release time.
2. Superseded-build rejection, including newer builds of the same revision, and current
   main rechecks immediately before external actions. GitHub/Kubernetes operations are
   not atomic merely because selection observed the same revision earlier.
3. Immutable upload and image-only deployment, bounded rollout/smoke handling, actual
   blocking/failure tests, and explicit script approval/scheduling update after review.
4. Reviewed publication and normal SCM AMD64 verification. Main #34 is not the manual
   961-test AMD64 candidate and is not the 975-test host result.

## Final state and evidence

Release definition disabled/unbuilt; all five diagnostic jobs disabled; queue empty;
source worker online; release worker stopped, exit 143; scheduling guard active.
Read-only cloud checks matched prior Deployment UID/generation/spec and Ready Pod UIDs:
two available replicas, public health **200**. No publication or deployment attempted.
Storage headroom remains limited; no image build or shared-cache pruning was performed.

[Bundle](step-03-release-selection/) retains installation/approval-state summary, native
checks, observed Git metadata, failed diagnostics, host/source gates, final state and
credential-free operator procedures. Private credentials/project/account identifiers are
excluded; host paths sanitized where present. Source hashes and
[SHA256SUMS](step-03-release-selection/SHA256SUMS) bind the records. Historical installers
are not verification commands to rerun against existing state.

See the [runbook](../../docs/runbooks/cloud-delivery.md#fixed-release-selection--installed-disabled-not-a-working-deployment-pipeline).
