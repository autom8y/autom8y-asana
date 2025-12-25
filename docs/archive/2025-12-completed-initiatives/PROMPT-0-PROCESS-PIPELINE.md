# Orchestrator Initialization: Process Pipeline and Salesforce Replacement

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`autom8-asana`** - SDK patterns, SaveSession, Business entities, detection, batch operations
  - Activates when: Working with Process entities, holders, detection, SaveSession integration

- **`documentation`** - PRD/TDD/ADR templates, workflow pipeline, quality gates
  - Activates when: Creating/reviewing PRD, TDD, ADR, or Test Plan

- **`standards`** - Tech stack decisions, code conventions, repository structure
  - Activates when: Writing code, choosing libraries, organizing files

- **`10x-workflow`** - Agent coordination, session protocol, quality gates
  - Activates when: Planning phases, coordinating handoffs, checking quality criteria

- **`prompting`** - Agent invocation patterns, workflow examples
  - Activates when: Invoking agents, structuring prompts

**How Skills Work**: Skills load automatically based on your current task. When you need template formats, the `documentation` skill activates. When you need SDK-specific patterns, the `autom8-asana` skill activates.

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

## The Mission: Model Process entities as pipeline events to replace Salesforce for sales team workflow

The autom8_asana SDK treats Asana as a structured database for business entities. Process entities are **events** (not dimensions like Business, Unit, Offer) representing workflow stages: Outreach, Sales, Onboarding, Implementation, Retention, Reactivation. This initiative properly models Process entities with pipeline semantics, enabling the sales team to operate entirely within Asana while maintaining cross-team coordination and external system integration (Calendly, webhooks).

### Why This Initiative?

- **Salesforce Replacement**: Sales team can work leads without context-switching to Salesforce
- **Pipeline Visibility**: Cross-team visibility from lead capture through implementation
- **Integration Foundation**: Webhook-driven automation for external systems (Calendly bookings, etc.)
- **Architectural Correctness**: Events (Process) deserve different semantics than dimensions (Business, Unit, Offer)
- **Efficiency**: Replace bespoke legacy integrations with SDK-standard patterns

### Current State

**Process Entity (Implemented but Incomplete)**:
- Base `Process` class extends `BusinessEntity` with 8 custom field descriptors
- `ProcessHolder` follows standard holder pattern under Unit
- `ProcessType` enum has only `GENERIC` - no pipeline types
- `process_type` property always returns `GENERIC`
- Navigation works: Process -> ProcessHolder -> Unit -> Business

**What Exists**:
- `PRIMARY_PROJECT_GID: ClassVar[str | None] = None` (stubbed, no project)
- Detection system (ADR-0093, ADR-0094) provides registry infrastructure
- SaveSession supports `move_to_section()` and `add_to_project()` operations
- Section model and SectionsClient implemented
- WebhooksClient implemented

**What's Missing**:

```python
# This is what we need to enable:

# 1. Pipeline-aware process creation
process = SalesProcess(name="Acme Corp - Demo Call")
process.pipeline_state  # -> ProcessSection.OPPORTUNITY

# 2. State transitions via section movement
async with SaveSession(client) as session:
    session.track(process)
    process.transition_to(ProcessSection.CONVERTED)  # Queues section move
    await session.commit_async()

# 3. Entity seeding for integrations
seeder = BusinessSeeder(client)
result = await seeder.seed_async(
    business_name="Acme Corp",
    process_type=ProcessType.SALES,
    assigned_to="sales_rep_gid",
    notes="Calendly booking - demo call",
)
# Creates: Business -> Unit -> ProcessHolder -> SalesProcess
# Adds Process to Sales Pipeline project (dual membership)

# 4. Process type detection from project
entity_type = detect_entity_type(task)  # -> EntityType.SALES_PROCESS
```

### Process Entity Profile

| Attribute | Value |
|-----------|-------|
| Primary Language | Python 3.10+ |
| Framework | Pydantic v2, async-first |
| Location | `src/autom8_asana/models/business/process.py` |
| Hierarchy Position | Business > Unit > ProcessHolder > Process |
| Key Distinction | Event (state-based) vs Dimension (identity-based) |
| Pipeline Projects | One per ProcessType (Sales Pipeline, Onboarding Pipeline, etc.) |

### Target Architecture

```
External Trigger (Calendly, Form, etc.)
         |
         v
+-------------------+
|  BusinessSeeder   |  Factory for entity creation
|  (Integration)    |
+-------------------+
         |
         v
+-------------------+     +-------------------+
|  Business         |     |  ProcessProject   |  Pipeline view
|  > Unit           |     |  (Sales Pipeline) |
|    > ProcessHolder|     +-------------------+
|      > Process <--|-------> dual membership
+-------------------+
         |
         v
+-------------------+
|  Section Move     |  State transition
|  (OPPORTUNITY ->  |
|   CONVERTED)      |
+-------------------+
         |
         v
+-------------------+
|  Webhook Fires    |  Integration point
|  (section_change) |
+-------------------+
         |
         v
+-------------------+
|  Next Pipeline    |  Sales -> Onboarding -> Implementation
|  Stage Created    |
+-------------------+
```

### Key Constraints

- **Public SDK**: Patterns must be generalizable across workspaces (no hardcoded GIDs)
- **Event vs Dimension Semantics**: Section membership = state (not category)
- **Dual Membership**: Process in hierarchy AND pipeline project simultaneously
- **No Business Logic**: SDK provides primitives; workflow rules stay in consumers
- **Backward Compatible**: Existing Process/ProcessHolder code must continue working
- **Async-First**: All new interfaces async; sync wrappers where needed
- **Integration-Friendly**: Enable but don't implement Calendly, webhook handling

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Expand ProcessType enum (SALES, OUTREACH, ONBOARDING, IMPLEMENTATION, RETENTION, REACTIVATION) | Must |
| Add ProcessSection enum for pipeline states (OPPORTUNITY, DELAYED, ACTIVE, SCHEDULED, CONVERTED, DID_NOT_CONVERT) | Must |
| ProcessProjectRegistry mapping ProcessType to project GIDs | Must |
| Process.pipeline_state property from section membership | Must |
| Process type detection via project membership (Tier 1) | Must |
| Dual membership support (hierarchy + pipeline project) | Must |
| State transition helpers (transition_to method or pattern) | Must |
| BusinessSeeder factory for integration patterns | Should |
| Webhook event parsing helpers for section changes | Should |
| Process subclasses (SalesProcess, OnboardingProcess, etc.) | Could |
| Pipeline state machine validation (allowed transitions) | Could |
| Healing for missing pipeline project membership | Nice |

### Success Criteria

1. ProcessType enum includes all 6 pipeline stages
2. ProcessSection enum models standard pipeline sections
3. Process.pipeline_state returns current section-based state
4. Process type detection works via pipeline project membership
5. Dual membership correctly modeled (hierarchy + project)
6. State transitions possible via SaveSession
7. BusinessSeeder creates complete entity hierarchies
8. All existing Process tests pass (backward compatibility)
9. Integration patterns documented with examples

### Performance Targets

| Metric | Development | Production |
|--------|-------------|------------|
| Process Type Detection | <1ms | <1ms |
| Pipeline State Access | <1ms | <1ms |
| Entity Seeding (full hierarchy) | <500ms | <200ms |
| State Transition (section move) | <100ms | <50ms |
| Batch Webhook Processing | 10 events/batch | 10 events/batch |

---

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | Legacy pattern analysis, process project audit, integration flow documentation |
| **2: Requirements** | Requirements Analyst | PRD-PROCESS-PIPELINE with acceptance criteria per component |
| **3: Architecture** | Architect | TDD-PROCESS-PIPELINE + ADRs for registry, state machine, seeding patterns |
| **4: Implementation P1** | Principal Engineer | ProcessType expansion, ProcessSection enum, registry |
| **5: Implementation P2** | Principal Engineer | pipeline_state property, dual membership, detection integration |
| **6: Implementation P3** | Principal Engineer | BusinessSeeder factory, state transition helpers |
| **7: Validation** | QA/Adversary | Pipeline flow testing, integration pattern validation, edge cases |

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

### Codebase Analysis

| File/Area | Questions to Answer |
|-----------|---------------------|
| `src/autom8_asana/models/business/process.py` | Current Process/ProcessHolder implementation, extension points |
| `src/autom8_asana/models/business/registry.py` | ProjectTypeRegistry pattern, can it extend to ProcessProject? |
| `src/autom8_asana/models/business/detection.py` | Detection tiers, how to add ProcessType-specific detection |
| `src/autom8_asana/persistence/session.py` | move_to_section(), add_to_project() - how to compose for transitions |
| `src/autom8_asana/models/section.py` | Section model, how to map to ProcessSection enum |
| `src/autom8_asana/clients/webhooks.py` | Webhook event structure, section change events |

### Legacy System Audit

| Resource/System | Questions to Answer |
|-----------------|---------------------|
| Legacy pipeline implementation | How does current Calendly -> Sales flow work? |
| Process project structure | What projects exist? What sections do they have? |
| Section naming conventions | Are sections named consistently across pipeline projects? |
| Webhook handlers | What events are consumed? How is section change detected? |
| Entity seeding patterns | How does legacy create Business + Unit + Process atomically? |
| Cross-team handoffs | How does Sales -> Onboarding transition work? |

### Process Project Inventory

| Process Type | Questions |
|--------------|-----------|
| Sales | What's the project GID? What sections exist? What custom fields? |
| Outreach | Same questions - is structure identical to Sales? |
| Onboarding | Same questions - what triggers creation? |
| Implementation | Same questions - how linked to Onboarding completion? |
| Retention | Same questions - ongoing vs triggered? |
| Reactivation | Same questions - how identified? |

### Integration Pattern Analysis

| Integration | Questions |
|-------------|-----------|
| Calendly | What data comes from booking? How is business matched/created? |
| Form submissions | What other entry points exist beyond Calendly? |
| Webhook consumption | What systems listen for section changes? |
| CRM sync | Any bidirectional sync with Salesforce during transition? |

---

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins, the following questions need answers:

### Process Model Questions

1. **Process subclasses vs single type**: Should we have `SalesProcess`, `OnboardingProcess` subclasses, or single `Process` class with `process_type` attribute?
2. **Section membership extraction**: How do we efficiently get section from task memberships without API call?
3. **Dual membership creation**: Should SDK handle adding to pipeline project automatically, or explicit consumer action?
4. **ProcessType from project vs custom field**: Primary detection via project membership, but what's fallback?

### Pipeline State Questions

5. **Standard vs custom sections**: Are the 7 sections (OPPORTUNITY, etc.) universal, or do some pipelines differ?
6. **Section GID mapping**: How do we map section GIDs to ProcessSection enum values?
7. **State validation**: Should SDK enforce valid transitions (e.g., OPPORTUNITY -> ACTIVE allowed, but not CONVERTED -> OPPORTUNITY)?
8. **Terminal states**: Are CONVERTED and DID_NOT_CONVERT truly terminal, or can processes be reopened?

### Integration Questions

9. **BusinessSeeder scope**: Full hierarchy (Business + Unit + ProcessHolder + Process) or just Process placement?
10. **Seeder idempotency**: If Business already exists, create under existing or fail?
11. **Webhook helpers scope**: Parse events only, or also routing/dispatch helpers?
12. **Cross-pipeline transitions**: When Sales converts, does SDK create Onboarding Process, or just signal completion?

### Configuration Questions

13. **Environment variable pattern**: `ASANA_SALES_PROJECT_GID` or `AUTOM8_PROCESS_PROJECT_SALES`?
14. **Section GID configuration**: Hardcode section names (match by name) or configure GIDs?
15. **Multi-workspace ProcessProjects**: Same pattern as entity detection registry override?

---

## Scope Boundaries

### Explicitly In Scope

- ProcessType enum expansion to 6+ pipeline types
- ProcessSection enum for standard pipeline states
- ProcessProjectRegistry for process-type-to-project mapping
- Process.pipeline_state property
- Dual membership model and creation helpers
- State transition helpers (section move composition)
- BusinessSeeder factory for entity hierarchy creation
- Detection integration for process type
- Documentation and examples for integration patterns

### Explicitly Out of Scope

- Workflow orchestration logic (business rules for transitions)
- Calendly integration implementation (SDK provides primitives)
- Webhook event routing/dispatch (consumers handle)
- State machine enforcement (allowed transitions - consumers validate)
- Salesforce sync implementation
- Pipeline analytics/reporting
- Process-specific custom field schemas (beyond existing 8 fields)
- UI/dashboard concerns

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Process project structure varies by pipeline type | Medium | High | Audit all projects in Discovery; design for flexibility |
| Legacy integration patterns too bespoke | Medium | Medium | Focus on primitives, not full workflow replication |
| Section naming inconsistent across projects | Medium | Medium | Match by name pattern, allow GID override |
| Dual membership complexity in SaveSession | Low | High | Careful design in TDD; incremental implementation |
| Backward compatibility breakage | Low | High | Preserve existing Process/ProcessHolder behavior; add, don't change |
| BusinessSeeder scope creep | Medium | Medium | Define clear boundaries in PRD; phase if needed |

---

## Your First Task

Confirm understanding by:

1. Summarizing the Process Pipeline initiative goal in 2-3 sentences
2. Listing the 7 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step before requirements
4. Confirming which files/systems must be analyzed before PRD-PROCESS-PIPELINE
5. Listing which open questions you need answered before Session 2
6. Noting the key distinction: Process entities are **events** (state-based) not **dimensions** (identity-based)

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

# Session Trigger Prompts

## Session 1: Discovery

```markdown
Begin Session 1: Process Pipeline Discovery

Work with the @requirements-analyst agent to analyze the current Process implementation and audit legacy pipeline patterns.

**Goals:**
1. Map current Process/ProcessHolder implementation and extension points
2. Audit all existing process project GIDs and their sections
3. Document legacy Calendly -> Sales -> Onboarding flow
4. Understand entity seeding patterns in legacy system
5. Identify webhook event patterns for section changes
6. Document cross-team handoff patterns
7. Catalog differences between pipeline types (Sales vs Onboarding vs Implementation)

**Files to Analyze:**
- `src/autom8_asana/models/business/process.py` - Current implementation
- `src/autom8_asana/models/business/registry.py` - Registry pattern reference
- `src/autom8_asana/models/business/detection.py` - Detection integration points
- `src/autom8_asana/persistence/session.py` - SaveSession operations
- `src/autom8_asana/clients/webhooks.py` - Webhook patterns
- `docs/analysis/ANALYSIS-PROCESS-ENTITIES.md` - Architect analysis

**Legacy System to Audit:**
- Process pipeline project inventory (GIDs, sections, custom fields)
- Calendly integration flow
- Entity seeding implementation
- Webhook event handlers
- Cross-pipeline transition patterns

**Deliverable:**
A discovery document with:
- Complete process project inventory (GID, sections per type)
- Legacy integration flow diagrams
- Extension point analysis for Process/ProcessHolder
- Open questions resolved or escalated
- Risk register for pipeline-specific variations

Create the analysis plan first. I'll review before you execute.
```

## Session 2: Requirements

```markdown
Begin Session 2: Process Pipeline Requirements Definition

Work with the @requirements-analyst agent to create PRD-PROCESS-PIPELINE.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Define ProcessType expansion requirements
2. Define ProcessSection enum requirements
3. Define ProcessProjectRegistry requirements
4. Define pipeline_state property requirements
5. Define dual membership requirements
6. Define state transition requirements
7. Define BusinessSeeder requirements
8. Define acceptance criteria for each component

**Key Questions to Address:**
- What ProcessType values are needed?
- What ProcessSection values are standard?
- How does Process.pipeline_state derive from memberships?
- What's the dual membership creation pattern?
- What's the BusinessSeeder factory interface?

**PRD Organization:**
- FR-TYPE-*: ProcessType enum requirements
- FR-SECTION-*: ProcessSection enum requirements
- FR-REG-*: ProcessProjectRegistry requirements
- FR-STATE-*: Pipeline state access requirements
- FR-DUAL-*: Dual membership requirements
- FR-TRANS-*: State transition requirements
- FR-SEED-*: BusinessSeeder requirements
- FR-COMPAT-*: Backward compatibility requirements
- NFR-*: Performance, reliability requirements

Create the plan first. I'll review before you execute.
```

## Session 3: Architecture

```markdown
Begin Session 3: Process Pipeline Architecture Design

Work with the @architect agent to create TDD-PROCESS-PIPELINE and foundational ADRs.

**Prerequisites:**
- PRD-PROCESS-PIPELINE approved

**Goals:**
1. Design ProcessType expansion and detection integration
2. Design ProcessSection enum and section-to-enum mapping
3. Design ProcessProjectRegistry (extend existing pattern)
4. Design pipeline_state derivation from memberships
5. Design dual membership model
6. Design state transition composition pattern
7. Design BusinessSeeder factory interface

**Required ADRs:**
- ADR-0096: ProcessType Expansion and Detection
- ADR-0097: ProcessSection State Machine Pattern
- ADR-0098: Dual Membership Model (Hierarchy + Pipeline)
- ADR-0099: BusinessSeeder Factory Pattern
- ADR-0100: State Transition Composition with SaveSession

**Module Structure to Consider:**

```
src/autom8_asana/models/business/
  +-- process.py              # ProcessType expansion, ProcessSection enum
  +-- process_registry.py     # NEW: ProcessProjectRegistry
  +-- seeding.py              # NEW: BusinessSeeder factory
  +-- detection.py            # Integration for process type detection
```

Create the plan first. I'll review before you execute.
```

## Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - Type and Section Enums

Work with the @principal-engineer agent to implement foundational enums and registry.

**Prerequisites:**
- PRD-PROCESS-PIPELINE approved
- TDD-PROCESS-PIPELINE approved
- ADRs documented

**Phase 1 Scope:**
1. Expand ProcessType enum (SALES, OUTREACH, ONBOARDING, IMPLEMENTATION, RETENTION, REACTIVATION)
2. Create ProcessSection enum (OPPORTUNITY, DELAYED, ACTIVE, SCHEDULED, CONVERTED, DID_NOT_CONVERT, OTHER)
3. Create ProcessProjectRegistry with __init_subclass__ pattern
4. Implement environment variable override for process project GIDs
5. Integrate with existing detection system (Tier 1 for process type)
6. Write unit tests for enums and registry

**Hard Constraints:**
- ProcessType.GENERIC must remain for backward compatibility
- Registry must follow existing ProjectTypeRegistry pattern
- Must not break existing Process tests
- Environment override takes precedence over ClassVar

**Explicitly OUT of Phase 1:**
- pipeline_state property (Phase 2)
- Dual membership helpers (Phase 2)
- BusinessSeeder (Phase 3)
- State transition helpers (Phase 3)

Create the plan first. I'll review before you execute.
```

## Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - State and Membership

Work with the @principal-engineer agent to implement state access and dual membership.

**Prerequisites:**
- Phase 1 complete and tested

**Phase 2 Scope:**
1. Implement Process.pipeline_state property (extract from memberships)
2. Implement section name -> ProcessSection mapping
3. Add Process.process_project property (pipeline project reference)
4. Implement dual membership creation helper
5. Add Process.is_in_pipeline property (has pipeline project membership)
6. Write integration tests for state and membership

**Integration Points:**
- Task.memberships for section extraction
- ProcessProjectRegistry for project-to-type mapping
- SaveSession for membership operations

Create the plan first. I'll review before you execute.
```

## Session 6: Implementation Phase 3

```markdown
Begin Session 6: Implementation Phase 3 - Seeding and Transitions

Work with the @principal-engineer agent to implement BusinessSeeder and transitions.

**Prerequisites:**
- Phase 2 complete and tested

**Phase 3 Scope:**
1. Create BusinessSeeder factory class
2. Implement seed_async() for full hierarchy creation
3. Implement transition_to() helper (or pattern) for state changes
4. Add section move composition with SaveSession
5. Implement webhook event parsing helpers
6. Add examples and documentation
7. Write integration tests for seeding and transitions

**BusinessSeeder Interface:**

```python
seeder = BusinessSeeder(client)
result = await seeder.seed_async(
    business_name="Acme Corp",
    process_type=ProcessType.SALES,
    assigned_to="user_gid",
    due_date=datetime.now() + timedelta(days=1),
    notes="Lead from Calendly",
)
# result.business, result.unit, result.process_holder, result.process
```

Create the plan first. I'll review before you execute.
```

## Session 7: Validation

```markdown
Begin Session 7: Process Pipeline Validation

Work with the @qa-adversary agent to validate the implementation.

**Prerequisites:**
- All implementation phases complete
- Process pipeline integrated

**Goals:**

**Part 1: Functional Validation**
- ProcessType enum includes all pipeline types
- ProcessSection enum includes all states
- Process.pipeline_state returns correct state
- Process type detection works via project membership
- Dual membership correctly created and accessed

**Part 2: Integration Pattern Validation**
- BusinessSeeder creates complete hierarchy
- State transitions work via SaveSession
- Webhook event helpers parse section changes
- Cross-pipeline handoff pattern documented

**Part 3: Edge Case Testing**
- Process without pipeline project membership (fallback)
- Multiple pipeline project memberships (precedence)
- BusinessSeeder with existing Business (idempotency)
- Section name mismatches (fuzzy matching)
- Missing process project configuration

**Part 4: Performance Validation**
- Pipeline state access <1ms (no API call)
- Process type detection <1ms
- Entity seeding <500ms

**Part 5: Backward Compatibility**
- Existing Process tests pass
- ProcessType.GENERIC still works
- No breaking changes to public API

Create the plan first. I'll review before you execute.
```

---

# Context Gathering Checklist

Before starting, gather:

**Codebase Context:**

- [ ] `src/autom8_asana/models/business/process.py` - Current Process/ProcessHolder
- [ ] `src/autom8_asana/models/business/registry.py` - ProjectTypeRegistry pattern
- [ ] `src/autom8_asana/models/business/detection.py` - Detection system
- [ ] `src/autom8_asana/persistence/session.py` - SaveSession operations
- [ ] `docs/analysis/ANALYSIS-PROCESS-ENTITIES.md` - Architect analysis

**Process Project Inventory:**

- [ ] Sales Pipeline project GID and sections
- [ ] Outreach Pipeline project GID and sections
- [ ] Onboarding Pipeline project GID and sections
- [ ] Implementation Pipeline project GID and sections
- [ ] Retention Pipeline project GID and sections
- [ ] Reactivation Pipeline project GID and sections

**Legacy Integration Reference:**

- [ ] Calendly -> Sales flow documentation
- [ ] Entity seeding implementation
- [ ] Webhook event handlers
- [ ] Cross-pipeline transition logic
- [ ] Section naming conventions

**Configuration Strategy:**

- [ ] Environment variable naming pattern for process projects
- [ ] Section GID vs section name matching approach
- [ ] Multi-workspace configuration pattern
