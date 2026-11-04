# Step 4.3 — Verified crane input preparation

**Status:** input component verified, not wired into the installed Pipeline. No credentials,
external registry access, image rebuild, application execution, cloud mutation or new push.

The preceding explicitly requested feature push succeeded through `0ac68c1`; remote SHA
matched local HEAD. This did not merge/update main or trigger an eligible main release.

## Implemented and tested

`scripts/release_input.py` takes the exact expected compressed archive hash and a caller-
owned private output directory/deadline. It requires canonical owned private paths and a
regular single-link source, caps both compressed/expanded bytes at 64 MiB, streams gzip
integrity checks and hashing, detects source mutation, and creates only mode-0600 `image.tar`.
No member is extracted to the filesystem and no image is rebuilt. Existing outputs/links
are preserved on refusal. New partial output is removed on error; cleanup failure adds a
safe note without replacing the primary error. Full artifact/gate/eligibility checks and
release authorization remain separate caller responsibilities.

**28 input tests** cover exact byte preservation, private permissions, checksum/truncation/
trailing-content failures, existing files/links, source links/permissions, strict digest and
budget inputs, size boundaries, mid-read timeout cleanup and cleanup-failure reporting.
All **1,192 host tests**, Ruff, `uv build`, existing source/dependency gates and secret-boundary
checks passed: **45 LOW**, zero blocking findings, **15 clean runtime dependencies**.
Initial lint found one line-length issue; it was corrected without suppression.

## Actual retained-archive/native-tool evidence

Pinned crane 0.22.1 ran in a temporary removed container: network disabled, no credentials,
read-only root, dropped capabilities, no privilege escalation, UID 1000, 512 MiB/0.5 CPU,
96 MiB owned tmpfs, and read-only mounts of the helper code and retained image artifact.
The release-agent service was not started. Successful owned scratch cleanup was checked.

The manual AMD64 candidate from `dc7ffe5` was used strictly as retained test data:

| Identity | Actual value |
|---|---|
| Compressed bytes | 21,435,786 |
| Prepared tar bytes | 21,542,912 |
| Compressed SHA-256 | `c7173b149f2821d3baba3521397eee791dd53f1b9e33c42b07a91eb2e13a0cf0` |
| Prepared tar SHA-256 | `a18734c58c072df8d06ca93d8a1644959a2bdd45872040b48b7442ce8fc582a5` |
| Config digest | `sha256:d4c23d06faf317e704f3732cb8af970a7b896556d1b8e5c90ac65e3ab744ac10` |
| Local crane manifest digest | `sha256:a5fc5aad54f4aa7d8a93154f2c63b704bbde36a8fb552547ac7ccc3c39ff4cb0` |
| Exported OCI manifest digest | `sha256:27ee6d5d4d5a4af23079d2310ca208c5bb4bd6989231fb858934ff9bfb791099` |

`crane validate --tarball` passed **without `--fast`**. `crane digest --tarball` computed
its local manifest digest. Independent hashing of the config and all **nine compressed
layer blobs**, followed by Docker-manifest reconstruction, matched that local digest.
The Docker and OCI manifest representations differ while the checked config/layer bytes
remain the same. This is **not a registry readback**, new vulnerability scan, normal-main
eligibility or native AMD64 application-runtime demonstration. No image was published.

The first successful local result and later stronger/final-code results remain retained
under ignored `reports/release-input/`; no failed image or gate attempt is represented as
success. The final recorded helper hashes match the code at this checkpoint.

## Closure and pending work

Read-only closure found the installed legacy job unchanged, disabled, unbuilt and pending
approval, with zero approved scripts and unchanged scheduling v1. Release service stayed
stopped, source worker online, queue empty and diagnostics disabled. Main remains #34
SUCCESS (781 tests), not this host test count. Deployment spec and Pod identities remained
unchanged; two replicas were Ready and public health returned 200.

Host free space fell from about 3.6 GiB at preflight to **2.7 GiB at closure**; the cause was
not established. Docker-backed Jenkins storage remained about 7.6 GiB free. Only owned
scratch/container resources were removed. No image build or shared-cache pruning occurred.
Review host headroom before further storage-intensive execution; do not infer Docker free
space means sufficient host space.

Production profile/auth setup, immutable upload and actual registry readback, Pipeline
integration, image-only execution, rollout/smoke and genuine SCM/downstream failure/runtime
evidence remain pending. Main merge/publication still requires review. The adjacent
[checksummed bundle](step-03-release-input/) contains reviewed results and historical
credential-free procedures; no image/archive bytes or raw cloud diagnostics are committed.
