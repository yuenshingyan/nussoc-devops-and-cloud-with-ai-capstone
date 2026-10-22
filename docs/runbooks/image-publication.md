# Container image publication

## Current release — 0.2.0

- Repository: [yuenshingyan/finsecure-pay](https://hub.docker.com/r/yuenshingyan/finsecure-pay), public.
- Tags: `0.2.0` and `sha-ada935d`.
- Reviewed source: [`ada935d033cd13f85e5e4adfed2d1e9ac449f6f8`](https://github.com/yuenshingyan/nussoc-devops-and-cloud-with-ai-capstone/tree/ada935d033cd13f85e5e4adfed2d1e9ac449f6f8).
- Platforms: Linux ARM64 and AMD64; AMD64 runtime tests used emulation on ARM64.
- Adds the [configurable validation policy](application-settings.md); defaults remain unchanged.

The Deployment pins this verified multi-platform index:

```text
docker.io/yuenshingyan/finsecure-pay@sha256:48ee0ef91737fd2ee1d2efea93cf9a94e840eec6908bde6ed3af7afede884e99
```

```sh
docker pull yuenshingyan/finsecure-pay:0.2.0
uv run --locked python scripts/smoke_test.py --image yuenshingyan/finsecure-pay:0.2.0
```

Both platforms passed default-policy, custom-policy, and invalid-startup checks
before pushing and after registry pulls. Anonymous registry/config access and
public source provenance were verified. See [0.2.0 release evidence](../../evidence/task-03/step-01-image-publication.md)
for platform digests, the recorded configuration-check harness, and actual results.

When testing both architectures on one Docker host, prefer distinct platform
digests. This host could not replace an AMD64 local index reference with ARM64
without first removing that newly created local reference. The registry was not
modified; the limitation and successful recovery are recorded in the evidence.

Release 0.1.0 remains available and unchanged. The historical instructions below
reproduce that original release; substitute a **new approved version and source**
when preparing a future release. Never overwrite either published release's tags.

## Initial release — 0.1.0 (historical)

- Registry: [Docker Hub — yuenshingyan/finsecure-pay](https://hub.docker.com/r/yuenshingyan/finsecure-pay)
- Visibility: public, verified without account credentials.
- Version tag: `docker.io/yuenshingyan/finsecure-pay:0.1.0`
- Commit tag: `docker.io/yuenshingyan/finsecure-pay:sha-dec0da0`
- Source commit: [`dec0da00b6e19defb34001ed84fc7696bf0f8089`](https://github.com/yuenshingyan/nussoc-devops-and-cloud-with-ai-capstone/tree/dec0da00b6e19defb34001ed84fc7696bf0f8089)
- Platforms: `linux/arm64` and `linux/amd64`.

Both release tags resolve to this immutable manifest-list digest:

```text
docker.io/yuenshingyan/finsecure-pay@sha256:18397d4d8391cdfde3220222f0b5d07afa8cbc2afaf92ef8b7d2b23b6494c10c
```

| Platform | Published platform manifest digest |
| --- | --- |
| ARM64 | `sha256:0f302152c2152b6bef90665efeb861d223731a290ed6fd02ef8ae49c15ca32ce` |
| AMD64 | `sha256:33d541d4987fddfd8e7b6dfc185db33eaca499c973d28acd5afc2cf866678e77` |

ARM64 was tested natively in Docker Desktop's ARM64 Linux VM. AMD64 was tested
under emulation on the same ARM64 host, not on a native AMD64 cloud node. Both
platforms passed HTTP, non-root identity, shutdown, and cleanup checks before
publication and after pulling their published platform digests.

## Pull and verify the initial 0.1.0 release

A normal pull chooses the matching host architecture:

```sh
docker pull yuenshingyan/finsecure-pay:0.1.0
uv run --locked python scripts/smoke_test.py --image yuenshingyan/finsecure-pay:0.1.0
```

The smoke script requires the project checkout, uv, and Docker; the image itself
contains everything required to run the API. To pin a deployment independent of
mutable tags, use the manifest-list digest above. For explicit ARM64 verification:

```sh
docker pull --platform linux/arm64 \
  yuenshingyan/finsecure-pay@sha256:0f302152c2152b6bef90665efeb861d223731a290ed6fd02ef8ae49c15ca32ce
uv run --locked python scripts/smoke_test.py --image \
  yuenshingyan/finsecure-pay@sha256:0f302152c2152b6bef90665efeb861d223731a290ed6fd02ef8ae49c15ca32ce
```

For AMD64, use `--platform linux/amd64` and its platform digest from the table.
Running a foreign architecture requires working emulation support. Select cluster
node architecture explicitly before cloud deployment even though both images exist.

## Why these choices

Docker Hub is explicitly recommended by the assignment. Public visibility makes
evaluator access and Kubernetes pulls simpler for this synthetic-data demo;
public visibility is not a rubric requirement. Multi-platform publishing supports
the development machine and common cloud nodes, but is also not required for full
marks. Meaningful versioning, real tests, publication, and reproducible build
instructions are the rubric-relevant capabilities.

## Release procedure

The following describes the procedure used for 0.1.0. **Do not overwrite these
published tags.** For a subsequent release, choose a new approved version and
source commit, and update the package/image version metadata consistently first.
Tag immutability here is a workflow rule, not a claimed Docker Hub enforcement setting.

1. Confirm the target Docker Hub account and public repository. Authenticate locally
   with `docker login --username yuenshingyan`; never put tokens in files or chat.
2. Check that the intended version, commit, and architecture-specific tags do not
   already exist. Stop on permission/network errors instead of treating them as
   evidence that tags are unused.
3. Build from an archive of the approved commit, rather than a potentially dirty
   working tree. The published 0.1.0 inputs came from `dec0da0`:

   ```sh
   revision=dec0da00b6e19defb34001ed84fc7696bf0f8089
   scratch=$(mktemp -d)
   # Use a dedicated shell; this trap removes only the newly created directory.
   trap 'rm -rf "$scratch"' EXIT
   git archive "$revision" | tar -x -C "$scratch"
   for arch in arm64 amd64; do
     docker buildx build --load --platform "linux/$arch" \
       --label "org.opencontainers.image.revision=$revision" \
       --tag "finsecure-pay:sha-dec0da0-$arch" "$scratch"
     uv run --locked python scripts/smoke_test.py \
       --image "finsecure-pay:sha-dec0da0-$arch"
   done
   ```

4. Tag and push only the exact locally tested image IDs. For this release the
   staging tags were `sha-dec0da0-arm64` and `sha-dec0da0-amd64` in the same repository.
   Do not rebuild between testing and pushing.
5. Record each pushed platform manifest digest. Verify its image-config digest
   matches the tested local image ID and its revision label matches the source commit.
6. Compose a multi-platform manifest list with `docker buildx imagetools create`,
   using the **platform digest references**, not mutable staging tags, as inputs.
   Publish the version and commit tags, then verify both resolve to the same index
   with exactly the two expected platforms.
7. Pull each published platform digest and rerun the smoke script. Check anonymous
   access to repository metadata, manifests, and image configuration. Record the
   digests, results, and source link under `evidence/task-02/`.

Separate platform builds were loaded and tested because the local Docker image
store is used for execution. A manifest list was then composed from those same
published images; this avoids claiming a separately rebuilt multi-platform image
was the one tested.

## Failure and credential handling

- The source and credential-store account must match the approved registry namespace
  or have explicitly confirmed permission to publish there. Do not guess a destination.
- Earlier credential-helper failures were resolved after the user corrected the
  local Docker Hub login. This release used the normal authenticated Docker setup;
  no empty-config workaround was used for pushes.
- Publishing multiple tags is not an atomic transaction. If a component or tag push
  fails, inspect remote state and report the partial result. Do not silently overwrite
  an existing release or delete published artifacts as an automatic rollback.
- Saved credentials remain in Docker's credential store. The Hub API bearer used
  for repository creation was kept in process memory and was not recorded in evidence.
- Runtime dependencies and base images are pinned/locked, but the isolated packaging
  backend still resolves from its declared version range. Bit-for-bit rebuilds are
  not guaranteed; digests identify the exact tested and published artifacts.

This is an assignment/demo release, not a production security certification.
Vulnerability scanning and release-blocking gates are still Task 5; cloud deployment
is Task 3. Use synthetic data only.

See [Step 2.3 evidence](../../evidence/task-02/step-03-image-publication.md) for actual
publication results and preserved build/push/pull logs.
