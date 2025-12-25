# Orchestrator Initialization: Process Pipeline Cleanup Initiative

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`documentation`** - PRD/TDD/ADR templates, workflow pipeline, quality gates
  - Activates when: Creating/reviewing PRD, TDD, ADR, or Test Plan

- **`standards`** - Tech stack decisions, code conventions, repository structure
  - Activates when: Writing code, choosing libraries, organizing files

- **`autom8-asana`** - SDK patterns, SaveSession, Business entities, detection, batch operations
  - Activates when: Working with SDK implementation, entity operations, hierarchy navigation

- **`10x-workflow`** - Agent coordination, session protocol, quality gates
  - Activates when: Planning phases, coordinating handoffs, checking quality criteria

**How Skills Work**: Skills load automatically based on your current task.

## Your Role: Orchestrator

You coordinate a 4-agent development workflow. You plan, delegate, coordinate, and verify - you do not implement directly.

## Your Specialist Agents

| Agent | Invocation | Responsibility |
|-------|------------|----------------|
| **Requirements Analyst** | `@requirements-analyst` | Requirements definition, acceptance criteria, scope boundaries |
| **Architect** | `@architect` | TDDs, ADRs, system design, trade-off analysis |
| **Principal Engineer** | `@principal-engineer` | Implementation, code quality, technical execution |
| **QA/Adversary** | `@qa-adversary` | Validation, failure mode testing, security/quality review |

---

## The Mission: Correct Process Pipeline Architecture Misunderstanding

The Process Pipeline implementation (PRD-PROCESS-PIPELINE, TDD-PROCESS-PIPELINE, ADRs 0096-0100) was based on a fundamental architectural misunderstanding. We built a "dual membership" model assuming separate "pipeline projects" exist, when in reality the canonical entity project IS the pipeline project.

**This initiative will:**
1. Revert/remove incorrectly implemented code
2. Keep correctly implemented components (ProcessType, ProcessSection, from_name)
3. Document the correction via ADR
4. Update tests to reflect correct architecture

### Why This Initiative?

- **Correctness**: Current implementation is based on wrong mental model
- **Simplification**: Removing unnecessary complexity (no dual membership needed)
- **Clarity**: Correct architecture is simpler to understand and maintain
- **Future-proofing**: Correct foundation for Process entity enhancements

### Current State (INCORRECT Implementation)

**What Was Built**:
- ProcessProjectRegistry singleton mapping ProcessType to "pipeline project" GIDs
- Process.add_to_pipeline() method to add Process to separate pipeline project
- Process.pipeline_state using ProcessProjectRegistry to find "pipeline project"
- Process.process_type detection via ProcessProjectRegistry reverse lookup
- BusinessSeeder adds Process to "pipeline project" via add_to_project()
- ADR-0098 documenting "dual membership" model

**What's Wrong**:
- There ARE NO separate "pipeline projects"
- The canonical entity project (e.g., "Sales Processes") IS the pipeline
- Sections within canonical project ARE the pipeline states
- No dual membership to separate projects is needed

### Target Architecture (CORRECT)

```
Process Entity Architecture (CORRECT)
=====================================

Business (root)
  +-- UnitHolder
        +-- Unit
              +-- ProcessHolder
                    +-- Process  ---------------------+
                                                       |
                                                       v
                              Process's Canonical Project (e.g., "Sales Processes")
                              +-- Section: OPPORTUNITY
                              +-- Section: DELAYED
                              +-- Section: ACTIVE
                              +-- Section: SCHEDULED
                              +-- Section: CONVERTED
                              +-- Section: DID NOT CONVERT
                              +-- Section: OTHER

Key Relationships:
- Process is subtask of ProcessHolder (hierarchy)
- Process is member of canonical project (which HAS pipeline sections)
- NO separate "pipeline project" to add to
- pipeline_state = section within canonical project
- move_to_state() = move within canonical project sections
```

### Key Constraints

- **Preserve ProcessType enum** - The 7 enum values are correct
- **Preserve ProcessSection enum** - The 7 enum values and from_name() are correct
- **Preserve move_to_state() concept** - Moving between sections is valid
- **Do not break existing tests** - Update tests to reflect correct architecture
- **Backward compatibility** - ProcessType.GENERIC fallback remains valid
- **Clean removal** - Remove incorrect code completely, don't leave dead code

### Components to Modify

| Component | File | Action |
|-----------|------|--------|
| ProcessProjectRegistry | `src/autom8_asana/models/business/process_registry.py` | REMOVE or REPURPOSE |
| Process.add_to_pipeline() | `src/autom8_asana/models/business/process.py` | REMOVE |
| Process.pipeline_state | `src/autom8_asana/models/business/process.py` | MODIFY - use canonical project |
| Process.process_type | `src/autom8_asana/models/business/process.py` | MODIFY - detection strategy |
| BusinessSeeder | `src/autom8_asana/models/business/seeder.py` | MODIFY - remove pipeline logic |
| Detection integration | `src/autom8_asana/models/business/detection.py` | REVIEW - remove ProcessProjectRegistry |
| ADR-0098 | `docs/decisions/ADR-0098-dual-membership-model.md` | SUPERSEDE |
| Test files | `tests/unit/models/business/test_process*.py` | UPDATE |

### Success Criteria

1. ProcessProjectRegistry removed (or clearly repurposed)
2. Process.add_to_pipeline() method removed
3. BusinessSeeder does not call add_to_project() for "pipeline"
4. Process.pipeline_state works with canonical project sections
5. Process.process_type detection uses correct approach
6. ADR-0101 created documenting correction
7. All tests pass
8. No dead code or orphaned imports

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Remove ProcessProjectRegistry (or repurpose) | Must |
| Remove Process.add_to_pipeline() method | Must |
| Modify BusinessSeeder to remove pipeline addition | Must |
| Update Process.pipeline_state to use canonical project | Must |
| Review Process.process_type detection | Must |
| Create ADR-0101 superseding ADR-0098 | Must |
| Update/remove related tests | Must |
| Clean up imports and dead code | Must |
| Document correct architecture | Should |
| Update environment variable documentation | Should |

---

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | Impact analysis - enumerate all affected files and code paths |
| **2: Architecture** | Architect | ADR-0101 (Correction), updated architecture documentation |
| **3: Implementation P1** | Principal Engineer | Remove ProcessProjectRegistry, remove add_to_pipeline() |
| **4: Implementation P2** | Principal Engineer | Modify BusinessSeeder, update pipeline_state |
| **5: Implementation P3** | Principal Engineer | Clean up imports, update process_type detection |
| **6: Testing** | Principal Engineer | Update/fix all affected tests |
| **7: Validation** | QA/Adversary | Validation report, verify no regression |

---

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rule**: Never execute without explicit confirmation.

---

## Discovery Phase: What Must Be Analyzed

Before implementation begins, the **Requirements Analyst** must analyze:

### Codebase Analysis

| File | Questions to Answer |
|------|---------------------|
| `src/autom8_asana/models/business/process.py` | What code uses ProcessProjectRegistry? What imports need updating? |
| `src/autom8_asana/models/business/process_registry.py` | What depends on this module? Can it be deleted entirely? |
| `src/autom8_asana/models/business/seeder.py` | What pipeline-related code needs removal? |
| `src/autom8_asana/models/business/detection.py` | Does detection use ProcessProjectRegistry? |
| `src/autom8_asana/models/business/__init__.py` | What exports need updating? |

### Test Analysis

| Test File | Questions |
|-----------|-----------|
| `tests/unit/models/business/test_process*.py` | What tests exist for add_to_pipeline, ProcessProjectRegistry? |
| `tests/unit/models/business/test_seeder*.py` | What tests need updating for seeder? |
| `tests/integration/` | Any integration tests affected? |

### Documentation Analysis

| Document | Questions |
|----------|-----------|
| `docs/decisions/ADR-0098*.md` | How should this be superseded? |
| `docs/decisions/ADR-0099*.md` | Does BusinessSeeder ADR need updates? |
| `docs/design/TDD-PROCESS-PIPELINE.md` | What sections are now incorrect? |

---

## Open Questions Requiring Resolution

Before Session 2 (Architecture) begins:

### Detection Strategy Questions

1. **How should Process.process_type be detected?** The current approach uses ProcessProjectRegistry reverse lookup. What's the correct approach?
2. **Should Process have PRIMARY_PROJECT_GID?** Currently set to None. Should ProcessType-specific subclasses each have their own?
3. **Can we reuse ProjectTypeRegistry?** The existing registry for entity type detection - can it handle ProcessType?

### Architecture Questions

4. **Should ProcessProjectRegistry be completely deleted or repurposed?** Is there any valid use case for a ProcessType-to-project mapping?
5. **What environment variables should remain?** AUTOM8_PROCESS_PROJECT_* pattern may be invalid.
6. **Section GID configuration**: How should section GIDs be configured if not via ProcessProjectRegistry?

### Scope Questions

7. **Should we update TDD-PROCESS-PIPELINE?** Or just archive it and create new documentation?
8. **What happens to VALIDATION-PROCESS-PIPELINE.md?** The validation report for incorrect implementation.

---

## Files to Modify/Remove

### Remove Entirely

```
src/autom8_asana/models/business/process_registry.py  # ProcessProjectRegistry
```

### Modify

```
src/autom8_asana/models/business/process.py           # Remove add_to_pipeline, update pipeline_state
src/autom8_asana/models/business/seeder.py            # Remove pipeline addition logic
src/autom8_asana/models/business/__init__.py          # Update exports
src/autom8_asana/models/business/detection.py         # Remove ProcessProjectRegistry usage (if any)
```

### Create

```
docs/decisions/ADR-0101-process-pipeline-correction.md  # Supersedes ADR-0098
```

### Archive/Supersede

```
docs/decisions/ADR-0098-dual-membership-model.md      # Add "Superseded by ADR-0101" header
```

---

## Your First Task

Confirm understanding by:

1. Summarizing the cleanup goal in 2-3 sentences
2. Listing the 7 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step
4. Confirming which files must be analyzed before cleanup begins
5. Listing which open questions you need answered before Session 2

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

## Session Trigger Prompts

### Session 1: Discovery

```markdown
Begin Session 1: Process Pipeline Cleanup Discovery

Work with the @requirements-analyst agent to analyze the codebase and document all affected files.

**Goals:**
1. Enumerate all usages of ProcessProjectRegistry
2. Document all code paths using add_to_pipeline()
3. Identify all imports that will break
4. List all tests that need updating
5. Confirm detection.py usage of ProcessProjectRegistry
6. Document BusinessSeeder pipeline logic
7. Create comprehensive impact assessment

**Files to Analyze:**
- `src/autom8_asana/models/business/process.py` - Core Process class
- `src/autom8_asana/models/business/process_registry.py` - Registry to remove
- `src/autom8_asana/models/business/seeder.py` - BusinessSeeder
- `src/autom8_asana/models/business/detection.py` - Detection system
- `src/autom8_asana/models/business/__init__.py` - Exports
- `tests/unit/models/business/test_process*.py` - Tests

**Deliverable:**
Impact analysis document with:
- Complete list of affected files
- Code snippets to remove
- Code snippets to modify
- Test impact assessment
- Import dependency graph
- Risk assessment

Create the analysis plan first. I'll review before you execute.
```

### Session 2: Architecture

```markdown
Begin Session 2: Process Pipeline Correction Architecture

Work with the @architect agent to create ADR-0101 and document correct architecture.

**Prerequisites:**
- Session 1 discovery complete

**Goals:**
1. Create ADR-0101 superseding ADR-0098
2. Document correct Process-to-canonical-project relationship
3. Define correct pipeline_state implementation
4. Define correct process_type detection approach
5. Update architecture diagrams
6. Mark TDD-PROCESS-PIPELINE sections as superseded

**Deliverables:**
- ADR-0101: Process Pipeline Architecture Correction
- Architecture diagram showing correct relationship
- Updated documentation recommendations

Create the plan first. I'll review before you execute.
```

### Session 3: Implementation Phase 1 - Core Removal

```markdown
Begin Session 3: Implementation Phase 1 - Core Removal

Work with the @principal-engineer agent to remove incorrect code.

**Prerequisites:**
- Discovery complete
- ADR-0101 approved

**Phase 1 Scope:**
1. Remove Process.add_to_pipeline() method
2. Remove ProcessProjectRegistry imports from process.py
3. Update process.py module docstring
4. Update __init__.py exports
5. Remove process_registry.py (or mark deprecated)
6. Remove ProcessProjectRegistry from __all__

**Hard Constraints:**
- Do not modify pipeline_state yet (Phase 2)
- Do not modify process_type detection yet (Phase 2)
- Ensure clean removal with no dangling references

Create the plan first. I'll review before you execute.
```

### Session 4: Implementation Phase 2 - Seeder and State

```markdown
Begin Session 4: Implementation Phase 2 - Seeder and State

Work with the @principal-engineer agent to update BusinessSeeder and pipeline_state.

**Prerequisites:**
- Phase 1 complete

**Phase 2 Scope:**
1. Remove pipeline addition logic from BusinessSeeder.seed_async()
2. Remove added_to_pipeline from SeederResult
3. Remove ProcessProjectRegistry imports from seeder.py
4. Update seeder module docstring
5. Simplify pipeline_state to use canonical project
6. Update process_type detection (if needed)

**Integration Points:**
- Ensure BusinessSeeder still creates entities correctly
- Ensure pipeline_state returns correct section
- Ensure existing functionality preserved

Create the plan first. I'll review before you execute.
```

### Session 5: Implementation Phase 3 - Cleanup

```markdown
Begin Session 5: Implementation Phase 3 - Cleanup

Work with the @principal-engineer agent to clean up and finalize.

**Prerequisites:**
- Phase 2 complete

**Phase 3 Scope:**
1. Remove/update detection.py ProcessProjectRegistry usage
2. Clean up all orphaned imports
3. Remove dead code
4. Update type hints
5. Run mypy and fix any type errors
6. Run ruff and fix linting issues
7. Verify no circular import issues

Create the plan first. I'll review before you execute.
```

### Session 6: Testing

```markdown
Begin Session 6: Test Updates

Work with the @principal-engineer agent to update tests.

**Prerequisites:**
- All implementation phases complete

**Scope:**
1. Update/remove tests for add_to_pipeline()
2. Update/remove tests for ProcessProjectRegistry
3. Update BusinessSeeder tests
4. Update pipeline_state tests
5. Ensure all tests pass
6. Verify test coverage maintained

Create the plan first. I'll review before you execute.
```

### Session 7: Validation

```markdown
Begin Session 7: Cleanup Validation

Work with the @qa-adversary agent to validate the cleanup.

**Prerequisites:**
- All implementation and testing complete

**Goals:**

**Part 1: Code Verification**
- No references to ProcessProjectRegistry remain
- No add_to_pipeline method exists
- BusinessSeeder works correctly without pipeline addition
- pipeline_state returns correct values

**Part 2: Test Verification**
- All tests pass
- No test failures related to removed code
- Coverage maintained or improved

**Part 3: Documentation Verification**
- ADR-0101 correctly supersedes ADR-0098
- INDEX.md updated
- No documentation references incorrect architecture

**Part 4: Integration Verification**
- SDK imports work correctly
- No circular import issues
- Type checking passes

Create the plan first. I'll review before you execute.
```

---

## Context Gathering Checklist

Before starting, gather:

**Source Files:**
- [x] `src/autom8_asana/models/business/process.py` - Process class, add_to_pipeline, pipeline_state
- [x] `src/autom8_asana/models/business/process_registry.py` - ProcessProjectRegistry to remove
- [x] `src/autom8_asana/models/business/seeder.py` - BusinessSeeder with pipeline logic
- [ ] `src/autom8_asana/models/business/detection.py` - Detection system
- [ ] `src/autom8_asana/models/business/__init__.py` - Module exports

**Documentation:**
- [x] `docs/requirements/PRD-PROCESS-PIPELINE.md` - Original PRD
- [x] `docs/requirements/PRD-PROCESS-PIPELINE-AMENDMENT.md` - This amendment
- [x] `docs/design/TDD-PROCESS-PIPELINE.md` - Original TDD
- [x] `docs/decisions/ADR-0098-dual-membership-model.md` - ADR to supersede

**Tests:**
- [ ] `tests/unit/models/business/test_process*.py` - Process tests
- [ ] `tests/unit/models/business/test_seeder*.py` - Seeder tests (if exist)

**Related Files:**
- [x] `docs/INDEX.md` - Documentation index to update
