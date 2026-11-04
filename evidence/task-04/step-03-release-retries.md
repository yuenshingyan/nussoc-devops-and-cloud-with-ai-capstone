# Step 4.3 — Approved bounded crane-internal retries

**Status:** policy exception approved and command execution component verified. Not a
production uploader, not installed in the Pipeline, and no real release authorization.
The user reports remote push unavailable; no push or merge was attempted.

## Contract

Pinned crane may perform its own internal retries within the remaining ten-minute release
budget. There is no Jenkins/shell retry loop or automatic command relaunch, Kubernetes
patch retry/rebase, or rollback. Unknown/failed write outcomes require inspection, not an
assumption that nothing changed. Existing source, test, freshness, image and current-main
checks remain required. This narrow approval does not activate delivery or authorize a
new external publication.

`scripts/release_command.py` launches one trusted argv without a shell. The caller supplies
a worker-local monotonic deadline bounded by the remaining release budget. It drains both
pipes, limits combined output to 1 MiB, returns bounded stdout and exit status, and does
not return/log provider stderr. Owned process-group termination/reaping covers descendants.
Timeout/output-limit failures explicitly identify unknown outcomes. This cannot undo a
remote write or prove Jenkins abort/restart cleanup. Callers must validate stdout and own
credential/profile setup; the helper is not an authorization boundary for arbitrary argv.

## Actual verification

- **24 process tests:** output/exit handling, no relaunch, deadline, simultaneous pipe
  draining, exact/excess output bounds, invalid inputs, safe startup errors, and descendant
  termination. The descendant case requires its startup marker before checking cleanup.
- **Actual pinned crane 0.22.1**, in a temporary removed container with network disabled,
  read-only root, no capabilities/privilege escalation, UID 1000, 128 MiB/0.5 CPU, an owned
  16 MiB tmpfs and a read-only bind of the reviewed helper. No production credentials.
- A synthetic loopback registry returned HTTP 503 to upload initiation. One invocation
  made **three POST attempts**, then returned exit 1 after approximately **4.17 seconds**.
- A separate invocation with a **0.8-second** budget made **one POST**, then the process
  group was stopped after approximately **0.81 seconds**, with unknown-outcome failure.
- No external registry was contacted; the synthetic archive was parsed, not run as an
  application. These observations are not a global attempt bound, manifest retry proof,
  successful real push, Pipeline timeout, user-abort or restart test.
- **1,164 full tests**, Ruff lint/format, `uv build`, existing source/dependency gates and
  Jenkins secret-boundary checks passed. Findings increased to **45 LOW**, zero blocking;
  the two new findings are B404/B603 for subprocess import/invocation. They were not hidden
  or suppressed. All 15 runtime dependencies remain clean.

## Retained attempts and limitations

Initial lint found import-order/line-length issues, corrected without suppressions. The
first native fixture supplied an outer-gzipped Docker tar and failed before any registry
request. An explicit, credential-free diagnostic confirmed `unexpected EOF`; its raw
synthetic stderr remains local. The fixture was corrected to an uncompressed tar, without
changing production code or weakening any gate. Production preparation of the retained
compressed image artifact still needs explicit verified decompression, not an image rebuild.
Original failed and first-successful probes are retained in ignored operator reports.

The command runner is not yet bundled into the release definition. Authentication/profile
ownership, actual immutable push, registry readback, image-only execution, rollout/smoke,
real cancellation/restart, and the remaining demonstrations are pending. No fixed universal
HTTP retry count is inferred from this one failure path.

## Closure

Read-only checks found the older installed delivery definition unchanged, disabled, never
built and pending approval; approved-script count remains zero and scheduling v1 still
excludes delivery. Release service stayed stopped, source worker online, queue empty,
diagnostic jobs disabled, main CI still #34 SUCCESS (781 tests). Deployment spec and Pod
identities remained unchanged, with two Ready replicas and public health 200.

No Git push, image build, real credential binding, external upload, cloud mutation, new
dependency or shared-cache pruning occurred. Remote publication remains an explicit blocker;
local fixtures cannot replace authoritative SCM/main provenance.

The adjacent [checksummed bundle](step-03-release-retries/) contains reviewed results and
credential-free historical procedures. Raw diagnostics remain outside Git.
