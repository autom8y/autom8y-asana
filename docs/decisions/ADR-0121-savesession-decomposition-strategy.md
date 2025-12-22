# ADR-0121: SaveSession Decomposition Strategy

## Metadata
- **Status**: Proposed
- **Author**: Architect (Claude)
- **Date**: 2025-12-19
- **Deciders**: SDK Team
- **Related**: [PRD-SPRINT-4-SAVESESSION-DECOMPOSITION](/docs/requirements/PRD-SPRINT-4-SAVESESSION-DECOMPOSITION.md), [TDD-SPRINT-4-SAVESESSION-DECOMPOSITION](/docs/design/TDD-SPRINT-4-SAVESESSION-DECOMPOSITION.md), ADR-0122, ADR-0066, ADR-0074

## Context

SaveSession (`persistence/session.py`) has grown to 2193 lines with 50 methods, exhibiting "god class" symptoms. The PRD targets an 82% line reduction (2193 -> ~400 lines) while preserving 100% backward compatibility.

The key question is: **How should we extract functionality from SaveSession?**

Two primary approaches were considered:
1. **Package extraction**: Create a `persistence/session/` package with multiple submodules (similar to the Sprint 3 detection decomposition per ADR-0120)
2. **In-place refactoring**: Keep SaveSession in a single file but extract reusable components to sibling modules

Forces at play:
- 18 action methods (920 lines, 42%) follow identical boilerplate patterns
- Tests access private attributes (`_state`, `_healing_queue`, `_auto_heal`)
- Import path `autom8_asana.persistence.session.SaveSession` must remain unchanged
- Healing logic exists in two places: standalone utilities and session-embedded methods
- SessionState enum is referenced across tests

## Decision

We will use **in-place refactoring** with sibling module extraction:

1. **Keep SaveSession in `session.py`** (not a package)
2. **Create `persistence/actions.py`** for ActionBuilder infrastructure
3. **Expand `persistence/healing.py`** to include HealingManager class
4. **Add inspection properties** to SaveSession for test access
5. **Clean up commit logic inline** rather than extracting to separate module

## Rationale

### Why In-Place Over Package?

| Factor | Package Approach | In-Place Approach | Winner |
|--------|-----------------|-------------------|--------|
| Import path stability | Requires `__init__.py` re-exports | No changes needed | In-place |
| Test disruption | Tests must update imports | Tests unchanged | In-place |
| Code review complexity | Many new files | Fewer, focused changes | In-place |
| IDE navigation | Harder to find related code | SaveSession remains discoverable | In-place |
| Rollback difficulty | Delete package, restore file | Revert individual modules | In-place |

**Key insight**: Unlike detection.py (1125 lines of conceptually independent tiers), SaveSession's components are tightly integrated. A facade class orchestrating submodules adds indirection without simplifying the mental model.

### Why ActionBuilder in Separate Module?

The ActionBuilder pattern requires:
- `ActionConfig` dataclass (~20 lines)
- `ActionVariant` enum (~10 lines)
- `ACTION_REGISTRY` with 18 configurations (~100 lines)
- `ActionBuilder` descriptor class (~80 lines)

Placing these in `session.py` would not reduce line count. A dedicated `actions.py`:
- Keeps registration logic separate from session logic
- Enables testing ActionBuilder in isolation
- Provides clear ownership for action configurations

### Why Merge Healing into Existing Module?

Current state:
- `persistence/healing.py` (~80 lines): Standalone utilities
- `session.py` (~165 lines): `_should_heal()`, `_queue_healing()`, `_execute_healing_async()`

Creating a third location (e.g., `session/healing.py`) would fragment healing logic further. Merging into existing `healing.py`:
- Single source of truth for all healing logic
- Standalone utilities remain available for ad-hoc use
- Session delegates to `HealingManager.execute_async()`

### Why Keep SessionState in session.py?

SessionState is:
- Used only by SaveSession
- Only 10 lines
- Tightly coupled to session lifecycle

Moving to `models.py` would:
- Add import complexity
- Fragment closely-related code
- Require updating test imports

### Why Skip Commit Orchestrator Extraction?

After ActionBuilder (770 line reduction) and HealingManager (115 line reduction):
- Expected `commit_async()` size: ~100 lines
- Phase ordering is critical (DEF-001 fix, ADR-0066 selective clearing)
- Extracting would add indirection without meaningful simplification

Instead: Clean up with private helper methods inline.

## Alternatives Considered

### Alternative 1: Package Extraction (Like Detection)

- **Description**: Create `persistence/session/` package with `__init__.py`, `actions.py`, `state.py`, `healing.py`, `commit.py`
- **Pros**:
  - Consistent with ADR-0120 pattern
  - Clear module boundaries
  - Easy to extend with new submodules
- **Cons**:
  - Requires `__init__.py` re-exports to maintain API
  - Tests must update imports or use re-exports
  - Adds complexity for tightly-coupled code
  - More files to navigate
- **Why not chosen**: SaveSession's components are more integrated than detection tiers. Package structure adds complexity without proportional benefit.

### Alternative 2: Mixin Classes

- **Description**: Define `ActionMixin`, `HealingMixin`, `CommitMixin`, compose into SaveSession
- **Pros**:
  - Methods stay on SaveSession
  - No import path changes
  - Clear separation by concern
- **Cons**:
  - Multiple inheritance can be confusing
  - Method resolution order (MRO) complexity
  - Mixins share instance state (coupling)
  - Harder to test mixins in isolation
- **Why not chosen**: Mixins work well for truly orthogonal concerns. SaveSession's concerns share state (`_pending_actions`, `_healing_queue`) making clean mixin boundaries difficult.

### Alternative 3: Strategy Pattern

- **Description**: Inject `ActionStrategy`, `HealingStrategy` objects at construction
- **Pros**:
  - Easy to swap implementations
  - Clear boundaries
  - Testable strategies
- **Cons**:
  - Over-engineering for single implementation
  - Adds runtime cost for strategy lookup
  - Strategies still need session state access
- **Why not chosen**: No current need for multiple implementations. Strategy pattern adds complexity for theoretical flexibility.

### Alternative 4: Keep Everything in session.py

- **Description**: Reduce line count through other means (shorter docstrings, less logging)
- **Pros**:
  - No structural changes
  - Lowest risk
- **Cons**:
  - Cannot achieve 82% reduction
  - Boilerplate remains
  - Cognitive load unchanged
- **Why not chosen**: Does not meet PRD targets. The 18 action methods are fundamentally boilerplate that should be generated.

## Consequences

### Positive

- **Minimal disruption**: Import path unchanged, tests work as-is
- **Clear extraction targets**: ActionBuilder and HealingManager have distinct responsibilities
- **Testable components**: ActionBuilder and HealingManager can be unit tested independently
- **Reduced cognitive load**: 920 lines of action boilerplate replaced with ~20 lines of declarations
- **Single healing location**: All healing logic in `persistence/healing.py`

### Negative

- **session.py still central**: ~400 lines remain in one file
- **New module to learn**: `actions.py` introduces ActionBuilder pattern
- **HealingManager coupling**: SaveSession depends on HealingManager for healing functionality
- **Descriptor complexity**: ActionBuilder uses Python descriptors (intermediate concept)

### Neutral

- **Line count**: 82% reduction achieved through different distribution than package approach
- **File count**: +1 new file (`actions.py`), same healing.py expanded
- **Test coverage**: Existing tests pass; new tests needed for ActionBuilder

## Compliance

How do we ensure this decision is followed?

1. **Code review**: ActionBuilder usage required for new action methods
2. **Test presence**: `test_action_builder.py` must exist and pass
3. **Line count gate**: session.py must remain under 500 lines post-extraction
4. **Import validation**: No direct imports from `persistence/session/` (package does not exist)

## Verification

After implementation:
```bash
# Verify line counts
wc -l src/autom8_asana/persistence/session.py  # Should be ~400
wc -l src/autom8_asana/persistence/actions.py  # Should be ~150
wc -l src/autom8_asana/persistence/healing.py  # Should be ~200

# Verify import path unchanged
python -c "from autom8_asana.persistence.session import SaveSession"

# Verify all tests pass
pytest tests/unit/persistence/test_session*.py -v
```
