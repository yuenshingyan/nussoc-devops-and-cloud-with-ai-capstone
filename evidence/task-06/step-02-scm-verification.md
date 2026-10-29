# Step 6.2 — Published main and normal SCM verification

After approval, `main` was fast-forwarded from `5e53c5f` to
`f61cb4f82039ff4327fc7dcbc958a69a4bbb48e4` and pushed to the existing GitHub remote.
No force-push, image-registry publication or cloud deployment occurred.

Existing SCM polling automatically started `finsecure-ci` **build #19**. The GET-only
observer verified the SCM cause, Pipeline-from-SCM configuration, exact checkout,
reports and all **33 archived artifacts**. No manual trigger, retry, candidate wrapper
or Jenkins reconfiguration was used.

## Actual results

- **SUCCESS: 578 tests passed, zero failed/skipped**, with no pytest warning summary.
- Ruff lint/format, package build and source/dependency gates passed.
- Bandit retained **29 LOW**, no MEDIUM/HIGH findings. All **15 runtime dependencies**
  audited with no known advisories; exported hashes matched `uv.lock`, with no audit warning.
- Application coverage: **194/194 lines, 37/38 branch outcomes**, quality gate inactive.
- Exact ARM64 application image gate passed with no known findings at any severity.
- Package/image manifests, source/lock identities, inventory, image revision/tag/config
  identity and all 33 downloads were checked.

[Verification record](step-02-scm/verification.json),
[sanitized console](step-02-scm/console.txt),
[JUnit summary](step-02-scm/junit-api-summary.json),
[source/dependency gate](step-02-scm/reports/security-summary.json), and
[image gate](step-02-scm/reports/image-security-summary.json).

Full artifacts remain in local Jenkins at
`http://127.0.0.1:8080/job/finsecure-ci/19/` (not a public CI link).
Large package/image downloads remain outside Git.

## Scope and retained limits

This closes the normal SCM-verification gap for Step 6.2's approved local scope.
The build #19 archive was **not loaded or executed** in this follow-up. The actual
Grafana screenshot remains tied to its original run and main build #18 application
image, as recorded in the [dashboard evidence](step-02-dashboard.md). No additional
synthetic traffic or screenshot capture was performed.

All three monitoring services remain stopped, and Prometheus/Grafana data plus the
secret volume are retained. Credentials were not rotated. Previously recorded
Grafana/browser diagnostics remain unresolved; a green CI run does not remove those
runtime observations or establish third-party Grafana image vulnerability coverage.

No alerting, notification delivery, managed-cluster metrics or centralized logging
was added. Registry release/Kubernetes pins remain unchanged. This documentation-only
follow-up is separate from the verified commit; its own revision did not run in #19.
