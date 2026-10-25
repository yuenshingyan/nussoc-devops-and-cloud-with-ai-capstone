# SCM triggering and real test-failure blocking — Step 4.4 local subset

Approved scope: application CI polling plus controlled public commits on the isolated
`demo/step-04-04-ci-gate` branch. Never merge that branch/history into `main`. No registry
credentials, image publishing, cloud deployment, or untrusted PR/fork execution is added.

## Ownership and timing

- `finsecure-ci` selects trusted `main`, polling `H/5 * * * *` (hashed five-minute schedule).
  Scheduling lives in administrator-owned Job DSL, not Jenkinsfile: inline candidate
  jobs stay manual, and startup seeding restores the application's schedule.
- `finsecure-checkout` becomes a manual setup diagnostic to avoid duplicate polling.
- `finsecure-ci-gate-demo` selects only the approved demo branch of this same repository.
  Its Jenkinsfile is unchanged from reviewed `main`. First create it without polling and
  run exactly one manual baseline to establish SCM state; only then enable the same poll
  schedule. Subsequent builds must have `SCMTriggerCause`, not manual/timer-only causes.
- Wait up to **20 minutes** per source change, including poll detection, queue, and build.
  The existing 15-minute pipeline/10-minute image-stage/9-minute build-client bounds stay
  unchanged. No build/test retries or requests to force polling are permitted as proof.
- On a timeout or client error, inspect/cancel only the owned queued/running demo build,
  revert any deliberate failing commit, then disable the demo job. Disabling alone does
  not cancel existing work. Do not silently rerun a failed build to manufacture a pass.
- One executor serializes agent work. Push each next change only after the prior build
  and evidence checks finish, so polling cannot skip/coalesce the intended revisions.
- Preserve the passing/reverted demo branch and disabled job history for review. Temporary
  Git worktree cleanup is allowed only when clean; never force removal or prune unrelated
  state. Reports/binaries stay in Jenkins/ignored storage; retain reviewed text evidence.

## Demonstration sequence

1. Seed the isolated job with published baseline source (245 tests), manually once.
2. Add a passing health-contract test only on the demo branch and push it. Wait for SCM
   polling to start a real pipeline: expect 246 passing tests, packages, and image export.
3. Change that test's expected response to `intentional-failure` and push. The API code
   remains unchanged. Expect 245 passing tests and one real pytest failure; JUnit/coverage
   remain accessible, while Package and Local image export are skipped and absent.
4. Revert that commit and push. Expect an SCM-triggered recovery with 246 passing tests
   and newly exported artifacts. Disable the demo job afterward.

`ops/jenkins/verify_trigger.py` is a read-only observer: it issues API GETs, checks the
exact revision and cause, counts, failure identity, stage skips, checksums and image
configuration. It never pushes commits, schedules builds, or forces an SCM poll. Example:

```sh
uv run --locked python ops/jenkins/verify_trigger.py \
  --revision <full-pushed-sha> --after-build <previous-number> --passed 246
# For the deliberately failing revision: --passed 245 --failed 1
```

A failed observation is not evidence of successful cleanup. Retain the failure, inspect
the actual job state, and restore the branch/job deliberately. The manual seed is never
counted as automatic-trigger proof. The isolated failure is not the earlier exit-37 probe.

## Verified results and current state

Actual runs on 25 October 2026 (each using an unchanged, Git-loaded Jenkinsfile):

| Demo build | Revision | Cause | Outcome |
| --- | --- | --- | --- |
| 1 | `2e0d9cd` | Manual seed | 245 passed; packages/image exported |
| 2 | `847a19d` | SCM change | 246 passed; packages/image exported |
| 3 | `7151c5b` | SCM change | 245 passed, 1 failed; package/image stages skipped |
| 4 | `ce60427` | SCM change | Revert recovery: 246 passed; exports restored |

The passing and reverted Git trees are identical. The temporary worktree was removed
without force; the public demo branch remains at `ce60427` for review. The job is disabled
and has exactly four builds, including the failed run. Build 2's archived image remains
available with its original checksum; this is not a claim about a deployed image.

Normal `finsecure-ci` also automatically detected the earlier published main advance to
`f167a76`: build 3 passed 245 tests with an SCM cause. This is separate from the three
explicit demo pushes; no implementation changes or failing tests were pushed to main.
A real idle controller restart restored application polling, kept checkout manual and
the demo disabled, and preserved credentials/history. All 73 existing plugin pins match.

The implementation branch adds 15 deterministic observer/configuration regressions:
**260 host tests passed**. They were not in the frozen demo checkout. Ruff, packaging,
and Compose validation passed. The existing Starlette/HTTPX deprecation warning remains
unsuppressed; existing Jenkins/BuildKit diagnostics are documented in their runbooks.

This is a preserved one-time exercise, not a command to overwrite the existing demo
job/ref. Its manual seed used `demo_job_xml()` to copy only the validated public-main
SCM definition, changed selection to the fixed demo branch, and installed no credentials
or initial trigger. After its successful seed, an authenticated job-config update added
`SCMTrigger` with `H/5 * * * *`. Builds 2–4 used no manual build or forced-poll requests.

See [curated demo evidence](../../evidence/task-04/step-04-trigger-gate.md). After approval,
implementation `2f30e7e` was merged and atomically published to main and the step branch.
Normal **finsecure-ci #4** then ran automatically with an SCM cause and passed all
**260 tests**. Its 17 artifacts were downloaded and package/image hashes/configuration
verified. The demo job remained disabled. This follow-up did not load or smoke-test the
new exported image; Step 4.3 retains its separate runtime proof. See
[post-merge evidence](../../evidence/task-04/step-04-scm-verification.md).
Full release/deployment blocking and unchanged deployed-image proof remain pending:
this local pipeline exports artifacts but does not deploy a service. No release
credentials exist here; future credential isolation still needs its own design.
