# Step 4.3 — actual AMD64 candidate CI

## Result

Manual Jenkins job `finsecure-ci-amd64-review-20261104041956` **#1 SUCCESS** ran
candidate **`dc7ffe5a2884f8aeb833f9befd0f1be30d608739`** on 4 November 2026.

- **961 tests**, lint/format, packaging and existing source/dependency/image gates passed.
- **33 downloaded artifacts** matched the expected inventory and their checksums.
- Trivy reported **zero UNKNOWN, LOW, MEDIUM, HIGH or CRITICAL findings**. Source Bandit
  retained **43 LOW** findings, with no MEDIUM/HIGH findings; all 15 runtime dependencies
  were audited. No gate suppression, severity change or timeout increase.
- Archive revision/tag/config identity and **linux/amd64** were independently checked.
  The raw scan and summary platform now also have to match the selected target.
- Actual local Mailpit SUCCESS receipt contained the candidate revision. This is not
  external email delivery or instructor acceptance.
- Separate host checks passed **961 tests**, Ruff lint/format and wheel/sdist build.

## Exact artifact

| Identity | Value |
| --- | --- |
| Archive SHA-256 | `c7173b149f2821d3baba3521397eee791dd53f1b9e33c42b07a91eb2e13a0cf0` |
| Config/image ID | `sha256:d4c23d06faf317e704f3732cb8af970a7b896556d1b8e5c90ac65e3ab744ac10` |
| Local tag | `finsecure-pay-ci:jenkins-finsecure-ci-amd64-review-20261104041956-1` |
| Platform | `linux/amd64` |
| Database age at scan completion | approximately 10,412 seconds; policy maximum 86,400 |

The config ID is **not** a registry manifest digest. This image was not pushed, loaded
for an application smoke test, or deployed. Existing GKE image/digest remains unchanged.

## Provenance and scope

The candidate changes export metadata, BuildKit platform and scanner argument together.
Scanner/archive helpers retain ARM64 defaults for explicitly separate workflows; the
current CI verifier explicitly selects AMD64. Regression cases exercise both supported
architectures and reject summary/raw-report mismatches alongside existing integrity
failures. Stage ordering and artifact withholding remain unchanged.

The operator-controlled wrapper cloned public base `19b4486`, checked a locally supplied
Git bundle hash and checked out the full candidate SHA. It used the candidate Jenkinsfile
with only checkout/notification provenance adaptation, validated that Pipeline before
execution, and verified source-scan file hashes against the candidate's Git objects.
This was a real Jenkins run, **not normal SCM triggering or a published-main checkout**.
Review/merge/publication and a normal SCM AMD64 run are still pending. Tests ran on the
ARM64 source worker; BuildKit targeted AMD64 using available emulation. No native GKE
execution of this candidate is claimed.

There was one candidate build and it succeeded; no failed build was retried. The initial
multi-edit request was rejected before changing a test file because its match was
ambiguous; corrected edits were applied and all checks passed before CI. No registry
or deployer credentials were bound by this pipeline.

## Closure and retained evidence

Candidate job disabled; release worker still stopped with exit 143; scheduling guard
active; all earlier diagnostic jobs disabled; queue empty; source worker online.
Normal main remains **#34 SUCCESS**, not this 961-test result. Read-only cloud checks
matched the preceding checkpoint's Deployment UID/generation/spec and Ready Pod UIDs:
two available replicas and public health **200**. No upload or deployment attempted.

Host free storage decreased to approximately **3.2 GiB**, Docker backing storage to
**7.6 GiB**. Review storage before another image build; no shared cache, old scanner
diagnostic, credential or volume was pruned.

[Bundle](step-03-amd64-ci/) retains verification, all artifact hashes, source/image gate
summaries, host checks, Pipeline validation, credential-free operator procedures,
notification summary and final state. Large image/packages and full CI reports remain
in the Jenkins build artifacts and ignored local reports. Host paths are sanitized
where present; private credentials/project/account identifiers are excluded.
[SHA256SUMS](step-03-amd64-ci/SHA256SUMS) covers the reviewed bundle.

Next: reviewed publication and normal SCM verification, followed by a separate trusted
release job with explicit artifact transfer, stale-build, serialization and failure
policies. Automatic publishing/deployment is still unimplemented.
