---
type: spec
status: proposed
---

# FRAME — SIBLING substrate arch sprint (the re-mint-vs-integrate follow-ons)

- Source seam: entity-resolution refoundation MERGED to origin/main `5b5c249a` (PR #214). The
  three items below were DEFER-watch-registered in
  `HANDOFF-arch-to-10xdev-entity-resolution-2026-07-08.md`; their reactivation triggers now fire.
- Read-root (fresh, off the post-merge main): `.knossos/worktrees/wt.arch.sibling-substrate.*`.
- Recommended shape: an arch DAG (map → option lenses → pythia adjudication → TDD+HANDOFF →
  adversary), same as the entity-resolution sprint. Switch to the `arch` rite for the native
  pantheon (incl. arch-adversary), then run.

## The backlog, ranked by leverage (impact ÷ blast-radius-controlled effort)

### SIBLING-1 — TASK cache hit-path projection-coverage check  **[FLAGSHIP]**
- **Defect**: `clients/tasks.py` `get_async` hit path serves the stored entry with NO
  projection-coverage check; `STANDARD_TASK_OPT_FIELDS` excludes `memberships.section.*`
  (`models/business/fields.py:268`), so a cross-reader whose projection ⊄ the stored union is
  silently starved. Receipt: `.ledge/reviews/DEFECT-taskcache-cross-reader-section-starvation-2026-07-08.md`.
- **Reactivation trigger (NOW MET)**: the resolver shipped; its callers are pinned to
  `NullCacheProvider()` purely to dodge this class. Fixing it unblocks unpinning fleet-wide.
- **Fix direction (litigate)**: serve from cache ONLY IF stored keys cover the requested
  projection, else treat as miss and hydrate `union(stored ∪ requested ∪ STANDARD)`. Closes the
  CLASS (any field family, any read order). **Highest leverage, highest blast-radius** (core cache
  infra, fleet-wide) → the DAG must weigh the coverage-check cost and the union-hydration write
  amplification; a 2-sided canary proving the starvation RED-before / coverage GREEN-after.
- **Post-fix follow-through**: unpin `NullCacheProvider()` in the resolver + floodgates callers
  (DEFER ITEM-6), watch the `method='phone'` provenance rate stays 0 on well-parented offices.

### SIBLING-2 — floodgates per-office Pages deploy accumulation
- **Defect**: `host_bundle.stage_deck_bundle` + `floodgates/office_runner.py` stage a per-office
  deploy root; the Pages domain is latest-deployment-only, so a naive per-office `wrangler pages
  deploy` 404s every prior office (incl. live client decks). Worked around this session by a
  hand-assembled combined root.
- **Fix direction**: the runner emits an ACCUMULATING deploy root (all live slugs), or integrates
  the `~/Code/a8t/deck-host` repo's `public/` accumulation model. Medium leverage (scales the batch
  without the manual combine); localized blast-radius.

### ITEM-5 — S2S `intake_resolve.resolve_business` hierarchy-aware overload
- **Defect**: `api/routes/intake_resolve.py:69` is phone-index-only (GidLookupIndex) — the same
  lossy class on the S2S API surface, separate process/store.
- **Fix direction**: additive-only `task_gid` param that delegates to the shipped resolver's
  store-optional path when present. Lowest urgency (no felt bug); a clean follow-up ticket.

## Suggested flagship for the DAG
SIBLING-1 (fleet cache correctness) — it is the load-bearing unblock (lets every caller drop the
`NullCacheProvider` pin) and the highest-risk, so it earns the full arch litigation + adversary gate.
SIBLING-2 and ITEM-5 map alongside and rank as fast-follows.
