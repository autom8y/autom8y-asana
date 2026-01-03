---
sprint_id: sprint-legacy-removal-phase4
session_id: session-20260102-195244-cd094308
initiative: "Unified Cache Migration - Legacy Path Elimination"
goal: "Remove legacy cache paths and make unified cache mandatory"
status: active
started_at: "2026-01-02T22:01:29Z"
risk_level: HIGH
depends_on: []
---

# Sprint: Phase 4 - Legacy Removal

## Overview

This sprint removes legacy cache paths identified in the smell report, making the unified cache architecture mandatory. This is HIGH RISK work involving breaking changes.

## Completed Phases

### Phase 1: Factory/DI Setup (Complete)
- 3 commits
- Established dependency injection foundation

### Phase 2: Client Wiring (Complete)
- 4 commits
- Connected clients to unified cache

### Phase 3: Cascade Integration (Complete)
- 1 commit
- Integrated cascade resolution with unified cache

## Phase 4 Tasks

### RF-009: Remove StalenessCheckCoordinator from clients
- **Status**: pending
- **Risk**: HIGH - Changes core client behavior
- **Scope**: Remove dual staleness checking architecture
- **Validation**: All tests pass, no regression in cache behavior

### RF-010: Remove legacy _parent_cache from CascadingFieldResolver
- **Status**: pending
- **Risk**: MEDIUM - Affects cascade resolution
- **Scope**: Eliminate fallback cache parameter
- **Validation**: Cascade resolution tests pass

### RF-011: Remove optional parameter fallbacks
- **Status**: pending
- **Risk**: LOW - Cleanup only
- **Scope**: Remove optional cache parameters from method signatures
- **Validation**: Type checking passes, no runtime errors

### Audit: Final verification
- **Status**: pending
- **Risk**: N/A
- **Scope**: Verify all legacy paths eliminated
- **Validation**: Full test suite passes, audit-lead signoff

## Risk Mitigation

1. **Breaking changes**: Each task is atomic and independently testable
2. **Rollback plan**: Git history allows clean revert of each commit
3. **Test coverage**: Full test suite must pass for each change
4. **Audit verification**: audit-lead must verify behavior preservation

## Dependencies

None - Phases 1-3 complete and committed.

## Success Criteria

- All RF-009, RF-010, RF-011 tasks complete
- Full test suite passing (unit + integration)
- No legacy cache paths remaining in codebase
- audit-lead signoff on behavior preservation
- Clean git history with atomic commits
