# Deferred Work Items

**Updated**: 2026-02-17 (initiative COMPLETE)

## Completed (WS1 S0)
- [x] ~~SM-003: BUSINESS_SCHEMA task_type "business" -> "Business"~~ (commit 03c780e)
- [x] ~~cascade:MRR dtype: Offer mrr/weekly_ad_spend Utf8 -> Decimal~~ (commit 03c780e)
- [x] ~~MRR dedup documentation: Added to ACTIVE_MRR and ACTIVE_AD_SPEND~~ (commit 03c780e)

## WS2 Scope: Cache Reliability (COMPLETE, commit 2977717)
- [x] Cache invalidation & staleness audit — exception audit clean (58/91 typed, 9 BROAD-CATCH, 0 needing narrowing)
- [x] Warm-up reliability hardening — SWR build lock try/finally, warmer observability
- [x] Unified store consistency — cascade per-descendant isolation, hierarchy register reorder

## WS3 Scope: Traversal Consolidation (COMPLETE, commit 9947f71)
- [x] B/C consolidation — DRY extraction to cf_utils.py, source_field wiring in both resolvers
- [x] Cascade promotion — _extract_office_async eliminated, office now cascade:Business Name
- [x] ~~Traversal unification~~ — spike determined "do NOT unify A/B/C"; B/C consolidation is the deliverable
- [x] ~~Entity traversal audit~~ — spike table confirmed no new dedicated extractors needed

## Backlog (P4, not scheduled)
- [ ] Query CLI utility (infrastructure exists, scripts in place)
- [ ] B6: is_completed vs completed naming documentation
