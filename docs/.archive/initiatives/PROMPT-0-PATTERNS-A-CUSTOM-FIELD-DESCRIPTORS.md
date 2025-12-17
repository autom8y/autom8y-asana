# Orchestrator Initialization: Design Patterns Sprint - Initiative A (Custom Field Property Descriptors)

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`documentation`** - PRD/TDD/ADR templates, workflow pipeline, quality gates
- **`standards`** - Tech stack decisions, code conventions, repository structure
- **`10x-workflow`** - Agent coordination, session protocol, quality gates
- **`autom8-asana-domain`** - SDK patterns, SaveSession, Asana resources
- **`autom8-asana-business-fields`** - Custom field accessor patterns, field types

**How Skills Work**: Skills load automatically based on your current task.

## Your Role: Orchestrator

You coordinate a 4-agent development workflow. You plan, delegate, coordinate, and verify - you do not implement directly.

## Your Specialist Agents

| Agent | Invocation | Responsibility |
|-------|------------|----------------|
| **Requirements Analyst** | `@requirements-analyst` | Requirements definition, acceptance criteria, scope boundaries |
| **Architect** | `@architect` | TDDs, ADRs, system design, trade-off analysis |
| **Principal Engineer** | `@principal-engineer` | Implementation, code quality, technical execution |
| **QA/Adversary** | `@qa-adversary` | Validation, failure mode testing, security/quality review |

---

## The Mission: Replace Custom Field Property Boilerplate with Declarative Descriptors

This initiative applies the proven Navigation Descriptor Pattern to custom field properties, replacing ~400 lines of repetitive getter/setter boilerplate across 5 business models with a declarative, type-safe descriptor system.

### Why This Initiative?

- **Code reduction**: Eliminate ~400 lines of near-identical property definitions
- **Consistency**: All custom field properties behave identically
- **Type safety**: Descriptors return proper types; IDE knows `company_id` is `str | None`
- **Maintainability**: Change field behavior once, affects all fields of that type
- **Proven pattern**: Builds directly on Navigation Descriptor success (ADR-0075, ADR-0076, ADR-0077)

### Issues Addressed

| Current Pattern | Problem |
|-----------------|---------|
| `_get_text_field()` + `@property` pairs | 10+ lines per text field, repeated 50+ times |
| `_get_enum_field()` + `@property` pairs | Same extraction logic duplicated across models |
| Manual `Fields` constants | Must manually keep in sync with properties |
| Type conversion in getters | Duplicated `int(value)`, `str(value)` logic |

### Current State

**Business Model Example** (19 custom fields):

```python
class Business(BusinessEntity):

    class Fields:
        COMPANY_ID = "Company ID"
        OFFICE_PHONE = "Office Phone"
        # ... 17 more constants

    def _get_text_field(self, field_name: str) -> str | None:
        value = self.get_custom_fields().get(field_name)
        if value is None or isinstance(value, str):
            return value
        return str(value)

    def _get_enum_field(self, field_name: str) -> str | None:
        value = self.get_custom_fields().get(field_name)
        if isinstance(value, dict):
            name = value.get("name")
            return str(name) if name is not None else None
        # ... more handling

    @property
    def company_id(self) -> str | None:
        return self._get_text_field(self.Fields.COMPANY_ID)

    @company_id.setter
    def company_id(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.COMPANY_ID, value)

    @property
    def office_phone(self) -> str | None:
        return self._get_text_field(self.Fields.OFFICE_PHONE)

    @office_phone.setter
    def office_phone(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.OFFICE_PHONE, value)

    # ... 17 more property pairs (each ~8 lines)
```

### Target State

**Same functionality with descriptors** (~2 lines per field):

```python
from autom8_asana.patterns import TextField, EnumField, NumberField, PeopleField

class Business(BusinessEntity):

    # Text fields - 1 line each
    company_id = TextField("Company ID")
    office_phone = TextField("Office Phone")
    facebook_page_id = TextField("Facebook Page ID")
    google_cal_id = TextField("Google Cal ID")
    owner_name = TextField("Owner Name")
    stripe_id = TextField("Stripe ID")
    twilio_phone_num = TextField("Twilio Phone Num")
    # ... more text fields

    # Enum fields
    vertical = EnumField("Vertical")
    booking_type = EnumField("Booking Type")
    vca_status = EnumField("VCA Status")
    aggression_level = EnumField("Aggression Level")

    # Number fields
    num_reviews = NumberField("Num Reviews")

    # People fields
    rep = PeopleField("Rep")
```

### Custom Field Model Profile

| Attribute | Value |
|-----------|-------|
| Models affected | Business, Contact, Unit, Offer, Process |
| Total custom field properties | ~65 across all models |
| Field types | Text, Enum, Number, People, Date |
| Lines per property (current) | ~8 (getter + setter + docstring) |
| Lines per property (target) | ~2 (descriptor declaration) |
| Total lines saved | ~400 |

### Key Constraints

- **Pydantic compatibility**: Descriptors must NOT have type annotations (ADR-0077)
- **No runtime performance regression**: Descriptor `__get__` must be fast
- **IDE autocomplete preservation**: Properties must remain discoverable
- **Backward compatibility**: Existing code using `business.company_id` must work unchanged
- **Change tracking integration**: Setting must use `get_custom_fields().set()` for dirty tracking
- **Type safety**: `TextField` returns `str | None`, `NumberField` returns `int | None`, etc.

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Create `TextField` descriptor for text custom fields | Must |
| Create `EnumField` descriptor for enum custom fields | Must |
| Create `NumberField` descriptor for number custom fields | Must |
| Create `PeopleField` descriptor for people custom fields | Must |
| Create `DateField` descriptor for date custom fields | Should |
| Migrate Business model (19 fields) | Must |
| Migrate Contact model custom fields | Must |
| Migrate Unit model custom fields | Must |
| Migrate Offer model custom fields | Should |
| Migrate Process model custom fields | Should |
| Auto-generate `Fields` class constants | Should |
| Preserve IDE autocomplete | Must |
| Maintain Pydantic compatibility (no type annotations) | Must |

### Success Criteria

1. `TextField`, `EnumField`, `NumberField`, `PeopleField` descriptors implemented
2. Business model migrated to descriptors (~19 fields)
3. Contact model migrated to descriptors
4. Unit model migrated to descriptors
5. All existing tests pass without modification
6. IDE autocomplete works for all descriptor properties
7. Type checker passes (`mypy --strict`)
8. No runtime performance regression (benchmark descriptor `__get__`)
9. Change tracking preserved (setting marks entity dirty)
10. Documentation updated with descriptor usage patterns

### Dependencies

**Depends On:**
- ADR-0077 (Pydantic Descriptor Compatibility) - Pattern for avoiding type annotations
- Existing Navigation Descriptors - Reference implementation in `descriptors.py`
- CustomFieldAccessor - `get_custom_fields()` method for underlying storage

**Blocks:**
- None (this initiative is foundational)

**Related:**
- Initiative B (Error Mixin) - Can run in parallel
- Initiative C (Holder Factory) - May benefit from descriptor familiarity

---

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | Current field patterns analysis, field type catalog |
| **2: Requirements** | Requirements Analyst | PRD-PATTERNS-A with acceptance criteria per field type |
| **3: Architecture** | Architect | TDD-PATTERNS-A + ADR for Custom Field Descriptor pattern |
| **4: Implementation P1** | Principal Engineer | Core descriptors (TextField, EnumField, NumberField) |
| **5: Implementation P2** | Principal Engineer | Business model migration + remaining descriptors |
| **6: Implementation P3** | Principal Engineer | Contact, Unit model migrations |
| **7: Validation** | QA/Adversary | Type safety validation, IDE testing, performance benchmarks |

---

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rule**: Never execute without explicit confirmation.

---

## Discovery Phase: What Must Be Explored

Before requirements can be finalized, the **Requirements Analyst** must explore:

### Custom Field Pattern Analysis

| File | Questions to Answer |
|------|---------------------|
| `src/autom8_asana/models/business/business.py` | How many fields? What types? What getter patterns? |
| `src/autom8_asana/models/business/contact.py` | What fields? Enum handling differences? |
| `src/autom8_asana/models/business/unit.py` | What fields? Any special conversions? |
| `src/autom8_asana/models/business/offer.py` | What fields? Date fields present? |
| `src/autom8_asana/models/business/process.py` | What fields? People fields present? |
| `src/autom8_asana/models/custom_field_accessor.py` | How does `get()` work? How does `set()` work? |

### Field Type Audit

| Field Type | Questions |
|------------|-----------|
| **Text** | Standard `str | None` return? Any special handling? |
| **Enum** | Always `{"gid": "...", "name": "Value"}` format? Edge cases? |
| **Number** | Integer only or float? `None` vs `0` handling? |
| **People** | List of dicts? Single person vs multi-select? |
| **Date** | ISO format? `{"date": "YYYY-MM-DD"}` or plain string? |

### Navigation Descriptor Reference

| Area | Questions |
|------|-----------|
| `src/autom8_asana/models/business/descriptors.py` | How is `__set_name__` used? |
| ADR-0077 | What Pydantic constraints must be followed? |
| Test patterns | How are existing descriptors tested? |

---

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins:

### Descriptor Design Questions

1. **Fields class generation**: Auto-generate from descriptor declarations, or keep manual?
2. **Docstring strategy**: Copy from descriptor to generated property, or single source?
3. **Validation**: Should descriptors validate values on set (e.g., enum options)?
4. **Default values**: Support default values beyond `None`?

### Field Type Questions

5. **Enum write format**: Does Asana accept name string or require GID on write?
6. **People field write**: What format for setting people? List of GIDs?
7. **Date field format**: ISO string or Python date objects?
8. **Number precision**: Integer vs float? Decimal handling?

### Migration Questions

9. **Incremental migration**: All fields at once or one model at a time?
10. **Test updates**: Update existing tests or add new descriptor tests?
11. **Deprecation**: Deprecate helper methods like `_get_text_field()`?

---

## Your First Task

Confirm understanding by:

1. Summarizing the Custom Field Descriptors goal in 2-3 sentences
2. Listing the 7 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step before requirements
4. Confirming which files must be analyzed before PRD-PATTERNS-A
5. Listing which open questions you need answered before Session 2
6. Acknowledging this builds on the Navigation Descriptor success (ADR-0075, ADR-0076, ADR-0077)

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

## Session Trigger Prompts

### Session 1: Discovery

```markdown
Begin Session 1: Custom Field Pattern Discovery

Work with the @requirements-analyst agent to analyze existing custom field patterns across business models.

**Goals:**
1. Catalog all custom field properties in Business model
2. Catalog all custom field properties in Contact, Unit, Offer, Process models
3. Identify field types (text, enum, number, people, date)
4. Document getter/setter patterns
5. Analyze CustomFieldAccessor integration
6. Review Navigation Descriptor implementation for reference
7. Identify edge cases and special handling

**Files to Analyze:**
- `src/autom8_asana/models/business/business.py` - 19 fields
- `src/autom8_asana/models/business/contact.py` - Field patterns
- `src/autom8_asana/models/business/unit.py` - Field patterns
- `src/autom8_asana/models/business/offer.py` - Field patterns
- `src/autom8_asana/models/business/process.py` - Field patterns
- `src/autom8_asana/models/custom_field_accessor.py` - Underlying storage
- `src/autom8_asana/models/business/descriptors.py` - Navigation pattern reference

**Deliverable:**
A discovery document with:
- Complete field catalog (name, type, model)
- Getter/setter pattern analysis
- CustomFieldAccessor integration requirements
- Edge cases and special handling
- Recommended descriptor types

Create the analysis plan first. I'll review before you execute.
```

### Session 2: Requirements

```markdown
Begin Session 2: Custom Field Descriptors Requirements

Work with the @requirements-analyst agent to create PRD-PATTERNS-A.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Define requirements for each descriptor type (TextField, EnumField, etc.)
2. Define migration requirements for each model
3. Define Pydantic compatibility requirements
4. Define change tracking integration requirements
5. Define IDE autocomplete requirements
6. Define acceptance criteria for each requirement

**Key Questions to Address:**
- What field types need descriptors?
- What's the migration strategy (incremental vs big-bang)?
- What's the backward compatibility strategy?
- What's the testing strategy?

**PRD Organization:**
- FR-DESC-*: Descriptor type requirements
- FR-MIGRATE-*: Model migration requirements
- FR-COMPAT-*: Compatibility requirements
- NFR-*: Performance, type safety requirements

Create the plan first. I'll review before you execute.
```

### Session 3: Architecture

```markdown
Begin Session 3: Custom Field Descriptors Architecture

Work with the @architect agent to create TDD-PATTERNS-A and required ADRs.

**Prerequisites:**
- PRD-PATTERNS-A approved

**Goals:**
1. Design descriptor class hierarchy
2. Design CustomFieldAccessor integration
3. Design type conversion strategy
4. Design Fields class auto-generation (if approved)
5. Design testing strategy

**Required ADRs:**
- ADR: Custom Field Descriptor Pattern
- ADR: Field Type Conversion Strategy (if needed)

**Descriptor Structure to Consider:**

```
src/autom8_asana/patterns/
├── __init__.py
├── custom_field_descriptors.py
│   ├── CustomFieldDescriptor[T]  (base)
│   ├── TextField
│   ├── EnumField
│   ├── NumberField
│   ├── PeopleField
│   └── DateField
└── (future: method_generator.py)
```

Create the plan first. I'll review before you execute.
```

### Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - Core Descriptors

Work with the @principal-engineer agent to implement core descriptor types.

**Prerequisites:**
- PRD-PATTERNS-A approved
- TDD-PATTERNS-A approved
- ADRs documented

**Phase 1 Scope:**
1. Create `src/autom8_asana/patterns/` module
2. Implement `CustomFieldDescriptor[T]` base class
3. Implement `TextField` descriptor
4. Implement `EnumField` descriptor
5. Implement `NumberField` descriptor
6. Unit tests for each descriptor type

**Hard Constraints:**
- No type annotations on descriptor declarations (ADR-0077)
- Descriptor `__get__` must use `get_custom_fields()` accessor
- Descriptor `__set__` must use `get_custom_fields().set()`
- Full type hints on descriptor classes themselves

**Explicitly OUT of Phase 1:**
- PeopleField, DateField (Phase 2)
- Business model migration (Phase 2)
- Other model migrations (Phase 3)

Create the plan first. I'll review before you execute.
```

### Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - Business Migration

Work with the @principal-engineer agent to complete descriptors and migrate Business model.

**Prerequisites:**
- Phase 1 complete and tested

**Phase 2 Scope:**
1. Implement `PeopleField` descriptor
2. Implement `DateField` descriptor (if needed)
3. Migrate Business model to descriptors (19 fields)
4. Remove `_get_text_field()`, `_get_enum_field()` helper methods
5. Update Business model tests
6. Verify IDE autocomplete works

**Integration Points:**
- CustomFieldAccessor integration must preserve dirty tracking
- Existing Business model tests must pass unchanged

Create the plan first. I'll review before you execute.
```

### Session 6: Implementation Phase 3

```markdown
Begin Session 6: Implementation Phase 3 - Remaining Models

Work with the @principal-engineer agent to migrate remaining business models.

**Prerequisites:**
- Phase 2 complete and tested
- Business model migration validated

**Phase 3 Scope:**
1. Migrate Contact model custom fields
2. Migrate Unit model custom fields
3. Migrate Offer model custom fields (if in scope)
4. Migrate Process model custom fields (if in scope)
5. Update tests for each model
6. Remove deprecated helper methods

**Migration Pattern:**
1. Identify all custom field properties
2. Add descriptor declarations
3. Remove @property implementations
4. Verify tests pass
5. Update docstrings if needed

Create the plan first. I'll review before you execute.
```

### Session 7: Validation

```markdown
Begin Session 7: Custom Field Descriptors Validation

Work with the @qa-adversary agent to validate the descriptor implementation.

**Prerequisites:**
- All implementation phases complete

**Goals:**

**Part 1: Type Safety Validation**
- Verify mypy passes with --strict
- Verify type hints are correct for each descriptor type
- Test IDE autocomplete (VSCode, PyCharm)

**Part 2: Functional Validation**
- Test getter returns correct type
- Test setter updates CustomFieldAccessor
- Test dirty tracking preserved
- Test None handling
- Test edge cases (empty string, 0, etc.)

**Part 3: Performance Validation**
- Benchmark descriptor __get__ vs old property
- Verify no significant regression
- Test with large number of field accesses

**Part 4: Compatibility Validation**
- Verify existing tests pass unchanged
- Verify Pydantic model_dump() works
- Verify Pydantic model_validate() works
- Test serialization/deserialization

Create the plan first. I'll review before you execute.
```

---

## Context Gathering Checklist

Before starting, gather:

**Codebase:**
- [ ] `src/autom8_asana/models/business/business.py` - Current 19-field implementation
- [ ] `src/autom8_asana/models/business/contact.py` - Contact fields
- [ ] `src/autom8_asana/models/business/unit.py` - Unit fields
- [ ] `src/autom8_asana/models/custom_field_accessor.py` - Field storage API
- [ ] `src/autom8_asana/models/business/descriptors.py` - Navigation pattern reference
- [ ] Related test files

**Documentation:**
- [ ] ADR-0075 (Navigation Descriptor Pattern)
- [ ] ADR-0076 (Auto-Invalidation Strategy)
- [ ] ADR-0077 (Pydantic Descriptor Compatibility)
- [ ] Design Pattern Analysis document

**Architect's Proposed Design:**
- [ ] CustomFieldDescriptor base class from analysis
- [ ] TextField, EnumField, etc. implementations
- [ ] Pydantic compatibility notes

---

## Related Documentation

| Document | Location | Relevance |
|----------|----------|-----------|
| Meta Prompt -1 | `/docs/initiatives/PROMPT-MINUS-1-DESIGN-PATTERNS.md` | Parent initiative |
| Design Pattern Analysis | `/docs/architecture/DESIGN-PATTERN-OPPORTUNITIES.md` | Pattern specification |
| Navigation Descriptor ADR | `/docs/decisions/ADR-0075-navigation-descriptor-pattern.md` | Proven pattern |
| Pydantic Compatibility ADR | `/docs/decisions/ADR-0077-pydantic-descriptor-compatibility.md` | Critical constraint |
| Existing Descriptors | `src/autom8_asana/models/business/descriptors.py` | Reference implementation |
| CustomFieldAccessor | `src/autom8_asana/models/custom_field_accessor.py` | Integration point |
| Business Model | `src/autom8_asana/models/business/business.py` | Primary migration target |

---

## Risk Assessment

This initiative has **LOW RISK** due to:

1. **Proven pattern**: Navigation Descriptors already successful
2. **Clear specification**: Architect provided detailed design
3. **Incremental migration**: Can migrate one model at a time
4. **No API changes**: External behavior unchanged
5. **Good test coverage**: Existing tests validate behavior

**Potential Issues**:
- IDE autocomplete edge cases
- Pydantic validation interaction
- Performance micro-regressions

**Mitigations**:
- Test with multiple IDEs
- Follow ADR-0077 strictly
- Benchmark before/after

---

*This is Initiative A of the Design Patterns Sprint. It is the FIRST initiative with lowest risk and highest familiarity due to Navigation Descriptor precedent.*
