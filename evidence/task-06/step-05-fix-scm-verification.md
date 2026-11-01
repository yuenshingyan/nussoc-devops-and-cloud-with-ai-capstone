# Step 6.5 — Published fix verified by automatic SCM build #27

Published `bc93c0f9d9cadbb259aa349cf31123ef6aa68e8d` after approval. Main was
fast-forwarded without checking out the older tree or touching live bind sources.
No controller restart, manual build, poll POST or retry occurred.

Automatic SCM **#27 SUCCESS** verified the exact revision and SCM-loaded Jenkinsfile:
655 tests passed with no skips/failures or pytest warning summary; lint, formatting,
packaging and existing source/dependency/image gates passed; **33 artifacts verified**.
Coverage remains observational, with no active numerical threshold. Bandit retains
29 LOW findings and no MEDIUM/HIGH; image scanning reports zero known vulnerability
findings. Trivy's existing third-party-SBOM caveat remains in the archived scan output.

Exactly one new Mailpit email arrived, `[SUCCESS] finsecure-ci #27`, with the exact
published revision, correct sender/recipient, result and build URL. Raw receipt and
an inspected browser screenshot are retained. This is actual automatic SCM delivery,
not an inline probe or a substituted candidate email. Inbox contains eight messages;
the isolated browser/profile were removed after capture.

Post-publication notification boundary verification passed: mounted configuration
readable, host/container hashes match, and existing isolation checks pass. Queue empty,
agent online/idle. Jenkins/Mailpit remain running; no application container was started.
The #27 image was verified as an archived artifact, not loaded, published or deployed.
Exact-container logging evidence remains attached to the earlier `1a1f4a3` candidate,
not relabelled as a runtime test of #27. Original #26 gaps and remediation diagnostics
remain unchanged in their historical records.

Cloud centralized logging, blocked-SMTP-socket cancellation, live profile-off switching
and instructor acceptance of local SMTP remain unverified/deferred. This completes the
approved local publication check, not every cloud requirement of Task 6.

- [Build/gate/artifact verification](step-05-fix-scm/verification.json)
- [Received email](step-05-fix-scm/notification.eml) / [screenshot](step-05-fix-scm/notification.png)
- [Final boundary and delivery checks](step-05-fix-scm/completion.json)
- [Read-only SCM observer](step-05-fix-scm/check-main.py.txt)
- [Manifest](step-05-fix-scm/SHA256SUMS)

Full reports and binary archives remain in Jenkins #27 and ignored
`reports/step65-main-27/`; their hashes are included in the curated verification record.
