# Step 3.3 — source and exact AMD64 release published

Date: 3 November 2026. User approved source merge/publication and publication of the
exact tested AMD64 image. **No cluster creation or application deployment was authorized
or performed in this operation.**

## Source publication and automatic CI

Main was fast-forwarded from `f22628a` to
`22048c8c0cfd90b204945df5c1e842c9577e892b` and pushed without force. The working tree
was not switched through an older commit: the live Jenkins notification bind source
remained present. Remote/main equality, ancestry, clean tree, idle agent and empty
queue were checked before publishing. Notification/secret boundaries passed before
and after, with the notification file hash unchanged.

Automatic main **#32 SUCCESS** was verified as an SCM-triggered, SCM-loaded pipeline,
not a manual build or selected passing retry:

- **770 tests passed**, no failed/skipped tests or pytest warning summary.
- Lint, formatting, packaging, source/dependency and image gates passed; **33 artifacts**.
- Source gate retained 31 LOW Bandit findings; no suppression or policy change.
- Coverage quality gates remain INACTIVE; this is not a newly enabled coverage gate.
- Real local Mailpit receipt: `[SUCCESS] finsecure-ci #32`, approved synthetic sender/
  recipient, exact published source revision. Not internet email delivery.
- Anonymous raw-GitHub reads of the Dockerfiles at both published main and image-source
  revision returned HTTP 200 and matched Git bytes. The image-source commit is reachable
  in published history, not an inaccessible local-only reference.

## Registry publication and recovery from missing login

The first credential preflight failed: Docker's desktop credential store listed no
Docker Hub entries. **No push was attempted then.** The user signed in locally; the
subsequent lookup matched the approved `yuenshingyan` namespace. No credential-helper
bypass, secret export, rotation or registry change was used.

Both new tags were verified absent before push, while historical digests were recorded.
The existing exact tested local image ID was tagged and pushed normally with the
operator's authenticated Docker configuration. No rebuild occurred between gate,
smoke test and push. These are workflow immutability checks, not a claim that Docker Hub
server-side immutable tags are enabled or that multi-tag publication is atomic.

| Identity | Verified value |
| --- | --- |
| Repository | `docker.io/yuenshingyan/finsecure-pay` |
| Tags | `0.3.0`, `sha-4b243e2-amd64` |
| Source revision | `4b243e278ee749c4d08bc713cd803bdd77b7e132` |
| Platform | **linux/amd64 only** |
| Config / tested image ID | `sha256:798fcb8de76aa2c6e15393911bb4edb51a5bd5f6c0bf4dd169d9dca3fa1714d8` |
| Registry manifest digest | `sha256:1fc3362f15ba91f4161b8fccab644631ccc0733e9b9675bb7e2cb88e7aea5b4c` |
| Tested archive SHA-256 | `d81de74c46fbea010585434060fccf30f74e050a1815751ab6f34f9fe5dc809e` |

The [candidate evidence](step-03-amd64-gate.md) records the actual image gate with zero
reported vulnerabilities. That is a scan-time result, not a guarantee of future safety.

## Anonymous verification and runtime

- Both new tags returned the same manifest; raw manifest SHA-256 matched the registry
  content-digest header. Its config digest matched the exact tested image ID.
- Anonymous config retrieval verified Linux AMD64, non-root user, version 0.3.0 and
  image-source revision. Registry authorization was not forwarded to the blob CDN.
- An isolated empty Docker configuration was used **only for the anonymous pull check**,
  not as an authentication workaround for pushing. The pull used local layer cache;
  it does not prove a completely uncached node download.
- Pulling by the immutable digest produced the same image ID. The existing smoke test
  passed again under local AMD64 emulation and removed its owned test container.
- Historical tags remained unchanged:
  - 0.1.0: `sha256:18397d4d8391cdfde3220222f0b5d07afa8cbc2afaf92ef8b7d2b23b6494c10c`
  - 0.2.0: `sha256:48ee0ef91737fd2ee1d2efea93cf9a94e840eec6908bde6ed3af7afede884e99`

## Identity and scope limits

The published AMD64 operator artifact comes from **4b243e2**. Jenkins #32's independently
built ARM64 artifact comes from **22048c8**. They are not the same image or source
revision; the intervening changes were documentation/evidence only, verified by a
path-scoped Git diff. The old Kubernetes pin is still 0.2.0 and no manifest was applied.
No native GKE runtime, external application endpoint or cloud rollout is proven here.

The proposed cluster/resource/access profile still requires approval, including its
public HTTP synthetic-only exposure and provisional S$225 planning envelope. No paid
billing upgrade occurred. Image publication does not authorize creating billable resources.

Artifacts: [manifest](step-03-publication/SHA256SUMS),
[SCM verification](step-03-publication/scm-verification.json),
[SCM completion](step-03-publication/scm-completion.json),
[local notification](step-03-publication/notification.json),
[credential diagnostic](step-03-publication/credential-diagnostic.json),
[registry preflight](step-03-publication/image-before.json),
[push progress](step-03-publication/push-progress.json),
[registry verification](step-03-publication/image-verification.json),
[post-pull smoke](step-03-publication/published-smoke.json).
