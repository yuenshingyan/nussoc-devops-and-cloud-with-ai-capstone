# Step 6.3 evidence publication — SCM build #22 scanner failure

The approved documentation follow-up was fast-forwarded/published as
`d89a0c437c9d5845da5085871f3f45a1bc7795ce`. Automatic normal SCM build #22 failed.
This does not replace the successful #21 result for `dcab1c5`.

## Observed results

- Ruff lint/format, all **584 tests**, package build and source/dependency gates passed.
- Bandit retained 29 LOW, no MEDIUM/HIGH; runtime dependency audit passed.
- The application image built, but Trivy 0.76.1 crashed during vulnerability scanning:

```text
panic: assertion failed: Page expected to be: 281746, but self identifies as 0
```

The stack includes `go.etcd.io/bbolt` page checks and Trivy advisory database reads.
Database download returned 0, reported database age was about four hours, and scanner
exit code was 2. The wrapper reported `execution_identity_or_report_invalid` in its
report phase. These facts indicate a scanner/database failure, **not a completed
vulnerability verdict**. The root cause (including whether local cache or upstream
content is responsible) has not been established.

The gate failed closed: **31 artifacts were archived, without the application image
archive**. No zero-vulnerability claim or full successful-artifact verification is made
for #22. The scanner also emitted its third-party SBOM warnings; these are preserved.

[Result](step-03-scm-failure/result.json), [console](step-03-scm-failure/console.txt),
[gate summary](step-03-scm-failure/image-security-summary.json),
[scanner output](step-03-scm-failure/trivy.txt),
[database output](step-03-scm-failure/trivy-db.txt), and
[SHA-256 manifest](step-03-scm-failure/SHA256SUMS).

The observer stopped at the failed build rather than selecting a passing retry.
No automatic retry, cache deletion, scanner upgrade, gate weakening, image execution,
registry publication or cloud deployment was performed. Monitoring remains stopped.
Investigate and preserve database/cache provenance before choosing remediation;
actual alert/email demonstration remains pending.
