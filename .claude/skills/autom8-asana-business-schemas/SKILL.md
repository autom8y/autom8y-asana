# Business Model Schemas

> Pydantic models for Business, Contact, Unit, Offer, Address, Hours entities

---

## Activation Triggers

**Use this skill when**:
- Defining or modifying Business, Contact, Unit, Offer, Address, Hours models
- Working with holder task types (ContactHolder, UnitHolder, OfferHolder, etc.)
- Implementing custom field definitions on business entities
- Understanding NAME_CONVENTION patterns and emoji indicators
- Writing Task subclasses for business domain

**Keywords**: Business model, Contact model, Unit model, Offer model, Address model, Hours model, Holder, ContactHolder, UnitHolder, OfferHolder, LocationHolder, custom field, ASANA_FIELDS, NAME_CONVENTION, PRIMARY_PROJECT_GID, HOLDER_KEY_MAP, CascadingFields, InheritedFields, CASCADING_FIELDS, INHERITED_FIELDS, allow_override, multi-level cascade, Unit cascading, target_types

**File patterns**: `**/models/business/*.py`, `**/models/contact*.py`, `**/models/unit*.py`, `**/models/offer*.py`, `**/models/address*.py`, `**/models/hours*.py`

---

## Architecture Decision: Task Subclass Hierarchy

**Decision**: Business, Contact, Unit, Offer, Address, Hours all inherit from Task (ADR-0029).

**Rationale**:
- Leverages existing SaveSession infrastructure for dependency ordering
- Reuses ChangeTracker snapshot-based dirty detection via `model_dump()`
- Custom fields already accessible via `get_custom_fields()` accessor
- Asana API treats all business entities as tasks with subtasks

```python
from autom8_asana.models.task import Task

class Business(Task):
    """Business entity - root of the hierarchy."""
    pass

class Contact(Task):
    """Contact within a Business's ContactHolder."""
    pass
```

---

## Quick Reference

| I need to...                        | See                                                    |
| ----------------------------------- | ------------------------------------------------------ |
| Understand Business model structure | [business-model.md](business-model.md)                 |
| Work with Contact models            | [contact-model.md](contact-model.md)                   |
| Work with Unit models               | [unit-model.md](unit-model.md)                         |
| Work with Offer models              | [offer-model.md](offer-model.md)                       |
| Work with Address models            | [address-model.md](address-model.md)                   |
| Work with Hours models              | [hours-model.md](hours-model.md)                       |
| Look up custom field names          | [custom-fields-glossary.md](custom-fields-glossary.md) |
| Understand Pydantic patterns        | [patterns-schemas.md](patterns-schemas.md)             |

---

## Model Hierarchy Overview

```
Business (Task)
    |
    +-- ContactHolder (Task) --> Contact[] (Task)
    |
    +-- UnitHolder (Task) --> Unit[] (Task)
    |                            |
    |                            +-- OfferHolder --> Offer[]
    |                            +-- ProcessHolder --> Process[]
    |
    +-- LocationHolder (Task) --> Address (Task)  [sibling]
    |                        --> Hours (Task)    [sibling]
    |
    +-- DNAHolder (Task) --> DNA[] (stub)
    +-- ReconciliationsHolder --> Reconciliation[] (stub)
    +-- AssetEditHolder --> AssetEdit[] (stub)
    +-- VideographyHolder --> Videography[] (stub)
```

Note: Address and Hours are **siblings** under LocationHolder (single-location business model).

---

## Core Patterns

### HOLDER_KEY_MAP

Business entities use `HOLDER_KEY_MAP` to define which subtask types they contain:

```python
class Business(Task):
    HOLDER_KEY_MAP: ClassVar[dict[str, tuple[str, str]]] = {
        "contact_holder": ("Contacts", "person"),     # (name, emoji)
        "unit_holder": ("Units", "package"),
        "location_holder": ("Location", "map"),
        "dna_holder": ("DNA", "dna"),
        "reconciliations_holder": ("Reconciliations", "abacus"),
        "asset_edit_holder": ("Asset Edit", "scissors"),
        "videography_holder": ("Videography", "video_camera"),
    }
```

### NAME_CONVENTION

Each entity type has a naming template for identification:

```python
# Business: Company name as task name
business.name = "Acme Corp"

# Contact: Full name or placeholder
contact.name = contact.full_name or "New Contact"

# Unit: "{vertical} - {mrr}" pattern
unit.name = f"{unit.vertical} - ${unit.mrr}"
```

---

## Progressive References

| Document                                               | Lines | Content                                        |
| ------------------------------------------------------ | ----- | ---------------------------------------------- |
| [business-model.md](business-model.md)                 | ~220  | Business class, 7 holders, 19 custom fields    |
| [contact-model.md](contact-model.md)                   | ~300  | Contact class, owner detection, 19 fields      |
| [unit-model.md](unit-model.md)                         | ~260  | Unit class, nested holders, 31 fields          |
| [offer-model.md](offer-model.md)                       | ~240  | Offer class (ad status unit), 39 fields        |
| [address-model.md](address-model.md)                   | ~160  | Address class (sibling of Hours), 12 fields    |
| [hours-model.md](hours-model.md)                       | ~240  | Hours class (sibling of Address), 7 day fields |
| [custom-fields-glossary.md](custom-fields-glossary.md) | ~280  | All field definitions by entity                |
| [patterns-schemas.md](patterns-schemas.md)             | ~280  | Pydantic v2 patterns, Task extension           |
