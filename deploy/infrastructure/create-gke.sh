#!/usr/bin/env bash
# One-time approved creation. On any partial failure, inspect; do not rerun blindly.
set -euo pipefail

: "${PROJECT_ID:?Supply the dedicated project ID locally; never commit it}"
: "${APPROVE_GKE_CREATION:?Set to trial-only after reviewing the resource proposal}"
# Bash 3.2 does not apply errexit to every compound conditional; exit explicitly.
if [[ ! "$PROJECT_ID" =~ ^finsecure-pay-capstone-[a-f0-9]{6}$ ]] ||
   [[ "$APPROVE_GKE_CREATION" != "trial-only" ]]; then
  printf '%s\n' 'Refusing unapproved creation or an unexpected project target.' >&2
  exit 2
fi

# No billing-account creation/upgrade, key export, retries or cleanup are performed here.
gcloud compute networks create finsecure-pay-demo \
  --project="$PROJECT_ID" --subnet-mode=custom --bgp-routing-mode=regional --quiet

gcloud compute networks subnets create finsecure-pay-singapore \
  --project="$PROJECT_ID" --network=finsecure-pay-demo --region=asia-southeast1 \
  --range=10.40.0.0/24 \
  --secondary-range=finsecure-pods=10.44.0.0/20,finsecure-services=10.48.0.0/24 \
  --enable-private-ip-google-access --no-enable-flow-logs --quiet

gcloud iam service-accounts create finsecure-gke-node \
  --project="$PROJECT_ID" --display-name="FinSecure GKE node" --quiet

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:finsecure-gke-node@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role=roles/container.defaultNodeServiceAccount --condition=None --quiet

# Exactly one node location: num-nodes is per zone, not an aggregate regional limit.
gcloud container clusters create finsecure-pay-demo \
  --project="$PROJECT_ID" --zone=asia-southeast1-a --node-locations=asia-southeast1-a \
  --cluster-version=1.36.4-gke.2046003 --release-channel=regular \
  --machine-type=e2-standard-2 --num-nodes=2 --image-type=COS_CONTAINERD \
  --disk-type=pd-standard --disk-size=30 \
  --no-enable-autoscaling --no-enable-autoprovisioning \
  --enable-autorepair --enable-autoupgrade \
  --max-surge-upgrade=1 --max-unavailable-upgrade=0 \
  --network=finsecure-pay-demo --subnetwork=finsecure-pay-singapore \
  --enable-ip-alias --cluster-secondary-range-name=finsecure-pods \
  --services-secondary-range-name=finsecure-services --no-enable-private-nodes \
  --enable-dns-access --no-enable-ip-access \
  --no-enable-k8s-certs-via-dns --no-enable-k8s-tokens-via-dns \
  --service-account="finsecure-gke-node@${PROJECT_ID}.iam.gserviceaccount.com" \
  --scopes=cloud-platform --workload-pool="${PROJECT_ID}.svc.id.goog" \
  --workload-metadata=GKE_METADATA \
  --logging=SYSTEM,WORKLOAD --monitoring=SYSTEM \
  --no-enable-managed-prometheus --auto-monitoring-scope=NONE \
  --labels=application=finsecure-pay,environment=demo \
  --async --format=json --quiet
