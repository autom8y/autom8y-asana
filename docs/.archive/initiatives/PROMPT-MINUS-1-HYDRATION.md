# Prompt -1: Initiative Scoping - Business Model Hydration

> **Purpose**: Validate readiness for the 4-agent workflow. Answer: "Do we know enough to write Prompt 0?"

---

## Initiative Summary

**One-liner**: Enable the SDK to hydrate business model hierarchies from any task entry point, not just from the Business root.

**Sponsor**: SDK Usability / Integration Friction Reduction

**Triggered by**: Observation that integrations encountering non-root tasks (webhooks, search results, deep links) cannot reliably access the "business model experience" (navigation to parents, siblings, holders, and typed descendants) without manual orchestration.

---

## Pre-Flight Checklist

### 1. Problem Validation

| Question | Answer | Confidence |
|----------|--------|------------|
| Is there a real problem? | **Yes** - `_fetch_holders_async()` is stubbed in `business.py:520-542` and `unit.py:320-327`. Hydration requires "starting from Business" with manual `_populate_holders()` calls. | High |
| Who experiences it? | SDK consumers who receive tasks from webhooks, search results, or action callbacks - they get typed entities but no navigable hierarchy. | High |
| What's the cost of not solving? | Integration friction: each caller must understand the internal structure and manually orchestrate hydration. Duplicate logic, inconsistent behavior, missed caches, wrong cascades. | High |
| Is this the right time? | **Yes** - Business model layer (Phase 1-3) is complete. The hydration mechanism is the explicit "Phase 2" TODO blocking real-world usage. | High |

**Problem Statement Draft**:
> The SDK provides typed Business Model entities (Business, Unit, Contact, Offer, etc.) with rich navigation properties and field inheritance. However, these navigation properties only work correctly when the hierarchy is populated top-down from the Business root via `_populate_holders()`. When a caller starts from a non-root task (e.g., a Contact received from a webhook), they get the typed entity but cannot navigate to `contact.business`, `contact.contact_holder.owner`, or traverse the hierarchy without manually fetching and wiring references. This defeats the purpose of the typed model layer.

### 2. Scope Boundaries

| Dimension | In Scope | Out of Scope | Decision Rationale |
|-----------|----------|--------------|-------------------|
| **Entry Points** | Any typed business entity (Unit, Offer, Contact, Process, Location, Hours) | Plain Task hydration (non-business tasks) | Business model hydration is the stated goal |
| **Hydration Direction** | Both upward (to ancestors) and downward (to descendants) | Cross-branch sibling hydration without common ancestor | Vertical navigation is the core need |
| **API Surface** | New hydration capability accessible to SDK consumers | Sync wrappers for hydration (async-only acceptable) | Multiple API calls required; async is appropriate |
| **Cache Integration** | Leverage existing caching architecture (ADR-0052) | New caching backends | Build on what exists |
| **Depth Control** | Caller-controllable hydration scope | Fully automatic "fetch everything" behavior | Caller should control API call volume |

### 3. Complexity Assessment

| Factor | Assessment | Notes |
|--------|------------|-------|
| **Scope** | Module | Touches models, persistence, possibly clients |
| **Technical Risk** | Medium | Core patterns exist, but orchestration across async hierarchy is non-trivial |
| **Integration Points** | Medium | SaveSession, TasksClient, entity models, cached references |
| **Team Familiarity** | High | Codebase well-documented with ADRs and TDDs |
| **Unknowns** | Medium | Optimal algorithm for finding root, performance characteristics, error handling strategy |

**Recommended Complexity Level**: Module

**Workflow Recommendation**: Full 4-agent workflow

**Rationale**: Touches multiple layers, requires architectural decisions, has performance and correctness implications. Worth the full workflow.

### 4. Dependencies & Blockers

| Dependency | Status | Owner | Blocking? |
|------------|--------|-------|-----------|
| `TasksClient.subtasks_async()` | **Proposed in ADR-0057** | Principal Engineer | **Likely** - needed for downward hydration |
| Existing `Task.parent: NameGid` field | Done | - | No - provides parent reference for upward traversal |
| Existing `TasksClient.get_async()` | Done | - | No - can fetch any task by GID |
| `Business._populate_holders()` | Done | - | No - downward population logic exists |
| ADR-0050 Holder Lazy Loading | Accepted | - | No |
| ADR-0052 Bidirectional Caching | Accepted | - | No |

**Blockers**:
- **ADR-0057 dependency needs assessment**: Discovery phase should determine if `subtasks_async()` is strictly required or if alternatives exist.

### 5. Success Definition (Draft)

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Can navigate to Business from any descendant | No | Yes | `contact.business` returns populated Business |
| Can access sibling entities from any entry point | No | Yes | `contact.business.units` returns populated list |
| Integration code complexity | Manual orchestration | Simple API call(s) | Lines of code needed |
| Performance acceptable | N/A | Reasonable for typical hierarchies | Benchmarks during validation |

### 6. Rough Effort Estimate

| Phase | Effort | Confidence |
|-------|--------|------------|
| Discovery / Requirements | 1 session | High |
| Architecture / Design | 1 session | Medium |
| Implementation | 2-3 sessions | Medium |
| Validation / QA | 1 session | High |
| **Total** | 5-6 sessions | Medium |

### 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Performance: excessive API calls** for deep/wide hierarchies | Medium | High | Architect to design optimal strategy; provide caller controls |
| **Cache coherency issues** when hydrating from different entry points | Low | High | Architect to specify cache invalidation behavior |
| **Circular reference issues** during bidirectional wiring | Medium | Medium | Leverage existing patterns from ADR-0052 |
| **Complex async orchestration** | Medium | Medium | Follow established SaveSession patterns |

---

## Open Questions for Discovery/Architecture Phases

### Architectural Decisions (For Architect)

| # | Question | Context |
|---|----------|---------|
| 1 | **Root Discovery Strategy**: What is the optimal algorithm to find the Business root from an arbitrary descendant? | Trade-offs: API call count vs. complexity vs. reliability. Existing infrastructure: `Task.parent: NameGid`, `get_async()`, project membership. |
| 2 | **Hydration API Design**: Where should the hydration capability live and what should its interface be? | Options include instance methods, SaveSession methods, standalone utilities. Consider discoverability, composability, error handling. |
| 3 | **Depth/Scope Control**: How should callers control how much of the hierarchy gets hydrated? | Balance between convenience (hydrate everything) and performance (minimal fetching). |
| 4 | **Cache Management**: How should hydration interact with existing cached references? | When to invalidate, when to reuse, how to handle partial hydration. |

### Implementation Dependencies (For Discovery)

| # | Question | Context |
|---|----------|---------|
| 5 | **Is ADR-0057 (subtasks_async) strictly required?** | Need to assess if downward hydration requires this, or if alternatives exist. |
| 6 | **What additional TasksClient methods might be needed?** | Discovery should audit current capabilities vs. requirements. |

### Scope Clarifications (For Requirements Analyst)

| # | Question | Context |
|---|----------|---------|
| 7 | **What hydration scenarios are highest priority?** | Webhook handlers, search result processing, deep link resolution - which are most common? |
| 8 | **Error handling expectations**: What should happen if hydration partially fails? | Keep partial results? Rollback? Raise with details? |

---

## Go/No-Go Decision

### Criteria for "Go"

- [x] Problem is validated and worth solving
- [x] Scope is bounded and achievable
- [x] No **hard** blocking dependencies (soft blocker on ADR-0057 needs assessment)
- [x] Complexity level appropriate for chosen workflow
- [x] Success metrics are measurable
- [x] Rough effort estimate acceptable
- [x] High-risk items identified for architect attention

### Recommendation

**GO** - Proceed to Prompt 0

**Rationale**:
- Problem is clearly validated with evidence from stubbed code (`_fetch_holders_async()` marked as "Phase 2")
- Scope is well-bounded to business model hydration
- Existing infrastructure provides building blocks (parent references, task fetching, population methods)
- Open questions are appropriate for Discovery and Architecture phases, not blockers for starting

**Note**: ADR-0057 (subtasks_async) should be assessed in Discovery. If determined to be a hard blocker, it can be implemented as part of Implementation phase or as a prerequisite.

---

## Next Steps

1. **Generate Prompt 0** for Orchestrator
   - Include this Prompt -1 as context
   - Define 7-session phased approach
   - Highlight architectural questions for early resolution

2. **Session 1 (Discovery)** should:
   - Audit existing infrastructure for hydration
   - Assess ADR-0057 dependency
   - Identify priority use cases
   - Surface any additional blockers

3. **Session 3 (Architecture)** should:
   - Design optimal root discovery algorithm
   - Define hydration API surface
   - Specify cache management behavior
   - Create ADRs for key decisions

---

## Appendix: Existing Infrastructure Summary

### For Upward Traversal

| Component | Location | Purpose |
|-----------|----------|---------|
| `Task.parent: NameGid` | `task.py:69` | Reference to parent task (contains GID) |
| `TasksClient.get_async()` | `tasks.py:87-116` | Fetch any task by GID |
| Cached references (`_business`, `_*_holder`) | Various entity files | Store resolved parent references |

### For Downward Population

| Component | Location | Purpose |
|-----------|----------|---------|
| `Business._populate_holders()` | `business.py:419-518` | Populate holder properties from subtask list |
| `Unit._populate_holders()` | `unit.py:263-287` | Populate nested holders from subtask list |
| `HolderMixin._populate_children()` | `base.py:49-76` | Generic child population |
| `TasksClient.subtasks_async()` | **Proposed ADR-0057** | Fetch subtasks of a task (not yet implemented) |

### For Cache Management

| Component | Location | Purpose |
|-----------|----------|---------|
| ADR-0052 pattern | Entity files | Cached upward references with invalidation |
| `_invalidate_refs()` | Entity files | Clear cached navigation on hierarchy change |

### Related Documentation

| Document | Location |
|----------|----------|
| ADR-0050: Holder Lazy Loading | `docs/decisions/ADR-0050-holder-lazy-loading-strategy.md` |
| ADR-0052: Bidirectional Caching | `docs/decisions/ADR-0052-bidirectional-reference-caching.md` |
| ADR-0057: subtasks_async | `docs/decisions/ADR-0057-subtasks-async-method.md` |
| TDD-BIZMODEL | `docs/architecture/TDD-BIZMODEL.md` |
| PRD-BIZMODEL | `docs/requirements/PRD-BIZMODEL.md` |

---

*This Prompt -1 **validated** that the initiative is ready for the full 4-agent workflow. Proceed to Prompt 0.*
