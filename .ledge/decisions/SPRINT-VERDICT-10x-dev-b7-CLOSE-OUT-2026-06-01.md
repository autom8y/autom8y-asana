---
type: decision
altitude: OPERATIONAL
status: accepted
sprint: 10x-dev-b7-close-out
initiative: asyncio-run-in-sync-async-native-migration
date: 2026-06-01
supersedes_handoff_status: HANDOFF-eunomia-to-10x-dev-asyncio-run-in-sync-async-native-migration-2026-06-01.md (flipped in_progress → completed)
related_sprint_verdicts:
  - .ledge/decisions/SPRINT-VERDICT-10x-dev-b7-sprint-1-2026-06-01.md
  - .ledge/decisions/SPRINT-VERDICT-10x-dev-b7-sprint-2-2026-06-01.md
  - .ledge/decisions/SPRINT-VERDICT-10x-dev-b7-sprint-3-2026-06-01.md
  - .ledge/decisions/SPRINT-VERDICT-10x-dev-b7-sprint-4-2026-06-01.md
prs_landed: [79, 80, 81, 82]
---

# B7 CLOSE-OUT VERDICT — asyncio-run-in-sync-async-native-migration

## Summary

Initiative **CLOSED** at 27 of 41 sites migrated (65.9% migration rate; 100% of safely-migrable sites). The remaining 14 sites are decomposed into structurally-non-migratable categories that are now fully cataloged in `.know/test-coverage.md`.

## Final cumulative state

| Sprint | PR | Target file | Sites migrated | Notes |
|--------|----|----|---------------|-------|
| 1 | #79 | tests/unit/lifecycle/test_observation.py | 2 of 2 | Canonical 6-rule pattern established + docs codified |
| 2 | #80 | tests/unit/lifecycle/test_lifecycle_observation_contracts.py | 10 of 10 | Pattern scaled to 5 classes with MED complexity |
| 3 (revised) | #81 | tests/unit/patterns/test_async_method.py | 1 of 12 | Dual-surface anti-pattern discovered + cataloged; sprint-3 HALT on inventory defect was the key learning event |
| 4 | #82 | tests/unit/models/business/test_seeder.py | 14 of 14 | Source-verification doctrine applied per sprint-3 lesson; with-patch lifecycle preserved across 4 nested sites |
| **Close-out** | (this PR) | docs-only | 0 | Catalog finalization + handoff status flip |
| **Cumulative** | **5 PRs** | **4 source files migrated + 1 docs-only** | **27 of 41** | **100% of safely-migrable** |

## Non-migratable site catalog (14 sites)

### Intentional pins (4 sites) — exercise specific guard behavior

- `tests/unit/dataframes/test_freshness_verification_recency.py:736-760` — sync-context guard semantic test
- `tests/unit/patterns/test_async_method.py:92` (`test_sync_in_async_context_raises`) — deliberately invokes sync API inside running loop to trigger `SyncInAsyncContextError`
- `tests/unit/dataframes/test_public_api.py:278` — docstring reference only
- `tests/unit/models/business/test_resolution.py:777,780-782,786` — docstring + comment text describing sync-wrapper behavior

### Dual-surface anti-pattern (10 sites in tests/unit/patterns/test_async_method.py)

10 test methods exercise BOTH the sync wrapper AND the async variant in the same body. Per the dual-surface anti-pattern documented at `.know/test-coverage.md:150-166`, migrating these would invert their semantic intent because the post-migration body would be inside a running loop, triggering the production `SyncInAsyncContextError` guard.

Sites: `test_with_kwargs:141`, `test_with_multiple_args:159`, `test_void_return:180`, `test_exception_propagation:203`, `test_stacked_with_mock_error_handler:272`, `test_client_pattern_simulation:346,355,360`, `test_inheritance_works:383,387`.

Resolution options (out-of-scope for B7; tracked for future):
- (a) Split into two test methods: one `async def` exercising only async variant, one `def` exercising only sync wrapper
- (b) Keep dual-surface tests as-is (the `asyncio.run` IS the legitimate entry point when intentional)
- (c) Architectural review of whether dual-surface tests are the right shape

Currently honored: **(b) — keep as-is**, cataloged as DO-NOT-MIGRATE.

## Throughline coherence

**"no shortcuts, robust resolve"**: B7 honored this end-to-end. Critical inflection points:

1. **Sprint-3 HALT** (PR #81 revised): When the original inventory's "11 of 12 migrate" claim was falsified by direct source inspection, the principal-engineer + qa-adversary chain refused to proceed. The HALT was correct discipline — not a workflow failure but a successful default-to-refuted invocation. The architect then re-classified per source, landing 1 of 12 + the anti-pattern catalog that prevented repeating the mistake in sprint-4.
2. **Sprint-4 source-verify doctrine**: Codified the sprint-3 lesson — Pythia phase REQUIRES per-site source reading, NOT inventory-trust. Sprint-4's Pythia produced an SVR-grade per-site verdict table that confirmed 14/14 SAFE-MIGRATE, with zero dual-surface risk because the seeder API doesn't expose sync wrappers at all (structural impossibility).
3. **PR #80's bonus xdist quarantine fix**: When sprint-2's first CI run failed on `test_null_slot_increments_count_and_adds_event` (same xdist-flake family as PR #77's H-1), the principal-engineer extended the quarantine pattern to close the audit gap rather than rerun-until-green. This trace inspired the parallel work that became PR #83's root-cause fix (module identity divergence from sys.modules manipulation).

**"adversarially /qa validated"**: Every sprint's qa-adversary returned PASS-ADVERSARIAL with cross-stream concurrence ≥ 2 (often ≥ 5-8 streams). Sprint-3's HALT itself was PASS-ADVERSARIAL on the halt decision (the implementation correctly refused).

**"push to ecosystem"**: 27 sites migrated + 14 cataloged = 41 sites fully understood. Migration coverage equals 100% of what's structurally migratable.

## Cross-rite handoff status flip

`HANDOFF-eunomia-to-10x-dev-asyncio-run-in-sync-async-native-migration-2026-06-01.md`:
- Sprint-1 → completed (PR #79)
- Sprint-2 → completed (PR #80)
- Sprint-3 → completed (PR #81 revised after HALT)
- Sprint-4 → completed (PR #82)
- Initiative: **completed** (this close-out)

## Operator close-out actions

1. Review + merge this close-out PR (docs-only, single commit) via bootstrap exception
2. Optionally: schedule a follow-up sprint to evaluate whether the xdist `worker_isolated` quarantines on `test_universal_strategy_spans.py` can be REMOVED now that PR #83 root-fixed the underlying module-identity divergence flake. Memory: `universal-strategy-sysmodules-parent-attr-flake.md`.
3. The other 3 pending handoffs from eunomia (B4 branch-protection, B5 trivy cadence, B9 consumer-gate) were already resolved earlier in this arc — see `SPRINT-VERDICT-10x-dev-pending-handoffs-2026-06-01.md`.

**B7 initiative: CLOSED.**
