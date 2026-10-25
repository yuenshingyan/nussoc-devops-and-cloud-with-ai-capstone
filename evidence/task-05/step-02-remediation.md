# Step 5.2 — Candidate base-image remediation study

**25 October 2026 UTC; local, unpublished candidates only.** The user approved testing
updated digest-pinned Python 3.14 bases and removing unnecessary runtime packaging tools.
The application Dockerfile, dependency lock, Jenkinsfile and public releases remain
unchanged. This is **not a completed Jenkins image gate**, a release, or a deployment.
Alpine adoption is proposed for review because it changes libc as well as the distribution.

## Findings and scoped remediation

Inspection of the original #7 archive found the SBOM at
`usr/local/lib/python3.14/site-packages/pip/_vendor/bom.cdx.json`, alongside real vendored
certifi, msgpack, pkg_resources and urllib3 trees. The bundled README says setuptools is
stripped down to pkg_resources. A package-level SBOM advisory therefore need not describe
all code actually shipped, and a scanner finding alone does not establish exploitability.
See [observed file provenance/counts](step-02-remediation/vendor-triage.json) and
[pip's vendoring policy](https://github.com/pypa/pip/blob/26.2.1/src/pip/_vendor/README.rst).

A separate vendor-status caveat is
[Debian's CVE-2023-45853 note](https://security-tracker.debian.org/tracker/CVE-2023-45853):
Bookworm's zlib does not build the affected contrib/minizip code, and Debian marks that
source-package issue ignored for that suite. **No exception was introduced**, and this
observation is not a claim that all remaining findings are false positives.

The candidates use updated official Python **3.14.9** bases. Runtime stages uninstall the
**whole pip package**, including its vendored code, then remove **the whole ensurepip
module and bundled wheels**. This is not selective SBOM deletion. The API installs
nothing at runtime; the locked builder still supplies `/opt/venv`. OS package databases
remain intact for scanning. Deleted files may remain in immutable lower image layers;
the runtime filesystem no longer exposes those tools, rather than erasing historical bytes.

The Alpine candidate additionally replaces Debian's account-creation commands with
BusyBox equivalents, preserving numeric UID/GID **10001:10001**, no home creation and
non-root execution. It uses **musl rather than glibc**; native wheel compatibility must
be retested when dependencies change. No dependency versions or API contracts changed.

## Actual build/scan comparison

All candidates were built by the operator's Docker Engine, not Jenkins/rootless BuildKit.
Each exact compressed Docker export was hashed and transferred to the verified Trivy
agent. Each scan used a separate temporary cache, fresh official-GHCR database download,
explicit empty ignore/config files, offline OS/library scanning, and the already approved
five-minute download/five-minute scan limits. No fallback, ignore rule, unfixed filtering,
or automatic retry was used. Temporary agent inputs/cache were removed.

| Candidate | Architecture | OS packages / Python records | HIGH | CRITICAL | Distinct blocking IDs |
|---|---|---:|---:|---:|---:|
| Original #7, Python 3.14.7 / Debian 12.15 | ARM64 | 97 / 34 | 70 | 6 | 29 |
| Python 3.14.9 / Debian 12.15, packaging tools removed | ARM64 | 97 / 15 | 61 | 2 | 16 |
| Python 3.14.9 / Debian 13.7, packaging tools removed | ARM64 | 87 / 15 | 44 | 0 | 8 |
| Python 3.14.9 / Alpine 3.24.3, packaging tools removed | ARM64 | 30 / 15 | 0 | 0 | 0 |
| Same Alpine candidate | AMD64 | 30 / 15 | 0 | 0 | 0 |

Both Alpine scans reported **zero known findings at any severity**, with the 14 locked
runtime dependencies plus the application present. This is a point-in-time result, not a
claim of vulnerability-free software. Both Debian candidates still violate the unchanged
policy; every remaining HIGH/CRITICAL occurrence has no listed fix. They were not run as
application services. Neither candidate is substituted for the working baseline.

For these four new scans, the DB UpdatedAt was `2026-10-25T12:57:48.463991102Z`, checked
at ages **7386–7940 seconds**, below 24 hours. Downloads took **27–82 seconds**, scans
**3–8 seconds**. All scanner exits were 0: this all-severity preflight reports findings
without requesting a HIGH/CRITICAL exit code. Debian's exit 0 therefore does **not** mean
policy compliance. `--exit-on-eol 2` was enabled; recognized OS inventories were returned.

### Exact inputs and reports

- [Pinned references and Dockerfile digests](step-02-remediation/candidates.json),
  [image IDs, export hashes and application-tree baseline](step-02-remediation/builds.json).
  Baseline application tree: **`01cc819`**. The effective candidate Dockerfiles are separate
  review inputs, not the Dockerfile at that commit; they were supplied via `--file` and
  their base defaults overridden by the explicitly recorded digest-pinned build argument.
- Exact [Debian candidate Dockerfile](step-02-remediation/Dockerfile.runtime-candidate) and
  [Alpine candidate Dockerfile](step-02-remediation/Dockerfile.alpine-candidate).
- Exact-version registry indexes:
  [Bookworm](step-02-remediation/python-3.14.9-bookworm-index.txt),
  [Trixie](step-02-remediation/python-3.14.9-trixie-index.txt),
  [Alpine](step-02-remediation/python-3.14.9-alpine-index.txt).
  The selected Alpine index is
  `sha256:dbeb11d16bb95c3a7e3c25c842cb9f20cbc8c18f8be0461a4a0dcc861ad386a0`.
- [Comparison with every remaining blocking occurrence](step-02-remediation/scan-summaries.json).
- Complete Alpine scan outputs:
  [ARM64](step-02-remediation/alpine-arm64-scan.json),
  [AMD64](step-02-remediation/alpine-amd64-scan.json).
- Build and DB/scan logs are alongside these files. Full Debian raw outputs stay in
  ignored `reports/step52-remediation/`; their hashes are in
  [provenance](step-02-remediation/provenance.json).

## Compatibility actually exercised

Only the two Alpine images with no reported findings were run as application services.
ARM64 execution was native; **AMD64 execution/build RUN steps were emulated** on Apple Silicon.

1. Runtime inspection verified Python **3.14.9**, musl-linked pydantic-core, and absence of
   pip/ensurepip and pip launchers: [ARM64](step-02-remediation/alpine-arm64-runtime.json),
   [AMD64](step-02-remediation/alpine-amd64-runtime.json).
2. Existing HTTP smoke tests passed health, accepted transaction, business rejection and
   schema rejection, with UID/GID 10001, read-only root, dropped capabilities,
   no-new-privileges, loopback-only access, clean exit 0 and container removal:
   [ARM64](step-02-remediation/alpine-arm64-smoke.json),
   [AMD64](step-02-remediation/alpine-amd64-smoke.json).
3. **316 tests passed on each architecture**, no failures/errors/skips. Separate test-only
   images added locked development tools to `/testenv`, without reinstalling the project.
   `PYTHONPATH` selected the candidate's actual installed application/runtime packages in
   `/opt/venv`; import provenance is retained. Tests ran with networking disabled and a
   read-only root. Coverage on each: **125/125 lines and 28/28 branch outcomes**, no new
   threshold. [Procedure/status](step-02-remediation/compatibility.json),
   [ARM64 test output](step-02-remediation/alpine-arm64-compatibility-tests.txt),
   [AMD64 test output](step-02-remediation/alpine-amd64-compatibility-tests.txt).
   JUnit, Coverage XML and import-provenance files are retained alongside these outputs.
   Test-only images contain extra tooling and are not the scanned runtime candidates.
4. Reused the Step 3.2 local safeguard harness with **0.5 CPU / 256 MiB**, no extra swap,
   16 MiB writable `/tmp`, no capabilities, seccomp and no-new-privileges. Both passed
   25 accepted requests, rejection/health checks, UID/GID checks, bounded memory with
   no OOM, clean shutdown and removal:
   [ARM64](step-02-remediation/alpine-arm64-constrained.json),
   [AMD64](step-02-remediation/alpine-amd64-constrained.json).
   These are local compatibility observations, **not Kubernetes scheduling/probe execution,
   load testing, a latency SLA or a cluster deployment**.

## Final repository checks

[Host checks](step-02-remediation/host-checks.txt) passed: **316 tests**, Ruff lint/format,
wheel/sdist build, Compose validation, source gate (17 LOW, no MEDIUM/HIGH) and audit of
14 locked runtime dependencies (no known advisories returned). These do not supersede
image scan results. [Final validation](step-02-remediation/final-checks.json) checked
archive/Dockerfile hashes, Alpine package inventories against the lock, actual coverage
paths under `/opt/venv`, cleanup, main #7, idle/online agent, empty queue and disabled
review/demo jobs. Document links and 386 files were checked for known live credentials.

## Procedures, caveats and remaining work

Saved operator procedures: [Debian builds](step-02-remediation/build-debian.py.txt),
[Alpine builds](step-02-remediation/build-alpine.py.txt),
[scans](step-02-remediation/scan-candidates.py.txt),
[compatibility suite](step-02-remediation/test-alpine.py.txt),
[constrained runtime](step-02-remediation/constrained-runtime.py.txt).
The scan wrapper uses the remote scan program from the
[earlier preflight harness](step-02-preflight/preflight.py.txt). Its explicit candidate
selection/no-overwrite guard was added before the Alpine scans; the remote procedure was
unchanged across all four scans. These are historical procedures, not instructions to
blindly overwrite retained tags/reports. Builders refuse existing review tags.

Operator inspection corrections, not scanner retries: compressed inner archive layers
required tar auto-detection; the broad Alpine alias and exact version had different index
digests, so the exact-version index was independently inspected and pinned; XML report
inspection needed the locked environment rather than system Python for defusedxml.
Existing Starlette/HTTPX deprecation warnings and pip's root-user uninstall warning remain
visible. Test-only Dockerfiles warn about an unset default for their required base-image
argument; each build supplied the explicit candidate tag, whose image ID was checked.
Warnings were retained rather than hidden by blanket filters.

**Recommended next decision:** adopt the tested Python 3.14.9/Alpine 3.24 digest and the
complete runtime-tool removal, then implement and verify the already approved Jenkins
image gate. Obtain approval for the libc/distribution adoption first. Rootless candidate
CI, actual gate/error/archival enforcement and normal SCM verification remain pending.
Current root Dockerfile/Jenkinsfile and main #7 remain unchanged. Review images/archives
are isolated locally, containers/cache were removed, and no image/source publication or
cloud operation occurred.
