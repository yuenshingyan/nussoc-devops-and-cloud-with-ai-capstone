# Step 3.1 — Configurable policy and Kubernetes resource candidate

- **Date:** 2026-10-22 UTC; manifest checks at 02:03:46, configured-container checks at 02:06:03.
- **Branch:** `task-03/step-01-manifests`.
- **Revision:** The commit introducing this evidence contains the verified source
  and manifests. Retrieve it with
  `git log -1 --diff-filter=A --format=%H -- evidence/task-03/step-01-manifests.md`.
- **Status:** Local implementation and verification complete; 0.2.0 publication,
  digest pinning, server-side validation, and step review remain pending.

## Scope and configuration decision

Step 2.3 was approved and fast-forward merged into local `main` before this branch
was created. Published 0.1.0 images remain unchanged. The user explicitly selected
configurable transaction policy rather than a logging-only ConfigMap.

Version 0.2.0 therefore adds validated environment settings, without new dependencies:

- `FINSECURE_MAX_TRANSACTION_AMOUNT`: default `10000`; positive plain decimal,
  at most 32 characters and two fractional digits, parsed exactly with `Decimal`.
- `FINSECURE_SUPPORTED_CURRENCIES`: default `SGD,USD,HKD`; nonempty, duplicate-free,
  exact uppercase comma-separated subset of the existing three supported currencies.

Defaults preserve the existing transaction behavior. Amount limits can be raised
or lowered; currency configuration enables/disables the existing currencies, not
arbitrary new ones. Precision, HTTP statuses, error ordering, and request/response
schemas are unchanged. Empty or invalid settings fail startup without echoing the
bad value. Unrelated environment variables are ignored.

Each application holds a frozen startup snapshot. The HTTP dependency passes that
snapshot to the validation service; the service remains independent of FastAPI and
does not read environment variables or perform I/O. Settings are not live-reloaded.

Package, OpenAPI, and Docker version metadata are 0.2.0. The lockfile change only
updates the local application's version; dependency resolutions remain unchanged.

## Local Kubernetes verification

Using kubectl 1.36.1 with built-in Kustomize 5.8.1:

```sh
kubectl version --client --output=json
kubectl kustomize deploy/kubernetes/base > reports/kubernetes-base.yaml
kubectl kustomize deploy/kubernetes/overlays/demo > reports/kubernetes-demo.yaml
```

The demo overlay rendered exactly:

1. Namespace `finsecure-pay`.
2. Deployment `finsecure-pay`, requesting two replicas on Linux nodes.
3. Internal ClusterIP Service `finsecure-pay`, port 80 to container port 8000
   through the named `http` port.
4. ConfigMap `finsecure-pay-config-fg4th549cg`, containing only the two default settings.

Parsed-output consistency checks verified matching namespaces, selectors/pod labels,
ports, image version, string configuration values, and the generated ConfigMap
reference in `envFrom`. In a temporary copy, changing the limit to `100` changed both
the ConfigMap name and the Deployment pod-template reference; repository inputs were
not modified by this experiment.

Parsing used the host's existing Ruby standard-library safe YAML loader and Python
standard-library JSON/assertions; no project dependency was installed. An initial
Ruby conversion failed when serializing a document node without a stream wrapper;
wrapping it in a stream fixed the checker, and the checks above passed afterward.

**No cluster was contacted and no resources were applied.** These are local rendering
and consistency checks, not Kubernetes API schema/admission validation or evidence
of Running/Ready pods. A server-side dry-run remains pending an approved cluster.

## Application tests and packaging

Commands and complete sanitized results are in
[verification output](step-01/task-03-verification.txt):

- Ruff lint and format checks passed.
- **210 tests passed** in 0.53 seconds: the original 167 plus 43 configuration cases.
- Coverage: **125/125 executable lines and 28/28 branch outcomes**. This is measured
  application coverage, not an exhaustive correctness or Kubernetes coverage claim.
- Wheel and source archive for 0.2.0 built successfully.
- The existing Starlette/HTTPX deprecation warning remained visible; it was not suppressed.

New tests exercise defaults, exact parsing, invalid/empty values, duplicate/unknown
currencies, immutable settings, sanitized startup tracebacks, pure service behavior,
HTTP limit boundaries, currency subsets, and independent per-application snapshots.

## Local container verification

Built from the candidate working tree, without publishing:

```sh
docker build --platform linux/arm64 --progress=plain --tag finsecure-pay:0.2.0-local .
uv run --locked python scripts/smoke_test.py --image finsecure-pay:0.2.0-local
```

- Platform: `linux/arm64`, native Docker Desktop Linux VM on the ARM64 host.
- Local image ID: `sha256:dc52147d5bce56c036086b69a1da155cfcefe1340a251bc39fb82f5a6fe7a912`.
- This is **not** a registry manifest digest or a published release.
- [Build-input SHA256 hashes](step-01/task-03-build-inputs.json) identify the exact
  Dockerfile/context inputs; post-build checks confirmed they remained unchanged.

The default-policy smoke test passed health, accepted/rejected/malformed transaction
checks, actual UID/GID 10001, read-only root filesystem, dropped capabilities,
clean exit 0, and container removal.

A separate loopback-only container used the ConfigMap input as a Docker env-file,
with explicit overrides `FINSECURE_MAX_TRANSACTION_AMOUNT=100` and
`FINSECURE_SUPPORTED_CURRENCIES=USD`. Real HTTP requests verified:

| Synthetic request | Actual result |
| --- | --- |
| USD `100.00` | HTTP 200, accepted at the inclusive limit |
| USD `100.01` | HTTP 200, `AMOUNT_LIMIT_EXCEEDED` |
| SGD `50` | HTTP 200, `UNSUPPORTED_CURRENCY` |
| SGD `125.50` | HTTP 200, both rejection codes in documented order |

OpenAPI reported 0.2.0, health remained healthy, and the container stopped with exit 0.
A third container with a synthetic invalid amount setting exited with code 1 before
successful application startup. Its captured logs contained the fixed configuration
error, not the invalid value. All owned containers were removed. These checks prove
Docker environment injection, **not Kubernetes ConfigMap execution**.

## Preserved artifacts and next approval

- [Rendered demo resources](step-01/kubernetes-demo.yaml)
- [Manifest consistency summary](step-01/kubernetes-checks.json)
- [ARM64 build output](step-01/task-03-build-arm64.txt)
- [Default-policy smoke test](step-01/task-03-default-smoke.json)
- [Configured-policy and invalid-startup checks](step-01/task-03-configured-smoke.json)

Logs have repository-home paths replaced with `<repository>`, Docker Desktop links
removed, and trailing whitespace trimmed. Results were not fabricated or relabeled
as cloud execution. Large generated JUnit/coverage reports remain ignored locally.

The draft Deployment references 0.2.0 because 0.1.0 does not consume these settings.
Before deployment: approve publication, build from reviewed committed source, test
ARM64 and AMD64, publish unused release/commit tags, verify registry pulls, and pin
the resulting multi-platform digest. No AMD64 0.2.0 test or registry push is claimed.
Step 3.2 still needs probes/resources/pod security; provider, budget, cloud access,
and external exposure remain undecided.

See the [settings runbook](../../docs/runbooks/application-settings.md) and
[Kubernetes runbook](../../docs/runbooks/kubernetes-manifests.md).
