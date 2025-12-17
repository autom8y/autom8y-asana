# ORCHESTRATOR SESSION 6 HANDOFF

**Document ID:** ORCHESTRATOR-SESSION6-HANDOFF
**From:** Orchestrator (Main Thread)
**To:** @principal-engineer
**Date:** 2025-12-12
**Status:** Ready for Engineer Execution

---

## Mission

Implement Session 6: **P4 Auto-tracking Models + P5 Simplified Client Constructor**

Complete SDK Usability Overhaul initiative by adding:
1. **P4:** Task.save()/refresh() with implicit SaveSession management
2. **P5:** Simplified AsanaClient(token) with workspace auto-detection

---

## Current State (Sessions 1-5 Complete)

All prerequisite work complete and solid:

**Discovery (Session 1):** 6 architectural questions answered
- ✓ SaveSession suitable for implicit use
- ✓ Task can store client reference (pattern exists: _custom_fields_accessor)
- ✓ No need for Task-level dirty flag (SaveSession handles it)
- ✓ NameNotFoundError feasible (stdlib difflib)
- ✓ Workspace auto-detection possible (simple API call)
- ✓ CustomFieldAccessor can support dict access

**Requirements (Session 2):** 41 FRs across P1-P5
- ✓ All validated and prioritized
- ✓ Acceptance criteria defined
- ✓ P1, P2, P3 specifically designed

**Architecture (Session 3):** Full TDD + ADR design
- ✓ All integration points identified
- ✓ File locations confirmed
- ✓ Method signatures specified
- ✓ Design decisions documented in ADRs

**P1 Implementation (Session 4):** 12 Direct Methods
- ✓ 12 async/sync method pairs on TasksClient
- ✓ All use SaveSession internally
- ✓ Pattern proven and tested

**P2 + P3 Implementation (Session 5):** 47 Tests
- ✓ P2 CustomFieldAccessor dict access (__getitem__, __setitem__)
- ✓ P3 NameResolver with per-session caching
- ✓ 31 name resolution tests + 16 custom field tests

**Test Status:** 2,959 tests passing, 0 failures

---

## What You're Implementing

### P4: Auto-tracking Models (3-4 hours)

**Add to Task model:**
```python
# Store client reference
_client: Any = PrivateAttr(default=None)

# Save changes
async def save_async(self) -> Task
def save(self) -> Task

# Reload from API
async def refresh_async(self) -> Task
def refresh(self) -> Task
```

**Update TasksClient to assign _client:**
```python
# In get_async(), create_async(), update_async()
task._client = self._client
```

**Key Design Points (All in ADRs):**
- Each save_async() creates fresh SaveSession, destroyed at method end
- No new dirty tracking in Task (SaveSession.ChangeTracker handles it)
- Custom field changes detected via _modifications (P2 feature)
- refresh_async() reloads all fields, clears pending modifications

**Files Modified:**
1. `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py`
2. `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`

**Tests Required:** ~10 cases (field changes, custom field changes, refresh, error handling)

### P5: Simplified Client Constructor (1.5-2 hours)

**Enhance AsanaClient:**
```python
# New: simple pattern
client = AsanaClient(token="...")  # Auto-detects workspace

# Existing: still works (backward compat)
client = AsanaClient(
    token="...",
    workspace_gid="...",
    cache=None,
    http_client=None
)
```

**Add auto-detection logic:**
- Fetch from /users/me endpoint
- If exactly 1 workspace → use it
- If 0 workspaces → raise ConfigurationError (invalid token)
- If >1 workspaces → raise ConfigurationError (ambiguous, specify workspace_gid)

**Files Modified:**
1. `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/client.py`
2. `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/exceptions.py` (if ConfigurationError missing)

**Tests Required:** ~7 cases (1 workspace, 0 workspaces, >1 workspaces, explicit workspace, backward compat)

---

## Comprehensive Specification

Complete implementation details provided in:

**PRIMARY:** `/Users/tomtenuta/Code/autom8_asana/docs/initiatives/SESSION-6-IMPLEMENTATION-CONTEXT.md`
- Method signatures (all specified)
- Implementation pseudocode (both P4 and P5)
- Testing requirements (17 test cases total)
- File locations and insertion points
- Error handling requirements
- Success criteria

**SUPPORTING:**
- **ADR-0061:** Implicit SaveSession Lifecycle (P4 design)
- **ADR-0063:** Client Reference Storage (P4 design)
- **ADR-0064:** Dirty Detection Strategy (P4 design)
- **SESSION-6-READINESS-ASSESSMENT:** Readiness verification and risk analysis

---

## Prerequisites Met

All blockers cleared:

| Prerequisite | Status | Evidence |
|--------------|--------|----------|
| SaveSession available | ✓ | Sessions 1-3 implemented and tested |
| CustomFieldAccessor _modifications tracking | ✓ | Session 5 P2 implemented |
| TasksClient methods exist | ✓ | Session 4 P1 enhanced tasks client |
| PrivateAttr pattern established | ✓ | Task._custom_fields_accessor example exists |
| @sync_wrapper decorator available | ✓ | Used throughout P1 implementation |
| httpx available | ✓ | Used in HTTP client |
| ConfigurationError exists (check) | ? | Verify in exceptions.py; add if missing |

**One Pre-Implementation Check:**
- Confirm ConfigurationError exists in `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/exceptions.py`
- If missing, add it (simple exception class)

---

## Quality Gates You Must Satisfy

### Before Commit

- [ ] All 17 new tests pass (10 for P4, 7 for P5)
- [ ] All 2,959+ existing tests pass
- [ ] mypy passes (type safety complete)
- [ ] No regressions (SaveSession unchanged, P1-P3 tests all pass)
- [ ] Documentation complete (docstrings with examples)
- [ ] Error handling verified (ValueError, ConfigurationError)

### Code Quality

- [ ] Follow project conventions (see `.claude/CLAUDE.md`)
- [ ] Docstrings: Every method has clear docstring with example
- [ ] Type hints: Complete (mypy should pass)
- [ ] Comments: Added for non-obvious logic
- [ ] Line length: Follows project style
- [ ] No TODOs left (either implement or document in future enhancement)

---

## Key Architectural Decisions (Already Approved)

**You don't need to make these decisions—they're in ADRs:**

| Decision | ADR | Status | Your Job |
|----------|-----|--------|----------|
| Implicit SaveSession in save_async() | ADR-0061 | Approved | Implement it exactly as specified |
| Store client as strong reference (not WeakRef) | ADR-0063 | Approved | Use `_client: Any = PrivateAttr(default=None)` |
| Leverage SaveSession.ChangeTracker for dirty detection | ADR-0064 | Approved | Just call session.track(); no new logic |
| GID detection for workspace auto-detection | (Design) | Confirmed | Use 16-digit numeric pattern |
| Error: ConfigurationError for workspace issues | (Design) | Confirmed | Not ValueError; use ConfigurationError |

**No ambiguities.** You can implement with confidence.

---

## Testing Strategy

### P4 Tests (~10 cases)

Use existing P1 test patterns:
- Mock SaveSession context manager
- Mock HTTP client for refresh_async()
- Verify track() called
- Verify commit_async() called
- Verify task modifications persisted
- Test error case (no _client)

### P5 Tests (~7 cases)

Use httpx mocking:
- Mock /users/me endpoint responses
- Test with 0, 1, >1 workspaces
- Verify ConfigurationError messages
- Test backward compatibility (explicit workspace_gid)
- Verify temporary httpx client creation/cleanup

---

## Recommended Order

**Sequential (not parallel):**

1. **Implement P4 first** (3-4 hours)
   - Why: Foundational; P5 is independent
   - Verify: All P4 tests pass + full suite passes
   - Commit: P4 only

2. **Then implement P5** (1.5-2 hours)
   - Why: P5 has no dependencies; can do after P4
   - Verify: All P5 tests pass + full suite passes
   - Commit: P5 only

**Total Time:** 5-6 hours

---

## Handoff Package

Everything you need is in one place:

| Document | Location | Purpose |
|----------|----------|---------|
| **SESSION-6-IMPLEMENTATION-CONTEXT** | `/docs/initiatives/SESSION-6-IMPLEMENTATION-CONTEXT.md` | MAIN SPEC: All implementation details |
| ADR-0061 | `/docs/decisions/ADR-0061-implicit-savesession-lifecycle.md` | P4 design rationale |
| ADR-0063 | `/docs/decisions/ADR-0063-client-reference-storage.md` | P4 design rationale |
| ADR-0064 | `/docs/decisions/ADR-0064-dirty-detection-strategy.md` | P4 design rationale |
| SESSION-6-READINESS-ASSESSMENT | `/docs/initiatives/SESSION-6-READINESS-ASSESSMENT.md` | Readiness verification |

---

## Starting Checklist

Before you begin:

- [ ] Read SESSION-6-IMPLEMENTATION-CONTEXT completely
- [ ] Understand P4 scope (Task + TasksClient changes)
- [ ] Understand P5 scope (AsanaClient.__init__ enhancement)
- [ ] Check ConfigurationError exists (add if needed)
- [ ] Verify @sync_wrapper available
- [ ] Confirm file paths in spec match your working directory
- [ ] Plan test structure (which test file for each)

---

## Escalation Paths

If you hit a blocker:

| Issue | Escalate To | Example |
|-------|-------------|---------|
| SaveSession behavior unclear | Architect | "How does SaveSession.track() handle nested objects?" |
| Design ambiguity | Architect | "Should refresh_async() preserve _client reference?" |
| Test infrastructure | QA/Adversary | "How do I mock SaveSession in tests?" |
| Type safety questions | Architect | "Should _client be typed as AsanaClient or Any?" |
| Dependency missing | Orchestrator | "ConfigurationError doesn't exist" |

**No expected blockers** (all design frozen in ADRs).

---

## Success Criteria

### Final Handoff (To QA)

When complete:

1. **All Tests Pass**
   - 10 new P4 tests: PASS
   - 7 new P5 tests: PASS
   - 2,959+ existing tests: PASS
   - Total: ~2,976+ tests passing

2. **Code Quality**
   - mypy passes
   - No warnings
   - Docstrings complete
   - Type hints complete

3. **Specification Compliance**
   - Task.save_async() uses SaveSession
   - Task.refresh_async() reloads from API
   - AsanaClient(token) auto-detects workspace
   - All error messages clear
   - Backward compatibility verified

4. **Documentation**
   - Docstrings include examples
   - ADR links provided where relevant
   - Error cases documented

---

## What Success Looks Like

After Session 6:

```
✓ Task.save() / Task.save_async() — implicit SaveSession, minimal cognitive load
✓ Task.refresh() / Task.refresh_async() — reload from API, clear pending changes
✓ AsanaClient(token) — single-argument pattern for common case
✓ All 2,976+ tests passing
✓ mypy clean
✓ Ready for Session 7 (QA/Validation)
```

---

## Next Phases (Context)

### Session 7: QA/Validation

@qa-adversary will:
- Run full test suite
- Validate acceptance criteria
- Check integration scenarios
- Verify no regressions
- Approve for release

### After Session 7: Release

- Merge to main
- Tag as v0.2.0 (P1-P5 complete)
- Publish to PyPI
- SDK usability overhaul complete

---

## Final Notes

- **No ambiguities remain.** All architectural decisions are in approved ADRs.
- **Pattern matches existing code.** P4 mirrors P1 (implicit SaveSession); P4 uses existing _client storage pattern (matches _custom_fields_accessor).
- **You can implement with confidence.** No surprises expected.
- **Ask for clarification if anything is unclear.** Better to ask than guess.

---

## Sign-Off

**Status:** Ready for Engineer Execution

**Recommendation:** Proceed immediately with Session 6 P4 + P5 implementation.

**Engineer:** Start with SESSION-6-IMPLEMENTATION-CONTEXT and proceed through P4, then P5.

---

**Document Complete — Orchestrator → Engineer Handoff Ready**

