# Step 6.5 — Approved diagnostic activation

The user approved one additional diagnostic controller activation after `efa5058`.
The verifier and application code were **unchanged**. The observer captured the exact
mount inputs before invoking the original check, restoring the observer hook afterward.

## Result

The diagnostic activation reproduced `notification_configuration_mount_invalid`.
For the controller's single notification configuration mount:

- Type was `bind`; destination was `/etc/jenkins/notifications.yaml`.
- `RW` was false; both approved networks were present.
- Expected source was `<repository>/ops/jenkins/notifications.yaml`.
- Actual source was `/host_mnt<repository>/ops/jenkins/notifications.yaml`.
- Thus the exact source comparison, not type or write access, failed.
- `docker info` identified the daemon operating system as `Docker Desktop`.

The actual absolute repository prefix is replaced consistently in the exported
records. The metadata establishes this diagnostic attempt's failure condition. The
first activation did not capture its mount metadata, so its exact inputs cannot be
verified retrospectively. The prior isolated probes used the host-form path; do not
claim the translated path is always returned for every Docker Desktop bind.

## Safe stopping point

The handler restored the baseline controller and stopped Mailpit again. A separate
post-rollback check passed: main remains #25, queue empty, agent online/idle,
controller on its original network only, notification opt-in absent, monitoring
stopped. No notification job, SMTP send, image scan, deployment or publication ran.
The previously documented persisted local Mailer settings are not erased by Compose
rollback. Shared named volumes, history, credentials and caches were preserved.

Host free space was approximately 10 GiB; VM free space approximately 14 GiB before
activation. Native Jenkinsfile validation passed again. Application tests were not
rerun because this diagnostic changed no application or verifier code.

## Proposed correction — approval required

Accept only either the exact expected host path or, **only with a verified Docker
Desktop daemon**, that same exact path prefixed by `/host_mnt`. Do not normalize
arbitrary paths, accept arbitrary bind mounts, or change read-only/network checks.
Also compare the mounted configuration's SHA-256 with the approved host file before
considering activation verified. File-content identity was not captured in this
attempt and is not claimed here.

Add regression cases for both exact representations, non-Desktop rejection of the
translated form, unrelated sources, writable/extra mounts and digest mismatch. Then
request one further bounded activation with the existing 180-second readiness limit,
diagnostics-before-check and rollback behavior. No further restart or verifier change
has been performed under this diagnostic approval.

## Records

[Inputs](step-05-diagnostic/controller-boundary-input.json),
[rollback state](step-05-diagnostic/rollback-state.json),
[observer failure](step-05-diagnostic/observer.txt),
[actual diagnostic script](step-05-diagnostic/diagnostic.py.txt),
[manifest](step-05-diagnostic/SHA256SUMS).

Exports were checked for known credentials. Repository prefixes were sanitized; no
secret contents or complete controller environment were exported.
