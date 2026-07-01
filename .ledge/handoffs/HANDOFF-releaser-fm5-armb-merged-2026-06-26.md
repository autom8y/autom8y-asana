---
type: handoff
status: accepted
handoff_type: execution
from_rite: releaser
to_rite: operator
date: 2026-06-26
initiative: receiver-contract-realization
node: FM-5 ARM-B -> MERGED (PR #161) -> operator/eunomia realization ladder
rung: "FM-5 ARM-B = merged (a87ae1ca); build seal = STRONG; verified_realized = [UNATTESTED — DEFER-POST-HANDOFF]"
seam_state: "MERGED. merged != live != verified_realized. The realization ladder (S9 live-HTTP canary, S10 denylist-retirement, the Door-C/SEAM-2 cure) is operator/eunomia-held."
authority_anchors:
  - "MERGED: PR autom8y/autom8y-asana#161 state=MERGED, mergedAt 2026-06-26T16:49:55Z, merge_sha a87ae1caaf..."
  - "origin/main advanced f8902aef -> a87ae1ca; squash 'feat(fm5): consumer-required-column contract -- typed contract-incomplete (#161)'"
  - "consumer surface on origin/main: field_contract_maps.py + query/engine.py + consumer_column_requirements.vendored.json (git cat-file -e OK)"
  - "CI all-green on ad8817757 (0-behind CLEAN = merged-equivalent tree); pre-merge re-verify CLEAN/MERGEABLE, scope clean"
  - "STRONG verdict: .ledge/reviews/fm5-armb-strong-verdict.md (rite-disjoint review critic; Grade A; cross_stream_concurrence: true)"
---

# HANDOFF — releaser-leg close — FM-5 ARM-B MERGED (#161)

## Grandeur Anchor
receiver-contract-realization makes a requested-but-absent REQUIRED column on `/v1/query` return a TYPED
contract-incomplete signal so the silent-drop / daily-KeyError / $0-7-row fossil class dies at the receiver.
FM-5 ARM-B is now **merged** (PR #161, `a87ae1ca`). `merged != live != verified_realized` — the merge ships
the additive, two-way-door mechanism; it did NOT activate the Door-C/SEAM-2 cure or discharge eunomia's
S9/S10. The realization ladder is the operator's (and eunomia's, at the live altitude).

## §1 — Landed (rung = `merged`)
PR #161 squash-merged to `main` at **`a87ae1ca`** (2026-06-26T16:49:55Z). `origin/main` f8902aef -> a87ae1ca.
Consumer surface resolves on `origin/main` (field_contract_maps.py + query/engine.py + the vendored manifest).
Land-proof: CI all-green on ad8817757 (the 0-behind/CLEAN merged-equivalent tree) + the merge SHA +
the surface-on-main receipt. Releaser self-attest of the LAND = MODERATE (CI+SHA mechanical); the STRONG
*build seal* is the review critic's, already issued.

## §2 — Rungs (G-RUNG — not rounded)
- FM-5 ARM-B = **merged** (`a87ae1ca`).
- build seal = **STRONG** (review-rite, rite-disjoint; `fm5-armb-strong-verdict.md`).
- **`verified_realized` = [UNATTESTED — DEFER-POST-HANDOFF]** — eunomia, LIVE: S9 = live `/v1/query` HTTP
  two-sided canary; S10 = operator-denylist retirement. The merge certifies neither.
- **NOT the gfr telos proof** — gfr `verified_realized` (`.know/telos/gfr.md:79-89`) is the send-origination
  round-trip at a distinct altitude, eunomia's. The fm5-column-fidelity telos
  (`.know/telos/fm5-column-fidelity.md`) carries its own eunomia verified_realized (deadline 2026-07-31).

## §3 — The operator/eunomia realization ladder (merged -> live -> verified_realized; surface-only)
1. **Door-C `project_gid`/section widen + SEAM-2 rebind** of `business_offers` onto `entity_type=offer`
   (the cure ARM-B's permanent loud `contract_complete=False` signal drives) — operator-held, premise-gated.
2. **The monolith manifest hand-back** finalizes the declared union (the drift guard runs schema-only until then).
3. **S9 live-HTTP two-sided canary** + **S10 denylist-retirement** -> eunomia `verified_realized` (live).
4. Prod deploy, the operator denylist — operator-sovereign.

## §4 — Watch-register (operator/critic-held; none scope-crept into the merge)
- Door-C/SEAM-2 cure + the monolith manifest hand-back — operator/SEAM-2.
- S9 live-HTTP canary + S10 denylist-retirement -> eunomia verified_realized.
- **FM-5 F2** (column_manifest projected-frame, Medium -> S9) + **F3** (empty-string member, Low) -> 10x-dev/principal-engineer if pursued.
- **grain-bridge FINDING-1** (collision_conflict consumer test) -> 10x-dev/principal-engineer.
- gfr `verified_realized` (distinct initiative + altitude) -> eunomia.

## §5 — Next step
No further rite-specialist dispatch is required for the merge (done). The realization ladder (§3) is the
operator's to walk when ready (frame the cure/activation via `ari sync --rite=…` only if you choose to
orchestrate it). F2/F3 + FINDING-1 route to 10x-dev/principal-engineer in parallel. The
receiver-contract-realization build->merge arc is closed at `merged` + STRONG-sealed.
