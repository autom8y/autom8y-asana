# Orchestrator Initialization: Resolution Batch Operations

## Metadata

- **Initiative ID**: RESOLUTION-BATCH
- **Type**: Feature (smaller than Module)
- **Parent Initiative**: Cross-Holder Relationship Resolution (Sessions 1-6, COMPLETE)
- **Author**: Requirements Analyst
- **Created**: 2025-12-16
- **Sponsor**: SDK Users requiring batch AssetEdit resolution

---

## Context & Available Skills

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`autom8-asana-domain`** - SDK patterns, SaveSession, async-first conventions, batch operations
  - Activates when: Implementing resolution logic, working with AsanaClient

- **`documentation`** - PRD/TDD/ADR templates, workflow pipeline, quality gates
  - Activates when: Reviewing existing documentation, updating docs

- **`standards`** - Tech stack decisions, code conventions, repository structure
  - Activates when: Writing code, ensuring consistency with existing patterns

- **`10x-workflow`** - Agent coordination, session protocol, quality gates
  - Activates when: Planning phases, coordinating handoffs

**How Skills Work**: Skills load automatically based on your current task. When you need SDK patterns, the `autom8-asana-domain` skill activates. When you need coding conventions, the `standards` skill activates.

---

## Your Role: Orchestrator

You coordinate a 4-agent development workflow. You plan, delegate, coordinate, and verify. For this focused initiative, most work will be delegated to @principal-engineer with @qa-adversary validation.

### Your Specialist Agents

| Agent | Invocation | Responsibility |
|-------|------------|----------------|
| **Principal Engineer** | `@principal-engineer` | Implementation, code quality, technical execution |
| **QA/Adversary** | `@qa-adversary` | Validation, edge case testing, quality review |

**Note**: Requirements and architecture are already complete. No @requirements-analyst or @architect work needed.

---

## The Mission: Complete Deferred Batch Resolution Functionality

Implement the batch resolution functions and sync wrappers that were deferred from the Cross-Holder Relationship Resolution initiative. These enable efficient resolution of multiple AssetEdits to Units/Offers in a single operation.

### Why This Initiative?

- **High-frequency use case**: Per user feedback, batch operations are "incredibly common" for patterns like "get all office phones of active offers"
- **API efficiency**: Batch functions optimize shared lookups, reducing redundant API calls
- **Complete the feature**: Instance methods are implemented; batch functions complete the API surface
- **Design ready**: ADR-0073 specifies the exact API design; no architecture decisions needed

### Current State

**Implemented (from Sessions 1-6)**:
- `AssetEdit` entity with 11 typed field accessors (`src/autom8_asana/models/business/asset_edit.py`)
- `ResolutionStrategy` enum with priority ordering (`src/autom8_asana/models/business/resolution.py`)
- `ResolutionResult[T]` generic type with ambiguity handling per ADR-0071
- `AssetEdit.resolve_unit_async()` instance method
- `AssetEdit.resolve_offer_async()` instance method
- `TasksClient.dependents_async()` method
- 78 unit tests passing

**Foundation in Place**:
- ADR-0071: Ambiguity handling (first match in entity, all in candidates)
- ADR-0072: No internal caching of resolution results
- ADR-0073: Batch API design (module-level functions, dict return type)
- Instance method implementations provide the per-item resolution logic

**What's Missing**:

```python
# This is what we need to enable:

from autom8_asana.models.business.resolution import resolve_units_async, resolve_offers_async

# Batch resolve all AssetEdits to Units efficiently
results = await resolve_units_async(asset_edits, client)

# Result: dict mapping gid to ResolutionResult
# - Shared lookups (Business.units fetched once, not per-AssetEdit)
# - Concurrent API calls where possible
# - Every input has an entry (even on failure)
```

### Implementation Profile

| Attribute | Value |
|-----------|-------|
| Target Location | `src/autom8_asana/models/business/resolution.py` |
| Dependencies | AssetEdit, ResolutionResult, ResolutionStrategy (all exist) |
| API Pattern | Module-level async functions (per ADR-0073) |
| Return Type | `dict[str, ResolutionResult[T]]` |
| Test Coverage Target | >80% on new code |
| Complexity | Feature (focused, design-complete) |

### Target API

Per ADR-0073, the batch API design is:

```python
# Module functions in src/autom8_asana/models/business/resolution.py

async def resolve_units_async(
    asset_edits: Sequence[AssetEdit],
    client: AsanaClient,
    *,
    strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
) -> dict[str, ResolutionResult[Unit]]:
    """Batch resolve multiple AssetEdits to Units.

    Optimizes shared lookups:
    1. Group AssetEdits by Business
    2. Ensure each Business has units hydrated (single fetch per Business)
    3. Concurrent dependents fetch for DEPENDENT_TASKS strategy
    4. Per-AssetEdit resolution using pre-fetched data
    """

async def resolve_offers_async(
    asset_edits: Sequence[AssetEdit],
    client: AsanaClient,
    *,
    strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
) -> dict[str, ResolutionResult[Offer]]:
    """Batch resolve multiple AssetEdits to Offers."""

# Sync wrappers (per FR-API-002)
def resolve_units(
    asset_edits: Sequence[AssetEdit],
    client: AsanaClient,
    *,
    strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
) -> dict[str, ResolutionResult[Unit]]:
    """Sync wrapper for resolve_units_async."""

def resolve_offers(
    asset_edits: Sequence[AssetEdit],
    client: AsanaClient,
    *,
    strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
) -> dict[str, ResolutionResult[Offer]]:
    """Sync wrapper for resolve_offers_async."""
```

---

## Key Constraints

1. **Follow ADR-0073**: API design is decided; implementation must match signatures exactly
2. **Module-level functions**: NOT class methods (per ADR-0073 rationale)
3. **Optimize shared lookups**: Fetch Business.units once per Business, not per AssetEdit
4. **Every input has entry**: Result dict must contain entry for every input AssetEdit
5. **Concurrent where possible**: Use asyncio.gather for independent API calls
6. **Export from package**: Functions must be exported from `models.business` `__init__.py`
7. **Match existing patterns**: Follow the same error handling and logging as instance methods

---

## Requirements Summary

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| **FR-BATCH-001** | `resolve_units_async(asset_edits, client)` batch function | Should | Not Started |
| **FR-BATCH-002** | `resolve_offers_async(asset_edits, client)` batch function | Should | Not Started |
| **FR-API-002** | Sync wrappers (`resolve_units`, `resolve_offers`) | Could | Not Started |

### Detailed Requirements (from PRD-RESOLUTION)

**FR-BATCH-001: Batch Unit Resolution**
- Function signature per ADR-0073
- Returns `dict[str, ResolutionResult[Unit]]` mapping `asset_edit.gid` to result
- Optimizes shared lookups (fetch Business.units once)
- Uses concurrent fetching where possible
- Handles partial failures (some resolve, some don't)

**FR-BATCH-002: Batch Offer Resolution**
- Function signature per ADR-0073
- Returns `dict[str, ResolutionResult[Offer]]`
- Can build on `resolve_units_async()` for efficiency
- Handles partial failures

**FR-API-002: Sync Wrappers**
- `resolve_units()` and `resolve_offers()` sync versions
- Uses `@sync_wrapper` pattern from SDK or `asyncio.run()`
- Functionally identical to async versions

---

## Success Criteria

1. `resolve_units_async()` implemented and tested
2. `resolve_offers_async()` implemented and tested
3. Sync wrappers `resolve_units()` and `resolve_offers()` implemented
4. Functions exported from `autom8_asana.models.business`
5. Unit tests for batch functions (>80% coverage on new code)
6. Integration test demonstrating batch optimization
7. All existing tests continue to pass
8. mypy passes with strict mode
9. Documentation in docstrings matches ADR-0073 examples

### Performance Validation

| Metric | Requirement |
|--------|-------------|
| Shared lookups | Business.units fetched once per unique Business |
| API call count | O(1) shared + O(N) per-item (not O(N) shared) |
| Partial failure | Some failures don't block others |

---

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Implementation** | @principal-engineer | Batch functions + sync wrappers + unit tests |
| **2: Validation** | @qa-adversary | Edge case testing, optimization verification |

**Note**: This is a 2-session initiative. Sessions may collapse to 1 if implementation is straightforward.

---

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rule**: Never execute without explicit confirmation.

---

## Implementation Guidance (from TDD-RESOLUTION)

### Batch Resolution Algorithm

```python
async def resolve_units_async(
    asset_edits: Sequence[AssetEdit],
    client: AsanaClient,
    *,
    strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
) -> dict[str, ResolutionResult[Unit]]:
    # 1. Collect unique Businesses from input AssetEdits
    businesses = _collect_unique_businesses(asset_edits)

    # 2. Ensure all Businesses have units hydrated (single fetch per Business)
    await asyncio.gather(*[
        _ensure_units_hydrated(b, client) for b in businesses.values()
    ])

    # 3. Pre-fetch strategy-specific data concurrently
    dependents_map = {}
    if strategy in (ResolutionStrategy.AUTO, ResolutionStrategy.DEPENDENT_TASKS):
        dependents_map = await _batch_fetch_dependents(asset_edits, client)

    # 4. Resolve each AssetEdit using pre-fetched data
    results = {}
    for ae in asset_edits:
        result = await ae.resolve_unit_async(client, strategy=strategy)
        # OR use optimized internal path with pre-fetched context
        results[ae.gid] = result

    return results
```

### Key Implementation Details

1. **Group by Business**: Extract `asset_edit._business` or `asset_edit.business` property
2. **Hydration check**: `if not business.unit_holder._children: await business.unit_holder.hydrate_async(client)`
3. **Concurrent dependents**: `asyncio.gather(*[client.tasks.dependents_async(ae.gid).collect() for ae in asset_edits])`
4. **Per-item resolution**: Can delegate to existing instance methods or inline optimized logic

### Sync Wrapper Pattern

```python
def resolve_units(
    asset_edits: Sequence[AssetEdit],
    client: AsanaClient,
    *,
    strategy: ResolutionStrategy = ResolutionStrategy.AUTO,
) -> dict[str, ResolutionResult[Unit]]:
    """Sync wrapper for resolve_units_async."""
    import asyncio
    return asyncio.get_event_loop().run_until_complete(
        resolve_units_async(asset_edits, client, strategy=strategy)
    )
```

**Alternative**: Use existing `@sync_wrapper` decorator if available in SDK.

---

## Files to Modify

| File | Change |
|------|--------|
| `src/autom8_asana/models/business/resolution.py` | Add batch functions |
| `src/autom8_asana/models/business/__init__.py` | Export new functions |
| `tests/unit/models/business/test_resolution.py` | Add batch function tests |

### Reference Files (Read-Only)

| File | Purpose |
|------|---------|
| `src/autom8_asana/models/business/asset_edit.py` | Instance method patterns |
| `docs/decisions/ADR-0073-batch-resolution-api-design.md` | API design decisions |
| `docs/requirements/PRD-RESOLUTION.md` | Full requirements |
| `docs/design/TDD-RESOLUTION.md` | Technical design |

---

## ADR References

- **ADR-0071**: Ambiguity handling - Return first match in entity, set ambiguous=True, all in candidates
- **ADR-0072**: No resolution caching - Each call resolves fresh
- **ADR-0073**: Batch API design - Module functions, dict return, signatures defined

---

## Open Questions

None. All design decisions are made in ADR-0073.

---

## Your First Task

Confirm understanding by:

1. Summarizing the initiative goal in 2-3 sentences
2. Listing the 2 sessions and their deliverables
3. Confirming the 3 functions to implement
4. Confirming the files to modify
5. Confirming ADR-0073 defines the exact API signatures

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

# Session Trigger Prompts

## Session 1: Implementation

```markdown
Begin Session 1: Batch Resolution Implementation

Work with the @principal-engineer agent to implement batch resolution functions.

**Prerequisites:**
- Instance methods (resolve_unit_async, resolve_offer_async) already implemented
- ADR-0073 defines exact API signatures
- resolution.py already contains ResolutionStrategy, ResolutionResult

**Goals:**
1. Implement `resolve_units_async()` batch function
2. Implement `resolve_offers_async()` batch function
3. Implement sync wrappers `resolve_units()` and `resolve_offers()`
4. Export functions from `models.business` package
5. Add unit tests for batch functions (>80% coverage)

**Implementation Path:**
- Add functions to `src/autom8_asana/models/business/resolution.py`
- Follow optimization pattern from TDD-RESOLUTION Section "Batch Resolution Algorithm"
- Match error handling and logging patterns from AssetEdit instance methods
- Export from `src/autom8_asana/models/business/__init__.py`

**Test Cases:**
- Empty input list -> empty dict
- Single AssetEdit -> dict with one entry
- Multiple AssetEdits same Business -> Business.units fetched once
- Multiple AssetEdits different Businesses -> each Business.units fetched once
- Partial failures -> failed entries have error, successful have entity
- All strategies: DEPENDENT_TASKS, CUSTOM_FIELD_MAPPING, EXPLICIT_OFFER_ID, AUTO

**Hard Constraints:**
- Signatures MUST match ADR-0073 exactly
- Module-level functions, NOT class methods
- Return type: dict[str, ResolutionResult[T]]
- Every input AssetEdit MUST have entry in result

Create the implementation plan first. I'll review before you execute.
```

## Session 2: Validation

```markdown
Begin Session 2: Batch Resolution Validation

Work with the @qa-adversary agent to validate the batch implementation.

**Prerequisites:**
- Session 1 complete (batch functions implemented and unit tested)

**Goals:**

**Part 1: Functional Validation**
- Verify resolve_units_async returns correct results for various inputs
- Verify resolve_offers_async returns correct results
- Verify sync wrappers work identically to async versions
- Verify exports are accessible from autom8_asana.models.business

**Part 2: Optimization Verification**
- Verify Business.units fetched once per unique Business (not per AssetEdit)
- Verify concurrent API calls where appropriate
- Count API calls in test to confirm O(1) shared + O(N) per-item

**Part 3: Edge Case Testing**
- Empty input list
- Single AssetEdit without Business context
- AssetEdits from different Businesses
- Mixed success/failure results
- All AssetEdits fail resolution
- Very large input list (performance check)

**Part 4: Integration Check**
- Verify instance methods still work after changes
- Verify all 78 existing tests pass
- Verify mypy passes
- Verify type safety of dict return type

Create the validation plan first. I'll review before you execute.
```

---

# Context Gathering Checklist

Before starting, confirm access to:

**Implementation Context:**
- [x] `src/autom8_asana/models/business/resolution.py` - Current resolution types
- [x] `src/autom8_asana/models/business/asset_edit.py` - Instance method patterns
- [x] `docs/decisions/ADR-0073-batch-resolution-api-design.md` - API design

**Requirements Context:**
- [x] `docs/requirements/PRD-RESOLUTION.md` - FR-BATCH-001, FR-BATCH-002, FR-API-002
- [x] `docs/design/TDD-RESOLUTION.md` - Batch resolution algorithm

**Test Context:**
- [ ] `tests/unit/models/business/test_resolution.py` - Existing resolution tests
- [ ] `tests/unit/models/business/test_asset_edit.py` - Instance method test patterns
