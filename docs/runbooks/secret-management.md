# Secret management — Step 5.3 local boundary verification

## Status and scope

Branch: `task-05/step-03-secret-management`, from reviewed `main` at `8fd7a36`.
The user approved automated boundary checks while retaining the trusted-local model
and deferring live rotation/cloud credentials. The **local subset is approved,
merged/published as `1ace992`, and SCM-verified in build #14 (503 tests)**. The
separate post-merge operator check also passed; see
[follow-up evidence](../../evidence/task-05/step-03-scm-verification.md).
Full cloud credential/RBAC and rotation verification remain deferred, so this is not
completion of every Step 5.3 requirement. No credentials were created, rotated,
revoked, printed or transferred to a new service. No permissions, Jenkins
authorization, infrastructure or application code were changed. No cluster was contacted.

The application validates synthetic transactions and currently requires **no secret**.
Do not add an application secret, Kubernetes Secret or private-registry pull secret
merely to demonstrate a feature. Public source/image reads do not require credentials.

## Inventory and actual boundaries

| Credential or capability | Current handling | Verification and limits |
| --- | --- | --- |
| Host Git publication | macOS Keychain Git credential helper | Helper configuration observed; no stored token retrieved, scope/expiry or account privilege checked |
| Host Docker publication | Docker credential store | Store configured; no nonempty inline `auth` entries in host config; no helper secrets retrieved or token scope/expiry checked |
| Jenkins admin password | Private host file; separate controller secret volume | Host directory 0700, file 0600 and not a symlink; container file 0400 owned by 1000:1000; read-only secret mount |
| Jenkins agent remoting secret | Separate agent secret volume; `-secret @/run/secrets/agent_secret` | File 0400 owned by 1000:1000; read-only mount; no known secret value in container argv/environment |
| CI Git checkout | Public anonymous HTTPS, trusted `*/main` | Live job configuration has no nonempty SCM credential ID |
| CI image export | Separate rootless BuildKit, temporary empty `DOCKER_CONFIG` | No host Docker socket/bind mount; builder has no secret mount or published port |
| Registry/cloud release credentials in CI | Not configured by tracked pipeline/setup | No publishing/deployment stages; this audit did not enumerate every possible credential store/plugin entry |
| Kubernetes application identity | Manifest disables service-account token automount | Static configuration only; no live RBAC/provider encryption or cluster verification |

The controller exposes only `127.0.0.1:8080`; the live anonymous API request returned
403. Controller, agent and builder are non-privileged containers. The builder's
existing narrowly scoped capability/security-profile exceptions are documented in
[local image building](local-image-builder.md); non-privileged does not mean it has
no additional privileges.

Bootstrap passes secret material through stdin to owned short-lived helpers, not
argv/environment. Its administrative HTTP client bypasses proxies and refuses
redirects. CI artifacts use an exact allowlist rather than archiving the workspace.
These are code/configuration observations, not proof that arbitrary future scripts
cannot leak credentials.

## Trust model and unresolved risks

- The current authorization policy gives every authenticated Jenkins user full
  control. Signup is disabled and the tracked configuration defines one admin.
  This is a trusted single-operator local setup, **not** least-privilege multi-user
  authorization. Do not add users or expose it publicly under this policy.
- Build code runs as the same UID as the agent and can read the agent remoting
  secret. A read-only mount prevents writes, not reads. Trusted main and explicitly
  reviewed candidate jobs are the current boundary; do not run untrusted PR code.
- Docker administrators and the host account can access Docker volumes and local
  credential material. Named secret volumes/file modes are not an encrypted vault.
  Jenkins home also holds sensitive controller state; do not export it as evidence.
- Loopback/private Docker HTTP is a local trust assumption, not TLS protection.
  Shared/remote hosting requires a separately approved authentication/network design.
- Keychain/store configuration is not evidence of least-privilege token scopes,
  expiry, revocation, MFA or access policies. Those require private operator review.
- No backup/retention/recovery guarantee, automated rotation or encryption-at-rest
  claim has been established. Do not delete volumes/password files as a recovery
  shortcut. Retained logs/history must not be published wholesale.

## Actual audit on 28 October 2026

The audit compared current Jenkins admin/agent secrets and derived Basic-auth values
in memory against tracked content, reachable Git blobs and the latest completed
main CI console. It also checked selected PEM/OpenSSH private-key and GitHub-token
patterns. Secret values and raw configuration/console exports were not saved.

- **552 tracked files:** zero known-value or selected-pattern matches.
- **660 reachable Git blobs:** zero known-value or selected-pattern matches.
- **Build #13 console:** zero known-value or selected-pattern matches. This audit
  does not independently verify that build's tests/artifacts.
- Current container mounts, exposed ports, configured users, secret file metadata
  and argv/environment boundaries were inspected without changing containers.
- Host Git/Docker credential-helper configuration was inspected without retrieving
  helper contents. Registry names/accounts/config values were not published.

[Sanitized metadata and limits](../../evidence/task-05/step-03-audit/verification.json)
and [historical audit procedure](../../evidence/task-05/step-03-audit/audit.py.txt).

This is **not proof that all credentials are absent from source/logs**. It excludes
unknown/old/revoked secret values, unreachable Git objects, remote-only refs,
unselected token formats, other Jenkins builds/raw service logs, binary image
contents, Keychain/helper secrets, and cloud-provider state. Existing evidence
retains its own narrower sanitization/verification claims.

## Automated operator check

From the repository root, with the existing local services running:

```sh
uv run --locked python ops/jenkins/verify_secrets.py
```

This is an **operator-only** check, not a Jenkins stage. Do not give the Jenkins
agent Docker access to run it. It uses authenticated GET requests and read-only
Docker inspection/`id`/`stat` commands, never POSTs, builds, restarts or repairs.
Each Docker call has a 15-second timeout and each HTTP call a 5-second timeout,
matching the audit's observation bounds. There are no automatic retries or background
tasks; this is not an overall execution-time guarantee.

The checker requires:

- Existing host credential directory/file: owned by the current host UID, modes
  0700/0600, correct directory/regular-file types, neither final path a symlink.
  Missing credentials are rejected, not created. Host ancestor directories and
  concurrent hostile host-account modifications are outside this trusted-local check.
- Expected running Compose services, live UID 1000, no OOM/privileged mode, host
  network/PID/IPC namespace or device mappings. Only the exact named volumes,
  destinations and read/write modes are accepted; no host bind mounts are allowed.
- Separate controller/agent read-only secret mounts, regular secret files at 0400
  owned by UID/GID 1000; no secret volume on the builder.
- Loopback-only controller port; no agent/builder published ports. Controller/agent
  drop ALL capabilities, add none and retain no-new-privileges. The builder retains
  only the already approved SETUID/SETGID and profile/path exceptions.
- No current admin/agent/Basic-auth literal value in inspected argv/environment.
  The agent secret argument must reference its mounted file.
- Anonymous API access denied and the live application job using the exact public
  repository, trusted main and SCM Jenkinsfile, without a nonempty SCM credential ID.

It does not enumerate all accounts, verify the live authorization strategy, scan
unknown credentials, audit all plugins/jobs/networks or establish token scopes.
The remaining trust limitations above still apply. Builder exceptions are checked
for consistency, not certified safe for hostile workloads.

`reports/secret-boundaries.json` contains only safe status/summary fields. A pass
returns 0. Handled boundary/observation failures return 1 with a generic failure
report; raw external errors are intentionally excluded because they may contain
sensitive configuration or response bodies. An initial `incomplete` report replaces
any stale pass. Unexpected failures also fail execution and must not be treated as
success. Only the one owned report file is replaced; no service configuration is
modified. Inspect the checklist privately on failure; never paste raw credential
files, JNLP responses or Docker inspection output into chat/evidence.

## Local implementation verification

On 28 October 2026:

- **503 tests passed with `-W error`**, including 57 new deterministic cases.
- Ruff lint/format, wheel/source build and source/runtime security gates passed.
- Bandit reported 21 LOW findings, zero MEDIUM/HIGH; the two new LOW findings
  remain visible, not suppressed. All 14 runtime dependencies passed auditing.
- The real operator verifier passed against existing controller/agent/builder
  services, with no secret, permission, authentication or lifecycle changes.
- Test failures cover missing/unsafe host files, namespace/privilege/mount/port
  drift, extra builder permissions, secret-in-environment/argv, changed checkout
  configuration, anonymous access/errors, malformed XML and failed observations.
  Tests also check stale-pass replacement, safe output and HTTP-error cleanup.

The first live check failed closed because Docker inspect normalizes SETUID/SETGID
to CAP-prefixed names and expands `systempaths=unconfined` into empty masked/read-only
path lists. The parser now checks those actual fields, with regression cases; no
runtime settings were weakened to make the check pass. An initial full-suite run
caught unclosed HTTPError resources under warnings-as-errors; both the real handler
and unconsumed synthetic fixture responses now close them. Initial formatting errors
were also corrected before the final passing checks. No warnings were suppressed.

[Local outputs](../../evidence/task-05/step-03-boundaries/local-checks.txt),
[operator result](../../evidence/task-05/step-03-boundaries/secret-boundaries.json),
[source/runtime summary](../../evidence/task-05/step-03-boundaries/security-summary.json),
and [source hashes](../../evidence/task-05/step-03-boundaries/source-sha256.json).
These were pre-merge local results; subsequent SCM verification is linked above.
They are not cloud evidence. Failure paths use
synthetic external boundaries; no live credential exposure or permission weakening
was introduced for a demonstration.

## Rotation and least-privilege planning — approval required

The following is a planning checklist, **not a tested rotation runbook**. Confirm
scope, maintenance window, recovery ownership and exact verification procedure
before changing any live credential. Never paste a secret into chat or a command
argument, and never save credential-bearing terminal output as evidence.

1. **Git/Docker operator tokens:** privately inspect current permissions, expiry and
   authorized destinations in the provider UI. Select the minimum repository/action
   scope supported by the provider. Agree on replacement/revocation order and verify
   the approved operation before revoking the old token. Use the existing credential
   helper; do not write plaintext auth into the repository. A publication-based test
   still needs explicit publication approval.
2. **Jenkins admin password:** plan coordinated replacement of the host source and
   controller-mounted file with JCasC startup reconciliation. Establish an approved
   maintenance/recovery procedure first; verify both new login success and old login
   rejection without deleting controller history. Account API tokens/sessions require
   separate review; do not assume password rotation revokes them. No rotation was run.
3. **Agent secret:** verify supported Jenkins invalidation/re-enrollment behaviour
   for this pinned controller version before specifying commands. Drain owned builds,
   preserve required history, and verify old-secret rejection/new-agent connectivity.
   Do not print the JNLP response, reuse the admin password, or assume restarting an
   agent rotates its secret. No supported rotation procedure has yet been validated.
4. **Future release credentials:** decide trusted release stages, credential-store
   scope, allowed branches and execution isolation before introducing credentials.
   Untrusted builds must not share release-secret access. Add only the exact registry
   and cluster permissions needed, not account-wide administrator privileges.

## Kubernetes Secrets and cloud controls — deferred

Kubernetes Secret `data` is **base64 encoding, not encryption**. A future secret
requirement must specify its owner, consumer, delivery, rotation, recovery and
least-privilege access before manifests or credentials are introduced.

When managed deployment is approved, verify provider encryption at rest/KMS policy,
namespace-scoped RBAC, Secret read/list/watch restrictions, service-account token
behaviour, workload identity options, audit logging and evaluator retention. Do not
claim provider defaults or existing manifest settings establish these controls.
Cloud credentials, kubectl contexts and kubeconfigs must remain outside Git/evidence.
Current public image pulls and the application need no Kubernetes Secret.

## Next review and deferred decisions

The trusted single-operator model and automated read-only checks were approved.
The implementation is merged/published and normal CI tests are verified; review
the evidence follow-up before starting the next step. Live rotation and registry/cloud credentials remain deferred by agreement. Any
permission, authorization, bootstrap or deployment change still needs separate
approval. Rotation checklists remain untested planning, not completion evidence;
provider-specific RBAC/encryption controls remain pending real cloud integration.
