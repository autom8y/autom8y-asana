---
type: handoff
status: accepted
handoff_type: execution
from_rite: releaser
to_rite: operator
date: 2026-06-26
initiative: grain-bridge-resolver
node: thin asana leads consumer -> MERGED (PR #160) -> operator realization ladder
rung: "consumer = merged (f8902aef); verified_realized = [UNATTESTED — DEFER-POST-HANDOFF]"
seam_state: "MERGED. merged != live != verified_realized. The prod-activation ladder (Lever C1, dedicated-SA, fleet-retire, scheduling) is operator/eunomia-held."
authority_anchors:
  - "MERGED: PR autom8y/autom8y-asana#160 state=MERGED, mergedAt 2026-06-26T15:31:36Z, merge_sha f8902aef73f88c7bc4deafee12b5ff7d8d255244"
  - "origin/main advanced b9648de4 -> f8902aef; squash commit 'feat(leads): per-business single-tenant grain-bridge consumer (#160)'"
  - "consumer surface on origin/main: src/autom8_asana/auth/business_token.py + automation/workflows/{leads_consumer,leads_ebid}.py (git cat-file -e OK)"
  - "CI all-green on 10ff40f2 (0-behind CLEAN = merged-equivalent tree): Lint&Type, OpenAPI Drift, 4 test shards, coverage/fleet/security/CodeQL all pass"
  - "STRONG verdict: .ledge/reviews/grain-bridge-consumer-strong-verdict.md (rite-disjoint review critic; Grade A; cross_stream_concurrence: true)"
  - "consumed contract: auth f2a95959 (seal surface byte-stable since 1ad88e87); data dd4566e5"
---

# HANDOFF — releaser-leg close — grain-bridge consumer MERGED (#160)

## Grandeur Anchor
grain-bridge-resolver retires the shared fleet token by making each ACTIVE customer's nightly leads
read a single-tenant per-business call, without re-opening DATA-VAL-003. The thin consumer is now
**merged** (PR #160, `f8902aef`). `merged != live != verified_realized` — the merge did NOT activate
the flag-gated consumer, retire the fleet token, or discharge the gfr telos. The realization ladder
is the operator's (and eunomia's, at the live altitude).

## §1 — Landed (rung = `merged`)
PR #160 squash-merged to `main` at **`f8902aef`** (2026-06-26T15:31:36Z). `origin/main` b9648de4 -> f8902aef.
Consumer surface resolves on `origin/main` (business_token.py + leads_consumer.py + leads_ebid.py).
Land-proof: CI all-green on `10ff40f2` (the 0-behind/CLEAN merged-equivalent tree) + the merge SHA +
the surface-on-main receipt — not the PR's stale check alone. Releaser self-attest of the LAND = MODERATE
(CI+SHA mechanical); the STRONG *seal* is the review critic's, already issued.

## §2 — Rungs (G-RUNG — not rounded)
- consumer = **merged** (`f8902aef`).
- consumer seal = **STRONG** (review-rite, rite-disjoint; `grain-bridge-consumer-strong-verdict.md`).
- **`verified_realized` = [UNATTESTED — DEFER-POST-HANDOFF]** — eunomia, LIVE, post-C1 + post-fleet-retire.
- **NOT the gfr telos proof** — gfr `verified_realized` (`.know/telos/gfr.md:79-89`) is the send-origination
  `{guid}@appointments.contenteapp.com` round-trip at a distinct altitude, eunomia's to close. Do NOT round.

## §3 — The operator's realization ladder (merged -> live -> verified_realized; surface-only, operator/eunomia-held)
1. **Lever C1 apply** — flip/provision the dedicated `leads-resolver` SA (Option B, per the G-SEC verdict) +
   **SC-C1-1: assert the orphaned `bypass_scope_enforcement` tuple is DELETED** (the reconciler is
   additive-write-only — deletion must be asserted, not assumed) + **SC-C1-2: F-001 frozenset timing
   fast-follow** (a C1 precondition). Gates fleet-token retirement.
2. **Dedicated leads-resolver SA provisioning** — start early (lead-time); precedes fleet-retire.
3. **Consumer scheduling/activation** — flip the feature flag + schedule the lambda (merging did NOT do this).
4. **UV-P-DBCLEAN** — DATA-VAL-003 live re-probe (zero normalized collisions / office_phone UNIQUE PK) at deploy.
5. **Fleet-token retirement** — the telos's "fleet token GONE" predicate.
6. **eunomia `verified_realized`** — live `insights/leads succeeded>0` + fresh LastSuccessTimestamp +
   zero DATA-VAL-003 in the leads path + fleet token retired; rite-disjoint, at the live altitude.

## §4 — FINDING-1 (LOW, non-blocking — parallel route to 10x-dev/principal-engineer)
`collision_conflict` is the only WS-SKIP class without a consumer-altitude counted-emit test (production
path `leads_consumer.py:223-225` present + correct). Author a consumer-loop test driving 409 ->
`MintCollision` -> counted `skipped_by_class[COLLISION_CONFLICT]` to close the 4/4 EMIT matrix. Did NOT
block the seal or the merge.

## §5 — DEFER watch-register (operator/critic-held; none scope-crept into the merge)
- Lever C1 (SC-C1-1 GR-6 deletion + SC-C1-2 F-001) — operator.
- Dedicated leads-resolver SA provisioning — operator (lead-time).
- UV-P-DBCLEAN (DATA-VAL-003 live re-probe) — operator/eunomia, deploy-time.
- FINDING-1 (collision_conflict consumer test) — 10x-dev/principal-engineer.
- Fleet-token retirement + prod deploy + consumer activation — operator-sovereign.
- gfr `verified_realized` — eunomia, live, distinct altitude, [UNATTESTED — DEFER].

## §6 — Next step
No further rite-specialist dispatch is required for the merge (it's done). The realization ladder (§3) is
the operator's to walk when ready (frame the C1/activation work via `ari sync --rite=…` only if you choose
to orchestrate it). FINDING-1 routes to 10x-dev/principal-engineer in parallel. The grain-bridge build->merge
arc is closed at `merged` + STRONG-sealed.
