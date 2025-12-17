# ADR-HARDENING-A-004: Minimal Stub Model Pattern

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-16
- **Deciders**: SDK Team
- **Related**: PRD-HARDENING-A, TDD-HARDENING-A, ADR-0050 (Holder Lazy Loading)

## Context

Per Discovery Issue 12, three stub holders return untyped `Task` children:

| Holder | Current Return | Problem |
|--------|---------------|---------|
| `DNAHolder` | `list[Task]` | No type hints for IDE/mypy |
| `ReconciliationsHolder` | `list[Task]` | Users get `Task` instead of domain type |
| `VideographyHolder` | `list[Task]` | Navigation to parent holder unclear |

The PRD requires creating minimal typed models (`DNA`, `Reconciliation`, `Videography`) so that:

1. `business.dna_holder.children` returns `list[DNA]` (typed)
2. Type checkers provide accurate completions
3. Bidirectional navigation works (child to holder, child to business)

However, these entities have unknown custom fields (domain not defined), so models must be minimal.

### Forces at Play

1. **Type safety**: `list[DNA]` is better than `list[Task]` for IDE/mypy
2. **Navigation**: Children should navigate to parent holder and root Business
3. **Unknown domain**: We do not know what custom fields DNA/Reconciliation/Videography have
4. **Consistency**: Follow existing patterns from Contact, AssetEdit models
5. **Future extensibility**: Allow adding typed fields later without breaking changes
6. **Minimal scope**: PRD explicitly excludes custom field accessors

## Decision

**Create minimal `BusinessEntity` subclasses for DNA, Reconciliation, and Videography with bidirectional navigation only. No custom field accessors.**

### Model Pattern

```python
# models/business/dna.py
"""DNA entity - minimal typed model for DNAHolder children.

Per ADR-HARDENING-A-004: Minimal stub model pattern.
Custom field accessors may be added when domain model is defined.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import PrivateAttr

from autom8_asana.models.business.base import BusinessEntity

if TYPE_CHECKING:
    from autom8_asana.models.business.business import Business, DNAHolder


class DNA(BusinessEntity):
    """DNA entity - child of DNAHolder.

    Minimal typed model providing:
    - Type-safe return from DNAHolder.children
    - Bidirectional navigation to parent holder and root Business
    - Inheritance from BusinessEntity for consistency

    Custom field accessors are intentionally omitted until
    the DNA domain model is defined.

    Example:
        # Access typed DNA children
        for dna in business.dna_holder.children:
            print(f"DNA: {dna.name}")  # dna is DNA, not Task
            print(f"Parent: {dna.business.name}")  # Navigate to root

    Navigation:
        dna.dna_holder -> DNAHolder (parent holder)
        dna.business -> Business (root entity)
    """

    # Private navigation references (ADR-0052)
    _dna_holder: DNAHolder | None = PrivateAttr(default=None)
    _business: Business | None = PrivateAttr(default=None)

    @property
    def dna_holder(self) -> DNAHolder | None:
        """Navigate to parent DNAHolder.

        Returns:
            Parent DNAHolder or None if not populated.
        """
        return self._dna_holder

    @property
    def business(self) -> Business | None:
        """Navigate to root Business.

        Returns:
            Root Business or None if not populated.
        """
        return self._business
```

### Holder Updates

```python
# models/business/business.py (updated DNAHolder)
from autom8_asana.models.business.dna import DNA

class DNAHolder(Task, HolderMixin[DNA]):
    """Holder task containing DNA children.

    Per ADR-HARDENING-A-004: Returns typed DNA instances.
    """

    CHILD_TYPE: ClassVar[type[DNA]] = DNA  # Updated from Task
    _children: list[DNA] = PrivateAttr(default_factory=list)
    _business: Business | None = PrivateAttr(default=None)

    @property
    def children(self) -> list[DNA]:  # Updated return type
        """All DNA children (typed)."""
        return self._children

    @property
    def business(self) -> Business | None:
        """Navigate to parent Business."""
        return self._business

    def _populate_children(self, subtasks: list[Task]) -> None:
        """Populate DNA children from fetched subtasks."""
        sorted_tasks = sorted(
            subtasks,
            key=lambda t: (t.created_at or "", t.name or ""),
        )

        self._children = []
        for task in sorted_tasks:
            dna = DNA.model_validate(task.model_dump())
            dna._dna_holder = self
            dna._business = self._business
            self._children.append(dna)

    def invalidate_cache(self) -> None:
        """Invalidate children cache."""
        self._children = []
```

### What Minimal Models Include

| Feature | Included | Rationale |
|---------|----------|-----------|
| `BusinessEntity` inheritance | Yes | Consistent base class |
| `_holder` private attr | Yes | Bidirectional navigation |
| `_business` private attr | Yes | Root navigation |
| `holder` property | Yes | Public navigation API |
| `business` property | Yes | Public navigation API |
| Custom field accessors | **No** | Domain unknown |
| Inner `Fields` class | **No** | No known fields |
| Inner `CascadingFields` | **No** | No cascade definitions |
| `from_gid_async` override | **No** | Use base class method |

### What Minimal Models Exclude

Per PRD FR-STUB-010, minimal models explicitly do NOT include:

```python
# NOT included - custom field accessors
@property
def some_field(self) -> str | None:
    return self.get_custom_fields().get("Some Field")

# NOT included - field name constants
class Fields:
    SOME_FIELD = "Some Field"

# NOT included - cascading field definitions
class CascadingFields:
    SOME_FIELD = CascadingFieldDef(...)
```

## Rationale

### Why Separate Files?

Each model in its own file (`dna.py`, `reconciliation.py`, `videography.py`) because:
1. **Consistency**: Matches Contact, AssetEdit, Location, etc.
2. **Import hygiene**: Avoids circular imports
3. **Future extensibility**: Easy to add fields without modifying large files
4. **Code organization**: Clear ownership of each entity

### Why BusinessEntity Over Task?

```python
# BusinessEntity provides:
class BusinessEntity(Task):
    NAME_CONVENTION: ClassVar[str]
    PRIMARY_PROJECT_GID: ClassVar[str | None]
    get_cascading_fields() -> list[CascadingFieldDef]
    get_inherited_fields() -> list[InheritedFieldDef]
```

Even without custom fields, inheriting from BusinessEntity:
- Signals these are domain entities, not raw Tasks
- Allows adding field definitions later without hierarchy changes
- Maintains consistency with Contact, Unit, Offer, etc.

### Why Private Attrs for Navigation?

Per ADR-0052, navigation references are private (`_dna_holder`) with public properties (`dna_holder`) because:
1. **Pydantic compatibility**: Private attrs not serialized
2. **Controlled access**: Properties can add validation/caching
3. **Setter control**: Only holder population should set references

## Alternatives Considered

### Alternative 1: Keep as Task (No Typed Models)

- **Description**: Continue returning `list[Task]` from stub holders
- **Pros**: No new code, simpler
- **Cons**: No type safety, poor IDE experience, navigation unclear
- **Why not chosen**: PRD requires typed children for mypy/IDE support

### Alternative 2: Use TypeAlias Only

- **Description**: `DNA = TypeAlias[Task]` without new class
- **Pros**: Zero runtime overhead, simple
- **Cons**: No navigation properties, no future extensibility
- **Why not chosen**: TypeAlias doesn't allow adding properties

### Alternative 3: Full Model with Stub Fields

- **Description**: Create full models with placeholder fields
- **Pros**: Ready for field additions
- **Cons**: Premature, fields unknown, misleading API
- **Why not chosen**: PRD explicitly excludes custom field accessors

### Alternative 4: Generic BusinessStubEntity Base

- **Description**: `class DNA(BusinessStubEntity[DNAHolder])`
- **Pros**: DRY for navigation properties
- **Cons**: Extra abstraction, generics add complexity
- **Why not chosen**: Three classes don't justify new abstraction

## Consequences

### Positive

- **Type safety**: `dna: DNA` is checkable by mypy
- **IDE experience**: Autocomplete shows `dna.dna_holder`, `dna.business`
- **Navigation**: Clear path from any entity to root Business
- **Future-ready**: Fields can be added without breaking changes

### Negative

- **Minimal functionality**: Models are mostly empty wrappers
- **Maintenance**: Three new files to maintain
- **Import overhead**: Slightly larger import graph

### Neutral

- **Performance**: Identical to current (Pydantic model_validate)
- **Testing**: Need tests for holder population with typed children

## Compliance

To ensure this decision is followed:

1. **Model pattern**: New stub models follow DNA/Reconciliation/Videography pattern
2. **No premature fields**: Do not add field accessors until domain is defined
3. **Export in `__init__.py`**: All new models exported from `models/business/`
4. **Tests**: Verify `children` returns typed instances with correct navigation

## File Structure

```
src/autom8_asana/models/business/
    __init__.py          # Add DNA, Reconciliation, Videography exports
    dna.py               # NEW: DNA minimal model
    reconciliation.py    # NEW: Reconciliation minimal model
    videography.py       # NEW: Videography minimal model
    business.py          # UPDATE: DNAHolder, ReconciliationsHolder, VideographyHolder
```

## Example Usage

```python
from autom8_asana.models.business import Business, DNA, Reconciliation, Videography

async def process_business(client, gid: str) -> None:
    business = await Business.from_gid_async(client, gid)

    # Type-safe iteration
    for dna in business.dna_holder.children:  # list[DNA]
        print(f"DNA: {dna.name}")
        assert dna.business == business  # Navigate to root

    for recon in business.reconciliations_holder.children:  # list[Reconciliation]
        print(f"Reconciliation: {recon.name}")

    for video in business.videography_holder.children:  # list[Videography]
        print(f"Videography: {video.name}")
```
