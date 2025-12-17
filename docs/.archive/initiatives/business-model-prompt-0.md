# Orchestrator Initialization: autom8_asana Business Model Implementation

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

**Domain-Specific Skills** (CRITICAL - use heavily):
- **`autom8-asana-domain`** — SDK patterns, SaveSession, Asana resources, async-first, batch operations
  - Activates when: Working with Task models, SaveSession, CustomFieldAccessor, client operations

- **`autom8-asana-business-schemas`** — Business, Contact, Unit, Location, Hours models; custom field definitions
  - Activates when: Defining models, custom fields, NAME_CONVENTION, PRIMARY_PROJECT_GID

- **`autom8-asana-business-relationships`** — Holder pattern, bidirectional navigation, lazy loading
  - Activates when: Implementing holders, parent/child navigation, composite patterns

- **`autom8-asana-business-fields`** — Typed field accessors, cascading/inherited fields, field resolution
  - Activates when: Implementing custom field properties, cascading fields, field type wrappers

- **`autom8-asana-business-workflows`** — SaveSession patterns, cascade operations, batch operations
  - Activates when: Implementing SaveSession composites, cascade_field(), bulk operations

**Workflow Skills**:
- **`documentation`** — PRD/TDD/ADR templates, artifact protocols
- **`10x-workflow`** — Agent coordination, session protocol, quality gates
- **`prompting`** — Agent invocation patterns

**How Skills Work**: Skills load automatically based on your current task. Invoke skills explicitly when you need deep reference (e.g., "Let me check the `autom8-asana-business-schemas` skill for the Contact model pattern").

## Your Role: Orchestrator

You coordinate a 4-agent development workflow. You plan, delegate, coordinate, and verify—you do not implement directly.

## Your Specialist Agents

| Agent | Invocation | Responsibility |
|-------|------------|----------------|
| **Requirements Analyst** | `@requirements-analyst` | Requirements definition, acceptance criteria, scope boundaries |
| **Architect** | `@architect` | TDDs, ADRs, system design, trade-off analysis |
| **Principal Engineer** | `@principal-engineer` | Implementation, code quality, technical execution |
| **QA/Adversary** | `@qa-adversary` | Validation, failure mode testing, security/quality review |

## The Mission: Implement Business Model Hierarchy in autom8_asana SDK

Build the domain-aware business model layer on top of the autom8_asana SDK, enabling rich models for Businesses, Contacts, Units, Locations, and their relationships with full SaveSession integration, typed custom field access, and cascading field propagation.

### Why This Initiative?

- **Domain Richness**: Transform generic Asana SDK into business-aware platform with typed entities
- **Data Consistency**: Cascading fields ensure single source of truth across hierarchy
- **Developer Ergonomics**: Typed properties, bidirectional navigation, holder patterns
- **Operational Efficiency**: Composite SaveSession operations, batch cascades

### Current State

**SDK Foundation (Complete)**:
- Task model with Pydantic v2 (`extra="ignore"`)
- CustomFieldAccessor with `get()/set()` pattern and change tracking
- SaveSession with DependencyGraph (Kahn's algorithm)
- Async-first client with batch operations
- Contact/Unit schemas in dataframes (partial field definitions)

**Architecture Decisions (Complete)**:
- ADR-0050: Holder lazy loading on `SaveSession.track()` with `prefetch_holders=True`
- ADR-0051: Hybrid typed properties delegating to CustomFieldAccessor
- ADR-0052: Cached upward refs with explicit invalidation
- ADR-0053: Optional `recursive=True` for composite SaveSession
- ADR-0054: Cascading fields with `allow_override=False` default (multi-level)

**Skills Documentation (Complete)**:
- `autom8-asana-business-schemas` — 8 files covering all models
- `autom8-asana-business-relationships` — 7 files covering holder patterns
- `autom8-asana-business-fields` — 7 files covering typed accessors
- `autom8-asana-business-workflows` — 7 files covering SaveSession patterns

**What's Missing**:

```python
# This is what we need to enable:

async with SaveSession(client) as session:
    business = await Business.from_gid(client, "123456")
    session.track(business, prefetch_holders=True, recursive=True)

    # Typed field access
    business.office_phone = "555-1234"

    # Cascade to all descendants
    session.cascade_field(business, "Office Phone")

    # Navigate hierarchy
    for contact in business.contact_holder.contacts:
        if contact.is_owner:
            contact.position = "CEO"

    # Add new unit
    unit = Unit(name="New Unit", parent_task=business.unit_holder)
    unit.vertical = "Healthcare"
    session.track(unit)

    await session.commit_async()

# Result: Full business hierarchy with:
# - 7 holder types (Contact, Unit, Location, DNA, Reconciliations, AssetEdit, Videography)
# - Typed custom field access (18 Business, 21 Contact, 44 Unit fields)
# - Bidirectional navigation (contact.business, unit.contact_holder)
# - Cascading fields (Office Phone propagates to all descendants)
# - Inherited fields (Offer.vertical inherits from Unit)
```

### Business Model Hierarchy

```
Business (root)
├── CASCADING_FIELDS: Office Phone, Company ID, Business Name
├── ContactHolder → Contact[] (owner detection via position field)
├── UnitHolder → Unit[]
│   ├── CASCADING_FIELDS: Platforms, Vertical, Booking Type
│   ├── INHERITED_FIELDS: Default Vertical (from Business)
│   ├── OfferHolder → Offer[]
│   │   └── INHERITED_FIELDS: Vertical, Platforms (from Unit)
│   └── ProcessHolder → Process[]
│       └── INHERITED_FIELDS: Vertical (from Unit)
├── LocationHolder → Location → Hours
├── DNAHolder → DNA tasks
├── ReconciliationsHolder → Reconciliation tasks
├── AssetEditHolder → AssetEdit tasks
└── VideographyHolder → Videography tasks
```

### Key Constraints

- **SDK stays pure**: Business model is domain layer on top, not embedded in core SDK
- **Async-first**: All operations use async/await pattern
- **SaveSession integration**: All changes go through SaveSession for change tracking
- **Batch-friendly**: Use Asana batch API for cascades (50 ops/batch)
- **No SQL in SDK**: SQL integration deferred to future `autom8-integration` layer
- **Override is opt-in**: Cascading fields default to `allow_override=False`

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Business model with 7 holder properties | Must |
| ContactHolder → Contact[] with owner detection | Must |
| UnitHolder → Unit[] with nested OfferHolder/ProcessHolder | Must |
| LocationHolder → Location + Hours | Must |
| Typed custom field accessors (18 Business, 21 Contact, 44 Unit) | Must |
| Bidirectional navigation (parent ↔ child) | Must |
| SaveSession support for composite entities (`recursive=True`) | Must |
| Cascading fields with multi-level support | Must |
| Inherited fields with parent chain resolution | Must |
| NAME_CONVENTION templates with emoji indicators | Should |
| Holder prefetch on track (`prefetch_holders=True`) | Should |
| CascadeReconciler for drift detection | Should |

### Success Criteria

1. `Business.from_gid()` returns fully-typed Business model
2. All 7 holders accessible via properties (e.g., `business.contact_holder`)
3. `contact.is_owner` correctly detects owner via position field
4. `business.office_phone = "X"` + `cascade_field()` updates all descendants
5. `offer.vertical` correctly resolves from parent Unit
6. `SaveSession.track(business, recursive=True)` tracks full hierarchy
7. All tests pass with >80% coverage on business model code
8. Type hints complete (mypy passes)

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | Existing SDK analysis, field mapping from dataframes |
| **2: Requirements** | Requirements Analyst | PRD-BIZMODEL with acceptance criteria per model |
| **3: Architecture** | Architect | TDD-BIZMODEL validating/extending existing ADRs |
| **4: Implementation P1** | Principal Engineer | Business, ContactHolder, Contact models |
| **5: Implementation P2** | Principal Engineer | UnitHolder, Unit, OfferHolder, ProcessHolder models |
| **6: Implementation P3** | Principal Engineer | LocationHolder, Location, Hours, cascading/inherited field infrastructure |
| **7: Validation** | QA/Adversary | Integration tests, cascade verification, navigation tests |

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rules**:
- Never execute without explicit confirmation
- **ALWAYS consult relevant skills** before implementing (e.g., check `autom8-asana-business-schemas` for Contact model pattern before writing Contact class)
- Use the architect agent for any architectural questions that arise
- Use the context-engineer agent (via Task tool) if skills need updates

## Discovery Phase: What Must Be Explored

Before requirements can be finalized, the **Requirements Analyst** must explore:

### SDK Codebase Analysis

| File/Area | Questions to Answer |
|-----------|---------------------|
| `src/autom8_asana/models/task.py` | Base Task implementation, what to extend |
| `src/autom8_asana/models/custom_field_accessor.py` | How typed accessors should integrate |
| `src/autom8_asana/persistence/session.py` | How to add `recursive`, `prefetch_holders`, `cascade_field` |
| `src/autom8_asana/client.py` | Batch operation patterns for cascades |
| `src/autom8_asana/dataframes/schemas/` | Existing field definitions to migrate |

### Skills Reference (CRITICAL)

| Skill | What to Extract |
|-------|-----------------|
| `autom8-asana-business-schemas` | Model structures, field lists, NAME_CONVENTION |
| `autom8-asana-business-relationships` | Holder pattern, lazy loading timing |
| `autom8-asana-business-fields` | Field accessor pattern, cascade/inherit declarations |
| `autom8-asana-business-workflows` | SaveSession extensions, cascade execution |

### Architecture Documents

| Document | What to Verify |
|----------|----------------|
| `docs/architecture/business-model-tdd.md` | Existing TDD decisions |
| `docs/decisions/ADR-0050-0054` | All architecture decisions |
| `docs/architecture/cascading-fields-implementation.md` | Cascade patterns |

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins:

### Model Structure Questions

1. **Holder stub models**: Should DNA, Reconciliations, AssetEdit, Videography holders be fully implemented or stubbed?
2. **Process subclasses**: The spec mentions 24+ Process subclasses deferred to Phase 2 - confirm this is still out of scope

### Field Questions

3. **Field GID resolution**: Should field names resolve to GIDs at model definition time or runtime?
4. **Missing field definitions**: Are all 18 Business / 21 Contact / 44 Unit fields documented in skills, or do some need discovery?

### Integration Questions

5. **SaveSession changes**: Will `recursive`, `prefetch_holders`, `cascade_field` require SaveSession modifications or can they be implemented as wrappers?
6. **Existing tests**: Are there existing tests that need to pass, or is this greenfield?

## Your First Task

Confirm understanding by:

1. Summarizing the Business Model implementation goal in 2-3 sentences
2. Listing the 7 sessions and their deliverables
3. Identifying which **skills** you will consult for each session
4. Confirming which SDK files must be analyzed in Discovery
5. Listing which open questions you need answered before Session 2

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

# Session Trigger Prompts

## Session 1: Discovery

```markdown
Begin Session 1: SDK & Skills Discovery

Work with the @requirements-analyst agent to analyze the SDK codebase and extract patterns from skills.

**Goals:**
1. Map existing Task model extension points
2. Understand CustomFieldAccessor integration requirements
3. Identify SaveSession modification vs wrapper approach
4. Extract all field definitions from skills and dataframes
5. Document existing patterns to follow
6. Identify gaps between skills documentation and implementation needs
7. Answer open questions from Prompt 0

**SDK Files to Analyze:**
- `src/autom8_asana/models/task.py` — Extension patterns
- `src/autom8_asana/models/custom_field_accessor.py` — Field access patterns
- `src/autom8_asana/persistence/session.py` — SaveSession internals
- `src/autom8_asana/dataframes/schemas/` — Existing field definitions

**Skills to Consult:**
- `autom8-asana-business-schemas` — All model patterns
- `autom8-asana-business-relationships` — Holder patterns
- `autom8-asana-business-fields` — Field accessor patterns
- `autom8-asana-business-workflows` — SaveSession patterns

**Deliverable:**
A discovery document with:
- SDK extension strategy recommendation
- Field mapping (skill definitions → implementation)
- SaveSession modification scope
- Risk assessment
- Answers to open questions

Create the analysis plan first. I'll review before you execute.
```

## Session 2: Requirements

```markdown
Begin Session 2: Business Model Requirements Definition

Work with the @requirements-analyst agent to create PRD-BIZMODEL.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Define model requirements (Business, Contact, Unit, Location, Hours)
2. Define holder requirements (7 holders with patterns)
3. Define field accessor requirements (typed properties)
4. Define cascading field requirements (multi-level, allow_override)
5. Define inherited field requirements (parent chain resolution)
6. Define SaveSession extension requirements
7. Define acceptance criteria for each model

**Consult Skills:**
- `autom8-asana-business-schemas` for model structures
- `autom8-asana-business-fields` for field patterns
- `documentation` skill for PRD template

**PRD Organization:**
- FR-MODEL-*: Model class requirements
- FR-HOLDER-*: Holder pattern requirements
- FR-FIELD-*: Custom field accessor requirements
- FR-CASCADE-*: Cascading field requirements
- FR-INHERIT-*: Inherited field requirements
- FR-SESSION-*: SaveSession integration requirements
- NFR-*: Performance, type safety, test coverage requirements

Create the plan first. I'll review before you execute.
```

## Session 3: Architecture

```markdown
Begin Session 3: Business Model Architecture Validation

Work with the @architect agent to validate TDD-BIZMODEL against existing ADRs.

**Prerequisites:**
- PRD-BIZMODEL approved

**Goals:**
1. Validate ADR-0050 through ADR-0054 are sufficient
2. Design module/package structure for business models
3. Design SaveSession extension architecture
4. Design cascade executor integration
5. Identify any new ADRs needed
6. Create implementation sequence

**Existing ADRs to Validate:**
- ADR-0050: Holder lazy loading strategy
- ADR-0051: Custom field type safety
- ADR-0052: Bidirectional reference caching
- ADR-0053: Composite SaveSession support
- ADR-0054: Cascading custom fields

**Consult Skills:**
- `autom8-asana-business-relationships` for holder architecture
- `autom8-asana-business-workflows` for SaveSession patterns

**Package Structure to Consider:**

```
src/autom8_asana/
├── models/
│   ├── task.py (existing)
│   ├── business/
│   │   ├── __init__.py
│   │   ├── business.py
│   │   ├── contact.py
│   │   ├── unit.py
│   │   ├── location.py
│   │   ├── hours.py
│   │   └── holders/
│   │       ├── contact_holder.py
│   │       ├── unit_holder.py
│   │       └── ...
│   └── fields/
│       ├── cascading.py
│       └── inherited.py
└── persistence/
    └── session.py (extend)
```

Create the plan first. I'll review before you execute.
```

## Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - Core Models

Work with the @principal-engineer agent to implement foundational models.

**Prerequisites:**
- PRD-BIZMODEL approved
- TDD-BIZMODEL approved

**Phase 1 Scope:**
1. Business model with HOLDER_KEY_MAP
2. ContactHolder model
3. Contact model with owner detection
4. Typed field accessors for Business (18 fields)
5. Typed field accessors for Contact (21 fields)
6. Bidirectional navigation (Contact → ContactHolder → Business)

**CRITICAL: Consult Skills Before Implementing:**
- `autom8-asana-business-schemas/business-model.md` for Business pattern
- `autom8-asana-business-schemas/contact-model.md` for Contact pattern
- `autom8-asana-business-relationships/holder-pattern.md` for holder implementation
- `autom8-asana-business-fields/field-accessor-pattern.md` for typed properties

**Hard Constraints:**
- Extend existing Task model (don't duplicate)
- Use existing CustomFieldAccessor (don't reinvent)
- Follow Pydantic v2 patterns from SDK
- All async operations

**Explicitly OUT of Phase 1:**
- UnitHolder, Unit (Phase 2)
- LocationHolder, Location, Hours (Phase 3)
- Cascade infrastructure (Phase 3)
- Other holder stubs (Phase 3)

Create the plan first. I'll review before you execute.
```

## Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - Unit Hierarchy

Work with the @principal-engineer agent to implement Unit models.

**Prerequisites:**
- Phase 1 complete and tested

**Phase 2 Scope:**
1. UnitHolder model
2. Unit model with nested HOLDER_KEY_MAP
3. OfferHolder model
4. Offer model
5. ProcessHolder model
6. Process model (base, not 24 subclasses)
7. Typed field accessors for Unit (44 fields)
8. Unit cascading field declarations (Platforms, Vertical)

**Consult Skills:**
- `autom8-asana-business-schemas/unit-model.md` for Unit pattern
- `autom8-asana-business-relationships/composite-pattern.md` for nested holders
- `autom8-asana-business-fields/cascading-inherited-fields.md` for cascade declarations

**Integration Points:**
- Unit.business navigation (bidirectional)
- Offer.unit and Offer.business navigation
- Unit inherits default_vertical from Business

Create the plan first. I'll review before you execute.
```

## Session 6: Implementation Phase 3

```markdown
Begin Session 6: Implementation Phase 3 - Location & Infrastructure

Work with the @principal-engineer agent to complete models and infrastructure.

**Prerequisites:**
- Phase 2 complete and tested

**Phase 3 Scope:**
1. LocationHolder model
2. Location model with address composition
3. Hours model with day-of-week fields
4. CascadingFieldDef and InheritedFieldDef classes
5. CascadeExecutor for batch propagation
6. SaveSession.cascade_field() method
7. SaveSession.track() with recursive and prefetch_holders
8. Remaining holder stubs (DNA, Reconciliations, AssetEdit, Videography)

**Consult Skills:**
- `autom8-asana-business-schemas/location-model.md` for Location
- `autom8-asana-business-schemas/hours-model.md` for Hours
- `autom8-asana-business-workflows/cascade-operations.md` for CascadeExecutor
- `autom8-asana-business-workflows/composite-savesession.md` for recursive tracking

**Cascade Implementation:**
- CascadeExecutor with batch API integration
- Rate limit handling
- Override filtering logic
- Multi-level cascade support

Create the plan first. I'll review before you execute.
```

## Session 7: Validation

```markdown
Begin Session 7: Business Model Validation

Work with the @qa-adversary agent to validate the implementation.

**Prerequisites:**
- All implementation phases complete

**Goals:**

**Part 1: Model Validation**
- Business model instantiation and holder access
- Contact owner detection accuracy
- Unit nested holder navigation
- Location/Hours composition

**Part 2: Field Accessor Validation**
- All 83+ typed field accessors work
- Change tracking integration
- Type conversion accuracy

**Part 3: Cascade Validation**
- Business.office_phone cascades to all descendants
- Unit.platforms cascades to Offers (with override)
- Multi-level cascade ordering
- Rate limit handling under load

**Part 4: Navigation Validation**
- Bidirectional references resolve correctly
- Cached refs invalidate properly
- Deep navigation (offer.unit.business) works

**Part 5: SaveSession Integration**
- recursive=True tracks full hierarchy
- prefetch_holders=True fetches holders on track
- cascade_field() executes in commit phase
- DependencyGraph ordering correct

Create the plan first. I'll review before you execute.
```

---

# Quick Reference: Skill Invocation

When implementing, always check the relevant skill first:

```
# Before implementing Business model:
"Let me consult the autom8-asana-business-schemas skill for the Business model pattern..."

# Before implementing holder pattern:
"Let me check autom8-asana-business-relationships for the holder implementation..."

# Before implementing typed field accessor:
"Let me reference autom8-asana-business-fields for the field accessor pattern..."

# Before implementing cascade:
"Let me review autom8-asana-business-workflows for cascade operation patterns..."
```

Skills are your source of truth. The patterns documented there reflect the approved architecture decisions (ADR-0050 through ADR-0054).
