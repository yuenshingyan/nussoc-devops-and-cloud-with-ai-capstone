# One-pod recovery demonstration and troubleshooting

Scope: Step 3.4, explicitly approved for **one normal application Pod deletion**.
No node/cluster deletion, forced termination, Deployment change, rollout to a different
version, billing change or monitoring installation is included.

## Actual result

Executed **2026-11-03 16:01 UTC / 4 November 00:01 Singapore**.

- Deleted `finsecure-pay-cdb4569cc-4gwtw` with a UID precondition and normal grace.
- The ReplicaSet created `finsecure-pay-cdb4569cc-775hq`, with a different UID and
  the same owner/image. The other original pod remained present and Ready.
- Observed old UID absent and two available replicas again after **16.14 seconds**.
  This includes observation/polling delay; it is not an exact controller-repair latency.
- All **21 sampled public health requests** succeeded. Sampling does not prove zero
  transient interruption or an availability SLA.
- Health and accepted/rejected/invalid synthetic requests passed before and after.
- Deployment spec/generation, Service and node identities remained unchanged.

See [before/after identities and observations](../../evidence/task-03/step-04-recovery.md).
The archived harness is execution evidence, **not an approved repeatable deletion job**.
Do not rerun it without fresh permission; it would select another currently healthy pod.

## Preconditions for a separately approved repeat

1. Use the isolated kubeconfig/plugin environment from [GKE creation](gke-creation.md).
   Confirm the current context and public Service IP match the intended cluster.
2. Require exactly two Ready nodes and two Running/Ready application pods, with the
   approved image digest and two available Deployment replicas. Stop if already degraded.
3. Capture Pod names/UIDs/owner UIDs, Deployment spec/generation and Service identity.
4. Validate public health and synthetic transaction cases before disruption.
5. Start an owned public health sampler: roughly one-second cadence, three-second HTTP
   phase timeouts, recording failures as well as successes. Credentials must never be
   sent to the public HTTP application.
6. Issue exactly one authenticated Kubernetes DELETE for the chosen Pod with
   `DeleteOptions.preconditions.uid` set to its captured UID. Do not override grace,
   force delete, target a selector/all pods, or repeat an ambiguous/timed-out DELETE.
7. Observe replacement for at most 300 seconds. Require a new UID, same ReplicaSet owner
   and image, surviving original UID, old UID absent, two Ready pods and two available
   replicas. Verify unchanged Deployment spec/generation, Service and node identities.
8. Repeat public synthetic cases once, retain every observation, stop/join the sampler
   in `finally`, and report any errors. Stop/join budget is ten seconds; Kubernetes
   reads have a 20-second request timeout and 30-second subprocess limit. The DELETE
   has 20-second HTTP phase timeouts and transport retries disabled. These HTTP phase
   timeouts are not a strict total response wall-clock bound.

A successful deletion/replacement demonstrates ReplicaSet reconciliation. It does not
prove liveness-triggered recovery, node-failure tolerance, rolling upgrades, rollback,
cloud alerts, or CI deployment gates.

## Read-only troubleshooting

Run with the isolated kubeconfig and SDK plugin PATH. Keep raw output private until
reviewed: describe/events may include infrastructure identifiers and configuration.

```sh
kubectl -n finsecure-pay get deployment,replicasets,pods,service -o wide
kubectl -n finsecure-pay get events --sort-by=.metadata.creationTimestamp
kubectl -n finsecure-pay describe pod "$POD_NAME"
kubectl -n finsecure-pay logs "$POD_NAME" --tail=100
kubectl -n finsecure-pay logs "$POD_NAME" --previous --tail=100
kubectl get nodes
```

`--previous` is only useful when that container restarted; absence of previous logs
is not proof of a new failure. Inspect scheduling/capacity, image pulls and readiness
before deciding remediation. Do not repeatedly delete pods, widen firewall rules,
increase node counts or upgrade billing as an automatic fix.

## Cleanup — separate approval, not performed in this demonstration

Target review date: **19 November**, after grading/evidence checks. Maintain the planned
availability through 18 November. There is no scheduled teardown automation.

After explicit teardown authorization and evidence export:

1. Stop any later-added delivery automation from recreating workloads. Review any
   monitoring PVC retention/reclaim policy before deleting its namespace/resources.
2. Remove the application Service while the cluster controller is still running so it
   can remove its load-balancer resources. Check the associated forwarding rule,
   backend/health-check/firewall/address cleanup before deleting the cluster.
3. Delete only the approved cluster, then verify its VM instances and boot disks are
   gone. Inspect retained PVC disks/addresses separately; do not assume cluster deletion
   removes every billable resource.
4. Remove the dedicated subnet/network and the dedicated node-account binding/account
   only after dependencies are gone. Do not delete the default VPC, unrelated projects,
   billing account or shared resources. Do not use wildcard cleanup commands.

Explicit resource commands for that **future authorized teardown**, not for use now:

```sh
kubectl -n finsecure-pay delete service finsecure-pay
# Verify load-balancer cleanup before the next command.
gcloud container clusters delete finsecure-pay-demo \
  --project="$PROJECT_ID" --zone=asia-southeast1-a
# Verify node/disk cleanup before removing dedicated networking/identity.
gcloud compute networks subnets delete finsecure-pay-singapore \
  --project="$PROJECT_ID" --region=asia-southeast1
gcloud compute networks delete finsecure-pay-demo --project="$PROJECT_ID"
gcloud projects remove-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:finsecure-gke-node@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role=roles/container.defaultNodeServiceAccount --condition=None
gcloud iam service-accounts delete \
  "finsecure-gke-node@${PROJECT_ID}.iam.gserviceaccount.com" --project="$PROJECT_ID"
```

A failed delete can leave partial resources. Inspect and record actual state; do not
retry blindly or claim teardown/cost cessation from a single successful CLI exit.
