# Step 6.3 blocker — Isolated post-recovery scanner comparison

Following approved Docker recovery, the user authorized continuation of the isolated
comparison. **No Jenkins build was retried and no gate/scanner policy was changed.**

## Inputs and capacity

The agent was online/idle, Jenkins queue empty, latest main build still #22 FAILURE.
Host free space was approximately 13 GiB and VM free space approximately 16 GiB before
execution; afterwards approximately 11 GiB and 14 GiB respectively. No allocation
increase, shared-cache reset, prune or deletion was performed.

A new owned directory `/home/jenkins/agent/trivy-diagnostic-build22-recovered` retained
its own image copy, empty configuration/ignore file, Docker configuration directory,
database and reports. It did not overwrite the earlier interrupted diagnostic.

- Exact #22 archive SHA-256:
  `b7687517a78a302a939e6a1751c0ea1ab0e7bdaa2322b6a7bad50c7d02254373`.
- Same pinned Trivy 0.76.1 binary SHA-256:
  `b422130ea54e53e142e65c838662e48919ce9c3f23f17d80066b43e70550cb85`.
- Database repository unchanged: `ghcr.io/aquasecurity/trivy-db:2`.
- One download and one offline image scan, each bounded to 300 seconds. All severity
  classes and OS/Python inventory were requested; parallelism remained 1. No ignores
  or report acceptance rules were relaxed.

## Actual result

Download exited 0; scan exited 0. The existing `image_result` validation accepted the
report's identity, timestamp, nonroot ARM64 configuration, supported OS, complete
inventories and every locked application runtime package. Existing database-age policy
also passed (about 4,558 seconds old at completion).

- Alpine 3.24.3: **30 OS packages**.
- Python: **16 packages**, including the application and 15 locked dependencies.
- **Zero known findings at every severity**, no OS end-of-life flag.
- Archive checksum unchanged before/after the operation.
- Database size 1,674,162,176 bytes; SHA-256 unchanged before/after:
  `d81ea576fbcd02c304b980d8eec4dd1a372648b648bfb876f48790d63ee58f93`.

[Validated comparison](step-03-scanner-comparison/validated-comparison.json),
[raw probe result](step-03-scanner-comparison/result.json),
[Trivy report](step-03-scanner-comparison/trivy.json),
[scanner output](step-03-scanner-comparison/scan.txt),
[database metadata](step-03-scanner-comparison/database-metadata.json),
[download output](step-03-scanner-comparison/database-download.txt), and
[historical probe](step-03-scanner-comparison/probe.py.txt).

The usual third-party SBOM accuracy warnings and license informational message remain
in scanner output. They were not suppressed. A successful complete report is not a
claim that every upstream advisory or SBOM is accurate.

## Conclusions and limits

The same image/scanner can now complete successfully after storage recovery using a
fresh database. However, **the new database metadata identifies a different snapshot
from #22**. The original failed database was removed by the gate's existing temporary-
directory cleanup. The exact cause of the original bbolt panic is therefore **not proven**;
this comparison cannot isolate original database content from storage/environment effects.

The earlier interrupted diagnostic contains an incomplete database and no scan result.
Both that directory and the new successful comparison directory are retained separately
on the agent volume; large database/image files are not committed to Git. These retained
files consume space and must be considered before another large operation. No speculative
scanner upgrade, gate bypass or cache-repair policy was introduced.

**Build #22 remains FAILURE and its CI image archive remains withheld.** This standalone
scan does not retroactively make that build successful, or replace normal SCM verification
of a future approved publication. No image was loaded/run/published, and no monitoring
service, outage demo or email delivery was started.

[Completion state](step-03-scanner-comparison/completion-state.json) and
[SHA-256 manifest](step-03-scanner-comparison/SHA256SUMS). Review the accumulated recovery
and comparison evidence before publication and a new normal SCM build.
