---
name: omniscience-sprint8-lifecycle-observation
description: ADR for lifecycle observation architecture -- StageTransitionRecord persistence, MetricExpr median/quantile extension, GAP-03 webhook dispatcher activation with 4-layer feature flag
type: project
---

Sprint 8 lifecycle observation ADR produced at `.ledge/decisions/ADR-omniscience-lifecycle-observation.md` on 2026-03-27.

**Why:** Sprint 6 intelligence rite designed three specs (observation data model, pipeline metrics, webhook dispatcher). Sprint 8 translates these into an implementation-ready architecture decision covering all three workstreams as a single ADR because they are mutually dependent.

**How to apply:** The ADR covers 4 decisions:
1. StageTransitionRecord data model + parquet persistence following TimelineStore pattern
2. 7 MetricExpr registrations + SUPPORTED_AGGS extension for median/quantile
3. LifecycleWebhookDispatcher replacing NoOpDispatcher at GAP-03 seam, feature-flagged with 4-layer config + LoopDetector
4. Implementation plan: 13 new files, 8 modified files, ~940 LOC production + ~520 LOC tests

Key architectural decisions:
- EntityStageTimeline is PARALLEL to SectionTimeline, not a replacement (different data sources)
- EntityCategory.OBSERVATION is the first non-Asana-backed entity type in EntityDescriptor
- Conversion rates are caller-level composition (not embedded in MetricExpr) to preserve the "one scalar agg" invariant
- LoopDetector in-memory dict is acceptable for MVP (30s TTL window < restart duration)
- Webhook dispatcher defaults are maximally conservative (disabled, dry-run, empty allowlists)
