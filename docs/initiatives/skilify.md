
# Autom8_asana Business Model Skills Architecture Design

> **Purpose**: Design a modular, skills-first architecture for building the autom8 business model hierarchy into the autom8_asana SDK with clear separation of concerns: schemas, relationships, custom fields, and workflows.

> **Approach**: Create 4 modular skills that build incrementally, starting with schemas → relationships → fields → workflows, keeping SDK pure and deferring SQL/integration concerns.

---

## Executive Summary

**Vision**: Expand autom8_asana from general Asana SDK to domain-aware business platform SDK with rich models for Businesses, Contacts, Units, Locations, and related entities—while keeping SDK code simple and reusable.

**Key Insight from Exploration**: autom8_asana SDK is already well-architected (Pydantic v2, SaveSession UoW, async-first, ChangeTracker). The business model migration is primarily about **adding Task subclasses and optional patterns for relationships**, not rearchitecting the SDK.

**Proposed Modular Skills Architecture**:

| Skill | Purpose | Content | Activates On |
|-------|---------|---------|--------------|
| **autom8-asana-business-schemas** | Models, fields, validation | Business, Contact, Unit, Location, Hours models; custom field definitions | Model definition, schema questions |
| **autom8-asana-business-relationships** | Holders, navigation, composition | Holder pattern, bidirectional refs, lazy loading, navigation | "How do I navigate...", "holder", "parent/child" |
| **autom8-asana-business-fields** | Custom field type mapping | Field type wrappers, accessors, resolvers, defaults, overrides | Custom field implementation, "CompanyId", field patterns |
| **autom8-asana-business-workflows** | SaveSession patterns, operations | Cascading saves, composite entities, update orchestration | SaveSession usage, bulk operations, workflow patterns |
| (Future) **autom8-integration** | SQL, webhooks, external APIs | SQL fallback patterns, thread-safe caching, webhook handlers | Database integration, legacy system sync |

**User Decisions (Applied)**:
- ✅ Modular skills by concept (not one monolithic skill)
- ✅ Keep SDK pure (SQL integration in separate layer)
- ✅ Create Prompt-0 (strategic) + Prompt-1 (tactical) versions
- ✅ Incremental skill expansion as features are built

---

## Phase 1: Prompt-0 (Strategic Overview)

### High-Level Objectives

**GA-Readiness Requirements** (P0):
1. Business root model with 7 holder properties
2. ContactHolder → Contact[] with owner detection
3. UnitHolder → Unit[] with nested OfferHolder/ProcessHolder support
4. LocationHolder with Location + Hours children
5. Custom field typed accessor infrastructure
6. SaveSession support for composite entities
7. Bidirectional navigation (parent ↔ child)

**Skills to Build Out**:
1. **autom8-asana-business-schemas** (Week 1-2)
   - Business, Contact, Unit, Location, Hours models
   - Custom field type definitions and mapping
   - NAME_CONVENTION patterns with emoji indicators

2. **autom8-asana-business-relationships** (Week 2-3)
   - Holder pattern protocol/mixin
   - Lazy loading with optional caching
   - Bidirectional navigation properties
   - Upward/downward traversal patterns

3. **autom8-asana-business-fields** (Week 3-4)
   - Custom field accessor wrappers with type safety
   - Default/fallback/override resolution
   - Field resolver patterns

4. **autom8-asana-business-workflows** (Week 4+)
   - Composite entity SaveSession patterns
   - Cascading updates (if SaveSession supports)
   - Bulk update orchestration

### What's Explicitly OUT of Scope

**Not in Business Model Skills**:
- SQL integration (→ autom8-integration skill)
- Manager classes (AdManager, ReconcileBudget)
- Process subclasses (24+ subclasses deferred to Phase 2)
- Advanced Insights/Analytics
- Webhooks (→ autom8-integration)

### Success Criteria for Prompt-0

1. ✅ 7 holders accessible from Business model
2. ✅ ContactHolder → Contact[] with owner detection working
3. ✅ UnitHolder → Unit[] working with nested Offer/Process holders
4. ✅ LocationHolder → Location + Hours working
5. ✅ Bidirectional navigation operational (Contact → Business, Unit → ContactHolder, etc.)
6. ✅ Custom field typed accessors for 18+ Business fields
7. ✅ SaveSession support for composite hierarchies
8. ✅ All models with proper NAME_CONVENTION templates
9. ✅ Tests covering navigation, custom fields, composition

---

## Phase 2: Prompt-1 (Tactical Implementation Guide)

### Skill 1: autom8-asana-business-schemas

**Location**: `/Users/tomtenuta/Code/autom8_asana/.claude/skills/autom8-asana-business-schemas/`

**Entry Point** (`SKILL.md`):
```yaml
When to activate:
  keywords:
    - "Business model"
    - "Holder", "Contact", "Unit", "Location"
    - "custom field", "ASANA_FIELDS"
    - "NAME_CONVENTION", "PRIMARY_PROJECT_GID"
  file_patterns:
    - "**/models/business/*.py"
    - "**/models/contact*.py"
    - "**/models/unit*.py"
  task_types:
    - Business model implementation
    - Custom field schema definition
    - Pydantic model design
```

**Contents**:

1. **business-model.md** (~200 lines)
   - Business base class with HOLDER_KEY_MAP
   - 7 holders and emoji indicators
   - PRIMARY_PROJECT_GID pattern
   - 18 custom field definitions
   - Example: `Business(Task) with contact_holder, unit_holder, location_holder, dna_holder, reconciliations_holder, asset_edit_holder, videography_holder`

2. **contact-model.md** (~150 lines)
   - Contact(Task) with 21 custom fields
   - Position field with "owner" detection
   - HumanName parsing pattern
   - Example field structure

3. **unit-model.md** (~200 lines)
   - Unit(Task) with 44 custom fields
   - Nested HOLDER_KEY_MAP for offer_holder + process_holder
   - Demographics composition pattern
   - Vertical field with reference to business.location context

4. **location-model.md** (~100 lines)
   - Location(Task) with 11 custom fields (address components)
   - Address line composition (line_1, line_2)
   - Stripe address format pattern
   - Geocoding integration hooks

5. **hours-model.md** (~80 lines)
   - Hours(Task) with 6 custom fields (days of week)
   - Hours array conversion pattern
   - Business hours format standardization

6. **custom-fields-glossary.md** (~250 lines)
   - All 18 Business fields: AggressionLevel, BookingType, CompanyId, etc.
   - All 21 Contact fields: ContactEmail, ContactPhone, Campaign, etc.
   - All 44 Unit fields: MRR, AdAccountId, Currency, etc.
   - Field type wrappers (not yet implementation details - that's Fields skill)
   - Default values, enums, validation rules

7. **patterns-schemas.md** (~150 lines)
   - Pydantic v2 model pattern from SDK baseline
   - extra="ignore" configuration
   - TYPE_CHECKING imports for circular refs
   - NAME_CONVENTION template rendering
   - How to extend Task base class

### Skill 2: autom8-asana-business-relationships

**Location**: `/Users/tomtenuta/Code/autom8_asana/.claude/skills/autom8-asana-business-relationships/`

**Entry Point** (`SKILL.md`):
```yaml
When to activate:
  keywords:
    - "holder", "parent_task", "subtasks"
    - "lazy load", "bidirectional", "navigation"
    - "contact_holder", "unit_holder", "location_holder"
    - "get_holder", "parent", "child"
  file_patterns:
    - "**/models/holder*.py"
    - "**/*holder*.py"
  task_types:
    - Holder pattern implementation
    - Navigation property design
    - Relationship composition
```

**Contents**:

1. **holder-pattern.md** (~200 lines)
   - Holder base pattern (Task subclass with HAS_SUB_MODELS)
   - HOLDER_KEY_MAP structure: `OrderedDict([("contact_holder", ("Contacts", "🧑"))])`
   - Optional HOLDER_PROJECT_MAP for project-specific holders
   - `@property holder()` vs `@property holders()` pattern (singular vs list)
   - Owner detection pattern (position field matching)

2. **lazy-loading.md** (~150 lines)
   - Thread-safe lazy loading in async context (different from legacy threading)
   - SaveSession-compatible lazy loading (don't fetch on init)
   - Caching pattern with hasattr checks
   - Optional weak references for memory efficiency
   - Lazy load timing: on first access or SaveSession.track()?

3. **bidirectional-navigation.md** (~180 lines)
   - Downward: `business.contact_holder.contact`
   - Upward: `contact.contact_holder`, `contact.business`
   - Cross-navigation: `contact.unit` (via business)
   - Circular import prevention (TYPE_CHECKING, forward refs)
   - Caching upward refs (cached vs computed)

4. **composite-pattern.md** (~120 lines)
   - How Unit contains OfferHolder + ProcessHolder
   - Recursive holder definitions
   - Depth limits (if any)
   - Performance implications

5. **patterns-relationships.md** (~100 lines)
   - get_holder() method implementation
   - Subtask fetching strategy (fetch all vs lazy)
   - Navigation consistency guarantees
   - Deletion cascade behavior (what happens if parent deleted?)

### Skill 3: autom8-asana-business-fields

**Location**: `/Users/tomtenuta/Code/autom8_asana/.claude/skills/autom8-asana-business-fields/`

**Entry Point** (`SKILL.md`):
```yaml
When to activate:
  keywords:
    - "custom field", "CustomFieldAccessor", "field getter", "field setter"
    - "@property", "field.get()", "field.set()"
    - "typed accessor", "field resolver"
  file_patterns:
    - "**/models/*field*.py"
    - "**/fields/*.py"
  task_types:
    - Custom field implementation
    - Field accessor design
    - Type mapping
```

**Contents**:

1. **field-accessor-pattern.md** (~180 lines)
   - Typed field accessor wrapper pattern
   - Three-level access: `business.company_id_field` (accessor), `business.company_id` (property), setter
   - Field resolver (name → GID conversion)
   - Change tracking integration
   - Validation in accessors vs models

2. **default-fallback-override.md** (~140 lines)
   - Default computation (from other fields, e.g., contact.full_name)
   - Fallback support (future: SQL column, external API)
   - Override priority: `override=True` forces default even if Asana has value
   - Resolution order: Asana value → Default → Fallback → None
   - When to use each pattern

3. **field-types.md** (~200 lines)
   - Enum fields (BookingType, Vertical, etc.) with value mapping
   - String fields with validation (email, phone, URL)
   - Numeric fields (MRR, AggressionLevel with limits)
   - List fields (AdAccountIdList, ZipCodeList)
   - Date fields (timestamps with timezone handling)
   - Custom composed types (Address composition, Demographics)

4. **field-resolver.md** (~100 lines)
   - How CustomFieldAccessor resolves field names to GIDs
   - Case-insensitive lookup
   - Caching resolver (don't re-resolve per access)
   - Integration with SaveSession (when does resolver run?)

5. **patterns-fields.md** (~100 lines)
   - Thread-safe lazy initialization of field accessors
   - Integration with Task.get_custom_fields()
   - Change tracking (modifications stored in accessor)
   - model_dump() override to serialize custom field changes

### Skill 4: autom8-asana-business-workflows

**Location**: `/Users/tomtenuta/Code/autom8_asana/.claude/skills/autom8-asana-business-workflows/`

**Entry Point** (`SKILL.md`):
```yaml
When to activate:
  keywords:
    - "SaveSession", "composite", "cascading"
    - "batch operation", "bulk update"
    - "save", "commit", "create business"
  file_patterns:
    - "**/workflows/*.py"
    - "**/operations/*.py"
  task_types:
    - Composite entity SaveSession
    - Bulk business operations
    - Workflow orchestration
```

**Contents**:

1. **composite-savesession.md** (~200 lines)
   - SaveSession with nested entities (Business → ContactHolder → Contact → ...)
   - Change tracking for full hierarchy
   - Dependency resolution (which entities save first?)
   - SaveSession already has DependencyGraph - how to leverage for composite?
   - Cascade vs explicit: should changes to contact auto-track business?

2. **workflow-patterns.md** (~150 lines)
   - Create new Business with all holders
   - Update contact in existing Business
   - Add new Unit to existing Business
   - Bulk import contacts into ContactHolder
   - Parallelize saves across units

3. **batch-operation-patterns.md** (~130 lines)
   - Batch create multiple tasks (contacts, units)
   - Custom field bulk update via batch API
   - Positioning operations (move to section)
   - Tag operations across multiple tasks

4. **operation-hooks.md** (~100 lines)
   - SaveSession @session.on_pre_save hooks for validation
   - Custom hook: validate ContactHolder has owner contact
   - Custom hook: validate Unit has location context
   - Post-save hooks for notifications

5. **patterns-workflows.md** (~80 lines)
   - Entry point for business operations
   - Context manager usage (with SaveSession)
   - Error handling and rollback
   - Observability/logging

---

## Implementation Roadmap

### Week 1: Foundation (Schemas + Relationships)

**Deliverables**:
- [ ] `autom8-asana-business-schemas` skill (7 files, ~1,080 lines)
- [ ] `autom8-asana-business-relationships` skill (5 files, ~750 lines)
- [ ] Business model implementation in SDK
- [ ] ContactHolder + Contact implementation
- [ ] Tests for models and navigation

**Code Output**:
- [ ] `src/autom8_asana/models/business.py` with 7 holder properties
- [ ] `src/autom8_asana/models/contact_holder.py`
- [ ] `src/autom8_asana/models/contact.py`
- [ ] `tests/unit/models/test_business.py`
- [ ] `tests/unit/models/test_contact_navigation.py`

### Week 2: Custom Fields (Fields)

**Deliverables**:
- [ ] `autom8-asana-business-fields` skill (5 files, ~820 lines)
- [ ] Custom field type wrappers
- [ ] Field accessor patterns in Business/Contact models
- [ ] Tests for field access and change tracking

**Code Output**:
- [ ] `src/autom8_asana/fields/business_fields.py` (18 field types)
- [ ] `src/autom8_asana/fields/contact_fields.py` (21 field types)
- [ ] Extend Business/Contact models with `@property field()` accessors
- [ ] `tests/unit/models/test_custom_fields.py`

### Week 3: Workflows (SaveSession)

**Deliverables**:
- [ ] `autom8-asana-business-workflows` skill (5 files, ~660 lines)
- [ ] SaveSession patterns for composite entities
- [ ] Example workflows (create business, bulk import contacts)
- [ ] Integration tests with SaveSession

**Code Output**:
- [ ] `src/autom8_asana/workflows/business_workflows.py`
- [ ] `examples/business_model_examples.py`
- [ ] `tests/integration/test_business_savesession.py`

### Week 4: Unit Model + Expansion

**Deliverables**:
- [ ] Unit model with nested holders
- [ ] Location + Hours models
- [ ] Remaining holder stubs (DNA, Reconciliations, AssetEdit, Videography)
- [ ] Comprehensive integration tests

**Code Output**:
- [ ] `src/autom8_asana/models/unit*.py`
- [ ] `src/autom8_asana/models/location*.py`
- [ ] `src/autom8_asana/models/hours.py`
- [ ] `tests/integration/test_business_hierarchy.py`

### Future: SQL Integration Layer

**When Ready** (not in initial phase):
- [ ] Create `autom8-integration` skill
- [ ] Design SQL fallback provider protocol
- [ ] Implement SQL accessors for optional fields
- [ ] Thread-safe caching patterns for DB reads

---

## Critical Architecture Decisions

**Decision 1: Task Subclass Hierarchy**
- ✅ **Chosen**: Business/Contact/Unit/Location/Hours inherit from Task
- **Rationale**: Leverages existing SaveSession, async operations, custom field infrastructure
- **Alternative Considered**: Composition (Business contains Contact models) - rejected because Asana API requires Task subtasks

**Decision 2: Holder Lazy Loading Strategy**
- ❓ **To Decide in Architect Phase**: When to fetch subtasks?
  - Option A: On property access (laziest)
  - Option B: On SaveSession.track() (more predictable)
  - Option C: On init (eager, simpler but more network calls)

**Decision 3: Custom Field Type Safety**
- ❓ **To Decide in Architect Phase**: Wrapper classes for each field type?
  - Option A: Field type classes (OfficePhone, CompanyId) - explicit, testable
  - Option B: Pydantic validators on model - simpler, less boilerplate
  - Option C: Hybrid (validators on model, accessors for complex types)

**Decision 4: Bidirectional Reference Caching**
- ❓ **To Decide in Architect Phase**: Cache parent/child refs or compute on access?
  - Option A: Cache upward refs (`_business`, `_contact_holder`) - faster, memory cost
  - Option B: Compute on access via parent_task.parent - slower, pure
  - Option C: Hybrid with weak references - complex but memory-efficient

**Decision 5: Composite SaveSession Support**
- ❓ **To Decide in Architect Phase**: Does SaveSession.track() on Business auto-track children?
  - Option A: Manual (developer tracks each entity) - explicit, flexible
  - Option B: Automatic (SaveSession recursively tracks tree) - convenient, magic
  - Option C: Optional (SaveSession.track(business, recursive=True)) - balanced

---

## Token Savings & Skills Structure

### Current State
- Root `.claude/` directory: 3 files, ~291 lines (after Session 2 migration)
- autom8-asana-domain skill: 7 files, ~1,266 lines
- **Total loaded per session**: ~870 tokens (root) + ~150 tokens (skill on-demand)

### After Business Model Skills Added
- Root `.claude/` directory: 3 files, ~291 lines (unchanged)
- autom8-asana-domain skill: 7 files, ~1,266 lines (unchanged)
- **NEW**:
  - autom8-asana-business-schemas: 7 files, ~1,080 lines
  - autom8-asana-business-relationships: 5 files, ~750 lines
  - autom8-asana-business-fields: 5 files, ~820 lines
  - autom8-asana-business-workflows: 5 files, ~660 lines

**Per-Session Loading**:
- Root files: ~870 tokens (always loaded)
- autom8-asana-domain: ~150 tokens (on-demand for SDK work)
- Business schemas: ~200 tokens (loaded when modeling Business, Contact, Unit)
- Business relationships: ~150 tokens (loaded when implementing holders)
- Business fields: ~180 tokens (loaded when working with custom fields)
- Business workflows: ~160 tokens (loaded when implementing SaveSession patterns)

**Result**: Granular loading - only load knowledge for the current task phase, avoiding cognitive overload

---

## Next Steps

**Immediate**:
1. ✅ Approved: User confirmed modular skills structure, no SQL in SDK, Prompt-1 detailed approach
2. Create Prompt-0 (this document - strategic) + Prompt-1 (below - tactical with code examples)
3. Present refined plan to user for approval
4. Invoke @orchestrator with Prompt-0 + Prompt-1 to begin implementation

**User Decisions Applied**:
- ✅ Skills by concept (schemas → relationships → fields → workflows)
- ✅ Incremental expansion (add skills as phases complete)
- ✅ SDK stays pure (SQL deferred to autom8-integration)
- ✅ Two-prompt structure (strategic + tactical)

---

## Prompt-0 Summary

**Mission**: Migrate Business model hierarchy from legacy autom8 monolith to autom8_asana SDK with modular skills architecture.

**Why This Works**:
1. SDK is already well-architected (SaveSession, async, change tracking)
2. Business model is domain logic on top of SDK, not fundamental to it
3. Modular skills separate concerns: schemas vs relationships vs fields vs workflows
4. Progressive skill expansion matches development phases
5. Keeps SDK reusable (not autom8-specific)

**Phased Approach**:
- **Week 1-2**: Schemas + Relationships (Business, ContactHolder, Contact)
- **Week 2-3**: Custom Fields (typed accessors)
- **Week 3-4**: Workflows (SaveSession patterns)
- **Week 4+**: Expansion (Unit, Location, remaining holders)

**Ready for Prompt-1**: Detailed implementation guide with code examples, ADRs, and specific patterns.

