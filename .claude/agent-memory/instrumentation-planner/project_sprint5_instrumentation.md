---
name: sprint5-instrumentation-plan
description: Sprint 5 resolution error path instrumentation plan — 7 gaps across resolver.py, universal_strategy.py, cascade_validator.py
type: project
---

Plan written to `.ledge/spikes/sprint5-instrumentation-plan.md` covering 7 gaps (G-01 through G-07) from gap report at `.ledge/reviews/sprint5-instrumentation-gap-report.md`.

Key decisions:

1. `trace_computation` is NOT used for any of the 7 gaps. The decorator prefixes all span names with `computation.` (hardcoded in `computation.py` line 126). Resolver and strategy spans must be in `resolver.*` and `strategy.*` namespaces — raw `tracer.start_as_current_span()` is the correct mechanism for new spans.

2. Three new spans: `resolver.entities.resolve` (G-01), `strategy.resolution.resolve` (G-04), `strategy.resolution.resolve_group` (G-05). Each uses a context manager with a module-level `_tracer = get_tracer(__name__)`.

3. G-02, G-03, G-07 are attribute writes on the existing `resolver.entities.resolve` span — no new spans.

4. G-06 writes to the ambient `computation.progressive.build` span via `trace.get_current_span()` — no new span, as specified by the design constraint.

5. Index-build failures (G-05) use `span.set_status(ERROR)` because the entire group fails. Per-criterion lookup failures use `span.add_event()` only (not span-level ERROR) because sibling criteria may succeed.

6. Null-slot hits (G-04) use `span.add_event()` only — not span-level ERROR — because multiple criteria can be null-slot while others succeed.

**Why:** Sprint 5 instrumentation initiative to make the resolution error path observable in distributed traces (not just logs). The 5 MUST gaps represent operationally invisible failure modes.

**How to apply:** If asked to plan additional gaps in these files, check that the module-level `_tracer` was already added by the span-engineer before assuming it needs to be added again.
