# Orchestrator Initialization: Automation Layer for Pipeline Conversion

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`autom8-asana`** - SDK patterns, SaveSession, Business entities, detection, batch operations
  - Activates when: Working with automation rules, SaveSession hooks, entity operations

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

## The Mission: Add an Automation Layer to the SDK for Pipeline Conversion and Advancement

The autom8_asana SDK has evolved from an API wrapper into an Asana Automation Platform. The next evolution is an **Automation Layer** that enables pipeline conversion and advancement - the core functionality that makes "Asana as Salesforce" work. When a Process moves to CONVERTED section, the automation layer detects this, finds the appropriate template in the next-stage project, creates a new Process from that template, seeds it with inherited and computed fields, and places it correctly in the hierarchy and project.

### Why This Initiative?

- **Platform Evolution**: SDK graduates from "API wrapper" to "automation platform"
- **Pipeline Automation**: Enables Sales -> Onboarding -> Implementation flow without external orchestration
- **SDK-Native**: Automation is platform infrastructure (like Django signals), not consumer business logic
- **Zero External Infrastructure**: No queues, no workers - synchronous execution via post-commit hooks
- **Extensibility**: Rule protocol enables custom automation beyond pipeline conversion

### Current State

**SDK Layers (Implemented)**:
- Transport: HTTP, auth, retry
- Clients: API operations (tasks, projects, sections, webhooks)
- Models: Typed resources (Pydantic v2)
- Business Entities: Domain models (Business, Unit, Process with holders)
- Persistence: SaveSession, Unit of Work, change tracking
- Detection: 5-tier entity type detection, ProjectTypeRegistry

**SaveSession Operations Available**:
- `move_to_section(task_gid, section_gid)` - State transitions
- `add_to_project(task_gid, project_gid, section_gid)` - Dual membership
- Post-commit result available via `SaveResult`

**What's Missing**:

```python
# This is what we need to enable:

client = AsanaClient(
    token=TOKEN,
    automation=AutomationConfig(
        pipeline=PipelineConfig(
            enabled_pipelines={
                "sales_gid": "onboarding_gid",
                "onboarding_gid": "implementation_gid",
            },
        ),
    ),
)

# Normal usage - automation fires automatically
async with client.save_session() as session:
    process.move_to_section(converted_section)
    await session.commit()
    # Post-commit: automation detects conversion, creates next-stage Process

# Result:
# - New Process created from template in next-stage project
# - Fields seeded: cascade from Business/Unit, carry-through from source Process
# - Placed as subtask of ProcessHolder AND in next-stage project
```

### Automation Layer Profile

| Attribute | Value |
|-----------|-------|
| Primary Language | Python 3.10+ |
| Framework | Pydantic v2, async-first |
| Location | `src/autom8_asana/automation/` (NEW package) |
| Integration Point | SaveSession post-commit hooks |
| Configuration Style | AsanaClient initialization parameter |
| Execution Model | Synchronous (no external queue) |

### Target Architecture

```
SaveSession.commit()
         |
         v
+-------------------+
| Phase 1: CRUD     |  Standard entity operations
| Phase 2: Cascade  |  Field propagation
| Phase 3: Actions  |  add_tag, move_section, etc.
+-------------------+
         |
         v (post-commit)
+-------------------+
| AutomationEngine  |  Rule executor
|   (Post-Commit)   |
+-------------------+
         |
         v
+-------------------+     +-------------------+
| Rule Registry     |     | PipelineConfig    |
| [AutomationRule]  |     | enabled_pipelines |
+-------------------+     +-------------------+
         |
         v (rule matches)
+-------------------+
| PipelineConversion|  Specific rule implementation
| Rule              |
+-------------------+
         |
         v
+-------------------+
| TemplateDiscovery |  Find template in next-stage project
| (fuzzy match)     |
+-------------------+
         |
         v
+-------------------+
| Process Creation  |  Create from template, seed fields
| + Field Seeding   |  cascade + carry-through + computed
+-------------------+
         |
         v
+-------------------+
| Placement         |  Subtask of ProcessHolder + project membership
+-------------------+
```

### Key Constraints

- **Opt-In Configuration**: Automation disabled by default, enabled via `AutomationConfig`
- **Post-Commit Isolation**: Hooks fire AFTER transaction succeeds, never during
- **No External Infrastructure**: No Redis, no Celery, no SQS - synchronous execution
- **Rule Protocol**: Extensible via `AutomationRule` protocol, not hardcoded logic
- **Template Discovery via Fuzzy Match**: Section contains "template" (case-insensitive)
- **Field Seeding Composition**: Cascade (from hierarchy) + Carry-through (from source) + Computed
- **Async-First**: All automation operations async; sync wrapper if needed
- **No Breaking Changes**: Existing SaveSession behavior unchanged when automation disabled

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| `automation/` package structure parallel to `persistence/` | Must |
| `AutomationRule` protocol (trigger, execute, config) | Must |
| `AutomationEngine` rule executor with post-commit integration | Must |
| `PipelineConversionRule` implementation | Must |
| `PipelineConfig` for enabled pipeline mappings | Must |
| `AutomationConfig` for AsanaClient initialization | Must |
| `TemplateDiscovery` with fuzzy section matching | Must |
| Field seeding: cascade from Business/Unit | Must |
| Field seeding: carry-through from source Process | Must |
| SaveSession post-commit hook integration | Must |
| Process placement (subtask + project membership) | Must |
| Field seeding: computed fields (due_date) | Should |
| Automation result reporting in SaveResult | Should |
| Rule execution logging and metrics | Should |
| Dry-run mode for automation preview | Could |
| Rule priority ordering | Could |
| Rule condition DSL | Nice |

### Success Criteria

1. `AutomationConfig` accepted by AsanaClient constructor
2. `PipelineConfig` maps source project -> destination project
3. Post-commit hook fires for section changes to CONVERTED
4. Template found via fuzzy match in destination project's Templates section
5. New Process created with correct name pattern
6. Fields seeded correctly (cascade + carry-through + computed)
7. Process placed as subtask of correct ProcessHolder
8. Process added to destination project in correct section
9. Automation disabled by default (opt-in)
10. Existing tests pass (no regression)

### Performance Targets

| Metric | Development | Production |
|--------|-------------|------------|
| Post-commit hook latency | <10ms | <10ms |
| Template discovery | <200ms | <100ms |
| Full pipeline conversion | <1s | <500ms |
| Rule matching | <1ms | <1ms |
| Field seeding computation | <10ms | <10ms |

---

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | SaveSession extension points, template section patterns, field seeding inventory |
| **2: Requirements** | Requirements Analyst | PRD-AUTOMATION-LAYER with acceptance criteria per component |
| **3: Architecture** | Architect | TDD-AUTOMATION-LAYER + ADRs for rule protocol, hook integration, config pattern |
| **4: Implementation P1** | Principal Engineer | AutomationRule protocol, AutomationEngine, AutomationConfig |
| **5: Implementation P2** | Principal Engineer | PipelineConversionRule, TemplateDiscovery, PipelineConfig |
| **6: Implementation P3** | Principal Engineer | Field seeding, placement, SaveSession integration |
| **7: Validation** | QA/Adversary | Pipeline conversion E2E, edge cases, performance verification |

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
| `src/autom8_asana/persistence/session.py` | Where to add post-commit hooks? What's `SaveResult` structure? |
| `src/autom8_asana/persistence/pipeline.py` | SavePipeline phases - where does automation fit? |
| `src/autom8_asana/client.py` | How to pass AutomationConfig through? |
| `src/autom8_asana/models/business/process.py` | Process fields available for carry-through |
| `src/autom8_asana/clients/sections.py` | Section operations for template discovery |
| `src/autom8_asana/clients/tasks.py` | Task creation patterns for template-based Process |

### Template Pattern Audit

| Resource/System | Questions to Answer |
|-----------------|---------------------|
| Template section naming | What variations exist? "Templates", "Template Tasks", etc. |
| Template task structure | What fields are pre-populated on templates? |
| Template naming convention | `[ProcessType] Process - [Business Name]` pattern? |
| Pipeline project structure | Are all pipeline projects structured identically? |
| Section naming across projects | Are OPPORTUNITY, CONVERTED, etc. consistent? |

### Field Seeding Inventory

| Field Category | Questions |
|----------------|-----------|
| Cascade fields | Which fields come from Business? From Unit? |
| Carry-through fields | Which fields copy from source Process to destination? |
| Computed fields | What's computed at creation time? (due_date, created_at) |
| Assignment | How is rep/assignee determined for new Process? |

### Integration Point Analysis

| Area | Questions |
|------|-----------|
| Post-commit timing | When exactly does hook fire? What's available in context? |
| SaveSession state | What's accessible post-commit? SaveResult? Original entities? |
| Error handling | What happens if automation fails? Rollback? Log only? |
| Retry semantics | Should failed automation retry? Manual intervention? |

---

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins, the following questions need answers:

### Architecture Questions

1. **Hook registration**: Should rules register globally or per-session?
2. **Rule execution order**: When multiple rules match, what's the precedence?
3. **Transactionality**: Should automation operations be in a new SaveSession?
4. **Error isolation**: If automation fails, should original commit succeed?

### Template Discovery Questions

5. **Section matching**: Exact match "Templates" or fuzzy contains "template"?
6. **Template selection**: If multiple templates exist, how to pick correct one?
7. **Missing template**: What if no template found? Fail? Create minimal Process?
8. **Template refresh**: Cache templates or fetch fresh each time?

### Field Seeding Questions

9. **Field conflict**: When cascade and carry-through specify same field, which wins?
10. **Null handling**: Carry through null values or skip?
11. **Computed field list**: What exactly is computed? Just due_date?
12. **Custom field mapping**: Are field names identical across pipeline projects?

### Configuration Questions

13. **Pipeline mapping granularity**: Project GID -> Project GID, or Section -> Project?
14. **Per-rule config**: Can rules have individual configuration?
15. **Environment override**: Should pipeline mappings be overridable via env vars?
16. **Workspace scoping**: Multi-workspace automation configuration pattern?

---

## Scope Boundaries

### Explicitly In Scope

- `automation/` package structure (base, pipeline, templates, config)
- `AutomationRule` protocol with trigger/execute/config
- `AutomationEngine` rule executor
- `PipelineConversionRule` for section -> new Process
- `TemplateDiscovery` for fuzzy section matching
- `PipelineConfig` and `AutomationConfig` dataclasses
- Field seeding (cascade, carry-through, computed)
- SaveSession post-commit hook integration
- Process creation from template
- Dual placement (subtask + project membership)
- Unit tests for all components

### Explicitly Out of Scope

- External queue integration (Redis, Celery, SQS)
- Complex orchestration (multi-step pipelines in single commit)
- Webhook-triggered automation (automation is commit-triggered only)
- State machine enforcement (allowed transitions - consumers validate)
- UI/dashboard for automation monitoring
- Automation history/audit log persistence
- Cross-workspace automation
- Rule condition DSL (keep simple predicate functions)
- Rollback on automation failure (log and continue)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Template section naming varies | Medium | Medium | Fuzzy match with configurable patterns |
| Field seeding complexity | Medium | High | Clear precedence rules in ADR |
| Post-commit hook adds latency | Low | Medium | Async execution, timeout limits |
| Automation failure handling unclear | Medium | High | Define error isolation in PRD |
| Template not found in some projects | Medium | Medium | Configurable fallback behavior |
| Breaking change to SaveSession API | Low | High | Opt-in config, existing behavior unchanged |

---

## Dependencies

### Prerequisites (Already Implemented)

| Dependency | Status | Notes |
|------------|--------|-------|
| ProcessType enum | Implemented | 6+ pipeline types defined |
| ProcessSection enum | Implemented | Standard pipeline states |
| SaveSession `move_to_section` | Implemented | Section changes tracked |
| SaveSession `add_to_project` | Implemented | Project membership operations |
| SectionsClient | Implemented | Section lookup and operations |
| Detection system | Implemented | Entity type detection for placement |

### Implementation Dependencies

| Dependency | Blocks | Notes |
|------------|--------|-------|
| AutomationConfig | Everything | Must be first; enables opt-in |
| AutomationRule protocol | Engine, rules | Define before implementing rules |
| AutomationEngine | Rule execution | Coordinator for all rules |
| TemplateDiscovery | PipelineConversionRule | Must find templates before creating |

---

## Test Resources (for Validation)

| Resource | GID | Purpose |
|----------|-----|---------|
| Business | `1201774764681405` | Root entity for hierarchy navigation |
| Unit | `1205571477139891` | Parent for ProcessHolder |
| Sales Process | `1209719836385072` | Source process for conversion test |

---

## Your First Task

Confirm understanding by:

1. Summarizing the Automation Layer initiative goal in 2-3 sentences
2. Listing the 7 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step before requirements
4. Confirming which files/systems must be analyzed before PRD-AUTOMATION-LAYER
5. Listing which open questions you need answered before Session 2
6. Noting the key distinction: automation is **platform infrastructure** (like Django signals), not consumer business logic

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

# Session Trigger Prompts

## Session 1: Discovery

```markdown
Begin Session 1: Automation Layer Discovery

Work with the @requirements-analyst agent to analyze SaveSession extension points and audit template patterns.

**Goals:**
1. Map SaveSession commit phases and identify post-commit hook insertion point
2. Audit SaveResult structure for automation result reporting
3. Document template section naming patterns across pipeline projects
4. Inventory fields for cascade, carry-through, and computed seeding
5. Understand Process creation patterns from TasksClient
6. Document AsanaClient configuration patterns for AutomationConfig
7. Identify error handling patterns in existing persistence layer

**Files to Analyze:**
- `src/autom8_asana/persistence/session.py` - SaveSession, commit phases
- `src/autom8_asana/persistence/pipeline.py` - SavePipeline orchestration
- `src/autom8_asana/persistence/models.py` - SaveResult, PlannedOperation
- `src/autom8_asana/client.py` - AsanaClient initialization
- `src/autom8_asana/models/business/process.py` - Process fields
- `src/autom8_asana/clients/sections.py` - Section operations

**Template/Project Audit:**
- Template section naming variations
- Template task structure and pre-populated fields
- Pipeline project section consistency
- Field availability across pipeline stages

**Deliverable:**
A discovery document with:
- SaveSession extension point analysis
- Template pattern documentation
- Field seeding inventory (cascade/carry-through/computed)
- Configuration pattern recommendation
- Open questions resolved or escalated
- Risk register for edge cases

Create the analysis plan first. I'll review before you execute.
```

## Session 2: Requirements

```markdown
Begin Session 2: Automation Layer Requirements Definition

Work with the @requirements-analyst agent to create PRD-AUTOMATION-LAYER.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Define AutomationConfig requirements
2. Define AutomationRule protocol requirements
3. Define AutomationEngine requirements
4. Define PipelineConversionRule requirements
5. Define TemplateDiscovery requirements
6. Define field seeding requirements (cascade, carry-through, computed)
7. Define SaveSession integration requirements
8. Define acceptance criteria for each component

**Key Questions to Address:**
- What triggers PipelineConversionRule?
- How does TemplateDiscovery find the right template?
- What's the field seeding precedence?
- How does automation report results?

**PRD Organization:**
- FR-CFG-*: Configuration requirements (AutomationConfig, PipelineConfig)
- FR-RULE-*: Rule protocol requirements
- FR-ENGINE-*: Engine requirements (execution, hooks)
- FR-PIPELINE-*: Pipeline conversion rule requirements
- FR-TEMPLATE-*: Template discovery requirements
- FR-SEED-*: Field seeding requirements
- FR-PLACE-*: Process placement requirements
- FR-COMPAT-*: Backward compatibility requirements
- NFR-*: Performance, reliability requirements

Create the plan first. I'll review before you execute.
```

## Session 3: Architecture

```markdown
Begin Session 3: Automation Layer Architecture Design

Work with the @architect agent to create TDD-AUTOMATION-LAYER and foundational ADRs.

**Prerequisites:**
- PRD-AUTOMATION-LAYER approved

**Goals:**
1. Design `automation/` package structure
2. Design AutomationRule protocol
3. Design AutomationEngine with rule registry
4. Design post-commit hook integration with SaveSession
5. Design PipelineConversionRule implementation
6. Design TemplateDiscovery with fuzzy matching
7. Design field seeding composition

**Required ADRs:**
- ADR-0102: Automation Rule Protocol Design
- ADR-0103: Post-Commit Hook Integration Pattern
- ADR-0104: Pipeline Configuration Strategy
- ADR-0105: Template Discovery Algorithm
- ADR-0106: Field Seeding Precedence Rules

**Module Structure to Consider:**

```
src/autom8_asana/
+-- automation/           # NEW PACKAGE
|   +-- __init__.py
|   +-- base.py           # AutomationRule protocol, AutomationEngine
|   +-- pipeline.py       # PipelineConversionRule
|   +-- templates.py      # TemplateDiscovery
|   +-- config.py         # AutomationConfig, PipelineConfig
|   +-- seeding.py        # FieldSeeder (cascade, carry-through, computed)
+-- persistence/
|   +-- session.py        # Extended with post-commit hooks
+-- client.py             # AutomationConfig parameter added
```

Create the plan first. I'll review before you execute.
```

## Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - Core Automation Infrastructure

Work with the @principal-engineer agent to implement foundational automation components.

**Prerequisites:**
- PRD-AUTOMATION-LAYER approved
- TDD-AUTOMATION-LAYER approved
- ADRs documented

**Phase 1 Scope:**
1. Create `automation/` package structure
2. Implement `AutomationRule` protocol (trigger, execute, config)
3. Implement `AutomationEngine` rule executor
4. Implement `AutomationConfig` and `PipelineConfig` dataclasses
5. Add `automation` parameter to AsanaClient
6. Write unit tests for protocol and engine

**Hard Constraints:**
- Automation disabled by default (opt-in)
- Engine executes rules synchronously
- Config must be serializable (for logging/debugging)
- No side effects during rule matching phase

**Explicitly OUT of Phase 1:**
- PipelineConversionRule (Phase 2)
- TemplateDiscovery (Phase 2)
- Field seeding (Phase 3)
- SaveSession integration (Phase 3)

Create the plan first. I'll review before you execute.
```

## Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - Pipeline Conversion Rule

Work with the @principal-engineer agent to implement pipeline-specific automation.

**Prerequisites:**
- Phase 1 complete and tested

**Phase 2 Scope:**
1. Implement `PipelineConversionRule` with trigger matching
2. Implement `TemplateDiscovery` with fuzzy section matching
3. Add template task fetching via SectionsClient
4. Implement template-to-Process conversion
5. Add rule registration to AutomationEngine
6. Write integration tests for rule execution

**Integration Points:**
- AutomationEngine for rule registration
- SectionsClient for template section lookup
- TasksClient for template task fetching
- PipelineConfig for project mapping

Create the plan first. I'll review before you execute.
```

## Session 6: Implementation Phase 3

```markdown
Begin Session 6: Implementation Phase 3 - Seeding and Integration

Work with the @principal-engineer agent to implement field seeding and SaveSession integration.

**Prerequisites:**
- Phase 2 complete and tested

**Phase 3 Scope:**
1. Implement `FieldSeeder` for cascade/carry-through/computed
2. Add Process creation with seeded fields
3. Implement dual placement (subtask + project membership)
4. Integrate AutomationEngine with SaveSession post-commit
5. Add automation results to SaveResult
6. Add comprehensive logging for automation execution
7. Write E2E integration tests

**Field Seeding Precedence:**

```python
# 1. Computed (highest priority)
due_date = datetime.now() + timedelta(days=1)

# 2. Carry-through from source Process
rep = source_process.rep
priority = source_process.priority

# 3. Cascade from Business/Unit
company_id = business.company_id
vertical = unit.vertical
office_phone = business.office_phone
```

Create the plan first. I'll review before you execute.
```

## Session 7: Validation

```markdown
Begin Session 7: Automation Layer Validation

Work with the @qa-adversary agent to validate the implementation.

**Prerequisites:**
- All implementation phases complete
- Automation layer integrated with SaveSession

**Goals:**

**Part 1: Functional Validation**
- AutomationConfig accepted by AsanaClient
- PipelineConfig maps projects correctly
- Post-commit hook fires on section change to CONVERTED
- Template found in destination project
- New Process created with correct structure

**Part 2: Field Seeding Validation**
- Cascade fields populated from Business/Unit
- Carry-through fields copied from source Process
- Computed fields calculated correctly
- Precedence rules respected

**Part 3: Placement Validation**
- Process created as subtask of correct ProcessHolder
- Process added to destination project
- Process in correct section (OPPORTUNITY)

**Part 4: Edge Case Testing**
- Template section not found -> graceful handling
- Multiple templates -> selection logic
- Automation disabled -> no hooks fire
- Empty PipelineConfig -> no conversions
- Failed automation -> original commit succeeds

**Part 5: Performance Validation**
- Post-commit hook latency <10ms
- Full pipeline conversion <1s
- No regression in existing SaveSession tests

**Part 6: Backward Compatibility**
- All existing tests pass
- SaveSession works identically when automation=None

Create the plan first. I'll review before you execute.
```

---

# Context Gathering Checklist

Before starting, gather:

**Codebase Context:**

- [ ] `src/autom8_asana/persistence/session.py` - SaveSession structure
- [ ] `src/autom8_asana/persistence/pipeline.py` - Commit phases
- [ ] `src/autom8_asana/persistence/models.py` - SaveResult
- [ ] `src/autom8_asana/client.py` - AsanaClient initialization
- [ ] `src/autom8_asana/models/business/process.py` - Process fields
- [ ] `src/autom8_asana/clients/sections.py` - Section operations

**Template Patterns:**

- [ ] Template section naming variations
- [ ] Template task structure
- [ ] Pipeline project section naming
- [ ] Field availability per pipeline stage

**Field Seeding:**

- [ ] Cascade fields from Business
- [ ] Cascade fields from Unit
- [ ] Carry-through fields from Process
- [ ] Computed fields (due_date, etc.)

**Integration Patterns:**

- [ ] Post-commit hook timing
- [ ] Error handling strategy
- [ ] Result reporting structure
- [ ] Configuration override patterns
