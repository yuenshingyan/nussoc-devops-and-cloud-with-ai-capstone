# Actual automated delivery, release blocks and rollback

## Successful normal source-to-deployment run

Normal SCM **finsecure-ci #39** at `b5ee4dece0a76a7621ad4d2222d34874b69c083d`
passed **1,349 tests**, source/dependency gates and the AMD64 image gate. Its native
SUCCESS upstream trigger started **finsecure-release/delivery #3**, which completed
**SUCCESS in 104.780 seconds**. No manual build cause was substituted for this trigger.

The fixed, approved controller definition independently verified the transferred archive,
materialized it without rebuilding, checked the absent SHA tag, published once, verified
registry manifest/config bytes, and performed one conditional image-only Kubernetes PATCH.
It verified rollout, two owned ready runtime-image Pods, public readiness and all four
single-attempt synthetic smoke cases. The live application is **0.4.0**.

- Registry digest: `sha256:a375d013ca16078c862d4184147daabb3808b68e0d2e87832991005676269d3e`.
- Image config: `sha256:047855d87e877634cca917385047a54d56f19939e53b1e519a7bfa1bde4c158c`.
- Export SHA256: `e1fd4fb32362aca46ecc5e5e8af26f68b34a3165a253e672351011f38afac150`.
- Deployment generation: **4**; rollout observation: **46.188 seconds** (not an SLA).

Reports saying `publishing_authorized: false` do not grant authority themselves; the fixed
controller authorizes the actions. That field does not mean the recorded push was skipped.

## Actual release-block demonstrations

Both cases used native Jenkins **Replay of normal build #36**, with one deliberate
workspace fault. They were operator-triggered demonstrations, **not automatic SCM runs**.
Main, the source job definition and the delivery policy were not changed by the faults.

| Case | Observed result | Downstream boundary |
| --- | --- | --- |
| Source #37: injected pytest assertion | 1 failed, 1,348 passed | No package/image artifacts; delivery remained at #2 |
| Source #38: pinned Debian base substituted in the isolated workspace | 38 HIGH, 2 CRITICAL; 40 blocking findings | Image withheld; delivery remained at #2 |

The vulnerable final artifact was never run as an application, published or deployed.
Normal #39 checked out clean main and passed. LOW Bandit findings remain visible; clean
image results mean no known findings in that database snapshot, not vulnerability freedom.

## Controlled rollback and retained failures

- Delivery **#1 failed before credentials**: Jenkins removed empty environment variables.
  The shell now handles their absence; the failure is retained.
- Delivery **#2 published and patched successfully**, then failed a public HTTP smoke request.
  Its result remains FAILURE. Subsequent read-only inspection proved public **0.4.0**, two
  ready runtime-image Pods and four passing smoke cases. The exact HTTP exception cause
  was not retained; no definitive root-cause claim is made.
- An **explicit operator rollback demonstration**, not automatic rollback or command retry,
  restored the independently approved **0.3.0** digest in **33.43 seconds**. Reversing only
  the inspected image field reproduced the previously approved full-spec hash before PATCH.
  Two ready Pods, the restored spec, public version and all smoke cases were verified.
- A fresh source revision then completed #39 → delivery #3. No old tag was repushed and no
  uncertain PATCH was relaunched. Public health observations precede the strict smoke suite.

The job is serialized, resume-disabled and restricted to its dedicated worker; those
settings are verified. Full live cancellation/restart/concurrency fault exercises are not
claimed here. Registry-side atomic tag immutability is not established. No automatic rollback
or spending cap is configured. Evaluator access remains planned through 18 November, with
separate cleanup approval on 19 November.

## Evidence

[Checksummed JSON records](step-03-live-delivery/) contain native causes, gate summaries,
publication/deployment identities, real failing-test counts and rollback observations.
Raw consoles and full scanner reports remain in Jenkins and ignored operator reports.
No credentials or raw private cloud objects are included.
