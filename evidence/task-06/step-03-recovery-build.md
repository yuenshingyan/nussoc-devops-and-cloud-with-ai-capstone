# Step 6.3 — Full pipeline verified after storage recovery

The user requested repair after the isolated comparison succeeded. One explicit,
operator-triggered recovery build of unchanged published main was performed:
**`finsecure-ci` #23, SUCCESS**, revision
`d89a0c437c9d5845da5085871f3f45a1bc7795ce`.

This was **not an automatic SCM-triggered build**. Its operator cause was checked;
the pipeline still obtained its Jenkinsfile/source from the configured main branch.
No source push, code/dependency modification, scanner upgrade, gate weakening or
repeated automatic retry was needed. #22 remains FAILURE with its original evidence.

## Actual checks

- Agent online/idle and queue empty before the single build trigger.
- **584 tests passed**, zero failed/skipped; no pytest warning summary.
- Ruff lint/format, package build and source/dependency gates passed.
- Bandit: **29 LOW**, no MEDIUM/HIGH. All **15 runtime dependencies** audited with no
  known advisories; exported hashes matched the lock and no audit warning was emitted.
- Existing application coverage remained 194/194 lines, 37/38 branch outcomes;
  the quality gate remains inactive.
- Application image gate passed with **zero known findings at every severity**.
- Exact source/image/lock identities, inventories, manifests and all **33 archived
  artifact downloads** were verified. The archived image was not loaded or executed.

[Verification record](step-03-recovery-build/verification.json),
[console](step-03-recovery-build/console.txt),
[JUnit summary](step-03-recovery-build/junit-api-summary.json),
[source/dependency summary](step-03-recovery-build/reports/security-summary.json),
[image gate](step-03-recovery-build/reports/image-security-summary.json),
[scanner output](step-03-recovery-build/reports/trivy.txt), and
[hash manifest](step-03-recovery-build/SHA256SUMS).

Full artifacts remain at `http://127.0.0.1:8080/job/finsecure-ci/23/` (local access).
Large package/image downloads remain outside Git. The
[GET-only observer](step-03-recovery-build/check-recovery.py.txt) followed the one
separately authorized trigger; it did not select a later passing retry.

## Meaning and remaining limits

Pipeline operation is restored and verified on the previously failing published
revision. The original #22 Trivy panic's exact cause is still not conclusively isolated
from database-snapshot/storage effects. Recovery does not prove complete integrity
of all Docker data, or guarantee that capacity problems cannot recur. The host still
had only about 11 GiB free after verification. Retained diagnostic databases occupy
space; no caches, volumes or diagnostic data were deleted to obtain this pass.

Trivy's existing third-party SBOM warnings and Bandit's LOW findings remain visible,
not suppressed. This application image result does not establish vulnerability
coverage of Grafana, Alertmanager or Mailpit images.

Monitoring remained stopped. No outage, alert/email demonstration, image-registry
publication or cloud deployment occurred. Review and publish the accumulated
recovery evidence before beginning Step 6.4 on its new branch from merged main.
