# Session 1: Discovery - Analyst Context Frame

> Hand-off document for Requirements Analyst. Contains mission, design confirmations, analysis scope, and quality gates.

---

## SESSION 1 MISSION

**Analyze the autom8_asana SDK codebase to map current architecture, identify integration points for P1-P5, answer 6 open questions, and validate technical feasibility for the usability improvements.**

---

## DESIGN DECISION CONFIRMATIONS

The following 3 blocking decisions from Prompt -1 have been APPROVED by the user. Use these as constraints during your analysis:

| Decision | Confirmed Choice | Rationale |
|----------|------------------|-----------|
| **Direct Method Return Type** | Return updated `Task` object | Consistent with existing TasksClient pattern (`.get()` returns Task, not SaveResult) |
| **Name Resolution Failures** | Raise `NameNotFoundError` with suggestions | Explicit errors are better than silent failures; suggestions aid debugging |
| **task.save() Pattern** | Implicit SaveSession | Ergonomic for simple cases; users can still use explicit SaveSession for complex workflows |

**Your role in discovery**: Validate that these decisions are architecturally sound by analyzing the code. Surface any implementation blockers or gotchas discovered during analysis.

---

## ANALYST RESPONSIBILITIES (What You Must Accomplish)

### 1. MAP TASKSCLIENT ARCHITECTURE
- Inventory all current async methods (e.g., `get_async`, `update_async`, `list_async`)
- Document method naming convention (all use `_async` suffix)
- Identify return type pattern (currently returns `Task` model or dict)
- Analyze sync wrapper pattern (how sync methods wrap async)
- Document existing error handling approach
- Find examples of methods that already do similar operations (e.g., update-like operations)

### 2. UNDERSTAND CUSTOMFIELDACCESSOR
- Analyze how `CustomFieldAccessor` currently works (read lines 14-80 in custom_field_accessor.py)
- Map the internal data structure (`_data` list of dicts with gid/name/value)
- Identify the change tracking mechanism (`_modifications` dict)
- Understand how `set(name_or_gid, value)` currently marks changes
- Assess what needs to change to support `task.custom_fields["Priority"] = "High"` syntax
- Determine if new `CustomFieldDict` class is needed or if `CustomFieldAccessor` can be enhanced

### 3. IDENTIFY NAME RESOLUTION DATA SOURCES
For each resource type, document:

| Resource | Current List Method | Scope | Cost |
|----------|---------------------|-------|------|
| **Tags** | `client.tags.list(workspace_gid)` | Workspace-level | Single call per workspace |
| **Sections** | `client.sections.list(project_gid)` | Project-level | Single call per project |
| **Projects** | `client.projects.list(workspace_gid)` | Workspace-level | Single call per workspace |
| **Assignees** | `client.users.list(workspace_gid)` | Workspace-level | Single call per workspace |

**To analyze**:
- Review `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tags.py` to understand list structure
- Review `sections.py`, `projects.py`, `users.py` to understand list methods
- Determine if we can cache lists or if we must resolve on-demand

### 4. UNDERSTAND SAVESESSION INTEGRATION
- Read through `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py`
- Document the context manager lifecycle (how `async with SaveSession(client)` works)
- Understand how `session.track(task)` registers changes
- Map how `session.commit_async()` applies changes
- Identify if SaveSession can be created implicitly (from within Task.save())
- Determine if Task needs a reference to the client (`self._client`)

### 5. ANALYZE TASK MODEL FOR INTEGRATION
- Review Task model (first 80 lines of task.py)
- Assess if Task can safely store `_client` reference without circular imports
- Understand PrivateAttr usage (already used for similar hidden state)
- Identify where to add `save()` and `refresh()` methods
- Determine dirty tracking mechanism (how to detect if task has changes)
- Check if `custom_fields` property exists (currently appears to be raw list)

### 6. ANSWER ALL 6 OPEN QUESTIONS
These are the questions you must answer with concrete code evidence:

**Blocking Questions** (already decided, but validate feasibility):
1. Is it architecturally sound to have direct methods return updated `Task`?
2. Can we cleanly raise `NameNotFoundError` when names are not found?
3. Can Task safely hold a `_client` reference for implicit SaveSession?

**Informing Questions** (provide recommendation):
4. Should we implement all 6 direct methods in P1 or subset them?
5. Should name resolution use TTL caching or explicit invalidation?
6. Should custom field access be read-only or read-write?

---

## CRITICAL QUESTIONS TO ANSWER

Your discovery document must answer these 6 questions with evidence from code analysis:

### Must Answer (Feasibility Validation)

**Q1: Direct Method Return Type Feasibility**
- Current: TasksClient.update_async returns Task
- Question: Can add_tag_async, move_to_section_async, etc. follow same pattern?
- Find evidence: Look at how update_async fetches and returns Task

**Q2: Name Resolution Error Pattern**
- Question: Can we create a NameNotFoundError that fits SDK error patterns?
- Find evidence: Look at existing error classes in exceptions.py
- Deliverable: Proposed NameNotFoundError class definition

**Q3: Task._client Reference Safety**
- Question: Can Task store a client reference without circular imports?
- Problem: Task.save() needs to call SaveSession(self._client)
- Find evidence: Check imports in task.py, session.py for circular dependency risk
- Deliverable: Confirmed safe approach or identified workaround

### Should Answer (Design Input)

**Q4: P1 Methods Scope**
- Prompt 0 suggests 6 methods: add_tag, remove_tag, move_to_section, set_assignee, add_to_project, remove_from_project
- Question: Are these the right core set? Missing any? Too many?
- Find evidence: Review session.py for existing action operations
- Deliverable: Recommended method list with rationale

**Q5: Name Resolution Caching Strategy**
- Options: TTL (5 min default) vs Explicit invalidation vs Both
- Question: What's practical given API call cost?
- Find evidence: How expensive are list calls? How often do names change?
- Deliverable: Recommended caching strategy with tradeoffs

**Q6: Custom Field Access Read/Write**
- Question: Should custom_fields["Priority"] = "High" work, or read-only?
- Problem: Writes need to mark task as dirty
- Find evidence: Check how modification tracking works in CustomFieldAccessor
- Deliverable: Recommendation with implementation approach

---

## SDK FILES TO ANALYZE

Analyze these files and extract specific information:

### File 1: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`
**Extract**:
- List all current methods (async and sync)
- Document return type for update-like operations
- Find pattern: how does get_async return Task?
- Find pattern: how do sync wrappers work?

### File 2: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py`
**Extract**:
- Current fields and structure
- Check if _client or similar already exists
- Review imports (any circular dependency risk?)
- Understand how custom_fields field is structured (currently `list[dict]`)

### File 3: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/custom_field_accessor.py`
**Extract**:
- Full implementation of __init__, _build_index, set, get methods
- How is _modifications tracked?
- How does name->gid resolution work currently?
- What would need to change for __getitem__/__setitem__ support?

### File 4: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py`
**Extract**:
- How is SaveSession a context manager?
- How are changes tracked and applied?
- Can SaveSession(client) be created from Task without issues?
- What happens in __aenter__ and __aexit__?

### File 5: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tags.py`
**Extract**:
- How does tags.list(workspace_gid) work?
- What does the returned list look like (structure)?

### File 6: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py`
**Extract**:
- How does sections.list(project_gid) work?
- What structure is returned?

### File 7: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/projects.py`
**Extract**:
- How does projects.list(workspace_gid) work?

### File 8: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/users.py`
**Extract**:
- How does users.list(workspace_gid) work?

### File 9: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/exceptions.py`
**Extract**:
- What error classes exist?
- What's the pattern for SDK exceptions?
- Design pattern for custom error types?

---

## DELIVERABLE SPECIFICATION

Your discovery must produce a **single document**: `DISCOVERY-SDKUX-001.md`

### Structure

```
# SDK Usability Overhaul - Discovery Report

## 1. API Inventory
- Current TasksClient methods (table)
- Proposed direct methods (table)
- Return type analysis
- Sync/async parity check

## 2. Integration Points Analysis

### P1: Direct Methods
- Current pattern for similar operations
- Proposed implementation approach
- Return type validation (confirmed Task)
- Sync wrapper pattern applicability

### P2: Custom Field Access
- Current CustomFieldAccessor structure
- __getitem__/__setitem__ design approach
- Change tracking mechanism
- Enhancement vs. new class recommendation

### P3: Name Resolution
- Data source inventory (tags, sections, projects, assignees)
- Resolution scope analysis (workspace/project level)
- Caching strategy recommendation
- Error pattern recommendation

### P4: Auto-tracking
- Task._client reference safety analysis
- SaveSession implicit creation approach
- Dirty tracking mechanism analysis
- save()/refresh() integration points

### P5: Client Constructor
- Current constructor analysis
- Simplified pattern proposal
- Backward compatibility impact

## 3. Open Questions - Answers with Evidence

### Blocking Questions (Feasibility Validation)
- Q1: Direct method return type → [FEASIBLE, with evidence]
- Q2: Name resolution errors → [APPROACH, with NameNotFoundError design]
- Q3: Task._client reference → [SAFE, no circular imports risk]

### Informing Questions (Design Input)
- Q4: P1 methods scope → [RECOMMENDATION: 6 core methods]
- Q5: Name caching strategy → [RECOMMENDATION: TTL with rationale]
- Q6: Custom field read-write → [RECOMMENDATION: read-write with tracking]

## 4. Backward Compatibility Verification

- [ ] Existing SaveSession code still works unchanged
- [ ] Existing task.get_custom_fields() still works
- [ ] All existing methods unchanged (additive only)
- [ ] No breaking import changes

## 5. Technical Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Circular imports with Task._client | Low | High | [Mitigation approach from code analysis] |
| Name resolution API cost | Medium | Medium | [Caching strategy recommendation] |
| Type erasure in dict-style access | Medium | Medium | [Preservation approach] |

## 6. Readiness Assessment

- [ ] All 6 questions answered
- [ ] No blocking technical issues found
- [ ] Implementation approach documented for each priority
- [ ] Backward compatibility path confirmed
- [ ] Session 2 (Requirements) can proceed: YES/NO

## 7. Code Evidence Appendix

- Key excerpts from each analyzed file
- Method signatures (current vs. proposed)
- Import chains (for circular dependency analysis)
- Error class patterns (for NameNotFoundError design)
```

### Length Expectation
- 2,000-3,000 words
- Code evidence for each major question
- Specific file citations with line numbers
- Clear recommendations for ambiguous points

---

## READINESS CHECKLIST

Before you begin analysis, confirm you have access to:

- [ ] Read Prompt 0 (mission, 7 sessions, P1-P5, open questions)
- [ ] Read Prompt -1 (problem validation, design decisions, risks)
- [ ] Read this context frame (your specific responsibilities)
- [ ] Access to SDK codebase (all files listed above)
- [ ] Understood the 3 approved design decisions
- [ ] Understood what makes discovery "done" (quality gates below)

---

## QUALITY GATES - DISCOVERY IS COMPLETE WHEN

**Content Quality**:
- [ ] All 6 open questions answered with code evidence
- [ ] Each answer supported by specific file excerpts (with line numbers)
- [ ] P1-P5 integration points identified and documented
- [ ] No ambiguities remain that would block Requirements session

**Backward Compatibility**:
- [ ] Confirmed: No breaking changes to existing APIs
- [ ] Confirmed: Additive changes only
- [ ] Confirmed: SaveSession patterns preserved

**Feasibility**:
- [ ] No blocking technical issues discovered
- [ ] All proposed integration points validated in code
- [ ] Implementation approach documented (even if high-level)

**Clarity**:
- [ ] Recommendations are specific (not vague)
- [ ] Tradeoffs clearly stated where relevant
- [ ] Next phase (Requirements) has clear input

**Readiness for Session 2**:
- [ ] Requirements Analyst can write PRD without re-analyzing code
- [ ] Architect can design TDD without re-analyzing code
- [ ] Implementation can begin in Session 4 with discovery as reference

---

## HANDOFF SUCCESS CRITERIA

When you finish, you will provide:

1. **Discovery Document** (`DISCOVERY-SDKUX-001.md`) with all sections complete
2. **Summary Email** to Orchestrator:
   - All 6 questions answered (yes/no on each)
   - Any new risks discovered
   - Readiness for Session 2 (thumbs up or blockers)
   - Estimated complexity for each priority based on code analysis

3. **Session 2 Input** prepared:
   - API inventory for Requirements to use
   - Integration point details for TDD design
   - Recommendations for each open question

---

## HOW TO INVOKE THIS

This session is **immediately ready to execute**. No additional questions needed.

**When you are ready**:
- Read this frame completely
- Begin detailed code analysis (start with tasks.py)
- Write findings into DISCOVERY-SDKUX-001.md
- Reference specific line numbers and file paths
- Answer all 6 questions with evidence
- Deliver document and readiness summary

---

## SKILL TO CONSULT

**`autom8-asana-domain`** - Use heavily for:
- SDK patterns and conventions
- SaveSession internals
- CustomFieldAccessor design
- Async/sync wrapper patterns
- Error handling patterns

---

**Status**: READY FOR EXECUTION
**Analyst**: @requirements-analyst
**Next Phase**: Session 2 (Requirements Definition) after discovery complete

