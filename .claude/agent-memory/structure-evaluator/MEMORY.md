# Structure Evaluator Memory

## Assessment Patterns
- Always perform the false-positive check BEFORE classifying as anti-pattern. Many patterns that look wrong are intentional trade-offs.
- The autom8y-asana codebase has extensive ADR documentation. Check for ADR references before flagging design decisions.
- Use dependency-map coupling scores and topology classifications as primary evidence. Supplement with targeted code reads for specific lines/logic.
- Risk register leverage scoring: impact / effort. Quick wins are high-leverage, long-term transformations are necessary-but-low-leverage.

## autom8y-asana Cache Subsystem
- Two independent tier systems: Entity Cache (Redis+S3) and DataFrame Cache (Memory+S3). Intentionally divergent per ADR-0067 (12/14 dimensions).
- SaveSession CacheInvalidator does NOT invalidate DataFrameCache (System B). MutationInvalidator DOES for structural mutations. This asymmetry is a key finding.
- LKG_MAX_STALENESS_MULTIPLIER = 0.0 means unlimited staleness (availability-first philosophy).
- `clear_all_tasks()` SCAN pattern `asana:tasks:*` matches ALL entity types except DATAFRAME (which uses `asana:struc:*`).
- Derived timeline cache: 300s fixed TTL, no upstream invalidation.
- Two coalescing systems (DataFrameCacheCoalescer + BuildCoordinator) -- incremental migration per ADR-BC-002.

## File References
- Cache assessment: `.claude/wip/SPIKE-CACHE-ARCH/ASSESSMENT-CACHE.md`
- Cache topology: `.claude/wip/SPIKE-CACHE-ARCH/TOPOLOGY-CACHE.md`
- Cache dependencies: `.claude/wip/SPIKE-CACHE-ARCH/DEPENDENCY-CACHE.md`
