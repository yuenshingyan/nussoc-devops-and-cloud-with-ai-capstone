# Local Jenkins image builder — Step 4.3 (partial)

Scope approved for this step: a separate rootless BuildKit builder and local image
build/export verification only. Registry credentials, publishing, Kubernetes, and cloud
resources are excluded. This is not the completed container-delivery requirement.

## Boundaries and operational policy

- BuildKit/buildctl **0.34.1**, from a digest-pinned official rootless image. The Python
  agent receives only the client binary; it does not receive a Docker CLI/daemon/socket.
- Builder runs as UID/GID **1000:1000**, not privileged, with all outer capabilities
  dropped except **SETUID/SETGID** for subordinate-ID mapping helpers. Those helpers
  require setuid execution, so **no-new-privileges is not enabled on the builder**.
- Builder-only exceptions: seccomp/AppArmor unconfined and system paths unmasked.
  Existing controller/agent capability drops and no-new-privileges remain unchanged.
  Rootless is risk reduction, not a security boundary for untrusted build code.
- Native snapshotter avoids a FUSE device. PID/process sandboxing stays enabled:
  **no `--oci-worker-no-process-sandbox`**, host PID namespace, or host network mode.
- Only the dedicated named socket volume is shared with the agent, mounted read-only
  there. A read-only socket mount still permits build requests. The socket directory
  is UID 1000 with owner-only access (0700 in the image, 01700 after BuildKit adds its
  sticky bit). Builder has no Jenkins home, workspace, or credential mounts.
- No TCP listener or published builder port. Builder gets its own Docker bridge for
  public base-image/package downloads; this is not a general outbound network firewall.
- Only administrator-controlled, trusted source may use this builder. Any code running
  on the Python agent can use its socket; never enable untrusted PR/fork builds on it.
- Builder: **1 CPU, 1 GiB**, one parallel Dockerfile operation. Existing Jenkins services
  each keep their 1 CPU/1 GiB limits. Local build target: **linux/arm64** only for now;
  existing published multi-platform releases are unchanged.
- Startup: Compose health wait **90 seconds**, outer Docker command **120 seconds**;
  each health probe allows 5 seconds (Docker terminates it at 6 seconds).
- Image stage: **10 minutes**, build client **9 minutes** via GNU `timeout` (TERM, then
  KILL after 15 seconds), within the existing 15-minute pipeline timeout after agent
  allocation. BuildKit's `--timeout=5` is only a five-second connection timeout, not
  a build deadline. No build retries. Jenkins aborts its shell;
  BuildKit cancels disconnected build RPCs. Inspect a stuck worker and stop
  only the owned builder if necessary; never kill unrelated containers.
- Builder stays up with this local stack; stopping it is the operator's responsibility.
  Stop grace is **30 seconds**. Named cache/socket volumes survive stops/restarts.
- Automatic BuildKit garbage collection is explicitly disabled for this reviewed demo.
  Cache, Jenkins artifacts/history, and ignored verification downloads are retained
  until deliberate manual cleanup. This is not a disk quota: monitor disk use and stop
  new builds when space is low. Do not run global prune or remove unrelated volumes.

These are explicit local-demo policies, not production sizing, tenant isolation, or
proof of security-scan compliance. See the upstream
[rootless guide](https://github.com/moby/buildkit/blob/v0.34.1/docs/rootless.md).

## Setup and verification

The local subset was reviewed, merged, and published as `ab538a2`. Normal SCM-loaded
**finsecure-ci build #2** passed all **245 tests**, exported an image, and its downloaded
archive passed host-side runtime smoke checks. See the
[post-merge evidence](../../evidence/task-04/step-03-scm-verification.md).

Build the agent/builder locally before bootstrap, with existing jobs/queue idle:

```sh
docker compose -f ops/jenkins/compose.yaml config --quiet
docker compose -f ops/jenkins/compose.yaml build agent builder
uv run --locked python ops/jenkins/bootstrap.py
```

Bootstrap checks ownership of both new named volumes before reuse. Compose starts the
builder before the agent mounts the socket volume, preserving the image's UID 1000
ownership on first creation. Existing passwords, agent identity, and history are retained.
No registry login is required: base images are public and the build client uses an empty
temporary Docker configuration rather than borrowing host credentials.

The image stage exports `images/finsecure-pay.tar.gz`, BuildKit metadata,
source/platform/local-tag metadata, and SHA-256. It does not load the image into Docker
from Jenkins. Tags use `finsecure-pay-ci:jenkins-<job>-<build>` and are local-only,
not the public repository's release tags. The revision label records the checkout.

## Candidate verification and artifact checks

The recorded success run used the unchanged candidate Jenkinsfile body with only an
explicit Git `scm` binding prepended, checking out published `d492a79` (230 tests):

```sh
uv run --locked python ops/jenkins/verify_ci.py \
  --source-revision d492a7902ad58891859911e8416befb50bd2cb64 --expected-tests 230
uv run --locked python ops/jenkins/verify_ci.py \
  --source-revision d492a7902ad58891859911e8416befb50bd2cb64 --expected-tests 230 \
  --fail-after-tests
```

Use `--existing-job <matching-review-job>` to inspect an existing completed build
without rebuilding. The success and failure records are respectively
`finsecure-ci-review-success-20261025015653` and
`finsecure-ci-review-failure-20261025020023`, build 1 each. Both are disabled after
verification and retain their history/artifacts.

The verifier checks the image archive's downloaded SHA-256, exact local tag, source
revision, Linux ARM64 platform, non-root configuration, and configuration digest against
BuildKit's metadata. It reads only unique regular JSON members of at most 1 MiB without
extracting archive files. This is artifact inspection, not a vulnerability scanner or
signed attestation. It also verifies test/coverage reports and wheel/source packages.

The isolated exit-37 probe occurs after passing tests and blocks both packaging and
image export. It is not a real failing-test, release, or deployment-gate demonstration.
There are **245 host tests** including 15 new operational regressions; those new tests
were not in the review job's published checkout. No Python dependency was added.

## Operator-side runtime smoke verification

After the verifier succeeds, use its `image_export` fields and archived checksum:

1. Check the destination local CI tag is unused (or already refers to the exact expected
   image); do not overwrite another image or any existing public release tag.
2. Load the downloaded archive with `docker load --input <downloaded-archive>` from the
   **host operator shell**, never from Jenkins.
3. Inspect the loaded tag and require its image ID to equal the verified configuration
   digest. Require the revision label and platform to match the verification record.
4. Run `uv run --locked python scripts/smoke_test.py --image <verified-image-id>`.

The recorded image ID is
`sha256:26a06f2c8e5d217bf00579b94d7b6811a4e420930da7aeeafb03da46ef7c549d`.
Its real PID 1 UID/GID, health, accepted/rejected/malformed validation cases, clean
shutdown, and removal passed. This operator-side check is not an automated deployment
or a CI smoke-test stage. The local image/download remains available for review; the
smoke container was removed. No AMD64 export/runtime claim is made for this candidate.

A controlled ten-second client timeout interrupted a started 120-second synthetic RUN;
BuildKit reported cancellation and no probe process survived. The builder restarted with
the same cache/worker identity, the agent reconnected to its socket, and repeated
bootstrap preserved credentials and existing Jenkins build history.

## Diagnostics, cleanup, and remaining scope

- Docker requires `systempaths=unconfined`, not the colon spelling accepted by some
  other security options. An initial container creation failed until this was corrected.
- Buildctl's connection timeout accepts integer seconds (`--timeout=5`), not `5s`.
  The first health probe failed before correction; no pipeline test was retried to hide it.
- Docker inspection prefixes capability names with `CAP_`, realizes unmasked system
  paths as empty masked/read-only lists, and BuildKit adds the directory's sticky bit.
  Runtime assertions were corrected to check these actual representations.
- BuildKit logs missing unused CDI directories, unsupported optional fsverity, and a
  skipped containerd worker. OCI/native builds worked; no warnings were suppressed.
  The worker's `network: host` label refers to its builder-container network, not Docker
  host networking. The outer container uses a dedicated bridge.
- Existing Starlette/HTTPX and Jenkins startup/JNLP metadata warnings remain documented.
- Stop the whole owned project with `docker compose -f ops/jenkins/compose.yaml stop`
  when idle. Do not add `--volumes` or run global prune. Cache/artifact cleanup is manual.

See the [historical pre-merge evidence](../../evidence/task-04/step-03-local-image-builder.md)
and completed [SCM follow-up](../../evidence/task-04/step-03-scm-verification.md). The new
SCM-built image is `sha256:eaca7256fb8b9d72896c8fba7a26bf0b57dbb2ae506f139201f7cc251004d45f`,
with local tag `finsecure-pay-ci:jenkins-finsecure-ci-2`; it was loaded and smoke-tested
separately from the earlier review image described above.
Step 4.3 remains partial until separately approved publishing and cloud delivery are
implemented and exercised. No later implementation step has started.
