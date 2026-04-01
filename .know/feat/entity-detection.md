---
domain: feat/entity-detection
generated_at: "2026-04-01T15:30:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/models/business/detection/**/*.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.91
format_version: "1.0"
---

# Multi-Tier Entity Type Detection

## Purpose and Design Rationale

The detection subsystem answers: given an Asana task, what business entity type does it represent? This is the prerequisite for all downstream behavior -- hydration, holder identification, cache TTL selection, write routing, and DataFrame extraction all depend on knowing the entity type.

Asana tasks do not carry a native "entity type" field. The codebase infers type from extrinsic signals -- which project a task belongs to, what its name contains, who its parent is, and (as last resort) what subtask structure it has. Because signals vary in reliability and cost, the system chains them into a priority-ordered tier hierarchy. Earlier tiers are cheap and authoritative; later tiers are expensive and probabilistic.

## Conceptual Model

### The Tier Chain

```
Tier 1 (sync): Project membership lookup -- O(1), no API, confidence=1.0
    |
Tier 2 (sync): Name pattern matching -- word-boundary regex, confidence=0.6
    |
Tier 3 (sync): Parent type inference -- PARENT_CHILD_MAP lookup, confidence=0.8
    |
Tier 4 (async): Subtask structure inspection -- API call, confidence=0.9
    |
Tier 5: UNKNOWN fallback -- confidence=0.0, needs_healing=True
```

The sync path (`detect_entity_type`) covers Tiers 1-3 only. The async path adds Tier 4 when `allow_structure_inspection=True`.

### DetectionResult Contract

Every tier produces a `DetectionResult` (frozen dataclass): `entity_type`, `confidence`, `tier_used`, `needs_healing`, `expected_project_gid`. Tier 1 sets `needs_healing=False`; all other tiers set `True`.

### Cache Layer (Tier 4 only)

Per `PRD-CACHE-PERF-DETECTION`, Tier 4 results are cached using `CacheEntry` with `EntryType.DETECTION`. UNKNOWN results are never cached.

## Implementation Map

| File | Role |
|------|------|
| `src/autom8_asana/models/business/detection/types.py` | `DetectionResult`, `EntityTypeInfo`, `CONFIDENCE_TIER_*` |
| `src/autom8_asana/models/business/detection/config.py` | `ENTITY_TYPE_INFO`, `NAME_PATTERNS`, `PARENT_CHILD_MAP` |
| `src/autom8_asana/models/business/detection/tier1.py` | Project membership (sync + async with lazy workspace discovery) |
| `src/autom8_asana/models/business/detection/tier2.py` | Name pattern (word-boundary regex, LRU-cached) |
| `src/autom8_asana/models/business/detection/tier3.py` | Parent inference (PARENT_CHILD_MAP lookup) |
| `src/autom8_asana/models/business/detection/tier4.py` | Structure inspection (async, API subtask fetch) |
| `src/autom8_asana/models/business/detection/facade.py` | Orchestration: `detect_entity_type()`, `detect_entity_type_async()`, `identify_holder_type()` |

**Test coverage**: 104 tests across unit (50), cache (26), and integration (28) files.

### Runbook Alignment Gap

The runbook at `docs/runbooks/RUNBOOK-detection-troubleshooting.md` describes an older architecture (references `EntityDetector` class, `Tier 0: Custom Field` that doesn't exist). It cannot be used for current-state troubleshooting without revision.

## Boundaries and Failure Modes

**Inbound consumers**: `Business._identify_holder`, `Unit._identify_holder`, hydration dispatch, cache builders/TTL selection.

**Outbound dependencies**: `core.entity_registry` (Tier 1 static lookup), `models.business.registry` (Tier 1 async workspace discovery), `models.business.patterns` (Tier 2 patterns), `client.tasks.subtasks_async()` (Tier 4).

**Key scars**: SCAR-001 (entity collision via name normalization -- motivates Tier 1 primacy), SCAR-009 (sync-in-async context).

## Knowledge Gaps

1. **`WorkspaceProjectRegistry` internals**: Async Tier 1 discovery mechanism not traced.
2. **Tier 2 priority ordering rationale**: `get_pattern_priority()` ordering not captured.
3. **Runbook accuracy**: Describes older architecture, needs revision.
4. **Batch detection**: No batch function exists; bulk scenarios call single-task functions in a loop.
