# Step 6.5 publication — SCM build #26 and follow-up gaps

Published `f4b2c5cb45c1d27c2828e560e17fb7b4e4b61be7` to main after approval.
Automatic SCM build **#26 SUCCESS** verified the exact revision and SCM-loaded
Jenkinsfile, 654 passing tests, existing source/image gates and all 33 artifacts.
No manual build or retry was triggered. Bandit retains 29 LOW findings; Trivy's
third-party-SBOM caveat remains. Image scan reports zero known vulnerability findings.
The new image was archived, not loaded, published to a registry or deployed.

## Notification gap

Mailpit received exactly one new message, `[SUCCESS] finsecure-ci #26`, with the
correct sender, recipient, job, build result and local build URL. However its body
says **`Revision: unavailable`**, despite the correct revision in build/image metadata.
The observer's revision assertion failed; this is not a completely successful
notification provenance check. Raw receipt and an inspected real browser screenshot
are retained. The isolated browser/profile were removed; inbox now contains five.

The candidate wrapper explicitly set `env.GIT_COMMIT` after its local-bundle checkout.
That did not establish availability in the normal agentless cleanup context. A narrow
checkout-revision propagation fix and a regression test are proposed, not implemented.
Do not rewrite the received email or rerun #26 to conceal the gap.

## Configuration-bind gap

Pre-publication notification boundary verification passed. After publication, the
same verifier failed while reading `/etc/jenkins/notifications.yaml` in the controller:
`sha256sum: /etc/jenkins/notifications.yaml: No such file or directory`.
The host file exists with the approved hash and Docker still describes its read-only
bind mount. Switching through the older main checkout temporarily removed that host
file before the fast-forward restored it; a stale Docker Desktop file bind is the
likely explanation, not a proven daemon diagnosis.

The already-running controller delivered mail using its loaded configuration. That
receipt does not establish readable current JCasC input or safe future reload.
No restart, recreation, mount relaxation or cache/volume deletion was attempted.
A separately approved bounded controller recreation is proposed after idle/capacity
checks, preserving Mailpit exports, plugin pins, private rollback backup and history.
Future publication should avoid checking out an older tree that removes a live bind
source; a stable deployment-copy design would require separate review.

The queue was empty and agent online/idle before the failed boundary check. Controller,
agent, builder and Mailpit remain running; application/other monitoring remain stopped.
The first receipt-observer assertion and subsequent boundary-check failure prevented
browser-helper creation, so their following Node commands also failed with module-not-found.
A separate browser-only capture then succeeded; none of these steps retriggered CI.

## Evidence

- [Build/gate/artifact verification](step-05-scm/verification.json)
- [Actual receipt](step-05-scm/notification.eml) and [screenshot](step-05-scm/notification.png)
- [Bind diagnostic](step-05-scm/mount-diagnostic.json)
- [Observer source](step-05-scm/check-main.py.txt)
- [Manifest](step-05-scm/SHA256SUMS)

Full downloaded reports and binaries remain in Jenkins #26 and ignored
`reports/step65-main-26/`. The curated record includes their verified hashes.
Remediation and publication of this follow-up evidence remain pending review.
