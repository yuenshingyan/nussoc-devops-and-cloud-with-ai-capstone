# Step 4.3 — Local rootless image builds (partial delivery step)

Historical pre-merge checkpoint: the local subset was subsequently approved, merged,
and published as `ab538a2`. Normal SCM build #2 passed 245 tests and produced a separately
smoke-tested image; see the [post-merge follow-up](step-03-scm-verification.md).
Pending-SCM statements below describe the earlier checkpoint, not current status.

## Approved scope and provenance

- Branch: `task-04/step-03-container-delivery`, based on reviewed/published `d492a79`.
- Verified **25 October 2026 UTC**, on local Docker Desktop/Linux ARM64.
- User approved a separate rootless builder, builder-only security exceptions, and local
  image build/export verification. **No registry credentials, image publishing, Kubernetes
  deployment, or cloud resources were authorized or introduced.**
- Candidate Jenkinsfile SHA-256:
  `ed0aa69e66d031096b08bd092a6368214e469100d8e5280333af0eebcd4a0576`.
- Exact checkout in both review jobs:
  `d492a7902ad58891859911e8416befb50bd2cb64` (published `main`).
- The success review executes the unchanged candidate body, preceded only by an explicit
  pinned `scm` binding. It is **not a Jenkinsfile loaded from Git**. The ordinary SCM job
  will gain the image stage only after approved merge/publication.
- Application source, dependencies/lock, application Dockerfile, Kubernetes manifests,
  and existing registry release tags are unchanged. No Python dependency was added.

This completes the tested **local subset**, not Step 4.3's full publish/deploy requirement.
See the [operational/security contract](../../docs/runbooks/local-image-builder.md).

## Builder boundary: actual checks

BuildKit/buildctl **0.34.1**, revision `f5b59a1f2fb25a0cb7072c398cab9aed7835da4e`, comes
from the pinned official rootless index:
`sha256:f68752a5a94acfcdad2d07867b7075601a421638e17fc5f28efc1c814d0c4f89`.

| Component | Actual local image ID | Boundary |
| --- | --- | --- |
| Controller | `sha256:ca8fcd71b20493a8bce991d61d25aea603c78be9ca73b999064f01d28cda6e3c` | Unchanged; zero build executors; original privilege restrictions |
| Python agent | `sha256:6f9da801bbef40599ed1b14316f7d4835c22b9270a98199639eee88a0de62be2` | Adds buildctl and read-only named builder-socket mount; no Docker CLI/socket |
| Rootless builder | `sha256:126890c1d9e4a80cc14a2b9c9257d0e65aacde6b30a80886b4270fb87d3f960f` | Own bridge, socket/cache volumes only, no Jenkins credentials/home/workspace |

Actual runtime checks confirmed non-privileged containers, no host bind mounts, one
CPU/1 GiB limits per service, and no OOM. Controller/agent retain dropped ALL capabilities
and no-new-privileges. Builder drops outer capabilities except SETUID/SETGID, permits its
mapping helpers, and uses the approved unconfined seccomp/AppArmor/unmasked-proc policy.
These exceptions are not applied to the controller or agent.

The daemon's actual outer UID/GID are **1000**, with user-namespace root mapped to UID
1000 and subordinate IDs starting at 100000. Its full capability mask **inside its own
user namespace** is not a claim of host-root privileges or zero capabilities. The socket
directory is owner-only, mode **01700** at runtime; the agent mount is read-only but
still permits RPC requests. No builder TCP/host port or host PID mode is configured.

Worker inspection confirmed **native snapshotter** and **process sandbox enabled**;
`--oci-worker-no-process-sandbox` was not used. The worker's `network: host` label is
relative to the builder container, which uses a separate Docker bridge—not host networking.
This remains trusted-source-only infrastructure, not isolation for hostile PRs.

## Real candidate pipeline results

| Check | Success review | Post-test failure probe |
| --- | --- | --- |
| Job, build | `finsecure-ci-review-success-20261025015653`, #1 | `finsecure-ci-review-failure-20261025020023`, #1 |
| Jenkins result | **SUCCESS** | **FAILURE**, intended exit 37 |
| Source/agent | Published revision above, `finsecure-python` | Same |
| Locked dependencies, Ruff | Passed | Passed |
| Tests and published JUnit | **230 pass / 0 fail / 0 skip** | Same, then shell failure inserted |
| Application coverage | 125/125 lines, 28/28 branch outcomes | Same, still published on failure |
| Packages | Wheel/sdist archived and downloads verified | Package stage skipped |
| Image | Real Dockerfile build, compressed archive exported/archived | Image stage skipped; no image files/reports |
| After verification | Job disabled, history retained | Same |

Coverage quality gates remain `INACTIVE`; no threshold was invented. The known
Starlette/HTTPX deprecation warning remains visible. The failure probe is **not** a real
failing-test, vulnerability-gate, or publishing/deployment-blocking demonstration.

The branch adds **15 operational regressions**: 13 archive-inspection cases and two
builder-volume ownership cases. The host suite passed **245** tests; those new cases
were not in the published-source checkout used by these pre-merge jobs.

## Exported image and real runtime smoke check

- Archive: `images/finsecure-pay.tar.gz`, **47,140,973 bytes**.
- Archive SHA-256:
  `184f9ba8a9d856b277b16133193b70a0fd8196b321c720ad5c6582f00433baa0`.
- Local tag: `finsecure-pay-ci:jenkins-finsecure-ci-review-success-20261025015653-1`.
- Configuration digest / loaded image ID:
  `sha256:26a06f2c8e5d217bf00579b94d7b6811a4e420930da7aeeafb03da46ef7c549d`.
- Platform: **linux/arm64**; revision label matches the exact checkout above.

The downloaded checksum matched the pipeline manifest. Archive inspection verified one
expected tag, platform, non-root configuration, source label, and configuration digest
against BuildKit metadata, without extracting files. The host operator verified the tag
was unused, loaded that downloaded archive, and checked its actual Docker image ID.
The pipeline itself has no Docker daemon access and does not perform this host-side load.

Running `scripts/smoke_test.py --image <that-image-id>` then confirmed:

- PID 1 UID/GID **10001:10001**, read-only root, dropped ALL capabilities,
  no-new-privileges, bounded temporary filesystem, loopback-only test port.
- `/health` returned 200; valid transaction returned 200/accepted; business rejection
  returned 200/rejected; malformed input returned sanitized 422.
- Clean exit **0**, no OOM, and the smoke container was removed.

The local image and archived/downloaded binaries remain available for review, not in
Git. No AMD64 build/runtime claim is made for this candidate. This is not an automated
CI deployment/smoke stage, signed attestation, or reproducible-build guarantee.

## Cancellation, restart, and local verification

A separate synthetic RUN printed its start marker and began a 120-second sleep. GNU
`timeout` interrupted its build client after 10 seconds, returning **124**; BuildKit
reported cancellation, and no probe process remained. Its temporary context was removed.
The builder was then restarted while Jenkins was idle: worker/cache identity survived,
the agent could reconnect through the socket, and repeated bootstrap preserved the admin
password, agent secret, and existing normal SCM job history. No volumes were pruned.

Host checks passed: locked Ruff lint/format, **245 tests**, application coverage,
wheel/source packaging, and Compose configuration validation. Live-credential scans,
configuration hashes, Markdown links, and whitespace are checked before commit.

### Corrections and remaining diagnostics

- Initial creation rejected `systempaths:unconfined`; the supported `=` spelling fixed it.
- The initial health probe rejected `--timeout=5s`; buildctl requires integer seconds.
  Its connection timeout is not a build deadline; the pipeline uses an independent
  nine-minute GNU timeout inside a ten-minute image-stage limit.
- Runtime inspection needed `CAP_` capability prefixes, empty masked/read-only path
  lists for the consumed systempaths option, and BuildKit's sticky directory bit.
  Assertions were corrected; privileges were not broadened to make checks pass.
- BuildKit reports missing unused CDI directories, unavailable optional fsverity, and
  skipped containerd worker/default-worker notices. OCI/native builds worked. These
  diagnostics, plus existing Jenkins/Starlette warnings, were not suppressed.
- The pre-existing Jenkins containers were stopped when work resumed; bootstrap reused
  their persistent state and restored service. No claim of uninterrupted uptime is made.

## Evidence

- [Success console](step-03-local/success-console.txt),
  [success verification](step-03-local/success-verification.json).
- [Failure console](step-03-local/failure-console.txt),
  [failure verification](step-03-local/failure-verification.json).
- JUnit API summaries: [success](step-03-local/success-junit-api-summary.json),
  [failure](step-03-local/failure-junit-api-summary.json).
- Coverage APIs: [success](step-03-local/success-coverage-api.json),
  [failure](step-03-local/failure-coverage-api.json).
- [Image build log](step-03-local/image-build.txt),
  [BuildKit export metadata](step-03-local/buildkit-image.json),
  [source/tag/platform metadata](step-03-local/image-metadata.txt),
  [archive SHA-256](step-03-local/image.sha256).
- [Host image load](step-03-local/image-load.txt),
  [actual runtime smoke results](step-03-local/image-smoke.json).
- [Runtime inventory](step-03-local/runtime.json),
  [daemon identity and namespace mapping](step-03-local/builder-identity.txt),
  [worker](step-03-local/builder-workers.txt), [cancellation](step-03-local/cancellation.txt).
- [Infrastructure image build](step-03-local/infrastructure-build.txt),
  [upstream index](step-03-local/upstream-image-index.txt),
  [initial creation error](step-03-local/initial-container-creation-error.txt),
  [corrected start](step-03-local/builder-start.txt), [host checks](step-03-local/local-checks.txt).
- [Configuration hashes](step-03-local/configuration-sha256.txt),
  [executed runtime harness](step-03-local/check-runtime.py.txt), run from the repository
  root with `PYTHONPATH=ops/jenkins uv run --locked python reports/check-step43-runtime.py`.

Curated host logs replace the repository prefix with `<repository>` and trim trailing
whitespace. No image/package binaries, credentials, or raw Jenkins home are committed.

**Local-subset review gate fulfilled:** approved merge/publication and the normal
SCM-loaded image/runtime verification are recorded in the follow-up above.
Registry publication and managed-cluster delivery remain separately pending.
