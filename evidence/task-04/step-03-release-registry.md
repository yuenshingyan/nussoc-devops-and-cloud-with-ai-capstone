# Step 4.3 — Private registry profile and readback adapter

**Status:** implemented and component-tested, not bundled/installed or run in Jenkins.
No real registry credential, response, upload or application execution was used in these
component checks. Read-only live closure used the existing operator access separately.

## Implementation

`scripts/release_registry.py` owns a temporary private Docker Hub client profile, never the
borrowed Jenkins credential file. It validates canonical private owned single-link file
metadata, bounds and exact opaque token syntax without trimming. The 0700 profile holds a
0600 Docker config for the fixed Docker Hub authority/user. Profile contents and unvalidated
command output are not logging inputs. Only Jenkins node/server cookies survive inherited
environment filtering; fixed HOME, DOCKER_CONFIG, TMPDIR and PATH replace ambient settings.
Proxy, cloud auth, alternate credential stores/helpers and certificate overrides are excluded.

The read-only adapter first queries the fixed `sha-<revision>-amd64` tag, then uses the
expected immutable digest reference for manifest/config queries. All three distinct crane
invocations share one caller-supplied worker-local remaining deadline. No command is
relaunched on failure; pinned crane's internal retries remain allowed inside that budget.
The profile closes on normal or exceptional exit; a cleanup failure is a release failure.
Hard-kill/restart cleanup is **not proved** by these normal Python exit cases.

Readback checks compare raw bytes against trusted pre-existing local/config identities,
not values learned from the same provider response. Strict JSON/schema checks cover Docker
manifest type, descriptor sizes/digests, duplicate/foreign layers, total bounds, exact config
identity and AMD64/Linux/nonroot/revision/rootfs identity. Manifest/config are checked, not
every remote layer blob or application behavior. A tag observation is point-in-time, not
proof of server-enforced tag immutability. Readback does not grant publishing authorization.

Pinned v0.22.1 CLI source inspection established that `digest` adds a newline, while
`manifest` and `config` print raw JSON bytes unchanged. The adapter does not strip/reformat
those JSON bytes. Source references are in the [runbook](../../docs/runbooks/cloud-delivery.md).

## Actual verification

- **67 focused cases**, including private-profile scope/permissions, borrowed binding
  preservation, normal/error cleanup, token/file/environment boundaries, strict identity/
  schema/budget/bounds and three-stage failure/timeout behavior.
- Readback orchestration used **mocked process boundaries**, asserting fixed tag then digest
  references, shared deadline, immediate stop/no relaunch and profile cleanup. This is not
  an actual registry request or live Jenkins Pipeline result.
- **1,259 host tests** passed, plus Ruff check/format, `uv build`, source/dependency gates and
  existing secret-boundary checks: **45 LOW**, zero blocking; **15 clean runtime dependencies**.
  Initial lint identified import/line formatting issues; these were corrected without
  suppression. No native/profile or test failure was relabeled as success.
- Actual pinned crane 0.22.1 `auth get index.docker.io` recovered the **synthetic** username/
  token from the private profile. The result was compared in memory, never published raw.
  Normal/error cleanup and borrowed binding preservation passed.
- Native checks used a temporary removed container: **network disabled**, read-only root,
  UID 1000, no capabilities/privilege escalation, 128 MiB/0.5 CPU and an 8 MiB owned tmpfs.
  Only reviewed scripts and small local image-metadata fixtures were mounted read-only;
  the release-agent service was not started.
- Local fixtures were reconstructed from the retained manual AMD64 archive, not registry
  responses. The 1,719-byte Docker manifest matched local crane digest
  `sha256:a5fc5aad54f4aa7d8a93154f2c63b704bbde36a8fb552547ac7ccc3c39ff4cb0`;
  the 7,803-byte config matched
  `sha256:d4c23d06faf317e704f3732cb8af970a7b896556d1b8e5c90ac65e3ab744ac10`.
  Nine layer descriptors and revision `dc7ffe5a2884f8aeb833f9befd0f1be30d608739` passed.
  No image rebuild, large archive copy, new vulnerability scan or application execution.

Final-code native hashes are recorded in the adjacent [checksummed bundle](step-03-release-registry/).
The first native success and final-code rerun are retained under ignored
`reports/release-registry/`; only reviewed results and credential-free historical procedures
are committed, not raw credentials, image blobs or cloud diagnostics.

## Live closure and storage

Installed legacy definition remained unchanged, disabled/unbuilt, with one pending approval,
zero approved scripts and scheduling v1 unchanged. Source worker remained online, release
service stopped, queue empty and diagnostic jobs disabled. Main #34 still has its own 781-
test result. Cloud spec/Pod identities were unchanged, two replicas Ready, public health 200.

Host free space fell from **2.7 to 1.8 GiB**; Docker-backed Jenkins storage remained about
**7.6 GiB**. Read-only inspection found package outputs 7.6 MiB, pytest temporary data 11.1
MiB, project reports 1,226.7 MiB and uv cache 1,678.2 MiB. Host VM/swap occupied 5 GiB, with
about 3,862 MiB actively used. There is no baseline that establishes the cause of the decline.
No shared caches, volumes, retained diagnostics or host applications were removed/stopped.
**Pause storage-intensive execution until headroom is reviewed.**

Next: immutable publication orchestration, Pipeline integration and actual approved registry/
SCM/deployment/runtime evidence. Neither this checkpoint nor the preceding input checkpoint
has been pushed or merged; the last verified remote feature revision remains `0ac68c1`.
