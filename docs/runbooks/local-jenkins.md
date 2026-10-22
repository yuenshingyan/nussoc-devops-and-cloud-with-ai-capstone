# Local Jenkins — Step 4.1

## Scope and boundaries

This is a **checkout-only setup**, not the finished CI/CD pipeline. It creates a local
Jenkins controller and one Python agent. The job fetches the public repository's
`main`, optionally checks an expected commit, and prints tool versions. It does not
run application tests, scanners, packaging, image publication, or Kubernetes deployment.
A green `finsecure-checkout` result proves only those setup checks.

- Controller: Jenkins **2.580.1 LTS**, Java 21, **zero executors**.
- Agent: one executor labelled `python`, Python **3.14.7**, uv **0.9.21**, Git, Java 21.
- Both run as UID 1000, drop all Linux capabilities, prohibit privilege escalation,
  and are limited to one CPU and 1 GiB memory each. These are local demo limits.
- The only published port is **127.0.0.1:8080**. Agent transport is WebSocket over the
  private Compose network; inbound TCP agent port 50000 is disabled.
- No host directories or Docker socket are mounted into either service. No registry,
  GitHub, or cloud credential is installed in Jenkins. Public Git checkout is anonymous.
- Only trusted `main` is selected; no untrusted PR builds are configured. Later release
  credentials must be scoped to trusted release stages, not shared with arbitrary code.
- This HTTP, single-admin instance is for a trusted local machine, not public hosting.
  The local URL is not an externally accessible submission link.

Images are digest-pinned in `ops/jenkins/*.Dockerfile`. `plugins.txt` pins the complete
63-plugin resolution, including transitive dependencies, using `--latest=false`.
This is not a bit-for-bit rebuild guarantee: Debian package repositories/build metadata
can change. Actual local image IDs and installed plugin versions are recorded as evidence.
No Jenkins image was published to a registry. Only Linux ARM64 execution was verified.

## Start and sign in

Prerequisites: Docker with Compose, Git, uv, and local Python 3.14. Allow roughly 2 GiB
for the service memory limits plus Docker/host overhead; verification used a Docker VM
with approximately 4 GiB. Internet access is needed for initial image/plugin/package
builds and public Git checkout. All commands below run from the repository root.

```sh
docker compose -f ops/jenkins/compose.yaml config --quiet
docker compose --progress plain -f ops/jenkins/compose.yaml build
uv run --locked python ops/jenkins/bootstrap.py
```

The bootstrap creates/reuses `~/.config/finsecure-pay/jenkins/admin-password`, protected
by a private directory and file permissions. It prints only the file **path**.
Open <http://127.0.0.1:8080/> and sign in as `admin`, obtaining the password privately
on your own machine. For example, macOS users may choose to copy it without displaying it:

```sh
pbcopy < ~/.config/finsecure-pay/jenkins/admin-password
```

Do not paste it into chat, screenshots, shell arguments, Git, or evidence. Self-signup
and anonymous API access are disabled. Password-authenticated API POSTs require a CSRF
crumb and matching session cookie; the helper preserves both rather than disabling CSRF.

The bootstrap transfers secrets through stdin to short-lived, network-disabled helpers.
Those helpers run as root with only `CHOWN`, `DAC_OVERRIDE`, and `FOWNER` for secret-volume
ownership/permissions; the controller and agent themselves retain **no capabilities**.
Helpers are removed automatically. Password and agent secret are separate files in
separate purpose-labelled Docker volumes, mounted read-only only where required.
The agent uses `-secret @/run/secrets/agent_secret`; secret values are not command-line
arguments or container environment variables. It cannot read the controller password volume.

These files/volumes are **not an encrypted secret-manager service**. Docker administrators
can read them. Never export Jenkins home or secret volumes as evidence; they contain
sensitive state. Protect any backups outside Git. Bootstrap preserves existing credentials;
if private credential material is missing or inconsistent, recover it deliberately rather
than deleting volumes or creating replacement accounts blindly. JCasC controls this admin
account, so do not treat a UI password change as a durable rotation procedure.

Startup polling allows 180 seconds for the controller and 120 for the agent; individual
HTTP/Docker calls are also bounded. An exited container fails startup promptly. Failure
leaves the owned persistent state available for diagnosis; the bootstrap does not prune,
reset credentials, or silently destroy the controller home.

## Verify checkout

Resolve the currently **published** `main`, not an unmerged local feature-branch commit:

```sh
revision="$(git ls-remote --exit-code \
  https://github.com/yuenshingyan/nussoc-devops-and-cloud-with-ai-capstone.git \
  refs/heads/main | cut -f1)"
uv run --locked python ops/jenkins/verify.py --expected-revision "$revision"
```

The verifier follows the returned queue item to its actual build number, checks success,
revision and tool markers, agent/controller separation, polling configuration, non-root
identity, privilege restrictions, and loopback/no-host-bind boundaries. It saves a sanitized
console log and summary in ignored `reports/`. It does not retry failed builds.

In the UI, open **finsecure-checkout → build number → Console Output**. Expect:

- `Running on finsecure-python`;
- `SOURCE_REVISION=<the published Git commit>`;
- Python 3.14.7 and uv 0.9.21;
- `CHECKOUT_ONLY: ... have NOT run.`;
- `Finished: SUCCESS`.

The sandboxed Pipeline definition is intentionally embedded in the trusted image's
Job DSL for this setup step; a repository Jenkinsfile is added in Step 4.2.
Builds are serialized. The five-minute Pipeline timeout includes agent allocation;
Git clone/fetch has a two-minute timeout and controller SCM checkout retries are zero.
The verifier's queue/build polling allowance is six minutes. A verification-client failure
is not proof of build cancellation: inspect the queue/build and stop an owned setup build
explicitly if necessary.

## Source-change triggering

The first run installs `H/5 * * * *` SCM polling (hashed five-minute schedule). This avoids
opening an Internet-facing webhook/tunnel. Polling only works while Docker, Jenkins, and
the laptop are running. A successful manual checkout and a configured poll schedule are
**not** proof of a source-change-triggered application pipeline; that demonstration is
reserved for Step 4.4. No source-change commit is published just to manufacture evidence here.

## Restart and stop without data loss

```sh
# Re-run startup safely with the existing credentials, job history, and workspace.
uv run --locked python ops/jenkins/bootstrap.py

# Stop this project when not needed; retain containers and all named volumes.
docker compose -f ops/jenkins/compose.yaml stop

# Alternatively remove its containers/network, but retain named volumes.
docker compose -f ops/jenkins/compose.yaml down
```

Do **not** add `--volumes`, run a system/volume prune, or delete the private password file.
Controller home/history and agent workspace use Compose volumes; two external secret
volumes survive normal `down`. There is no automatic restart policy: run bootstrap when
needed. Destructive reset, credential rotation, and final cleanup require deliberate review.

Before restarting or applying changed images, confirm the queue is empty and no builds
are running; maintenance can interrupt work. Bootstrap is not a draining/zero-downtime
upgrade mechanism. To apply changed configuration, build and rerun bootstrap. For plugin upgrades,
review the pinned list and persistent plugin state; do not assume an image rebuild alone
reconciles every manually upgraded plugin in Jenkins home. Avoid UI plugin upgrades in this demo.

## Troubleshooting and recorded corrections

- **Python installation:** uv 0.9.21's managed-download catalogue lacks 3.14.7. The final
  agent derives from the already pinned Python image and copies Java/remoting from the
  official inbound-agent image. It does not downgrade the interpreter or change app dependencies.
- **CSRF schema:** this Jenkins version no longer accepts `excludeClientIPFromCrumb`.
  `standard: {}` retains the supported CSRF issuer; protection was not switched off.
- **Repeated secret setup:** existing files are owned by UID 1000 and read-only. The
  bounded initialization helper needs `FOWNER` to reapply permissions; application services
  do not receive that capability. Repeated startup must preserve the same credentials.
- **Agent offline / disk monitor:** a 128 MiB tmpfs triggered Jenkins's default 1 GiB
  temporary-disk threshold. The final Jenkins services use disk-backed container `/tmp`;
  disk monitors remain enabled. This differs intentionally from the API's bounded tmpfs.
  Reclaim only owned disposable data if real disk space is low; do not disable monitoring.
- **Initial queued build:** build 1 was explicitly aborted before checkout after the
  temporary-disk problem. The corrected configuration then passed real checkout.
- **Failed startup:** inspect only this Compose project's status and logs locally. Raw logs
  may contain sensitive data; sanitize before sharing. The bootstrap deliberately keeps
  raw Docker stderr out of exceptions rather than risking secret disclosure.
- **Restart readiness:** an early restart probe encountered an API/authentication-not-ready
  response. Startup polling now tolerates bounded 401/403/404/500/503 responses while
  Jenkins initializes, but persistent failures still time out. This retries readiness
  observations, not failed builds. Regression tests cover transient initialization,
  credential preservation, ownership guards, and blocked/closed redirects.

## What remains pending

Step 4.2 adds real application tests, reports, packaging, and a Jenkinsfile. Container
build/push requires a separately agreed isolated builder; the current agent has neither
Docker CLI nor daemon access. Do not attach the host Docker socket as a shortcut.
Security gates, real source-change/failure demonstrations, notifications, and all managed
Kubernetes/cloud delivery and observability evidence remain pending under the budget-aware plan.

References: [Jenkins Docker image](https://github.com/jenkinsci/docker),
[inbound agents](https://github.com/jenkinsci/docker-inbound-agent),
[JCasC secret sources](https://github.com/jenkinsci/configuration-as-code-plugin/blob/master/docs/features/secrets.adoc),
[controller isolation](https://www.jenkins.io/doc/book/security/controller-isolation/),
[CSRF protection](https://www.jenkins.io/doc/book/security/csrf-protection/).
