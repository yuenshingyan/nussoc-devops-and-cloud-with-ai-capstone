# Step 5.2 — Verified tools and blocking image preflight

**Checkpoint, 25 October 2026 UTC.** Active branch:
`task-05/step-02-image-security-gates`, based on published `6c76293`.
This is **not** completion of Step 5.2 or proof of an enforced Jenkins image gate.
No application-base changes, ignore lists, package upgrades or release/deployment occurred.

## Tool verification and preserved agent boundary

The user approved Trivy **0.76.1**, Cosign **3.1.4**, signature verification, the strict
image policy, database freshness and timing limits. See the
[policy/checkpoint runbook](../../docs/runbooks/image-security.md).

Before executing Cosign, the existing GitHub CLI **2.95.0** verified its immutable release
asset using signed GitHub attestations. Trivy's release asset was independently verified
that way too. Download digests matched GitHub metadata and the Trivy checksum file.
Verified Cosign then checked the Trivy Sigstore bundle against the exact expected workflow
identity/tag and GitHub Actions issuer, returning **Verified OK**.

- [Asset digests/URLs](step-02-preflight/download-verification.json).
- [Cosign release attestation](step-02-preflight/cosign-release-attestation.json),
  [Trivy release attestation](step-02-preflight/trivy-release-attestation.json),
  [Sigstore bundle](step-02-preflight/trivy.sigstore.json),
  [signature verification result](step-02-preflight/trivy-signature-verification.txt).
- [Agent build log](step-02-preflight/agent-build.txt),
  [executed installation harness](step-02-preflight/install-agent.py.txt),
  [verified agent runtime/binary identity](step-02-preflight/agent-verification.json).

The agent image now pins the verified ARM64 archive by SHA-256. Its installed executable
matches the signed archive's unique regular `trivy` member. Agent image ID:
`sha256:f51d2a954718ca4b6948e8bde555d77fdf326b3715d08cff28531c8714fe2fe9`.
Credentials/history and non-root privilege/mount restrictions were preserved, and the
agent reconnected. No Docker socket, host bind, new service, port or cloud resource was added.
The application image and Jenkinsfile remain unchanged from main.

The original controller/builder/agent containers were already stopped with exit 255
when the first API check failed; no upgrade had executed then. Only the owned stack was
restarted. The shutdown cause was not investigated or inferred. The agent was upgraded
while idle; normal main's latest build remained **#7**.

## Exact image and real scanner result

The operator transferred and scanned the exact archive downloaded from normal main #7,
source **`6c762936a51a95834f1320a2383869c2aef1a230`**. It was not loaded or executed.
Archive SHA-256 matched the earlier download record; Trivy's reported image ID matched:
`sha256:577738d786429e319a04472d99a0c031c5eb49f70055d89d9e1785af988dcdac`.

- A fresh DB was downloaded solely from `ghcr.io/aquasecurity/trivy-db:2` in **31.90 s**.
- DB UpdatedAt: `2026-10-25T12:57:48.463991102Z`; age at check: **6053 s**, within 24 hours.
- The archive scan completed in **3.71 s**; both operations stayed within their individual
  300-second limits. No wrapper retry or stale/mirror fallback was used.
- Detected Debian **12.15**, **97 OS packages**, and **34 Python package records**.
- Findings: **70 HIGH, 6 CRITICAL, 111 MEDIUM, 100 LOW, 4 UNKNOWN occurrences**.
- The **76 blocking occurrences represent 29 distinct advisory IDs**; **63 occurrences
  have no listed fix**. An advisory can affect multiple binary packages.

**The approved policy would block this image.** The raw Trivy exit **0** only means this
all-severity report-generation command completed; no HIGH/CRITICAL CLI gate was requested
in this preflight. It is not evidence of a passing security gate. Jenkins gate integration
and failure-path/image-archival enforcement are still pending.

Scanner findings are not proof of exploitability. Trivy warned about potential inaccuracies
in embedded third-party SBOM data and use of other vendors' severities. Blocking Python
records include certifi, msgpack, setuptools and urllib3 attributed to an embedded SBOM
in the base layer. They are not simply the 14 application requirements audited by Step 5.1.
Further package/vendor triage is needed; no exceptions or SBOM removal were used.

## Evidence, cleanup, and next decision

- [Bounded findings/provenance summary](step-02-preflight/findings-summary.json) contains
  all 76 blocking occurrences, available fixes/statuses, archive ID/checksum, DB metadata,
  timing and full raw preflight-file SHA-256.
- [Actual DB log](step-02-preflight/database-log.txt) and
  [actual scan log with warnings retained](step-02-preflight/scan-log.txt).
- [Executed operator harness](step-02-preflight/preflight.py.txt), invoked as
  `PYTHONPATH=ops/jenkins uv run --locked python reports/preflight-step52.py`.
- [Configuration hashes](step-02-preflight/configuration-sha256.txt),
  [host checks](step-02-preflight/host-checks.txt), and
  [final status checks](step-02-preflight/final-checks.json).

Final checks passed: **316 tests**, Ruff lint/format, wheel/sdist build, Compose validation,
source scanning (17 LOW, no MEDIUM/HIGH), and auditing of 14 runtime dependencies (no known
advisories returned). These do not override the blocking image findings. Main's #7,
disabled review/demo jobs, UID 1000 and unchanged application Dockerfile/Jenkinsfile/
dependencies were checked. Document links and 336 files were checked for known live
credentials before committing this checkpoint.

The agent's owned temporary archive/cache/configuration directory was removed after results
were captured. Full raw output stays at ignored `reports/step52-preflight.json`; scanner
binaries, database contents and image archives are not committed. Public attestations and
curated diagnostics are retained; host repository paths/trailing whitespace are normalized.
The original main/review/demo build histories and named volumes remain intact.

Before changing the application base or runtime contents, agree remediation scope: evaluate
updated digest-pinned Python 3.14 bases (including a newer Debian variant) and removal of
genuinely unnecessary packaging tools, then rescan and reverify application behavior.
A newer base is not guaranteed to remove every finding. The strict policy is unchanged.
No image publication, base change, pipeline-gate completion, or remediation success is claimed.
