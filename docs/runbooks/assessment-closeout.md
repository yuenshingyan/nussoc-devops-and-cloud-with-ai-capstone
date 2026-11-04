# Lessons, remaining decisions and post-assessment closeout

## Actual lessons

- A large helper-test suite and CPS compilation did not prove end-to-end delivery.
  Native Jenkins execution exposed empty-variable and public-smoke assumptions.
  Prioritize a guarded end-to-end path earlier; retain component tests as supporting evidence.
- Preserve failed runs. Delivery #2 changed runtime state before failing smoke; inspect
  that state before deciding what to do. Do not automatically retry an uncertain write.
- Ready Pods do not establish public routing readiness. Bounded observations now precede
  strict smoke checks; the precise earlier HTTP exception cause remains unproven.
- Archive, config and registry-manifest hashes identify different representations. Verify
  each boundary rather than treating every digest as interchangeable.
- Check host storage and Docker-backed storage separately. Preserve scanner diagnostics;
  an earlier scanner/storage failure is not proof of its final root cause.
- Verify notification bind sources after controller or worktree changes. Scope alert rules
  to the actual target; a local-target rule was not valid evidence of a cloud alert.
- A load-balancer scrape is not complete per-Pod monitoring, and Mailpit is not external SMTP.
  Label observations accurately rather than claiming an aggregate SLO or internet delivery.

## Future improvements — not implemented or newly authorized

Decide TLS/authentication, per-Pod monitoring discovery and resource costs, external SMTP,
server-enforced image-update policy, short-lived release identity, and controlled live
cancellation/restart/concurrency exercises before implementing them. Define budget alerts
separately from any hard-stop mechanism: a billing alert is not a spending cap. The proposed
AI provider, budget, retention and access policy still require decisions.

## Post-assessment checklist — execute only after separate approval

Planned evaluator access continues through **18 November**. Review teardown on **19 November**;
this is a checklist, not an executed or automatic cleanup.

1. Confirm assessment access has ended and obtain approval for the exact resource list.
2. Preserve reviewed PDFs, video, checksums, native reports and notification evidence.
   Keep raw private exports and credentials out of the public evidence archive.
3. Inventory only this project's cluster/nodes, services/load balancer, addresses,
   forwarding/firewall resources and disks. Inspect actual ownership and persistence;
   do not infer that deleting a cluster removes every related resource.
4. After approval, stop the project's automatic release/SCM triggers before removing cloud
   targets. Preserve reviewed job configurations and the Mailpit inbox.
5. Execute only the reviewed cloud deletion plan, then check for orphaned disks, addresses,
   load-balancer resources and ongoing usage. Do not delete unrelated projects/resources.
6. Review credential revocation separately, including whether any token is shared. Do not
   rotate/revoke credentials or remove local Docker volumes merely as incidental cleanup.
7. Check billing after provider reporting delay and document the observed residual resources
   and charges. Do not claim immediate zero cost from a successful deletion command alone.

The student must still watch the whole video, confirm the silent format, explain the major
implementation decisions and perform the final submission. No upload or student rehearsal
has been represented as complete.
