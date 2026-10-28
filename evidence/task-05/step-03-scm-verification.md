# Step 5.3 — Local subset post-merge verification

On 28 October 2026, following explicit approval, the audit and local boundary
verifier were merged into `main` and published at
`1ace992bd9d249431e15ed0bd8579f64b346a7cd`. The queue was empty and previous build
#13 had completed SUCCESS. No manual build or polling request was sent.

Normal **finsecure-ci build #14 succeeded**, with SCMTriggerCause. It loaded its
Jenkinsfile from Git and checked out the exact approved revision.

- **503 tests passed**, none failed/skipped; no pytest warning summary.
- Ruff, packaging, source/dependency and fresh image gates passed.
- Bandit retained **21 LOW**, no MEDIUM/HIGH findings; no suppressions added.
- All 14 locked runtime dependencies were audited; no advisories or audit warnings.
- All **33 artifacts** were downloaded and verified, including package manifests,
  exported image identity, source/lock/report hashes, and lock-bound dependency hashes.
- Application coverage: 125/125 lines and 28/28 branch outcomes, no coverage gate.
- The operator separately ran `uv run --locked python ops/jenkins/verify_secrets.py`
  from the approved source. It passed against the actual local services. It was
  **not** run inside Jenkins; the agent did not receive Docker access.

[Build verification](step-03-scm/verification.json),
[sanitized console](step-03-scm/console.txt),
[test summary](step-03-scm/junit-api-summary.json),
[source gate](step-03-scm/security-summary.json),
[image gate](step-03-scm/image-security-summary.json), and
[operator boundary result](step-03-scm/operator-boundaries.json).

The retained [GET-only observer](step-03-scm/check-main.py.txt) used the
[pre-push baseline](step-03-scm/before.json), verified all source hashes against Git,
and used the hash-aware parser with the lock from that same revision. Known live
Jenkins credential values were checked before saving artifacts; raw secrets were
not saved. Binary exports remain outside Git. The disabled failed-test demo job
still had four builds and remained disabled.

## Boundaries

This verifies the approved **local subset**, not all of Step 5.3. Live credential
rotation, provider RBAC/encryption controls and registry/cloud credentials remain
deferred. The trusted single-operator model and agent-secret read access are
unchanged. No credentials, permissions, authorization settings or service lifecycle
were changed. No registry publication, deployment, or additional image runtime
smoke test occurred. This is not a live misconfiguration/failure demonstration;
negative boundary checks remain deterministic tests using synthetic external inputs.

See the [secret-management runbook](../../docs/runbooks/secret-management.md) for
the full scope, audit limitations and deferred decisions.
