# Evidence index

Store only reviewed, sanitized evidence from actual execution here. Task 1 has
application, test, package-installation, and public source-access evidence.
Task 2 has image-build, execution, versioned registry publication, and anonymous
pull/access evidence for ARM64 and AMD64. Task 3 has locally verified configuration,
0.2.0 registry publication, digest-pinned manifests, and constrained-container runtime
checks, not cloud-deployment or kubelet-probe evidence. Task 4 includes local Jenkins
checkout, candidate and normal SCM-loaded application CI, published reports, package downloads,
and report retention on an isolated failure. Cloud delivery remains unverified.

| Task | Directory | Status |
| --- | --- | --- |
| 1 — Application and Git | [task-01](task-01/) | Complete and merged |
| 2 — Containerisation | [task-02](task-02/) | Complete, reviewed, merged, and published |
| 3 — Kubernetes and cloud | [task-03](task-03/) | Steps 3.1–3.2 merged; cloud execution deferred |
| 4 — CI/CD | [task-04](task-04/) | Steps 4.1–4.2 merged; Step 4.3 local build/export merged and SCM-verified (245 tests/image smoke); Step 4.4 local SCM/test-gate merged and SCM-verified (260 tests); publishing/deployment pending |
| 5 — DevSecOps | [task-05](task-05/) | Step 5.1 source/runtime scan gate merged and SCM-verified (316 tests, 25 artifacts); remaining steps pending |
| 6 — Observability | [task-06](task-06/) | Pending |
| 7 — Documentation and demonstration | [task-07](task-07/) | Pending |

## Recorded evidence

- [Step 1.1 — Scaffold verification](task-01/step-01-scaffold.md): clean install,
  lint/format checks, scaffold tests, packaging, and real local HTTP requests.
- [Step 1.2 — Health endpoint verification](task-01/step-02-health.md): API contract
  tests, lint/format checks, packaging, and live GET/POST requests.
- [Step 1.3 — Transaction validation verification](task-01/step-03-validation.md):
  54 unit/API cases, build checks, and live accepted/rejected/malformed requests.
- [Step 1.4 — Expanded tests and reports](task-01/step-04-tests.md): 167 passing cases,
  100% measured line/branch coverage, parsed XML reports, and sanitized run artifacts.
- [Step 1.5 — Packaging and publication](task-01/step-05-source-publication.md):
  clean wheel/source-distribution installs, live HTTP checks, actual branch pushes,
  and anonymous GitHub access.
- [Step 2.1 — Container definition and build](task-02/step-01-dockerfile.md): pinned
  multi-stage build, non-root configuration, final filesystem inspection, and the
  documented Docker Desktop metadata-timeout workaround.
- [Step 2.2 — Container execution](task-02/step-02-container-validation.md): actual
  non-root PID 1, loopback HTTP checks, clean shutdown/removal, and a missing-image
  failure check.
- [Step 2.3 — Image publication](task-02/step-03-image-publication.md): public Docker Hub
  version/commit tags, ARM64/AMD64 manifests, smoke tests before and after registry
  pulls, and anonymous digest/provenance verification.
- [Step 3.1 — Configurable policy and Kubernetes manifests](task-03/step-01-manifests.md):
  210 passing tests, local Kustomize checks, and ARM64 0.2.0 container checks with
  default/custom/invalid settings in the initial candidate; no cluster execution.
- [Step 3.1 — Approved 0.2.0 publication follow-up](task-03/step-01-image-publication.md):
  both platforms tested before/after registry pulls, public provenance, unchanged
  0.1.0 release, local index-cache recovery, and Deployment digest verification.
- [Step 3.2 — Runtime safeguards](task-03/step-02-runtime-safeguards.md): rendered
  probe/resource/security/rollout checks; ARM64 and emulated AMD64 execution with
  CPU/memory caps, verified process restrictions, writable bounded temporary storage,
  and clean shutdown/removal. Kubernetes execution remains unverified.

- [Step 4.1 — Local Jenkins and checkout](task-04/step-01-jenkins-setup.md): authenticated
  loopback-only controller, separate non-root Python agent, real public `main` checkout,
  runtime/plugin checks, and preserved restart state. No application tests ran in Jenkins;
  SCM polling configuration is not yet a source-change-trigger demonstration.

- [Step 4.2 — Application CI and reports](task-04/step-02-build-test-package.md): the
  candidate Jenkinsfile ran on the real agent against reviewed source; 221 tests passed,
  JUnit/coverage results were published, and package downloads matched their checksums.
  An isolated post-test shell failure retained reports and skipped packaging.
- [Step 4.2 — Post-merge SCM verification](task-04/step-02-scm-verification.md): normal
  `finsecure-ci` build #1 loaded the Jenkinsfile from Git at `8deecec`, passed 230 tests,
  published accessible reports, and provided packages with verified download hashes.
  The build was manually triggered; no source-trigger, release, or deployment gate is claimed.

- [Step 4.3 — Local rootless image building (partial)](task-04/step-03-local-image-builder.md):
  candidate Jenkins build exported an ARM64 image, downloaded checksum/configuration
  matched, and the loaded image passed local non-root/HTTP/shutdown checks. Failure
  blocking and worker cancellation/restart were verified. 245 host tests passed versus
  230 from published source in Jenkins. No image publication, scan gate, or cloud deployment.

- [Step 4.3 — Post-merge SCM/image verification](task-04/step-03-scm-verification.md):
  normal build #2 loaded the Jenkinsfile from Git at `ab538a2`, passed 245 tests, and
  exported an image whose downloaded checksum/configuration and real local runtime
  checks passed. This was a manual trigger and operator-side smoke test, not deployment.

- [Step 4.4 — SCM-triggered real test gate (local subset)](task-04/step-04-trigger-gate.md):
  isolated demo builds 2–4 automatically passed, failed one real pytest case (skipping
  package/image export), and recovered after revert. Demo job disabled, branch restored,
  prior artifact unchanged, polling persisted after restart. 260 host tests passed;
  no deployed-service or credential-isolation gate is claimed.

- [Step 4.4 — post-merge automatic main verification](task-04/step-04-scm-verification.md):
  normal build #4 automatically detected published `2f30e7e`, passed 260 tests, and
  exported 17 verified artifacts. Demo remains disabled. No new image load/smoke or
  registry/cloud delivery is claimed for this follow-up.

- [Step 5.1 — source/runtime dependency scans](task-05/step-01-source-scans.md):
  12 MEDIUM parser findings remediated without suppression; 17 LOW findings retained,
  14 runtime dependencies audited with no known advisories. 316 host/candidate tests passed;
  restoring the original parsers before scanning blocked packaging/image export and retained
  reports. Candidate source used a local Git bundle, not publication or SCM Jenkinsfile loading.
  Historical pre-merge record; approval and normal verification are recorded below.

- [Step 5.1 — post-merge SCM verification](task-05/step-01-scm-verification.md): normal
  build #6 automatically detected `76b0f7d`, passed 316 tests and real security scans,
  and exported 25 verified artifacts. 17 LOW findings remain visible; 14 dependencies
  had no known advisories. Image scanning and delivery remain pending.

For each artifact, record the requirement demonstrated, timestamp, command or
procedure, actual result, commit, applicable image digest, and artifact path or
accessible external link. Redact secrets and personal information before adding
files. Keep large generated reports in CI artifact storage where practical.
