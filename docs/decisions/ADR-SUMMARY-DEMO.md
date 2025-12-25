# ADR Summary: Demo System

> Consolidated decision record for SDK demonstration infrastructure. Individual ADRs archived.

## Overview

The SDK Demonstration Suite was designed to showcase autom8_asana capabilities through interactive examples. These decisions shaped how demo scripts handle name resolution, state management, error handling, and scope boundaries. The demo system balances user experience (readable names, graceful failures) with technical pragmatism (session-scoped caching, manual recovery).

The architecture evolved from initial requirements to prioritize demonstration value over production-grade robustness. The system successfully demonstrates SDK functionality while maintaining clear boundaries between SDK code and demo-specific utilities.

## Key Decisions

### State Management: Shallow Copy with GID References

**Context**: Demo operations must be reversible to restore entities to their initial state after demonstrating each capability.

**Decision**: Implement shallow copy state capture storing scalar fields by value and relationships as GID references only. Restoration uses SDK action operations (add_tag, set_parent, move_to_section) to re-establish relationships.

**Rationale**:
- GID-based restoration is idempotent and memory-efficient
- Only need GIDs to restore relationships since actual entities still exist in Asana
- Aligns with SDK's existing action operation patterns
- Enables differential restoration by comparing initial vs. current GID sets

**Alternatives Rejected**:
- Deep copy (memory intensive, stale data risk)
- No state capture/re-fetch (cannot determine original state)
- SaveSession's ChangeTracker (different lifecycle, SDK coupling)

**Source ADRs**: ADR-0088 (ADR-DEMO-001)

---

### Name Resolution: Lazy-Loading with Session-Scoped Caching

**Context**: Demo scripts need to resolve human-readable names (tags, users, sections) to Asana GIDs without hard-coding identifiers.

**Decision**: Implement NameResolver class with lazy-loading, session-scoped caching, and case-insensitive matching. Cache populates on first use and persists for the demo run. Returns None for missing names to enable graceful degradation.

**Rationale**:
- Lazy loading minimizes unnecessary API calls and startup latency
- Session scope appropriate since resources won't change during single demo run
- Case-insensitive matching improves usability ("Optimize" == "optimize")
- Centralized resolver reusable across all demo categories
- None return enables caller-controlled handling of missing names

**Alternatives Rejected**:
- Eager loading at startup (slow startup, unused data)
- No caching/lookup each time (unacceptable performance)
- Extending CustomFieldAccessor pattern (fundamentally different resource types)
- Global persistent cache (stale data, invalidation complexity)

**Source ADRs**: ADR-0089 (ADR-DEMO-002)

---

### Error Handling: Graceful Degradation with Manual Recovery

**Context**: Demo scripts encounter API errors, rate limits, resolution failures, and partial SaveSession failures.

**Decision**: Implement error classification system with operation-level failures that log and continue rather than aborting. Pre-flight failures are fatal, rate limits trigger automatic retry, and restoration failures provide manual recovery commands. Structured DemoError captures category, operation, entity, message, and recovery hints.

**Rationale**:
- Graceful degradation maximizes demo value despite individual failures
- Manual recovery acceptable for demo context (not production)
- Rate limit handling automatic and transparent to user
- Pre-flight failures fail fast when test entities don't exist
- Structured errors enable consistent reporting and actionable guidance

**Alternatives Rejected**:
- Fail-fast on any error (too aggressive, hides working functionality)
- Silent error swallowing (hides important information)
- Automatic rollback (restoration may fail, loses progress)
- Transaction-style all-or-nothing (not feasible with Asana API)

**Source ADRs**: ADR-0090 (ADR-DEMO-003)

---

### Scope Boundary: BUG-4 GID Display Out of Scope

**Context**: Demo output displays GIDs instead of human-readable names in some contexts (cosmetic issue, not SDK bug).

**Decision**: BUG-4 is out of scope for SDK Demo Bug Fix Sprint. Issue is demo output formatting enhancement, not SDK functionality bug. Demo successfully demonstrates SDK capabilities with current GID display.

**Rationale**:
- Not an SDK bug (SDK returns correct data, demo chooses display)
- Sprint charter targets SDK bugs blocking demo execution (demo runs successfully)
- Better resource allocation to validate core SDK bug fixes (BUG-1, BUG-2, BUG-3)
- Can be addressed in future "Demo Polish" initiative
- Fix would be demo script only (~20-30 lines, zero SDK changes)

**Alternatives Rejected**:
- Include in sprint (scope creep, misaligned with charter)
- Quick fix without ADR (sets precedent for undocumented additions)

**Source ADRs**: ADR-0058

## Evolution Timeline

| Date | Decision | Impact |
|------|----------|--------|
| 2025-12-12 | State capture via shallow copy (ADR-0088) | Foundation for reversible demo operations |
| 2025-12-12 | Name resolution with lazy caching (ADR-0089) | Enabled user-friendly demo scripts |
| 2025-12-12 | Graceful error handling (ADR-0090) | Demo resilience to individual failures |
| 2025-12-12 | BUG-4 scope exclusion (ADR-0058) | Maintained sprint focus on SDK bugs |

## Cross-References

- Related PRDs: PRD-SDKDEMO
- Related TDDs: TDD-SDKDEMO
- Related Summaries: ADR-SUMMARY-SAVESESSION (restoration uses action operations)
- Discovery: DISCOVERY-SDKDEMO

## Archived Individual ADRs

| ADR | Title | Date | Key Decision |
|-----|-------|------|--------------|
| ADR-0058 | BUG-4 Demo GID Display Out of Scope | 2025-12-12 | Cosmetic output issue excluded from SDK bug sprint |
| ADR-0088 | State Capture Strategy for Demo Restoration | 2025-12-12 | Shallow copy with GID references, SDK action restoration |
| ADR-0089 | Name Resolution Approach for Demo Scripts | 2025-12-12 | Lazy-loading NameResolver with session-scoped cache |
| ADR-0090 | Error Handling Strategy for Demo Scripts | 2025-12-12 | Graceful degradation with structured errors and recovery |
