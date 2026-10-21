# Step 2.3 — Versioned multi-platform registry publication

- **Date:** 2026-10-21 UTC; anonymous registry verification completed at 16:02:28 UTC.
- **Step branch:** `task-02/step-03-image-publication`.
- **Released source commit:** `dec0da00b6e19defb34001ed84fc7696bf0f8089`.
- **Repository:** [Docker Hub — yuenshingyan/finsecure-pay](https://hub.docker.com/r/yuenshingyan/finsecure-pay).
- **Visibility:** public, verified via anonymous repository metadata and registry access.
- **Purpose:** An assignment/demo release using synthetic transaction data.

## Actual preparation and publication

After the user confirmed the Docker Hub namespace and corrected the local login,
the credential-store username matched `yuenshingyan`. No password, access token,
or bearer token was printed or committed. A public `finsecure-pay` repository was
created through Docker Hub's API. The repository visibility and absence of all
four intended tags were checked before pushing; no existing release was overwritten.

Both images were built from a temporary `git archive` of the released source commit,
not the documentation working tree. Each build used the committed Dockerfile,
pinned base-image indexes, locked runtime dependencies, and the label
`org.opencontainers.image.revision=dec0da00b6e19defb34001ed84fc7696bf0f8089`.

The ARM64 and AMD64 local images were smoke-tested before being tagged and pushed.
The version and commit tags were then composed with `docker buildx imagetools create`
from the exact pushed platform digests; no post-test image rebuild was published.

## Published references

Both multi-platform tags:

```text
docker.io/yuenshingyan/finsecure-pay:0.1.0
docker.io/yuenshingyan/finsecure-pay:sha-dec0da0
```

resolve to:

```text
sha256:18397d4d8391cdfde3220222f0b5d07afa8cbc2afaf92ef8b7d2b23b6494c10c
```

| Platform | Platform tag | Registry manifest digest | Image config digest / local image ID |
| --- | --- | --- | --- |
| `linux/arm64` | `sha-dec0da0-arm64` | `sha256:0f302152c2152b6bef90665efeb861d223731a290ed6fd02ef8ae49c15ca32ce` | `sha256:42592d31c98fee276015202061fda94e41e61e060fe69b39fbac6677b599bb90` |
| `linux/amd64` | `sha-dec0da0-amd64` | `sha256:33d541d4987fddfd8e7b6dfc185db33eaca499c973d28acd5afc2cf866678e77` | `sha256:efa84869c27fbe80f684b1afb2871d714e7cfc5336cc032a5c96ab55a0ac4b4b` |

The multi-platform index contains exactly these two Linux platforms. Index,
platform-manifest, and image-config digests identify different objects; they are
not interchangeable. Use the index digest to let Kubernetes select the matching
platform while pinning the complete release.

## Execution before and after publication

| Platform | Before push | After registry pull | Execution environment |
| --- | --- | --- | --- |
| ARM64 | Passed at 15:59:41 UTC | Passed at 16:01:30 UTC | Docker Desktop ARM64 Linux VM |
| AMD64 | Passed at 15:59:44 UTC | Passed at 16:01:35 UTC | AMD64 emulation on the ARM64 host |

Each run verified:

- GET `/health`: HTTP 200, `{"status":"healthy"}`.
- POST `/validate` accepted transaction: HTTP 200, `valid: true`.
- POST zero amount: HTTP 200, `AMOUNT_NOT_POSITIVE`.
- POST numeric rather than string amount: HTTP 422, safe schema-error metadata.
- Actual PID 1 UID/GID 10001, a read-only root filesystem, dropped capabilities,
  `no-new-privileges`, and bounded temporary storage.
- Exit code 0 after graceful shutdown, no OOM kill, and removal of the owned container.

Post-publication runs used `docker pull --platform ... repository@platform-digest`
and tested those pulled references. Docker reused cached layers, reporting that
images were up to date; this was a real registry pull/manifest check, not a claim
that all bytes were downloaded again. Pulled image IDs matched both the registry
config digests and the pre-publication tested local IDs. All four smoke-test
containers were independently confirmed absent afterward.

## Anonymous access and provenance

Without account credentials or browser cookies:

- Docker Hub repository metadata returned public visibility.
- An anonymous registry pull token permitted retrieval of both release tag manifests,
  both platform manifests, and both image-configuration blobs.
- SHA256 hashes of retrieved manifest/config bytes matched their advertised digests.
- Platform configuration architecture, non-root user, and source revision label
  matched the expected values and local smoke results.
- The released source Dockerfile was retrievable from GitHub at the full commit
  and matched the local Dockerfile byte-for-byte.

The already-reviewed GitHub `main`, `task-02/step-01-dockerfile`, and
`task-02/step-02-container-validation` branches were pushed without force. Remote
`main` points to `dec0da00b6e19defb34001ed84fc7696bf0f8089`. This step's subsequent
publication notes do not change the already-tested image inputs.

## Other verification

Ruff lint/format checks and Python packaging passed. All 167 application tests
passed in 0.46 seconds with the existing Starlette/HTTPX deprecation warning.
Measured application coverage remained 72/72 lines and 14/14 branch outcomes.
This is not a claim of exhaustive tests or coverage of Docker itself.

## Preserved artifacts

- [Registry verification summary](step-03/registry-verification.json)
- [Published manifest list](step-03/manifest-list.json)
- [ARM64 build](step-03/release-build-arm64.txt) / [AMD64 build](step-03/release-build-amd64.txt)
- [ARM64 local smoke](step-03/release-local-smoke-arm64.json) / [AMD64 local smoke](step-03/release-local-smoke-amd64.json)
- [ARM64 push](step-03/release-push-arm64.txt) / [AMD64 push](step-03/release-push-amd64.txt)
- [Index publication](step-03/release-index-create.txt) / [Index inspection](step-03/release-index-inspect.txt)
- [ARM64 pull](step-03/release-pull-arm64.txt) / [AMD64 pull](step-03/release-pull-amd64.txt)
- [ARM64 registry smoke](step-03/release-registry-smoke-arm64.json) / [AMD64 registry smoke](step-03/release-registry-smoke-amd64.json)

Logs came from actual executions; trailing whitespace and Docker Desktop dashboard
links were removed. `manifest-list.json` preserves the exact registry response bytes,
whose SHA256 matches the recorded index digest. No authentication secrets are included. See the
[publication runbook](../../docs/runbooks/image-publication.md) for repeatable
commands, tag safety, and failure handling.

## Limits

No native AMD64 cloud-node test, Kubernetes deployment, vulnerability scan, or
production security gate is claimed. Those remain future tasks. Tags are treated
as immutable by release workflow; server-side tag immutability was not configured.
The isolated build backend retains a version range, so bit-for-bit rebuilds are
not guaranteed. Deploy the recorded digest for the exact tested release.
