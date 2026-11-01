# Step 6.5 — Approved JCasC bridge and inherited notification delivery

Status: **bridge implemented and locally verified; Step 6.5 still unpublished/partial**.
The user approved the base-JCasC bridge, a local controller rebuild with unchanged
pinned components, and one controller recreation.

## Implemented

`ops/jenkins/jenkins.yaml` now explicitly supplies the single non-secret
`FINSECURE_CI_NOTIFICATIONS` job-environment property from the controller environment,
using `${FINSECURE_CI_NOTIFICATIONS:-false}`. Declaring it in the base configuration
avoids relying on removal of optional JCasC to clear persisted state. The optional
notification overlay still selects true; no credentials are exported into job env.

`ops/jenkins/compose.yaml` selects local controller image
`finsecure-jenkins-controller:step-06-05`. The controller Dockerfile, pinned base,
plugin list, seed scripts, agent/builder images, privileges, ports and resource limits
were not changed. No plugin/dependency or cloud/registry publication was added.

## Actual verification

- **654 host tests passed**, including the base-JCasC false-default contract. Locked
  Ruff lint/format checks and package build passed. The initial formatting check
  required one formatting correction; both records are retained.
- Source/dependency gates passed: 29 LOW Bandit findings retained, no MEDIUM/HIGH;
  15 runtime dependencies audited with no blocking findings.
- All **73 reference plugin archives were byte-identical** before activation. The
  running plugin inventory (versions, active/enabled state) also matched after restart.
- Existing seed-script hashes were checked before activation. The new running base
  JCasC file hash matched the reviewed host file.
- The controller was recreated once while idle. Existing agent reconnected within
  the 180-second readiness limit. Memory/CPU limits and notification-mode credential,
  mount, hash, network and privilege checks passed.
- Owned native job `finsecure-notification-bridge-20261101072200` build #1 passed.
  It asserted inherited true in **both agentless and Python-agent contexts**, without
  a Pipeline `environment` block or `withEnv` override, then ran the candidate's actual
  notification cleanup block.
- One additional real SMTP message arrived in Mailpit, taking the inbox from two to
  three messages. Raw email, API metadata and an inspected native UI screenshot were
  exported. The job was disabled; Chrome and its isolated profile were removed.

This was an inline operator-triggered probe, not application CI or an SCM-triggered
build. It performed no checkout, so the email correctly says `Revision: unavailable`.
The previously published main job remains at **#25** with its old Jenkinsfile; receipt
from normal SCM CI is not claimed before the candidate is reviewed and published.

## Retained resources and limitations

Jenkins controller/agent/builder and Mailpit remain running; other monitoring and
application services remain stopped. Queue empty, agent online/idle, final boundaries
passed. The old controller image is retained for rollback. A private root-configuration
backup was retained **inside the existing controller-home volume**, at
`/var/jenkins_home/.finsecure-step65-bridge-config.xml.backup`, owned 1000:1000 with mode
0600. Its contents were never exported. Keep it through Step 6.5 review; decide cleanup
explicitly then. The image-inspection container and its newly created anonymous volume
were removed; shared named volumes/caches/history were preserved.

The false default is explicitly configured and regression-tested. A live profile-off
restart to demonstrate clearing the property was **not performed** under this
one-recreation approval. Native interruption tests, full candidate application/image
gates and exact exported-image logging remain pending. No centralized cloud logging,
Gmail/internet delivery or instructor acceptance claim.

## Records

[Manifest](step-05-bridge/SHA256SUMS),
[build/plugin comparison](step-05-bridge/build-verification.json),
[activation](step-05-bridge/activation-result.json),
[inherited-environment probe](step-05-bridge/probe-result.json),
[raw email](step-05-bridge/inherited.eml),
[screenshot](step-05-bridge/inherited.png),
[final state](step-05-bridge/completion-state.json).

Repository/temporary directory prefixes and the closed browser-debugger endpoint are
sanitized in text. Raw email and screenshots are unchanged. Known credentials were
checked before export; browser diagnostics remain visible in the retained record.
