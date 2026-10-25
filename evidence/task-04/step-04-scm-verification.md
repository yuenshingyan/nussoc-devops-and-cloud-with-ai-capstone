# Step 4.4 — Post-merge SCM-triggered main verification

## Publication and trigger

Following approval, implementation **`2f30e7e6464b7b306a504c73cfa07a5cbdd431ba`** was
fast-forward merged and atomically published to `main` and
`task-04/step-04-failure-demonstration`. No deliberate failing demo commit was merged.
Before publication, normal CI's latest completed build was #3, its queue was empty,
main polling was `H/5 * * * *`, and the demo job was disabled.

**finsecure-ci #4** automatically detected the published implementation and completed
**SUCCESS**, verified **25 October 2026 03:26:03 UTC**. Its sole cause was
`hudson.triggers.SCMTrigger$SCMTriggerCause` / “Started by an SCM change”.
The observer used only GET requests: no manual build request, forced poll, or retry.

The console records `Obtained Jenkinsfile from git`, the exact source revision above,
and execution on `finsecure-python`. Jenkinsfile SHA-256 remained
`ed0aa69e66d031096b08bd092a6368214e469100d8e5280333af0eebcd4a0576`.
This is a normal trusted-main SCM job, not an inline candidate/review job or demo job.

## Actual results

- **260 passed, 0 failed, 0 skipped**, including the 15 new observer/configuration tests.
- Locked installation, Ruff lint/format, pytest, package build, and local image export
  succeeded on the real Jenkins agent. The Starlette/HTTPX deprecation warning remains
  unsuppressed; existing BuildKit optional-feature diagnostics remain documented.
- JUnit and Coverage APIs are accessible. Executable application coverage remains
  **125/125 lines and 28/28 branch outcomes**; coverage quality gate is **INACTIVE**.
- All **17** allowlisted artifacts were downloaded. Package hashes matched the manifest;
  wheel and sdist contained the application. No stale/unexpected archive paths were accepted.
- Image archive checksum, platform, non-root user, exact revision label, unique per-build
  tag, and configuration digest matched the recorded build output.
- The isolated demo remains disabled with exactly four builds. Its passing/reverted branch
  and previous failure/recovery history are retained.

### Image export identity

| Field | Verified value |
| --- | --- |
| Archive | `images/finsecure-pay.tar.gz`, 47,141,079 bytes |
| SHA-256 | `0b3170b7a115e4db30ef41a6e1bf294c02f6204647668ce9f8e4798a7630b941` |
| Configuration image ID | `sha256:1f8b288c175656e50ed3771821261c94aca9908ffd9e19775dedc9be286de206` |
| Local tag | `finsecure-pay-ci:jenkins-finsecure-ci-4` |
| Platform | `linux/arm64` |

This follow-up **did not load or smoke-test this new image**, publish to a registry,
contact Kubernetes, or deploy anything. The earlier Step 4.3 runtime verification belongs
to its own exact image/revision; do not attribute it to this export.

## Evidence and reproduction

- [Sanitized actual console](step-04-scm/console.txt).
- [Verification, SCM cause, and all artifact hashes](step-04-scm/verification.json).
- [JUnit counts](step-04-scm/junit-api-summary.json) and [Coverage API](step-04-scm/coverage-api.json).
- [Pre-publication baseline](step-04-scm/before.json).
- [Executed GET-only observer](step-04-scm/check-main.py.txt), run with:
  `PYTHONPATH=ops/jenkins uv run --locked python reports/check-step44-main.py`.
- [Original real failing-test/recovery demonstration](step-04-trigger-gate.md).

The observer allowed 20 minutes, rejected extra builds rather than selecting a successful
retry, and validated the expected revision before accepting results. It downloaded artifacts
to ignored `reports/step44-main-4/`; binary artifacts and raw generated XML are not committed.
Known live credential values were checked privately before export. The console is sanitized
and trailing whitespace normalized; no credentials, Jenkins-home export, or private keys
are included. The [local build URL](http://127.0.0.1:8080/job/finsecure-ci/4/) requires this
machine and authentication, not an externally hosted evaluator service.

**Status:** the approved local Step 4.4 subset is reviewed, merged, published, and verified.
This evidence follow-up is documentation-only, not the source revision tested by build #4.
Full registry/deployment blocking, deployed-image continuity, release-credential isolation,
and cloud rollout/rollback remain pending. No Step 5 implementation has started.
