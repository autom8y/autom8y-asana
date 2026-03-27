---
name: Sprint 5 instrumentation context
description: Key facts about the Sprint 5 resolution error path instrumentation initiative — gaps, spans, and validation outcome
type: project
---

Sprint 5 instrumented 7 gaps (G-01 through G-07) across resolver.py, universal_strategy.py, and cascade_validator.py. All 5 MUST gaps and both SHOULD gaps were closed. Validation verdict: PASS WITH WARNINGS (3 NOTE-level issues only, no blockers).

**Why:** The instrumentation initiative goal is traceable error paths from resolution failure to actionable diagnostic without log correlation.

**How to apply:** When working on future instrumentation sprints for this service, the three-level span tree (HTTP → resolver.entities.resolve → strategy.resolution.resolve → strategy.resolution.resolve_group) is now the baseline. New spans should fit this hierarchy. The cascade audit attributes attach to the ambient computation.progressive.build span (separate warmup trace), not the request trace.

Key open items for future sprints:
- Silent schema-lookup exception at resolver.py:431-443 (available_fields metadata path, no span signal on miss)
- Un-awaited coroutine RuntimeWarning in test_universal_strategy_spans.py T-G04 null-slot test — test hygiene, route to span-engineer
- Warmup-trace / request-trace cross-correlation requires entity_type + project_gid join — no code change needed, document in runbook
