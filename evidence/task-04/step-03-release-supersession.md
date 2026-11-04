# Step 4.3 — Supersession and action-time recheck candidate

**Status:** verified code candidate, not installed, merged or published. Delivery remains
disabled and unbuilt. No worker startup, source build, image build, upload or cloud mutation.

## Implemented

`ops/jenkins/release-job.groovy` now requires the selected upstream build to be the
source job's latest build, with no source build queued. A newer build supersedes it
regardless of revision or outcome, including a newer failure or still-running build.
Missing/invalid ordering observations fail closed. Selection checks ordering before
reading reports and again after the remote current-main lookup.

`recheck(releaseRun, expected)` repeats full selection, including current main and native
provenance, then compares the complete original candidate map. Changed build/revision,
archive/config/lock identity, tag, missing fields or extra fields fail closed. The future
orchestrator must retain the original selection separately from verification outputs
and call this helper immediately before each external action. No such actions exist yet.
These checks cannot make Jenkins, GitHub and Kubernetes updates atomic.

## Actual verification

The exact candidate compiled and executed its helper methods against installed Jenkins
APIs, without running the Pipeline body:

- Ten build-order/type/queue rejection cases passed.
- Three synthetic newer-build cases retained the same SHA and were rejected for
  `SUCCESS`, `FAILURE` and `RUNNING` states.
- Nine candidate-map drift/missing-input cases were rejected; an unchanged copy passed.
- Existing 28 selection rejection cases, three bounded-parser cases and absent/manual
  cause checks passed. Positive selection used the previously documented synthetic
  main-authority fixture around real candidate reports; it is not real release eligibility.
- Actual main #33 was rejected as `RELEASE_SUPERSEDED_BUILD` behind #34, through both
  `select` and `recheck`, using simulated upstream envelopes around the real builds.
  Actual main #34 remained rejected as `RELEASE_PLATFORM_DENIED`.

No real queue, concurrent build or Git revision was changed to induce these cases.
Synthetic state changes are not concurrent Pipeline or downstream-trigger evidence.
The candidate source SHA-256 is
`e0d6db76457e8e654691f302f05e04e9e2a1baf491297d9526d7be7e88965ed5`.

All **1,062 host tests** passed, including two added structural wiring checks. Ruff lint,
Ruff format check, `uv build` and the existing source/dependency gates passed: 43 LOW
findings retained, no blocking source findings, 15 runtime dependencies clean. No new
dependency or security-policy exception was introduced.

## Live state and remaining work

Read-only checks verified that the installed definition is still the older exact script
from `e195899`, SHA-256
`78192f53c275bf58d8e8def12ed097c133bcff7b7c3541b2136938bbc9a800cf`.
It is disabled, never built and pending approval; approved-script count is zero.
**The working source intentionally differs from that installed definition.** No update
or approval was attempted. The release worker remained stopped, diagnostic jobs disabled,
queue empty and source worker online. Main CI remains #34 SUCCESS, not a new SCM build.
The cloud Deployment specification and Pod identities remained unchanged, with two
Ready replicas and public health 200.

Trusted production Git snapshots, integration of selection/transfer/verification/recheck,
reviewed installation and scheduling changes, publishing/deployment, and real downstream,
concurrency, cancellation and restart evidence remain pending. Storage is still low;
review headroom before any image build. See the [runbook](../../docs/runbooks/cloud-delivery.md).

The adjacent [`step-03-release-supersession/`](step-03-release-supersession/) bundle contains
native results, code hash, sanitized host output, source-gate summary and read-only
closure/approval records. Historical observer procedures are credential-free text;
`SHA256SUMS` covers the bundle. Original responses remain ignored under
`reports/release-supersession/`.
