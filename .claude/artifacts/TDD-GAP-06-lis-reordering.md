---
artifact_id: TDD-GAP-06-lis-reordering
title: "LIS-Based Subtask Reordering"
created_at: "2026-02-07T19:30:00Z"
author: architect
prd_ref: PRD-GAP-06-lis-reordering
status: approved
components:
  - name: reorder
    type: module
    description: "LIS algorithm, data models, move generation, and SaveSession wrapper"
    dependencies:
      - name: bisect (stdlib)
        type: external
      - name: SaveSession
        type: internal
      - name: structlog
        type: external
    files:
      - src/autom8_asana/persistence/reorder.py
schema_version: "1.0"
---

# TDD: LIS-Based Subtask Reordering

**Status:** APPROVED -- direct handoff to principal-engineer
**Complexity:** SCRIPT
**PRD:** `PRD-GAP-06-lis-reordering`
**Stakeholder Decisions:** `stakeholder-decisions-GAP-06-lis-reordering.md`

---

## 1. Overview

Compute the minimum number of `SET_PARENT` actions needed to reorder subtasks from a current order to a desired order. The Longest Increasing Subsequence (LIS) identifies elements already in correct relative position; only the remaining elements move. For the typical holder case (7 holders, 5 already ordered), this reduces API calls from 7 to 2.

Everything lives in a single new file: `src/autom8_asana/persistence/reorder.py`.

---

## 2. Data Models

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from autom8_asana.models.base import AsanaResource


@dataclass(frozen=True, slots=True)
class Move:
    """A single reorder instruction.

    Attributes:
        item: The AsanaResource to move.
        reference: The AsanaResource to position relative to (stable -- in the LIS
                   or already placed).
        direction: "insert_before" or "insert_after".
    """
    item: AsanaResource
    reference: AsanaResource
    direction: Literal["insert_before", "insert_after"]


@dataclass(frozen=True, slots=True)
class ReorderPlan:
    """Result of compute_reorder_plan().

    Attributes:
        moves: Ordered list of Move instructions. Executing them sequentially on
               the input produces the desired order.
        lis_length: Length of the longest increasing subsequence (elements that
                    stay in place).
        total_children: Total number of children in the input.
    """
    moves: tuple[Move, ...]
    lis_length: int
    total_children: int

    @property
    def moves_required(self) -> int:
        """Number of SET_PARENT actions needed."""
        return len(self.moves)
```

`frozen=True` and `slots=True` for immutability and memory efficiency. `moves` is a tuple (immutable) rather than a list to reinforce that the plan is a computed result, not a mutable accumulator.

---

## 3. LIS Algorithm

O(N log N) patience sorting using `bisect.bisect_left`. This is the standard algorithm for LIS with index recovery.

### Signature

```python
def _compute_lis_indices(position_sequence: list[int]) -> set[int]:
    """Compute indices of elements forming the Longest Increasing Subsequence.

    Args:
        position_sequence: For each element at index i in the current order,
            the value is its position in the desired order. E.g., if current[2]
            should be at desired position 5, then position_sequence[2] == 5.

    Returns:
        Set of indices into position_sequence that form the LIS.
        These elements are already in correct relative order and do not need to move.
    """
```

### Algorithm (pseudocode)

```
tails = []            # tails[i] = smallest ending value of IS of length i+1
tail_indices = []     # tail_indices[i] = index in position_sequence of tails[i]
predecessors = [-1] * N  # predecessors[i] = index of element before i in the LIS

for i, val in enumerate(position_sequence):
    pos = bisect_left(tails, val)
    if pos == len(tails):
        tails.append(val)
        tail_indices.append(i)
    else:
        tails[pos] = val
        tail_indices[pos] = i
    predecessors[i] = tail_indices[pos - 1] if pos > 0 else -1

# Backtrack from tail_indices[-1] through predecessors to recover full LIS
lis_indices = set()
idx = tail_indices[-1]
while idx != -1:
    lis_indices.add(idx)
    idx = predecessors[idx]

return lis_indices
```

This gives O(N log N) time from the `bisect_left` call and O(N) space.

---

## 4. compute_reorder_plan()

### Signature

```python
def compute_reorder_plan(
    current_order: list[AsanaResource],
    desired_order: list[AsanaResource],
) -> ReorderPlan:
    """Compute the minimum moves to transform current_order into desired_order.

    Pure function. No I/O. No session dependency. This IS the dry-run.

    Both lists must contain the same elements (by gid). Order differs.

    Args:
        current_order: Elements in their current sequence.
        desired_order: Elements in the target sequence.

    Returns:
        ReorderPlan with Move instructions.

    Raises:
        ValueError: If the two lists contain different elements (by gid) or
            contain duplicate gids.
    """
```

### Algorithm

```
1. Build desired_position: dict[str, int]  -- maps gid -> index in desired_order
2. Validate: same gids in both lists, no duplicates
3. Build position_sequence: [desired_position[item.gid] for item in current_order]
4. lis_indices = _compute_lis_indices(position_sequence)
5. Generate moves (see Section 5)
6. Return ReorderPlan(moves, len(lis_indices), len(current_order))
```

### Degenerate cases (handled before step 3)

- `len(current_order) <= 1`: Return `ReorderPlan((), len(current_order), len(current_order))`
- Empty desired_order with empty current_order: Return `ReorderPlan((), 0, 0)`

---

## 5. Move Generation Strategy

For each element NOT in the LIS, we must place it at its correct position in the desired order, using a reference element that is stable (either in the LIS or already placed by a prior move in this sequence).

### Reference selection algorithm

After computing the LIS, build the "placed" set: initially the set of elements in the LIS. Process non-LIS elements in desired order (ascending by their desired position). For each non-LIS element at desired position `p`:

1. **Look left** in desired_order for the nearest element at position `p-1, p-2, ...` that is in the "placed" set.
2. If found: `Move(item=current_element, reference=left_neighbor, direction="insert_after")`.
3. If not found (element belongs at position 0, before all placed elements): **Look right** in desired_order for the nearest element at position `p+1, p+2, ...` that is in the "placed" set. Generate `Move(item=current_element, reference=right_neighbor, direction="insert_before")`.
4. Add the current element to the "placed" set.

This guarantees:
- Every reference is stable at the time of the move (it is either an original LIS member or was placed by an earlier move).
- Processing in desired order means earlier placements become available as references for later ones.
- The algorithm produces exactly `N - LIS_length` moves.

### Why this works

Elements in the LIS are already in correct relative order. They form the "skeleton" of the final sequence. Non-LIS elements are inserted into this skeleton at their target positions. By processing left-to-right in desired order, each insertion either slots after an already-placed element or before the first placed element.

---

## 6. SaveSession.reorder_subtasks() Wrapper

A thin method on `SaveSession` that calls `compute_reorder_plan()` and queues `SET_PARENT` actions via the existing `set_parent()` method.

```python
def reorder_subtasks(
    self,
    parent: AsanaResource | str,
    current_order: list[AsanaResource],
    desired_order: list[AsanaResource],
) -> ReorderPlan:
    """Reorder subtasks under a parent with minimum API calls.

    Per TDD-GAP-06: Computes LIS-optimized reorder plan, then queues
    SET_PARENT actions for each Move.

    Does NOT modify the existing reorder_subtask() singular method.

    Args:
        parent: Parent task (AsanaResource or GID string). All items in
            current_order must be subtasks of this parent.
        current_order: Children in their current sequence.
        desired_order: Children in the target sequence.

    Returns:
        The computed ReorderPlan (for logging/inspection).

    Raises:
        ValueError: If current_order and desired_order contain different elements.
        SessionClosedError: If session is closed.
    """
    self._ensure_open()

    plan = compute_reorder_plan(current_order, desired_order)

    if plan.moves_required > 0:
        import structlog
        log = structlog.get_logger(__name__)
        log.info(
            "reorder_plan_computed",
            parent_gid=parent if isinstance(parent, str) else parent.gid,
            total_children=plan.total_children,
            lis_length=plan.lis_length,
            moves_required=plan.moves_required,
        )

    for move in plan.moves:
        if move.direction == "insert_after":
            self.set_parent(move.item, parent, insert_after=move.reference)
        else:
            self.set_parent(move.item, parent, insert_before=move.reference)

        import structlog
        log = structlog.get_logger(__name__)
        log.debug(
            "move_planned",
            item=move.item.gid,
            reference=move.reference.gid,
            direction=move.direction,
        )

    return plan
```

**Implementation note:** The `import structlog` above is illustrative. The actual implementation should use the project's standard `autom8y_log.get_logger(__name__)` pattern, consistent with the rest of the persistence package. The logger should be initialized at module level or use `self._log` if available.

### Where to add

Add `reorder_subtasks` as a method on `SaveSession` in `persistence/session.py`, in the "Parent Operations" section (after `reorder_subtask()` at line ~1410). Import `compute_reorder_plan` and `ReorderPlan` from `persistence.reorder`.

The existing `reorder_subtask()` (singular, line 1363-1409) is NOT modified.

---

## 7. GAP-01 Wiring Point

### Current state (from code inspection)

`HolderEnsurer.ensure_holders_for_entities()` in `persistence/holder_ensurer.py` creates missing holders and wires parent references. After the ENSURE_HOLDERS phase completes (commit_async line 818), the newly-created holders enter the CRUD pipeline along with original dirty entities. There is **no holder ordering step** anywhere in the current code.

GAP-01's PRD explicitly deferred holder ordering to GAP-06 (FR-009, marked COULD):

> **Holder re-ordering**: Sorting holders into a canonical order after creation is deferred to GAP-06 (LIS Reordering).

### Integration point

After `HolderEnsurer.ensure_holders_for_entities()` returns the combined entity list (line 818 of `session.py`), add a holder reordering step. This runs BEFORE the CRUD pipeline (Phase 1) so that any `SET_PARENT` actions for ordering are queued alongside the creation actions.

However, there is a subtlety: newly created holders have temp GIDs. The `SET_PARENT` actions queued by `reorder_subtasks()` will reference these temp GIDs. The existing `ActionExecutor` already handles temp GID resolution via the `gid_map` populated during CRUD execution. Since actions execute AFTER CRUD (this is the existing contract in `execute_with_actions`), the temp GIDs will have been resolved to real GIDs by the time the SET_PARENT actions fire.

### Where to wire

In `SaveSession.commit_async()`, after the ENSURE_HOLDERS block (line ~818) and before Phase 1 CRUD (line ~823):

```python
# Phase 0.5: REORDER_HOLDERS -- order holders to match HOLDER_KEY_MAP
# Per TDD-GAP-06: Only when holders were ensured and parent has HOLDER_KEY_MAP
if self._auto_create_holders and dirty_entities:
    from autom8_asana.persistence.reorder import compute_reorder_plan
    self._reorder_holders_for_entities(dirty_entities)
```

The `_reorder_holders_for_entities` private method:

```python
def _reorder_holders_for_entities(self, entities: list[AsanaResource]) -> None:
    """Queue SET_PARENT actions to order holders per HOLDER_KEY_MAP.

    Per TDD-GAP-06 Section 7: Scans entities for parents with HOLDER_KEY_MAP,
    collects their populated holders, and calls reorder_subtasks() to queue
    the minimum moves.

    Args:
        entities: Combined dirty entities (original + newly created holders).
    """
    from autom8_asana.persistence.reorder import compute_reorder_plan

    seen_parents: set[int] = set()

    for entity in entities:
        holder_key_map = getattr(entity, "HOLDER_KEY_MAP", None)
        if not holder_key_map or id(entity) in seen_parents:
            continue
        seen_parents.add(id(entity))

        # Build current_order: holders in whatever order they currently exist
        # Build desired_order: holders in HOLDER_KEY_MAP key order
        current_holders: list[AsanaResource] = []
        desired_holders: list[AsanaResource] = []

        for holder_key in holder_key_map:
            holder = getattr(entity, f"_{holder_key}", None)
            if holder is not None:
                desired_holders.append(holder)

        if len(desired_holders) <= 1:
            continue

        # current_order is the same set of holders but we don't know Asana's
        # actual order without an API call. For newly-created holders (all temp
        # GIDs), Asana will place them in creation order which matches the
        # HOLDER_KEY_MAP iteration order of HolderEnsurer. For existing holders
        # we optimistically assume they MAY already be in order.
        #
        # Since we cannot know the true current Asana order without fetching,
        # and the PRD says "the caller provides current_order", the GAP-01
        # integration should only reorder when the caller explicitly provides
        # the current order. For the initial integration, we skip automatic
        # reordering during commit and expose the utility for explicit use.
        #
        # The wiring point is documented here for the principal-engineer to
        # implement when a caller (e.g., Business.save()) provides both orders.
```

**Architect decision:** The GAP-01 auto-reorder during commit is **not wired in Phase 1**. The reason is that determining the "current order" of holders in Asana requires an API fetch that the PRD explicitly says is out of scope (Non-Goal #4: "Current order fetching"). The `compute_reorder_plan()` utility and `SaveSession.reorder_subtasks()` wrapper are fully functional and available for explicit use. A consumer who has hydrated a Business (and therefore knows the current holder order from `_populate_holders()`) can call `session.reorder_subtasks()` directly.

**Future integration (post-GAP-06):** After `ensure_holders_for_entities()` returns, the holder order on the parent's private attributes reflects the HOLDER_KEY_MAP iteration order. If the parent was hydrated before the commit, the original holder order is available from the hydration step. A future enhancement can compare hydrated order vs. HOLDER_KEY_MAP order and call `reorder_subtasks()` when they differ.

---

## 8. structlog Events

| Event | Level | Fields | When |
|-------|-------|--------|------|
| `reorder_plan_computed` | info | `parent_gid`, `total_children`, `lis_length`, `moves_required` | After `compute_reorder_plan()` returns with >0 moves |
| `move_planned` | debug | `item` (gid), `reference` (gid), `direction` | For each Move queued via `set_parent()` |

Use `autom8y_log.get_logger(__name__)` at module level in both `reorder.py` and the SaveSession wrapper.

---

## 9. Error Handling

| Condition | Behavior |
|-----------|----------|
| `current_order` and `desired_order` have different gids | `ValueError` with descriptive message listing the difference |
| Duplicate gids in either list | `ValueError` |
| Empty or single-element lists | Return `ReorderPlan((), N, N)` with zero moves |
| Elements in desired_order not in current_order | `ValueError` (same as "different gids") |

No try/except wrapping in `compute_reorder_plan()` -- it is a pure function and should raise immediately on invalid input. The caller (`SaveSession.reorder_subtasks()` or direct consumer) decides error policy.

---

## 10. Test Strategy

All tests in `tests/unit/persistence/test_reorder.py`.

### Unit test matrix

| Test | SC | Input | Expected |
|------|----|-------|----------|
| `test_already_sorted_zero_moves` | SC-001 | 7 items in order | `moves == (), lis_length == 7` |
| `test_partially_sorted_minimum_moves` | SC-002 | 7 items, 5 in order, 2 out | `len(moves) == 2, lis_length == 5` |
| `test_fully_reversed_n_minus_1_moves` | SC-003 | 7 items reversed | `len(moves) == 6, lis_length == 1` |
| `test_moves_produce_desired_order` | SC-004 | Various inputs | Apply moves to mock list, assert == desired |
| `test_empty_input_zero_moves` | SC-005 | `[]` | `ReorderPlan((), 0, 0)` |
| `test_single_element_zero_moves` | SC-005 | `[a]` | `ReorderPlan((), 1, 1)` |
| `test_two_elements_swapped` | - | `[b, a]` desired `[a, b]` | 1 move |
| `test_mismatched_elements_raises` | - | Different gids | `ValueError` |
| `test_duplicate_gids_raises` | - | Same gid twice | `ValueError` |

### Hypothesis property-based test

```python
from hypothesis import given
from hypothesis import strategies as st

@given(st.permutations(st.lists(st.integers(min_value=0, max_value=99), min_size=0, max_size=20, unique=True)))
def test_property_moves_produce_desired_order(perm):
    """For any permutation, applying generated moves to the input produces the sorted output."""
    # Build AsanaResource-like objects with gid = str(value)
    # current_order = perm
    # desired_order = sorted(perm)
    # plan = compute_reorder_plan(current_order, desired_order)
    # simulate applying moves to current_order
    # assert result == desired_order
```

The exact Hypothesis strategy: generate a list of unique integers, use that as the desired order (sorted), generate a random permutation of that list as the current order. Apply the computed moves to the current order and assert the result matches desired order.

### Move simulation for SC-004 and property test

To verify moves produce the desired order, implement a test helper:

```python
def apply_moves(current: list[AsanaResource], moves: tuple[Move, ...]) -> list[AsanaResource]:
    """Simulate applying reorder moves to a list."""
    result = list(current)
    for move in moves:
        # Remove item from current position
        result.remove(move.item)
        # Find reference position
        ref_idx = result.index(move.reference)
        # Insert relative to reference
        if move.direction == "insert_after":
            result.insert(ref_idx + 1, move.item)
        else:
            result.insert(ref_idx, move.item)
    return result
```

### SaveSession integration test

Test that `session.reorder_subtasks()` queues the correct number of `SET_PARENT` `ActionOperation` entries on `_pending_actions`:

```python
def test_reorder_subtasks_queues_set_parent_actions():
    # Create mock session, 7 mock AsanaResource holders
    # Call session.reorder_subtasks(parent, current, desired)
    # Assert len(session._pending_actions) == expected_moves
    # Assert all actions have ActionType.SET_PARENT
    # Assert each action has correct insert_before or insert_after
```

---

## 11. File Layout

```
src/autom8_asana/persistence/reorder.py     # New file: ~100 LOC
    - Move (dataclass)
    - ReorderPlan (dataclass)
    - _compute_lis_indices(position_sequence) -> set[int]
    - compute_reorder_plan(current_order, desired_order) -> ReorderPlan

src/autom8_asana/persistence/session.py      # Edit: ~25 LOC added
    - SaveSession.reorder_subtasks()          # New method, after reorder_subtask()

tests/unit/persistence/test_reorder.py       # New file: ~200 LOC
    - All tests from Section 10
```

---

## 12. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LIS correctness bug | Low | Wrong elements moved | Pure function is trivially testable; Hypothesis catches edge cases |
| Reference element instability | Low | Move references an element that is also moving | Algorithm processes non-LIS elements in desired order and uses "placed" set; references are guaranteed stable |
| Temp GID resolution for SET_PARENT | Low | Action fails because GID not yet resolved | Actions execute after CRUD per existing contract; temp GIDs are resolved in the gid_map by then |
| Over-engineering for 7-element lists | Medium | Complexity disproportionate to scale | Module is ~100 LOC; the algorithm is well-known and concise |

---

## 13. ADR: Deferred GAP-01 Auto-Reorder

**Context:** GAP-01 (FR-009) deferred holder ordering to GAP-06. The natural integration point is after `HolderEnsurer.ensure_holders_for_entities()` in `commit_async()`. However, determining the current Asana order of holders requires either an API fetch (explicitly out of scope per PRD Non-Goal #4) or relying on the hydration state of the parent entity.

**Decision:** Ship `compute_reorder_plan()` and `SaveSession.reorder_subtasks()` as standalone, explicitly-invoked APIs. Do NOT auto-wire into `commit_async()` for Phase 1. Consumers who have hydrated parents (and therefore know current holder order) can call `reorder_subtasks()` directly.

**Rationale:**
1. The PRD says the caller provides both `current_order` and `desired_order` (OQ-2 resolution).
2. Adding an implicit API fetch during commit violates the "no hidden I/O" principle.
3. Newly-created holders (all temp GIDs, no existing Asana order) are created in HOLDER_KEY_MAP iteration order by HolderEnsurer, so they naturally appear in the canonical order. No reorder needed for the pure-creation case.
4. The only case needing reorder is when existing holders are already in Asana but in wrong order. That case requires hydration first, which means the caller already has the current order.

**Consequences:** Consumers must explicitly call `session.reorder_subtasks()` when they want ordering. This is one additional line of code at the call site. A future PR can add auto-wiring if the pattern proves common.

---

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| This TDD | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/TDD-GAP-06-lis-reordering.md` | Written |
| PRD (source) | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-GAP-06-lis-reordering.md` | Read |
| Stakeholder Decisions | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/stakeholder-decisions-GAP-06-lis-reordering.md` | Read |
| SaveSession | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py` | Read |
| Business.HOLDER_KEY_MAP | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/business.py` | Read |
| Unit.HOLDER_KEY_MAP | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/unit.py` | Read |
| HolderEnsurer | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/holder_ensurer.py` | Read |
| ActionOperation / ActionType | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/models.py` | Read |
| AsanaResource base | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/base.py` | Read |
| Task.parent (NameGid) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py` | Read |
| Holder construction | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/holder_construction.py` | Read |
| GAP-01 PRD (FR-009 deferred) | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-GAP-01-hierarchical-save.md` | Read |
