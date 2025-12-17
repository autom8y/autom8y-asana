# Discovery Document: Business Model Implementation

**Document ID**: DISCOVERY-BIZMODEL-001
**Date**: 2025-12-11
**Session**: Session 1 of Business Model Initiative
**Author**: Requirements Analyst (via Orchestrator)

---

## Executive Summary

This discovery document analyzes the autom8_asana SDK codebase and business model skills to establish the implementation strategy for the Business Model layer. The analysis confirms that the SDK provides a solid foundation for extension, and the pre-existing architecture decisions (ADR-0050 through ADR-0054) are implementable with **minimal modification** to existing code.

**Key Finding**: SaveSession requires **extension** (new methods), not **modification** (changing existing behavior). The Task model is designed for subclassing. CustomFieldAccessor already provides the change tracking infrastructure needed.

---

## 1. SDK Extension Strategy

### 1.1 Task Model Analysis

**File**: `src/autom8_asana/models/task.py` (157 lines)

**Extension Points Identified**:

| Extension Point | Pattern | Usage |
|-----------------|---------|-------|
| Class inheritance | `class Business(Task)` | All business models inherit from Task |
| `PrivateAttr` fields | `_custom_fields_accessor: CustomFieldAccessor = PrivateAttr(...)` | Holder references, cached parent refs |
| `model_dump()` override | `def model_dump(self, **kwargs) -> dict` | Include holder data in serialization |
| `get_custom_fields()` | Returns `CustomFieldAccessor` instance | Foundation for typed property accessors |

**Task Model Features Available**:
- Pydantic v2 with `extra="ignore"` (forward compatible)
- `parent: NameGid | None` field for hierarchy navigation
- `custom_fields: list[dict[str, Any]]` for custom field data
- Built-in change tracking via `_custom_fields_accessor`

**Recommendation**: **Subclass Task directly**. No modifications to `task.py` required.

```python
# Clean extension pattern
class Business(Task):
    HOLDER_KEY_MAP: ClassVar[dict[str, tuple[str, str]]] = {...}
    _contact_holder: ContactHolder | None = PrivateAttr(default=None)

    @property
    def contact_holder(self) -> ContactHolder | None:
        return self._contact_holder
```

### 1.2 CustomFieldAccessor Analysis

**File**: `src/autom8_asana/models/custom_field_accessor.py` (194 lines)

**Key Capabilities**:

| Capability | Method | Notes |
|------------|--------|-------|
| Get by name or GID | `get(name_or_gid, default)` | Case-insensitive name lookup |
| Set by name or GID | `set(name_or_gid, value)` | Tracks modifications |
| Check for changes | `has_changes()` | Returns True if any modifications |
| Serialize changes | `to_list()` | API payload format |
| Name-to-GID resolution | `_resolve_gid()` | Uses local index + optional resolver |

**Integration Pattern for Typed Properties**:

```python
@property
def company_id(self) -> str | None:
    return self.get_custom_fields().get("Company ID")

@company_id.setter
def company_id(self, value: str | None) -> None:
    self.get_custom_fields().set("Company ID", value)
```

**Finding**: CustomFieldAccessor handles:
- Name-to-GID resolution (case-insensitive)
- Change tracking (via `_modifications` dict)
- API serialization (via `to_list()`)

**Recommendation**: **Use existing CustomFieldAccessor without modification**. Typed properties delegate to `get_custom_fields().get/set()`.

### 1.3 SaveSession Analysis

**File**: `src/autom8_asana/persistence/session.py` (1544 lines)

**Current Capabilities**:

| Feature | Status | Notes |
|---------|--------|-------|
| `track(entity)` | Exists | Returns entity for chaining |
| `untrack(entity)` | Exists | Remove from tracking |
| `delete(entity)` | Exists | Mark for deletion |
| `commit_async()` | Exists | Execute CRUD + actions |
| `preview()` | Exists | Returns (crud_ops, action_ops) |
| Action operations | Exists | add_tag, set_parent, etc. |

**Required Extensions** (new methods, not modifications):

| Extension | Type | Impact |
|-----------|------|--------|
| `track(entity, prefetch_holders=True)` | Extend signature | Add optional parameter |
| `track(entity, recursive=True)` | Extend signature | Add optional parameter |
| `cascade_field(entity, field_name)` | New method | Queue cascade operation |
| `_pending_cascades` | New attribute | Store pending cascades |
| `CascadeExecutor` | New class | Execute cascades in batch |

**Recommendation**: **Extend SaveSession.track() signature and add new methods**. Existing behavior unchanged for `track(entity)` with no parameters.

```python
def track(
    self,
    entity: T,
    *,
    prefetch_holders: bool = False,  # NEW
    recursive: bool = False,  # NEW
) -> T:
    """Track entity with optional holder prefetch and recursive tracking."""
    self._ensure_open()
    self._tracker.track(entity)

    # NEW: Handle prefetch
    if prefetch_holders and hasattr(entity, 'HOLDER_KEY_MAP'):
        self._pending_prefetch.append(entity)

    # NEW: Handle recursive
    if recursive:
        self._track_recursive(entity)

    return entity
```

---

## 2. Field Mapping Analysis

### 2.1 Current Dataframe Schema Fields

**Existing field definitions in SDK**:

| Schema | File | Columns |
|--------|------|---------|
| BASE | `schemas/base.py` | 12 (gid, name, type, date, created, etc.) |
| CONTACT | `schemas/contact.py` | 9 Contact-specific (full_name, nickname, contact_phone, etc.) |
| UNIT | `schemas/unit.py` | 11 Unit-specific (mrr, weekly_ad_spend, products, etc.) |

**Dataframe Schema Pattern** (uses `cf:` prefix for dynamic resolution):
```python
ColumnDef(
    name="mrr",
    dtype="Decimal",
    source="cf:MRR",  # Resolves to custom field "MRR"
)
```

### 2.2 Skills Documentation Field Count

| Entity | Documented Fields | Schema Fields | Gap |
|--------|-------------------|---------------|-----|
| Business | 19 | 0 | +19 (all new) |
| Contact | 19 | 9 | +10 (missing fields) |
| Unit | 31 | 11 | +20 (missing fields) |
| Address | 12 | 0 | +12 (all new) |
| Hours | 7 | 0 | +7 (all new) |
| Offer | 39 | 0 | +39 (all new) |
| **Total** | **127** | **20** | **+107** |

**Finding**: The skills documentation provides comprehensive field definitions. The dataframe schemas are a subset used for DataFrame exports, not the full business model.

### 2.3 Field Type Patterns

From `custom-fields-glossary.md`:

| Type | Pattern | Example |
|------|---------|---------|
| Text | Direct string return | `return accessor.get("Company ID")` |
| Number | Convert to Decimal | `Decimal(str(accessor.get("MRR")))` |
| Enum | Extract `name` from dict | `value.get("name") if isinstance(value, dict) else value` |
| Multi-enum | Extract list of names | `[v.get("name") for v in value if isinstance(v, dict)]` |
| People | Return list of dicts | `return accessor.get("Rep") or []` |
| Date | Return as-is | `return accessor.get("Date Value")` |

---

## 3. SaveSession Modification Scope

### 3.1 Modification vs. Wrapper Analysis

| Approach | Pros | Cons |
|----------|------|------|
| **Modify session.py** | Single source of truth | Risk of breaking existing code |
| **Wrapper class** | No risk to existing code | Two classes to maintain |
| **Extend via parameters** | Backward compatible, single class | Slight complexity increase |

**Recommendation**: **Extend via optional parameters**. This is the approach used by existing action operations (add_tag has optional `extra_params`).

### 3.2 Required Changes to SaveSession

**Changes in `session.py`**:

```python
class SaveSession:
    def __init__(self, ...):
        # Existing init
        self._pending_prefetch: list[AsanaResource] = []  # NEW
        self._pending_cascades: list[CascadeOperation] = []  # NEW

    def track(
        self,
        entity: T,
        *,
        prefetch_holders: bool = False,  # NEW parameter
        recursive: bool = False,  # NEW parameter
    ) -> T:
        # Existing logic unchanged when params are False
        ...

    def cascade_field(  # NEW method
        self,
        entity: AsanaResource,
        field_name: str,
        *,
        target_types: set[type] | None = None,
    ) -> SaveSession:
        ...

    async def commit_async(self) -> SaveResult:
        # Add prefetch step before validation
        await self._execute_prefetch()  # NEW

        # Existing CRUD execution
        ...

        # Add cascade execution after CRUD
        await self._execute_cascades()  # NEW
```

**New files needed**:

| File | Purpose |
|------|---------|
| `persistence/cascade.py` | `CascadeOperation`, `CascadeExecutor` classes |
| `models/business/__init__.py` | Business model package |
| `models/business/base.py` | `BusinessTask` base with HOLDER_KEY_MAP support |
| `models/business/fields.py` | `CascadingFieldDef`, `InheritedFieldDef` dataclasses |

### 3.3 Backward Compatibility Verification

**Existing tests that must pass** (from `tests/unit/persistence/`):

| Test File | Count | Risk |
|-----------|-------|------|
| `test_session.py` | ~50 tests | LOW - parameters are optional |
| `test_tracker.py` | ~30 tests | NONE - no changes |
| `test_graph.py` | ~20 tests | NONE - no changes |
| `test_pipeline.py` | ~25 tests | LOW - cascade is additive |

**Recommendation**: Run existing test suite after each change to verify backward compatibility.

---

## 4. Risk Assessment

### 4.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SaveSession changes break existing code | LOW | HIGH | Optional parameters, extensive tests |
| Circular imports in model hierarchy | MEDIUM | MEDIUM | TYPE_CHECKING imports, forward refs |
| Custom field GIDs vary between environments | HIGH | MEDIUM | Resolve by name at runtime (already supported) |
| Cascade batch API hits rate limits | MEDIUM | MEDIUM | Use existing BatchClient with chunking |
| Large hierarchies exhaust memory | LOW | MEDIUM | Document limits, provide streaming option |

### 4.2 Implementation Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Holder detection fails on renamed tasks | LOW | MEDIUM | Emoji fallback, validation on track |
| Cached refs become stale | MEDIUM | LOW | Document session-scoped validity |
| Developer forgets cascade_field() | HIGH | MEDIUM | Lint rule, documentation |

---

## 5. Open Questions Resolution

### 5.1 From Prompt 0

| # | Question | Resolution | Rationale |
|---|----------|------------|-----------|
| 1 | **Holder stub models**: Should DNA, Reconciliations, AssetEdit, Videography holders be fully implemented or stubbed? | **Stub** - Return as plain Task | Not in primary workflow, can extend later |
| 2 | **Process subclasses**: Confirm 24+ Process subclasses remain out of scope (Phase 2) | **Confirmed** - Out of scope | Skills explicitly document this as Phase 2 |
| 3 | **Field GID resolution**: At model definition time or runtime? | **Runtime** - CustomFieldAccessor handles this | Existing pattern, environment-agnostic |
| 4 | **Missing field definitions**: Are all 18/21/44 fields documented? | **Yes** - Skills provide comprehensive definitions | See `custom-fields-glossary.md` |
| 5 | **SaveSession changes**: Modifications or wrappers? | **Extensions** - Optional parameters + new methods | Backward compatible, single class |
| 6 | **Existing tests**: Tests that must pass, or greenfield? | **Must pass** - ~125 persistence tests exist | Run pytest after each change |

### 5.2 New Questions for Architecture Session

| # | Question | Owner | Resolution Needed By |
|---|----------|-------|---------------------|
| 1 | Should `Business.from_gid()` be async factory method or classmethod? | Architect | Session 3 |
| 2 | How should holder children be sorted (by name, created_at, custom field)? | Architect | Session 3 |
| 3 | Should cascade errors fail the entire commit or be partial? | Architect | Session 3 |
| 4 | CascadeReconciler: implement in Phase 1 or defer? | Architect | Session 3 |

---

## 6. Implementation Recommendations

### 6.1 Package Structure

```
src/autom8_asana/
+-- models/
|   +-- business/
|   |   +-- __init__.py          # Public exports
|   |   +-- base.py              # BusinessTask mixin with HOLDER_KEY_MAP
|   |   +-- business.py          # Business(Task)
|   |   +-- contact.py           # Contact(Task), ContactHolder(Task)
|   |   +-- unit.py              # Unit(Task), UnitHolder(Task)
|   |   +-- offer.py             # Offer(Task), OfferHolder(Task)
|   |   +-- process.py           # Process(Task), ProcessHolder(Task)
|   |   +-- location.py          # Location/Address(Task), LocationHolder(Task)
|   |   +-- hours.py             # Hours(Task)
|   |   +-- fields.py            # CascadingFieldDef, InheritedFieldDef, enums
|   +-- task.py                  # Existing (unchanged)
+-- persistence/
|   +-- session.py               # Extend with prefetch/recursive/cascade
|   +-- cascade.py               # NEW: CascadeOperation, CascadeExecutor
```

### 6.2 Implementation Sequence

| Phase | Components | Dependencies |
|-------|------------|--------------|
| **P1** | Business, ContactHolder, Contact | Task model |
| **P2** | UnitHolder, Unit, OfferHolder, Offer, ProcessHolder, Process | P1 |
| **P3** | LocationHolder, Address, Hours, cascade infrastructure | P1, P2 |

### 6.3 Testing Strategy

| Test Type | Target | Tools |
|-----------|--------|-------|
| Unit tests | Model construction, field accessors | pytest |
| Integration tests | SaveSession with business models | pytest-asyncio, fixtures |
| Type safety | All business model code | mypy |
| Coverage | >80% on business model code | pytest-cov |

---

## 7. Artifacts for Next Session

### 7.1 Inputs to PRD (Session 2)

- Field definitions from `custom-fields-glossary.md` (127 fields)
- Model structures from skills documentation
- SaveSession extension requirements
- Acceptance criteria patterns from ADR-0050 through ADR-0054

### 7.2 Inputs to TDD (Session 3)

- Package structure recommendation
- SaveSession modification scope
- Risk assessment and mitigations
- New questions requiring architectural decision

---

## 8. Session 1 Completion Checklist

- [x] Task model extension points analyzed
- [x] CustomFieldAccessor integration requirements understood
- [x] SaveSession modification scope defined
- [x] Field definitions extracted from skills (127 fields)
- [x] Existing patterns documented
- [x] Gaps between skills and implementation identified
- [x] Open questions answered
- [x] Risk assessment completed
- [x] Implementation recommendations provided

---

## Appendix A: Field Count Summary

| Entity | Text | Number | Enum | Multi-enum | People | Date | Total |
|--------|------|--------|------|------------|--------|------|-------|
| Business | 13 | 1 | 4 | 0 | 1 | 0 | 19 |
| Contact | 15 | 0 | 4 | 0 | 0 | 0 | 19 |
| Unit | 17 | 10 | 3 | 4 | 0 | 0 | 31* |
| Address | 11 | 2 | 0 | 0 | 0 | 0 | 12* |
| Hours | 7 | 0 | 0 | 0 | 0 | 0 | 7 |
| Offer | 25 | 7 | 5 | 2 | 1 | 0 | 39* |
| **Total** | **88** | **20** | **16** | **6** | **2** | **0** | **127** |

*Some fields have Boolean type (counted as Number for simplicity)

---

## Appendix B: Cascading Field Summary

| Source | Field | Targets | Allow Override |
|--------|-------|---------|----------------|
| Business | Office Phone | Unit, Offer, Process, Contact | NO |
| Business | Company ID | All descendants | NO |
| Business | Business Name | Unit, Offer | NO |
| Business | Primary Contact Phone | Unit, Offer, Process | NO |
| Unit | Platforms | Offer | YES |
| Unit | Vertical | Offer, Process | NO |
| Unit | Booking Type | Offer | NO |

---

*End of Discovery Document*
