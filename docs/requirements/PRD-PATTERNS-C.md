# PRD-PATTERNS-C: Holder Factory with `__init_subclass__`

> Product Requirements Document for Initiative C of the Design Patterns Sprint

**Status**: Active
**Initiative**: Design Patterns Sprint - Initiative C
**Dependencies**: None (benefits from Initiative A's descriptor familiarity)
**Estimated Effort**: 1-2 sessions

---

## 1. Problem Statement

The `autom8_asana` SDK contains **4 near-identical holder implementations** (DNAHolder, ReconciliationHolder, AssetEditHolder, VideographyHolder) that share:

- Identical inheritance pattern (`Task, HolderMixin[T]`)
- Identical ClassVar configuration (CHILD_TYPE, PARENT_REF_NAME, CHILDREN_ATTR)
- Identical PrivateAttr declarations (_children, _business)
- Identical property boilerplate (children, business)
- Identical `_populate_children()` implementation (sort, convert, set refs)

Each holder requires ~65-75 lines of code, totaling **~300 lines** of duplicated structure. The only variations are:
1. Child type name (DNA, Reconciliation, AssetEdit, Videography)
2. Parent reference attribute name (_dna_holder, _reconciliation_holder, etc.)
3. Children storage attribute name (some use _children, AssetEditHolder uses _asset_edits)
4. Optional semantic alias properties (reconciliations, asset_edits, videography)

This duplication:
- Increases maintenance burden
- Risks copy-paste errors
- Makes adding new holder types tedious
- Obscures the simple declarative intent

---

## 2. Solution Overview

Implement a **`HolderFactory` base class** using Python's `__init_subclass__` hook that allows declarative holder definitions:

```python
# BEFORE: ~70 lines per holder
class DNAHolder(Task, HolderMixin[Task]):
    CHILD_TYPE: ClassVar[type[Task]] = Task
    PARENT_REF_NAME: ClassVar[str] = "_dna_holder"
    CHILDREN_ATTR: ClassVar[str] = "_children"

    _children: list[Any] = PrivateAttr(default_factory=list)
    _business: Business | None = PrivateAttr(default=None)

    @property
    def children(self) -> list[Any]:
        return self._children

    @property
    def business(self) -> Business | None:
        return self._business

    def _populate_children(self, subtasks: list[Task]) -> None:
        from autom8_asana.models.business.dna import DNA
        self.__class__.CHILD_TYPE = DNA
        sorted_tasks = sorted(subtasks, key=lambda t: (t.created_at or "", t.name or ""))
        self._children = []
        for task in sorted_tasks:
            child = DNA.model_validate(task.model_dump())
            child._dna_holder = self
            child._business = self._business
            self._children.append(child)

# AFTER: 3-5 lines per holder
class DNAHolder(HolderFactory, child_type="DNA", parent_ref="_dna_holder"):
    """Holder for DNA children."""
    pass
```

---

## 3. Requirements

### 3.1 Functional Requirements

#### FR-FACTORY-001: `__init_subclass__` Configuration
The `HolderFactory` base class SHALL accept keyword arguments in class definition:
- `child_type: str` - Name of child class (e.g., "DNA", "Reconciliation")
- `parent_ref: str` - Name of parent reference attribute (e.g., "_dna_holder")
- `children_attr: str` - Name of children storage attribute (default: "_children")
- `semantic_alias: str | None` - Optional alias for children property (e.g., "reconciliations")

**Acceptance Criteria**:
```python
class ReconciliationHolder(
    HolderFactory,
    child_type="Reconciliation",
    parent_ref="_reconciliation_holder",
    semantic_alias="reconciliations"
):
    pass

holder = ReconciliationHolder.model_validate(task_data)
assert holder.children == holder.reconciliations  # Alias works
```

#### FR-FACTORY-002: Auto-Generated ClassVars
`HolderFactory.__init_subclass__` SHALL automatically set:
- `CHILD_TYPE`: Initially `Task`, resolved at runtime
- `PARENT_REF_NAME`: From `parent_ref` argument
- `CHILDREN_ATTR`: From `children_attr` argument (default: "_children")
- `_CHILD_MODULE`: Inferred module path for dynamic import
- `_CHILD_CLASS_NAME`: From `child_type` argument

**Acceptance Criteria**:
```python
class DNAHolder(HolderFactory, child_type="DNA", parent_ref="_dna_holder"):
    pass

assert DNAHolder.PARENT_REF_NAME == "_dna_holder"
assert DNAHolder.CHILDREN_ATTR == "_children"
assert DNAHolder._CHILD_CLASS_NAME == "DNA"
```

#### FR-FACTORY-003: Generic `_populate_children` Implementation
`HolderFactory` SHALL provide a generic `_populate_children()` method that:
1. Dynamically imports child class using `_CHILD_MODULE` and `_CHILD_CLASS_NAME`
2. Sorts subtasks by (created_at, name) for stability
3. Converts Task instances to typed children via `model_validate()`
4. Sets bidirectional references (parent_ref -> self, _business -> self._business)
5. Stores children in the configured children attribute

**Acceptance Criteria**:
```python
holder = DNAHolder.model_validate(task_data)
holder._business = business
holder._populate_children(subtasks)

assert len(holder.children) == len(subtasks)
for child in holder.children:
    assert child._dna_holder is holder
    assert child._business is business
```

#### FR-FACTORY-004: Dynamic Import Resolution
Child class import SHALL be deferred to `_populate_children()` call time to avoid circular imports at class definition time.

**Acceptance Criteria**:
- No circular import errors when importing `HolderFactory` or holder subclasses
- Child classes are correctly resolved at runtime

#### FR-FACTORY-005: Properties Auto-Generation
`HolderFactory` SHALL provide:
- `children: list[Any]` property returning the children list
- `business: Business | None` property returning `_business`
- Optional semantic alias property if `semantic_alias` was provided

**Acceptance Criteria**:
```python
class AssetEditHolder(
    HolderFactory,
    child_type="AssetEdit",
    parent_ref="_asset_edit_holder",
    children_attr="_asset_edits",
    semantic_alias="asset_edits"
):
    pass

holder = AssetEditHolder.model_validate(task_data)
assert holder.children is holder.asset_edits  # Same list
```

#### FR-FACTORY-006: Backward Compatibility
Migrated holders MUST maintain exact same public API:
- Same property names and return types
- Same `_populate_children()` behavior
- Same ClassVar values
- ReconciliationsHolder deprecation alias preserved

**Acceptance Criteria**:
- All existing tests pass without modification
- No changes required to Business hydration code

### 3.2 Non-Functional Requirements

#### NFR-FACTORY-001: Code Reduction
The migration SHALL reduce total holder code by at least 250 lines (80%+ reduction).

#### NFR-FACTORY-002: Type Safety
All generated properties and methods SHALL maintain correct type hints for IDE support.

#### NFR-FACTORY-003: Performance
`__init_subclass__` hook SHALL not introduce measurable performance overhead at class definition time.

#### NFR-FACTORY-004: Extensibility
Adding a new holder type SHOULD require only 3-5 lines of code.

---

## 4. Scope

### 4.1 In Scope
- `HolderFactory` base class with `__init_subclass__` hook
- Migration of DNAHolder to HolderFactory pattern
- Migration of ReconciliationHolder to HolderFactory pattern
- Migration of AssetEditHolder to HolderFactory pattern
- Migration of VideographyHolder to HolderFactory pattern
- ReconciliationsHolder deprecation alias preservation
- Comprehensive test coverage

### 4.2 Out of Scope
- ContactHolder (has business-specific `owner` property logic)
- UnitHolder (works well with inherited `_populate_children`)
- OfferHolder/ProcessHolder (require intermediate `_unit` reference logic)
- LocationHolder (requires special Hours sibling logic)
- Changes to HolderMixin base class

---

## 5. Success Criteria

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| Lines removed | >250 | `wc -l` before/after |
| Test coverage | 100% | pytest-cov on HolderFactory |
| Existing tests | Pass | All holder tests pass unchanged |
| Type check | Pass | mypy --strict passes |
| New holder lines | <10 | Lines required for new holder |

---

## 6. Technical Approach

### 6.1 HolderFactory Class Location
`/src/autom8_asana/models/business/holder_factory.py`

### 6.2 Module Import Convention
Child module inferred from class name: `{child_type.lower()}` -> `autom8_asana.models.business.{module}`

### 6.3 PrivateAttr Handling
- `_children` (or custom attr): `list[Any]` - children storage
- `_business`: `Business | None` - parent business reference

These must be class-level PrivateAttr declarations on HolderFactory, inherited by subclasses.

### 6.4 Semantic Alias Implementation
Generate property at class definition time via `__init_subclass__`:
```python
if semantic_alias:
    setattr(cls, semantic_alias, property(lambda self: self.children))
```

---

## 7. Migration Plan

### Phase 1: Create HolderFactory
1. Create `holder_factory.py` with base implementation
2. Add comprehensive unit tests

### Phase 2: Migrate Holders (in business.py)
1. Replace DNAHolder class with HolderFactory subclass
2. Replace ReconciliationHolder class (preserve deprecation alias)
3. Replace AssetEditHolder class
4. Replace VideographyHolder class

### Phase 3: Validation
1. Run existing test suite
2. Verify hydration still works
3. Verify backward compatibility

---

## 8. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Pydantic inheritance issues | High | Test PrivateAttr inheritance thoroughly |
| Dynamic import failures | Medium | Explicit module mapping fallback |
| `__init_subclass__` complexity | Low | Pattern proven in BusinessEntity |
| Type hint degradation | Medium | Generate .pyi stubs if needed |

---

## 9. References

- **Parent**: PROMPT-MINUS-1-DESIGN-PATTERNS.md (Meta-Initiative)
- **Predecessor**: TDD-PATTERNS-A (Custom Field Descriptors)
- **Architecture**: DESIGN-PATTERN-OPPORTUNITIES.md (Opportunity 3)
- **Related ADRs**: ADR-0082 (Fields auto-generation via `__init_subclass__`)

---

*PRD-PATTERNS-C v1.0 | Design Patterns Sprint Initiative C*
