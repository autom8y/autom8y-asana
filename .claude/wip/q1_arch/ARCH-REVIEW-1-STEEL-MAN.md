# Architectural Review 1: Steel-Man (Architecture Defense)

**Date**: 2026-02-18
**Scope**: Strongest possible defense of the autom8y-asana architecture
**Methodology**: Steel-man analysis -- interpreting every design decision in its most favorable light, evaluating whether complexity is proportionate to the problem
**Review ID**: ARCH-REVIEW-1

---

## 1. The Descriptor System (ADR-0081, ADR-0082)

### What It Does

The descriptor system replaces ~800 lines of duplicated `@property` implementations across entity classes with declarative patterns:

```python
# Before: ~800 lines of this across all entities
@property
def business(self) -> Business | None:
    if self._business is not None:
        return self._business
    if self._contact_holder is not None:
        return self._contact_holder.business
    return None

# After: 1 line per relationship
business = ParentRef[Business](holder_attr="_contact_holder")
```

**Source**: `src/autom8_asana/models/business/descriptors.py`

### Why This Is Good

1. **Elimination of boilerplate**: ~800 lines of near-identical property implementations compressed to ~50 lines of descriptor declarations. This is not just DRY -- it eliminates an entire class of copy-paste bugs.

2. **Abbreviation preservation**: The descriptor system handles the Asana API's inconsistent custom field naming. `TextField()`, `NumberField()`, `EnumField()` etc. abstract over Asana's varying field representation formats. The auto-generated `Fields` class handles the abbreviation-to-GID mapping.

3. **Two-phase registration (ADR-0082)**: The `__set_name__` + `__init_subclass__` pattern is the correct Python mechanism for metaclass-level registration without metaclass inheritance conflicts. Pydantic v2's metaclass (`ModelMetaclass`) makes custom metaclasses impossible; `__init_subclass__` is the sanctioned workaround.

4. **IDE type hints via `@overload`**: Despite descriptors being declared without type annotations (required by Pydantic v2 to avoid field creation), the `@overload` pattern on `__get__` provides full IDE autocompletion and type checking.

5. **Auto-invalidation (ADR-0076)**: `ParentRef` descriptors auto-invalidate computed caches when parent references change. This would be impossible to maintain consistently across 800 lines of manual property code.

### Proportionality Verdict

The descriptor system addresses genuine complexity: 17 entity types with 3 descriptor families, each entity having 3-8 navigation properties and 5-15 custom field accessors. The ~400 lines of descriptor infrastructure is proportionate to the ~800 lines it eliminates, and the consistency guarantee is worth the abstraction cost.

---

## 2. Five-Tier Entity Detection

### What It Does

Entity type detection uses 5 tiers with calibrated confidence levels:

| Tier | Method | Confidence | Rationale |
|------|--------|-----------|-----------|
| 1 | Project membership | 1.0 | Deterministic: task in known project = known type |
| 2 | Name patterns | 0.6 | Unreliable: regex on task names |
| 3 | Parent inference | 0.8 | Reliable: if parent is X_HOLDER, child is X |
| 4 | Structure inspection | 0.9 | Structural: subtask patterns, custom fields |
| 5 | Unknown fallback | 0.0 | Default: cannot determine |

**Source**: `src/autom8_asana/models/business/detection/` (tier1.py through tier4.py)

### Why This Is Good

1. **Proportionate to genuine domain ambiguity**: Asana tasks have no "entity_type" field. A task in Asana is just a task -- the system must infer whether it represents a Business, Unit, Contact, Offer, Process, Location, etc. This is genuinely ambiguous, and 5 tiers is proportionate to 5 levels of certainty.

2. **Calibrated confidence scores**: The confidence values are not arbitrary. Tier 1 (project membership) is truly deterministic. Tier 2 (name patterns) is empirically unreliable (users rename tasks). Tier 3 (parent inference) is highly reliable but indirect. Tier 4 (structure inspection) examines actual data shape. The 1.0/0.6/0.8/0.9/0.0 graduation reflects real-world accuracy.

3. **DetectionResult provenance**: Each detection carries its tier, confidence, and healing information. Downstream consumers can make informed decisions about trust level. A process entity detected at Tier 1 (1.0 confidence) is treated differently from one detected at Tier 2 (0.6).

4. **Healing integration**: When Tier 3 or 4 detects an entity that should be in a project but is not, `needs_healing=True` + `expected_project_gid` enables automated repair. Detection is not just classification -- it is a self-healing mechanism.

5. **Clean decomposition**: Each tier is a separate file with a single responsibility. Tiers are composable and independently testable. New detection strategies can be added as new tiers without modifying existing ones.

### Proportionality Verdict

Five tiers for seventeen entity types across four ambiguity levels is well-calibrated. The alternative (a single detection function with 17-way branching) would be unmaintainable. The tier architecture makes the confidence model explicit rather than implicit.

---

## 3. Caching Philosophy: Operational Resilience

### What It Does

The caching subsystem prioritizes operational resilience over data freshness:

- **4:2 servable-to-reject ratio**: Of 6 freshness states, 4 result in serving data (possibly stale), only 2 result in rejection (EXPIRED, ERROR)
- **Per-project circuit breakers**: S3 failures for one project do not cascade to others
- **Container-aware memory sizing**: Memory cache auto-sizes to ECS container limits
- **Stale-while-revalidate (SWR)**: Serves stale data while refreshing in background
- **Graceful degradation**: S3 down -> Redis only; Redis down -> API direct; API down -> stale cache

### Why This Is Good

1. **Asana API rate limiting is the binding constraint**: Asana's API has strict rate limits (150 requests/minute per personal access token). Without aggressive caching, the system would be perpetually rate-limited. The caching complexity is directly proportionate to this external constraint.

2. **4:2 servable ratio is operationally correct**: For an internal business tool, serving slightly stale data is strictly better than showing an error page. A contact's phone number from 15 minutes ago is still useful; no contact data at all is not.

3. **Per-project circuit breakers prevent cascading failures**: If S3 access fails for one project (e.g., due to key rotation issues), other projects continue operating normally. This isolation is a genuine operational resilience pattern, not over-engineering.

4. **Container-aware sizing is operationally necessary**: ECS containers have memory limits. An unconstrained LRU cache would OOM-kill the container. Detecting the container's memory limit and sizing the cache to a percentage of it is the correct approach.

5. **Write-through to S3 provides cold-start resilience**: When an ECS task restarts or a new Lambda container cold-starts, the S3 cold tier provides pre-warmed data. Without this, every cold start would require a full Asana API refresh, which could take minutes and hit rate limits.

### Proportionality Verdict

~14.1% of the codebase dedicated to caching is high but justified by the external constraint (Asana API rate limits) and the operational requirement (sub-second response times for a business-critical tool). The complexity is concentrated, not diffused.

---

## 4. `extra="ignore"` Forward Compatibility

### What It Does

Pydantic v2 models use `extra="ignore"` to silently discard unknown fields from Asana API responses.

### Why This Is Good

1. **Third-party API SDKs must handle schema evolution**: Asana adds new fields to their API responses without notice. A Pydantic model with `extra="forbid"` would raise `ValidationError` on any new field, causing production outages on Asana API changes the SDK does not control.

2. **`extra="ignore"` is the correct setting for API consumers**: The SDK consumes Asana's API; it does not define it. Unknown fields should be silently ignored because they represent Asana's forward evolution, not data corruption.

3. **Preferable to `extra="allow"`**: `extra="allow"` would also accept unknown fields but would store them on the model, increasing memory usage and potentially causing serialization issues. `extra="ignore"` is the minimal, correct response.

### Proportionality Verdict

Exactly right. This is the standard pattern for third-party API SDK models and requires no justification beyond "this is how it is done."

---

## 5. SaveSession Unit of Work

### What It Does

**Source**: `src/autom8_asana/persistence/session.py` (1,853 lines, 58 methods)

`SaveSession` implements a phase-based Unit of Work:

1. **ensure_holders**: Create/verify holder entities for new children
2. **CRUD**: Execute create/update/delete operations
3. **cascades**: Execute cascade operations (e.g., moving unit moves all children)
4. **healing**: Repair detected inconsistencies (project membership)
5. **automation**: Fire automation rules (pipeline transitions)
6. **finalize**: Cache invalidation, event emission

### Why This Is Good

1. **Phase ordering prevents data inconsistencies**: Holders must exist before children can be created. CRUD must complete before cascades can execute. Automation must fire after persistence is confirmed. The 6-phase ordering is not arbitrary -- it reflects genuine data dependency ordering.

2. **LIS-optimized reordering**: SaveSession uses a longest-increasing-subsequence (LIS) algorithm to minimize Asana API calls when reordering subtasks. This is algorithmically sophisticated and directly reduces API call count.

3. **Automation isolation**: Automation rules fire in Phase 5, after all persistence operations complete. This prevents automation from seeing intermediate states (e.g., a unit without its holder).

4. **Delegation to collaborators**: Despite 58 methods, SaveSession delegates well:
   - `ChangeTracker` for dirty detection
   - `DependencyGraph` for ordering
   - `EventSystem` for hooks
   - `SavePipeline` for execution
   - `ActionExecutor` for CRUD
   - `HealingManager` for repairs
   - `CascadeExecutor` for cascades
   - `CacheInvalidator` for invalidation

5. **Transactional semantics for a non-transactional API**: Asana's REST API has no transaction support. SaveSession provides the closest approximation: ordered operations with rollback awareness and cache consistency.

### Proportionality Verdict

1,853 lines is large but the class orchestrates 8 collaborators across 6 phases with transactional semantics over a non-transactional API. The complexity is genuinely necessary. The alternative (scattered, uncoordinated API calls) would produce data inconsistencies.

---

## 6. Dual-Mode Deployment

### What It Does

A single Docker image serves both ECS (long-running API server) and Lambda (event-driven handlers), dispatched by environment variable.

### Why This Is Good

1. **Single image, single test suite**: One Docker image means all code paths are tested together. There is no "Lambda version" and "ECS version" that can drift.

2. **Env-driven dispatch**: `EXECUTION_MODE=api` starts FastAPI; `EXECUTION_MODE=lambda` starts Lambda handler. The dispatch logic in `entrypoint.py` is minimal.

3. **Lazy loading**: Lambda-only modules (cache warming, hierarchy warming) are not imported in ECS mode, and vice versa. The `__getattr__` lazy import pattern in `automation/__init__.py` prevents loading the entire automation subsystem until it is needed.

4. **Shared cache configuration**: Both ECS and Lambda use the same Redis/S3 cache configuration. Cache entries written by the ECS API server are immediately readable by Lambda warmers, and vice versa.

5. **Cost optimization**: Lambda for periodic cache warming (pay per invocation) + ECS for always-on API serving is the standard cost-optimized deployment pattern for this type of workload.

### Proportionality Verdict

Straightforward and well-executed. Dual-mode deployment from a single image is industry best practice.

---

## 7. HolderFactory Pattern

### What It Does

**Source**: `src/autom8_asana/models/business/holder_factory.py`

9 holder classes reduced from ~70 lines each to 3-5 lines via `__init_subclass__`:

```python
class DNAHolder(HolderFactory, child_type="DNA", parent_ref="_dna_holder"):
    '''Holder for DNA children.'''
    pass
```

### Why This Is Good

1. **630 -> 45 lines**: 9 holders x 70 lines = 630 lines of boilerplate compressed to 9 x 5 = 45 lines. This is a 14x reduction.

2. **`__init_subclass__` is the correct mechanism**: Holders share identical behavior (child management, parent reference, serialization). The only variation is child type and parent attribute name. `__init_subclass__` captures this variation declaratively.

3. **Consistent behavior guarantee**: All 9 holders are guaranteed to behave identically because they share the same base class implementation. Manual implementations could drift.

4. **Testable at the factory level**: One test suite for `HolderFactory` validates all 9 holders. Manual implementations would require 9 separate test suites.

### Proportionality Verdict

Elegant and effective. The pattern is simple, the reduction is dramatic, and the consistency guarantee is valuable.

---

## 8. Query Engine: Algebraic Predicate AST

### What It Does

**Source**: `src/autom8_asana/query/` (1,935 LOC)

A composable predicate AST with explicit operator/dtype compatibility matrix:

```python
# AST
PredicateNode = Comparison | AndGroup | OrGroup | NotGroup

# Compiler
PredicateCompiler: AST -> pl.Expr

# Compatibility
OPERATOR_MATRIX: dict[Op, set[pl.DataType]]

# Guards
QueryLimits: depth, row count, aggregate groups
```

### Why This Is Good

1. **Algebraic AST is composable**: `And(Or(A, B), Not(C))` is naturally representable. A flat filter API would require flattening nested logic, losing expressiveness.

2. **Stateless compiler**: `PredicateCompiler` takes schema per-call, enabling one compiler instance to serve all entity types. No state accumulation, no cleanup, no concurrency issues.

3. **Explicit compatibility matrix**: `OPERATOR_MATRIX` declares which operators work on which dtypes. `starts_with` on a number column is a compile-time error, not a runtime surprise. This is a correctness guarantee that a stringly-typed API cannot provide.

4. **Guards as first-class concepts**: `QueryLimits` with `predicate_depth`, max row count, and aggregate group limits are not afterthought validations -- they are part of the query engine's type system. A query that exceeds limits is rejected before execution, not after scanning millions of rows.

5. **Cross-entity joins with explicit depth limit**: `MAX_JOIN_DEPTH=1` is an intentional design choice that prevents explosive join complexity while still enabling the most common use case (e.g., task -> unit joins). The depth limit is a tunable parameter, not a permanent restriction.

6. **Section scoping**: Queries are naturally scoped to sections, matching the domain model (entities live in project sections). Section predicates are stripped from the main predicate tree and applied as a separate filter, enabling efficient section-first query planning.

### Proportionality Verdict

1,935 lines for a query engine with AST, compiler, guards, joins, and aggregation is lean. The architecture is well-decomposed (8 modules, each < 300 lines) and the design choices (explicit matrix, stateless compiler, depth limits) reflect mature engineering.

---

## 9. Summary: Where Complexity Is Earned

| Design Decision | Complexity Cost | Problem Addressed | Verdict |
|----------------|----------------|-------------------|---------|
| Descriptor system | ~400 lines | 800+ lines boilerplate, consistency | **Earned** |
| 5-tier detection | ~600 lines | 17 types, 4 ambiguity levels | **Earned** |
| Tiered caching | ~15,658 lines | API rate limits, cold starts, resilience | **Earned** (at the edge) |
| SaveSession UoW | 1,853 lines | Non-transactional API, 6 phases | **Earned** |
| HolderFactory | ~200 lines | 9 x 70 = 630 lines boilerplate | **Earned** |
| Query engine | 1,935 lines | Composable queries, type safety | **Earned** |
| Dual-mode deploy | ~100 lines | Cost optimization, single image | **Earned** |
| `extra="ignore"` | 0 lines (config) | Third-party API evolution | **Earned** |

The overall pattern: complexity is concentrated in subsystems that address genuine external constraints (Asana API limitations, entity ambiguity, non-transactional persistence). The architecture consistently chooses provably correct patterns (`__init_subclass__`, protocol-based DI, algebraic AST) over ad-hoc solutions.
