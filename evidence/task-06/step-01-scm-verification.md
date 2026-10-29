# Step 6.1 — Published main and normal SCM verification

On 29 October 2026 UTC, after explicit approval, `main` was fast-forwarded from
`d76b713` to `cc25ae3913088ae59faf529b092a1aac5a82e227` and pushed to the existing
GitHub remote. No force-push, registry publication or cloud deployment occurred.

The existing `finsecure-ci` SCM polling trigger automatically started **build #17**.
The observer used GET requests only, checked the SCM cause and Pipeline-from-SCM
configuration, and verified checkout of that exact revision. No manual build/poll
request, retry, inline candidate wrapper or job reconfiguration was used.

## Actual results

- **SUCCESS: 538 passed, zero failed/skipped**, with no pytest warning summary.
- Coverage: 194/194 application lines and 37/38 branch outcomes. Quality gate inactive.
- Lint, format, package build and source/dependency gates passed. Bandit retained
  21 LOW findings and no MEDIUM/HIGH findings; all 15 runtime dependencies audited
  with no known advisories. Exported artifact hashes matched `uv.lock`; no audit warning.
- Exact ARM64 application image gate passed: no known findings at any severity.
- **33 artifacts** downloaded and checked, including package/image manifests,
  source/lock identity, runtime inventory and image revision/tag/config identity.
- Image ID: `sha256:82b5d38ad3ec729ff3e4f7f282a15612c2045a0435b87018667d79ffb8732836`.
- Archive SHA-256: `7a9aef8337ba95be1bdb4d3263754c3f919d6f50f05ea5b1334409fbfa7fd52c`.

[Verification record](step-01-scm/verification.json),
[sanitized console](step-01-scm/console.txt),
[JUnit summary](step-01-scm/junit-api-summary.json),
[source/dependency gate](step-01-scm/reports/security-summary.json),
[image gate](step-01-scm/reports/image-security-summary.json), and
[historical GET-only observer](step-01-scm/check-main.py.txt).
Full artifacts remain in local Jenkins at `http://127.0.0.1:8080/job/finsecure-ci/17/`;
this is not a publicly accessible CI link. Large package/image archives remain outside Git.

## Scope and current state

This closes the normal SCM-verification gap for the approved local metrics subset.
The new main image was **not loaded or run** in this follow-up. The separate real
Prometheus demonstration remains tied to candidate `2328b9c` and its exact image,
as recorded in the [original evidence](step-01-metrics.md); do not relabel that
execution as a test of build #17's archive.

Monitoring containers remain stopped; their named TSDB volume is retained. The
registry release/Kubernetes pins remain at the previously published 0.2.0 image.
Managed-cluster metrics, dashboards, alerts and centralized logging are not completed
by this follow-up. This documentation-only evidence commit is separate from the
verified application commit; no claim is made that its own revision ran in build #17.
