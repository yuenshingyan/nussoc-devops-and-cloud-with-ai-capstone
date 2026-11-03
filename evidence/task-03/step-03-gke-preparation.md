# Step 3.3 — GKE preparation checkpoint

Status: **preparation implemented; no live cloud eligibility or deployment evidence**.
The deferred `task-03/step-03-cloud-deployment` branch was advanced from its empty
historical checkpoint to published main `f22628a`. The user's standalone dark HTML
architecture follow-up was retained as local commit `30cfaaf`; no publication occurred.

## Actual changes

- `scripts/gke_preflight.py`: safe SDK token retrieval and fixed-endpoint GET-only checks
  for API state, billing-enabled state, CPU quota headroom, selected machine shape and
  readable GKE server configuration. No API enablement, login, SDK installation, IAM
  modification, provisioning or paid upgrade. Exit 0 never authorizes deployment.
- `tests/unit/test_gke_preflight.py`: 49 deterministic cases for validation, quota
  boundaries/missing fields, API failures, redirect refusal, token errors and timeouts.
  Google and SDK boundaries are mocked; these tests are not a live account check.
- [Deployment runbook](../../docs/runbooks/gke-deployment.md): agreed dates/cost guardrails,
  concrete preflight behavior and outstanding image/access/resource decisions.

## Verification

- Ruff lint and formatting: passed after correcting five initial line-length findings.
- Full host pytest suite: **704 passed** (49 new cases); packaging passed.
- Source/dependency gates: passed; **31 LOW Bandit findings remain visible**, no
  MEDIUM/HIGH; 15 runtime dependencies audited without blocking findings. The new
  preflight was included in the scanned source inventory. No suppression was added.
- Existing demo manifests rendered locally with `kubectl kustomize`. No API server was
  contacted and no Kubernetes configuration was changed or applied.
- An actual offline CLI invocation returned exit 2 with `GCLOUD_NOT_INSTALLED`, as
  expected. No account details/token were supplied and no Google endpoint was called.

The helper cannot verify trial-credit balance/currency/expiry from ordinary billing
metadata. A listed machine shape is not proof of zonal capacity or creation permission.
Missing quotas are unknown, not unlimited. Address/disk quota checks depend on the
final approved resource plan. No claim of free deployment or complete preflight is made.

## Important compatibility finding

The historical Kubernetes pin is a public 0.2.0 multi-architecture release. Later local
CI exports are ARM64 and are not compatible substitutes for the proposed AMD64 E2
nodes. Current observability must be released in a compatible newly gated image before
cloud deployment; no image was rebuilt or published in this checkpoint.

## Pending

Google Cloud CLI installation requires approval; browser authentication remains with
the user. Live preflight/API enablement, final resource/exposure agreement and compatible
image publication remain pending. No provisioning before 3 November; no paid billing
upgrade. Availability through 18 November and teardown review on 19 November remain a
plan, not a scheduled automatic deletion or a promise of sufficient credit.

[Host checks](step-03-preparation/host-checks.txt),
[offline preflight](step-03-preparation/offline-preflight.json),
[source-gate summary](step-03-preparation/security-summary.json),
[manifest](step-03-preparation/SHA256SUMS).
