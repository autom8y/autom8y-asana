# Orchestrator Initialization: autom8_asana SDK Usability Overhaul

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

**Domain-Specific Skills** (CRITICAL - use heavily):
- **`autom8-asana-domain`** - SDK patterns, SaveSession, Asana resources, async-first, client patterns
  - Activates when: Working with Task models, SaveSession, CustomFieldAccessor, TasksClient

**Workflow Skills**:
- **`documentation`** - PRD/TDD/ADR templates, artifact protocols
- **`10x-workflow`** - Agent coordination, session protocol, quality gates
- **`prompting`** - Agent invocation patterns

**How Skills Work**: Skills load automatically based on your current task. Invoke skills explicitly when you need deep reference (e.g., "Let me check the `autom8-asana-domain` skill for the SaveSession patterns").

## Your Role: Orchestrator

You coordinate a 4-agent development workflow. You plan, delegate, coordinate, and verify - you do not implement directly.

## Your Specialist Agents

| Agent | Invocation | Responsibility |
|-------|------------|----------------|
| **Requirements Analyst** | `@requirements-analyst` | Requirements definition, acceptance criteria, scope boundaries |
| **Architect** | `@architect` | TDDs, ADRs, system design, trade-off analysis |
| **Principal Engineer** | `@principal-engineer` | Implementation, code quality, technical execution |
| **QA/Adversary** | `@qa-adversary` | Validation, failure mode testing, security/quality review |

## The Mission: Transform SDK Usability

Transform the autom8_asana SDK from "functional but tedious" to "easy by default, powerful when needed." Make simple things simple (1-2 lines) while keeping complex things possible (SaveSession for batching).

### Why This Initiative?

- **Developer Ergonomics**: Reduce ceremony for common operations (5+ lines to 1-2 lines)
- **Lower Learning Curve**: New users shouldn't need to understand SaveSession for basic tasks
- **Natural API**: Names work as well as GIDs; custom fields feel like dictionaries
- **Backward Compatibility**: All existing code continues to work unchanged

### Current State

**SDK Foundation (Complete)**:
- SaveSession with Unit of Work pattern (track, commit, dependency graph)
- CustomFieldAccessor with `get()/set()` pattern and change tracking
- TasksClient with async CRUD operations
- Batch API with automatic chunking
- Async-first design with sync wrappers

**What's Tedious Today**:

```python
# Current: Add tag to task (5-6 lines)
async with SaveSession(client) as session:
    task = await client.tasks.get(task_gid)
    session.track(task)
    session.add_tag(task.gid, tag_gid)  # Must know tag GID!
    await session.commit_async()

# Current: Set custom field (6-7 lines)
async with SaveSession(client) as session:
    task = await client.tasks.get(task_gid)
    session.track(task)
    cf = task.get_custom_fields()
    cf.set("Priority", "High")
    await session.commit_async()
```

**What We Want**:

```python
# Target: Add tag to task (1 line)
await client.tasks.add_tag_async(task_gid, "Urgent")  # Name or GID

# Target: Set custom field (2 lines)
task = await client.tasks.get(task_gid)
task.custom_fields["Priority"] = "High"
await task.save()  # Auto-tracks and commits
```

### Prioritized Changes

| Priority | Change | Impact | Effort | Description |
|----------|--------|--------|--------|-------------|
| **P1** | Direct methods on TasksClient | High | Low | `add_tag_async`, `move_to_section_async`, etc. |
| **P2** | Property-style custom field access | High | Medium | `task.custom_fields["X"] = Y` with change tracking |
| **P3** | Built-in name resolution | High | High | Accept names or GIDs for tags, sections, projects |
| **P4** | Auto-tracking models | Medium | Medium | `task.save()` creates implicit SaveSession |
| **P5** | Simplify client constructor | Low | Low | Single-arg pattern for common case |

### Key Constraints

- **No breaking changes**: All existing code must continue to work
- **Additive only**: New methods supplement, not replace, existing patterns
- **Async-first**: Follow existing `_async` suffix pattern
- **Type safety**: Full mypy compliance on new code
- **SaveSession stays powerful**: Complex workflows still use explicit SaveSession
- **Python 3.10+**: Must support autom8 runtime

### Design Decisions (From Prompt -1)

These decisions should be confirmed in Discovery, but the recommended defaults are:

| Decision | Recommendation | Rationale |
|----------|----------------|-----------|
| Direct method return type | Return updated `Task` | Consistent with existing client pattern |
| Name resolution failures | Raise `NameNotFoundError` | Explicit errors are better than silent failures |
| `task.save()` pattern | Implicit SaveSession | Ergonomic for simple cases; explicit still available |

### Success Criteria

1. Single-task operations complete in 1-2 lines (no explicit SaveSession)
2. `task.custom_fields["Priority"]` works for read and write
3. Names accepted anywhere GIDs are currently required
4. `task.save()` commits changes without explicit session management
5. All existing tests pass (backward compatibility)
6. New code has >80% test coverage
7. Type hints complete (mypy passes)
8. Documentation updated with new patterns

## Session-Phased Approach

| Session | Agent | Deliverable | Priority Coverage |
|---------|-------|-------------|-------------------|
| **1: Discovery** | Requirements Analyst | SDK analysis, API inventory, integration points | - |
| **2: Requirements** | Requirements Analyst | PRD-SDKUX with acceptance criteria per priority | P1-P5 |
| **3: Architecture** | Architect | TDD-SDKUX + ADRs for key patterns | All |
| **4: Implementation P1** | Principal Engineer | Direct methods on TasksClient | P1 |
| **5: Implementation P2-P3** | Principal Engineer | Custom field access + Name resolution | P2, P3 |
| **6: Implementation P4-P5** | Principal Engineer | Auto-tracking + Client simplification | P4, P5 |
| **7: Validation** | QA/Adversary | Integration tests, backward compat verification | All |

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rules**:
- Never execute without explicit confirmation
- Consult `autom8-asana-domain` skill for SDK patterns
- Ensure backward compatibility at every step
- Run tests after each implementation session

## Discovery Phase: What Must Be Explored

Before requirements can be finalized, the **Requirements Analyst** must explore:

### SDK Codebase Analysis

| File/Area | Questions to Answer |
|-----------|---------------------|
| `src/autom8_asana/clients/tasks.py` | Current methods, extension points |
| `src/autom8_asana/models/task.py` | Task model structure, how to add `save()` |
| `src/autom8_asana/models/custom_field_accessor.py` | How to bridge to `__getitem__`/`__setitem__` |
| `src/autom8_asana/persistence/session.py` | How to create implicit sessions |
| `src/autom8_asana/clients/` | Other clients for name resolution (tags, sections, projects) |

### Name Resolution Analysis

| Resource | How to Resolve Names |
|----------|---------------------|
| Tags | `client.tags.list(workspace)` or project-specific |
| Sections | `client.sections.list(project)` |
| Projects | `client.projects.list(workspace)` |
| Assignees | `client.users.list(workspace)` |

### Existing Patterns to Preserve

| Pattern | Where Used | Must Not Break |
|---------|------------|----------------|
| `SaveSession` context manager | All batch operations | Existing tracking/commit flow |
| `task.get_custom_fields()` | Custom field access | Existing accessor pattern |
| Action operations | `session.add_tag()`, etc. | Existing deferred execution |
| Async/sync parity | All client methods | Sync wrappers via decorator |

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins:

### API Design Questions

1. **Direct method signature**: Should `add_tag_async(task_gid, tag)` accept `tag: str | Tag` (polymorphic) or require separate methods?
2. **Name resolution scope**: Workspace-level or project-level resolution for tags/sections?
3. **Custom field wrapper type**: New `CustomFieldDict` class or enhance existing `CustomFieldAccessor`?

### Integration Questions

4. **Implicit SaveSession lifecycle**: Create per-operation or cache on Task instance?
5. **Name cache invalidation**: TTL-based or require explicit refresh?
6. **Error message quality**: Include suggestions for similar names on `NameNotFoundError`?

## Your First Task

Confirm understanding by:

1. Summarizing the SDK Usability Overhaul goal in 2-3 sentences
2. Listing the 7 sessions and their deliverables
3. Confirming the 5 priorities (P1-P5) and which sessions cover them
4. Identifying which SDK files must be analyzed in Discovery
5. Listing which open questions you need answered before Session 2

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

# Session Trigger Prompts

## Session 1: Discovery

```markdown
Begin Session 1: SDK Usability Discovery

Work with the @requirements-analyst agent to analyze the SDK codebase and identify integration points.

**Goals:**
1. Map current TasksClient methods and extension patterns
2. Understand CustomFieldAccessor internals for P2
3. Identify name resolution data sources (tags, sections, projects)
4. Document SaveSession patterns to preserve
5. Analyze Task model for `save()` integration point
6. Identify potential circular import issues
7. Answer open questions from Prompt 0

**SDK Files to Analyze:**
- `src/autom8_asana/clients/tasks.py` - Current methods
- `src/autom8_asana/models/task.py` - Model structure
- `src/autom8_asana/models/custom_field_accessor.py` - Field access
- `src/autom8_asana/persistence/session.py` - SaveSession internals
- `src/autom8_asana/clients/tags.py` - Tag resolution
- `src/autom8_asana/clients/sections.py` - Section resolution

**Skills to Consult:**
- `autom8-asana-domain` - SDK patterns and conventions

**Deliverable:**
A discovery document with:
- API inventory (current vs. proposed)
- Integration points for each priority (P1-P5)
- Name resolution strategy recommendation
- Backward compatibility verification approach
- Answers to open questions

Create the analysis plan first. I'll review before you execute.
```

## Session 2: Requirements

```markdown
Begin Session 2: SDK Usability Requirements Definition

Work with the @requirements-analyst agent to create PRD-SDKUX.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Define P1 requirements (direct methods)
2. Define P2 requirements (custom field access)
3. Define P3 requirements (name resolution)
4. Define P4 requirements (auto-tracking)
5. Define P5 requirements (client constructor)
6. Define backward compatibility requirements
7. Define acceptance criteria for each requirement

**Consult Skills:**
- `autom8-asana-domain` for existing patterns
- `documentation` skill for PRD template

**PRD Organization:**
- FR-DIRECT-*: Direct method requirements (P1)
- FR-CFIELD-*: Custom field access requirements (P2)
- FR-NAMES-*: Name resolution requirements (P3)
- FR-TRACK-*: Auto-tracking requirements (P4)
- FR-CLIENT-*: Client constructor requirements (P5)
- FR-COMPAT-*: Backward compatibility requirements
- NFR-*: Performance, type safety, test coverage requirements

Create the plan first. I'll review before you execute.
```

## Session 3: Architecture

```markdown
Begin Session 3: SDK Usability Architecture Design

Work with the @architect agent to create TDD-SDKUX and required ADRs.

**Prerequisites:**
- PRD-SDKUX approved

**Goals:**
1. Design direct method architecture (P1)
2. Design CustomFieldDict/accessor bridge (P2)
3. Design NameResolver with caching (P3)
4. Design Task.save() and implicit session (P4)
5. Design simplified client constructor (P5)
6. Identify new ADRs needed
7. Create implementation sequence

**Required ADRs:**
- ADR-XXXX: Direct Methods vs. SaveSession Actions
- ADR-XXXX: Name Resolution Caching Strategy
- ADR-XXXX: Implicit SaveSession Lifecycle
- ADR-XXXX: Custom Field Dictionary Interface

**Architecture Questions:**
- Where does NameResolver live (client-level or global)?
- How does Task.save() access the client?
- Should CustomFieldDict be a new class or enhanced accessor?

**Module Structure to Consider:**

```
src/autom8_asana/
├── clients/
│   ├── tasks.py (add direct methods)
│   └── name_resolver.py (NEW)
├── models/
│   ├── task.py (add save(), custom_fields property)
│   └── custom_field_dict.py (NEW or enhance accessor)
└── persistence/
    └── session.py (add implicit session factory)
```

Create the plan first. I'll review before you execute.
```

## Session 4: Implementation Phase 1 - Direct Methods

```markdown
Begin Session 4: Implementation Phase 1 - Direct Methods (P1)

Work with the @principal-engineer agent to implement direct methods on TasksClient.

**Prerequisites:**
- PRD-SDKUX approved
- TDD-SDKUX approved

**Phase 1 Scope (P1 Only):**
1. `TasksClient.add_tag_async(task_gid, tag_gid)` - Add tag
2. `TasksClient.remove_tag_async(task_gid, tag_gid)` - Remove tag
3. `TasksClient.move_to_section_async(task_gid, section_gid)` - Move section
4. `TasksClient.set_assignee_async(task_gid, assignee_gid)` - Set assignee
5. `TasksClient.add_to_project_async(task_gid, project_gid, section_gid=None)` - Add to project
6. `TasksClient.remove_from_project_async(task_gid, project_gid)` - Remove from project
7. Sync wrappers for all above methods

**Implementation Pattern:**
```python
async def add_tag_async(self, task_gid: str, tag_gid: str) -> Task:
    """Add tag to task without explicit SaveSession.

    Args:
        task_gid: Task GID
        tag_gid: Tag GID (name resolution in P3)

    Returns:
        Updated Task
    """
    async with SaveSession(self._client) as session:
        session.add_tag(task_gid, tag_gid)
        result = await session.commit_async()
    return await self.get(task_gid)
```

**Hard Constraints:**
- Methods return updated Task (not SaveResult)
- Use existing SaveSession internally (don't bypass)
- Follow async/sync parity pattern
- Full type hints

**Explicitly OUT of Phase 1:**
- Name resolution (P3 - Session 5)
- Custom field access (P2 - Session 5)
- Task.save() (P4 - Session 6)

Create the plan first. I'll review before you execute.
```

## Session 5: Implementation Phase 2 - Custom Fields & Name Resolution

```markdown
Begin Session 5: Implementation Phase 2 - Custom Fields & Names (P2, P3)

Work with the @principal-engineer agent to implement property-style custom fields and name resolution.

**Prerequisites:**
- Phase 1 complete and tested

**Phase 2 Scope (P2 + P3):**

**P2: Custom Field Access**
1. `CustomFieldDict` class with `__getitem__`/`__setitem__`
2. `Task.custom_fields` property returning `CustomFieldDict`
3. Change tracking integration (mark dirty on set)
4. Type preservation for enum, number, text fields

**P3: Name Resolution**
1. `NameResolver` class with caching
2. `resolve_tag(name_or_gid, project_gid=None)` -> GID
3. `resolve_section(name_or_gid, project_gid)` -> GID
4. `resolve_project(name_or_gid, workspace_gid)` -> GID
5. `resolve_assignee(name_or_gid, workspace_gid)` -> GID
6. `NameNotFoundError` with helpful message
7. TTL-based cache (5 min default)
8. Update P1 methods to accept names

**Integration Points:**
- CustomFieldDict wraps existing CustomFieldAccessor
- NameResolver attached to client instance
- Direct methods resolve names before operation

**Test Cases:**
- Custom field get/set by name
- Name resolution hit/miss
- Cache expiry behavior
- NameNotFoundError with similar suggestions

Create the plan first. I'll review before you execute.
```

## Session 6: Implementation Phase 3 - Auto-tracking & Client

```markdown
Begin Session 6: Implementation Phase 3 - Auto-tracking & Client (P4, P5)

Work with the @principal-engineer agent to complete the usability improvements.

**Prerequisites:**
- Phase 2 complete and tested

**Phase 3 Scope (P4 + P5):**

**P4: Auto-tracking Models**
1. `Task.save()` method that creates implicit SaveSession
2. `Task._client` reference for session creation
3. `Task.refresh()` method for explicit re-fetch
4. Change detection (only save if dirty)

**P5: Client Constructor**
1. Simplified single-arg pattern: `AsanaClient(token)`
2. Default workspace detection (if user has one)
3. Preserve full constructor for advanced cases

**Task.save() Implementation:**
```python
async def save_async(self) -> "Task":
    """Save changes using implicit SaveSession.

    Returns:
        Updated Task from API
    """
    if not self._dirty:
        return self
    async with SaveSession(self._client) as session:
        session.track(self)
        await session.commit_async()
    return await self._client.tasks.get(self.gid)
```

**Test Cases:**
- Task.save() commits changes
- Task.save() no-op when not dirty
- Task.refresh() fetches latest
- Simplified client constructor works
- Full constructor still works

Create the plan first. I'll review before you execute.
```

## Session 7: Validation

```markdown
Begin Session 7: SDK Usability Validation

Work with the @qa-adversary agent to validate the implementation.

**Prerequisites:**
- All implementation phases complete

**Goals:**

**Part 1: Direct Method Validation (P1)**
- All 6 direct methods work correctly
- Return updated Task
- Handle API errors gracefully
- Sync wrappers work

**Part 2: Custom Field Validation (P2)**
- Get by name works
- Set by name marks dirty
- Type preservation (enum, number, text)
- Change tracking integration

**Part 3: Name Resolution Validation (P3)**
- Name lookup succeeds
- GID passthrough works
- Cache hit/miss behavior
- NameNotFoundError with suggestions
- TTL expiry works

**Part 4: Auto-tracking Validation (P4)**
- Task.save() commits changes
- Dirty detection works
- Task.refresh() fetches latest
- Client reference maintained

**Part 5: Backward Compatibility**
- Existing SaveSession patterns work unchanged
- Existing custom field accessor works
- All pre-existing tests pass
- No breaking import changes

**Part 6: Documentation Verification**
- README updated with new patterns
- Docstrings complete
- Type hints pass mypy

Create the plan first. I'll review before you execute.
```

---

# Quick Reference: Implementation Patterns

When implementing, follow these patterns from the SDK:

### Async Method Pattern
```python
async def method_async(self, arg: str) -> ReturnType:
    """Async implementation."""
    ...

def method(self, arg: str) -> ReturnType:
    """Sync wrapper."""
    return sync_wrapper(self.method_async)(arg)
```

### Error Handling Pattern
```python
class NameNotFoundError(AsanaSDKError):
    """Resource name could not be resolved to GID."""
    def __init__(self, resource_type: str, name: str, suggestions: list[str] | None = None):
        self.resource_type = resource_type
        self.name = name
        self.suggestions = suggestions or []
        msg = f"{resource_type} '{name}' not found"
        if suggestions:
            msg += f". Did you mean: {', '.join(suggestions[:3])}"
        super().__init__(msg)
```

### Caching Pattern
```python
from functools import lru_cache
from time import time

class TTLCache:
    def __init__(self, ttl_seconds: int = 300):
        self._cache: dict[str, tuple[Any, float]] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Any | None:
        if key in self._cache:
            value, expires = self._cache[key]
            if time() < expires:
                return value
            del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = (value, time() + self._ttl)
```

---

# Context Gathering Checklist

Before starting, verify access to:

**SDK Code:**
- [ ] `src/autom8_asana/clients/tasks.py` - Direct method target
- [ ] `src/autom8_asana/models/task.py` - Task.save() target
- [ ] `src/autom8_asana/models/custom_field_accessor.py` - P2 integration
- [ ] `src/autom8_asana/persistence/session.py` - SaveSession patterns
- [ ] `src/autom8_asana/clients/tags.py` - Name resolution source
- [ ] `src/autom8_asana/clients/sections.py` - Name resolution source

**Documentation:**
- [ ] `docs/initiatives/sdk-usability-prompt-minus-1.md` - Initiative scoping
- [ ] `.claude/skills/autom8-asana-domain/` - SDK patterns
- [ ] `.claude/skills/documentation/templates/` - PRD/TDD templates

**Tests:**
- [ ] `tests/` directory structure - Where to add tests
- [ ] Existing test patterns to follow

---

# Success Metrics Summary

| Metric | Current | Target | How to Verify |
|--------|---------|--------|---------------|
| Lines for tag add | 5-6 | 1-2 | Code comparison |
| Custom field access | `.get_custom_fields().get("X")` | `["X"]` | API signature |
| GID requirement | 100% | 0% (names work) | Method signatures |
| Test coverage (new code) | 0% | >80% | pytest-cov |
| Type safety | - | mypy passes | mypy src/ |
| Backward compat | - | 100% | Existing tests pass |
