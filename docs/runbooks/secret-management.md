# Secret management — Step 5.3 audit checkpoint

## Status and scope

Branch: `task-05/step-03-secret-management`, from reviewed `main` at `8fd7a36`.
This is a **read-only audit and planning checkpoint**, not completion of Step 5.3.
No credentials were created, rotated, revoked, printed or transferred to a new
service. No permissions, Jenkins authorization, infrastructure or application code
were changed. No cluster was contacted.

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

## Next decisions

1. Confirm keeping the current trusted, single-operator local model for this demo.
2. Approve a bounded local verification/hardening scope, including any automated
   checks, before changing permissions, authorization or bootstrap behaviour.
3. Decide whether to validate Jenkins rotation now or defer live rotation until
   a maintenance/recovery procedure is approved. An untested checklist is not proof.
4. Keep registry/cloud credential work pending until delivery and provider decisions
   are approved. Step 5.3 remains partial until its agreed scope is verified.
