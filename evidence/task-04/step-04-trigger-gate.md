# Step 4.4 — SCM-triggered real pytest failure and recovery (local subset)

> Historical pre-merge checkpoint. Implementation `2f30e7e` was subsequently approved,
> merged/published, and verified through automatic main build #4 (260 tests).
> The [post-merge evidence](step-04-scm-verification.md) supersedes the pending-review
> statements below, without changing this demo's recorded revisions or results.

## Scope and provenance

Verified **25 October 2026 UTC**. Implementation branch:
`task-04/step-04-failure-demonstration`, based on reviewed main
`f167a76582bcad3b0ed116dc0099968494f5ccf5`.

The user explicitly approved public controlled commits on the isolated
[`demo/step-04-04-ci-gate`](https://github.com/yuenshingyan/nussoc-devops-and-cloud-with-ai-capstone/tree/demo/step-04-04-ci-gate)
branch. Those commits were published; **the implementation branch is not yet merged or
published**. Main stayed at the reviewed revision throughout this demonstration. Neither
main nor the implementation branch contains the demo test or deliberately failing commit.

All four demo revisions have the identical, reviewed Jenkinsfile SHA-256:
`ed0aa69e66d031096b08bd092a6368214e469100d8e5280333af0eebcd4a0576`.
There was no inline candidate wrapper, injected exit code, or altered pipeline. Each
build loaded Jenkinsfile from Git and checked out its exact recorded revision.

## Actual sequence

Job: **finsecure-ci-gate-demo**, separate from normal main CI.

| Build | Published revision | Trigger | Actual test result | Downstream result |
| --- | --- | --- | --- | --- |
| 1 | `2e0d9cd` | Manual baseline only | 245 pass, 0 fail/skip | Packages and image export succeeded |
| 2 | `847a19d` | **SCM change** | 246 pass, 0 fail/skip | Packages and image export succeeded |
| 3 | `7151c5b` | **SCM change** | 245 pass, **1 fail**, 0 skip | **Package and Local image export skipped** |
| 4 | `ce60427` | **SCM change**, after revert | 246 pass, 0 fail/skip | Packages and image export succeeded again |

Full hashes and subjects are in [demo-commits.txt](step-04/demo-commits.txt).
Builds 2–4 each report exclusively
`hudson.triggers.SCMTrigger$SCMTriggerCause` / “Started by an SCM change”. They were
observed through API GETs only: **no manual build request, forced SCM poll, or retry**
was used for those three builds. The initial manual build is not automatic-trigger proof.
The existing `H/5 * * * *` polling schedule detected each separately pushed revision.

The added test used the existing FastAPI client fixture to call `/health`. Its passing
expectation was `{"status": "healthy"}`. The deliberately failing commit changed only
that expectation to `{"status": "intentional-failure"}`; application code stayed unchanged.
See the [exact failing diff](step-04/intentional-failure.diff).

## Gate and artifact checks

- Failed build #3 reached pytest, not merely a lint or shell failure. Its unique failing
  testcase was **test_ci_demo_health_contract** and pytest exited **1**.
- JUnit and Coverage APIs remained accessible after failure. Application coverage was
  still 125/125 lines and 28/28 branch outcomes; no coverage threshold was introduced.
- The failure console explicitly records both downstream stages skipped. Exactly seven
  diagnostic/test report files were archived: **no wheel, sdist, image archive, package
  manifest, or image-build output** was present in failed build #3.
- Successful builds each exposed all 17 expected artifacts. Downloaded package/image
  hashes matched their manifests. Image archive configuration matched the expected
  ARM64 platform, revision label, per-build tag, and non-root identity.
- Build #2's previously archived image was downloaded again after the failure/recovery
  and retained its original SHA-256. This proves previous artifact preservation, **not**
  that a deployed service/image remained unchanged: no service is deployed by this pipeline.
- Build #4's source tree exactly matches the passing build #2 tree. The deliberate failing
  expectation was reverted, rather than deleted from history or hidden through retries.

## Normal CI, restart, and cleanup

Scheduling is in trusted Job DSL, not Jenkinsfile. Normal `finsecure-ci` polls trusted
main every hashed five minutes; `finsecure-checkout` is now a **manual** diagnostic.
The diagnostic verifier was updated and run successfully against the unchanged main.

Normal CI also produced **build #3 SUCCESS**, with 245 tests and an SCM cause, after it
detected main's earlier published advance to `f167a76`. This separate observation is
not presented as a fourth newly pushed demo change. See its
[actual console](step-04/main-auto-console.txt).

After recovery, the demo job was disabled and its four builds/artifacts retained. Its
public branch head remains `ce60427af470c2a1bef0e71776ca3ee9bfe09d83`, with a passing test.
The clean temporary Git worktree was removed without force. Neither the demo branch nor
its failing history was merged into the baseline; retain the branch for reviewed evidence.

A real idle controller restart and bootstrap verified:

- Main polling persists; checkout stays manual; demo stays disabled with four builds.
- Admin password, agent secret, and existing build history are preserved.
- Controller has zero executors; the one-executor agent is online.
- All **73** existing plugins match their pins and are active/enabled.
- No privileged container or host bind mount was added; services were running without OOM.

Controller image ID is
`sha256:2ad1f02e551217828aa245c96367c7c7bc7847f9ae56a97b1c9d6cd56aabb93f`.
Agent and builder image IDs are unchanged from Step 4.3; see [runtime.json](step-04/runtime.json).
No new plugin or Python dependency was installed. Existing Jenkins/BuildKit diagnostics
remain documented; the Starlette/HTTPX deprecation warning was not suppressed.

## Local verification and evidence

**260 host tests passed**, including 15 new regressions for cause classification, exact
JUnit counts, isolated branch selection, and rejection of unexpected repositories or
credential references. These new tests were not present in the frozen demo/main checkouts.
Ruff lint/format, application coverage, wheel/sdist packaging, and Compose validation passed.
Configuration hashes, changed-document links, known live credentials, and whitespace
are checked before commit. No numerical coverage acceptance gate was invented.

- Consoles: [seed #1](step-04/build-1-console.txt), [pass #2](step-04/build-2-console.txt),
  [failure #3](step-04/build-3-console.txt), [recovery #4](step-04/build-4-console.txt).
- Verification/cause/artifact hashes: [#1](step-04/build-1-verification.json),
  [#2](step-04/build-2-verification.json), [#3](step-04/build-3-verification.json),
  [#4](step-04/build-4-verification.json).
- JUnit summaries and Coverage APIs for all four builds are in [step-04/](step-04/).
- [Controller build](step-04/controller-build.txt), [manual checkout diagnostic](step-04/checkout-diagnostic.json),
  [host checks](step-04/local-checks.txt), [configuration hashes](step-04/configuration-sha256.txt).
- [Executed runtime/restart harness](step-04/check-runtime.py.txt), run from repository
  root with `PYTHONPATH=ops/jenkins uv run --locked python reports/check-step44-runtime.py`.
- [Runbook and observer commands](../../docs/runbooks/ci-trigger-gate.md).

Local authenticated [demo job](http://127.0.0.1:8080/job/finsecure-ci-gate-demo/),
[failed tests](http://127.0.0.1:8080/job/finsecure-ci-gate-demo/3/testReport/), and
[recovered build](http://127.0.0.1:8080/job/finsecure-ci-gate-demo/4/) require this machine;
they are not externally hosted evaluator URLs. Binaries/raw generated XML remain in
Jenkins/ignored local storage. Curated host logs replace the repository path with
`<repository>` and normalize trailing whitespace; no raw credentials/home exports are included.

**Review gate:** approve before merging/publishing the implementation. Then observe the
SCM-triggered main build with the new suite (currently 260 tests). Full publishing/deployment
blocking, deployed-image continuity, release-credential isolation, security scans, and
cloud recovery remain pending. There are no registry/cloud credentials or delivery stages
here; their absence is not evidence of a future credential-isolation policy being enforced.
