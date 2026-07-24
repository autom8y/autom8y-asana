---
type: review
status: draft
rite: arch
agent: dependency-analyst
date: 2026-07-24
initiative: fleet-delegation-phase2
wave: WAVE-1
lane: FL-2
fork: FORK-C
landing_mode: AUTONOMOUS (evidence-only)
discharges: UV-P #1 (autom8y-auth 4.2.0 CodeArtifact-resolvability)
feeds: SP FORK-alpha option-1 (INFORMATIONAL evidence — NOT a hard blocker on SP)
evidence_ceiling: MODERATE   # main-thread live CodeArtifact probe on fresh interactive IAM-user creds; self-graded; STRONG-lift = rite-disjoint critic CONCUR at CP-3
disciplines: [structural-verification-receipt, credential-scope-assertion-discipline, conventions]
---

# FL-2 FORK-C Resolvability Receipt — autom8y-auth 4.2.0 (2026-07-24)

> **VERDICT: RESOLVABLE.** `autom8y-auth` version `4.2.0` is present in the
> `autom8y-python` CodeArtifact repository (domain `autom8y`, format `pypi`) with
> `status: Published` and is the repository's `defaultDisplayVersion`. The probe
> ran on **FRESH** interactive IAM-user credentials (no 401, no credential
> refresh required). UV-P #1 is **DISCHARGED** (not re-carried).
>
> **THE FORK-C PIN STAYS HELD AT 4.1.0.** This receipt is EVIDENCE ONLY. A
> RESOLVABLE result does NOT bump the pin. This is INFORMATIONAL evidence for
> SP FORK-alpha option-1, not a hard blocker on SP.

## A. The probe — exact command run (verbatim from the frame)

```
aws codeartifact list-package-versions --domain autom8y --repository autom8y-python --format pypi --package autom8y-auth | grep 4.2.0
```

Verbatim stdout (piped-to-grep form; exit 0):

```
            "version": "4.2.0",
    "defaultDisplayVersion": "4.2.0",
```

The grep matched **two** independent lines: the `4.2.0` entry in the `versions[]`
array AND the top-level `defaultDisplayVersion` field. Both confirm presence.

## B. Full raw evidence (the same probe without the grep filter)

Command: `aws codeartifact list-package-versions --domain autom8y --repository autom8y-python --format pypi --package autom8y-auth` (exit 0).

The `4.2.0` version object, verbatim from stdout:

```
        {
            "version": "4.2.0",
            "revision": "Zk1FoF6K2aV/V6Votir2aSgsQEjvr2TX+FTIukJsAgw=",
            "status": "Published",
            "origin": {
                "domainEntryPoint": {
                    "repositoryName": "autom8y-python"
                },
                "originType": "INTERNAL"
            }
        }
```

Top-level fields, verbatim:

```
    "defaultDisplayVersion": "4.2.0",
    "format": "pypi",
    "package": "autom8y-auth",
    "namespace": null
```

`status: Published` is load-bearing: a listed version can be `Unfinished`,
`Archived`, or `Disposed` and NOT installable. `4.2.0` is `Published` and is the
`defaultDisplayVersion` (i.e. the latest published release), so it is fully
resolvable by an authenticated reader. The full listing also confirms the pinned
`4.1.0` (`status: Published`, revision `H8KhYVek4hLPZugUH+nrkLxEsWzc5FinnpFpUm3Axh8=`)
is present and installable — the pin target is intact.

## C. Structural-Verification-Receipt (SVR) — bash-probe

```yaml
structural_verification_receipt:
  claim: "autom8y-auth 4.2.0 is present and Published in the autom8y-python CodeArtifact repository, therefore resolvable/installable to an authenticated reader on fresh credentials"
  verification_method: bash-probe
  verification_anchor:
    source: "aws codeartifact list-package-versions --domain autom8y --repository autom8y-python --format pypi --package autom8y-auth"
    command_output_verbatim: |
      "version": "4.2.0",
      "revision": "Zk1FoF6K2aV/V6Votir2aSgsQEjvr2TX+FTIukJsAgw=",
      "status": "Published",
    exit_code: 0
    claim: "the present-tense CodeArtifact list probe returns a Published 4.2.0 version object; this falsifies any claim that 4.2.0 is absent, unpublished, or unresolvable in the autom8y-python repo at probe time"
```

Receipt-quality: `command_output_verbatim` is a literal contiguous stdout slice
(re-runnable for re-verification); `exit_code: 0`; the `claim` articulates
resolvability (the downstream fact), orthogonal to the raw key-value slice.

## D. Credential scope assertion (per credential-scope-assertion-discipline)

The probe is a **single-protocol, single-receiver, read-only** surface
(HTTPS AWS CodeArtifact `list-package-versions`). Per the discipline's "When to
Use", the 7-step (protocol x scope x auth_routing_field) binding protocol does
NOT formally apply — there is one receiver, one read scope, and no wire-level
tenant `auth_routing_field` to route a write. What the discipline DOES bind here
is scope honesty:

| Axis | Value (name/metadata only — no secret material) |
|---|---|
| Protocol | HTTPS AWS CodeArtifact API (`list-package-versions`, read) |
| Scope | authenticated CodeArtifact read on domain `autom8y` / repo `autom8y-python` |
| Principal | IAM user `arn:aws:iam::696318035277:user/tom.tenuta` (account `696318035277`) |
| Freshness | `aws sts get-caller-identity` exit 0 — creds VALID; no 401; no refresh needed |

**Scope boundary (honesty — no overclaim):** the probe used **interactive
IAM-user read credentials**, NOT the CI/deploy CodeArtifact-login token the build
pipeline would present. The verdict is scoped to "an authenticated reader of
`autom8y-python` resolves `4.2.0` as `Published`." The CI token targets the same
domain/repo, but this receipt does not independently attest CI-token-specific
behavior. That residual is bounded and does not affect the presence/`Published`
fact, which is a property of the repository, not of the reader.

## E. Verdict and disposition

- **Verdict: RESOLVABLE.** `autom8y-auth 4.2.0` exists and is `Published` in
  `autom8y-python`; resolvable on fresh creds.
- **Creds: FRESH.** R-CRED hazard (the inaugural-wave 401 on expired CodeArtifact
  creds) did NOT recur. No credential refresh was executed. UV-P #1 is
  **DISCHARGED**, not re-carried.
- **Pin: HELD at 4.1.0.** Evidence does not bump the pin. FORK-C remains pinned
  to `4.1.0` regardless of this RESOLVABLE result.
- **Feeds:** SP FORK-alpha option-1 as INFORMATIONAL evidence only. Not a hard
  blocker on SP.

## F. Evidence ceiling

MODERATE (self-graded). Main-thread live probe on fresh interactive IAM-user
creds; single-thread synthesis. STRONG-lift = rite-disjoint critic CONCUR at CP-3
(main thread merges after CONCUR + green CI). Secrets referenced by name/metadata
only (IAM ARN + account id; no keys, no tokens, no session material logged).
`revision` hashes are CodeArtifact content-address metadata, not secrets.
