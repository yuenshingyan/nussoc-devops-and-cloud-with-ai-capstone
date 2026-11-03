# Step 3.3 — project ready; first AMD64 candidate blocked by architecture guard

Date: 3 November 2026. **No cluster or application deployment yet. No source/image
publication or paid-billing upgrade.** The user separately authorized SDK installation,
project creation/billing linkage and activation of four APIs.

## Observed account/project setup

- Google Cloud CLI 591.0.0 installed; user completed browser login. Homebrew also
  installed OpenSSL 4 and updated CA certificates. Post-install lint/format/build
  and all 704 tests passed; no automatic rollback or unrelated cleanup was performed.
- Initial read-only discovery found five accessible projects, not five billable VMs
  and not evidence that a capstone project already existed. The user chose a new
  dedicated project. It was created, linked to the sole visible open billing account,
  selected locally, and verified active. Existing projects were not modified.
- Compute Engine, Kubernetes Engine, Cloud Logging and Cloud Monitoring APIs were
  enabled with separate approval and their states verified. API activation may create
  Google-managed service identities/dependencies; this is not a claim that project
  setup makes zero platform-managed changes. No cluster/VM/LB creation was requested.
- Technical preflight passed: free regional CPU quota 100, E2 quota 24, global quota 12.
  The proposed baseline/surge need six CPUs. Regional disk allowance 2,048 GB and eight
  in-use addresses were unused. Quota does not reserve actual zonal capacity.
- Billing API confirms **SGD**. S$385 unused credit, Free Trial state and 2 February
  expiry remain user-reported, not independently verified by ordinary billing APIs.
- An authenticated Compute SKU catalog lookup was denied. No price entries were
  obtained; the proposal's S$225 envelope is not a live tariff quote or spending cap.
  No additional billing API was activated as a workaround.

The nested read-only checker report says it performs no API activation; this describes
that checker, not the separately authorized activation preceding its execution.

## Source and local candidate

Source commit: `33d47709391efcc516e19759e67cc2c632af0f78` (local, unpublished).
Proposed release: **0.3.0**. Updated package, local-project lock entry, OpenAPI metadata,
Docker label and associated test together. Dependency versions and transaction schemas
were not changed. Historical published 0.1.0/0.2.0 tags and Kubernetes pin were untouched.

- All 704 host tests, Ruff lint/format and packaging passed.
- Source gates passed: 31 LOW Bandit findings retained, no MEDIUM/HIGH; 15 runtime
  dependencies audited with no blocking findings. No suppressions were added.
- Built from a Git archive of the exact commit for **linux/amd64**, using the existing
  pinned Dockerfile bases. This was an operator build, not an automatic SCM build.
- Exact local image: `sha256:4f4449f2667a7d0a316f38acdf67b0b6a85cc936a39fe4bc9826854f05ccb596`.
- Existing container smoke test passed against that image under local **emulation**.
  Its owned test container was removed. This does not prove native AMD64 GKE behavior.
- Exported the exact image, recorded its archive checksum and BuildKit identity, then
  ran the existing image-gate implementation in an owned agent workspace.

## Preserved gate failure — not a vulnerability result

The image gate exited **2**, phase **input**, reason `execution_identity_or_report_invalid`.
A direct invocation of the archive validator reproduced:

```text
Expected the explicitly selected linux/arm64 platform
```

`ops/jenkins/image_archive.py` deliberately verifies ARM64 because that is the existing
CI platform. The new candidate is AMD64. **No vulnerability scan or fresh DB download
ran.** No severity counts or pass claim can be inferred from this attempt. Do not
change the image's platform metadata or bypass the identity guard to obtain a pass.

Proposed next change, requiring review: accept an explicit expected target platform
(ARM64 or AMD64), retain ARM64 as the existing default, and keep digest/tag/revision/user
checks unchanged. Add success/mismatch/default tests before rerunning the gate.

The temporary agent workspace was removed only after comparing exported archive/report
hashes to retained host copies. The local image/export and failure reports remain.
Shared Docker caches, volumes and historical diagnostic databases were not pruned.
The first storage query used an absent mount path; the successful follow-up checked
`/` in the builder (about 10.5 GiB free). Host free space was separately about 4.2 GiB.

## Review before continuing

- [Resource/access proposal](../../deploy/infrastructure/gke-proposal.md): two fixed
  nodes, keyless node identity, IAM/DNS control plane, private dashboards, and proposed
  **public HTTP synthetic-data-only** application exposure. Not yet approved/applied.
- Explicit AMD64 support in the existing image validator/gate needs approval.
- Source/image publication and billable-resource creation still require approval.
- Recheck trial status/remaining credit and current pricing before provisioning;
  preserve the no-paid-upgrade constraint even if resources fail or credits run out.

Artifacts: [manifest](step-03-live-preparation/SHA256SUMS),
[project creation](step-03-live-preparation/project-creation.json),
[API activation and preflight](step-03-live-preparation/api-activation.json),
[extended quota/currency check](step-03-live-preparation/extended-preflight.json),
[candidate identity](step-03-live-preparation/candidate-identity.json),
[smoke result](step-03-live-preparation/smoke.json),
[gate failure](step-03-live-preparation/image-security-summary.json),
[diagnosis](step-03-live-preparation/gate-diagnosis.json),
[host checks](step-03-live-preparation/host-checks.txt).
