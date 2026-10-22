# Step 3.1 follow-up — Approved 0.2.0 publication and digest pinning

- **Date:** 2026-10-22 UTC; exact timestamps are retained in the linked JSON records.
- **Branch:** `task-03/step-01-manifests`; final review/merge still pending.
- **Reviewed release source:** [`ada935d033cd13f85e5e4adfed2d1e9ac449f6f8`](https://github.com/yuenshingyan/nussoc-devops-and-cloud-with-ai-capstone/tree/ada935d033cd13f85e5e4adfed2d1e9ac449f6f8).
- **Approval:** The user approved publishing 0.2.0 for ARM64/AMD64 and pinning its verified digest.
- **Repository:** [Docker Hub — yuenshingyan/finsecure-pay](https://hub.docker.com/r/yuenshingyan/finsecure-pay), public.

## Published references

Both tags `0.2.0` and `sha-ada935d` resolve to this exact multi-platform index:

```text
docker.io/yuenshingyan/finsecure-pay@sha256:48ee0ef91737fd2ee1d2efea93cf9a94e840eec6908bde6ed3af7afede884e99
```

| Platform | Platform tag | Manifest digest | Config digest / tested image ID |
| --- | --- | --- | --- |
| `linux/arm64` | `sha-ada935d-arm64` | `sha256:fa11c7014e86747717d3eb6a2df121581cc66bce011e83456d2c7870d81ad3eb` | `sha256:3f8096c09e173b78b3677273001dfb8ecdb0a0f37019e6d4ac373f24f0ea9a8a` |
| `linux/amd64` | `sha-ada935d-amd64` | `sha256:66ade57348103ac7fbcd01f323f6c01469f6a1e2c441196612942c2dcfb1e245` | `sha256:f0f277d911f2a12a93acb68407deb9ed023013b3b42455d5de69a20eb6ed4adb` |

ARM64 ran natively in Docker Desktop's ARM64 Linux VM. AMD64 ran under emulation
on the ARM64 host, not on a native AMD64 cloud node. The index contains exactly these
two Linux platforms. Index, platform-manifest, and image-config digests identify
different objects.

## Actual release procedure

1. Confirmed the Docker credential-store account was `yuenshingyan`, with a secret
   present but never printed. No credential settings were changed.
2. Confirmed public repository access. All four intended tags returned explicit
   `MANIFEST_UNKNOWN` responses before building and again before pushing; other
   HTTP failures were not treated as permission to overwrite a release.
3. Created a temporary `git archive` of reviewed commit `ada935d`, then built and
   loaded each architecture separately with its full OCI source-revision label.
4. Ran default-policy, custom-policy, and invalid-startup checks on each local image.
   Only those exact tested image IDs were tagged and pushed.
5. Composed the version/commit index tags from the pushed platform digests, without
   rebuilding. Retrieved both tag manifests anonymously and confirmed identical bytes.
6. Retrieved both platform manifests and configuration blobs anonymously. Byte hashes,
   architecture, Linux OS, non-root user, version 0.2.0, and full source-revision labels
   matched the tested images.
7. Pulled both platform digests and repeated all three categories of runtime checks.
   Pulled IDs matched the pre-publication tested IDs. These pulls reused cached layers;
   no fresh download of every layer is claimed.
8. Verified the previous `0.1.0` and `sha-dec0da0` tags still resolve to their original
   index `sha256:18397d4d8391cdfde3220222f0b5d07afa8cbc2afaf92ef8b7d2b23b6494c10c`.
9. Published reviewed `main` and the Step 3.1 source branch without force. Anonymous
   GitHub retrieval of the released Dockerfile and configuration module matched
   `git show ada935d:<path>` byte-for-byte.

The release-specific [verification harness](step-01-release/configuration-smoke.py.txt)
was executed from the project root with stdin, so it could reuse the existing
`scripts.smoke_test` helpers. For example, after an explicit ARM64 platform pull:

```sh
reference=yuenshingyan/finsecure-pay@sha256:fa11c7014e86747717d3eb6a2df121581cc66bce011e83456d2c7870d81ad3eb
docker pull --platform linux/arm64 "$reference"
uv run --locked python - "$reference" \
  < evidence/task-03/step-01-release/configuration-smoke.py.txt
```

The harness is intentionally specific to version 0.2.0 and its source-revision label.
For AMD64 use its platform digest and working emulation or a native AMD64 machine.
Do not republish existing release tags when reproducing local checks.

## Runtime outcomes

For each architecture, before push and after pull:

- Default policy: health, accepted transaction, zero-amount rejection, sanitized
  malformed-amount HTTP 422, actual PID 1 UID/GID 10001, read-only root filesystem,
  dropped capabilities, clean shutdown, and owned-container removal passed.
- Configured policy (`100`, `USD`): USD `100.00` accepted; USD `100.01` rejected at
  the configured cap; SGD `50` rejected as disabled; SGD `125.50` returned both
  applicable codes in order. OpenAPI version and health checks passed; exit was 0.
- Invalid startup: a synthetic malformed setting caused a nonzero exit, without
  successful application startup or logging the malformed value.

All **12 owned smoke containers** were independently confirmed absent afterward.
The initial cleanup checker expected capitalized Docker error text; adjusting the
check for the CLI's lowercase `no such object` response resolved the checker failure.
No runtime tests were automatically retried or hidden.

Ruff checks and packaging passed. The complete application suite passed again:
**210 tests**, 125/125 measured lines and 28/28 branch outcomes, with the existing
Starlette/HTTPX deprecation warning still visible. See the preserved test output.

## Extra index-pull check and local cache recovery

Pulling the shared index explicitly for AMD64 selected the expected tested AMD64
image. Immediately switching that same local digest reference to ARM64 failed with
`cannot overwrite digest`. This was a local image-store reference conflict, not a
registry overwrite attempt or failed platform-specific image test.

After confirming the AMD64 image still had its explicit local build tag, only the
newly created local index reference was removed with `docker image rm <repository@index>`.
No force option, image prune, registry deletion, or credential reset was used.
The ARM64 index pull then succeeded and selected the expected tested ARM64 image.
The AMD64 tagged image remained available. Both the initial failure and recovery
logs are preserved. Prefer distinct platform digests for side-by-side architecture
tests on this host; do not automatically remove unrelated local references.

## Deployment pin verification and limits

`deploy/kubernetes/base/deployment.yaml` now pins the verified index above. The demo
overlay was rendered again and parsed locally: its image matched the registry record,
replicas remained two, selectors/namespace/ports matched, the Service stayed ClusterIP,
and its generated ConfigMap reference and default values remained correct.

**No cluster was contacted and no manifests were applied.** Kustomize consistency
checks do not replace API-server schema/admission validation or actual deployment.
Probes, requests/limits, rolling-update settings, and pod security remain Step 3.2;
cloud provider, access, budget, exposure, and teardown still require approval.
Vulnerability gates remain Task 5. Tag immutability is a workflow rule, not registry
enforcement, and the packaging backend's version range prevents a bit-for-bit rebuild
guarantee. Deploy the recorded digest for this exact tested release.

## Preserved artifacts

- [Tag/account/public-access preflight](step-01-release/v020-preflight.json)
- [Registry verification summary](step-01-release/v020-registry-verification.json)
- [Exact index bytes](step-01-release/v020-manifest-list.json), whose SHA256 matches the index digest
- [ARM64 build](step-01-release/v020-build-arm64.txt) / [AMD64 build](step-01-release/v020-build-amd64.txt)
- [ARM64 pre-push checks](step-01-release/v020-local-smoke-arm64.json) / [AMD64 pre-push checks](step-01-release/v020-local-smoke-amd64.json)
- [ARM64 push](step-01-release/v020-push-arm64.txt) / [AMD64 push](step-01-release/v020-push-amd64.txt) / [Index publication](step-01-release/v020-index-create.txt)
- [ARM64 pull](step-01-release/v020-pull-arm64.txt) / [AMD64 pull](step-01-release/v020-pull-amd64.txt)
- [ARM64 post-pull checks](step-01-release/v020-registry-smoke-arm64.json) / [AMD64 post-pull checks](step-01-release/v020-registry-smoke-amd64.json)
- [AMD64 index pull](step-01-release/v020-index-pull-amd64.txt) / [Initial ARM64 index failure](step-01-release/v020-index-pull-arm64-initial-failure.txt)
- [Owned local reference removal](step-01-release/v020-index-local-alias-removal.txt) / [Successful ARM64 index pull](step-01-release/v020-index-pull-arm64.txt)
- [Test output](step-01-release/v020-tests.txt)
- [Final rendered resources](step-01-release/v020-kubernetes-demo.yaml) / [Consistency checks](step-01-release/v020-manifest-checks.json)

Logs retain actual results; repository-home paths were replaced with `<repository>`,
Docker Desktop links removed, and trailing whitespace trimmed. Secrets were not
recorded. Original candidate evidence remains separate in
[Step 3.1 implementation verification](step-01-manifests.md).
