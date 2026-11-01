# Step 6.4 — Published evidence and automatic SCM verification

Reviewed Step 6.4 evidence was merged and published as
`ab36eb567abfa617a811e3919fdc3ac0de1f3051` after approval. Normal Jenkins
`finsecure-ci` build **#25 SUCCESS** checked out that revision and has verified
SCM-trigger provenance, not an operator-triggered recovery cause.

- 584 tests passed; source, dependency and image gates passed.
- 33 artifacts were downloaded and checked by the retained observer.
- Bandit retained 29 LOW findings, no MEDIUM/HIGH findings.
- Image scan reported zero known findings at every severity.
- No application outage, email delivery, deployment or registry publication occurred
  during this follow-up. The earlier actual alert emails are separate demonstration
  evidence. Jenkins build notifications were not configured in this revision.
- `main` and `origin/main` matched the revision; monitoring remained stopped.

Records: [verification](step-04-scm/verification.json),
[observer](step-04-scm/check-main.py.txt),
[pre-publication build/revision boundary](step-04-scm/before.json),
[hash manifest](step-04-scm/SHA256SUMS).

This verification covers the published Step 6.4 revision, not subsequent Step 6.5
planning or implementation. The previous Trivy failure in #22 remains recorded;
a successful later build does not identify its original cause.
