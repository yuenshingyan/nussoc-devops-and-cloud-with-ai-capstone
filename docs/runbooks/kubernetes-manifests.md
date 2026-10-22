# Kubernetes manifests — Step 3.1

## Scope and readiness

This step defines and locally renders resources; **it does not deploy them**.
The draft Deployment references `yuenshingyan/finsecure-pay:0.2.0`, which is not yet
published by this step. After publication and pull-back verification, replace that
reference with the recorded multi-platform digest. Do not substitute 0.1.0: it does
not consume the new validation settings.

Probes, resource requests/limits, rolling-update policy, and the restricted pod
security context belong to Step 3.2. Provider/region, cluster access, costs, external
exposure, and teardown require approval before Step 3.3. These manifests are not
yet a deployment-ready or production-secured configuration.

## Resource layout

| Input | Purpose |
| --- | --- |
| `deploy/kubernetes/base/deployment.yaml` | Two desired replicas; Linux nodes; named container port `http` at 8000; ConfigMap-backed environment |
| `deploy/kubernetes/base/service.yaml` | ClusterIP Service, port 80 to named target port `http`; selects the application pods |
| `deploy/kubernetes/base/configmap.env` | Non-secret default validation settings |
| `deploy/kubernetes/base/kustomization.yaml` | Shared resources and content-hashed ConfigMap generator |
| `deploy/kubernetes/overlays/demo/namespace.yaml` | Dedicated `finsecure-pay` namespace |
| `deploy/kubernetes/overlays/demo/kustomization.yaml` | Demo namespace applied to the base resources |

The resulting Kubernetes resources are one Namespace, one Deployment, one Service,
and one ConfigMap. A Kustomization file is local build input, not a resource to submit
directly to the API server. The Service is internal-only: no public load balancer,
NodePort, Ingress, cloud account, or credentials are configured here. Two desired
replicas are not evidence that two pods have actually run.

No node CPU architecture is hard-coded yet. The image must support the selected
cluster's architecture; the OS selector restricts scheduling to Linux nodes.

## Render without cluster access

Prerequisite: `kubectl` with built-in Kustomize. Run from the repository root:

```sh
mkdir -p reports
kubectl version --client --output=json
kubectl kustomize deploy/kubernetes/base > reports/kubernetes-base.yaml
kubectl kustomize deploy/kubernetes/overlays/demo > reports/kubernetes-demo.yaml
```

These commands only use local files; they do not contact a cluster. Verify:

- All three namespaced resources target `finsecure-pay` in the demo output.
- Deployment and Service selectors match the pod labels.
- Service port 80 targets `http`, which maps to container port 8000.
- The Deployment requests two replicas and references version 0.2.0, not `latest`.
- The generated ConfigMap name has a content hash and matches `envFrom.configMapRef`.
- The generated data contains string settings matching the
  [application settings contract](application-settings.md).

Kustomize rendering and consistency checks are not Kubernetes API schema/admission
validation. Server-side dry-run remains pending until an approved cluster is
available and the image/runtime prerequisites above are complete. Later, with an
explicitly approved context, validate without persisting resources:

```sh
# Future step only: requires an approved, reachable cluster/context.
kubectl --context "${APPROVED_CONTEXT:?Set an explicitly approved context first}" \
  apply --dry-run=server -k deploy/kubernetes/overlays/demo
```

A server-side dry-run does not persist the Namespace, so namespaced resources may
need the approved namespace to exist first. Namespace creation itself is a separate
approved operation. A successful dry-run still does not pull the image, schedule
pods, or demonstrate runtime behavior.

## Configuration changes

Change only the two documented values in `base/configmap.env`, then rerender and
review the output. Kustomize generates a new ConfigMap name when its data changes
and rewrites the pod template's reference. Applying that reviewed change later
will cause a Deployment rollout; this step verified the reference change locally,
not an actual rollout.

Do not disable the hash or patch the generated ConfigMap in place: process
environment variables are startup snapshots, not live configuration. During a
rolling change, old and new policy versions can coexist. For this demo, wait for a
successful rollout before validating transactions under a changed policy; atomic
policy cutover is not implemented.

Old generated ConfigMaps are not automatically pruned by a normal apply. Retain
those needed by rollback revisions; review cleanup separately rather than deleting
configuration still referenced by old ReplicaSets.

ConfigMaps are not secret storage. Do not put tokens, passwords, private keys,
request bodies, or personal data in these files. The API currently needs no secrets.

See [Step 3.1 evidence](../../evidence/task-03/step-01-manifests.md) for actual checks
and remaining release/deployment prerequisites.
