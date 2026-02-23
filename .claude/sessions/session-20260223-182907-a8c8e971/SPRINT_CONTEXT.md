---
schema_version: "2.1"
sprint_id: sprint-20260223-test-arch-remediation
session_id: session-20260223-182907-a8c8e971
status: ACTIVE
created_at: "2026-02-23T18:29:07Z"
name: test-arch-remediation
goal: "Fix broken CI (fast-tests 25min, full-tests 45min both timing out) by restructuring CI pipeline and rationalizing 217K LOC test suite (10,682 tests, 1.87:1 test-to-source ratio)"
rite: hygiene
complexity: SYSTEM
workstreams:
  - id: WS-1
    name: CI Pipeline Architecture
    priority: 1
    description: Restructure CI pipeline to eliminate timeouts
  - id: WS-2
    name: Test Suite Rationalization
    priority: 2
    description: Rationalize test suite to improve signal-to-noise ratio
constraints:
  - coverage >= 80%
  - no sole-coverage test deletion
  - no source behavior changes
---

# Sprint: test-arch-remediation

## Goal

Fix broken CI (fast-tests 25min, full-tests 45min both timing out) by restructuring CI pipeline and rationalizing 217K LOC test suite (10,682 tests, 1.87:1 test-to-source ratio).

## Workstreams

| ID | Name | Priority |
|----|------|----------|
| WS-1 | CI Pipeline Architecture | 1 (first) |
| WS-2 | Test Suite Rationalization | 2 (after WS-1) |

## Constraints

- Coverage >= 80% must be maintained
- No sole-coverage test deletion (no test may be deleted if it is the only test covering a given code path)
- No source behavior changes (test-only remediation)

## Tasks

| ID | Phase | Description | Status | Workstream |
|----|-------|-------------|--------|------------|
| T-001 | Phase 1: Assessment | Smell report on test architecture | pending | — |
| T-002 | Phase 2: Planning | CI restructuring + test rationalization plan | pending | — |
| T-003 | Phase 3a: Execution | CI pipeline restructuring | pending | WS-1 |
| T-004 | Phase 3b: Execution | Test suite rationalization | pending | WS-2 |
| T-005 | Phase 4: Audit | Verify coverage + CI times + test count | pending | — |

## Phase Log

| Phase | Agent | Status | Notes |
|-------|-------|--------|-------|
| Phase 1: Assessment | code-smeller | pending | |
| Phase 2: Planning | architect-enforcer | pending | |
| Phase 3a: Execution (WS-1) | janitor | pending | |
| Phase 3b: Execution (WS-2) | janitor | pending | |
| Phase 4: Audit | audit-lead | pending | |

## Blockers

None.

## Notes

- WS-1 (CI Pipeline Architecture) is prioritized before WS-2 (Test Suite Rationalization)
- Fast CI budget target: sub-10min; Full CI budget target: sub-20min (from current 25min/45min timeouts)
- Test suite baseline: 10,682 tests, 217K LOC, 1.87:1 test-to-source ratio
