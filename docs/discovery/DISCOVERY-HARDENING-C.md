# Discovery: Initiative C - Navigation Patterns

> Comprehensive audit of navigation patterns across the SDK's entity types
>
> **Initiative**: C (Navigation Patterns)
> **Prerequisites**: A (Foundation), B (Custom Fields) - Complete
> **Addresses**: Issues 4, 6, 7 from Architecture Hardening

---

## Executive Summary

### Key Findings

| Metric | Value | Assessment |
|--------|-------|------------|
| SDK entity types (core) | 13 | No navigation patterns |
| Business entity types | 10 | Full navigation patterns |
| Distinct navigation implementations | 12 | High duplication |
| Copy-paste code blocks | ~35 | Significant redundancy |
| `_invalidate_refs()` implementations | 12 | Consistent coverage |
| `HOLDER_KEY_MAP` definitions | 2 | Business, Unit only |
| Back-reference patterns | 6 distinct types | Inconsistent naming |
| Lines of duplicated code | ~800+ | Maintenance risk |

### Critical Observations

1. **Two-tier architecture**: SDK entities (Task, Project) have NO navigation; Business entities (Contact, Offer) have FULL navigation
2. **No `__getattr__` magic**: Despite documentation, HOLDER_KEY_MAP uses explicit properties, not `__getattr__`
3. **Consistent `_invalidate_refs()`**: All business entities implement it
4. **No auto-invalidation**: Manual invalidation required on hierarchy changes
5. **High copy-paste ratio**: Navigation property implementations are nearly identical across 10+ entities

---

## 1. Navigation Property Inventory

### 1.1 SDK Core Entities (No Navigation)

These entities use `NameGid` references without navigation capabilities:

| Entity | Reference Fields | Navigation Properties | Assessment |
|--------|------------------|----------------------|------------|
| `Task` | `parent`, `projects`, `assignee`, `workspace` | None | Static refs only |
| `Project` | `owner`, `team`, `workspace` | None | Static refs only |
| `Section` | `project` | None | Static refs only |
| `User` | `workspaces` | None | Static refs only |
| `Workspace` | None | None | Root entity |
| `Team` | `organization` | None | Static refs only |
| `Tag` | `workspace`, `followers` | None | Static refs only |
| `Goal` | `owner`, `workspace`, `team` | None | Static refs only |
| `Portfolio` | `owner`, `workspace` | None | Static refs only |
| `Story` | `target`, `created_by` | None | Static refs only |
| `Attachment` | `parent`, `created_by` | None | Static refs only |
| `Webhook` | `resource` | None | Static refs only |
| `CustomField` | `workspace` | None | Static refs only |

**Finding**: All 13 SDK core entities use `NameGid` for references. No lazy loading, no caching, no invalidation needed.

### 1.2 Business Entities (Full Navigation)

| Entity | Navigation Properties | Back-References | `_invalidate_refs()` |
|--------|----------------------|-----------------|---------------------|
| `Business` | 7 holder properties + convenience shortcuts | None (root) | No |
| `Contact` | `business`, `contact_holder` | `_business`, `_contact_holder` | Yes |
| `Unit` | `business`, `unit_holder`, `offer_holder`, `process_holder` | `_business`, `_unit_holder`, etc. | Yes |
| `Offer` | `business`, `unit`, `offer_holder` | `_business`, `_unit`, `_offer_holder` | Yes |
| `Process` | `business`, `unit`, `process_holder` | `_business`, `_unit`, `_process_holder` | Yes |
| `Location` | `business`, `location_holder` | `_business`, `_location_holder` | Yes |
| `Hours` | `business`, `location_holder` | `_business`, `_location_holder` | Yes |
| `DNA` | `business` | `_business`, `_dna_holder` | Yes |
| `Reconciliation` | `business` | `_business`, `_reconciliations_holder` | Yes |
| `AssetEdit` | `business` | `_business`, `_asset_edit_holder` | Yes |
| `Videography` | `business` | `_business`, `_videography_holder` | Yes |

**Finding**: All 11 business entities implement full bidirectional navigation with cached back-references.

---

## 2. Copy-Paste Detection Analysis

### 2.1 Navigation Property Pattern (HIGH DUPLICATION)

The following pattern is duplicated across 10 entities:

```python
# Pattern: Upward navigation with lazy resolution
@property
def business(self) -> Business | None:
    """Navigate to containing Business (cached)."""
    if self._business is None and self._<holder> is not None:
        self._business = self._<holder>._business
    return self._business
```

**Occurrences**:
- `contact.py:100-111` - Contact.business
- `unit.py:229-241` - Unit.business
- `offer.py:163-175` - Offer.business
- `process.py:159-172` - Process.business
- `location.py:60-71` - Location.business
- `hours.py:60-69` - Hours.business

Each implementation is 10-15 lines with minor variations in holder reference name.

### 2.2 _invalidate_refs() Pattern (HIGH DUPLICATION)

```python
# Pattern: Clear all cached references
def _invalidate_refs(self) -> None:
    """Invalidate cached references on hierarchy change."""
    self._business = None
    self._<holder> = None
    # Additional refs if present
```

**Occurrences**:
- `contact.py:122-128`
- `unit.py:251-259`
- `offer.py:177-184`
- `process.py:174-181`
- `location.py:82-88`
- `hours.py:80-86`
- `dna.py:61-64`
- `reconciliation.py:61-64`
- `videography.py:61-64`
- `asset_edit.py:107-114`

### 2.3 _populate_children() Pattern (HIGH DUPLICATION)

```python
# Pattern: Convert Task to typed children with refs
def _populate_children(self, subtasks: list[Task]) -> None:
    sorted_tasks = sorted(
        subtasks,
        key=lambda t: (t.created_at or "", t.name or ""),
    )
    self._children = []
    for task in sorted_tasks:
        child = ChildType.model_validate(task.model_dump())
        child._<holder> = self
        child._business = self._business
        self._children.append(child)
```

**Occurrences** (8 holders):
- `ContactHolder._populate_children` - contact.py:532-551
- `UnitHolder._populate_children` - unit.py:878-897
- `OfferHolder._populate_children` - offer.py:786-806
- `ProcessHolder._populate_children` - process.py:327-347
- `LocationHolder._populate_children` - location.py:262-295
- `DNAHolder._populate_children` - business.py:60-82
- `ReconciliationsHolder._populate_children` - business.py:134-158
- `AssetEditHolder._populate_children` - business.py:210-233
- `VideographyHolder._populate_children` - business.py:285-309

### 2.4 Holder Property Pattern (MODERATE DUPLICATION)

```python
# Pattern: Holder property with None check
@property
def <holder>_holder(self) -> <Holder>Type | None:
    """<Holder>Holder subtask containing <Child> children."""
    return self._<holder>_holder
```

All 7 holder properties on Business follow identical structure.

### 2.5 Duplication Summary

| Pattern | Occurrences | Lines Each | Total Duplicated |
|---------|-------------|------------|------------------|
| Navigation property (business) | 6 | 12 | ~72 |
| Navigation property (holder) | 10 | 8 | ~80 |
| `_invalidate_refs()` | 10 | 8 | ~80 |
| `_populate_children()` | 9 | 20 | ~180 |
| `_set_child_parent_ref()` | 9 | 6 | ~54 |
| Holder property accessor | 9 | 6 | ~54 |
| Custom field getter helpers | 10 | 15 | ~150 |
| Convenience shortcuts | 7 | 8 | ~56 |

**Total Estimated Duplication**: ~800+ lines

---

## 3. HOLDER_KEY_MAP Analysis

### 3.1 Definitions

Only 2 entities define `HOLDER_KEY_MAP`:

**Business.HOLDER_KEY_MAP** (7 entries):
```python
HOLDER_KEY_MAP: ClassVar[dict[str, tuple[str, str]]] = {
    "contact_holder": ("Contacts", "busts_in_silhouette"),
    "unit_holder": ("Units", "package"),
    "location_holder": ("Location", "round_pushpin"),
    "dna_holder": ("DNA", "dna"),
    "reconciliations_holder": ("Reconciliations", "abacus"),
    "asset_edit_holder": ("Asset Edit", "art"),
    "videography_holder": ("Videography", "video_camera"),
}
```

**Unit.HOLDER_KEY_MAP** (2 entries):
```python
HOLDER_KEY_MAP: ClassVar[dict[str, tuple[str, str]]] = {
    "offer_holder": ("Offers", "gift"),
    "process_holder": ("Processes", "gear"),
}
```

### 3.2 Usage Pattern

`HOLDER_KEY_MAP` is used for:
1. **Detection**: `_identify_holder()` matches subtasks to holder types
2. **Iteration**: `_fetch_holders_async()` iterates keys to prefetch
3. **Conditional tracking**: `SaveSession.track()` checks for map presence

### 3.3 NO __getattr__ Magic

**Key Finding**: Despite documentation suggesting `__getattr__` magic, the actual implementation uses **explicit properties**:

```python
# NOT USED: __getattr__ approach
def __getattr__(self, attr: str) -> Any:
    if attr in self.HOLDER_KEY_MAP:
        return self.get_holder(f"_{attr}", self.HOLDER_KEY_MAP[attr])
    raise AttributeError(...)

# ACTUALLY USED: Explicit properties
@property
def contact_holder(self) -> ContactHolder | None:
    return self._contact_holder
```

This is more verbose but provides better type safety and IDE support.

---

## 4. Reference Invalidation Analysis

### 4.1 _invalidate_refs() Coverage

| Entity | Implemented | What It Clears |
|--------|-------------|----------------|
| `BusinessEntity` (base) | Yes (no-op) | Nothing - override required |
| `Contact` | Yes | `_business`, `_contact_holder` |
| `Unit` | Yes | `_business`, `_unit_holder`, `_offer_holder`, `_process_holder` |
| `Offer` | Yes | `_business`, `_unit`, `_offer_holder` |
| `Process` | Yes | `_business`, `_unit`, `_process_holder` |
| `Location` | Yes | `_business`, `_location_holder` |
| `Hours` | Yes | `_business`, `_location_holder` |
| `DNA` | Yes | `_business`, `_dna_holder` |
| `Reconciliation` | Yes | `_business`, `_reconciliations_holder` |
| `AssetEdit` | Yes | `_business`, `_asset_edit_holder` + calls super |
| `Videography` | Yes | `_business`, `_videography_holder` |

### 4.2 Where _invalidate_refs() Is NOT Called

**Critical Gap**: `_invalidate_refs()` is defined but rarely called automatically.

**Call Sites Found**:
- None in SaveSession
- None in hydration code
- Manual call required on parent changes

**Risk**: Stale references if hierarchy mutates without explicit invalidation.

### 4.3 Holder Cache Invalidation

Holders use `invalidate_cache()` (different from entity `_invalidate_refs()`):

| Holder | Method | What It Clears |
|--------|--------|----------------|
| `ContactHolder` | `invalidate_cache()` | `_contacts = []` |
| `UnitHolder` | `invalidate_cache()` | `_units = []` |
| `OfferHolder` | `invalidate_cache()` | `_offers = []` |
| `ProcessHolder` | `invalidate_cache()` | `_processes = []` |
| `LocationHolder` | `invalidate_cache()` | `_locations = []`, `_hours = None` |
| `DNAHolder` | `invalidate_cache()` | `_children = []` |
| `ReconciliationsHolder` | `invalidate_cache()` | `_children = []` |
| `AssetEditHolder` | `invalidate_cache()` | `_asset_edits = []` |
| `VideographyHolder` | `invalidate_cache()` | `_children = []` |

---

## 5. Back-Reference Patterns

### 5.1 Reference Types

| Type | Purpose | Entities Using |
|------|---------|----------------|
| `_business` | Root navigation | All business entities |
| `_contact_holder` | Parent holder | Contact |
| `_unit_holder` | Parent holder | Unit |
| `_offer_holder` | Parent holder | Offer |
| `_process_holder` | Parent holder | Process |
| `_location_holder` | Parent holder | Location, Hours |
| `_dna_holder` | Parent holder | DNA |
| `_reconciliations_holder` | Parent holder | Reconciliation |
| `_asset_edit_holder` | Parent holder | AssetEdit |
| `_videography_holder` | Parent holder | Videography |
| `_unit` | Intermediate navigation | Offer, Process |

### 5.2 Naming Inconsistencies

| Entity | Holder Reference | Business Reference | Notes |
|--------|-----------------|-------------------|-------|
| Contact | `_contact_holder` | `_business` | Standard |
| Unit | `_unit_holder` | `_business` | Standard |
| Offer | `_offer_holder` | `_business` | Also has `_unit` |
| Process | `_process_holder` | `_business` | Also has `_unit` |
| Location | `_location_holder` | `_business` | Standard |
| Hours | `_location_holder` | `_business` | Same as Location |
| DNA | `_dna_holder` | `_business` | Standard |
| Reconciliation | `_reconciliations_holder` | `_business` | Note: plural |
| AssetEdit | `_asset_edit_holder` | `_business` | Standard |
| Videography | `_videography_holder` | `_business` | Standard |

**Inconsistency**: `_reconciliations_holder` uses plural while others use singular.

---

## 6. Recommendations for Architecture

### 6.1 Descriptor-Based Navigation (Priority: High)

Replace copy-paste properties with descriptors:

```python
class ParentRef(Generic[T]):
    """Descriptor for cached upward navigation."""

    def __init__(self, holder_attr: str | None = None):
        self.holder_attr = holder_attr
        self.private_name: str

    def __set_name__(self, owner: type, name: str) -> None:
        self.private_name = f"_{name}"

    def __get__(self, obj: Any, objtype: type | None = None) -> T | None:
        if obj is None:
            return None
        cached = getattr(obj, self.private_name, None)
        if cached is None and self.holder_attr:
            holder = getattr(obj, self.holder_attr, None)
            if holder is not None:
                cached = getattr(holder, '_business', None)
                setattr(obj, self.private_name, cached)
        return cached

# Usage:
class Contact(BusinessEntity):
    business: Business | None = ParentRef(holder_attr="_contact_holder")
```

**Impact**: ~72 lines to ~15 lines for navigation properties.

### 6.2 HolderMixin Enhancement (Priority: High)

Consolidate `_populate_children` into mixin:

```python
class HolderMixin(Generic[T]):
    CHILD_TYPE: ClassVar[type[Task]]
    PARENT_REF_NAME: ClassVar[str]  # e.g., "_contact_holder"
    BUSINESS_REF_NAME: ClassVar[str] = "_business"

    def _populate_children(self, subtasks: list[Task]) -> None:
        sorted_tasks = sorted(subtasks, key=lambda t: (t.created_at or "", t.name or ""))
        children = []
        for task in sorted_tasks:
            child = self.CHILD_TYPE.model_validate(task.model_dump())
            setattr(child, self.PARENT_REF_NAME, self)
            setattr(child, self.BUSINESS_REF_NAME, getattr(self, self.BUSINESS_REF_NAME, None))
            children.append(child)
        self._children_cache = children
```

**Impact**: ~180 lines to ~30 lines.

### 6.3 Auto-Invalidation (Priority: Medium)

Add automatic invalidation on parent changes:

```python
class BusinessEntity(Task):
    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        # Trigger invalidation on hierarchy-changing attrs
        if name in ('parent', '_parent'):
            self._invalidate_refs()
```

### 6.4 Standardize Naming (Priority: Low)

Fix `_reconciliations_holder` to `_reconciliation_holder` (singular).

---

## 7. Open Questions for Architecture

1. **Descriptor type safety**: Can descriptors preserve type hints for IDE support?
2. **Invalidation triggers**: What operations should auto-invalidate?
3. **SDK entity navigation**: Should SDK entities gain navigation patterns?
4. **Holder detection**: Should emoji fallback be implemented or removed?
5. **Circular import handling**: Better pattern than runtime imports in `_populate_children`?

---

## 8. Files Analyzed

### SDK Core Models
- `/src/autom8_asana/models/base.py` (32 lines)
- `/src/autom8_asana/models/common.py` (187 lines)
- `/src/autom8_asana/models/task.py` (460 lines)
- `/src/autom8_asana/models/project.py` (235 lines)
- `/src/autom8_asana/models/section.py` (174 lines)
- `/src/autom8_asana/models/user.py` (45 lines)
- `/src/autom8_asana/models/workspace.py` (41 lines)
- `/src/autom8_asana/models/team.py` (77 lines)
- `/src/autom8_asana/models/tag.py` (52 lines)
- `/src/autom8_asana/models/goal.py` (118 lines)
- `/src/autom8_asana/models/portfolio.py` (66 lines)
- `/src/autom8_asana/models/story.py` (92 lines)
- `/src/autom8_asana/models/attachment.py` (60 lines)
- `/src/autom8_asana/models/webhook.py` (86 lines)
- `/src/autom8_asana/models/custom_field.py` (141 lines)

### Business Layer Models
- `/src/autom8_asana/models/business/base.py` (194 lines)
- `/src/autom8_asana/models/business/business.py` (1105 lines)
- `/src/autom8_asana/models/business/contact.py` (565 lines)
- `/src/autom8_asana/models/business/unit.py` (911 lines)
- `/src/autom8_asana/models/business/offer.py` (821 lines)
- `/src/autom8_asana/models/business/process.py` (362 lines)
- `/src/autom8_asana/models/business/location.py` (310 lines)
- `/src/autom8_asana/models/business/hours.py` (243 lines)

---

## Appendix A: Navigation Pattern Matrix

```
                    SDK Entities           Business Entities
                    ============           =================
Parent Reference:   NameGid (static)       PrivateAttr (cached)
Lazy Loading:       No                     Yes (via holder)
Invalidation:       N/A                    _invalidate_refs()
Navigation Props:   No                     Yes (8-10 per entity)
Holder Detection:   N/A                    HOLDER_KEY_MAP
Population:         N/A                    _populate_children()
```

---

## Appendix B: Duplicated Code Locations

### Navigation Properties
| File | Lines | Pattern |
|------|-------|---------|
| contact.py | 100-128 | business, contact_holder, _invalidate_refs |
| unit.py | 229-259 | business, unit_holder, _invalidate_refs |
| offer.py | 142-184 | business, unit, offer_holder, _invalidate_refs |
| process.py | 139-181 | business, unit, process_holder, _invalidate_refs |
| location.py | 58-88 | business, location_holder, _invalidate_refs |
| hours.py | 58-86 | business, location_holder, _invalidate_refs |

### _populate_children Implementations
| File | Lines | Children Type |
|------|-------|---------------|
| contact.py | 532-564 | Contact |
| unit.py | 878-910 | Unit |
| offer.py | 786-820 | Offer |
| process.py | 327-361 | Process |
| location.py | 262-309 | Location + Hours |
| business.py | 60-96 | DNA |
| business.py | 134-171 | Reconciliation |
| business.py | 210-246 | AssetEdit |
| business.py | 285-322 | Videography |

---

**Document Version**: 1.0
**Created**: 2025-12-16
**Author**: Requirements Analyst (Discovery Phase)
**Next Steps**: Architecture review, descriptor implementation TDD
