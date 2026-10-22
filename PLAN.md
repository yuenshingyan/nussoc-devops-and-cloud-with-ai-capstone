# FinSecure Pay — Implementation Plan

## Agreed structure

- Complete all seven assignment tasks in order.
- Break each task into small, independently verifiable steps.
- Work on one step at a time, on a dedicated Git branch.
- Explain and verify each step, then pause for review before merging and continuing.
- Do not claim external deployment, notifications, security scans, or recovery succeeded without real execution evidence.

Tasks 1–2 are reviewed, merged into `main`, and published. Step 3.1 adds configurable validation policy and locally verified Kubernetes manifests on `task-03/step-01-manifests`. Approved release 0.2.0 is published and pull-tested for ARM64/AMD64, and the Deployment pins its verified index digest. Step 3.1 awaits final review and merge. No cluster has been contacted; server-side validation awaits approved cluster access. See the [evidence index](evidence/README.md) and [Kubernetes runbook](docs/runbooks/kubernetes-manifests.md).

## Technology choices

| Area | Planned choice | Reason |
| --- | --- | --- |
| Application | Python, FastAPI, Pydantic | Familiar language, typed request validation, automatic API documentation |
| Dependencies/build | `pyproject.toml`, uv and a committed lockfile | Reproducible dependency installation and builds |
| Testing | pytest, HTTPX, coverage | Unit tests, endpoint tests, and coverage reporting |
| Money | Python `Decimal` | Avoid binary floating-point errors; define explicit precision rules |
| Source control | Git, GitHub | Branch-per-step history and evaluator-accessible repository |
| CI/CD | Jenkins, Jenkinsfile | Matches the recommended CI/CD tool |
| Containers | Docker, Docker Hub | Reproducible container packaging and versioned image publishing |
| Orchestration | Kubernetes on EKS, AKS, or GKE | Required managed-cloud deployment; provider to be selected |
| Security/quality | Ruff, Bandit, pip-audit, Trivy | Code checks, Python static security analysis, dependency and image scanning |
| Secrets | Jenkins credentials and Kubernetes Secrets or cloud secrets manager | Keep credentials outside source control; restrict access |
| Monitoring | Prometheus, Grafana, Alertmanager | Application/infrastructure metrics, dashboards, and alerts |
| Logging | Structured application logs plus cloud-native centralized logging | Searchable operational evidence and troubleshooting |
| Notifications | Jenkins Email Extension with SMTP; Alertmanager receiver | Real build and monitoring notifications |
| AI use case | AI-assisted incident triage | Practical operations proposal; no production ML model required |

The assignment allows equivalent application, build, and unit-testing tools with justification. Document why FastAPI, uv, and pytest replace Spring Boot, Maven, and JUnit. Document security-tool alternatives as well. Keep Jenkins; changing CI/CD tools requires facilitator approval.

## Working and evidence rules

1. Bootstrap the Git repository in `capstone/` at Task 1, Step 1. Use a minimal initial `main` commit for the plan and ignore rules, then create the implementation branch.
2. For every later step, start its branch from the latest reviewed and merged `main`.
3. Implement only the active step; do not work on future branches in parallel.
4. Run the step's checks. Record commands, outcomes, limitations, and evidence locations.
5. Commit the step's changes, explain the implementation, and pause for review.
6. Merge after approval. Retain commits and branch names as an auditable history.
7. Keep controlled failing-test and vulnerable-dependency demonstrations isolated. Never deploy intentionally vulnerable artifacts or merge deliberate failures into the working baseline.
8. Store sanitized evidence under `evidence/task-01/` through `evidence/task-07/`. Reference large artifacts with evaluator-accessible links instead of committing them unnecessarily.
9. Keep an evidence index mapping each requirement to its actual run, commit, image version/digest, report, screenshot, or log. Missing evidence stays explicitly marked as pending.
10. Never commit passwords, tokens, kubeconfigs, private keys, raw sensitive logs, or unreviewed exports. The downloaded `instructions.html` contains embedded submission-form data; exclude it from Git and use sanitized requirement notes instead.
11. Obtain confirmation before publishing externally, provisioning billable resources, or running disruptive cloud demonstrations. Never ask for secrets in chat.
12. The user must validate, understand, and explain the implementation for the individual assessment.

## Task 1 — Application Development and Version Control

### Step 1.1 — Initialize and scaffold
- **Branch:** `task-01/step-01-scaffold`
- Initialize Git using the bootstrap procedure above.
- Select a supported Python version and create a FastAPI project with `pyproject.toml`, lockfile, source/test directories, README, and ignore rules.
- Document local setup and the framework/build-tool justification.
- **Verify:** A clean dependency installation succeeds and the application starts locally.

### Step 1.2 — Implement health endpoint
- **Branch:** `task-01/step-02-health`
- Implement `GET /health` with a stable JSON response and HTTP 200 when healthy.
- Add endpoint tests and document request/response examples.
- **Verify:** Both an automated test and a real local HTTP request succeed.

### Step 1.3 — Implement transaction validation
- **Branch:** `task-01/step-03-validation`
- Agree on and document the transaction schema before coding it.
- Define meaningful rules: required identifiers, positive amount, maximum amount, supported currencies, currency precision, and distinct sender/recipient identifiers.
- Use synthetic identifiers, not real payment-card or customer information.
- Implement `POST /validate` with explicit successful, business-rejected, and malformed-request responses.
- Keep validation logic separate from HTTP handling. This service validates transactions; it does not transfer money.
- **Verify:** Demonstrate at least one accepted transaction, one rejected transaction, and malformed input.

### Step 1.4 — Complete tests
- **Branch:** `task-01/step-04-tests`
- Add unit and endpoint tests for each validation rule, boundary values, missing fields, invalid types, and decimal handling.
- Generate coverage and JUnit-compatible test reports for Jenkins.
- **Verify:** The full test suite passes; record actual coverage without inventing a result.

### Step 1.5 — Verify packaging and publish source
- **Branch:** `task-01/step-05-source-publication`
- Verify clean installation, package build, and tests.
- Create or connect an approved GitHub repository, then push the reviewed history.
- Document repository access for the evaluator.
- **Verify:** Repository link works with the intended access permissions; retain build and test evidence.

## Task 2 — Containerisation

### Step 2.1 — Define container
- **Branch:** `task-02/step-01-dockerfile`
- Create a multi-stage Dockerfile and `.dockerignore` using locked dependencies.
- Run as a non-root user and exclude development files and secrets.
- **Verify:** Image builds successfully and the configured runtime user is non-root.

### Step 2.2 — Run and test locally
- **Branch:** `task-02/step-02-container-validation`
- Run the image locally and document port mapping, configuration, and shutdown commands.
- Test `/health` and accepted/rejected `/validate` requests against the container.
- **Verify:** Save actual endpoint responses and container execution evidence.

### Step 2.3 — Version and publish image
- **Branch:** `task-02/step-03-image-publication`
- Confirm registry destination and authenticate using local credential management.
- Publish a meaningful version tag and a commit-derived tag; record the immutable digest.
- Ensure the image architecture matches the eventual Kubernetes nodes.
- **Verify:** Pull and run the published image; retain registry and version evidence.

## Task 3 — Kubernetes and Cloud Deployment

### Step 3.1 — Define Kubernetes resources
- **Branch:** `task-03/step-01-manifests`
- Add a namespace, Deployment with at least two replicas, Service, and ConfigMap.
- Define configurable limits/currencies and document which values must not be secrets.
- The user confirmed configurable business policy: preserve defaults; validate environment overrides at startup; keep services pure. Currency configuration enables/disables the existing SGD/USD/HKD set without changing precision rules.
- Reference a versioned image rather than relying on `latest`. Version 0.1.0 cannot consume the new settings. Approved release 0.2.0 has been published and verified for ARM64/AMD64; the Deployment now pins its multi-platform index digest.
- **Verify:** Validate manifest structure; use server-side dry-run when a cluster is available.

### Step 3.2 — Configure health and runtime safeguards
- **Branch:** `task-03/step-02-runtime-safeguards`
- Configure readiness and liveness probes, startup handling, resource requests/limits, and a restricted security context.
- Define rolling-update behavior and explain probe semantics.
- **Verify:** Validate configuration; verify actual probe behavior after deployment in Step 3.3.

### Step 3.3 — Deploy to managed cloud Kubernetes
- **Branch:** `task-03/step-03-cloud-deployment`
- Confirm provider, region, account, cost budget, exposure controls, and teardown plan before provisioning.
- Provision or connect to EKS, AKS, or GKE using reproducible configuration where feasible.
- Deploy the application and configure external access appropriate for a synthetic-data demo.
- **Verify:** At least two application pods are Running and Ready; rollout and probes succeed.

### Step 3.4 — Demonstrate access and recovery
- **Branch:** `task-03/step-04-recovery-demonstration`
- Verify external health and transaction-validation requests.
- With confirmation, delete one application pod and observe its replacement.
- Document troubleshooting and resource cleanup commands.
- **Verify:** Capture before/after pod identities, replacement readiness, and external responses.

## Task 4 — CI/CD Pipeline Automation

### Step 4.1 — Connect Jenkins and Git
- **Branch:** `task-04/step-01-jenkins-setup`
- Set up Jenkins, required plugins, and an agent with the required build tools.
- Configure repository access, credential references, and webhook or equivalent source-change triggering.
- Limit deployment credentials and trusted release branches.
- **Verify:** Jenkins checks out the expected repository revision without exposing secrets.

### Step 4.2 — Build, test, and package
- **Branch:** `task-04/step-02-build-test-package`
- Add Jenkinsfile stages for checkout, locked dependency installation, code checks, tests, and packaging.
- Publish test/coverage reports and archive relevant artifacts, including on failure.
- **Verify:** A real Jenkins run passes and its reports are accessible.

### Step 4.3 — Automate container delivery
- **Branch:** `task-04/step-03-container-delivery`
- Add container build, versioned push, and Kubernetes deployment stages.
- Deploy the exact built image, wait for rollout completion, and perform a smoke test.
- Serialize deployments to the shared demo environment to prevent overlapping releases.
- This is an intermediate pipeline; Task 5 adds the final security gates before release.
- **Verify:** A real pipeline publishes and deploys the intended version successfully.

### Step 4.4 — Prove triggering and failed-test blocking
- **Branch:** `task-04/step-04-failure-demonstration`
- Make a source change that triggers a pipeline run.
- Introduce a controlled failing test in an isolated demonstration commit, capture the failed run, then revert it.
- Ensure release credentials are not exposed to untrusted branches.
- **Verify:** The failing test stops downstream publishing/deployment; the deployed image remains unchanged.

### Step 4.5 — Demonstrate rollout and rollback
- **Branch:** `task-04/step-05-rollout-rollback`
- Release a distinguishable new application version.
- Record the known-good revision/image and demonstrate rollback to it.
- Document manual recovery and the limits of any automated rollback behavior.
- **Verify:** Capture successful rollout, restored image/version, Ready pods, and healthy endpoint responses after rollback.

## Task 5 — DevSecOps and Security Integration

### Step 5.1 — Add code and dependency scans
- **Branch:** `task-05/step-01-source-dependency-scans`
- Integrate Ruff/Bandit and pip-audit into Jenkins using the locked runtime dependencies.
- Archive scan reports and document tool choices, severity interpretation, and remediation workflow.
- **Verify:** Real scans run and report actual findings; scanner failures are not silently treated as passes.

### Step 5.2 — Scan images and enforce gates
- **Branch:** `task-05/step-02-image-security-gates`
- Scan the built image with Trivy before publishing/deployment.
- Block at least HIGH and CRITICAL image vulnerabilities; define the dependency/static-analysis failure policies explicitly.
- Document how exceptions, if any, require justification and review.
- **Verify:** Jenkins enforces scan exit codes, archives reports on failure, and only releases images that satisfy the gates.

### Step 5.3 — Harden secret handling
- **Branch:** `task-05/step-03-secret-management`
- Audit the credential handling already used for Git, registry, Jenkins, and Kubernetes.
- Configure least-privilege credential access and Kubernetes Secrets or a cloud-native manager where needed.
- Explain that Kubernetes Secret base64 encoding is not encryption; document RBAC and provider encryption controls.
- Add secret-safe examples and rotation instructions without introducing unnecessary application secrets.
- **Verify:** Source and logs do not expose credentials; capture redacted configuration evidence.

### Step 5.4 — Demonstrate blocking and remediation
- **Branch:** `task-05/step-04-security-demonstration`
- Select a controlled, scanner-detectable HIGH/CRITICAL vulnerability in an isolated demonstration artifact/commit.
- Run the actual gate and capture the blocked release. Do not deploy the vulnerable artifact.
- Remove or upgrade the affected component and rerun the pipeline.
- **Verify:** Retain finding identifier, severity, blocked stages, remediation diff, and subsequent successful scan/build evidence.

## Task 6 — Monitoring, Alerting and Logging

### Step 6.1 — Instrument and collect metrics
- **Branch:** `task-06/step-01-metrics`
- Expose Prometheus request counts, latency, errors, and validation outcomes with bounded labels.
- Collect pod/node health and resource metrics using the monitoring stack.
- Avoid transaction identifiers, personal data, and secrets in metric labels.
- **Verify:** Prometheus scrapes real application and infrastructure time series.

### Step 6.2 — Build dashboard
- **Branch:** `task-06/step-02-dashboard`
- Provision a Grafana dashboard with request rate and latency plus error rate or pod readiness/resource usage.
- Generate bounded synthetic traffic so panels display live data.
- **Verify:** At least two meaningful live metrics are visible; save dashboard configuration and screenshots.

### Step 6.3 — Configure alerts and delivery
- **Branch:** `task-06/step-03-alert-configuration`
- Define a useful threshold, evaluation window, and recovery behavior.
- Configure Alertmanager routing and a real notification receiver with secrets stored securely.
- **Verify:** Rules validate, monitoring loads them, and receiver configuration is accepted.

### Step 6.4 — Trigger and receive an alert
- **Branch:** `task-06/step-04-alert-demonstration`
- Agree on a safe, bounded trigger in the demo environment; avoid uncontrolled load.
- Trigger the condition, capture the firing alert and received notification, then restore normal operation.
- **Verify:** Preserve timestamps linking the measured condition, firing alert, notification receipt, and recovery.

### Step 6.5 — Add build notifications and centralized logs
- **Branch:** `task-06/step-05-notifications-logging`
- Configure Jenkins Email Extension and SMTP, or an approved notification equivalent.
- Demonstrate at least one real received Jenkins notification.
- Emit structured, sanitized application logs and collect them in cloud-native centralized logging.
- Document both centralized queries and `kubectl logs` troubleshooting commands.
- **Verify:** Trace a synthetic request or error through real logs and capture redacted notification/log evidence.

## Task 7 — Documentation, AI Application and Final Demonstration

### Step 7.1 — Write design document and architecture
- **Branch:** `task-07/step-01-design-document`
- Produce a 3–5-page design document and end-to-end architecture diagram.
- Explain source-to-deployment flow, tool alternatives, validation behavior, security boundaries, observability, recovery, and rollback.
- Clearly distinguish implemented features from proposals and limitations.
- **Verify:** Check rendered page count and trace architecture components to actual implementation.

### Step 7.2 — Document AI-assisted incident triage
- **Branch:** `task-07/step-02-ai-use-case`
- Explain the operational problem and why AI-assisted summarization/correlation is appropriate.
- Define inputs: sanitized alerts, logs, metrics, deployment history, and approved runbooks.
- Describe proposed integration from Alertmanager to an advisory triage service and human-reviewed incident summary.
- Cover expected benefits, hallucinations, sensitive-data exposure, prompt injection in logs, access controls, retention, cost, and evaluation.
- Require human approval for operational changes; no autonomous production remediation.
- **Verify:** Include a clearly labeled illustrative input/output example and success criteria. A production ML model is not required.

### Step 7.3 — Assemble evidence and presentation
- **Branch:** `task-07/step-03-presentation`
- Audit the evidence index against all seven tasks and the assignment's core test cases.
- Create an 8–10-slide PowerPoint or PDF with repository/project links, architecture, real results, security reports, recovery, monitoring, and AI discussion.
- Suggested slides: overview; application/Git; containers/cloud; CI/CD; security; observability; architecture/AI; tests/recovery; lessons; optional additional evidence.
- **Verify:** Check slide count, link accessibility, readability, and absence of secrets. Mark any remaining gaps rather than fabricating evidence.

### Step 7.4 — Prepare and rehearse demonstration
- **Branch:** `task-07/step-04-demo-lessons`
- Create and rehearse a 10–15-minute end-to-end demonstration script.
- Include successful validation, tests, container/cloud access, pipeline gating, rollout/rollback, recovery, monitoring, notifications, and AI explanation.
- Use clearly identified recorded evidence for long-running operations where appropriate.
- Record actual lessons learned, limitations, future improvements, and a post-assessment cloud teardown checklist.
- **Verify:** Time the rehearsal and confirm the user can explain the major code and architecture decisions.

## Decisions needed when their steps are reached

- **Task 1:** Complete; Python 3.14 and transaction contract confirmed. Public source access verified, and GitHub defaults to `main` following approval.
- **Task 2:** Public Docker Hub repository `yuenshingyan/finsecure-pay` confirmed. Version 0.1.0 published for ARM64/AMD64 and verified after registry pulls; AMD64 was tested under emulation. Cluster node architecture remains a cloud-deployment decision.
- **Task 3:** Configurable policy and 0.2.0 publication approved and verified; final Step 3.1 review pending. Cloud provider, region, credentials configured locally, budget, exposure policy, and teardown timing remain undecided.
- **Task 4:** Jenkins hosting and agent setup; webhook reachability.
- **Task 6:** SMTP/notification receiver and cloud logging configuration.
- **Task 7:** PowerPoint or PDF preference and evaluator access arrangements.

## Immediate next action

Review completed **Task 3, Step 1** on `task-03/step-01-manifests`, including the 0.2.0 publication evidence and digest-pinned Deployment. After approval, merge and start `task-03/step-02-runtime-safeguards`. Do not apply manifests or provision cloud resources before the remaining runtime safeguards and provider/access/budget approvals.
