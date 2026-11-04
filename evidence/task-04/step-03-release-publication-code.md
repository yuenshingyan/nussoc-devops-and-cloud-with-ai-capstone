# Step 4.3 — Publication primitives and cache recovery

**Status: implementation checkpoint, not completed delivery.** The installed job remains
disabled/unbuilt and does not call these primitives. No registry write, new image build,
main merge/push, rollout or rollback occurred.

## Implemented

`scripts/release_publication.py` rehashes a canonical owned private prepared tar against the
trusted preparation result. Preflight invokes full local crane validation, local digest,
and successful tag listing. Malformed listings, command failures and an existing target tag
are refused. This is an observation, not an atomic reservation against another writer.

The fixed controller must independently verify the original archive/config/revision binding,
run preflight, and recheck the original candidate immediately before calling the separate
write primitive. That primitive rehashes the tar, invokes push once, then requires the
existing digest-pinned manifest/config readback. Push stdout is never treated as proof.
Failed/timed-out push outcomes require manual inspection, not command relaunch, deletion,
retagging or automatic rollback. All commands share the remaining worker-local deadline;
pinned crane internal retries remain allowed. The primitive itself grants no authorization.

## Execution evidence

- **20 focused tests and all 1,279 host tests passed.** Process-boundary fixtures exercise
  existing/malformed tags, staged failures, exact argv/deadline, changed bytes, uncertain
  writes and successful push followed by failed readback. Only process boundaries are mocked;
  actual profile cleanup and manifest/config validation run in those tests.
- Ruff check/format, `uv build`, existing source/dependency gates and secret-boundary checks
  passed: **45 LOW**, zero blocking; **15 clean runtime dependencies**.
- A removed temporary 128 MiB/0.5 CPU, UID-1000, read-only-root, capability-free container
  used actual pinned crane to read the public repository listing without stored credentials.
  **10 tags** passed the newline-delimited framing checks. Only the reviewed command helper
  was mounted; owned temporary profile cleanup passed. This proves public listing behavior,
  **not** release eligibility, publication, image readback or Pipeline execution.
- An attempted pinned `cmd/crane/cmd/ls.go` source lookup returned 404; native CLI observation
  verified listing framing instead. No failed lookup is represented as source verification.
- Read-only closure confirmed unchanged installed job/approval/scheduling, stopped release
  service, online source worker, empty queue, disabled diagnostic jobs, unchanged cloud spec/
  Pod identities, two Ready replicas and public health 200. Main #34 remains its separate
  781-test result, not the host test count above.

## Approved cleanup and limits

Unused host uv-cache pruning removed **124.8 MiB** but did not materially improve rounded
free-space output. After further user approval, remaining-cache cleanup removed **1.4 GiB**.
Host free space rose from 1.8 to **2.9 GiB**, measuring **2.8 GiB** after verification. Docker-
backed Jenkins remained about **7.6 GiB** free. No reports, retained diagnostics, Docker data
or host applications were removed/stopped. Dependencies may need downloading again.

The adjacent [checksummed bundle](step-03-release-publication-code/) contains sanitized
results and the credential-free listing procedure. Raw diagnostics remain under ignored
`reports/delivery-completion/`. New monitoring volumes still require explicit confirmation
of sufficient trial credit. Deployment execution, full Pipeline integration, actual gated
publication/rollout, blocking demonstrations, rollback and cloud monitoring remain pending.
