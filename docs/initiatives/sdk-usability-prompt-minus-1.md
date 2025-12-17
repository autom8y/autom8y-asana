# Prompt -1: Initiative Scoping - SDK Usability Overhaul

> **Purpose**: Validate readiness for the 4-agent workflow. Answer: "Do we know enough to write Prompt 0?"

---

## Initiative Summary

**One-liner**: Transform the autom8_asana SDK from "functional but tedious" to "easy by default, powerful when needed" through direct client methods, property-style custom field access, built-in name resolution, and ergonomic API improvements.

**Sponsor**: Tom Tenuta

**Triggered by**: Architect triage identifying that the current SDK requires 5+ lines of ceremony for simple operations, forcing users to understand SaveSession patterns even for single-task updates.

---

## Pre-Flight Checklist

### 1. Problem Validation

| Question | Answer | Confidence |
|----------|--------|------------|
| Is there a real problem? | Yes - SDK requires excessive ceremony for common operations | High |
| Who experiences it? | Developers using autom8_asana for Asana automation | High |
| What's the cost of not solving? | Low adoption, code duplication, developer frustration, workarounds | High |
| Is this the right time? | Yes - SDK foundation (SaveSession, CustomFieldAccessor) is stable | High |

**Problem Statement Draft**:
> The autom8_asana SDK provides powerful abstractions (SaveSession, batch operations) but requires excessive ceremony for common operations. A single task update requires understanding SaveSession, tracking, and commit patterns. Custom fields require two-step access (`get().set()`). All lookups require GIDs, not human-readable names. This friction discourages adoption and creates error-prone code for simple use cases.

### 2. Scope Boundaries

| Dimension | In Scope | Out of Scope | Decision Rationale |
|-----------|----------|--------------|-------------------|
| **Direct Methods** | `add_tag_async`, `move_to_section_async`, `set_assignee_async`, etc. on TasksClient | Bulk operations, complex workflows | Common operations first; complex stays in SaveSession |
| **Custom Fields** | Property-style access (`task.custom_fields["X"] = Y`) | Custom field creation, schema modification | Read/write access, not admin operations |
| **Name Resolution** | Accept names OR GIDs for tags, sections, projects, assignees | Full fuzzy matching, approximate search | Exact match by name is sufficient |
| **Auto-tracking** | Opt-in `task.save()` pattern | Default auto-tracking for all models | Explicit is better; `save()` is sugar |
| **Client Constructor** | Simplified single-arg pattern | Multi-environment configuration | Focus on common case |

### 3. Complexity Assessment

| Factor | Assessment | Notes |
|--------|------------|-------|
| **Scope** | Module | Multiple convenience layers, no new infrastructure |
| **Technical Risk** | Low-Medium | Building on proven SDK patterns |
| **Integration Points** | Medium | TasksClient, CustomFieldAccessor, SaveSession |
| **Team Familiarity** | High | SDK patterns well-documented |
| **Unknowns** | Low | Clear user needs, established patterns |

**Recommended Complexity Level**: Module

**Workflow Recommendation**: Full 4-agent workflow (adjusted sessions for phased priorities)

**Rationale**: While individual changes are low-complexity, the initiative spans multiple SDK layers (client, models, persistence) and requires careful API design to maintain backward compatibility. Each priority (P1-P5) can be a focused session.

### 4. Dependencies & Blockers

| Dependency | Status | Owner | Blocking? |
|------------|--------|-------|-----------|
| SaveSession (existing) | Done | - | No |
| CustomFieldAccessor (existing) | Done | - | No |
| TasksClient patterns (existing) | Done | - | No |
| Business Model implementation | In Progress | - | No (parallel workstream) |
| Name resolution data source (projects, tags, sections) | Available via API | - | No |

**Blockers**: None identified

### 5. Success Definition (Draft)

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Lines for single-task tag add | 5-6 lines | 1-2 lines | Code comparison |
| Custom field access pattern | `task.get_custom_fields().get("X")` | `task.custom_fields["X"]` | API signature |
| GID requirement for operations | 100% require GID | 0% require GID (names work) | API acceptance |
| Auto-tracking model save | N/A | `task.save()` available | Feature exists |
| Type safety | Partial | Full (mypy passes) | Zero type errors |
| Backward compatibility | N/A | 100% existing code works | No breaking changes |

### 6. Rough Effort Estimate

| Phase | Effort | Confidence |
|-------|--------|------------|
| Discovery / Requirements | 1 session | High |
| Architecture / Design | 1 session | High |
| Implementation (P1: Direct Methods) | 1 session | High |
| Implementation (P2: Custom Fields) | 1 session | Medium |
| Implementation (P3: Name Resolution) | 1-2 sessions | Medium |
| Implementation (P4: Auto-tracking) | 1 session | Medium |
| Implementation (P5: Client Constructor) | 0.5 session | High |
| Validation / QA | 1 session | Medium |
| **Total** | 7-8 sessions | Medium |

**Note**: Phased implementation allows early value delivery (P1 in Session 4) while higher-effort items (P3) can be deferred if needed.

### 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking backward compatibility | Low | High | Additive changes only; existing APIs unchanged |
| Name resolution performance (API calls) | Medium | Medium | Caching layer for resolved names; lazy resolution |
| SaveSession complexity leakage | Low | Medium | Clear separation: direct methods vs. SaveSession |
| Type erasure in dict-style custom fields | Medium | Medium | Preserve CustomFieldAccessor types via __getitem__ |
| Scope creep (too many convenience methods) | Medium | Low | Strict P1-P5 prioritization; defer extras |

---

## Open Questions to Resolve Before Prompt 0

### Must Answer (Blocking)

| # | Question | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 1 | Should direct methods return the updated Task or just success? | Return Task / Return bool / Return SaveResult | Return updated Task (consistent with current client pattern) | DECISION NEEDED |
| 2 | How should name resolution failures be handled? | Raise error / Return None / Best-effort match | Raise `NameNotFoundError` with suggestions | DECISION NEEDED |
| 3 | Should `task.save()` create implicit SaveSession or require one? | Implicit / Require explicit / Configurable | Implicit for ergonomics (user can still use explicit SaveSession) | DECISION NEEDED |

### Should Answer (Informing)

| # | Question | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 4 | Which direct methods to implement in P1? | Full list / Core subset | Core subset: `add_tag`, `remove_tag`, `move_to_section`, `set_assignee`, `add_to_project`, `remove_from_project` | Recommend core subset |
| 5 | Should name resolution cache use TTL or explicit invalidation? | TTL / Explicit / Both | TTL (5 min default) for simplicity | Recommend TTL |
| 6 | Property-style custom fields: read-only or read-write? | Read-only / Read-write | Read-write with change tracking | Recommend read-write |

### Nice to Answer (Context)

| # | Question | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 7 | P4 (auto-tracking) timeline | Phase 1 / Phase 2 | Phase 1 (it's straightforward) | Flexible |
| 8 | Should we add `task.refresh()` for explicit re-fetch? | Yes / No | Yes (useful for stale data scenarios) | Flexible |

---

## Spike Recommendations (If Applicable)

No spikes needed - patterns are well-understood from existing SDK.

**Reference implementations**:
- SaveSession already demonstrates client abstraction patterns
- CustomFieldAccessor shows type-safe field access
- Existing TasksClient shows async method patterns

---

## Go/No-Go Decision

### Criteria for "Go"

- [x] Problem is validated and worth solving
- [x] Scope is bounded and achievable
- [x] No blocking dependencies
- [x] Complexity level appropriate for chosen workflow
- [x] Success metrics are measurable
- [x] Rough effort estimate acceptable
- [x] High-risk items have mitigation plans

### Recommendation

**CONDITIONAL GO** - Initiative is well-scoped, pending 3 design decisions

**Rationale**:
- Clear user need with measurable improvement
- Builds on stable SDK foundation
- Low technical risk with additive approach
- Phased priorities allow early value delivery
- No blocking dependencies

**Conditions (must resolve before Session 2)**:
1. Decide: Direct method return type (Task vs SaveResult)
2. Decide: Name resolution failure behavior (raise vs None)
3. Decide: `task.save()` implicit vs explicit SaveSession

---

## Next Steps

1. **Resolve 3 blocking questions** (15 min)
   - Get stakeholder input on direct method return types
   - Confirm error handling preference for name resolution
   - Decide implicit SaveSession behavior

2. **Generate Prompt 0** (after decisions)
   - Use this document as context
   - Structure sessions around P1-P5 priorities

3. **Start Fresh Session**
   - Open new Claude Code session
   - Provide Prompt 0 to initialize orchestrator

---

## Appendix: Quick Reference

### Prioritized Opportunities (from Architect Triage)

| Priority | Change | Impact | Effort | Session Target |
|----------|--------|--------|--------|----------------|
| P1 | Direct methods on TasksClient | High | Low | Session 4 |
| P2 | Property-style custom field access | High | Medium | Session 5 |
| P3 | Built-in name resolution | High | High | Sessions 5-6 |
| P4 | Auto-tracking models (`task.save()`) | Medium | Medium | Session 6 |
| P5 | Simplify client constructor | Low | Low | Session 6 |

### Current vs. Target Patterns

**Current: Add tag to task**
```python
async with SaveSession(client) as session:
    task = await client.tasks.get(task_gid)
    session.track(task)
    session.add_tag(task.gid, tag_gid)  # Must know tag GID
    await session.commit_async()
```

**Target: Add tag to task**
```python
await client.tasks.add_tag_async(task_gid, "Urgent")  # Name or GID works
```

**Current: Set custom field**
```python
async with SaveSession(client) as session:
    task = await client.tasks.get(task_gid)
    session.track(task)
    cf = task.get_custom_fields()
    cf.set("Priority", "High")
    await session.commit_async()
```

**Target: Set custom field**
```python
task = await client.tasks.get(task_gid)
task.custom_fields["Priority"] = "High"
await task.save()
```

### Skills Reference

| Skill | Purpose | Key Files |
|-------|---------|-----------|
| `autom8-asana-domain` | SDK patterns, SaveSession, client patterns | code-conventions.md, context.md |
| `documentation` | PRD template for requirements phase | templates/prd.md |
| `10x-workflow` | Agent coordination, quality gates | SKILL.md, quality-gates.md |
| `prompting` | Agent invocation patterns | patterns/*.md |

### Related Documentation

| Document | Location | Relevance |
|----------|----------|-----------|
| SDK Conventions | `.claude/skills/autom8-asana-domain/code-conventions.md` | Current patterns |
| Project Context | `.claude/PROJECT_CONTEXT.md` | SDK purpose and constraints |
| SaveSession impl | `src/autom8_asana/persistence/session.py` | Integration point |
| CustomFieldAccessor | `src/autom8_asana/models/custom_field_accessor.py` | P2 integration |
| TasksClient | `src/autom8_asana/clients/tasks.py` | P1 target |

---

*This Prompt -1 **conditionally validated** that the initiative is ready for the full 4-agent workflow. **Resolve 3 blocking questions, then proceed to Prompt 0**.*
