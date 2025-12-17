# Orchestrator Initialization: SDK Demo Bug Fix Sprint

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

**Domain-Specific Skills** (CRITICAL - use heavily):
- **`autom8-asana-domain`** - SDK patterns, SaveSession, Asana resources, async-first, batch operations
  - Activates when: Investigating SaveSession, action operations, batch client behavior

**Workflow Skills**:
- **`standards`** - Python/testing patterns, code conventions
- **`10x-workflow`** - Agent coordination, quality gates

**How Skills Work**: Skills load automatically based on your current task. Invoke skills explicitly when you need deep reference (e.g., "Let me check the `autom8-asana-domain` skill for SaveSession commit patterns").

## Your Role: Orchestrator

You coordinate a 4-agent development workflow. You plan, delegate, coordinate, and verify—you do not implement directly.

## Your Specialist Agents

| Agent | Invocation | Responsibility |
|-------|------------|----------------|
| **Requirements Analyst** | `@requirements-analyst` | Bug triage, root cause discovery, acceptance criteria |
| **Architect** | `@architect` | Fix design, impact analysis, API format research |
| **Principal Engineer** | `@principal-engineer` | Bug fixes, code implementation |
| **QA/Adversary** | `@qa-adversary` | Fix validation, regression testing |

## The Mission: Fix SDK Demo Suite Bugs

The SDK Demonstration Suite (`scripts/demo_sdk_operations.py`) was completed but live testing revealed **critical bugs** that prevent core functionality from working. All custom field CRUD operations fail, action operations appear to silently not execute, and missing client methods break subtask/project operations.

### Why This Initiative?

- **Demo Suite Non-Functional**: Core demo purpose (validating SDK operations) is defeated by these bugs
- **SDK Reliability**: Bugs reveal fundamental issues in SaveSession, CustomFieldAccessor, and client methods
- **Production Impact**: These same bugs would affect any production code using the SDK
- **Regression Risk**: Fixes must not break working functionality (tags, description, membership)

### Current State

**Working Operations** (from demo logs):
- Tag operations: `add_tag`, `remove_tag` - correctly queue and log
- Description operations: `task.notes` CRUD - works correctly (SaveResult shows succeeded=1)
- Membership operations: `move_to_section`, `add_to_project`, `remove_from_project` - work correctly

**Broken Operations** (from demo logs):

```python
# BUG 1: Action operations show succeeded=0, failed=0 (not executing)
session.add_dependency(task, dep_gid)   # SaveResult(succeeded=0, failed=0)
session.remove_dependency(task, dep_gid) # SaveResult(succeeded=0, failed=0)
session.add_dependent(task, dep_gid)     # SaveResult(succeeded=0, failed=0)
session.remove_dependent(task, dep_gid)  # SaveResult(succeeded=0, failed=0)

# BUG 2: All custom field writes fail (SaveResult shows failed=1)
cf.set("Company ID", "test")           # SaveResult(succeeded=0, failed=1)
cf.set("Rep", [user_gid])              # SaveResult(succeeded=0, failed=1)
cf.set("Aggression Level", option_gid) # SaveResult(succeeded=0, failed=1)
cf.set("Facebook Page ID", 12345.67)   # SaveResult(succeeded=0, failed=1)
cf.set("Products", [gid1, gid2])       # SaveResult(succeeded=0, failed=1)

# BUG 3: Missing async client methods
await client.tasks.subtasks_async(parent_gid)  # AttributeError: no attribute 'subtasks_async'
await client.projects.list_for_workspace_async(ws_gid)  # AttributeError: no attribute 'list_for_workspace_async'

# BUG 4: Display issues (minor)
people_field.value  # Shows ['1201051797275398'] instead of user names
multi_enum.value    # Shows 'Meta Marketing' (string) instead of ['Meta Marketing'] (list)
```

### Bug Evidence from Demo Logs

| Bug | Log Evidence | Impact |
|-----|--------------|--------|
| **BUG-1** | `[SUCCESS] Added dependency: SaveResult(succeeded=0, failed=0)` | Dependency/dependent ops silently fail |
| **BUG-2** | `BatchClient.execute: Batch complete: 0/1 succeeded` followed by `SaveResult(succeeded=0, failed=1)` | ALL custom field writes fail |
| **BUG-3** | `'TasksClient' object has no attribute 'subtasks_async'` | Subtask ordering broken |
| **BUG-3** | `'ProjectsClient' object has no attribute 'list_for_workspace_async'` | Multi-project demo broken |
| **BUG-4** | `Original value (user GIDs): ['1201051797275398']` | People field shows raw GIDs |
| **BUG-4** | `Display value: Meta Marketing` (not a list) | Multi-enum display is string |

### Key Constraints

- **No Breaking Changes**: Tags, description, membership operations work—don't regress them
- **Follow Asana API Spec**: Custom field updates require specific format per field type
- **Async-First**: All new client methods must be async
- **Test with Real API**: Fixes must be validated against live Asana workspace
- **Minimal Changes**: Fix root causes, don't over-engineer

### Requirements Summary

| Requirement | Priority | Bug |
|-------------|----------|-----|
| Fix dependency/dependent action operations to execute | Must | BUG-1 |
| Fix CustomFieldAccessor.set() for text fields | Must | BUG-2 |
| Fix CustomFieldAccessor.set() for people fields | Must | BUG-2 |
| Fix CustomFieldAccessor.set() for enum fields | Must | BUG-2 |
| Fix CustomFieldAccessor.set() for number fields | Must | BUG-2 |
| Fix CustomFieldAccessor.set() for multi-enum fields | Must | BUG-2 |
| Add `TasksClient.subtasks_async()` method | Must | BUG-3 |
| Add `ProjectsClient.list_for_workspace_async()` method | Must | BUG-3 |
| Improve people field display (show names) | Should | BUG-4 |
| Fix multi-enum display (show as list) | Should | BUG-4 |
| Verify tag operations still work after fixes | Must | Regression |
| Verify description operations still work | Must | Regression |
| Verify membership operations still work | Must | Regression |

### Success Criteria

1. `session.add_dependency()` and related ops execute and persist to Asana
2. `cf.set()` successfully updates all 5 custom field types
3. `TasksClient.subtasks_async()` returns subtask list
4. `ProjectsClient.list_for_workspace_async()` returns project list
5. Demo runs end-to-end with all 10 categories succeeding
6. No regressions in working operations

### Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Custom field write latency | < 2s | Single field update |
| Subtask list fetch | < 1s | Up to 50 subtasks |
| Project list fetch | < 2s | Up to 100 projects |

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | Root cause analysis for each bug |
| **2: Design** | Architect | Fix strategy, API format research, impact analysis |
| **3: Fix BUG-1** | Principal Engineer | Dependency/dependent action operations |
| **4: Fix BUG-2** | Principal Engineer | CustomFieldAccessor.set() for all types |
| **5: Fix BUG-3** | Principal Engineer | Missing client methods |
| **6: Fix BUG-4** | Principal Engineer | Display improvements |
| **7: Validation** | QA/Adversary | Full demo execution, regression verification |

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, confirm fix before moving on

**Critical Rules**:
- Never execute without explicit confirmation
- **ALWAYS consult Asana API documentation** for correct request formats
- Test each fix individually before moving to next bug
- Document root cause and fix for each bug

## Discovery Phase: What Must Be Explored

Before fixes can be implemented, the **Requirements Analyst** must explore:

### SaveSession Action Operations Analysis

| File/Area | Questions to Answer |
|-----------|---------------------|
| `src/autom8_asana/persistence/session.py` | How are dependency/dependent actions queued? Are they included in `commit_async()`? |
| `src/autom8_asana/persistence/session.py` | What's the difference between action ops that work (tags) and those that don't (dependencies)? |
| `src/autom8_asana/batch/` | How does BatchClient handle action operations? Are dependencies batched differently? |

### CustomFieldAccessor Analysis

| File/Area | Questions to Answer |
|-----------|---------------------|
| `src/autom8_asana/models/custom_field_accessor.py` | How does `set()` format the value for API? |
| `src/autom8_asana/models/custom_field_accessor.py` | What format does each field type need? (text vs enum vs people vs multi-enum) |
| Asana API Docs | What is the correct `custom_fields` format for task updates? |

### Client Methods Analysis

| File/Area | Questions to Answer |
|-----------|---------------------|
| `src/autom8_asana/clients/tasks.py` | What async methods exist? What's the pattern for subtasks? |
| `src/autom8_asana/clients/projects.py` | What async methods exist? What's the pattern for workspace listing? |
| `src/autom8_asana/clients/base.py` | What's the base pattern for async pagination? |

### Asana API Format Research

| Endpoint | Questions to Answer |
|----------|---------------------|
| `PUT /tasks/{gid}` | What format does `custom_fields` expect? |
| `POST /tasks/{gid}/addDependencies` | What format does this endpoint expect? |
| `POST /tasks/{gid}/setParent` | What format for insert_after/insert_before? |
| `GET /tasks/{parent_gid}/subtasks` | What fields are returned? |

## Open Questions Requiring Resolution

Before Session 2 (Design) begins, the following questions need answers:

### BUG-1 Questions (Action Operations)

1. **Action commit path**: Are dependency/dependent actions going through `commit_async()` or a different path?
2. **Batching behavior**: Are action operations batched? Do they need individual API calls?
3. **Tag vs dependency**: Why do tags work but dependencies don't? What's different in implementation?
4. **SaveResult interpretation**: `succeeded=0, failed=0` suggests ops weren't attempted—why?

### BUG-2 Questions (Custom Field Writes)

5. **API format**: What exact JSON format does Asana expect for `custom_fields` updates?
6. **Field type handling**: Does `set()` produce different formats for text vs enum vs people?
7. **GID vs value**: Should enum/multi-enum send option GID or option name?
8. **People format**: Does people field expect `[{gid}]` or `[{"gid": gid}]`?

### BUG-3 Questions (Missing Methods)

9. **Existing pattern**: What async methods exist in `TasksClient`? Is there a `get_async`?
10. **Pagination**: How should subtask listing handle pagination?
11. **Method naming**: Should it be `subtasks_async` or `get_subtasks_async` or `list_subtasks_async`?

### BUG-4 Questions (Display)

12. **People resolution**: Should we fetch user details at display time or store richer data?
13. **Multi-enum type**: Why is the captured value a string instead of list? Is this a capture bug or display bug?

## Your First Task

Confirm understanding by:

1. Summarizing the 4 bug categories and their impacts
2. Listing the 7 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step to understand root causes
4. Confirming which SDK files must be analyzed for each bug
5. Listing which open questions you need answered before Session 2

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

# Session Trigger Prompts

## Session 1: Discovery

```markdown
Begin Session 1: Bug Root Cause Discovery

Work with the @requirements-analyst agent to analyze the SDK source code and identify root causes.

**Goals:**
1. Understand why dependency/dependent operations show succeeded=0, failed=0
2. Understand why CustomFieldAccessor.set() produces failed=1 for all field types
3. Identify what async methods exist vs what's missing in TasksClient/ProjectsClient
4. Document the exact API format Asana expects for each operation type
5. Create a root cause document for each bug

**SDK Files to Analyze:**
- `src/autom8_asana/persistence/session.py` — Action operation handling
- `src/autom8_asana/models/custom_field_accessor.py` — set() implementation
- `src/autom8_asana/clients/tasks.py` — Available async methods
- `src/autom8_asana/clients/projects.py` — Available async methods
- `src/autom8_asana/batch/` — Batch execution for custom fields

**Asana API to Research:**
- Custom field update format: https://developers.asana.com/reference/updatetask
- Dependency endpoints: https://developers.asana.com/reference/adddependenciesfortask
- Subtasks endpoint: https://developers.asana.com/reference/getsubtasksfortask

**Deliverable:**
A discovery document with:
- Root cause for BUG-1 (action operations)
- Root cause for BUG-2 (custom field writes)
- Root cause for BUG-3 (missing methods)
- Root cause for BUG-4 (display issues)
- Recommended fix approach for each
- Risk assessment for each fix

Create the analysis plan first. I'll review before you execute.
```

## Session 2: Design

```markdown
Begin Session 2: Fix Strategy Design

Work with the @architect agent to design fixes based on discovery findings.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Design fix for dependency/dependent action operations
2. Design fix for CustomFieldAccessor.set() across all field types
3. Design new async methods for TasksClient and ProjectsClient
4. Design display improvements for people and multi-enum fields
5. Identify regression risks and mitigation

**Key Design Questions:**
- Should custom field format be handled in CustomFieldAccessor or in batch layer?
- Should missing client methods follow existing async patterns?
- What's the minimal change to fix each bug?

**Deliverable:**
Fix design document with:
- Proposed changes for each bug
- API format specifications
- Code location for each change
- Regression test strategy

Create the plan first. I'll review before you execute.
```

## Session 3: Fix BUG-1 (Action Operations)

```markdown
Begin Session 3: Fix Dependency/Dependent Action Operations

Work with the @principal-engineer agent to fix BUG-1.

**Prerequisites:**
- Discovery complete
- Fix design approved

**Scope:**
1. Fix `session.add_dependency()` to execute correctly
2. Fix `session.remove_dependency()` to execute correctly
3. Fix `session.add_dependent()` to execute correctly
4. Fix `session.remove_dependent()` to execute correctly
5. Verify SaveResult shows succeeded=1 after each operation

**Test Verification:**
Run demo with `-c DEP` flag and verify:
- Dependency added (check in Asana UI)
- Dependency removed (check in Asana UI)
- Dependent added (check in Asana UI)
- Dependent removed (check in Asana UI)
- SaveResult shows correct counts

**Explicitly OUT of Scope:**
- Custom field fixes (Session 4)
- Missing client methods (Session 5)
- Display improvements (Session 6)

Create the fix plan first. I'll review before you execute.
```

## Session 4: Fix BUG-2 (Custom Field Writes)

```markdown
Begin Session 4: Fix CustomFieldAccessor.set() Operations

Work with the @principal-engineer agent to fix BUG-2.

**Prerequisites:**
- BUG-1 fixed and verified

**Scope:**
1. Fix `cf.set()` for text fields
2. Fix `cf.set()` for number fields
3. Fix `cf.set()` for enum fields (single-select)
4. Fix `cf.set()` for multi-enum fields
5. Fix `cf.set()` for people fields
6. Verify SaveResult shows succeeded=1 after each operation

**Key Implementation Details:**
Based on Asana API, custom_fields format should be:
```json
{
  "custom_fields": {
    "<field_gid>": "<value>"  // text, number
    "<field_gid>": "<option_gid>"  // enum
    "<field_gid>": ["<option_gid>", ...]  // multi-enum
    "<field_gid>": ["<user_gid>", ...]  // people
  }
}
```

**Test Verification:**
Run demo with `-c STR -c PPL -c ENM -c NUM -c MEN` flags and verify:
- Each field type shows SaveResult(succeeded=1, failed=0)
- Values actually change in Asana UI
- Values can be cleared (set to null)
- Values can be restored

Create the fix plan first. I'll review before you execute.
```

## Session 5: Fix BUG-3 (Missing Client Methods)

```markdown
Begin Session 5: Add Missing Async Client Methods

Work with the @principal-engineer agent to fix BUG-3.

**Prerequisites:**
- BUG-1 and BUG-2 fixed and verified

**Scope:**
1. Add `TasksClient.subtasks_async(parent_gid, opt_fields)` method
2. Add `ProjectsClient.list_for_workspace_async(workspace_gid)` method
3. Follow existing async patterns in the client classes
4. Handle pagination if needed

**Test Verification:**
Run demo with `-c SUB -c MEM` flags and verify:
- Subtasks are fetched without AttributeError
- Siblings can be enumerated for reorder operations
- Projects are fetched without AttributeError
- Multi-project demo works (add to second project)

Create the fix plan first. I'll review before you execute.
```

## Session 6: Fix BUG-4 (Display Improvements)

```markdown
Begin Session 6: Improve Field Display

Work with the @principal-engineer agent to fix BUG-4.

**Prerequisites:**
- BUG-1, BUG-2, BUG-3 fixed and verified

**Scope:**
1. Improve people field display to show user names (not just GIDs)
2. Fix multi-enum capture/display to show as list (not string)
3. Update demo script to use improved display

**Test Verification:**
Run full demo and verify:
- People field shows: `['Tom Tenuta', 'Vince Marino']` not `['123', '456']`
- Multi-enum shows: `['Option A', 'Option B']` not `'Option A'`

Create the fix plan first. I'll review before you execute.
```

## Session 7: Validation

```markdown
Begin Session 7: Full Demo Validation

Work with the @qa-adversary agent to validate all fixes.

**Prerequisites:**
- All bugs fixed

**Goals:**

**Part 1: Individual Bug Verification**
- Run `-c TAG` - verify tags still work (regression)
- Run `-c DEP` - verify dependencies now work (BUG-1 fix)
- Run `-c DESC` - verify description still works (regression)
- Run `-c STR -c PPL -c ENM -c NUM -c MEN` - verify custom fields work (BUG-2 fix)
- Run `-c SUB` - verify subtask ordering works (BUG-3 fix)
- Run `-c MEM` - verify multi-project works (BUG-3 fix)

**Part 2: End-to-End Validation**
- Run full demo with no category flags
- Verify all 10 categories pass
- Verify state restoration works

**Part 3: Regression Testing**
- Confirm no new errors introduced
- Confirm SaveResult counts are correct for all operations
- Confirm Asana UI reflects all changes

**Deliverable:**
Validation report confirming:
- Each bug is fixed
- No regressions
- Demo is fully functional

Create the plan first. I'll review before you execute.
```

---

# Context Gathering Checklist

Before starting, gather:

**SDK Source Files:**

- [ ] `src/autom8_asana/persistence/session.py` — Action operation implementation
- [ ] `src/autom8_asana/models/custom_field_accessor.py` — set() method
- [ ] `src/autom8_asana/clients/tasks.py` — Async method patterns
- [ ] `src/autom8_asana/clients/projects.py` — Async method patterns
- [ ] `src/autom8_asana/batch/batch_client.py` — Batch execution

**Demo Files:**

- [ ] `scripts/demo_sdk_operations.py` — Demo implementation
- [ ] `scripts/_demo_utils.py` — Demo utilities

**Asana API Documentation:**

- [ ] Task update endpoint format for custom_fields
- [ ] Dependency endpoint format
- [ ] Subtasks endpoint format

**Test Data:**

- [ ] Business GID: `1203504488813198`
- [ ] Unit GID: `1203504489143268`
- [ ] Dependency Task GID: `1211596978294356`
- [ ] Workspace GID: `1143357799778608`

---

# Bug Reference Matrix

| Bug ID | Category | Symptom | Root Cause (TBD) | Session |
|--------|----------|---------|------------------|---------|
| BUG-1 | Action Ops | `SaveResult(succeeded=0, failed=0)` | Discovery needed | 3 |
| BUG-2 | Custom Fields | `SaveResult(succeeded=0, failed=1)` | Discovery needed | 4 |
| BUG-3a | Client Methods | `AttributeError: subtasks_async` | Method missing | 5 |
| BUG-3b | Client Methods | `AttributeError: list_for_workspace_async` | Method missing | 5 |
| BUG-4a | Display | People shows GIDs only | Display logic | 6 |
| BUG-4b | Display | Multi-enum shows string | Capture/display logic | 6 |

---

# Full Demo Logs Reference

```
===========================================================
  SDK Demonstration Suite
  Per TDD-SDKDEMO: Interactive validation of SDK operations
============================================================
[INFO] Categories to run: ['Tag Operations', 'Dependency Operations', ...]

# BUG-1 Evidence:
[SUCCESS] Added dependency: SaveResult(succeeded=0, failed=0)
[SUCCESS] Removed dependency: SaveResult(succeeded=0, failed=0)
[SUCCESS] Added dependent: SaveResult(succeeded=0, failed=0)
[SUCCESS] Removed dependent: SaveResult(succeeded=0, failed=0)

# BUG-2 Evidence:
BatchClient.execute: Batch complete: 0/1 succeeded
[SUCCESS] Set string field: SaveResult(succeeded=0, failed=1)
[SUCCESS] Set people field: SaveResult(succeeded=0, failed=1)
[SUCCESS] Set enum field: SaveResult(succeeded=0, failed=1)
[SUCCESS] Set number field: SaveResult(succeeded=0, failed=1)
[SUCCESS] Set multi-enum to single option: SaveResult(succeeded=0, failed=1)

# BUG-3 Evidence:
[WARN] Could not fetch siblings: 'TasksClient' object has no attribute 'subtasks_async'
[WARN] Failed to load projects: 'ProjectsClient' object has no attribute 'list_for_workspace_async'

# BUG-4 Evidence:
[INFO] Original value (user GIDs): ['1201051797275398']  # Should show names
[INFO] Display value: Meta Marketing  # Should be list: ['Meta Marketing']
```
