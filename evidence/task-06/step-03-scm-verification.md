# Step 6.3 — Published main and normal SCM verification

After approval, main was fast-forwarded from `c27a2e8` to
`dcab1c52ec530e07cce90f77b3f0f267002ef0b2` and pushed to the existing remote.
Automatic SCM polling started `finsecure-ci` **#21**, which completed **SUCCESS**.
The GET-only observer checked the SCM cause, Pipeline-from-SCM configuration, exact
revision, package/image identities and all **33 archived artifacts**. No manual build
trigger, retry, Jenkins reconfiguration or force-push was used.

## Verified results

- **584 tests passed**, zero failed/skipped, no pytest warning summary.
- Ruff lint/format, package build and source/dependency gates passed.
- Bandit: **29 LOW**, no MEDIUM/HIGH. All **15 runtime dependencies** audited with no
  known advisories. Exported artifact hashes matched `uv.lock`; no audit warning.
- Application coverage: 194/194 lines, 37/38 branch outcomes; quality gate inactive.
- ARM64 application image gate passed: zero known findings at all severities.
- All 33 downloads, manifests, source/lock hashes and image metadata verified.

[Verification](step-03-scm/verification.json), [console](step-03-scm/console.txt),
[JUnit summary](step-03-scm/junit-api-summary.json),
[source/dependency gate](step-03-scm/reports/security-summary.json),
[image gate](step-03-scm/reports/image-security-summary.json), and
[SHA-256 manifest](step-03-scm/SHA256SUMS).

Full artifacts remain at `http://127.0.0.1:8080/job/finsecure-ci/21/` (local, not public).
Large downloaded images/packages stay outside Git. The historical
[observer](step-03-scm/check-main.py.txt) made GET requests only.

## Scope is unchanged

The #21 image was **not loaded or executed**. Earlier local native-rule tests and SMTP
receiver preflight retain their own provenance; they were not rerun inside this CI job.
All monitoring services remain stopped and owned persistent volumes are retained.
No outage or SMTP DATA/email delivery was generated. Actual firing/recovery receipt
and browser evidence remain Step 6.4; Jenkins notifications remain Step 6.5.

The previously recorded temporary-storage, network, observer and exit-137 failures
remain in the [original evidence](step-03-alert-configuration.md). Passing CI does not
resolve those historical observations or provide full third-party Alertmanager/Mailpit
image vulnerability assurance. No registry publishing or cloud deployment occurred.

This documentation-only follow-up is separate from the verified `dcab1c5` revision;
its own commit did not run in #21.
