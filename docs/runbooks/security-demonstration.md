# Step 5.4 — Isolated blocking/remediation demonstration

## Status

**Approved local demonstration executed and verified; review/publication pending.**
Manual job `finsecure-security-demo-20261028144809` ran exactly twice on 28 October
2026: build #1 passed 503 tests then blocked 61 HIGH/2 CRITICAL image findings;
build #2 passed 503 tests and the restored production image gate with no known
findings. The job is disabled and workspace image archives are removed. See
[actual results and preservation limits](../../evidence/task-05/step-04-security-demonstration.md).

Branch: `task-05/step-04-security-demonstration`, created from reviewed/published
`main` at `43d6771`. Step 5.3's evidence follow-up is merged and published.
This step does not change the normal pipeline, application contract, dependency
lock, published images or Kubernetes image pin.

## Approved local scope

Use one dedicated, manual, sandboxed Jenkins demonstration job with no SCM polling,
release credentials, registry push or deployment stage. Keep normal `finsecure-ci`
unchanged. Run two deliberately different configurations once each:

1. **Blocked configuration:** check out exact reviewed revision
   `43d6771faff9d269697f64cb70a87080d224f23c`. Use that revision's
   Jenkinsfile and application/lock/scanner files. After checkout, override only
   the demonstration workspace's Dockerfile with the previously studied Debian
   candidate, setting its base to:

   ```text
   python:3.14.9-slim-bookworm@sha256:945c2676dc2b18e0c1f16879244122c57c0ffede60006bf3df159c507a31bcae
   ```

   Use the recorded `Dockerfile.runtime-candidate` under
   `evidence/task-05/step-02-remediation/`, changing only its base ARG to the above
   pinned candidate. This retains whole pip/ensurepip removal, the current locked
   application dependencies and non-root runtime user. Record the complete
   Dockerfile and its SHA-256 before building. The source label identifies the
   reviewed application baseline **plus this documented Dockerfile override**, not
   an unmodified production image.

2. **Remediated configuration:** run the same reviewed revision and actual pipeline
   again, without the Dockerfile override. Its existing pinned Python 3.14.9/Alpine
   3.24 base is the previously approved remediation. Verify the Dockerfile exactly
   matches Git; record the before/after diff and its hash. No vulnerability suppression,
   database substitution, dependency downgrade or change to security thresholds.

The blocked candidate previously produced 61 HIGH/2 CRITICAL occurrences in Step 5.2,
but those counts are **historical, not promised results**. Both runs must use the
current fresh official database and actual scanner. If the candidate no longer has
HIGH/CRITICAL findings, or the remediated image now blocks, stop and agree on the next
action. Never alter reports, ignore findings or weaken the gate to produce a demo.

## Safety and execution boundaries

- Wait until the owned executor/queue is idle before starting; do not interrupt
  normal builds. Serialize these runs on the existing single agent/builder.
- The wrapper must differ from the reviewed Jenkinsfile only in exact reviewed
  checkout selection and the explicit blocked-case Dockerfile override. Record
  wrapper hashes and compare application, lock, scanner and Dockerfile bytes.
- Each run retains the existing 30-minute pipeline budget, 300-second source gate,
  five-minute image DB/scan budgets, 24-hour maximum DB age, no automatic retries,
  and current exact artifact allowlists. Operator observation uses a bounded
  35-minute deadline, as in prior verification; observation timeout is not proof
  of cancellation. Inspect the exact owned queue/build before deciding cleanup.
- Building executes the pinned base's build instructions; the completed vulnerable
  image must **never be loaded into Docker, started as an application, published,
  deployed or smoke-tested**. Trivy reads the exported archive without a daemon.
- Do not add Docker access, release credentials, privileges, mounts, tunnels, external
  services or notifications. Ordinary anonymous dependency/base/DB downloads remain
  necessary; no billable cloud provisioning is involved.
- Do not commit the vulnerable workspace Dockerfile into main or publish a vulnerable
  demonstration branch. The existing historical candidate remains evidence, not a
  working deployment configuration.
- Do not convert infrastructure/scanner errors into a claimed vulnerability block.
  A scan error is a failure requiring investigation; only an actual complete report
  with HIGH/CRITICAL findings and wrapper exit 1 establishes the proposed block.

## Required verification and evidence

For **both** runs, retain job/build identity, exact checkout and executed-wrapper
hashes, UTC times, actual test counts, source/dependency results, and available
sanitized image reports. The baseline currently has 503 tests; verify the observed
count rather than copying the historical 410-test demonstration result.

For the blocked run, verify:

- Real HIGH/CRITICAL findings, advisory IDs, package/installed versions, fix status,
  severity source and fresh DB metadata. Preserve vendor/SBOM caveats from the
  [image-security runbook](image-security.md); findings are not proof of exploitability.
- The real `scripts.image_scan` wrapper returns 1 and Jenkins fails at its image gate.
- Reports and packages remain available; **no downloadable image artifact** exists.
  With a complete gate report, the current pipeline normally retains 32 artifacts.
- No image load/run/push/deploy operation was introduced. No deployed workload is
  claimed to have changed or been protected by an unimplemented release stage.

For the remediation run, verify:

- Exact restoration of the production Dockerfile and unchanged application/lock/gate.
- Passing tests and actual source/dependency/image gates. Do not assume zero findings
  from previous runs; record the real severity counts and policy outcome.
- Successful pipeline and all expected artifacts (currently 33), with downloaded
  archive checksum, config/image ID, source label, platform, lock and report bindings.
  Downloading an archive for identity verification does not authorize loading it.

This demonstrates local **image-archival blocking and remediation**, not registry
release/deployment blocking, managed Kubernetes rollout or completion of the deferred
cloud delivery requirements. It also re-demonstrates an already adopted remediation;
it must not be presented as a newly discovered production fix.

## Approved preservation and cleanup

After both builds finish, disable the owned demo job, preserving its build history
and sanitized diagnostics. Remove only the hash-identified workspace image archives
and any explicitly created transfer files after verification and while idle.
The blocked image must not become an archived downloadable image. Retain only
reviewed text/JSON evidence in Git; keep package/image binaries out of Git.

Do not prune named volumes, Jenkins history, unrelated workspaces or the shared
BuildKit cache. The cache may retain layers from the controlled build; record this
limitation rather than claiming complete erasure. No new retention/expiry policy is
introduced. If execution fails early, preserve diagnostic state and report what
remains; do not silently retry or broaden cleanup.

## Review boundary

The two local manual runs and bounded cleanup were approved and completed. The
procedure above defines that run's scope; it is not permission for further runs.
Review the branch and evidence before merge/publication. No registry publication,
completed-image execution, credential rotation or cloud operation was included.
Registry/deployment-blocking proof remains pending until those stages exist.
