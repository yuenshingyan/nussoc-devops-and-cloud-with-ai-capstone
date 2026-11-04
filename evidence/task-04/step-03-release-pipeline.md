# Step 4.3 — Fixed verification Pipeline candidate

**Status:** assembled and component-tested, **not installed or executed as a Pipeline**.
No worker startup, credential binding, job update/approval/trigger, CI/image build, upload,
cloud mutation, merge or publication occurred.

## Implemented candidate

- Fixed local helper assembly, with a single explicit boundary removing the older
  selection-only body. Reviewed local sources must be bounded regular non-linked files.
- Five fixed verifier modules embedded as bounded base64 chunks with SHA-256 hashes;
  no code is obtained from Git fetches or upstream artifacts for execution.
- Selection before node acquisition, authoritative rechecks, independent source/data
  preparation, original-candidate confirmation, and reviewed-tool installation/readback.
- Isolated Python verification with private output permissions, followed by controller
  result-schema/identity/bounds checks and a further eligibility check.
- Report-only archival and cleanup of a new random owned scratch subdirectory. Ordinary
  secondary failures preserve a primary failure; interruptions propagate.
- A final unconditional publishing/deployment-disabled error. No release credentials,
  registry upload or Kubernetes mutation commands are introduced.

The enclosing ten-minute and verifier two-minute timeouts are declarations, not measured
wall-clock/cancellation proof. New job XML requests disabled restart resumption, while
keeping serialized execution without aborting predecessors. No restart behavior is claimed;
owned scratch can remain after a crash. The creator still refuses existing jobs and never
approves/enables them. Read-only inspection of the older installed definition uses the
explicit legacy resume profile, not the new-job profile.

## Executed verification

1. **Actual Jenkins CPS compilation:** the trusted CPS shell's class loader compiled
   the assembled definition. Its base class and generated CPS methods were checked.
   The script was not initialized with a build owner or run.
2. **Native result contract:** an existing retained worker-result fixture was accepted;
   21 altered status/authorization/identity/architecture/count/age/finding/digest cases
   were rejected. The historical fixture is not a new freshness or eligibility check.
3. **Native boundary/bundle checks:** a controller-local wrong-node path was rejected.
   Five bundled files were written, hash-readback and mode-0600 checked in a newly owned
   **controller-local** temporary directory. Reinstallation into an existing tool directory
   was rejected. The directory was removed. No worker-remoting or Python execution here.
4. **Fourteen plain-Groovy recording-DSL cases:** selection/allocation/preparation/tool/
   process/result/archive/cleanup failure paths, primary-failure preservation and interruption
   propagation. These are synchronous fixtures, **not Jenkins Pipeline engine execution**.
5. **Host checks:** all **1,083 tests**, Ruff lint/format, `uv build`, source/dependency
   security gates and Jenkins secret-boundary checks passed. Source findings remained
   **43 LOW, zero blocking**; all **15 runtime dependencies** were clean.

The five tool hashes remain the earlier independently exercised verifier versions.
Whole-definition and flow hashes, individual tool hashes and case traces are in the
adjacent [checksummed bundle](step-03-release-pipeline/).

## Retained failed attempts

- Initial lint identified line-length issues; corrected without suppressions.
- First CPS attempt found `}class` at an assembled class boundary. The assembler now
  inserts explicit separators; a regression test covers this boundary.
- Second attempt compiled but the observer tried to initialize a CPS script without a
  build owner, causing an owner-null error. The observer now performs compile-only class
  loading and checks that CPS transformation occurred. It does not fabricate a build owner.

Original native procedures, candidate definitions and responses remain under ignored
`reports/release-pipeline/{first-attempt,second-attempt}/`. No Pipeline body or scratch
installation ran during those failed native attempts. Corrected checks did not require
job configuration changes, script approval or policy weakening.

## Live closure and remaining work

The installed legacy selection definition was read back exactly and remains disabled,
never built and pending approval. Approved script count remains zero; scheduling v1 still
excludes delivery. Source worker stayed online, release worker stopped, diagnostics disabled
and queue empty. Main CI remains #34 SUCCESS with 781 tests, not this host test run.

Read-only cloud checks found unchanged Deployment specification and Pod identities,
two Ready replicas and public health 200. No infrastructure or application changes.

Pending: immutable upload/image-only deployment implementation; reviewed installation,
approval/scheduling and activation; eligible automatic-main AMD64 provenance; actual
Pipeline/remoting/verifier/archival/cleanup runs; genuine downstream/concurrency/timeout/
interruption/restart behavior; deployment-blocking demonstrations and rollout/rollback.
The recording fixtures cannot substitute for those results. Storage remains constrained;
no image build or shared-cache pruning was attempted.
