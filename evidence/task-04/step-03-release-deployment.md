# Step 4.3 — Image-only patch planner and uploader blocker

**Status:** pure planning/checking code verified; not integrated into the Pipeline and
not a deployment executor. Delivery remains disabled. No registry or cluster writes,
CI/image builds, job changes/approvals, merge or publication occurred.

## Planner and response contract

`scripts/release_deployment.py` requires a trusted, independently approved Deployment
UID and full-spec SHA-256, plus a separately registry-verified manifest digest. It cannot
establish registry provenance or release eligibility itself. The approval hash must not
be derived from the same unreviewed live GET. Hash encoding matches existing checkpoint
records and does not silently coerce Python keys/values or accept non-finite JSON numbers.

The fixed namespace/Deployment is `finsecure-pay`; its single container is `api` and its
images must be digest references in the fixed Docker Hub repository. The planner rejects
wrong/deleting/paused targets, malformed identifiers, recreated objects, spec drift and
an already-current image. Resource versions and UIDs are opaque, not numeric sequences.

The patch has five tests (UID, resource version, generation, container name, old image)
and **one image replacement**. It does not edit labels, annotations, replicas, resources,
security settings or any other spec value. Response checks require the same identity,
a new resource version, generation +1 and exactly the expected spec. This is not rollout,
readiness, stable managed-metadata or smoke-test proof. No automatic rebase, retry,
rollback or ambiguous-write success interpretation is introduced.

## Actual checks

- **57 deterministic cases:** exact patch shape, input non-mutation, opaque identifiers,
  malformed/wrong targets, strict types/digests/JSON, spec/security/label/image drift,
  unchanged-image rejection and positive/negative synthetic response checks.
- **1,140 full host tests**, Ruff lint/format, `uv build`, existing source/dependency gates
  and Jenkins secret-boundary checks passed. 43 LOW findings remain visible; zero blocking
  source findings and all 15 runtime dependencies clean.
- **One live read-only Deployment GET** matched the UID/spec hash from the prior reviewed
  release-agent checkpoint. Patch planning and response cases used a **synthetic digest
  in memory only**. No PATCH, server dry-run, rollout, registry lookup or authorization.
- The first observer failed before the GET because the repository root was absent from
  its import path. Diagnostics were retained; explicit `PYTHONPATH=.` corrected invocation.
  This was not a production-code failure or a mutation retry.

## Actual uploader-policy finding

Two temporary containers ran only `crane push --help` and `crane version`, with the existing
pinned worker image: no network, credential mounts, published ports or capabilities,
read-only root, UID 1000, resource limits, `--pull=never`, and `--rm`. The release-agent
service remained stopped. Version output was `v0.22.1`; help offered no retry-disable flag.

Matching public upstream source was fetched as bounded data and never executed:

- [`remote/options.go`](https://raw.githubusercontent.com/google/go-containerregistry/v0.22.1/pkg/v1/remote/options.go)
  configures default retry backoff and retry transport.
- [`remote/write.go`](https://raw.githubusercontent.com/google/go-containerregistry/v0.22.1/pkg/v1/remote/write.go)
  wraps blob and manifest upload paths in `retry.Retry`.
- [`crane/options.go`](https://raw.githubusercontent.com/google/go-containerregistry/v0.22.1/pkg/crane/options.go)
  was also reviewed for the CLI/library option boundary.

Exact source hashes and passages are retained in `retry-review.json`; full source remains
in ignored operator reports. This is **not** runtime registry fault-injection evidence or
proof of a global attempt count. It establishes that omitting a Jenkins retry block is
insufficient to honor the approved no-automatic-retry design with these defaults.

**Blocked decision:** keep the current policy and review a no-retry uploader, or explicitly
revise the policy for bounded internal retries. No choice was silently made, no dependency
was added, and upload was not wired or attempted. The recommended default is to retain the
current policy until a concrete alternative is reviewed.

## Closure

Read-only closure found the old installed job exact, disabled, unbuilt and pending
approval, with zero approved scripts; scheduling v1 is unchanged and excludes delivery.
The candidate verification Pipeline hash remains unchanged. Worker stayed stopped, queue
empty, diagnostics disabled and main CI still #34 SUCCESS (781 tests). Deployment spec
and Pod identities remained unchanged, with two Ready replicas and health 200.

Host storage was approximately 4.4 GiB free; Docker-backed Jenkins storage approximately
7.6 GiB free. No shared-cache or retained-diagnostic pruning occurred. No cloud resources
or credentials were changed. Upload/execution, rollout/smoke, actual Pipeline/CAS/conflict/
timeout/restart demonstrations and review/publication remain pending.

The adjacent [checksummed bundle](step-03-release-deployment/) contains reviewed results,
sanitized check logs and credential-free historical observer procedures. Raw cloud objects
and raw failure traces remain outside Git.
