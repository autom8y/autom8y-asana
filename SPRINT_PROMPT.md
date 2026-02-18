# Session 3: Architecture Sprint (U-005, SI-5, U-001)

**Rite**: arch | **Complexity**: MODULE | **Branch**: sprint/arch-u005-si5-u001

Execute 3 items sequentially. Each produces an investigation document, not code changes.

---

## Item 1: U-005 Entry-Point Bootstrap Audit

### Prompt 0 (paste after `/go arch`)

```
## U-005: Entry-Point Bootstrap Audit

### Objective
Audit all entry points for explicit `register_all_models()` bootstrap guards.
3 Lambda handlers lack explicit guards and rely on transitive import side effects.

### Context
`models/business/__init__.py:64-66` calls `register_all_models()` at import time.
Only `cache_warmer.py` has an explicit `_ensure_bootstrap()` guard (lines 55-91).
Three other handlers are unaudited.

### Investigation Targets
For each, trace: does the import chain reach `models.business` before first registry use?

1. `src/autom8_asana/lambda_handlers/cache_warmer.py` — HAS explicit guard (baseline)
2. `src/autom8_asana/lambda_handlers/cache_invalidate.py` — NO explicit guard
3. `src/autom8_asana/lambda_handlers/insights_export.py` — NO explicit guard
4. `src/autom8_asana/lambda_handlers/conversation_audit.py` — NO explicit guard
5. `src/autom8_asana/lambda_handlers/checkpoint.py` — NO explicit guard
6. `src/autom8_asana/lambda_handlers/workflow_handler.py` — NO explicit guard
7. `src/autom8_asana/api/main.py` — API startup (check for explicit side-effect import)
8. `src/autom8_asana/entrypoint.py` — ECS entrypoint (if exists)

Also check:
- `src/autom8_asana/models/business/detection/tier1.py:91-105` — has a defensive guard
- `src/autom8_asana/core/system_context.py` — `reset_all()` calls `reset_bootstrap()`

### Deliverables
1. **Audit document** at `.claude/wip/ENTRY-POINT-AUDIT.md`:
   - Table of all entry points with import chain analysis
   - Risk rating per entry point (covered/gap/medium-risk)
   - Recommendation: add explicit guards where missing

2. **Bootstrap guards** for unguarded entry points (if warranted):
   ```python
   import autom8_asana.models.business  # noqa: F401 - bootstrap side effect
   ```

### Guardrails
- Code changes limited to adding import guards. Do not refactor registration mechanism.
- VERIFY: `git log --oneline -10` to check for recent Lambda handler changes.
```

---

## Item 2: SI-5 Cache System Divergence ADR

### Prompt 0 (paste after U-005 completes)

```
## SI-5: Entity Cache vs DataFrame Cache Divergence ADR

### Objective
Write an ADR determining whether the divergence between entity cache and DataFrame
cache is intentional, convergeable, or accidental.

### Pre-Computed Context
The explore agents identified 14 dimensions of divergence. The cache directory
contains ~15,900 LOC across 35+ files.

Key structural differences:
- Entity cache: `CacheProvider` protocol, Redis+S3, synchronous, TTL-based, per-entity
- DataFrame cache: concrete class (no protocol), Memory+S3 Parquet, async, SWR, per-project

### Key Files to Read
| File | Why | LOC |
|------|-----|-----|
| `protocols/cache.py` | Entity cache interface | 250 |
| `cache/integration/dataframe_cache.py` | DataFrame cache + DataFrameCacheEntry | 987 |
| `cache/models/entry.py` | CacheEntry hierarchy | 579 |
| `cache/integration/mutation_invalidator.py` | Both systems invalidated together | 371 |
| `cache/providers/unified.py` | Highest-level entity cache composition | 923 |
| `cache/dataframe/tiers/memory.py` | MemoryTier LRU + heap-bound | 264 |
| `.claude/wip/q1_arch/ARCH-REVIEW-1-CACHE.md` | Pre-computed cache topology | — |

### 14 Dimensions to Classify
For each: intentional / convergeable / accidental

1. Cache unit (entity dict vs Polars DataFrame)
2. Key space (per-entity vs per-project+type)
3. Interface contract (protocol vs concrete class)
4. Hot tier (Redis vs in-process OrderedDict)
5. Cold tier (S3 JSON vs S3 Parquet)
6. Eviction (TTL vs LRU by heap size)
7. Freshness model (3-mode vs 6-state + SWR)
8. Staleness detection (Batch API call vs watermark comparison)
9. Invalidation granularity (per-entity vs per-project)
10. Schema versioning (none vs SchemaRegistry)
11. Build coordination (none vs CircuitBreaker + Coalescer)
12. Completeness tracking (CompletenessLevel vs absent)
13. Async model (sync protocol vs async methods)
14. Singleton pattern (factory-injected vs module-level singleton)

### Deliverables
ADR at `docs/adr/ADR-011-cache-system-divergence.md` (or follow existing numbering):
- 14-dimension comparison table with verdict per dimension
- Overall assessment: converge / partially converge / accept divergence
- If convergence: which dimensions, what effort
- Recommendation on the "31 cache concepts" concern from the arch review

### Guardrails
- INVESTIGATION AND DOCUMENTATION ONLY. No code changes.
- Reference `.claude/wip/q1_arch/ARCH-REVIEW-1-CACHE.md` first — don't re-derive topology.
- Use spike checkpoints at 25%/50%/75%/100% for this 2-3 day item.
```

---

## Item 3: U-001 Pipeline Parity Analysis

### Prompt 0 (paste after SI-5 completes)

```
## U-001: Pipeline Parity Post-WS6 Analysis

### Objective
Document what remains of the dual-path architecture after WS6 extracted 6 shared
primitives to `core/creation.py`. Determine if D-022 (full consolidation) is still warranted.

### What WS6 Already Converged
`core/creation.py` contains 6 shared primitives imported identically by both pipelines:
- `generate_entity_name`, `discover_template_async`, `duplicate_from_template_async`
- `place_in_section_async`, `compute_due_date`, `wait_for_subtasks_async`

Comment in core/creation.py: "Seeding is intentionally NOT shared -- automation uses
FieldSeeder (explicit field lists), lifecycle uses AutoCascadeSeeder (zero-config matching)."

### What Remains Divergent (from explore agents)
1. **Seeding layer** — intentionally diverged by design. `AutoCascadeSeeder` already
   imports from `FieldSeeder` infrastructure.
2. **Hierarchy placement** — different holder resolution paths (manual walk vs ResolutionContext)
3. **Assignee resolution** — lifecycle is a strict superset (4-step YAML-configurable cascade
   vs 3-step inline cascade)
4. **Blank task fallback** — lifecycle only
5. **Duplicate detection** — lifecycle only
6. **Onboarding comment** — automation only

### Key Files
- `src/autom8_asana/core/creation.py` — shared primitives
- `src/autom8_asana/automation/pipeline.py` — legacy automation path
- `src/autom8_asana/lifecycle/creation.py` — canonical lifecycle path
- `src/autom8_asana/automation/seeding.py` — FieldSeeder
- `src/autom8_asana/lifecycle/seeding.py` — AutoCascadeSeeder

### Deliverables
Analysis document at `.claude/wip/PIPELINE-PARITY-ANALYSIS.md`:
- What WS6 converged (with evidence from core/creation.py)
- What remains divergent (with line references)
- Classification per divergence: essential (different use cases) vs accidental
- Updated effort estimate for D-022
- Recommendation: proceed / descope / close D-022

### Guardrails
- ANALYSIS ONLY. No code changes.
- VERIFY: `git log --oneline --grep="RF-00" -10` to confirm WS6 commits are on main.
- If D-022 is no longer needed because WS6 extracted enough, that is a valid outcome.
```
