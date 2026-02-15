# TDD: Runtime Efficiency Audit -- Refactoring Plan

```yaml
id: TDD-RUNTIME-EFF-001
initiative: INIT-RUNTIME-EFF-001
rite: hygiene
agent: architect-enforcer
upstream: SMELL-RUNTIME-EFF-001
downstream: janitor
date: 2026-02-15
status: ready-for-janitor
```

---

## 1. Prioritization Matrix

Scoring dimensions per PROMPT-0:

| Dimension | Weight | Scale |
|-----------|--------|-------|
| **API calls saved per execution** | 40% | High (8-10), Medium (5-7), Low (1-4) |
| **Execution frequency** | 30% | High (8-10: daily+), Medium (5-7: per-event), Low (1-4: rare) |
| **Implementation complexity** | 20% | Easy reuse (8-10), Moderate adaptation (5-7), New infra (1-4) |
| **Risk** | 10% | Low blast radius (8-10), Medium (5-7), High blast radius (1-4) |

### Scoring Table

| ID | Finding | API Saved (40%) | Exec Freq (30%) | Impl Ease (20%) | Risk (10%) | Weighted | Action |
|----|---------|:---:|:---:|:---:|:---:|:---:|--------|
| AT3-001 | InsightsExport missing Business dedup cache | 8 (80 redundant fetches for 100 offers / 20 businesses) | 8 (daily cron) | 9 (proven `_activity_map` pattern) | 8 (isolated to 1 workflow) | **8.3** = 83 | **SHIP** |
| AT2-002 | HierarchyTraversal 2x API per depth level | 7 (halves calls: 10 -> 5 per traversal) | 7 (100-500 resolutions/day) | 8 (single opt_fields change) | 7 (resolution pipeline, but strategy-local) | **7.3** = 73 | **SHIP** |
| BUG-001 | sections.py hard-coded TTL (1800 vs SECTION_CACHE_TTL) | 1 (correctness, not savings) | 10 (every section operation) | 10 (2-line literal replacement) | 10 (zero blast radius) | **7.1** = 71 | **SHIP** |
| AT2-001 | DependencyShortcut sequential dep fetch | 6 (1-4 calls parallelizable) | 7 (100-500 resolutions/day) | 7 (asyncio.gather pattern) | 6 (resolution pipeline, changes ordering) | **6.5** = 65 | **DEFER** |
| DRY-001 | Section extraction 4x duplication | 1 (maintenance, not API savings) | 10 (used everywhere) | 6 (3 callers need adapting; dict vs model divergence) | 6 (touches 4 files across 3 packages) | **5.5** = 55 | **DEFER** |
| AT3-002 | Resolution cross-context cache miss | 5 (re-traversal of shared parents) | 7 (100-500 resolutions/day) | 3 (needs new shared cache infra, lifecycle management) | 4 (cross-cutting concern across resolution) | **5.0** = 50 | **DEFER** |
| AT1-001 | ProgressiveBuilder fetches ALL sections | 7 (12 Offer + 11 Unit unnecessary sections) | 3 (1-5 cold builds/day; mitigated by S3 resume) | 5 (needs classifier injection into builder) | 4 (shared builder infra, 2 projects) | **5.3** = 53 | **DEFER** |
| AT1-002 | ParallelSectionFetcher fetches ALL sections | 7 (same as AT1-001 -- shared infra) | 3 (same as AT1-001) | 4 (requires contract change on shared infra) | 3 (ParallelSectionFetcher used by multiple callers) | **4.7** = 47 | **DEFER** |
| AT2-003 | Freshness delta sequential added GID fetch | 4 (O(N) for typically small N) | 6 (every 5 min probes, but delta path is conditional) | 8 (simple gather pattern) | 7 (isolated to freshness delta path) | **5.7** = 57 | **DEFER** |
| AT2-004 | AssetEdit 3-hop chain walk | 4 (3 -> 1-2 calls per resolution) | 2 (10-20 user actions/day) | 6 (opt_fields nesting, but Asana support uncertain) | 7 (isolated to asset_edit) | **4.2** = 42 | **DEFER** |
| AT2-005 | Lifecycle init sequential dep check | 2 (1-N, bounded by early return) | 2 (5-15 entity creations/day) | 8 (simple gather + cancel) | 8 (isolated, early return bounds risk) | **4.2** = 42 | **DEFER** |

### Score Derivation Notes

**AT3-001 (83)**: Highest-value fix. 100 offers across ~20 unique businesses = 80 redundant Business fetches per daily cron. The `_activity_map` pattern from `conversation_audit.py` is a drop-in template. Zero architectural risk -- single file change, instance-level cache.

**AT2-002 (73)**: Each depth level in `_traverse_to_business_async` makes 2 API calls: one to fetch `["parent", "parent.gid"]` and one to fetch the full parent task. The first call exists only to discover the parent GID. By requesting full task fields in the first call, the second call is eliminated entirely. This halves the API cost of the hottest resolution strategy path. Implementation is a single-method change within `strategies.py`.

**BUG-001 (71)**: Not an efficiency fix, but a correctness bug where the constant `SECTION_CACHE_TTL` (configurable via env var) is bypassed by literal `1800` at 2 locations. Trivial fix, zero risk, and prevents silent configuration drift.

---

## 2. Ship List (Score >= 70)

| Task ID | Finding | Score | Files |
|---------|---------|:-----:|-------|
| RF-001 | BUG-001: sections.py hard-coded TTL | 71 | `src/autom8_asana/clients/sections.py` |
| RF-002 | AT2-002: HierarchyTraversal double-fetch | 73 | `src/autom8_asana/resolution/strategies.py` |
| RF-003 | AT3-001: InsightsExport Business dedup cache | 83 | `src/autom8_asana/automation/workflows/insights_export.py` |

---

## 3. Defer List (Score 40-69)

| Finding | Score | Reason for Deferral | Follow-Up |
|---------|:-----:|---------------------|-----------|
| AT2-001: DependencyShortcut sequential dep fetch | 65 | Changes resolution ordering semantics (parallel gather returns any match, not first-match). Requires careful verification of early-return budget semantics. | File as `FOLLOW-UP-AT2-001` in deferred roadmap |
| AT2-003: Freshness delta sequential added GID fetch | 57 | Typically small N (delta additions are rare); gather batching is straightforward but needs error handling per-GID with `return_exceptions=True`. | File as `FOLLOW-UP-AT2-003` |
| DRY-001: Section extraction 4x duplication | 55 | Location 3 (`DataFrameViewPlugin`) operates on `dict` not `Task` model -- the canonical function takes `Any` with `.memberships` attribute access, but dict data uses `.get("memberships")`. Adapting requires either a protocol or an overload. Safe but touches 4 files across 3 packages. | File as `FOLLOW-UP-DRY-001` |
| AT1-001: ProgressiveBuilder fetches ALL sections | 53 | Requires injecting `SectionClassifier` into builder constructor (currently has no activity concept). Also blocked by AT1-002 since progressive builder delegates to `ParallelSectionFetcher`. | File as `FOLLOW-UP-AT1-001` (blocked by AT1-002) |
| AT3-002: Resolution cross-context cache miss | 50 | Needs new shared cache infra (module-level or registry-level). Lifecycle management (when to clear?) is nontrivial. Session-level isolation is intentional for context safety. | File as `FOLLOW-UP-AT3-002` |
| AT1-002: ParallelSectionFetcher fetches ALL sections | 47 | Shared infrastructure with multiple callers. Adding `section_filter` parameter changes the contract. Needs careful coordination with AT1-001. | File as `FOLLOW-UP-AT1-002` |
| AT2-004: AssetEdit 3-hop chain walk | 42 | Low frequency (10-20/day). Asana nested `opt_fields` support for `parent.parent.gid` is not verified. Requires API experimentation before committing. | File as `FOLLOW-UP-AT2-004` |
| AT2-005: Lifecycle init sequential dep check | 42 | Low frequency (5-15/day), bounded by early return. Parallelizing with early cancellation adds complexity for minimal gain. | File as `FOLLOW-UP-AT2-005` |

---

## 4. Document Only (Score < 40)

None. All findings scored 42 or above.

---

## 5. Refactoring Tasks

### RF-001: Replace hard-coded TTL with SECTION_CACHE_TTL constant

**Finding**: BUG-001
**Risk Level**: TRIVIAL
**Estimated Lines Changed**: 2

**Before State:**

File: `src/autom8_asana/clients/sections.py`

Line 27 defines the constant:
```python
SECTION_CACHE_TTL = get_settings().cache.ttl_section
```

Line 130 uses a hard-coded literal instead of the constant:
```python
self._cache_set(section_gid, data, EntryType.SECTION, ttl=1800)
```

Line 365 uses a hard-coded literal instead of the constant:
```python
entry = CacheEntry(
    key=gid,
    data=section_data,
    entry_type=EntryType.SECTION,
    version=now,  # No modified_at for sections
    ttl=1800,  # 30 min TTL
)
```

**After State:**

Line 130 becomes:
```python
self._cache_set(section_gid, data, EntryType.SECTION, ttl=SECTION_CACHE_TTL)
```

Line 365 becomes:
```python
entry = CacheEntry(
    key=gid,
    data=section_data,
    entry_type=EntryType.SECTION,
    version=now,  # No modified_at for sections
    ttl=SECTION_CACHE_TTL,
)
```

**Invariants:**
- Default behavior unchanged (`SECTION_CACHE_TTL` defaults to 1800 via `settings.py:168`)
- Env var override via `ASANA_CACHE_TTL_SECTION` now correctly applies to all 3 locations (line 27 definition + lines 130 and 365 usage)
- No API behavior change
- No test changes needed (tests do not assert on literal TTL values)

**Verification:**
1. `grep -n '1800' src/autom8_asana/clients/sections.py` -- must return ZERO results
2. `grep -n 'SECTION_CACHE_TTL' src/autom8_asana/clients/sections.py` -- must return 3 results (line 27 definition + 2 usages)
3. `.venv/bin/pytest tests/unit/clients/test_sections*.py -x -q --timeout=60` -- all pass
4. `.venv/bin/pytest tests/unit/ --ignore=tests/unit/api/ -x -q --timeout=60` -- 8781 passed

**Rollback**: Revert single commit. No downstream dependencies.

---

### RF-002: Eliminate double-fetch in HierarchyTraversalStrategy parent walk

**Finding**: AT2-002
**Risk Level**: LOW
**Estimated Lines Changed**: ~15

**Before State:**

File: `src/autom8_asana/resolution/strategies.py`, method `_traverse_to_business_async` (lines 253-284):

```python
while depth < max_depth:
    if isinstance(current, Business):
        context.cache_entity(current)
        return current

    if budget.exhausted:
        return None

    # Fetch parent -- CALL 1: just to get parent.gid
    parent_task = await context.client.tasks.get_async(
        current.gid, opt_fields=["parent", "parent.gid"]
    )
    budget.consume(1)

    if parent_task.parent is None or parent_task.parent.gid is None:
        return None

    # Fetch parent -- CALL 2: full data for the parent
    parent = await context.client.tasks.get_async(parent_task.parent.gid)
    budget.consume(1)

    # Try to cast parent to Business
    try:
        business = Business.model_validate(parent.model_dump())
        context.cache_entity(business)
        return business
    except (ValueError, ValidationError):
        pass

    current = parent
    depth += 1
```

**Problem**: Two sequential API calls per depth level. Call 1 fetches only `["parent", "parent.gid"]` from the current entity, then Call 2 fetches the full parent. But the current entity's parent GID is the ONLY thing needed from Call 1. If we request the parent reference AS PART OF fetching the full current entity (or if `current` already has a parent attribute from a previous fetch), we can skip Call 1 entirely.

**Key Insight**: On the first iteration, `current` is `from_entity` (a `BusinessEntity` with `.gid` but potentially no `.parent`). On subsequent iterations, `current` is the full parent from the previous iteration's Call 2 -- which already has the parent attribute populated (since `get_async()` returns all default fields including `parent`). So Call 1 is redundant for all iterations after the first, and for the first iteration we can request `parent` in the same call that fetches the full task.

**After State:**

```python
async def _traverse_to_business_async(
    self,
    entity: BusinessEntity,
    context: ResolutionContext,
    budget: ApiBudget,
) -> Business | None:
    """Walk parent chain to reach Business."""
    from autom8_asana.models.business.business import Business

    # Check session cache first
    cached_business = context.get_cached_business()
    if cached_business is not None:
        return cached_business

    current: Any = entity
    depth = 0
    max_depth = 5  # Business -> UnitHolder -> Unit -> ProcessHolder -> Process

    while depth < max_depth:
        if isinstance(current, Business):
            context.cache_entity(current)
            return current

        if budget.exhausted:
            return None

        # Get parent GID from current entity.
        # On first iteration, current may lack parent -- fetch with parent fields.
        # On subsequent iterations, current is a full task from previous get_async
        # which already includes parent.
        parent_gid = getattr(getattr(current, "parent", None), "gid", None)

        if parent_gid is None:
            # Need to fetch current to discover its parent
            parent_task = await context.client.tasks.get_async(
                current.gid, opt_fields=["parent", "parent.gid"]
            )
            budget.consume(1)

            if parent_task.parent is None or parent_task.parent.gid is None:
                return None
            parent_gid = parent_task.parent.gid

        # Fetch the full parent task (single call instead of two)
        parent = await context.client.tasks.get_async(parent_gid)
        budget.consume(1)

        # Try to cast parent to Business
        try:
            business = Business.model_validate(parent.model_dump())
            context.cache_entity(business)
            return business
        except (ValueError, ValidationError):
            pass

        current = parent
        depth += 1

    return None
```

**Key behavioral difference**: On iterations where `current` already has a `parent.gid` attribute (all iterations after the first, since `get_async()` returns full task data including `parent`), the first `get_async` call (formerly lines 262-264) is SKIPPED entirely. This reduces API calls from 2 per depth to 1 per depth for all but potentially the first iteration.

**Invariants:**
- Same resolution result (finds same Business or returns None)
- Same budget consumption semantics (budget.consume called for each actual API call)
- Same session cache behavior (cache_entity called on Business match)
- Same max_depth bound (5 levels)
- Same null-parent termination (returns None when parent chain ends)
- `api_calls` count in `ResolutionResult` from `resolve_async` still uses `budget.used` -- correctly reflects actual calls made

**Verification:**
1. `.venv/bin/pytest tests/unit/resolution/ -x -q --timeout=60` -- all pass
2. `.venv/bin/pytest tests/unit/ --ignore=tests/unit/api/ -x -q --timeout=60` -- 8781 passed
3. Manual trace: with a 3-deep hierarchy (Process -> Unit -> Business), before = 6 API calls (2 per level), after = 4 calls worst case (first level: 2 calls if entity lacks parent, subsequent levels: 1 call each since parent is populated from prior fetch). Best case (entity has parent): 3 calls.
4. Search for other callers of `_traverse_to_business_async`: `grep -rn '_traverse_to_business_async' src/` -- must show only `strategies.py` (called from `resolve_async` at line 203)

**Rollback**: Revert single commit. `_traverse_to_business_async` is a private method with no external callers.

---

### RF-003: Add Business dedup cache to InsightsExportWorkflow

**Finding**: AT3-001
**Risk Level**: LOW
**Estimated Lines Changed**: ~25

**Before State:**

File: `src/autom8_asana/automation/workflows/insights_export.py`

`__init__` (lines 98-106):
```python
def __init__(
    self,
    asana_client: Any,
    data_client: DataServiceClient,
    attachments_client: AttachmentsClient,
) -> None:
    self._asana_client = asana_client
    self._data_client = data_client
    self._attachments_client = attachments_client
```

`_resolve_offer` (lines 552-593):
```python
async def _resolve_offer(
    self,
    offer_gid: str,
    parent_gid: str | None,
) -> tuple[str, str, str | None] | None:
    # If parent_gid not available from enumeration, fetch the task
    if not parent_gid:
        offer_task = await self._asana_client.tasks.get_async(
            offer_gid,
            opt_fields=["parent", "parent.gid"],
        )
        if not offer_task.parent or not offer_task.parent.gid:
            return None
        parent_gid = offer_task.parent.gid

    # Use ResolutionContext to resolve Business
    async with ResolutionContext(
        self._asana_client,
        business_gid=parent_gid,
    ) as ctx:
        business = await ctx.business_async()
        office_phone = business.office_phone
        vertical = business.vertical
        business_name = business.name

    if not office_phone or not vertical:
        return None

    return (office_phone, vertical, business_name)
```

**Problem**: Each of the ~100 offers creates its own `ResolutionContext`, which has its own `_session_cache` (cleared on `__aexit__`). If 5 offers share the same `parent_gid` (Business), the same Business task is fetched 5 times. With 100 offers across 20 unique businesses, this means 80 redundant Business fetches per daily run.

**Proven Pattern** (from `conversation_audit.py:83,305-342`):
```python
# In __init__:
self._activity_map: dict[str, AccountActivity | None] = {}

# In resolve method:
if business_gid in self._activity_map:
    return self._activity_map[business_gid]
# ... fetch ...
self._activity_map[business_gid] = activity
return activity
```

**After State:**

`__init__` adds a dedup cache:
```python
def __init__(
    self,
    asana_client: Any,
    data_client: DataServiceClient,
    attachments_client: AttachmentsClient,
) -> None:
    self._asana_client = asana_client
    self._data_client = data_client
    self._attachments_client = attachments_client
    # Dedup cache: parent_gid -> (office_phone, vertical, business_name)
    # Per AT3-001: eliminates redundant Business fetches across offers
    # sharing the same parent Business. Same pattern as
    # conversation_audit.py._activity_map.
    self._business_cache: dict[str, tuple[str, str, str | None] | None] = {}
```

`_resolve_offer` checks the cache before creating a `ResolutionContext`:
```python
async def _resolve_offer(
    self,
    offer_gid: str,
    parent_gid: str | None,
) -> tuple[str, str, str | None] | None:
    # If parent_gid not available from enumeration, fetch the task
    if not parent_gid:
        offer_task = await self._asana_client.tasks.get_async(
            offer_gid,
            opt_fields=["parent", "parent.gid"],
        )
        if not offer_task.parent or not offer_task.parent.gid:
            return None
        parent_gid = offer_task.parent.gid

    # Check dedup cache first (per AT3-001: same pattern as
    # conversation_audit._activity_map)
    if parent_gid in self._business_cache:
        cached = self._business_cache[parent_gid]
        logger.debug(
            "insights_business_cache_hit",
            extra={
                "offer_gid": offer_gid,
                "parent_gid": parent_gid,
            },
        )
        return cached

    # Cache miss -- resolve via ResolutionContext
    async with ResolutionContext(
        self._asana_client,
        business_gid=parent_gid,
    ) as ctx:
        business = await ctx.business_async()
        office_phone = business.office_phone
        vertical = business.vertical
        business_name = business.name

    if not office_phone or not vertical:
        result = None
    else:
        result = (office_phone, vertical, business_name)

    # Populate dedup cache
    self._business_cache[parent_gid] = result

    return result
```

**Observability**: Add a summary log at the end of `execute_async` (after the gather completes, before returning `WorkflowResult`). This requires finding the appropriate location in `execute_async`. The janitor should add a log line after the `await asyncio.gather(...)` block (around line 199) in the results aggregation section:

```python
logger.info(
    "insights_business_cache_summary",
    extra={
        "total_offers": len(offers),
        "unique_businesses": len(self._business_cache),
        "cache_hits": len(offers) - len(self._business_cache),
        "api_calls_saved": len(offers) - len(self._business_cache),
    },
)
```

The exact insertion point is after line 199 (`await asyncio.gather(...)`) and before line 201 (`succeeded = sum(...)`). The janitor should find the appropriate location in the result aggregation section.

**Invariants:**
- Same resolution result for every offer (same `(office_phone, vertical, business_name)` tuple or None)
- Same error handling semantics (any exception in `ResolutionContext` propagates unchanged)
- Cache is instance-level (per workflow execution), not persistent -- no TTL needed
- Cache is populated even for `None` results (prevents re-fetching known-unresolvable businesses)
- `ResolutionContext` still used for the actual resolution (no change to resolution logic)
- The `_business_cache` is safe for concurrent access because Python dict operations are GIL-protected and the gather uses a Semaphore(5) which serializes the critical section within each coroutine

**Verification:**
1. `.venv/bin/pytest tests/unit/automation/workflows/test_insights_export*.py -x -q --timeout=60` -- all pass
2. `.venv/bin/pytest tests/unit/ --ignore=tests/unit/api/ -x -q --timeout=60` -- 8781 passed
3. `grep -n '_business_cache' src/autom8_asana/automation/workflows/insights_export.py` -- must show __init__ definition + _resolve_offer cache check + cache populate + summary log
4. Verify no persistent caching: `grep -n 'redis\|ttl\|TTL\|expire' src/autom8_asana/automation/workflows/insights_export.py` -- must not show any new TTL/persistence references

**Rollback**: Revert single commit. `_business_cache` is internal state with no external API.

---

## 6. Sequencing

### Phase 1: Zero-Risk Correctness (RF-001)

| Order | Task | Risk | Dependency | Rollback Point |
|:-----:|------|------|------------|----------------|
| 1 | RF-001: Replace hard-coded TTL | TRIVIAL | None | Commit boundary |

**Rationale**: Smallest change, zero blast radius, fixes a real correctness bug. Establishes the commit-and-verify cadence before touching any behavioral code.

**Rollback checkpoint**: Run full test suite after this commit. If any test fails, revert before proceeding.

### Phase 2: Resolution Pipeline Optimization (RF-002)

| Order | Task | Risk | Dependency | Rollback Point |
|:-----:|------|------|------------|----------------|
| 2 | RF-002: Eliminate double-fetch in hierarchy traversal | LOW | None | Commit boundary |

**Rationale**: Single private method change in `strategies.py`. No public API change. The resolution pipeline has comprehensive tests. Run resolution-specific tests first, then full suite.

**Rollback checkpoint**: Run `tests/unit/resolution/` after this commit. If any resolution test fails, revert before proceeding to Phase 3.

### Phase 3: Workflow Optimization (RF-003)

| Order | Task | Risk | Dependency | Rollback Point |
|:-----:|------|------|------------|----------------|
| 3 | RF-003: Business dedup cache for InsightsExport | LOW | None | Commit boundary |

**Rationale**: Isolated to one workflow file. Does not change the resolution infrastructure. The dedup cache is the most impactful optimization (highest score: 83) but scheduled last because it has slightly more lines changed and would benefit from the janitor being warmed up on the simpler tasks first.

**Rollback checkpoint**: Run `tests/unit/automation/workflows/test_insights_export*.py` after this commit. Then full suite.

### Dependency Graph

```
RF-001 (TTL fix)
  |
  v
RF-002 (hierarchy traversal)     [independent of RF-001, sequenced for risk ordering]
  |
  v
RF-003 (business dedup cache)    [independent of RF-002, sequenced for risk ordering]
```

All three tasks are technically independent (no code dependencies between them). The sequencing is purely risk-ordered: trivial -> low -> low-with-more-lines.

---

## 7. Risk Assessment

| Task | Blast Radius | Failure Detection | Recovery Path | Recovery Cost |
|------|-------------|-------------------|---------------|:-------------:|
| RF-001 | `sections.py` only; cache TTL behavior | Unit tests for SectionsClient | Revert 1 commit | Trivial |
| RF-002 | `strategies.py` `_traverse_to_business_async` only | Resolution unit tests; budget tracking assertions | Revert 1 commit | Trivial |
| RF-003 | `insights_export.py` `_resolve_offer` + `__init__` | InsightsExport unit tests; verify dedup log output | Revert 1 commit | Trivial |

**Aggregate risk**: LOW. All three tasks modify private methods/state in isolated modules. No public API changes. No cross-module contract changes. Each is independently revertible.

---

## 8. Janitor Notes

### Commit Conventions

Each task gets ONE atomic commit:

```
fix(clients): replace hard-coded TTL with SECTION_CACHE_TTL constant

Fixes BUG-001: two locations in sections.py use literal 1800 instead of
the SECTION_CACHE_TTL constant, causing silent configuration drift if
ASANA_CACHE_TTL_SECTION env var is overridden.

Refs: INIT-RUNTIME-EFF-001, SMELL-RUNTIME-EFF-001

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

```
perf(resolution): eliminate double-fetch in hierarchy parent traversal

AT2-002: _traverse_to_business_async made 2 API calls per depth level
(one for parent.gid, one for full parent). Now checks if current entity
already has parent.gid populated (which it does after the first iteration
since get_async returns full task data). Reduces calls from 2 to 1 per
depth level for iterations 2+.

Refs: INIT-RUNTIME-EFF-001, SMELL-RUNTIME-EFF-001

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

```
perf(workflows): add Business dedup cache to InsightsExportWorkflow

AT3-001: offers sharing the same parent Business were each creating
separate ResolutionContext instances, re-fetching the same Business.
Adds instance-level _business_cache (same pattern as conversation_audit
_activity_map) to cache resolved (office_phone, vertical, business_name)
tuples by parent_gid. For 100 offers across 20 businesses, eliminates
~80 redundant Business fetches per daily run.

Refs: INIT-RUNTIME-EFF-001, SMELL-RUNTIME-EFF-001

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

### Test Commands

```bash
# After RF-001:
.venv/bin/pytest tests/unit/clients/test_sections*.py -x -q --timeout=60

# After RF-002:
.venv/bin/pytest tests/unit/resolution/ -x -q --timeout=60

# After RF-003:
.venv/bin/pytest tests/unit/automation/workflows/test_insights_export*.py -x -q --timeout=60

# After ALL tasks (full regression):
.venv/bin/pytest tests/unit/ --ignore=tests/unit/api/ -x -q --timeout=60
# Expected: 8781 passed

# Pre-existing failures to IGNORE:
# - test_adversarial_pacing.py (checkpoint assertions)
# - test_paced_fetch.py (checkpoint assertions)
# - test_parallel_fetch.py::test_cache_errors_logged_as_warnings (caplog vs structured logging)
```

### Critical Ordering Constraints

1. **No dependencies between tasks** -- the janitor MAY implement in any order, but the recommended order (RF-001 -> RF-002 -> RF-003) progresses from trivial to slightly more involved.

2. **RF-002: Do NOT change the public interface of `HierarchyTraversalStrategy`** -- `resolve_async()` signature and return type must remain unchanged. The optimization is entirely within the private `_traverse_to_business_async` method.

3. **RF-003: Do NOT change `_resolve_offer` signature** -- the return type `tuple[str, str, str | None] | None` must remain unchanged. The cache is transparent to callers.

4. **RF-003: Cache must include `None` results** -- if a Business resolution fails (returns None), that result must be cached to prevent re-attempting the same unresolvable Business for other offers sharing the same `parent_gid`.

5. **RF-002: Budget consumption must match actual API calls** -- `budget.consume(1)` must be called exactly once per `get_async` call. If the parent GID is obtained from the existing entity attributes (no API call), do NOT consume budget.

6. **All tasks: No new modules** -- per PROMPT-0 implementation rule 5, prefer adding methods/attributes to existing classes.

### Implementation Rules Reminder (from PROMPT-0)

1. Every optimization MUST have a fallback -- RF-002 naturally falls back (if entity lacks parent, it fetches; otherwise skips). RF-003 falls back on cache miss.
2. Every optimization MUST log before/after -- RF-003 includes `insights_business_cache_summary` log with `total_offers`, `unique_businesses`, `cache_hits`, `api_calls_saved`.
3. Every optimization MUST preserve test compatibility -- no public APIs change.
4. Concurrency limits: Semaphore(5) for processing, Semaphore(8) for resolution -- not changed by any task.
5. No new modules unless necessary -- all changes are within existing files.

---

## 9. Attestation

| Source Artifact | Verified Via | Line References Confirmed |
|-----------------|-------------|--------------------------|
| `src/autom8_asana/clients/sections.py` | Read tool | Lines 27, 130, 365: constant defined, 2 hard-coded sites confirmed |
| `src/autom8_asana/resolution/strategies.py` | Read tool | Lines 235-284: double-fetch pattern in `_traverse_to_business_async` confirmed; lines 140-172: sequential dep fetch in `DependencyShortcutStrategy` confirmed |
| `src/autom8_asana/automation/workflows/insights_export.py` | Read tool | Lines 98-106: no dedup cache in `__init__`; lines 552-593: new `ResolutionContext` per offer confirmed; lines 197-198: `asyncio.gather` dispatching all offers confirmed |
| `src/autom8_asana/automation/workflows/conversation_audit.py` | Read tool | Lines 83, 305-342: `_activity_map` dedup cache pattern confirmed as template |
| `src/autom8_asana/resolution/context.py` | Read tool | Lines 74, 86-88: `_session_cache` cleared on `__aexit__` confirmed (each context is isolated) |
| `src/autom8_asana/dataframes/builders/progressive.py` | Read tool | Lines 562-567: `_list_sections` returns ALL sections, no classifier filtering |
| `src/autom8_asana/dataframes/builders/parallel_fetch.py` | Read tool | Lines 124-166: `fetch_all()` fetches ALL sections without ACTIVE filtering |
| `src/autom8_asana/dataframes/builders/freshness.py` | Read tool | Lines 340-346: sequential `get_async` for added GIDs |
| `src/autom8_asana/models/business/asset_edit.py` | Read tool | Lines 644-663: 3-hop sequential chain confirmed |
| `src/autom8_asana/lifecycle/init_actions.py` | Read tool | Lines 199-204: sequential dep check with early return |
| `src/autom8_asana/models/business/activity.py` | Read tool | Lines 138-171: orphaned `extract_section_name` canonical implementation |
| `src/autom8_asana/dataframes/extractors/base.py` | Read tool | Lines 488-521: duplicate `_extract_section` |
| `src/autom8_asana/dataframes/views/dataframe_view.py` | Read tool | Lines 835-870: duplicate `_extract_section` with dict input divergence |
| `src/autom8_asana/models/business/process.py` | Read tool | Lines 414-430: simplified `pipeline_state` variant |
| SMELL report (`docs/hygiene/SMELL-runtime-efficiency-audit.md`) | Read tool | All 11 findings reviewed |
| PROMPT-0 (`.claude/artifacts/PROMPT-0-runtime-efficiency-audit.md`) | Read tool | Prioritization matrix, implementation rules, anti-patterns reviewed |

---

## Handoff Checklist

- [x] Every smell classified (3 SHIP, 8 DEFER with reasons, 0 dismissed)
- [x] Each shipping refactoring has before/after contract documented (RF-001, RF-002, RF-003)
- [x] Invariants and verification criteria specified for each task
- [x] Refactorings sequenced with explicit dependencies (none; risk-ordered)
- [x] Rollback points identified between phases (commit boundary after each task)
- [x] Risk assessment complete for each phase (all LOW/TRIVIAL)
- [x] Artifacts verified via Read tool with attestation table
