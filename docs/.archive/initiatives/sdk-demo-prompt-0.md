# Orchestrator Initialization: SDK Demonstration Suite

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

**Domain-Specific Skills** (CRITICAL - use heavily):
- **`autom8-asana-domain`** - SDK patterns, SaveSession, Asana resources, async-first, batch operations
  - Activates when: Working with Task models, SaveSession, CustomFieldAccessor, client operations

- **`autom8-asana-business-schemas`** - Business, Contact, Unit, Location, Hours models; custom field definitions
  - Activates when: Understanding holder types, custom field names, test data relationships

- **`autom8-asana-business-relationships`** - Holder pattern, bidirectional navigation, lazy loading
  - Activates when: Implementing holder traversal, parent/child navigation

- **`autom8-asana-business-fields`** - Typed field accessors, cascading/inherited fields, field resolution
  - Activates when: Working with custom field types (enum, multi-enum, people, number, text)

- **`autom8-asana-business-workflows`** - SaveSession patterns, cascade operations, batch operations
  - Activates when: Implementing batch-friendly demo steps, cascade_field() demonstrations

**Workflow Skills**:
- **`documentation`** - PRD/TDD/ADR templates, artifact protocols
- **`10x-workflow`** - Agent coordination, session protocol, quality gates
- **`prompting`** - Agent invocation patterns

**How Skills Work**: Skills load automatically based on your current task. Invoke skills explicitly when you need deep reference (e.g., "Let me check the `autom8-asana-business-fields` skill for multi-enum patterns").

## Your Role: Orchestrator

You coordinate a 4-agent development workflow. You plan, delegate, coordinate, and verify - you do not implement directly.

## Your Specialist Agents

| Agent | Invocation | Responsibility |
|-------|------------|----------------|
| **Requirements Analyst** | `@requirements-analyst` | Requirements definition, acceptance criteria, scope boundaries |
| **Architect** | `@architect` | TDDs, ADRs, system design, trade-off analysis |
| **Principal Engineer** | `@principal-engineer` | Implementation, code quality, technical execution |
| **QA/Adversary** | `@qa-adversary` | Validation, failure mode testing, security/quality review |

## The Mission: Build Interactive SDK Demonstration Suite

Create a comprehensive, interactive demonstration script that validates all autom8_asana SDK functionality. The demo must be executable against real Asana data, confirm each operation with the user, and restore original state after completion.

### Why This Initiative?

- **SDK Validation**: Prove that all SDK operations work correctly against real Asana API
- **Developer Onboarding**: Provide executable examples of every SDK capability
- **Regression Testing**: Create a repeatable validation suite for future SDK changes
- **Documentation by Example**: Living code demonstrates usage patterns better than docs

### Current State

**SDK Foundation (Complete)**:
- SaveSession with Unit of Work pattern and change tracking
- Action operations: add_tag, remove_tag, add_dependency, remove_dependency, add_dependent, remove_dependent
- Membership operations: add_to_project, remove_from_project, move_to_section
- Subtask operations: set_parent, reorder_subtask
- CustomFieldAccessor with get/set/remove and name-to-GID resolution
- Batch API integration with 10-operation chunking
- Task model with Pydantic v2 and custom_fields support

**Business Model Layer (In Progress)**:
- 7 holder types defined (Contact, Unit, Location, DNA, Reconciliations, AssetEdit, Videography)
- 126 typed custom field accessors across Business (18), Contact (21), Unit (44)
- Bidirectional navigation patterns
- Cascading and inherited field infrastructure

**What's Missing**:

```python
# This is what we need to demonstrate:

# Demo 1: Tag operations
session.add_tag(business, "optimize")  # Confirm added
session.remove_tag(business, "optimize")  # Confirm removed

# Demo 2: Dependency operations
session.add_dependent(business, dependency_task)  # Confirm dependent
session.remove_dependent(business, dependency_task)  # Confirm removed
session.add_dependency(business, dependency_task)  # Confirm dependency
session.remove_dependency(business, dependency_task)  # Confirm removed

# Demo 3: Description updates (via Task.notes)
business.notes = "Test 1"  # Confirm set
business.notes = "Test 2"  # Confirm updated
business.notes = None  # Confirm cleared

# Demo 4-8: Custom field operations by type
# String, People, Enum, Number, Multi-Enum

# Demo 9: Subtask operations
session.set_parent(subtask, None)  # Remove subtask
session.set_parent(subtask, holder)  # Add back
session.reorder_subtask(subtask, insert_after=last)  # Move to bottom
session.reorder_subtask(subtask, insert_before=first)  # Move to top

# Demo 10: Membership operations
session.move_to_section(business, other_section)  # Change section
session.remove_from_project(business, project)  # Remove
session.add_to_project(business, project, section=target)  # Add back

# Result: Complete validation of:
# - All 10 operation categories
# - Each operation interactive (user confirms)
# - Original state restored after demo
# - Name->GID resolution for tags, users, enums
# - Works with real Asana data
```

### Test Data Profile

| Entity | GID | Notes |
|--------|-----|-------|
| **Business** | `1203504488813198` | Primary test entity - all field demos |
| **Unit** | `1203504489143268` | Multi-enum field demo (Disabled Questions) |
| **Dependency Task** | `1211596978294356` | For dependency/dependent demo |
| **Subtask** | `1203996810236966` | For subtask position demo |
| **Reconciliation Holder** | `1203504488912317` | Parent of subtask |

### Target Script Architecture

```
scripts/
    demo_sdk_operations.py    # Main interactive demo (10 categories)
    demo_business_model.py    # Business model traversal demo
    _demo_utils.py            # Shared utilities (confirm, restore, log)
```

### Key Constraints

- **Interactive mode required**: Every mutating operation requires user confirmation
- **Reversibility mandatory**: Script must restore original state at end
- **No hardcoded GIDs**: Resolve tags, users, enum options by name at runtime
- **Real API calls**: Uses actual Asana API, not mocks
- **Batch-friendly**: Use SaveSession batch operations where possible
- **Error recovery**: Graceful handling with rollback guidance on failure
- **Verbose logging**: Show exactly what is happening at each step

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Tag add/remove operations demonstrated | Must |
| Dependency add/remove operations demonstrated | Must |
| Dependent add/remove operations demonstrated | Must |
| Description set/update/clear demonstrated | Must |
| Custom field (string) set/update/clear demonstrated | Must |
| Custom field (people) change/clear/restore demonstrated | Must |
| Custom field (enum) change/clear/restore demonstrated | Must |
| Custom field (number) set/update/clear demonstrated | Must |
| Custom field (multi-enum) add/replace/remove demonstrated | Must |
| Subtask remove/add/reorder demonstrated | Must |
| Membership section change/remove/add demonstrated | Must |
| Name-to-GID resolution for tags, users, enums | Must |
| Interactive confirmation at each step | Must |
| State restoration after demo completion | Must |
| Verbose operation logging | Must |
| Error handling with rollback guidance | Should |
| Business model traversal demo script | Should |
| Documentation of any SDK gaps discovered | Should |

### Success Criteria

1. All 10 operation categories successfully demonstrated
2. Each mutating operation prompts user for confirmation before execution
3. Original entity state restored after demo completes
4. Tag names resolved to GIDs automatically (like "optimize" -> GID)
5. User names resolved to GIDs (like "Tom Tenuta" -> GID)
6. Enum option names resolved to GIDs (like "Tentative" -> GID)
7. Script works with real Asana data (not mocked)
8. Clear verbose output shows what is happening at each step
9. Script can be safely interrupted and re-run
10. All discovered SDK gaps documented

### Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Single operation latency | < 2s | Including confirmation prompt |
| Batch operation latency | < 5s per batch | 10 ops per batch |
| State restoration time | < 30s total | All demo entities restored |
| Memory usage | < 100MB | With all entities loaded |

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | SDK capability audit, test data verification |
| **2: Requirements** | Requirements Analyst | PRD-SDKDEMO with acceptance criteria |
| **3: Architecture** | Architect | TDD-SDKDEMO with script structure design |
| **4: Implementation P1** | Principal Engineer | Core demo utilities and Tag/Dependency demos |
| **5: Implementation P2** | Principal Engineer | Custom field demos (all 5 types) |
| **6: Implementation P3** | Principal Engineer | Subtask, Membership demos and Business model traversal |
| **7: Validation** | QA/Adversary | Execute full demo suite, verify restoration |

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rules**:
- Never execute without explicit confirmation
- **ALWAYS consult relevant skills** before implementing
- Use the architect agent for any script architecture questions
- Document any SDK gaps discovered during implementation

## Discovery Phase: What Must Be Explored

Before requirements can be finalized, the **Requirements Analyst** must explore:

### SDK Capability Analysis

| File/Area | Questions to Answer |
|-----------|---------------------|
| `src/autom8_asana/persistence/session.py` | Which action operations are fully implemented? |
| `src/autom8_asana/models/custom_field_accessor.py` | How does name->GID resolution work for custom fields? |
| `src/autom8_asana/models/task.py` | What fields support direct modification (notes, etc.)? |
| `src/autom8_asana/clients/tasks.py` | How to fetch task with custom fields populated? |
| `src/autom8_asana/clients/tags.py` | How to resolve tag name to GID? |
| `src/autom8_asana/clients/users.py` | How to resolve user name to GID? |

### Test Data Verification

| Entity | Questions to Answer |
|--------|---------------------|
| Business `1203504488813198` | Does it exist? Current custom field values? Current tags? |
| Unit `1203504489143268` | Does it have `Disabled Questions` field? Current value? |
| Dependency Task `1211596978294356` | Does it exist? Is it in same workspace? |
| Subtask `1203996810236966` | Does it exist? Current parent? Current position? |
| Reconciliation Holder `1203504488912317` | Does subtask belong to it? Other subtasks present? |

### Name Resolution Audit

| Resource Type | Questions |
|---------------|-----------|
| Tags | How to look up tag by name in workspace? Does "optimize" exist? |
| Users | How to look up user by name? GIDs for "Tom Tenuta", "Vince Marino"? |
| Enum Options | How are enum option names resolved? Already in CustomFieldAccessor? |
| Sections | How to resolve section name to GID? "BUSINESSES", "OTHER", "OPPORTUNITY"? |
| Projects | How to resolve project name to GID? "Businesses", "Issue Log"? |

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins, the following questions need answers:

### SDK Capability Questions

1. **Tag name resolution**: Does the SDK have a built-in way to resolve tag names to GIDs, or do we need to implement lookup?
2. **User name resolution**: How do we resolve user display names to GIDs for People-type custom fields?
3. **Enum option resolution**: Is enum option name->GID resolution built into CustomFieldAccessor, or only GID->GID?
4. **Multi-enum set semantics**: When setting multi-enum, does the SDK replace all values or merge?

### Test Data Questions

5. **Tag existence**: Does the tag "optimize" exist in the workspace? If not, should demo create it?
6. **Current field values**: What are the current values of all fields we plan to modify, for restoration?
7. **Subtask siblings**: Are there other subtasks under Reconciliation Holder for position testing?
8. **Section names**: What are the exact section names in the Businesses project?

### Script Design Questions

9. **Confirmation pattern**: `input("Press Enter to continue...")` or more sophisticated?
10. **State capture timing**: Capture original state at script start or per-operation?
11. **Partial failure handling**: If restoration fails, what should script do?

## Your First Task

Confirm understanding by:

1. Summarizing the SDK Demo Suite goal in 2-3 sentences
2. Listing the 7 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step before requirements
4. Confirming which SDK files must be analyzed before PRD-SDKDEMO
5. Listing which open questions you need answered before Session 2

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

# Session Trigger Prompts

## Session 1: Discovery

```markdown
Begin Session 1: SDK Capability & Test Data Discovery

Work with the @requirements-analyst agent to analyze the SDK and verify test data.

**Goals:**
1. Audit all SaveSession action operations (tag, dependency, dependent, parent, section)
2. Verify custom field accessor capabilities by type (string, number, enum, multi-enum, people)
3. Confirm name->GID resolution patterns (tags, users, enum options)
4. Verify all test data entities exist and capture current state
5. Document any capability gaps that may affect demo scope
6. Answer open questions from Prompt 0
7. Identify any additional test data needed

**SDK Files to Analyze:**
- `src/autom8_asana/persistence/session.py` - All action methods
- `src/autom8_asana/models/custom_field_accessor.py` - Resolution patterns
- `src/autom8_asana/clients/tasks.py` - Fetch patterns
- `src/autom8_asana/clients/tags.py` - Tag lookup
- `src/autom8_asana/clients/users.py` - User lookup

**Test Data to Verify:**
- Business `1203504488813198` - exists, custom field values, current tags
- Unit `1203504489143268` - exists, Disabled Questions field
- Dependency Task `1211596978294356` - exists, accessible
- Subtask `1203996810236966` - exists, parent, position
- Reconciliation Holder `1203504488912317` - subtask list

**Deliverable:**
A discovery document with:
- SDK capability matrix (operation -> implemented status)
- Test data verification results
- Name resolution strategy recommendation
- Gaps and risks identified
- Answers to open questions
- Recommended demo scope adjustments (if any)

Create the analysis plan first. I'll review before you execute.
```

## Session 2: Requirements

```markdown
Begin Session 2: SDK Demo Requirements Definition

Work with the @requirements-analyst agent to create PRD-SDKDEMO.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Define demo script requirements (10 operation categories)
2. Define interactive confirmation requirements
3. Define state restoration requirements
4. Define name resolution requirements
5. Define error handling requirements
6. Define logging/output requirements
7. Define acceptance criteria for each demo category

**Key Questions to Address:**
- Which operations should use SaveSession batch vs. immediate?
- What is the confirmation UX pattern?
- How is original state captured and restored?
- What happens if restoration fails?

**PRD Organization:**
- FR-TAG-*: Tag operation demo requirements
- FR-DEP-*: Dependency operation demo requirements
- FR-DESC-*: Description update demo requirements
- FR-CF-*: Custom field operation demo requirements (by type)
- FR-SUB-*: Subtask operation demo requirements
- FR-MEM-*: Membership operation demo requirements
- FR-INT-*: Interactivity requirements
- FR-REST-*: State restoration requirements
- NFR-*: Performance, reliability, usability requirements

Create the plan first. I'll review before you execute.
```

## Session 3: Architecture

```markdown
Begin Session 3: SDK Demo Script Architecture

Work with the @architect agent to create TDD-SDKDEMO with script structure design.

**Prerequisites:**
- PRD-SDKDEMO approved

**Goals:**
1. Design script module structure
2. Design demo utility library (_demo_utils.py)
3. Design state capture and restoration pattern
4. Design confirmation interaction pattern
5. Design operation result display format
6. Design error recovery pattern
7. Design business model traversal demo

**Key Design Decisions:**
- Single script vs. modular demos
- Class-based vs. function-based organization
- State storage format (dict, dataclass, JSON?)
- Logging library (structlog, logging, print?)

**Script Structure to Consider:**

```
scripts/
    demo_sdk_operations.py     # Main entry point
    demo_business_model.py     # Hierarchy traversal demo
    _demo_utils.py             # Shared utilities
        - confirm(message: str) -> bool
        - capture_state(entity) -> EntityState
        - restore_state(entity, state)
        - log_operation(op: str, entity: str, result: str)
        - format_custom_field(name: str, old: Any, new: Any)
```

**ADRs to Consider:**
- ADR-DEMO-001: State capture strategy (shallow vs. deep copy)
- ADR-DEMO-002: Name resolution approach (eager vs. lazy)
- ADR-DEMO-003: Error handling strategy (fail-fast vs. continue)

Create the plan first. I'll review before you execute.
```

## Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - Core Utilities and Tag/Dependency Demos

Work with the @principal-engineer agent to implement foundational components.

**Prerequisites:**
- PRD-SDKDEMO approved
- TDD-SDKDEMO approved

**Phase 1 Scope:**
1. Create scripts/_demo_utils.py with core utilities
2. Create scripts/demo_sdk_operations.py skeleton
3. Implement Demo 1: Tag operations (add/remove "optimize" on Business)
4. Implement Demo 2: Dependency operations (add/remove dependent task)
5. Implement state capture for tag and dependency state
6. Implement restoration for tag and dependency state

**CRITICAL: Consult Skills Before Implementing:**
- `autom8-asana-domain` for SaveSession action patterns
- `autom8-asana-business-schemas` for Business model context

**Hard Constraints:**
- Interactive confirmation before every mutating operation
- Verbose logging showing what is happening
- Name-to-GID resolution for tag "optimize"
- Original state captured before any modifications
- State restored at script end or on error

**Explicitly OUT of Phase 1:**
- Custom field demos (Phase 2)
- Subtask demos (Phase 3)
- Membership demos (Phase 3)
- Business model traversal (Phase 3)

Create the plan first. I'll review before you execute.
```

## Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - Custom Field Demos

Work with the @principal-engineer agent to implement custom field demonstrations.

**Prerequisites:**
- Phase 1 complete and tested

**Phase 2 Scope:**
1. Implement Demo 3: Description updates (notes field)
2. Implement Demo 4: String custom field (Fallback Page ID)
3. Implement Demo 5: People custom field (Rep)
4. Implement Demo 6: Enum custom field (Booking Type)
5. Implement Demo 7: Number custom field (Max Pipeline Stage)
6. Implement Demo 8: Multi-enum custom field (Disabled Questions on Unit)
7. Implement state capture/restore for all custom field types

**Consult Skills:**
- `autom8-asana-business-fields` for field type patterns
- `autom8-asana-business-schemas` for field definitions

**Key Implementation Details:**
- People field: Resolve "Tom Tenuta", "Vince Marino" names to GIDs
- Enum field: Resolve "Standard", "Tentative" option names to GIDs
- Multi-enum: Test set, add, remove semantics
- All fields: Demonstrate set -> update -> clear cycle

**Integration Points:**
- CustomFieldAccessor.set() for all field updates
- Name resolution via custom field metadata
- State restoration via captured original values

Create the plan first. I'll review before you execute.
```

## Session 6: Implementation Phase 3

```markdown
Begin Session 6: Implementation Phase 3 - Subtask, Membership, and Business Model

Work with the @principal-engineer agent to complete demo suite.

**Prerequisites:**
- Phase 2 complete and tested

**Phase 3 Scope:**
1. Implement Demo 9: Subtask operations
   - Remove subtask from holder (set_parent(None))
   - Add subtask back to holder (set_parent(holder))
   - Reorder to bottom (insert_after=last_sibling)
   - Reorder to top (insert_before=first_sibling)
2. Implement Demo 10: Membership operations
   - Change section (move_to_section to 'OTHER')
   - Remove from project (remove_from_project)
   - Add back to project in section 'OPPORTUNITY'
   - Move to original section 'BUSINESSES'
   - Add to 'Issue Log' project
   - Remove from 'Issue Log' project
3. Implement state capture/restore for subtask and membership
4. Create scripts/demo_business_model.py for hierarchy traversal
5. Implement final cleanup and state restoration orchestration
6. Document any SDK gaps discovered

**Consult Skills:**
- `autom8-asana-business-relationships` for holder patterns
- `autom8-asana-domain` for action operation patterns

**State Restoration Sequence:**
1. Restore memberships (section, project)
2. Restore subtask parent and position
3. Restore custom field values
4. Restore description
5. Restore tags
6. Restore dependencies

Create the plan first. I'll review before you execute.
```

## Session 7: Validation

```markdown
Begin Session 7: SDK Demo Suite Validation

Work with the @qa-adversary agent to validate the demo suite.

**Prerequisites:**
- All implementation phases complete

**Goals:**

**Part 1: Functional Validation**
- Execute full demo_sdk_operations.py end-to-end
- Verify all 10 operation categories work
- Verify confirmation prompts appear correctly
- Verify verbose logging is clear and accurate
- Verify state is captured before modifications

**Part 2: Restoration Validation**
- Verify all entities restored to original state
- Verify no orphaned tags or dependencies
- Verify custom fields back to original values
- Verify subtask position restored
- Verify membership restored to original project/section

**Part 3: Error Handling Validation**
- Test interruption mid-demo (Ctrl+C)
- Test network failure simulation (if possible)
- Test invalid GID handling
- Verify error messages are helpful

**Part 4: Business Model Demo Validation**
- Execute demo_business_model.py
- Verify hierarchy traversal works
- Verify bidirectional navigation displayed

**Part 5: Documentation Validation**
- Review script docstrings and comments
- Verify SDK gap documentation is complete
- Check that demo serves as usage example

Create the plan first. I'll review before you execute.
```

---

# Context Gathering Checklist

Before starting, gather:

**SDK Source Files:**

- [ ] `src/autom8_asana/persistence/session.py` - All action methods
- [ ] `src/autom8_asana/models/custom_field_accessor.py` - Field operations
- [ ] `src/autom8_asana/models/task.py` - Direct field updates
- [ ] `src/autom8_asana/clients/tasks.py` - Task fetch with opt_fields

**Test Data Verification:**

- [ ] Business GID `1203504488813198` existence and fields
- [ ] Unit GID `1203504489143268` existence and Disabled Questions field
- [ ] Dependency Task GID `1211596978294356` existence
- [ ] Subtask GID `1203996810236966` existence and parent
- [ ] Reconciliation Holder GID `1203504488912317` and subtask list

**Name Resolution Data:**

- [ ] Tag "optimize" GID (or creation strategy)
- [ ] User "Tom Tenuta" GID
- [ ] User "Vince Marino" GID
- [ ] Enum options for "Booking Type" field
- [ ] Multi-enum options for "Disabled Questions" field
- [ ] Section GIDs for "BUSINESSES", "OTHER", "OPPORTUNITY"
- [ ] Project GID for "Businesses"
- [ ] Project GID for "Issue Log"

**SDK Skills Reference:**

- [ ] `autom8-asana-domain` for SaveSession patterns
- [ ] `autom8-asana-business-schemas` for model definitions
- [ ] `autom8-asana-business-fields` for custom field types
- [ ] `autom8-asana-business-relationships` for holder navigation

---

# Demo Operation Reference

## Demo Categories with Expected Operations

### Demo 1: Tag Operations (on Business)

| Step | Operation | Expected Result |
|------|-----------|-----------------|
| 1a | `session.add_tag(business, "optimize")` | Tag appears on task |
| 1b | Confirm added | User verifies in Asana |
| 1c | `session.remove_tag(business, "optimize")` | Tag removed from task |
| 1d | Confirm removed | User verifies in Asana |

### Demo 2: Dependency Operations (on Business)

| Step | Operation | Expected Result |
|------|-----------|-----------------|
| 2a | `session.add_dependent(business, "1211596978294356")` | Dependent task linked |
| 2b | Confirm dependent added | User verifies |
| 2c | `session.remove_dependent(business, "1211596978294356")` | Dependent removed |
| 2d | Confirm dependent removed | User verifies |
| 2e | `session.add_dependency(business, "1211596978294356")` | Business depends on task |
| 2f | Confirm dependency added | User verifies |
| 2g | `session.remove_dependency(business, "1211596978294356")` | Dependency removed |
| 2h | Confirm dependency removed | User verifies |

### Demo 3: Description Updates (on Business)

| Step | Operation | Expected Result |
|------|-----------|-----------------|
| 3a | `business.notes = "Test 1"` + commit | Description set |
| 3b | Confirm set | User verifies |
| 3c | `business.notes = "Test 2"` + commit | Description updated |
| 3d | Confirm update | User verifies |
| 3e | `business.notes = None` + commit | Description cleared |
| 3f | Confirm cleared | User verifies |

### Demo 4: String Custom Field (Fallback Page ID)

| Step | Operation | Expected Result |
|------|-----------|-----------------|
| 4a | `cf.set("Fallback Page ID", "test-page-123")` | Value set |
| 4b | Confirm set | User verifies |
| 4c | `cf.set("Fallback Page ID", "test-page-456")` | Value updated |
| 4d | Confirm update | User verifies |
| 4e | `cf.set("Fallback Page ID", None)` | Value cleared |
| 4f | Confirm cleared | User verifies |

### Demo 5: People Custom Field (Rep)

| Step | Operation | Expected Result |
|------|-----------|-----------------|
| 5a | Capture current value (Vince Marino) | Store for restore |
| 5b | `cf.set("Rep", "Tom Tenuta")` | Rep changed |
| 5c | Confirm changed | User verifies |
| 5d | `cf.set("Rep", None)` | Rep cleared |
| 5e | Confirm cleared | User verifies |
| 5f | `cf.set("Rep", "Vince Marino")` | Rep restored |
| 5g | Confirm restored | User verifies |

### Demo 6: Enum Custom Field (Booking Type)

| Step | Operation | Expected Result |
|------|-----------|-----------------|
| 6a | Capture current value (Standard) | Store for restore |
| 6b | `cf.set("Booking Type", "Tentative")` | Changed to Tentative |
| 6c | Confirm changed | User verifies |
| 6d | `cf.set("Booking Type", None)` | Cleared |
| 6e | Confirm cleared | User verifies |
| 6f | `cf.set("Booking Type", "Standard")` | Restored |
| 6g | Confirm restored | User verifies |

### Demo 7: Number Custom Field (Max Pipeline Stage)

| Step | Operation | Expected Result |
|------|-----------|-----------------|
| 7a | `cf.set("Max Pipeline Stage", 1)` | Set to 1 |
| 7b | Confirm set | User verifies |
| 7c | `cf.set("Max Pipeline Stage", 2)` | Updated to 2 |
| 7d | Confirm update | User verifies |
| 7e | `cf.set("Max Pipeline Stage", None)` | Cleared |
| 7f | Confirm cleared | User verifies |

### Demo 8: Multi-Enum Custom Field (Disabled Questions on Unit)

| Step | Operation | Expected Result |
|------|-----------|-----------------|
| 8a | `cf.set("Disabled Questions", ["ability_to_pay"])` | Set single value |
| 8b | Confirm set | User verifies |
| 8c | `cf.set("Disabled Questions", ["ability_to_pay", "commute"])` | Set two values |
| 8d | Confirm both present | User verifies |
| 8e | `cf.set("Disabled Questions", ["commute"])` | Keep only commute |
| 8f | Confirm replacement | User verifies |
| 8g | `cf.set("Disabled Questions", None)` | Clear all |
| 8h | Confirm cleared | User verifies |

### Demo 9: Subtask Operations

| Step | Operation | Expected Result |
|------|-----------|-----------------|
| 9a | Capture current parent/position | Store for restore |
| 9b | `session.set_parent(subtask, None)` | Subtask removed |
| 9c | Confirm removed | User verifies |
| 9d | `session.set_parent(subtask, holder)` | Subtask added back |
| 9e | Confirm added | User verifies |
| 9f | `session.reorder_subtask(subtask, insert_after=last)` | Move to bottom |
| 9g | Confirm at bottom | User verifies |
| 9h | `session.reorder_subtask(subtask, insert_before=first)` | Move to top |
| 9i | Confirm at top | User verifies |

### Demo 10: Membership Operations

| Step | Operation | Expected Result |
|------|-----------|-----------------|
| 10a | Capture current project/section | Store for restore |
| 10b | `session.move_to_section(business, "OTHER")` | Section changed |
| 10c | Confirm section changed | User verifies |
| 10d | `session.remove_from_project(business, project)` | Removed |
| 10e | Confirm removed | User verifies |
| 10f | `session.add_to_project(business, project, section="OPPORTUNITY")` | Added in OPPORTUNITY |
| 10g | Confirm added in OPPORTUNITY | User verifies |
| 10h | `session.move_to_section(business, "BUSINESSES")` | Back to original |
| 10i | Confirm restored | User verifies |
| 10j | `session.add_to_project(business, "Issue Log")` | Added to Issue Log |
| 10k | Confirm in Issue Log | User verifies |
| 10l | `session.remove_from_project(business, "Issue Log")` | Removed from Issue Log |
| 10m | Confirm removed | User verifies |
