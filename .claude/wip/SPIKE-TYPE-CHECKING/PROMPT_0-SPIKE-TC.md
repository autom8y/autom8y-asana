# TYPE_CHECKING Classification Spike

**Type**: Spike (investigation, not implementation)
**Scope**: 233 files with `if TYPE_CHECKING:` blocks in src/autom8_asana/
**Output**: Taxonomy + conditional removal plan
**Rite**: hygiene (code-smeller -> architect-enforcer -> [janitor -> audit-lead])

---

## Problem Statement

233 files contain `if TYPE_CHECKING:` blocks (233 total occurrences, 1 per file).
Industry standard for well-structured projects: 0-10.
Prior work (REM-ASANA-ARCH) broke 6 of 13 bidirectional cycles,
raising health score from 68 to 91. 7 structural cycles remain.

**Question this spike answers**: Of the 233 TYPE_CHECKING blocks,
how many are now unnecessary (guarding cycles that were cut) vs.
structurally necessary (guarding cycles that remain)?

---

## Known Facts (Do Not Re-Discover)

### Cycles Cut (6 total)
1. cache -> api (Cycle 5, Phase 1)
2. automation <-> lifecycle (P2-02)
3. dataframes <-> services (P2-02)
4. cache <-> models (P2-02)
5. core <-> dataframes (P2-02)
6. core <-> models (P2-02)

### Structural Cycles (7, remain, do NOT attempt to fix)
1. clients <-> persistence (23 reverse imports)
2. cache <-> dataframes
3. models <-> dataframes (convenience methods, AP-2)
4. models <-> persistence (convenience methods, AP-2)
5. models <-> core (residual)
6. api <-> auth
7. services <-> core (residual)

### Protocols Already on Main
- EndpointPolicy: clients/data/_policy.py
- InsightsProvider: protocols/insights.py
- MetricsEmitter: protocols/metrics.py
- DataFrameProvider: protocols/dataframe_provider.py

### Utility Extractions Already Done
- core/string_utils.py (to_pascal_case)
- core/registry.py (register_holder)
- core/field_utils.py
- core/types.py

---

## TYPE_CHECKING Taxonomy

Classify each block into one of:

| Category | Code | Meaning | Action |
|----------|------|---------|--------|
| Cycle Guard | A | Protects against a known structural cycle | KEEP |
| Type-Only | B | Purely for type hints, no cycle involved | KEEP (standard practice) |
| Removable | C | Guarded a cycle that was cut | CANDIDATE for removal |
| Defensive | D | No current cycle, cautionary guard | JUDGMENT CALL |

---

## Guardrails

1. Do NOT decompose SaveSession
2. Do NOT re-open cache divergence (ADR-0067)
3. Do NOT pursue full pipeline consolidation (D-022)
4. Do NOT convert deferred imports wholesale (SI-3)
5. Do NOT modify automation/seeding.py field strategy
6. Run tests after every change (green-to-green)
7. Verify file paths before editing
8. Do NOT attempt to fix all 233 blocks
9. Do NOT attempt to eliminate all 13 2-cycles
10. Do NOT recreate existing protocols
11. **This is a SPIKE. Phases 1-2 produce analysis only.
    Phases 3-4 (execution) require explicit user go-ahead.**

---

## Spike Phases

### Phase 1: Code Smeller -- Classify
- Input: This file + codebase scan of 233 `if TYPE_CHECKING:` files
- Output: `.claude/wip/SPIKE-TYPE-CHECKING/SMELL-REPORT.md`
- Scope: READ-ONLY analysis. Classify each block by category.
- Do NOT scan for other smells. Do NOT evaluate architecture.
- Do NOT propose fixes. Produce the taxonomy only.

### Phase 2: Architect Enforcer -- Plan
- Input: SMELL-REPORT.md from Phase 1
- Output: `.claude/wip/SPIKE-TYPE-CHECKING/REFACTORING-PLAN.md`
- Scope: Design removal contracts for Category C blocks.
  Render verdict on Category D blocks (keep/remove).
  Do NOT design new abstractions or protocols.
- End with PROCEED / DEFER / PARTIAL verdict.

### Phase 3: Janitor -- Execute (CONDITIONAL)
- Only after user reviews Phase 2 output and approves
- Input: REFACTORING-PLAN.md
- Scope: Remove approved TYPE_CHECKING blocks only

### Phase 4: Audit Lead -- Verify (CONDITIONAL)
- Only after Phase 3 completes
- Verify no circular import errors introduced
- Verify all tests pass

---

## Prior Art (Load ONLY When Needed)

| Artifact | When to Load |
|----------|-------------|
| .claude/wip/REM-ASANA-ARCH/PHASE2-GAP-ANALYSIS.md | If you need cycle details beyond what is listed above |
| .claude/wip/REM-ASANA-ARCH/DEPENDENCY-GRAPH.md | If you need the full adjacency matrix for a specific cycle |
| .claude/wip/q1_arch/deep-dive/ | If you need anti-pattern evidence for a specific cycle |
| .claude/wip/REM-ASANA-ARCH/SESSION-CONTEXT-ARCHITECTURE.md | Do NOT load (previous initiative infrastructure) |

---

## Classification Heuristics

To classify a TYPE_CHECKING block:

1. Read the imports under `if TYPE_CHECKING:`
2. Identify which package(s) are being imported
3. Check: does this file's package have a known cycle with the imported package?
   - If YES and cycle is in the "Structural Cycles" list -> **Category A**
   - If YES but cycle was in the "Cycles Cut" list -> **Category C** (removable)
4. If NO cycle relationship exists:
   - Is the import used ONLY in type annotations (: Type, -> Type)? -> **Category B**
   - Is the import used in runtime code too (would fail without guard)? -> Investigate further
   - Is this a preventive guard with no current cycle? -> **Category D**

---

## Test Commands

- Import verification: `python -c "import autom8_asana.{module}"`
- Scoped tests: `pytest tests/unit/{module}/ -x`
- Full suite (QA gate only): `AUTOM8Y_ENV=production .venv/bin/python -m pytest tests/ -x`

---

## Closed Decisions (Do NOT Reopen)

- D-022 full pipeline consolidation: CLOSED
- ADR-0067 cache divergence: CLOSED
- SaveSession decomposition: REJECTED
- SI-3 circular deps wholesale fix: DEFERRED
- 7 structural cycles: PERMANENT (require major redesign)
