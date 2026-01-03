---
name: doc-ecosystem
description: "Ecosystem and hygiene templates for CEM sync, migration, compatibility, and code quality workflows. Use when: planning CEM migrations, validating compatibility across satellites, analyzing code smells, designing refactoring sequences, or documenting system-level changes. Triggers: gap analysis, context design, migration runbook, compatibility report, smell report, refactoring plan, CEM sync, satellite migration, code cleanup."
---

# Documentation Ecosystem & Hygiene

> **Status**: Complete (Session 2)

## Purpose

This skill provides templates for ecosystem-level documentation: CEM/satellite synchronization, migration planning, compatibility validation, and code hygiene workflows. These templates support cross-repository changes, breaking changes, and systematic code cleanup.

## Core Principles

### Ecosystem Awareness
Changes to CEM affect all satellites. Templates here ensure backward compatibility, migration paths, and clear satellite owner communication.

### Hygiene Before Features
Refactoring and cleanup are first-class work. Templates support smell detection, architectural assessment, and phased cleanup plans.

### Migration Safety
Breaking changes require runbooks, rollback procedures, and compatibility matrices. Never ship ecosystem changes without validated migration paths.

---

## Template Categories

### Ecosystem Change Templates
- [Gap Analysis](#gap-analysis-template) - Issue diagnosis for CEM/satellite problems
- [Context Design](#context-design-template) - Technical design for ecosystem changes
- [Migration Runbook](#migration-runbook-template) - Satellite owner migration guide
- [Compatibility Report](#compatibility-report-template) - Cross-satellite validation results

### Code Hygiene Templates
- [Smell Report](#smell-report-template) - Code smell catalog and cleanup priorities
- [Refactoring Plan](#refactoring-plan-template) - Phased refactoring sequence

---

# Ecosystem Change Templates

## Gap Analysis Template {#gap-analysis-template}

```markdown
# Gap Analysis: [Issue Title]

## Executive Summary
[2-3 sentences: what's broken, impact, root cause]

## Reproduction Steps
1. [Step with exact commands]
2. [Expected vs. actual behavior]

## Root Cause
**Component**: [CEM | skeleton | roster]
**File**: [path/to/file:line]
**Issue**: [technical explanation]

## Success Criteria
- [ ] [Concrete, testable criterion]
- [ ] [e.g., "cem sync completes without errors"]

## Affected Systems
- [x] CEM
- [ ] skeleton
- [ ] roster

## Recommended Complexity
**Level**: [PATCH | MODULE | SYSTEM | MIGRATION]
**Rationale**: [why this complexity]

## Test Satellites
- skeleton (always)
- [other satellites based on issue characteristics]

## Notes for Context Architect
[Anything relevant for design phase]
```

---

## Context Design Template {#context-design-template}

```markdown
# Context Design: [Solution Title]

## Overview
[2-3 sentences: what we're building, why this approach]

## Architecture

### Components Affected
- **CEM**: [what changes, why]
- **skeleton**: [what changes, why]
- **roster**: [what changes, why]

### Design Decisions
[Key architectural choices and rationale]

## Schema Definitions (if applicable)

### [Hook/Skill/Agent] Schema
```yaml
# Schema structure with comments
name: string
version: string
lifecycle:
  - event: string
    action: string
```

**Validation Rules**:
- [Rule 1]
- [Rule 2]

## Implementation Specification

### CEM Changes
**File**: `path/to/file`
**Function**: `function_name`
**Changes**: [detailed specification]

### skeleton Changes
**File**: `path/to/file`
**Changes**: [detailed specification]

### roster Changes
**Location**: `path/to/content`
**Changes**: [detailed specification]

## Backward Compatibility

**Classification**: [COMPATIBLE | BREAKING]

**Migration Path** (if breaking):
1. [Step-by-step satellite upgrade process]

**Deprecation Timeline** (if applicable):
- Version N: New pattern available, old pattern deprecated
- Version N+1: Old pattern removed

**Compatibility Matrix**:
| CEM Version | skeleton Version | Status |
|-------------|------------------|--------|
| 2.0 | 2.0 | ✓ Supported |
| 2.0 | 1.9 | ✓ Backward compatible |

## Integration Test Matrix

| Satellite | Test Case | Expected Outcome | Validates |
|-----------|-----------|------------------|-----------|
| skeleton | `cem sync` | No conflicts | Basic compatibility |
| [satellite-2] | Hook registration | Fires on event | Schema enforcement |

## Notes for Integration Engineer
[Implementation hints, gotchas, suggested approach]
```

---

## Migration Runbook Template {#migration-runbook-template}

```markdown
# Migration Runbook: [Change Title]

## Overview
**Affects**: [All satellites | Satellites with X configuration]
**Breaking**: [YES | NO]
**CEM Version**: [version]
**skeleton Version**: [version]

[2-3 sentences describing what changed and why satellite owners care]

## Before You Begin
- [ ] Backup `.claude/` directory
- [ ] Verify current CEM version: `cem --version`
- [ ] Read this runbook completely before starting

## Current Behavior
[Description with config example]

```json
// Old configuration
{
  "setting": "old-style-value"
}
```

## New Behavior
[Description with config example]

```json
// New configuration
{
  "setting": {
    "new": "nested-style-value"
  }
}
```

## Migration Steps

### 1. Update CEM
```bash
# Commands to upgrade CEM
cd /path/to/cem
git pull origin main
./install.sh
cem --version  # Should show vX.Y.Z
```

### 2. Update skeleton
```bash
cd /path/to/skeleton
cem sync  # Pulls latest skeleton changes
```

### 3. Migrate Settings
```bash
# Specific migration commands
mv .claude/settings.json .claude/settings.json.backup
# Apply transformation...
```

### 4. Verify Migration
```bash
# Verification commands
cem sync  # Should complete without errors
# Check specific functionality...
```

**Expected output**: [what success looks like]

### 5. Test Satellite Functionality
- [ ] Hooks fire correctly: `# test command`
- [ ] Skills load: `# test command`
- [ ] Agents register: `# test command`

## Rollback Procedure
If migration fails:

```bash
# Restore backup
cp .claude/settings.json.backup .claude/settings.json
cem sync --force  # Reset to pre-migration state
```

## Troubleshooting

### Issue: [Common problem]
**Symptom**: [error message or behavior]
**Solution**: [fix]

## Compatibility
| CEM | skeleton | Status |
|-----|----------|--------|
| 2.0 | 2.0 | ✓ Fully supported |
| 2.0 | 1.9 | ✓ Backward compatible |
| 1.9 | 2.0 | ✗ Unsupported—upgrade CEM first |

## Support
Questions? Issues? [contact info or issue tracker]
```

---

## Compatibility Report Template {#compatibility-report-template}

```markdown
# Compatibility Report: [Change Title]

## Test Summary
**Date**: [YYYY-MM-DD]
**Complexity**: [PATCH | MODULE | SYSTEM | MIGRATION]
**CEM Version**: [version]
**skeleton Version**: [version]
**Tester**: [agent/person]

**Status**: [✓ APPROVED | ✗ REJECTED | ⚠ APPROVED WITH CAVEATS]

## Test Matrix Results

| Satellite | Config Type | cem sync | Hook Reg | Settings Merge | Migration | Status |
|-----------|-------------|----------|----------|----------------|-----------|--------|
| skeleton | Minimal | ✓ Pass | ✓ Pass | ✓ Pass | ✓ Pass | ✓ PASS |
| satellite-a | Standard | ✓ Pass | ✓ Pass | ✗ Fail | N/A | ✗ FAIL |
| satellite-b | Complex | ✓ Pass | ⚠ Warn | ✓ Pass | ✓ Pass | ⚠ WARN |

**Legend**:
- ✓ Pass: Works as expected
- ✗ Fail: Broken, blocks release
- ⚠ Warn: Works with caveats or minor issues
- N/A: Not applicable to this satellite

## Defects

### P0 Defects (Critical)
None

### P1 Defects (High)
#### DEF-001: Settings merge fails with nested null values
**Severity**: P1
**Satellite**: satellite-a (standard config)
**Reproduction**:
1. Configure settings with `"custom": {"nested": null}`
2. Run `cem sync`
3. Error: "jq: null cannot be iterated"

**Expected**: Merge succeeds, null preserved
**Actual**: Sync fails with jq error
**Impact**: Blocks satellites using null config values

### P2 Defects (Medium)
[Details]

### P3 Defects (Low)
None

## Migration Runbook Validation

### Runbook Issues Found
- Step 3: "Apply transformation" is vague—needs exact commands
- Verification step output example doesn't match actual output
- Rollback tested successfully in all satellites

### Recommended Runbook Changes
1. Add explicit jq command for step 3
2. Update verification output example to match v2.0 format

## Regression Testing

**Pre-existing functionality tested**:
- ✓ Agent invocation from commands
- ✓ Skill loading on session start
- ✓ Settings tier precedence (global < team < user)
- ⚠ Hook lifecycle events (warning in complex config, see DEF-002)

**Regressions found**: None beyond DEF-002

## Backward Compatibility Verification

| CEM | skeleton | Tested | Result | Notes |
|-----|----------|--------|--------|-------|
| 2.0 | 2.0 | ✓ | ✓ Pass | Fully compatible |
| 2.0 | 1.9 | ✓ | ✓ Pass | Backward compatible confirmed |
| 1.9 | 2.0 | ✓ | ✗ Fail | Settings merge incompatible (expected) |

## Rollout Recommendation

**Decision**: ✗ REJECTED for release

**Rationale**:
- P1 defect (DEF-001) blocks satellites with null config values
- Affects standard configuration type (not edge case)
- Migration runbook has ambiguous step 3

**Required for approval**:
1. Fix DEF-001 (null handling in settings merge)
2. Clarify migration runbook step 3
3. Re-test satellite-a after fix

**P2/P3 defects**: Can defer to v2.0.1 patch release

## Notes for Next Iteration
- Consider adding integration test for null config values
- Warning message in DEF-002 could be suppressed for known schema versions
```

---

# Code Hygiene Templates

## Smell Report Template {#smell-report-template}

```markdown
# Code Smell Report
**Codebase**: [repository name]
**Analyzed**: [date]
**Scope**: [what was analyzed]

## Executive Summary
- Total smells identified: [count]
- Critical: [count] | High: [count] | Medium: [count] | Low: [count]
- Top 3 cleanup opportunities: [brief list]

## Critical Findings
[Highest priority items that should be addressed immediately]

## Category: Dead Code
### DC-001: [Specific smell]
- **Severity**: [level]
- **Location**: [file:line]
- **Pattern**: [what was found]
- **Evidence**: [why we know it's dead]
- **Blast radius**: [what's affected]

## Category: DRY Violations
[Same format]

## Category: Complexity Hotspots
[Same format]

## Category: Naming Inconsistencies
[Same format]

## Category: Import Hygiene
[Same format]

## Recommended Cleanup Order
1. [First target - why]
2. [Second target - why]
3. [Third target - why]

## Notes for Architect Enforcer
- Patterns that may indicate boundary violations: [list]
- Smells that cluster around specific modules: [list]
- Dependencies between smells (fixing X may fix Y): [list]
```

---

## Refactoring Plan Template {#refactoring-plan-template}

```markdown
# Refactoring Plan
**Based on**: [smell report reference]
**Prepared**: [date]
**Scope**: [what will be refactored]

## Architectural Assessment

### Boundary Health
- [Module A]: Clean boundaries, local cleanup only
- [Module B]: Leaking internals to Module C
- [Module C]: God module, needs decomposition

### Root Causes Identified
1. [Root cause 1]: Explains smells DC-001, DC-003, CX-007
2. [Root cause 2]: Explains smells DRY-002, DRY-005

## Refactoring Sequence

### Phase 1: Foundation [Low Risk]
**Goal**: Prepare for larger refactors without changing behavior

#### RF-001: [Refactoring name]
- **Smells addressed**: DC-001, NM-003
- **Category**: Local
- **Before**: [current state]
- **After**: [target state]
- **Invariants**: [what must stay true]
- **Verification**: [how to confirm success]
- **Commit scope**: [what goes in one commit]

[Rollback point: can stop here safely]

### Phase 2: Module Cleanup [Medium Risk]
**Goal**: Clean up internal module structure

#### RF-002: [Refactoring name]
[Same structure as RF-001]

### Phase 3: Boundary Repair [Higher Risk]
**Goal**: Fix cross-module issues and restore encapsulation

[Same structure]

## Risk Matrix
| Refactor | Risk | Blast Radius | Rollback Cost |
|----------|------|--------------|---------------|
| RF-001   | Low  | 2 files      | Trivial       |
| RF-002   | Med  | 1 module     | 1 commit      |
| RF-003   | High | 3 modules    | 3 commits     |

## Notes for Janitor
- Commit message conventions: [format]
- Test run requirements: [what tests after each commit]
- Files to avoid touching: [generated code, etc.]
- Order is critical for: [specific refactors with dependencies]

## Out of Scope
Findings deferred for future work:
- [Finding X]: Requires feature work, not just cleanup
- [Finding Y]: Needs architectural decision from user
```

---

## Related Skills

- **documentation** - Core artifact templates (PRD, TDD, ADR, Test Plan)
- **initiative-scoping** - Prompt -1/0 for new projects
- **10x-workflow** - Agent coordination and handoffs
- **standards** - Code conventions and repository structure

## Quality Gates Summary

**Gap Analysis**: Clear reproduction, root cause identified, success criteria testable

**Context Design**: Backward compatibility assessed, migration path documented, integration tests defined

**Migration Runbook**: Step-by-step instructions, rollback tested, compatibility matrix complete

**Compatibility Report**: All satellites tested, defects prioritized, recommendation justified

**Smell Report**: Evidence-based, severity assigned, cleanup priority established

**Refactoring Plan**: Phases sequenced by risk, invariants defined, commit scope clear
