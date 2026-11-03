# Step 3.3 — explicitly selected AMD64 gate passed

Status: **local candidate verified, not published or deployed**. The user approved
explicit AMD64 target support after reviewing the preserved ARM64-only rejection.

## Change and regression coverage

Implementation commit: `4b243e278ee749c4d08bc713cd803bdd77b7e132`.

- `inspect_image_archive` accepts an explicit `platform`; default remains `linux/arm64`.
- `scripts/image_scan.py --platform linux/amd64` forwards the target to both archive
  and scanner-report validation. Only `linux/arm64` and `linux/amd64` are supported.
- Archive and Trivy configuration must independently match the selected target.
  No automatic architecture acceptance, host-platform inference or platform rewriting.
- Digest, tag, source revision, non-root identity, locked inventory, OS support/EOL,
  scanner checksum/version, fresh DB and HIGH/CRITICAL policy checks are unchanged.
- Jenkinsfile, native ARM64 build selection, credentials, dependencies and resource
  limits are unchanged. This is not normal SCM-to-cloud pipeline verification.
- 66 additional cases: full suite **770 passed**, focused archive/scan suite **159 passed**.
  Tests cover both platforms' success, cross-platform mismatches, identity tampering,
  severity/EOL policy and tool failures; CLI default/selection/unsupported-target cases.
- Ruff lint/format, packaging and source gates passed. Source scan still reports
  **31 LOW Bandit findings**, zero MEDIUM/HIGH, and 15 audited runtime dependencies
  without blocking findings. No suppression was introduced.

## Real operator build and scan

Built version **0.3.0** from a Git archive of the implementation commit, with the
existing pinned bases and an explicit Linux AMD64 build target. No mutable source
checkout or rebuild was substituted between smoke testing and export/scan.

- Image ID: `sha256:798fcb8de76aa2c6e15393911bb4edb51a5bd5f6c0bf4dd169d9dca3fa1714d8`.
- Export SHA-256: `d81de74c46fbea010585434060fccf30f74e050a1815751ab6f34f9fe5dc809e`.
- Source revision, BuildKit config digest, smoke-tested image ID, archive metadata and
  scan summary agree. Application image is AMD64; runtime smoke ran under local
  emulation on the ARM64 host, not on a GKE node. Owned smoke container was removed.
- The unchanged pinned ARM64 Trivy executable scanned the AMD64 archive in the existing
  agent, with a fresh database, complete OS/Python inventories and no Docker access.
- Actual image gate: **passed**, exit 0; **zero reported vulnerabilities at every
  severity**, no EOL/blocking findings. This is a time-bounded scan result, not a
  guarantee of vulnerability-free software.
- The real candidate archive still fails when the platform argument is omitted, with
  `Expected the explicitly selected linux/arm64 platform`; explicit AMD64 succeeds.
  This checks the preserved default against the actual archive, not just fixtures.
- Fresh temporary DB/cache was removed by the gate. The owned agent workspace was
  removed after its archive/report hashes matched retained host copies. Local image,
  export, logs and reports remain; no shared caches, volumes or diagnostic DBs were pruned.
- Host storage after verification: about 5.2 GiB free. Recheck before another large run.

## Boundaries and next approval

The [earlier failed attempt](step-03-gke-live-preparation.md) is retained unchanged.
No automatic retries were used to hide it. This is a distinct candidate with a reviewed
validator change. No cloud resources or billing settings changed in this follow-up.

Source/image publication, the [resource/access proposal](../../deploy/infrastructure/gke-proposal.md)
(including public HTTP synthetic-only access), actual cluster creation and native GKE
verification still need approval. The current Kubernetes public-image pin remains
historical 0.2.0; this local candidate is not yet accessible to an evaluator.

Artifacts: [manifest](step-03-amd64-gate/SHA256SUMS),
[identity](step-03-amd64-gate/identity.json),
[host checks](step-03-amd64-gate/host-checks.txt),
[build](step-03-amd64-gate/build.txt),
[smoke](step-03-amd64-gate/smoke.json),
[image gate](step-03-amd64-gate/image-security-summary.json),
[Trivy report](step-03-amd64-gate/trivy.json),
[database metadata](step-03-amd64-gate/trivy-db.json),
[source gate](step-03-amd64-gate/security-summary.json).
