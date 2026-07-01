---
type: handoff
status: accepted
handoff_type: implementation
from_rite: releaser
to_rite: 10x-dev
date: 2026-06-26
initiative: receiver-contract-realization
node: S1 (WS-PIN landing) -> S2/S3 (FM-5 premise + design-lock)
rung: "S1 = merged; initiative verified_realized = UNATTESTED"
seam_state: "S1 MERGED — seam reached; HALT for operator-walked rite-switch to 10x-dev"
authority_anchors:
  - "PR autom8y/autom8y-asana#114 state=MERGED mergedAt=2026-06-26T10:36:45Z"
  - "merge_sha=b9648de494115063161cd1e019ec1a931c05d725 (origin/main)"
  - "ci_green_head=d5bcb55c92564f8e0bd5871eac754e6bf42748c6 run=28232420336 (23 pass / 2 skip / 0 fail)"
  - "shape=.sos/wip/frames/receiver-contract-realization.shape.md (S1; edges E1-E4)"
  - "frame=.sos/wip/frames/receiver-contract-realization.md (realization predicate)"
  - "ordering-pin=.ledge/decisions/ORDERING-PIN-114-before-fm5-design-lock-2026-06-11.md"
---

# HANDOFF — releaser -> 10x-dev — receiver-contract-realization (S1 landed)

## Grandeur Anchor
receiver-contract-realization makes the monolith + fleet **consume** the GFR-realized honest
contract so the live **$8,775 BusinessOffers fossil dies at root** and the operator's denylist
bridge becomes **retireable**. S1 closed only the WS-PIN gate (the FieldContract SSOT on main).
The cure is NOT realized until the two-sided discriminating canary (S9) and the
denylist-retirement (S10) pass — downstream, rite-disjoint from the 10x-dev builder.

## §1 — What landed (S1 = `merged`), with receipts
| Claim | Receipt (mechanical) |
|---|---|
| Receiver #114 MERGED | `gh pr view 114` -> state=MERGED, mergedAt 2026-06-26T10:36:45Z |
| Merge SHA on main | **b9648de4**94115063161cd1e019ec1a931c05d725 ; `origin/main` e49c30d7 -> b9648de4 |
| **E1 CLOSED** — FieldContract SSOT on main | `git cat-file -e origin/main:src/autom8_asana/dataframes/contracts/field_contract_maps.py` -> PRESENT |
| CI all-green on the merged tree | head d5bcb55c, run 28232420336: 23 pass / 2 skip / 0 fail |
| GFR spine GREEN (strictly-additive) | `ci / Test (shard {1..4}/4)` all PASS on d5bcb55c (the 105-spine tests) |
| Scope clean (no stowaways) | #114 = 4 files: contracts/`__init__`+`field_contract_maps`, schemas/`asset_edit`, tests/`test_field_contract_parity` |
| Dormant seam untouched | #114 does NOT touch monolith `business_offers/main.py:164,203,223` (that seam is in autom8, not this repo) |

**Land-fix-up applied (recorded honestly, not papered):** #114 was 38 commits behind and its new
test file was unformatted (real `ruff format --check` red) + the prior OpenAPI check hit a
transient CodeArtifact timeout. Resolved in an isolated worktree: merge `origin/main` in (clean,
`ort`, zero conflicts) + `ruff 0.15.4 format` of `test_field_contract_parity.py` (1 file, 2 lines)
-> pushed d5bcb55c -> fresh CI all-green -> squash-merged. This was a landing fix-up (format +
update-branch), **not a build**; no logic touched.

## §2 — Rung statement
- **S1 -> `merged`** (`authored < emitting < alerting < proven < merged < live < protecting-prod`).
- **Initiative `verified_realized` -> UNATTESTED.** Do NOT round `merged` to realized. The
  predicate's two arms + the denylist-retirement are S9/S10, attested by a REVIEW-rite critic
  rite-disjoint from the 10x-dev builder AND from releaser (self-grade caps MODERATE).

## §3 — What is now unblocked (for 10x-dev)
E1 (`#114 merge ≺ FM-5 design-lock`) is satisfied — the FieldContract SSOT (`field_contract_maps.py`)
now exists on main, so **FM-5 design-lock has a home to land in**. Per the shape DAG, 10x-dev owns:
- **S2 — premise-validation (architect/principal-engineer):** query the REAL production frame
  shape for BusinessOffers (GID 1143843662099250) BEFORE any "declare required column" design-lock
  (`@premise-validation-discipline`). Evidence the column set; do not assume.
- **S3 — FM-5 build (ARM-B):** consumer-required-column declaration -> typed `contract-incomplete`
  on `/v1/query` (silent drop -> loud typed signal), built INTO the SSOT (`field_contract_maps.py`),
  + Door-C receiver projection widening. Contract LOCUS is a genuine fork (FORK-A in the shape:
  consumer vs `/v1/query` endpoint vs two-layer — enumerate at design-lock, Pythia-nav).
- S2 ∥ S3-precondition; then S3 -> S4 (rite-disjoint attest) -> S5 (merge, ARM-B live).

## §4 — Carried realization predicate (verbatim — into every downstream sprint exit)
> "Verified-realized" = a rebound consumer (start C3=OfferHolders, cheapest-ready) computes REAL
> non-$0 economics off a real offer_id/asset_id-bearing frame for BusinessOffers (project GID
> 1143843662099250), AND a frame missing the required column returns a typed contract-incomplete
> (NOT KeyError, NOT silent-drop, NOT fossil) — both arms proven by ONE two-sided discriminating
> canary RUN by a rite-disjoint critic; AND the operator can drop both GIDs from
> SATELLITE_GET_DF_GID_DENYLIST with NO fossil reappearing. NOT "FM-5/SEAM-2 PRs merged."

## §5 — Acceptance criteria + design references for 10x-dev
- Design references: `@.ledge/specs/SPEC-fm5-consumer-column-declaration-shape-2026-06-11.md`,
  `@.know/telos/fm5-column-fidelity.md`, `@.know/telos/seam2-consumer-realization.md`,
  `@.sos/wip/frames/receiver-contract-realization.shape.md` (S2-S5 + FORK-A).
- Strictly-additive: 105 GFR spine GREEN, `assert_rows_tenant_identity` fires RED-on-bypass,
  `_resolve_identity_plan_async` frozen. Derive/delegate-never-replicate (consume the GFR contract;
  do NOT grow a second engine). Drift gate WARN-first; codegen-from-model is FORBIDDEN (reverses
  ADR-S4-001, one-way door).
- ARM-B canary (two-sided): a frame MISSING a required column returns typed contract-incomplete;
  a complete frame passes — RUN by the disjoint critic at S4/S9, never the builder.

## §6 — Risk carry + DEFER watch-register (none scope-crept into S1)
- **R1 dormant-seam prod-breaker** — monolith `business_offers/main.py:164,203,223` byte-locked by
  `test_offer_contract.py:254-272`; NEVER graft a guard there (the review critic already caught
  this). Out of this repo's scope anyway.
- **R2 legacy-arm S3 stale-cache** — the operator's denylist bridge leans on the legacy SDK cache;
  confirm freshness when SEAM-2 retires it (S10).
- **R3 receiver-#114 gate** — RETIRED (S1 closed it).
- **DEFER-1** fleet cf-contract registry (Future-4) — escalate-only one-way door (S4a/S4c). NOT this
  crusade. Confirmed not pulled into S1.
- **P-6 verdict-UV-P** — gfr-dynvocab `verified_realized` verdict exists only as an uncommitted file
  in the `autom8y-asana-wt-gfr` worktree (never committed to any ref); telos citation dangles.
  Non-blocking corroboration gap; operator owns whether to durably anchor it.
- **denylist POPULATION** — the operator's reversible bridge (GIDs 1202204184560785,1143843662099250);
  this crusade makes it RETIREABLE, it does not set it.

## §7 — Next command (operator-walked; releaser does NOT dispatch 10x-dev)
The next node (S2/S3) is a different rite. The operator walks the switch:
```
ari sync --rite=10x-dev    # + CC restart
# then: /frame the FM-5 design-lock (S2 premise-validation -> S3 build), grounded in this handoff + the shape
```
Releaser HALTS here. Do not dispatch 10x-dev specialists from this rite (agents cannot cross rites;
main-thread is the sole dispatcher within a rite).
