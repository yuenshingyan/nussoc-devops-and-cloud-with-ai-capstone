# Step 6.2 — Dashboard configuration and blocked credential preflight

**Later status:** the user approved the secret-volume correction, which was implemented
and actually verified. See [dashboard results](step-02-dashboard.md). The original
failure and then-blocked status below are retained as historical evidence.

29 October 2026 UTC, branch `task-06/step-02-dashboard`, based on reviewed main
`5e53c5f`. Initial scope was approved. This is a **partial implementation checkpoint**,
not proof of a working Grafana deployment or completed dashboard step.

## Actual checks

- Official release API identified Grafana 13.3.0. Docker manifest inspection verified
  ARM64 availability and index digest
  `sha256:488984b716c0862639f91a698adbe2862677a5a07bad42da5f03f3030883b205`.
  The downloaded ARM64 image has UID 472 and no implicit volumes. Its entrypoint
  and defaults were inspected without starting the server. No independent signature
  or whole-image vulnerability-scan claim is made.
- Docker had about 3.83 GiB allocated, with existing Jenkins services using about
  1.68 GiB at preflight. Jenkins was not stopped/reconfigured. Chrome 156.0.8078.48
  and Node 22.23.2 were already available; no browser dependency was installed.
- Optional Grafana overlay, native file-backed configuration, data-source/dashboard
  provisioning, five-panel JSON and a credential helper were written. The existing
  application, metrics-only Compose file and metrics contract were not changed.
- Ruff lint/format, **572 host tests** (34 new), warnings-as-errors execution, test
  report generation, wheel/source build and source/dependency gates passed.
- Bandit: 26 LOW, zero MEDIUM/HIGH. All 15 runtime dependencies audited with no known
  advisories. The new credential helper was included in the source audit.

[Host checks](step-02-preflight/host-checks.txt),
[source gate](step-02-preflight/security-summary.json),
[Compose structural validation](step-02-preflight/compose-config-check.txt),
[checked implementation hashes](step-02-preflight/checked-source-hashes.json), and
[image index](step-02-preflight/grafana-index.txt).

## Real failure, without weakening controls

The generated host credential was private, mode 0400, inside an operator-owned 0700
directory. The approved network-isolated helper used a read-only root and only CHOWN
capability to change that single bind-mounted file to UID/GID 472. Docker Desktop
returned `chown: /secret: Permission denied`. A second ownership-only diagnostic
confirmed the same result; neither operation changed the credential value.

The helper failed closed rather than relaxing permissions or adding capabilities.
Both temporary helpers were removed. The password remains operator-owned UID 501,
GID 20, mode 0400, outside Git; its value was not emitted into reports/chat. No Grafana
data volume was created and Grafana was not started. Existing monitoring services
were not started. No screenshots or actual dashboard queries were captured.
The unit tests simulate ownership metadata; they do not establish host bind-mount
compatibility. The live failure remains recorded rather than hidden by a retry.

[Failure output](step-02-preflight/chown-diagnostic.txt) and
[retained state](step-02-preflight/preflight-checkpoint.json).

## Next decision

Approve the [dedicated secret-volume correction](../../docs/runbooks/dashboard.md):
keep the existing operator-owned host file unchanged, initialize a purpose-labelled
Linux Docker secret volume through stdin, set internal UID/GID 472 and private modes
using only CHOWN, and mount it read-only in Grafana. Refuse unowned/mismatched state;
no automatic rotation or additional capability is proposed.

This correction is **not implemented or verified**. Until approval, the current
initializer is a documented fail-closed checkpoint, not a working setup procedure
for this host. Nothing from this step has been merged or published.
