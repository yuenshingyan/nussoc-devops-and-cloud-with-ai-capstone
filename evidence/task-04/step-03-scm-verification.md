# Step 4.3 — Approved local subset: SCM build and image verification

## Source publication

After user approval, `main` was fast-forwarded and pushed atomically with
`task-04/step-03-container-delivery` at:

**`ab538a2d67b9bd6fa5525fdf72c2236eb3cfd763`**

`git ls-remote` confirmed both published refs. This evidence follow-up changes documentation
only; the build below tested the exact implementation revision above, not this later
record's commit. The [pre-merge checkpoint](step-03-local-image-builder.md) remains historical.
No image was published to a registry and no cloud resource was created.

## Actual normal pipeline execution

- Verified **25 October 2026, 02:30:56 UTC**.
- **finsecure-ci build #2: SUCCESS**, manually triggered through the authenticated API.
- Actual job definition: `CpsScmFlowDefinition`, `*/main`, script path `Jenkinsfile`.
- Console reports **“Obtained Jenkinsfile from git”**, execution on **finsecure-python**,
  and checkout/`SOURCE_REVISION` matching the published revision above.
- Jenkinsfile SHA-256:
  `ed0aa69e66d031096b08bd092a6368214e469100d8e5280333af0eebcd4a0576`.
- Locked dependencies, Ruff lint/format, tests, packaging, and local image export passed.
- Published JUnit result: **245 passed / 0 failed / 0 skipped**. The 15 new operational
  regressions are now included, unlike the 230-test pre-merge checkout.
- Coverage: **125/125 application lines**, **28/28 branch outcomes**; quality gate
  `INACTIVE`. The existing Starlette/HTTPX deprecation warning remains visible.
- All **17** allowlisted report/package/image artifacts were downloaded. Wheel/source
  package hashes matched their manifest and expected application modules were present.

## Exported image and host-side smoke test

| Property | Verified value |
| --- | --- |
| Platform | `linux/arm64` |
| Local tag | `finsecure-pay-ci:jenkins-finsecure-ci-2` |
| Archive | `images/finsecure-pay.tar.gz`, 47,141,003 bytes |
| Archive SHA-256 | `bdc89ef132788ef415e428c199d9ece603de95501dc4bc23fab2c95a0feb02e2` |
| Configuration digest / loaded image ID | `sha256:eaca7256fb8b9d72896c8fba7a26bf0b57dbb2ae506f139201f7cc251004d45f` |
| Revision label | `ab538a2d67b9bd6fa5525fdf72c2236eb3cfd763` |

The downloaded checksum matched the pipeline manifest. Archive inspection checked the
single expected tag, platform, revision, non-root identity, and configuration digest
against BuildKit metadata without extracting files. The host operator confirmed the tag
was unused, loaded this exact archive, and checked Docker's actual image ID and label.
Jenkins still has no host Docker socket and did not perform that load.

The existing smoke verifier then ran **this image ID**, confirming PID 1 UID/GID
**10001:10001**, read-only root, dropped capabilities, no-new-privileges, bounded `/tmp`,
and a loopback-only test port. `/health`, accepted transaction, business rejection, and
malformed-input responses matched the contract. Shutdown exited **0**, no OOM occurred,
and the smoke container was confirmed removed. The local image/download is retained.

This was an **operator-side smoke test**, not a deployment stage. No AMD64 validation,
registry publication, signed attestation, or bit-for-bit reproducibility is claimed.
The builder/security boundaries are unchanged from the approved pre-merge checkpoint.

## Evidence and reproduction

- [Console](step-03-scm/console.txt), [verification and all artifact hashes](step-03-scm/verification.json).
- [JUnit summary](step-03-scm/junit-api-summary.json), [Coverage API](step-03-scm/coverage-api.json).
- [Source/tool metadata](step-03-scm/build-metadata.txt), [package hashes](step-03-scm/packages.sha256).
- [Image build](step-03-scm/image-build.txt), [export metadata](step-03-scm/buildkit-image.json),
  [source/tag/platform](step-03-scm/image-metadata.txt), [archive hash](step-03-scm/image.sha256).
- [Host load output](step-03-scm/image-load.txt), [real smoke results](step-03-scm/image-smoke.json).
- [Executed harness](step-03-scm/check-scm.py.txt), run from the repository root as
  `PYTHONPATH=ops/jenkins:scripts uv run --locked python reports/check-step43-scm.py`.
  It starts one build and loads/smokes its export; rerunning is unnecessary for inspection.
  No job reconfiguration, test retries, image publishing, or cloud commands were used.

Local authenticated [build #2](http://127.0.0.1:8080/job/finsecure-ci/2/) has
[tests](http://127.0.0.1:8080/job/finsecure-ci/2/testReport/),
[coverage](http://127.0.0.1:8080/job/finsecure-ci/2/coverage/), and
[artifacts](http://127.0.0.1:8080/job/finsecure-ci/2/artifact/).
These require the local machine/Jenkins account and are not hosted evaluator links.
Binaries/full generated XML remain in Jenkins and ignored local storage, not Git.

**Status:** the approved local Step 4.3 subset and SCM follow-up are complete. Full Step
4.3 remains incomplete until separately approved registry publishing and managed-cluster
delivery are implemented and verified. Source-triggered CI, real failing-test release
gates, security scans, and later steps are not established by this manually triggered run.
