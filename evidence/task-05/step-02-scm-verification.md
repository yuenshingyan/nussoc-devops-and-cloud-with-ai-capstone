# Step 5.2 — Post-merge SCM verification

On 28 October 2026, following explicit user approval, Step 5.2 was fast-forward
merged into `main` and both main and the step branch were pushed to GitHub at
`3d3aaa6dcb4ca14bd19d273b0f23c0964dcbc6f6`.

Existing local Jenkins services were restarted through the bootstrap, preserving
credentials, volumes and history. The queue was empty and build #7 was complete
before publication. No manual build or polling request was sent.

## Observed results

Normal `finsecure-ci` **build #8 succeeded**, with `SCMTriggerCause`. Its Jenkinsfile
was loaded from Git, and its checkout matched the published revision.

- **410 tests passed**, none failed/skipped. Ruff checks and packaging passed.
- Application coverage: 125/125 lines and 28/28 branch outcomes; no coverage gate.
- Source gate passed: 19 LOW, zero MEDIUM/HIGH Bandit findings. LOW findings remain visible.
- All 14 locked runtime dependencies passed pip-audit.
- Fresh Trivy 0.76.1 image gate passed with no known findings at any severity.
- All **33 artifacts** were downloaded and checksum-recorded. Package manifests,
  image archive identity, source-file hashes, lock hash, and image-gate report hashes
  were checked. The scanned image matches the archived ARM64 image.
- Existing isolated failed-test demonstration job remains disabled with four builds.

[Verification record](step-02-scm/verification.json),
[sanitized console](step-02-scm/console.txt),
[test summary](step-02-scm/junit-api-summary.json),
[coverage](step-02-scm/coverage-api.json),
[source gate](step-02-scm/security-summary.json),
[image gate](step-02-scm/image-security-summary.json),
[Trivy report](step-02-scm/trivy.json), and
[database metadata](step-02-scm/trivy-db.json).

The [GET-only observer](step-02-scm/check-main.py.txt) was adapted from Step 5.1 to
check 410 tests and the new image reports, with a 35-minute observation deadline.
It used the [pre-push baseline](step-02-scm/before.json). Live credential values
were checked privately before artifact saving; console values were redacted.
Binary artifacts remain in local reports and Jenkins, not Git.

## Warnings and limits

The Starlette/HTTPX deprecation warning remains visible; no dependency changes or
warning suppression were made. The existing pip-audit hash-export recommendation
also remains in its report. These are not failed gates.

This follow-up did not load/run the exported image again. Prior candidate runtime
checks remain separate evidence. No registry publication, cloud deployment,
rollout/rollback or later task was performed. Published 0.2.0 release tags and the
Kubernetes image pin remain unchanged. A passing scan is time-bound, not proof of
vulnerability-free software.
