---
name: omniscience-sprint6-lifecycle-observation
description: Sprint 6 lifecycle observation design artifacts produced for Project Omniscience covering stage transition data model, pipeline metrics, stages 5-10 parity assessment, and webhook dispatcher activation.
type: project
---

Project Omniscience Sprint 6 (2026-03-27) produced three design artifacts as analytics-engineer:

1. **Lifecycle Observation Data Model** (`.ledge/spikes/omniscience-lifecycle-observation-design.md`): StageTransitionRecord generalizing SectionTimeline to all entity types, MetricExpr extensions for median/quantile, pipeline metrics (conversion, duration, stall detection), funnel query patterns via existing /v1/query/aggregate endpoint.

2. **Stages 5-10 Assessment** (`.ledge/spikes/omniscience-stages-5-10-assessment.md`): Per HD-03, classified each stage. Key blockers: `activate_campaign`/`deactivate_campaign` handlers not implemented, self-loop scheduling not implemented in LifecycleEngine, pipeline_stage numbering incorrect for retention(1)/reactivation(2)/expansion(6). Expansion is intentionally-manual. Total parity estimate: ~24 engineering days across 3 sprints.

3. **Webhook Dispatcher Design** (`.ledge/spikes/omniscience-webhook-dispatcher-design.md`): Per GAP-03/R-007, LifecycleWebhookDispatcher replaces NoOpDispatcher with feature-flagged dry-run support. LoopDetector prevents self-triggered webhook loops via time-windowed outbound GID tracking. Four env vars control rollout phases.

**Why:** Sprint 6 is the intelligence rite's contribution to Omniscience, scoping the observation layer that enables pipeline analytics.

**How to apply:** These are DESIGN artifacts for Sprint 8 implementation by a principal-engineer. No production code was written. Key integration points: LifecycleEngine emit hook, MetricExpr agg extension, webhooks.py dispatcher injection.
