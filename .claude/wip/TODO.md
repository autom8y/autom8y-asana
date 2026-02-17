# Deferred Work Items

**Updated**: 2026-02-17 (post WS1 merge)

## Completed (WS1 S0)
- [x] ~~SM-003: BUSINESS_SCHEMA task_type "business" -> "Business"~~ (commit 03c780e)
- [x] ~~cascade:MRR dtype: Offer mrr/weekly_ad_spend Utf8 -> Decimal~~ (commit 03c780e)
- [x] ~~MRR dedup documentation: Added to ACTIVE_MRR and ACTIVE_AD_SPEND~~ (commit 03c780e)

## WS2 Scope: Cache Reliability
- [ ] Cache invalidation & staleness audit
- [ ] Warm-up reliability hardening
- [ ] Unified store consistency

## WS3 Scope: Traversal Consolidation
- [ ] B/C consolidation: CascadeViewPlugin as primary, CascadingFieldResolver as fallback
- [ ] Cascade promotion (deferred S3.5): eliminate UnitExtractor._extract_office_async duplication
- [ ] Traversal unification: generalized parent-chain walker within DataFrame layer
- [ ] Audit entity traversal needs (Business, AssetEdit, AssetEditHolder)

## Backlog (P4, not scheduled)
- [ ] Query CLI utility (infrastructure exists, scripts in place)
- [ ] B6: is_completed vs completed naming documentation
