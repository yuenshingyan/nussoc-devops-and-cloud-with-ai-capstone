# Step 6.3 blocker — Docker storage failure during scanner investigation

## Findings, not a completed repair

The image gate already creates a fresh per-run temporary Trivy cache and removes it
through `TemporaryDirectory` cleanup, including on scanner failure. The failed #22
cache directory was confirmed absent. There is no retained original database checksum
or byte copy; deleting a shared cache is not a justified diagnosis/remediation.

The original failed image archive remained in the Jenkins workspace. One isolated
comparison was attempted with the same pinned Trivy binary and a copied, checksum-
verified image. The diagnostic used a new directory, not the CI workspace/cache, and
was intended to retain database hashes before/after scanning. It did not trigger a
Jenkins build or change scanner/gate policy.

The probe failed to save its result with **`OSError: [Errno 5] Input/output error`**.
Its final result is unavailable; no fresh-download or scan success is claimed. The
probe directory `/home/jenkins/agent/trivy-diagnostic-build22` may contain partial
artifacts and must not be treated as verified evidence without recovery/inspection.
No diagnostic directory or cache was deliberately deleted.

## Subsequent read-only observations

On 31 October 2026:

- `docker ps` timed out after 20 seconds.
- Jenkins's loopback login endpoint could not be reached (curl exit 7, HTTP 000).
- Docker VM kernel logs at **12:00:55–12:00:56 UTC** report write I/O errors on `vda1`,
  an aborted EXT4 journal, superblock write errors, then **remounting read-only**.
- Docker's host virtualization log at **12:02:43 UTC** reports **no space left on
  device** while writing its console log.
- A later host disk check reported about **12 GiB free**, 94% capacity on the data
  volume. That later reading does not disprove earlier exhaustion, or prove its cause.
- Docker's backing `Docker.raw` file has a logical size of 60 GiB; that is not a
  measurement of allocated blocks or a verified backup-space requirement.

These observations confirm a Docker storage/filesystem failure. They do **not** prove
that storage exhaustion caused the earlier #22 Trivy panic at approximately 11:07 UTC,
or establish whether the original upstream database content was valid.

[Bounded log observations](step-03-storage-investigation/storage-observations.json),
[probe error](step-03-storage-investigation/probe-output.txt),
[historical probe](step-03-storage-investigation/probe.py.txt), and
[hash manifest](step-03-storage-investigation/SHA256SUMS).

## Safety boundary and next decision

No Docker restart, factory reset, prune, volume deletion, filesystem repair, scanner
upgrade or CI retry was performed by the assistant. Current Docker volume integrity
and service states cannot be verified while the engine is unresponsive. Earlier clean
shutdown records must not be represented as a current health check.

Pause further Docker writes. Recovery requires an explicit data-preservation/backup
plan with sufficient destination space, then approval before stopping/restarting
Docker or performing filesystem repair. Do not factory-reset Docker or discard its
backing disk: Jenkins history, credentials and retained monitoring volumes are at risk.
The host Git repository and sanitized evidence remain available. Alert demonstration
and normal image-gate verification remain blocked.
