# Orchestrator Initialization: Pipeline Automation Enhancement - From Exists to Expert

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`autom8-asana`** - SDK patterns, SaveSession, Business entities, detection, batch operations
  - Activates when: Working with automation rules, SaveSession hooks, entity operations, Process/ProcessHolder hierarchy

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

## The Mission: Evolve Pipeline Automation from "Basic Trigger" to "Production-Ready with Full Legacy Feature Parity"

The Automation Layer (PROMPT-0-AUTOMATION-LAYER) successfully established the foundation: `PipelineConversionRule` triggers on section change to CONVERTED, `TemplateDiscovery` finds templates, and basic task creation works. We are at approximately **1/10 feature completeness**. This initiative delivers the remaining 9/10: subtask duplication with race condition handling, Process hierarchy integration (ProcessHolder placement), custom field seeding that actually writes to API, assignee assignment based on rep fields, and onboarding comments that explain context.

### Why This Initiative?

- **Legacy Feature Parity**: Match all automation behaviors from the legacy system
- **Production Readiness**: Handle race conditions, edge cases, and error scenarios
- **Complete Data Flow**: Fields actually propagate to new Processes (not just computed)
- **Hierarchy Integrity**: New Processes placed correctly in Business > Unit > ProcessHolder chain
- **Human Context**: Onboarding comments explain why a task exists

### Current State

**Automation Layer (Implemented - Phase 1)**:
- `PipelineConversionRule` triggers on `section_changed` to CONVERTED
- `TemplateDiscovery` finds template task via fuzzy section name matching
- `tasks.create_async()` creates new task with name and notes
- `FieldSeeder` computes cascade/carry-through/computed field values
- `AutomationEngine` executes rules post-commit with loop prevention

**What's Working**:
```python
# This triggers successfully:
process.move_to_section(converted_section)
await session.commit()
# Result: New task created in target project with name from source process

# FieldSeeder computes these values (but doesn't write them):
fields = await seeder.seed_fields_async(business, unit, source_process)
# fields = {"Office Phone": "555-1234", "Vertical": "Dental", "Started At": "2024-01-15"}
```

**What's Missing**:

```
Current:                              Needed:
[X] Trigger on CONVERTED             [ ] Subtask duplication from template
[X] Find template task               [ ] Wait for subtasks before API calls
[X] Create task with name            [ ] Hierarchy insertion (ProcessHolder)
[X] Compute field values             [ ] Actually WRITE fields to API
                                     [ ] Assignee assignment from rep field
                                     [ ] Onboarding comment on new Process
```

### Current vs. Target State

| Feature | Current | Target |
|---------|---------|--------|
| Trigger detection | Works | Works |
| Template discovery | Works | Works |
| Task creation | `create_async()` - no subtasks | `duplicate_async()` - with subtasks |
| Subtask handling | None | Full duplication, race condition aware |
| Field seeding | Computed, not applied | Computed AND written to API |
| Hierarchy placement | None | Subtask of ProcessHolder, after preceding Process |
| Assignee | Not set | Rep-based assignment (sales rep vs implementation rep) |
| Comments | None | Onboarding comment with context |

### Automation Enhancement Profile

| Attribute | Value |
|-----------|-------|
| Primary Language | Python 3.10+ |
| Framework | Pydantic v2, async-first |
| Location | `src/autom8_asana/automation/` |
| Current Completeness | ~10% |
| Target Completeness | 100% (legacy parity) |
| Key Integration Points | TasksClient, SaveSession, StoriesClient, ProcessHolder |

### Target Architecture Enhancement

```
PipelineConversionRule.execute_async()
         |
         v
+------------------------+
| 1. Template Discovery  |  (EXISTING - works)
|    find_template_task  |
+------------------------+
         |
         v
+------------------------+
| 2. Task Duplication    |  <-- NEW: Use duplicate_async()
|    with subtasks       |      instead of create_async()
+------------------------+
         |
         v
+------------------------+
| 3. Wait for Subtasks   |  <-- NEW: Race condition handling
|    (polling/delay)     |      Subtasks must exist before
+------------------------+      further API operations
         |
         v
+------------------------+
| 4. Field Seeding       |  (EXISTING - compute)
|    cascade + carry +   |  <-- NEW: Actually WRITE to API
|    computed            |      via update_async()
+------------------------+
         |
         v
+------------------------+
| 5. Hierarchy Placement |  <-- NEW: set_parent() to ProcessHolder
|    ProcessHolder       |      insert_after preceding Process
|    subtask ordering    |
+------------------------+
         |
         v
+------------------------+
| 6. Assignee Assignment |  <-- NEW: Rep field resolution
|    rep-based logic     |      sales rep vs impl rep
+------------------------+
         |
         v
+------------------------+
| 7. Onboarding Comment  |  <-- NEW: stories.create_comment_async()
|    context explanation |      "Created from [source] conversion"
+------------------------+
```

### Key Constraints

- **Race Condition Awareness**: Asana's `duplicate_async()` may return before subtasks are fully created; subsequent API calls can interrupt subtask creation
- **Hierarchy Integrity**: New Process MUST be subtask of ProcessHolder, not floating
- **Ordering Preservation**: Insert AFTER preceding Process (maintain chronological order)
- **Field Seeding Precedence**: Computed > Carry-through > Cascade (existing logic is correct)
- **Async-First**: All operations remain async; no blocking waits
- **Backward Compatibility**: Existing automation behavior unchanged for current consumers
- **Graceful Degradation**: If any enhancement step fails, log and continue (don't break conversion)

### Requirements Summary

| Requirement | Priority | Status |
|-------------|----------|--------|
| Use `duplicate_async()` for task creation with subtasks | Must | Gap |
| Wait for subtasks before further API operations | Must | Gap |
| Set ProcessHolder as parent via `set_parent()` | Must | Gap |
| Insert after preceding Process (ordering) | Must | Gap |
| Write seeded fields to API via `update_async()` | Must | Gap |
| Resolve assignee from rep field | Must | Gap |
| Add onboarding comment via `create_comment_async()` | Must | Gap |
| Determine rep field based on ProcessType | Must | Gap |
| Support configurable wait strategy for subtasks | Should | Gap |
| Log each enhancement step for debugging | Should | Gap |
| Handle missing ProcessHolder gracefully | Should | Gap |
| Support dry-run mode for conversion preview | Could | Future |

### Success Criteria

1. Template subtasks duplicated to new Process (checklist items preserved)
2. No API calls made until all subtasks exist on new Process
3. New Process is subtask of correct ProcessHolder in Unit
4. New Process ordered after preceding Process (not first/last)
5. All seeded field values written to new Process custom fields
6. Assignee set based on appropriate rep field for ProcessType
7. Onboarding comment added explaining conversion context
8. Existing automation tests still pass
9. Full pipeline conversion completes successfully end-to-end
10. Graceful handling when ProcessHolder not found

### Performance Targets

| Metric | Current | Target | Notes |
|--------|---------|--------|-------|
| Task creation | <200ms | <500ms | duplicate_async() is slower |
| Subtask wait | N/A | <2s | Configurable timeout |
| Field seeding write | N/A | <300ms | Single update_async() call |
| Hierarchy placement | N/A | <200ms | set_parent() operation |
| Comment creation | N/A | <100ms | Single API call |
| **Full conversion** | <500ms | <3s | All steps complete |

---

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | Gap analysis, Asana API research for duplicate, rep field mapping |
| **2: Requirements** | Requirements Analyst | PRD-PIPELINE-AUTOMATION-ENHANCEMENT with acceptance criteria |
| **3: Architecture** | Architect | TDD-PIPELINE-AUTOMATION-ENHANCEMENT + ADRs for key decisions |
| **4: Implementation P1** | Principal Engineer | Task duplication, subtask wait strategy |
| **5: Implementation P2** | Principal Engineer | Field seeding write, hierarchy placement |
| **6: Implementation P3** | Principal Engineer | Assignee assignment, onboarding comments |
| **7: Validation** | QA/Adversary | Full pipeline E2E, edge cases, performance |

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
| `src/autom8_asana/automation/pipeline.py` | Current `execute_async()` implementation - what's the insertion point for enhancements? |
| `src/autom8_asana/automation/seeding.py` | `FieldSeeder` design - how to extend to write fields? |
| `src/autom8_asana/clients/tasks.py` | Does `duplicate_async()` exist? What parameters? |
| `src/autom8_asana/persistence/session.py` | `set_parent()` implementation - supports `insert_after`? |
| `src/autom8_asana/clients/stories.py` | `create_comment_async()` signature and usage |
| `src/autom8_asana/models/business/process.py` | `ProcessHolder` structure, how to find it for a Unit |
| `src/autom8_asana/models/business/unit.py` | How does Unit relate to ProcessHolder? |

### Asana API Research

| API Endpoint | Questions to Answer |
|--------------|---------------------|
| `POST /tasks/{task_gid}/duplicate` | Does SDK support this? What options available? |
| Task duplication behavior | Are subtasks duplicated synchronously or async? |
| Subtask creation timing | How to detect when all subtasks exist? |
| `POST /tasks/{task_gid}/setParent` | Already wrapped in `set_parent()`? |
| `POST /tasks/{task_gid}/stories` | Comment creation - `create_comment_async()` exists? |

### Rep Field Mapping

| Field | Questions |
|-------|-----------|
| `Business.rep` | PeopleField - what format? GID? User object? |
| `Unit.rep` | Same pattern as Business.rep? |
| `Offer.rep` | Is this used for any pipeline type? |
| Rep selection logic | Sales Process -> sales rep; Implementation -> impl rep? |
| Legacy behavior | What did the legacy system do for assignee? |

### ProcessHolder Integration

| Area | Questions |
|------|-----------|
| ProcessHolder discovery | Given a Unit, how to get its ProcessHolder? |
| Process ordering | How are Processes ordered within ProcessHolder? |
| Preceding Process | How to identify the Process to insert after? |
| Missing ProcessHolder | What if Unit has no ProcessHolder? Create one? |

---

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins, the following questions need answers:

### Task Duplication Questions

1. **duplicate_async() existence**: Does TasksClient have `duplicate_async()` or do we need to add it?
2. **Subtask duplication options**: Can we control what gets duplicated (subtasks, attachments, etc.)?
3. **Race condition timing**: How long should we wait for subtasks? Fixed delay vs. polling?
4. **Subtask count expectation**: Do we know expected subtask count from template, or poll until stable?

### Field Seeding Questions

5. **Custom field GID resolution**: How do we map field names to GIDs for update_async()?
6. **Batch vs. individual**: Single update_async() with all fields, or multiple calls?
7. **Field type handling**: Enum fields require GID, not value - how to resolve?
8. **Field existence**: What if target project doesn't have a field that source had?

### Hierarchy Questions

9. **ProcessHolder discovery**: `unit.process_holder` property exists? Or need to fetch?
10. **Preceding Process identification**: By created_at? By name pattern? By position?
11. **Insert after semantics**: Does `set_parent(insert_after=X)` put new task immediately after X?
12. **Missing ProcessHolder handling**: Create on-demand, or fail gracefully?

### Assignee Questions

13. **Rep field resolution**: `business.rep` returns what? List of dicts? Single GID?
14. **Pipeline-specific rep**: Different rep for Sales vs Implementation vs Retention?
15. **Rep field location**: Always on Unit? Or varies by ProcessType?
16. **Fallback assignee**: What if rep field is empty?

### Comment Questions

17. **Comment content template**: What should the onboarding comment say?
18. **Source Process reference**: Include link to source Process in comment?
19. **Comment timing**: Before or after field seeding?
20. **Error handling**: If comment fails, continue or fail conversion?

---

## Feature Gap Analysis

### Gap 1: Subtask Duplication from Template

**Current State**: `tasks.create_async()` creates empty task, no subtasks

**Target State**: Template subtasks (checklists, action items) duplicated to new Process

**Technical Approach**:
- Use Asana's `POST /tasks/{task_gid}/duplicate` API
- Options: `include: ["subtasks"]` to duplicate subtask hierarchy
- May need to add `duplicate_async()` to TasksClient

**Risk**: Race condition - Asana may return from duplicate before subtasks fully created

### Gap 2: Subtask Race Condition Handling

**Current State**: No subtask handling

**Target State**: Wait for all subtasks to exist before further API calls

**Technical Approach Options**:
1. **Fixed delay**: Wait 1-2 seconds after duplicate (simple, wasteful)
2. **Polling**: Check `subtasks_async()` until count matches template
3. **Webhook-based**: Wait for subtask creation events (complex, overkill)

**Recommendation**: Polling with timeout (most reliable)

### Gap 3: ProcessHolder Hierarchy Integration

**Current State**: New Process is top-level task in project (no parent)

**Target State**: New Process is subtask of ProcessHolder, ordered correctly

**Technical Approach**:
- Discover ProcessHolder via Unit: `unit.process_holder` or `unit._process_holder`
- Use `session.set_parent(new_process, process_holder, insert_after=preceding_process)`
- Identify preceding process by position/created_at in ProcessHolder.processes

**Risk**: ProcessHolder may not be hydrated - need to fetch

### Gap 4: Custom Field Seeding to API

**Current State**: `FieldSeeder.seed_fields_async()` returns dict of values, not written

**Target State**: Seeded values written to new Process via API

**Technical Approach**:
- Extend `FieldSeeder` with `write_fields_async()` method
- Use `tasks.update_async()` with `custom_fields` parameter
- Resolve field names to GIDs using custom field definitions on project

**Challenge**: Enum fields require option GID, not display value

### Gap 5: Assignee Assignment from Rep Field

**Current State**: Assignee not set on new Process

**Target State**: Assignee set based on appropriate rep for ProcessType

**Technical Approach**:
- Determine rep source based on target ProcessType:
  - Sales/Outreach -> Business.rep or Unit.rep (sales rep)
  - Implementation/Onboarding -> Different rep field or same?
- Rep field is PeopleField - returns list of user dicts with `gid`
- Use `tasks.update_async()` with `assignee` parameter

**Open Question**: What's the rep field mapping per ProcessType?

### Gap 6: Onboarding Comment

**Current State**: No comment on new Process

**Target State**: Comment explaining conversion context

**Technical Approach**:
- Use `stories.create_comment_async(task=new_process_gid, text=comment)`
- Comment template: "Created from [Source Process Name] conversion on [Date]. Original process converted in [Source Project Name]."

**Example**:
```
This Onboarding process was automatically created when "Acme Corp - Sales"
was converted on 2024-01-15.

Source: Sales Pipeline > Converted
Contact: John Smith (555-1234)
```

---

## Implementation Order (Dependency-Based)

```
Session 4: Task Duplication + Subtask Wait
    |
    +-- Add duplicate_async() to TasksClient (if missing)
    +-- Implement SubtaskWaiter utility
    +-- Update PipelineConversionRule to use duplication
    |
    v
Session 5: Field Seeding Write + Hierarchy
    |
    +-- Add write_fields_async() to FieldSeeder
    +-- Implement ProcessHolder discovery
    +-- Add hierarchy placement logic
    |
    v
Session 6: Assignee + Comments
    |
    +-- Implement rep field resolution
    +-- Add assignee setting
    +-- Add onboarding comment creation
```

---

## Scope Boundaries

### Explicitly In Scope

- Task duplication with subtasks via Asana API
- Subtask wait strategy (polling with timeout)
- ProcessHolder parent relationship
- Process ordering within ProcessHolder
- Custom field value writing to API
- Assignee assignment from rep field
- Onboarding comment creation
- Unit tests for all new functionality
- Integration tests for full pipeline

### Explicitly Out of Scope

- ProcessHolder auto-creation (if missing, log warning)
- Custom field creation (fields must exist on project)
- Multi-hop pipeline (Sales -> Onboarding -> Implementation in one commit)
- Rollback on partial failure (log and continue)
- Webhook-based subtask detection
- Template subtask modification
- Attachment duplication

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `duplicate_async()` not in SDK | High | Medium | Add wrapper for Asana duplicate API |
| Subtask race condition | High | High | Polling with configurable timeout |
| ProcessHolder not hydrated | Medium | Medium | Fetch on-demand if not present |
| Field GID resolution complexity | Medium | High | Use project custom field definitions |
| Rep field varies by org | Medium | Medium | Configurable rep field mapping |
| Performance degradation | Medium | Medium | Parallelize where possible |

---

## Dependencies

### Prerequisites (Already Implemented)

| Dependency | Status | Notes |
|------------|--------|-------|
| `PipelineConversionRule` | Implemented | Trigger and basic flow |
| `TemplateDiscovery` | Implemented | Finds template task |
| `FieldSeeder` | Implemented | Computes field values |
| `AutomationEngine` | Implemented | Rule execution |
| `StoriesClient` | Implemented | `create_comment_async()` exists |
| `set_parent()` | Implemented | Supports `insert_after` |

### Implementation Dependencies

| Dependency | Blocks | Notes |
|------------|--------|-------|
| `duplicate_async()` | Subtask duplication | May need to add to TasksClient |
| SubtaskWaiter | Field seeding | Must wait for subtasks |
| ProcessHolder discovery | Hierarchy placement | Unit -> ProcessHolder resolution |
| Custom field GID resolution | Field writing | Name -> GID mapping |

---

## Test Resources (for Validation)

| Resource | GID | Purpose |
|----------|-----|---------|
| Test Business | `1201774764681405` | Root entity for hierarchy |
| Test Unit | `1205571477139891` | Parent for ProcessHolder |
| Sales Process (template) | TBD | Template with subtasks |
| Sales Process (source) | `1209719836385072` | Source for conversion test |
| Onboarding Project | TBD | Target project for conversion |

---

## Your First Task

Confirm understanding by:

1. Summarizing the Pipeline Automation Enhancement initiative goal in 2-3 sentences
2. Listing the 7 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step
4. Confirming which files/APIs must be analyzed before PRD
5. Listing which open questions you need answered before Session 2
6. Noting the key technical risks: subtask race conditions and field GID resolution

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

# Session Trigger Prompts

## Session 1: Discovery

```markdown
Begin Session 1: Pipeline Automation Enhancement Discovery

Work with the @requirements-analyst agent to analyze current implementation gaps and research Asana API capabilities.

**Goals:**
1. Verify whether `duplicate_async()` exists in TasksClient or needs implementation
2. Research Asana duplicate API behavior for subtask timing
3. Map ProcessHolder discovery pattern from Unit
4. Document rep field structure and pipeline-specific assignment logic
5. Analyze custom field GID resolution approach
6. Identify existing `set_parent()` capabilities for ordering
7. Review `create_comment_async()` for onboarding comments

**Files to Analyze:**
- `src/autom8_asana/automation/pipeline.py` - Current execution flow
- `src/autom8_asana/automation/seeding.py` - FieldSeeder extension point
- `src/autom8_asana/clients/tasks.py` - duplicate_async() presence
- `src/autom8_asana/persistence/session.py` - set_parent() implementation
- `src/autom8_asana/clients/stories.py` - create_comment_async()
- `src/autom8_asana/models/business/unit.py` - ProcessHolder relationship
- `src/autom8_asana/models/business/process.py` - ProcessHolder structure

**API Research:**
- Asana POST /tasks/{task_gid}/duplicate - options and behavior
- Subtask duplication timing characteristics
- Custom field update payload format

**Deliverable:**
A discovery document with:
- Gap analysis with technical approach per gap
- API research findings
- ProcessHolder discovery pattern
- Rep field mapping per ProcessType
- Custom field resolution strategy
- Risk register with mitigations
- Recommended implementation order

Create the analysis plan first. I'll review before you execute.
```

## Session 2: Requirements

```markdown
Begin Session 2: Pipeline Automation Enhancement Requirements Definition

Work with the @requirements-analyst agent to create PRD-PIPELINE-AUTOMATION-ENHANCEMENT.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Define subtask duplication requirements
2. Define subtask wait strategy requirements
3. Define hierarchy placement requirements
4. Define field seeding write requirements
5. Define assignee assignment requirements
6. Define onboarding comment requirements
7. Define acceptance criteria for each feature

**Key Questions to Address:**
- What's the subtask wait timeout and strategy?
- What's the exact rep field mapping per ProcessType?
- What's the onboarding comment template?
- What's the fallback behavior for each failure mode?

**PRD Organization:**
- FR-DUP-*: Task duplication requirements
- FR-WAIT-*: Subtask wait strategy requirements
- FR-HIER-*: Hierarchy placement requirements
- FR-SEED-*: Field seeding write requirements
- FR-ASSIGN-*: Assignee assignment requirements
- FR-COMMENT-*: Onboarding comment requirements
- FR-ERR-*: Error handling requirements
- NFR-*: Performance, reliability requirements

Create the plan first. I'll review before you execute.
```

## Session 3: Architecture

```markdown
Begin Session 3: Pipeline Automation Enhancement Architecture Design

Work with the @architect agent to create TDD-PIPELINE-AUTOMATION-ENHANCEMENT and ADRs.

**Prerequisites:**
- PRD-PIPELINE-AUTOMATION-ENHANCEMENT approved

**Goals:**
1. Design `duplicate_async()` implementation (if needed)
2. Design SubtaskWaiter utility with polling strategy
3. Design FieldSeeder extension for write operations
4. Design ProcessHolder discovery pattern
5. Design rep field resolution strategy
6. Design onboarding comment generation

**Required ADRs:**
- ADR-0110: Task Duplication vs. Creation Strategy
- ADR-0111: Subtask Wait Strategy (Polling vs. Delay)
- ADR-0112: Custom Field GID Resolution Pattern
- ADR-0113: Rep Field Mapping per ProcessType

**Integration Points to Consider:**
- TasksClient extension for duplicate_async()
- FieldSeeder extension for write_fields_async()
- PipelineConversionRule execute_async() enhancements
- ProcessHolder discovery via Unit hydration

Create the plan first. I'll review before you execute.
```

## Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - Task Duplication and Subtask Wait

Work with the @principal-engineer agent to implement duplication infrastructure.

**Prerequisites:**
- PRD approved
- TDD approved
- ADRs documented

**Phase 1 Scope:**
1. Add `duplicate_async()` to TasksClient (if missing)
2. Implement SubtaskWaiter utility class
3. Update PipelineConversionRule to use duplicate_async()
4. Add configurable wait timeout to AutomationConfig
5. Write unit tests for duplication
6. Write integration test for subtask wait

**Hard Constraints:**
- Async-first (no blocking waits)
- Configurable timeout (default 2s)
- Graceful fallback if timeout exceeded
- Log subtask count for debugging

**Explicitly OUT of Phase 1:**
- Field seeding write (Phase 2)
- Hierarchy placement (Phase 2)
- Assignee assignment (Phase 3)
- Onboarding comments (Phase 3)

Create the plan first. I'll review before you execute.
```

## Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - Field Seeding Write and Hierarchy

Work with the @principal-engineer agent to implement field writing and placement.

**Prerequisites:**
- Phase 1 complete and tested

**Phase 2 Scope:**
1. Add `write_fields_async()` to FieldSeeder
2. Implement custom field GID resolution
3. Add ProcessHolder discovery to PipelineConversionRule
4. Implement `set_parent()` with `insert_after` for ordering
5. Handle missing ProcessHolder gracefully
6. Write unit tests for field writing
7. Write integration test for hierarchy placement

**Integration Points:**
- FieldSeeder computes values, then writes them
- ProcessHolder discovered from source Process's Unit
- New Process placed after source Process (or at end)

Create the plan first. I'll review before you execute.
```

## Session 6: Implementation Phase 3

```markdown
Begin Session 6: Implementation Phase 3 - Assignee and Comments

Work with the @principal-engineer agent to implement assignment and comments.

**Prerequisites:**
- Phase 2 complete and tested

**Phase 3 Scope:**
1. Implement rep field resolution per ProcessType
2. Add assignee setting to PipelineConversionRule
3. Add onboarding comment generation
4. Integrate comment creation via StoriesClient
5. Handle missing rep gracefully
6. Write unit tests for assignment logic
7. Write E2E integration test for full pipeline

**Comment Template:**
```
This {ProcessType} process was automatically created when "{Source Process Name}"
was converted on {Date}.

Source: {Source Project Name} > Converted
```

Create the plan first. I'll review before you execute.
```

## Session 7: Validation

```markdown
Begin Session 7: Pipeline Automation Enhancement Validation

Work with the @qa-adversary agent to validate the implementation.

**Prerequisites:**
- All implementation phases complete

**Goals:**

**Part 1: Subtask Duplication Validation**
- Template subtasks duplicated correctly
- Subtask wait completes within timeout
- Fallback behavior on timeout works

**Part 2: Field Seeding Validation**
- All seeded fields written to API
- Enum fields resolved to correct GIDs
- Field precedence (computed > carry-through > cascade) respected

**Part 3: Hierarchy Validation**
- New Process is subtask of ProcessHolder
- Ordering correct (after preceding Process)
- Missing ProcessHolder handled gracefully

**Part 4: Assignment Validation**
- Assignee set from correct rep field
- ProcessType-specific rep selection works
- Missing rep handled gracefully

**Part 5: Comment Validation**
- Onboarding comment created
- Comment content accurate and helpful
- Comment failure doesn't break conversion

**Part 6: Performance Validation**
- Full conversion <3s
- No regression in existing tests

Create the plan first. I'll review before you execute.
```

---

# Context Gathering Checklist

Before starting, gather:

**Automation Layer:**

- [ ] `src/autom8_asana/automation/pipeline.py` - Current PipelineConversionRule
- [ ] `src/autom8_asana/automation/seeding.py` - FieldSeeder implementation
- [ ] `src/autom8_asana/automation/templates.py` - TemplateDiscovery
- [ ] `tests/unit/automation/test_pipeline.py` - Current test coverage

**Client Layer:**

- [ ] `src/autom8_asana/clients/tasks.py` - duplicate_async() presence
- [ ] `src/autom8_asana/clients/stories.py` - create_comment_async()
- [ ] `src/autom8_asana/persistence/session.py` - set_parent() with insert_after

**Business Entities:**

- [ ] `src/autom8_asana/models/business/unit.py` - ProcessHolder relationship
- [ ] `src/autom8_asana/models/business/process.py` - ProcessHolder structure
- [ ] `src/autom8_asana/models/business/business.py` - rep field definition

**Asana API:**

- [ ] Duplicate task endpoint behavior
- [ ] Subtask duplication timing
- [ ] Custom field update format
