---
type: handoff
schema: cross-rite-handoff/v1.0
handoff_type: validation
status: proposed
approved_by: OPERATOR-PENDING
from_rite: 10x-dev (premise-validation re-baseline)
from_repo: autom8y-asana
to_rite: operator / eunomia / 10x-dev(follow-on)
initiative: insights-export-tenancy-two-phase
node: PR-2 GRAIN-BRIDGE CONSUMER (#160) — MERGED + DEPLOYED; SUBSTRATE COMPLETE
date: 2026-06-26
prs: { pr2_consumer: 160, resolver: 209, follow_on_open: 161 }
supersedes_premise: "PR-2 BLOCKED on autom8y-core TokenManager ebid-passthrough (UV-P-R2)"
---

# HANDOFF — premise-firewall re-baseline: the Phase-1 substrate is COMPLETE (merged + deployed)

## ★ The correction (the handoff chain ran THREE rungs stale)

The MERGED-seam handoff said "PR-2 BLOCKED on the autom8y-core TokenManager ebid-passthrough";
Pythia's releaser adjudication said "the next rung is to BUILD PR-2 in 10x-dev"; the main thread
relayed it. **All three were stale.** Verified LIVE this session:

- **PR-2 (#160) is MERGED + DEPLOYED.** `feat(leads): per-business single-tenant grain-bridge
  consumer` → merge `f8902aef` on `autom8y-asana/origin/main`, merged **2026-06-26T15:31:36Z**
  (tomtenuta). Deployed: **`Satellite Receiver — asana` completed/success @ 2026-06-26T15:37:52Z**.
- **The UV-P-R2-CACHE fork resolved with NO SDK change** (as Pythia predicted): the consumer mints a
  single-tenant per-business token by **per-business instantiation** — `auth/business_token.py`
  (`BusinessTokenMinter`, `EXCHANGE_PATH = "/tokens/exchange-business"`, `mint(external_business_id)`)
  + `auth/per_business_provider.py` (`PerBusinessTokenProvider` → one `DataServiceClient` per
  business). It consumes the S1 auth grain-bridge (hop-3) directly. **autom8y-core untouched; no
  publish, no releaser leg.** (autom8y-core@4.6.0 already shipped the primitive: `token_manager.py:548`
  `body["business_id"]=str(config.business_id)` → single-tenant TEB; the only constraint was the
  single-token cache `_token:85`, routed around by per-business instantiation.)
- Build includes the discriminating canary (`tests/unit/canary/test_grain_bridge_canary.py`), the
  CLOSED 4-class skip taxonomy (`workflows/leads_skip.py`), ebid compute (`workflows/leads_ebid.py`),
  and the AC-S3 reconciliation invariant (`attempted == succeeded + Σ skip-class`).

## The full substrate — all MERGED + DEPLOYED (verified live)

| Member | Repo | Merge | Deploy receipt |
|---|---|---|---|
| S1 auth ebid-bridge + oracle seal (#779) | autom8y | `1ad88e87` on main | service-deploy (prior) |
| S2/WS-HARDEN office_phone→guid guard (#201/#202/#203) + #206 verify | autom8y-data | on main | deployed |
| **S3 C2 resolver (#209)** | autom8y-data | `5aa49648` on main | **ECS run `28250820372` completed/success @ 16:43:22Z — running INERT** |
| **PR-2 grain-bridge consumer (#160)** | autom8y-asana | `f8902aef` on main | **`Satellite Receiver — asana` success @ 15:37:52Z** |

## Honest rungs (G-RUNG — verified, not rounded)

```
S1+S2+S3+PR-2: merged ✅  +  deployed ✅  (resolver ECS-LANDED; consumer DEPLOYED)
            ≠  key-provisioned  ≠  live  ≠  leads-green
```

**insights-export = live-auth / RED-export, UNCHANGED.** The resolver is **deployed but INERT**
(`RESOLVER_API_KEY` unprovisioned → default-deny reject-all, `resolver_key.py:57-64`), so the
end-to-end grain-bridge cannot run live yet. The export counter
(`insights_export_completed succeeded>0`) reads **ZERO**. No build advances it — the remaining
levers are operator-sovereign + eunomia.

## The counter-moving path is now ENTIRELY operator + eunomia (NO 10x-dev build on it)

1. **OPERATOR — provision `RESOLVER_API_KEY`** (route-scoped, distinct from `AUTOM8Y_DATA_API_KEY`,
   sha256-only in any record). **STRICT-IMPOSSIBILITY from session** (out-of-tree AWS SM/SSM;
   `[[auth-operator-admin-token-dx-gap]]`: botocore[crt] gap + expired admin JWT + interactive-MFA).
   Lifts the resolver from INERT → answering. **THE binding blocker.**
2. **OPERATOR — UV-P-S2-2 normalized re-probe** (`GROUP BY normalize(office_phone)`) + **SUB-1**
   `chiropractors(office_phone)` UNIQUE-index verify (live DB; same AWS wall).
3. **OPERATOR — Lever C1** (exempt SA → `business_scoped:true` + provision ~75-tenant
   `authorized_organizations`). **GR-6 inversion guard is now SATISFIED** (PR-2 deployed) → C1 is
   unblocked-in-sequence. Regresses #747's exempt enrollment; operator-sovereign.
4. **EUNOMIA — the live SUBSTRATE-FLOOR attestation**: the full round-trip
   (`office_phone → resolver(ebid) → auth exchange-business → per-business token → /leads`) +
   the live deny-leg + the C1-arm-vs-live-key. Entry-gated on 1+3. `ari sync --rite=eunomia`.

## Genuine remaining 10x-dev work (FOLLOW-ON polish — none moves the counter)

- **Open PR #161** `feat(fm5): consumer-required-column contract — typed contract-incomplete (ARM-B)`
  (`feat/fm5-column-fidelity`, CI-green @ 16:08) — consumer-contract-completeness hardening; needs
  adversarial qa + rite-disjoint review → merge-ready (operator merge).
- **L-001 Arm-1 enumeration-hardening** on the resolver (autom8y-data; dynamic router introspection
  vs the 4-of-50+ sample) — flagged before-live; UV-P whether already folded into a branch.
- **Worktree hygiene**: `autom8y-asana-wt-grain-bridge @ 10ff40f2` is now redundant (byte-identical to
  merged #160) — safe to prune.
- DEFER (watch, not scope-crept): autom8y-core 4.9.0 bump (asana #159 / data #208); WS-HARDEN
  residuals L15/L12/L5 + F-N1-2/SUB-1 (eunomia close-gate).

## Seam — operator next syncs

```
# The counter-mover (operator hand, then eunomia):
#   1. provision RESOLVER_API_KEY (AWS SM/SSM — interactive)
#   2. fire Lever C1 (exempt→business_scoped:true + ~75-tenant authorized_organizations)
#   3. cd autom8y-data && ari sync --rite=eunomia   # the live attestation
# The 10x-dev follow-on (polish, parallelizable, non-counter-moving):
#   cd autom8y-asana && ari sync --rite=10x-dev     # /task #161 ARM-B → merge-ready
```
Do NOT dispatch the next rite's specialists from this context — they load on sync + restart.

— END HANDOFF —
