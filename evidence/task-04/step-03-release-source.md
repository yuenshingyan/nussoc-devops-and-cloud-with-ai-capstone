# Step 4.3 — Trusted Git source and preparation candidate

**Status:** code/helper checkpoint verified; not installed, merged or published. No
worker startup, CI/image build, credential binding, upload or cloud mutation occurred.

## Actual source acquisition

The controller fetched the fixed public GitHub codeload endpoint for immutable revision
`19b44861114c18e07dff249423365215547035a3`. It used HTTPS with no proxy, redirects or
added credentials, and the existing bundled Ant 1.10.18 reader. No dependency was added.
No fetched code was checked out, extracted, installed or executed.

The helper read **1,492 tree entries**, retaining **245,380 selected bytes** as hashes
and two metadata documents. All **30 Python source hashes**, `uv.lock` and
`pyproject.toml` hashes matched independent local Git objects at that exact revision.
Observed acquisition time was **1.68 seconds**, not a latency guarantee.

Native checks also passed:

- Seventeen archive fixtures, including valid/exact-size inputs and rejection of
  duplicate/traversal/wrong-prefix paths, links, directory data, missing inputs,
  oversized source, excess file count and incorrect/duplicate Git commit headers.
- Three bounded-stream cases: read overflow, skip overflow and expired deadline.
- Four invalid revision cases, rejected before constructing a source request.

The helper hashes source bytes and retains only lock/project metadata as data. The
[runbook](../../docs/runbooks/cloud-delivery.md) records limits, ownership and trust:
GitHub over TLS plus the independently selected revision, not independently verified
commit signatures or reproducible-build attestation. Blocked-I/O/DNS cancellation and
the complete Pipeline timeout remain unproved.

## Preparation composition

`release-preparation.groovy` composes authoritative selection, independent source
acquisition, revision/lock binding, fresh re-selection, then controller-owned transfer.
It does not bind credentials, provide verifier code from Git, run a worker process or
authorize publishing. Its result explicitly requires independent worker verification.

Native checks used the real fetched snapshot with a **synthetic candidate image
identity** to test context construction; mismatched revision/lock and invalid build
identity were rejected. Simulated upstream envelopes around actual main #33 and #34
were rejected as superseded and ARM64, respectively, before preparation. There is no
claim of positive full preparation, real downstream triggering or Pipeline-body execution.
The future fixed Pipeline must bundle reviewed verifier code separately and own scratch
cleanup; it must not execute source fetched from Git or upstream artifacts.

## Retained failures and checks

1. The first observer could not resolve Commons Compress. No source request ran.
   The helper was changed to Jenkins' existing bundled Ant reader.
2. A valid fixture then failed because Groovy `entry.file` selected Ant's nullable
   `getFile()` rather than `isFile()`. Explicit type predicates corrected this.
3. The first public archive attempt rejected its prefix because Ant exposed Git's
   global commit-comment header. A read-only header diagnostic identified the exact
   52-byte record. The helper now accepts only one exact matching commit record before
   the tree; incorrect/duplicate records are rejected. No arbitrary prefix exception.

Original procedures, helper versions and responses remain under ignored
`reports/release-source/{first-attempt,second-attempt,third-attempt}/`. These were
explicit corrected verification attempts, not automatic mutation retries.

All **1,064 host tests**, Ruff lint/format, `uv build` and existing source/dependency
gates passed. There are two additional structural wiring checks; native behavior tests
are recorded separately. The source gate retained 43 LOW findings with zero blocking
findings; all 15 runtime dependencies were clean.

## Closure and pending work

Read-only closure verified the older installed selection script remains exact, disabled,
unbuilt and pending approval; approved-script count is zero. The working selection and
new helper candidates are intentionally not installed. Worker stayed stopped, source
worker online, diagnostic jobs disabled and queue empty. Main CI remains #34 SUCCESS
(781 tests), not this host run. Cloud Deployment specification and Pod identities were
unchanged, with two Ready replicas and public health 200.

Fixed Pipeline assembly, positive preparation with an eligible normal-main AMD64 build,
reviewed installation/scheduling, publishing/deployment and genuine downstream,
concurrency, timeout/cancellation and restart evidence remain pending. No merge or push
was performed. Storage headroom must still be reviewed before an image build.

The adjacent [`step-03-release-source/`](step-03-release-source/) bundle contains reviewed
results, code hashes, sanitized host output, source-gate summary and credential-free
historical observer procedures. `SHA256SUMS` covers the bundle. Large source responses
were consumed in memory, not archived or executed on a worker.
