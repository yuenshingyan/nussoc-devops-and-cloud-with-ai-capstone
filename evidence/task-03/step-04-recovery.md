# Step 3.4 — one-pod recovery demonstrated

Status: **actual controlled deletion and recovery verified**; local documentation
checkpoint pending review/publication. The user explicitly approved deleting one
application pod while leaving the other running, with public health observation.

Execution: **3 November 2026 16:01 UTC / 4 November 00:01 Singapore**.
Baseline: reviewed/merged main `7e37eaa56c494a6506bf6ca3cab58604eae16045`.
Automatic #33 passed 781 tests/all gates/33 artifacts at that baseline and verified its
notification revision. It did not test this later evidence/documentation checkpoint.

## Preconditions and the single mutation

The harness required two Ready nodes, exactly two Running/Ready application pods,
two available Deployment replicas, the published image digest and the expected public
Service IP. External health and accepted/rejected/invalid synthetic requests passed
before deletion. The sampler was running and had a healthy observation before mutation.

Exactly **one** Kubernetes DELETE was issued over the authenticated HTTPS DNS endpoint:

- Target: `finsecure-pay-cdb4569cc-4gwtw`.
- Target UID: `d6a455c7-1a55-457c-b34d-edeb4cf3eff9`.
- `DeleteOptions.preconditions.uid` bound the request to that exact object.
- Response: HTTP **200**. No force, grace override, selector/all-pod deletion or retry.
- No Deployment, Service, node, cluster, account or billing modification was requested.
- Separate clients kept Google credentials off the public HTTP health/validation API.

The operator harness had pre-execution import/line-length corrections; it passed Ruff
before running. There was no failed live deletion attempt or selected passing rerun.
The archived harness is the exact executed code, preserved for review, **not permission
to run another disruption**.

## Replacement and unchanged resources

| Item | Observed result |
| --- | --- |
| Replacement | `finsecure-pay-cdb4569cc-775hq` |
| Replacement UID | `c878c97b-552a-4c4c-aa4f-9d0b01a71346` |
| Owner | Same ReplicaSet UID `8d9a82f4-b5b2-4729-b192-86b597c46a94` |
| Original survivor | Its original UID remained present and Ready |
| End state | Old UID absent; two Running/Ready pods and two available replicas |
| Observed recovery bound | **16.1373 seconds** after the deletion timer started |
| Deployment | Spec hash, UID and generation unchanged |
| Service | UID, spec and status unchanged |
| Nodes | Same node UID set, still Ready, compared by the harness |
| Published image | Unchanged 0.3.0 AMD64 digest; replacement restart count zero |

The timing includes polling/command latency and waiting for old-object disappearance;
it is **not** an exact scheduler/controller repair latency. The 12 intermediate Pod
observations and before/after Pod identities are retained. Node UID comparisons were
asserted during execution; only their boolean result, not raw node objects, was retained.
A follow-up read captured 16 relevant retained Kubernetes events, including the
ReplicaSet's `SuccessfulCreate` event naming the actual replacement. Some retained
events describe the earlier initial deployment, not this disruption.

## Public availability observations

- **21** public `/health` samples; all returned 200 with the healthy body.
- **Zero observed failed samples**; the sampler ran across deletion and replacement.
- Sampling was roughly once per second, not continuous. It does not prove that no
  transient failure occurred between samples or establish an availability SLA.
- Before and after: health 200; accepted validation 200/valid; business rejection
  200/`AMOUNT_NOT_POSITIVE`; wrong input type returned the expected safe HTTP 422.
- Only health was sampled during recovery; the transaction cases were before/after,
  not a sustained transaction load test. All input values were synthetic.

The observation deadline was 300 seconds. The sampler was owned by the harness, stopped
in `finally`, and joined successfully with no sampler errors. There were no retained
background probes. The real application remains running at
http://35.198.197.186/health with the same service/image identity.

## Verification and scope limits

All **781 host tests**, Ruff lint/format and packaging passed. The exact archived harness
also passed its own Ruff check/format check. No application behavior or dependencies
changed; no new unit tests or image rebuild were needed for this documentation/demo step.

This demonstrates ReplicaSet recovery from a normal Pod deletion, not liveness failure,
node failure, new-version rolling upgrade, rollback, cloud monitoring/alerts or automatic
SCM-to-cloud delivery. Those remain separate work. No resource teardown was performed.

[Operator/troubleshooting/cleanup runbook](../../docs/runbooks/pod-recovery.md) records
future teardown commands behind separate approval. Availability through 18 November
and teardown review on 19 November remain the plan; there is no automatic deletion job
or spending cap and no paid upgrade is authorized.

Artifacts: [manifest](step-04/SHA256SUMS), [full observations](step-04/verification.json),
[execution summary](step-04/execution.txt), [Kubernetes events](step-04/events.json),
[exact harness](step-04/run.py.txt),
[host checks](step-04/host-checks.txt),
[prior automatic #33 verification](step-04/baseline-scm-verification.json),
[prior automatic #33 completion](step-04/baseline-scm-completion.json).
