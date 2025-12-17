# SESSION 3: Architecture Context for SDK Usability Overhaul

**For: @architect**
**From: Discovery (Session 1) + Requirements (Session 2)**
**Date: 2025-12-12**
**Status: Ready for Architecture Design**

---

## Executive Summary

PRD-SDKUX defines 41 functional requirements across 5 priorities (P1-P5) to transform the autom8_asana SDK from "functional but tedious" to "easy by default, powerful when needed."

All 6 critical architectural questions from Discovery have been answered and validated as feasible. Your job in Session 3 is to design the implementation approach, document design decisions in TDD and ADRs, and ensure Engineer can implement without clarification.

**Key Insight:** Discovery eliminated all architectural uncertainty. This should be a straightforward design phase.

---

## What PRD-SDKUX Specifies (41 FRs Summary)

### Priority 1: Direct Methods (12 FRs - P1)
**6 async/sync method pairs on TasksClient**
- `add_tag_async() / add_tag()` - Add tag to task
- `remove_tag_async() / remove_tag()` - Remove tag
- `move_to_section_async() / move_to_section()` - Move to section
- `set_assignee_async() / set_assignee()` - Set assignee
- `add_to_project_async() / add_to_project()` - Add to project
- `remove_from_project_async() / remove_from_project()` - Remove from project

**Pattern:** Each method wraps SaveSession internally, returns Task object, accepts GID parameters (P3 adds name support later)

**Success Metric:** Add tag drops from 5-6 lines to 1 line (for simple case)

---

### Priority 2: Custom Field Access (5 FRs - P2)
**Dictionary-style access to custom fields**
- `task.custom_fields["Priority"]` for get (new `__getitem__()`)
- `task.custom_fields["Priority"] = "High"` for set (new `__setitem__()`)
- Type preservation (enum, number, text, date, multi-enum, people)
- Change tracking integration (marks task dirty)
- Error handling (KeyError for missing fields)

**Pattern:** Enhance existing `CustomFieldAccessor` with `__getitem__()` and `__setitem__()` methods

**Success Metric:** Custom field access drops from `.get_custom_fields().set("X", Y)` to `["X"] = Y`

---

### Priority 3: Name Resolution (11 FRs - P3)
**Resolve human-readable names to GIDs**
- `resolve_tag_async(name_or_gid)` → GID
- `resolve_section_async(name_or_gid, project_gid)` → GID
- `resolve_project_async(name_or_gid, workspace_gid)` → GID
- `resolve_assignee_async(name_or_gid, workspace_gid)` → GID
- Sync wrappers for all
- Update P1 methods to accept names polymorphically
- New `NameNotFoundError` exception with fuzzy match suggestions
- Per-SaveSession caching (zero staleness)

**Pattern:** New `NameResolver` class; P1 methods enhanced to call resolver before operation

**Success Metric:** GID requirement drops from 100% to 0% (names work everywhere)

---

### Priority 4: Auto-tracking Models (6 FRs - P4)
**Implicit SaveSession management via Task methods**
- `Task.save_async()` / `Task.save()` - Save changes using implicit session
- `Task.refresh_async()` / `Task.refresh()` - Reload from API
- `Task._client` private attribute storage (PrivateAttr)
- Dirty detection via SaveSession.ChangeTracker (no new Task-level logic)

**Pattern:** Task stores client reference; save() creates implicit SaveSession internally

**Success Metric:** Save changes drops from explicit SaveSession to `task.save()`

---

### Priority 5: Client Constructor (3 FRs - P5)
**Simplified client initialization**
- Single-argument pattern: `AsanaClient(token)` (new)
- Auto-detect workspace if exactly one exists
- Full constructor still available for advanced cases

**Pattern:** Enhance `AsanaClient.__init__()` with optional simplified signature

**Success Metric:** Common case drops from full constructor to single argument

---

### Backward Compatibility (4 FRs)
- SaveSession workflows unchanged
- Custom field accessor unchanged
- Pre-existing tests pass
- Exception handling unchanged

---

### Non-Functional Requirements (5 NFRs)
- Type safety: mypy passes
- Test coverage: >80% for new code
- Documentation: Updated docstrings + README
- Performance: No regressions on existing operations
- Name caching: 100% hit rate for repeated names in session

---

## Key Design Decisions Already Validated by Discovery

### 1. Direct Method Pattern: Return Task Objects ✓
**Decision:** `add_tag_async()` returns updated Task, not SaveResult
**Discovery Evidence:** TasksClient already follows this pattern (get_async, create_async, update_async all return Task via `Task.model_validate()`)
**Your Job:** Document this pattern in TDD and ensure consistency

### 2. Task.save() Uses Implicit SaveSession ✓
**Decision:** Create SaveSession internally; no user-visible session management
**Discovery Evidence:**
- No circular import risk with TYPE_CHECKING
- PrivateAttr precedent exists (Task._custom_fields_accessor)
- SaveSession designed to support implicit creation
**Your Job:** Design implicit session lifecycle; document in ADR

### 3. NameNotFoundError with Fuzzy Matching ✓
**Decision:** Use difflib.get_close_matches() for suggestions
**Discovery Evidence:** Straightforward design; stdlib available
**Your Job:** Design exception error message format; document in TDD

### 4. CustomFieldAccessor Enhancement (Not New Class) ✓
**Decision:** Add `__getitem__()` and `__setitem__()` to existing accessor
**Discovery Evidence:** Accessor already has `_modifications` dict and `has_changes()`; avoid new class
**Your Job:** Design interface contract; ensure backward compatibility

### 5. Per-SaveSession Caching ✓
**Decision:** Cache names within SaveSession context (zero staleness)
**Discovery Evidence:** Multiple sources available (PageIterator); per-session cache is simplest
**Your Job:** Design cache location (SaveSession or NameResolver); document lifecycle

### 6. No Task-Level Dirty Tracking ✓
**Decision:** Leverage SaveSession.ChangeTracker; Task.save() just calls session.track()
**Discovery Evidence:** SaveSession captures snapshots at track time; detects changes at commit
**Your Job:** Design Task.save() to delegate dirty detection to SaveSession

---

## What PRD Specifies for Your Design

### Integration Points (Where Code Goes)
```
src/autom8_asana/
├── clients/
│   ├── tasks.py
│   │   └── Add 6 direct methods (P1) + name resolution calls (P3)
│   └── name_resolver.py (NEW)
│       └── NameResolver class with resolve_*() methods (P3)
├── models/
│   ├── task.py
│   │   ├── Add _client PrivateAttr (P4)
│   │   └── Add save()/save_async(), refresh()/refresh_async() (P4)
│   └── custom_field_accessor.py
│       └── Add __getitem__(), __setitem__() methods (P2)
├── exceptions.py
│   └── Add NameNotFoundError (P3)
├── client.py
│   └── Enhance __init__() for simplified constructor (P5)
└── persistence/
    └── session.py
        └── Integrate NameResolver (P3 caching)
```

### Method Signatures (From PRD)

**P1 Direct Methods:**
```python
async def add_tag_async(self, task_gid: str, tag_gid: str) -> Task
def add_tag(self, task_gid: str, tag_gid: str) -> Task
# Similar for remove_tag, move_to_section, set_assignee, add_to_project, remove_from_project
```

**P2 Custom Fields:**
```python
def __getitem__(self, name_or_gid: str) -> Any
def __setitem__(self, name_or_gid: str, value: Any) -> None
```

**P3 Name Resolution:**
```python
async def resolve_tag_async(self, name_or_gid: str, project_gid: str | None = None) -> str
async def resolve_section_async(self, name_or_gid: str, project_gid: str) -> str
async def resolve_project_async(self, name_or_gid: str, workspace_gid: str) -> str
async def resolve_assignee_async(self, name_or_gid: str, workspace_gid: str) -> str
```

**P4 Auto-tracking:**
```python
async def save_async(self) -> Task
def save(self) -> Task
async def refresh_async(self) -> Task
def refresh(self) -> Task
_client: Any = PrivateAttr(default=None)
```

**P5 Client Constructor:**
```python
def __init__(self, token: str, workspace_gid: str | None = None, ...)
# Plus auto-detection logic
```

---

## Acceptance Criteria for Each Feature Class (From PRD)

### P1 Direct Methods
- [ ] Method exists on TasksClient
- [ ] Returns updated Task object (not SaveResult)
- [ ] Uses SaveSession internally
- [ ] Raises APIError on invalid GIDs
- [ ] Sync wrapper uses @sync_wrapper decorator
- [ ] All 6 methods implemented (add_tag, remove_tag, move_to_section, set_assignee, add_to_project, remove_from_project)

### P2 Custom Fields
- [ ] `task.custom_fields["Priority"]` returns value (get)
- [ ] `task.custom_fields["Priority"] = "High"` sets value (set)
- [ ] Raises KeyError for missing fields (get only)
- [ ] Type preserved (enum, number, text, date, multi-enum, people)
- [ ] Marks task dirty on set
- [ ] Existing `.get_custom_fields()` still works

### P3 Name Resolution
- [ ] All 4 resolver methods exist (tag, section, project, assignee)
- [ ] GID passthrough works (already-GID returns as-is)
- [ ] Name matching is case-insensitive, exact match
- [ ] NameNotFoundError raised with suggestions (difflib fuzzy match)
- [ ] Suggestions include up to 3 similar names + available list (first 10)
- [ ] Per-SaveSession caching (zero staleness)
- [ ] P1 methods updated to call resolvers polymorphically

### P4 Auto-tracking
- [ ] `task.save()` and `task.save_async()` exist
- [ ] `task.refresh()` and `task.refresh_async()` exist
- [ ] Task._client reference stored via PrivateAttr
- [ ] save() creates implicit SaveSession internally
- [ ] Dirty detection via SaveSession snapshot (no Task-level tracking)
- [ ] refresh() reloads from API, updates all fields
- [ ] Raises ValueError if Task._client is None

### P5 Client Constructor
- [ ] `AsanaClient(token)` pattern works
- [ ] Auto-detects workspace if exactly 1 exists
- [ ] Raises ConfigurationError if 0 or >1 workspaces
- [ ] Full constructor still works (backward compat)

### Backward Compatibility
- [ ] SaveSession unchanged
- [ ] CustomFieldAccessor unchanged (only additions)
- [ ] All pre-existing tests pass
- [ ] Exception hierarchy unchanged (NameNotFoundError is addition)

---

## Architectural Questions for You to Decide

Discovery answered "is this feasible?" for all 6 questions. You need to decide the implementation details:

### 1. NameResolver Location & Lifecycle
**Options:**
- A) New `NameResolver` class in `src/autom8_asana/clients/name_resolver.py`
- B) Methods directly on `AsanaClient`
- C) Methods on `SaveSession` (cache lifetime)

**Recommendation (from Discovery):** Option A + instance on SaveSession for caching
**Your Decision:** Where does NameResolver live? How is it attached to SaveSession?

### 2. Cache Invalidation Detail
**Options:**
- A) Per-SaveSession cache only (simplest, zero staleness)
- B) TTL-based cache on client (optimized, some staleness)
- C) Hybrid (per-session + optional client-level)

**PRD Spec:** Per-SaveSession (MVP). TTL cache as future enhancement.
**Your Decision:** Design for per-session only, or design to support both?

### 3. GID Detection Pattern
**Option A:** GID is exactly 16 characters, all numeric
**Option B:** Use `gid_pattern = re.compile(r'^\d{16}$')`
**Option C:** Keep track of GIDs separately; ambiguity raises error

**Recommendation:** Option A (simple, follows Asana format)
**Your Decision:** Confirm this heuristic or propose alternative?

### 4. Implicit SaveSession Client Reference
**Options:**
- A) Strong reference: `task._client = client`
- B) Weak reference: `task._client = weakref.ref(client)`

**Discovery Finding:** Strong reference unlikely to cause memory issues (short-lived tasks)
**Your Decision:** Strong or weak? Document trade-off in ADR

### 5. Error Handling in Task.save()
**Options:**
- A) Raise PartialSaveError if commit has any failures
- B) Raise first error only
- C) Return SaveResult (more information, less ergonomic)

**PRD Spec:** Option A (PartialSaveError with error details)
**Your Decision:** Confirm or propose alternative?

### 6. Action Operations in Task.save()
**Question:** Should `task.save()` flush pending action operations (add_tag, move_to_section, etc.), or only save field modifications?

**Current Design:** Only field modifications (actions are explicit via SaveSession)
**Your Decision:** Confirm or propose alternative?

---

## Required ADRs (You Decide Scope)

Discovery suggests 5-6 ADRs. PRD gives you authority to define what needs documentation:

**Likely ADRs:**
1. **Direct Methods Architecture** - Why wrap SaveSession instead of implementing directly? Why return Task not SaveResult?
2. **Name Resolution Caching** - Why per-SaveSession? What are trade-offs vs. TTL-based?
3. **Implicit SaveSession Lifecycle** - How does Task.save() create and manage session? Risks?
4. **CustomFieldAccessor Enhancement vs. Wrapper** - Why add methods to existing class vs. wrap in new CustomFieldDict?
5. **Client Reference Storage** - Why strong reference? Circular import risks? Memory implications?
6. **Dirty Detection Strategy** - Why no Task-level flag? Rely entirely on SaveSession snapshot?

---

## Files to Reference in Your TDD

When designing, cite evidence from these files:

**Existing Patterns (Follow These):**
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py` (lines 46-68, 155-198, 322-342)
  - Return pattern: `return Task.model_validate(data)`
  - Async/sync pattern: async method + @sync_wrapper
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py` (lines 114-134)
  - PrivateAttr precedent: `_custom_fields_accessor: CustomFieldAccessor | None = PrivateAttr(default=None)`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/custom_field_accessor.py`
  - Existing methods: `get()`, `set()`, `has_changes()`, `to_api_dict()`
  - Change tracking: `_modifications` dict
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py` (lines 195-256, 469-556)
  - SaveSession.track() and change detection
  - Context manager lifecycle (async + sync)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/exceptions.py` (lines 26-99)
  - Exception hierarchy; AsanaError base class

---

## Complexity Assessment

**Expected Complexity Level:** Module (per architect.md complexity calibration)

Rationale:
- Clear API surface (TasksClient methods + Task methods + NameResolver)
- Minimal layering (direct integration with existing SaveSession + CustomFieldAccessor)
- No external API contracts (SaveSession already exists)
- Team can operate the design
- No need for full Service-level rigor (observability, deployment, etc.)

**You may adjust this assessment in your TDD.**

---

## Testing Strategy (For Your TDD)

QA will need comprehensive tests (Session 7). Specify in TDD:

**P1 Direct Methods Tests:**
- Happy path: Method returns updated Task
- Error cases: Invalid GID raises APIError
- Integration: Full round-trip with SaveSession

**P2 Custom Field Tests:**
- Get/set operations
- Type preservation (enum, number, date, etc.)
- Dirty detection on set
- Backward compatibility with .get_custom_fields()

**P3 Name Resolution Tests:**
- Name lookup (exact match, case-insensitive)
- GID passthrough
- Fuzzy match suggestions on error
- Caching behavior (hit/miss)
- Cache clearing on session exit

**P4 Auto-tracking Tests:**
- save() commits changes
- refresh() reloads state
- Dirty detection (no-op when clean)
- Client reference required (raises ValueError if None)

**P5 Constructor Tests:**
- Single-argument pattern
- Auto-detection (1 workspace, 0 workspaces, >1 workspace cases)
- Full constructor backward compatibility

**Backward Compatibility Tests:**
- Existing SaveSession patterns work
- Existing custom field accessor works
- All pre-existing tests pass

---

## Success Criteria for TDD Completion (Session 3 Handoff)

Hand off to Engineer when your TDD includes:

- [ ] Every FR has a design response (which component, which method, how it integrates)
- [ ] Component diagram is drawable (TasksClient, NameResolver, Task, SaveSession relationships)
- [ ] Method signatures defined (parameters, return types, exceptions)
- [ ] Data flow for critical paths explicit (e.g., task.save() → SaveSession → API)
- [ ] All ADRs written with discovery evidence and rationale
- [ ] Integration points specified (exactly which files, which lines get modified)
- [ ] Complexity level justified
- [ ] Risks identified with mitigations
- [ ] Engineer could start tomorrow without clarifying questions

---

## Implementation Sequencing (Guidance from PRD)

PRD specifies dependency graph (lines 1212-1246):

**Critical Path:** P2 (Custom Fields) → P4 (Auto-tracking)

**Recommended Implementation Order:**
1. P1 (Direct Methods) - Independent, no blockers
2. P2 (Custom Field Access) - Independent, parallel with P1
3. P3 (Name Resolution) - Integrates with P1, after P1 complete
4. P4 (Auto-tracking) - Depends on P2, after P2 complete
5. P5 (Client Constructor) - Independent, can run anytime

Engineer will implement in sessions 4, 5a, 5b, 6a, 6b based on your TDD sequencing.

---

## Checklist for You Before Session 4

Before invoking Engineer, verify:

- [ ] PRD-SDKUX is fully understood (read entire document)
- [ ] All 41 FRs have corresponding TDD design responses
- [ ] Method signatures match PRD exactly
- [ ] All 5-6 ADRs are written and reasoned
- [ ] No ambiguities remain (Engineer won't ask clarifications)
- [ ] Testing strategy is specified for QA
- [ ] Backward compatibility verified in design
- [ ] Risk mitigations documented

---

## Available Resources

**Documentation Skill:**
- TDD template: `/Users/tomtenuta/Code/autom8_asana/.claude/skills/documentation/templates/tdd.md`
- ADR template: `/Users/tomtenuta/Code/autom8_asana/.claude/skills/documentation/templates/adr.md`

**Existing Documentation:**
- Discovery: `/Users/tomtenuta/Code/autom8_asana/docs/decisions/DISCOVERY-SDKUX-001.md`
- PRD: `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-SDKUX.md`
- Project Context: `/Users/tomtenuta/Code/autom8_asana/.claude/PROJECT_CONTEXT.md`
- Glossary: `/Users/tomtenuta/Code/autom8_asana/.claude/GLOSSARY.md`

**Domain Skill (SDK Patterns):**
- Consult `autom8-asana-domain` skill for SaveSession, PrivateAttr, async/sync patterns, existing architecture

---

## Handoff Gates

**You are ready to handoff to Engineer (Session 4) when:**

From architect.md (lines 166-175):
- [ ] TDD traces to approved PRD ✓ (PRD approved; will trace in TDD)
- [ ] All significant decisions have ADRs (you'll write these)
- [ ] Component boundaries and responsibilities explicit (you'll define)
- [ ] Interfaces defined (method signatures, exceptions)
- [ ] Complexity level justified (guidance: Module)
- [ ] Risks identified with mitigations (you'll document)
- [ ] Engineer could implement without clarifying questions (acid test)

---

## Next Steps

1. **Read PRD-SDKUX** fully (lines 1-1382)
2. **Review Discovery evidence** (DISCOVERY-SDKUX-001) for context
3. **Create TDD-SDKUX** using documentation template
   - Component architecture
   - Method signatures and contracts
   - Data flows for critical paths
   - Complexity justification
4. **Create 5-6 ADRs** for significant decisions
   - Direct Methods Pattern
   - Name Resolution Caching
   - Implicit SaveSession Lifecycle
   - CustomFieldAccessor Enhancement
   - Client Reference Storage
   - Dirty Detection Strategy (optional if straightforward)
5. **Verify Engineer readiness** using checklist above
6. **Signal completion** to main thread for Session 4 handoff

---

**You are now ready to begin Session 3: SDK Usability Architecture Design.**

Good luck. This should be straightforward—all the hard questions were answered in Discovery.
