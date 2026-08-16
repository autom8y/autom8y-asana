---
type: review
status: accepted
---

# ENUM — Fleet gitleaks RED/GREEN prediction at re-pin

**Wave**: coc-reattest-seam (LANE B, pythia-ruled lever 2b)
**Author**: platform-engineer (sre, co-seated)
**Date**: 2026-08-16
**Evidence grade**: MODERATE (self-ref cap; single-attester local reproduction, no rite-disjoint corroboration)
**Scope**: read-only enumeration. No repo was re-pinned. No PR was opened on any enumerated repo.

---

## §0 Question

`autom8y-workflows` PR #30 (`6753f943212f7c3b63658ac700f6d8194771cd1b`) retired the
`|| true` exit-code swallow from `security-gitleaks.yml`. All external consumers pin an
immutable SHA, so the retirement is **inert** for them until a deliberate re-pin.

This enumeration answers, for each of the 8 private consumers: **if that repo re-pinned
today, would the delegated `gitleaks / Secrets Scan` leg go GREEN or RED?**

autom8y-asana is excluded from the table — it is lever 2a and is already re-pinned
(PR #379, delegated leg observed GREEN on the live wire).

---

## §1 Method

Each repo was cloned **fresh** into a scratchpad (never scanned in place, never scanned
from an existing local checkout — existing checkouts carry uncommitted operator state and
divergent branch sets). gitleaks was then run locally at the **same engine version the
reusable installs** (8.24.3), with the **same invocation shape** an un-swallowed delegated
leg would use:

```
gitleaks detect --source . --redact --no-banner --exit-code 1
```

No baseline flag is passed, mirroring the reusable — gitleaks auto-discovers a repo-root
`.gitleaksignore` and `.gitleaks.toml`. Any repo that carries a baseline therefore has it
honored in these numbers automatically.

**Substrate fidelity.** The reusable checks out with `fetch-depth: 0`, so the CI scan sees
all fetched refs, not just the default branch. A full `git clone` reproduces this: remote
refs live under `refs/remotes/`, and `gitleaks detect` walks `git log --all`, which includes
them. Reproduction of the invariant was confirmed against asana itself, where the local
scan (1949 commits) is a strict superset of the CI scan (1629 commits) and both report
`no leaks found`.

**CR-5 compliance.** `--redact` was set on every run. This document records **counts, rule
IDs, and file paths only**. No secret value, and no finding fingerprint containing one, is
reproduced here or in any scratchpad artifact retained past cleanup.

---

## §2 Prediction table

| Repo | Findings | Rule IDs (redacted) | `.gitleaks.toml` | `.gitleaksignore` | Required ctx? | Predicted post-re-pin |
|---|---:|---|:---:|:---:|:---:|---|
| **autom8y** (monorepo) | **148** | generic-api-key ×58, stripe-access-token ×49, asana-client-id ×14, curl-auth-header ×12, cloudflare-api-key ×8, private-key ×6, hashicorp-tf-password ×1 | yes | **no** | **YES** | **RED — merge-blocking** |
| **autom8y-data** | **69** | generic-api-key ×66, curl-auth-header ×3 | yes | **no** | no (9 ctx, gitleaks absent) | **RED — non-blocking** |
| **autom8y-scheduling** | **13** | generic-api-key ×11, asana-client-id ×1, curl-auth-header ×1 | no | **no** | no protection | **RED — non-blocking** |
| **autom8y-ads** | **8** | jwt ×6, generic-api-key ×2 | yes | **no** | no protection | **RED — non-blocking** |
| **a8** | **4** | generic-api-key ×4 | yes | **no** | no (1 ctx, gitleaks absent) | **RED — non-blocking** |
| **autom8y-sms** | **2** | generic-api-key ×2 | yes | **no** | no protection | **RED — non-blocking** |
| **autom8y-dev-x** | **1** | generic-api-key ×1 | no | **no** | no protection | **RED — non-blocking** |
| **autom8y-api-schemas** | **0** | — | no | no | no protection | **GREEN — safe to re-pin now** |

**Headline: 7 of 8 would go RED. 1 is safe.**

**Not one of the 8 carries a `.gitleaksignore`.** asana is the only repo in the fleet with a
committed baseline. Every finding above is therefore unmasked — there is no baseline
absorbing any of it.

---

## §3 The one that actually bites

Blast radius is not consumer count. Only **two** repos in the org carry
`gitleaks / Secrets Scan` as a *required* status check: `autom8y` (monorepo) and
`autom8y-asana`. asana is done and green.

That leaves **autom8y monorepo as the single dangerous re-pin in the fleet**: 148 unmasked
findings, no baseline, and the check registered as required under branch protection. A
re-pin there without prior remediation converts every open and future PR into a hard block.
The other six RED repos would surface a failing check that blocks nothing.

**The monorepo re-pin is a two-file change.** `.github/required-contexts.expected.txt:34`
encodes the callee SHA and is validated by `scripts/ruleset-context-name-parity.py`, which
refuses any ref that is not a 40-hex commit SHA. Editing only the workflow breaks parity.

**Flag — stale `armed` label.** That row currently reads:

```
armed|gitleaks / Secrets Scan|autom8y/autom8y-workflows/.github/workflows/security-gitleaks.yml@f5601acbe3905270dfcb9069854c78c0f940ad05
```

It asserts `armed` for the **swallowed** pin — a gate structurally incapable of failing. The
ledger's own claim about the monorepo's posture is false today. This is a governance-debt
finding independent of whether the re-pin proceeds.

---

## §4 HEAD-survival (remediation shape)

Path-level proxy: does the file carrying the finding still exist at HEAD?

| Repo | Findings | Distinct files | Files present at HEAD | Findings in HEAD-present files | Findings in deleted files |
|---|---:|---:|---:|---:|---:|
| autom8y | 148 | 59 | 42 | 77 | 71 |
| autom8y-data | 69 | 25 | 11 | 14 | 55 |
| autom8y-scheduling | 13 | 4 | 4 | 13 | 0 |
| autom8y-ads | 8 | 7 | 7 | 8 | 0 |
| a8 | 4 | 3 | 3 | 4 | 0 |
| autom8y-sms | 2 | 2 | 2 | 2 | 0 |
| autom8y-dev-x | 1 | 1 | 1 | 1 | 0 |

[UV-P: per-finding HEAD-survival at line granularity | METHOD: deferred-to-triage-lane | REASON: this is a path-existence proxy — a file present at HEAD may have had the secret line removed, and a file absent at HEAD may still carry the secret on a live non-default branch. Exact survival requires per-fingerprint content triage of the class R-CC7-1 ran for asana.]

**Consequence for remediation.** gitleaks walks full history. Deleting a file at HEAD does
**not** clear its finding — 71 of the monorepo's 148 and 55 of autom8y-data's 69 already sit
in files that no longer exist at HEAD and are still detected. The only mechanisms that clear
a finding are a `.gitleaksignore` baseline, a `.gitleaks.toml` allowlist, or history rewrite.
For every repo above, **the re-pin's precondition is a triaged baseline, not a cleanup commit.**

The dominant rule is `generic-api-key` (145 of 245 fleet-wide), and the dominant paths are
test fixtures (`tests/api/...`, `tests/auth/...`) and design/spike documents
(`.ledge/spikes/...`, `.sos/wip/frames/...`). That shape is consistent with a high
false-positive rate — asana's own triage dispositioned 28 of 31 as false-positive. **It is not
evidence of one.** Classes that warrant real triage attention before any baseline is minted:
`private-key` ×6, `stripe-access-token` ×49, and `cloudflare-api-key` ×8, all in the monorepo.

---

## §5 Standing law

**A green delegated leg proves "no unbaselined finding". It never proves "history clean."**
Anything a baseline masks is invisible to a green run by construction. This holds for asana
post-re-pin and would hold for every repo above. Rotation obligations are not discharged by
a gate going green.

---

## §6 Per-repo receipts

Engine: gitleaks 8.24.3 (darwin_arm64), matching the reusable's pinned `GITLEAKS_VERSION`.
Command, identical for every row:

```
gitleaks detect --source . --redact --no-banner --exit-code 1
```

Exit 1 = findings present (would fail an un-swallowed job). Exit 0 = clean.

| Repo | Exit | UTC | Commits scanned |
|---|:---:|---|---:|
| a8 | 1 | 2026-08-16T17:45:24Z | 701 |
| autom8y-ads | 1 | 2026-08-16T17:45:26Z | 424 |
| autom8y-api-schemas | **0** | 2026-08-16T17:45:27Z | 100 |
| autom8y-data | 1 | 2026-08-16T17:45:40Z | 1938 |
| autom8y-dev-x | 1 | 2026-08-16T17:45:42Z | 116 |
| autom8y-scheduling | 1 | 2026-08-16T17:45:44Z | 220 |
| autom8y-sms | 1 | 2026-08-16T17:45:45Z | 306 |
| autom8y | 1 | 2026-08-16T17:46:02Z | 2923 |

Clone timestamps 2026-08-16T17:43:10Z–17:43:34Z; all clones removed after scanning.

**Census receipt** — every repo consumes the reusable via a single
`.github/workflows/gitleaks.yml`. Current pins: `44b771e5…` ×7 (a8, autom8y-ads,
autom8y-api-schemas, autom8y-data, autom8y-dev-x, autom8y-scheduling, autom8y-sms) and
`f5601acb…` ×1 (autom8y monorepo). Both are pre-retirement; neither bites.

**Branch-protection receipt** — `gh api repos/autom8y/{repo}/branches/main/protection`:
protected with gitleaks required = `autom8y`, `autom8y-asana` (asana also carries
`Secrets Scan (enforcing)`, so R-3 ACTION 2 registration is complete there); protected
without gitleaks = `a8` (1 ctx), `autom8y-data` (9 ctx); unprotected = `autom8y-ads`,
`autom8y-api-schemas`, `autom8y-dev-x`, `autom8y-scheduling`, `autom8y-sms`.

---

## §7 Recommended sequencing (advisory — no lever fired)

1. **autom8y-api-schemas** — re-pin whenever convenient. Zero findings, no protection, no baseline needed. Free.
2. **The five unprotected RED repos** (ads, dev-x, scheduling, sms + a8/data which are protected but do not gate on gitleaks) — re-pin is non-blocking, so the leg can be armed to *surface* signal before it is made to bite. Triage-then-baseline per repo.
3. **autom8y monorepo — do not re-pin until a triaged baseline lands.** 148 unmasked findings against a required context. Sequence: triage (rotate/false-positive/accept, as R-CC7-1 did for asana) → mint `.gitleaksignore` → re-pin workflow **and** `required-contexts.expected.txt` in one change → verify parity script passes.

The stale `armed|` label at `required-contexts.expected.txt:34` should be corrected
regardless of re-pin timing, since it currently misrepresents the monorepo's gate posture.
