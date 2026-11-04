# Step 4.3 — Controller transfer and independent artifact verification

**Status:** helper checkpoint verified on 4 November 2026; not merged/published and
not integrated into the disabled release Pipeline. No upload or deployment occurred.

## Actual execution

- Four native controller stream cases passed: exact-size transfer/hash, oversize rejection,
  expired-budget rejection and an empty log. The fixed transfer inventory has 21 files.
- An administrator-owned probe used Jenkins' artifact manager and remoting to transfer
  **21,615,108 bytes** from retained manual candidate
  `finsecure-ci-amd64-review-20261104041956` #1. No worker Jenkins-admin credential,
  registry/GKE binding, upstream-code execution or image execution was used.
- The existing constrained ARM64 worker independently verified all 21 file hashes/sizes,
  source hashes against exact operator-supplied Git-object snapshots, lock-bound exports,
  raw source/dependency/image gates, DB freshness and nine image layers. Expanded layer
  bytes totalled **62,625,792**. The final observation's DB age was **20,739.79 seconds**,
  within the unchanged 86,400-second policy; freshness must be checked again for a release.
- Changed report bytes were rejected. A separate **synthetic clock two days later** was
  rejected as stale. Restored inputs passed again. These are validation probes, not real
  failing downstream releases or an actual present-time stale database.
- Runtime/credential boundaries passed; the owned scratch directory was removed and
  the worker stopped normally without OOM. Queue empty; five diagnostic jobs disabled.

The inspected source is `dc7ffe5a2884f8aeb833f9befd0f1be30d608739`, archive SHA-256
`c7173b149f2821d3baba3521397eee791dd53f1b9e33c42b07a91eb2e13a0cf0`, and config ID
`sha256:d4c23d06faf317e704f3732cb8af970a7b896556d1b8e5c90ac65e3ab744ac10`.
The archive's OCI manifest digest is an **export identity, not a published registry
manifest**. This candidate remains distinct from main #34 and deployed version 0.3.0.

## Checks and retained failures

All **1,060 host tests** passed, including 85 new offline cases. Ruff lint/format and
`uv build` passed. Existing source/dependency gates passed: 43 LOW findings retained,
zero MEDIUM/HIGH source findings, and all 15 runtime dependencies clean. Jenkins and
notification secret-boundary checks passed. No new dependency or image build was needed.

The first test collection failed because repository tooling was not on pytest's import
path. The pytest configuration now explicitly includes the repository root; application
packaging/dependencies are unchanged. The first live probe then failed at Groovy
compilation: a 293,316-code-unit fixture exceeded the JVM's 65,535-unit string-literal
limit. No transfer occurred; the worker stopped cleanly. The corrected fixture uses
32,000-character chunks. Its successful probe is retained, followed by a final successful
probe using the recorded helper hashes after the DB/report-time consistency check was
added. Failed attempts were not replaced with success claims or mutation retries.

## Limits and next work

The helper code is fixed and administrator-owned. It transfers only the allowlisted
artifacts, creates the receipt itself, and never executes upstream files. The verifier
returns `publishing_authorized: false`. Its trusted control files and tooling must not
be sourced from the upstream artifact collection. The current probe supplies Git
snapshots from the operator's exact local objects; **production snapshot acquisition
and integration with authoritative selection are still pending**.

The [runbook](../../docs/runbooks/cloud-delivery.md#artifact-transfer-and-verification-checkpoint--4-november-2026)
records explicit size/expansion limits and 120-second cooperative check budgets.
Blocked-I/O cancellation, Pipeline wall-clock timeout, downstream triggering,
serialization/restart behavior, newer-build rejection (including the same revision),
action-time main checks and upload/deployment remain unverified/unimplemented as stated
there. The administrator-owned remoting probe is not a Pipeline executor assignment or
a new test of scheduling isolation.

The installed selection-only job is unchanged, disabled, pending approval and never
built; scheduling policy v1 still excludes it. Main CI remains #34 SUCCESS (781 tests),
not the 1,060-test host run or the retained 961-test manual candidate. Read-only closure
verified the unchanged Deployment specification and Pod identities, two Ready replicas
and public `/health` 200. Host storage remains low (~3.5 GiB free); no cache/volume or
retained scanner-diagnostic pruning occurred. Review headroom before another image build.

## Reviewed bundle

[`step-03-release-artifacts/`](step-03-release-artifacts/) contains sanitized results,
source-gate summary, host test/build output, recorded code hashes, fixed-input inventory,
read-only closure and credential-free historical observer procedures. `SHA256SUMS`
covers the bundle. Large original artifacts remain in retained CI/operator storage.
Historical procedures are not general-purpose installers; do not replay them against
new state or arbitrary inputs. Raw failed responses and original procedures remain
ignored under `reports/release-artifacts/`, including `first-live-attempt/` and
`first-successful-probe/`.
