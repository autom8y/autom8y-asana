# PRD Amendment: Process Pipeline Architectural Correction

> **IMPLEMENTATION NOTE (2025-12-19)**
>
> This PRD Amendment describes the architectural correction that led to the removal of `ProcessProjectRegistry`. The correction was implemented via [ADR-0101](../decisions/ADR-0101-process-pipeline-correction.md) and [TDD-TECH-DEBT-REMEDIATION](../design/TDD-TECH-DEBT-REMEDIATION.md). Pipeline project detection now uses `WorkspaceProjectRegistry` for dynamic discovery.

## Metadata
- **PRD ID**: PRD-PROCESS-PIPELINE-AMENDMENT
- **Status**: Implemented
- **Author**: Requirements Analyst
- **Created**: 2025-12-17
- **Last Updated**: 2025-12-19
- **Amends**: [PRD-PROCESS-PIPELINE](PRD-PROCESS-PIPELINE.md)
- **Implemented By**: [ADR-0101](../decisions/ADR-0101-process-pipeline-correction.md), [TDD-TECH-DEBT-REMEDIATION](../design/TDD-TECH-DEBT-REMEDIATION.md)
- **Stakeholders**: autom8 platform team
- **Related PRDs**: [PRD-0010 Business Model Layer](PRD-0010-business-model-layer.md), [PRD-0013 Hierarchy Hydration](PRD-0013-hierarchy-hydration.md)

---

## Problem Statement

**What went wrong?**

The PRD-PROCESS-PIPELINE and its subsequent implementation (TDD-PROCESS-PIPELINE, ADRs 0096-0100) were based on a fundamental architectural misunderstanding about how Process entities relate to pipeline projects in Asana.

**The Incorrect Model (What We Built)**:

We assumed that pipeline projects are **separate projects** from the canonical entity projects. This led to a "dual membership" model where:

1. A Process exists in the hierarchy (ProcessHolder subtask relationship)
2. A Process is ALSO added to a separate "pipeline project" (e.g., "Sales Pipeline Project")
3. ProcessProjectRegistry maps ProcessType to these separate pipeline project GIDs
4. `add_to_pipeline()` method adds Process to this separate project
5. BusinessSeeder adds Process to this separate pipeline project at creation

**The Correct Model (What Should Have Been Built)**:

The canonical project for each process type **IS** the pipeline. There are NOT separate pipeline projects:

1. Each ProcessType has ONE canonical project (e.g., "Sales Processes" project)
2. This canonical project contains sections that represent pipeline states (OPPORTUNITY, ACTIVE, CONVERTED, etc.)
3. A Process is in its ProcessHolder (hierarchy via subtask) AND its canonical project (entity project = pipeline)
4. Sections within the canonical project = pipeline states
5. There is NO second "pipeline project" to add to

**Impact of the Misunderstanding**:

| Area | Impact |
|------|--------|
| ProcessProjectRegistry | Wrong concept - maps to non-existent separate projects |
| Process.add_to_pipeline() | Wrong concept - no separate pipeline to add to |
| BusinessSeeder | Wrong - adds to non-existent separate pipeline project |
| Detection integration | Wrong - checks for separate pipeline project membership |
| ADR-0098 (Dual Membership) | Based on incorrect premise |
| Environment variables | AUTOM8_PROCESS_PROJECT_* pattern expects wrong project GIDs |

---

## Correct Architecture

### Canonical Model

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
- Process is subtask of ProcessHolder (hierarchy relationship)
- Process is member of its canonical project (entity project = pipeline project)
- Sections within canonical project represent pipeline states
- NO separate "pipeline project" exists
```

### Pipeline State Mechanism

**Correct Understanding**:
- `pipeline_state` = which section of the canonical project the Process is in
- `move_to_state()` = move within canonical project sections (this is correct in concept)
- Process.PRIMARY_PROJECT_GID should point to the canonical project (which has pipeline sections)
- Pipeline view is **per-account**, accessed via ProcessHolder traversal, NOT via querying a cross-account pipeline project

### ProcessType Detection

**Correct Approach**:
- ProcessType should be determined by which canonical project the Process belongs to
- Each ProcessType (SALES, ONBOARDING, etc.) corresponds to a different canonical project
- The canonical project GID is what Process.PRIMARY_PROJECT_GID should reference for that type
- No separate registry of "pipeline projects" is needed - the entity project IS the pipeline

---

## What Should Be Kept vs. Reverted

### KEEP (Correct Concepts)

| Component | Status | Rationale |
|-----------|--------|-----------|
| ProcessType enum (7 values) | KEEP | Correct - represents process types (SALES, ONBOARDING, etc.) |
| ProcessSection enum (7 values) | KEEP | Correct - represents pipeline states within canonical project |
| ProcessSection.from_name() | KEEP | Correct - maps section names to enum values |
| Process.pipeline_state concept | KEEP (MODIFY) | Correct concept - state = section within canonical project |
| Process.move_to_state() concept | KEEP (MODIFY) | Correct - moves between sections in canonical project |
| ProcessType.GENERIC fallback | KEEP | Correct - backward compatibility for processes not in typed projects |

### REVERT/REMOVE (Incorrect Concepts)

| Component | Action | Rationale |
|-----------|--------|-----------|
| ProcessProjectRegistry | REMOVE or REPURPOSE | Wrong concept - no separate pipeline projects |
| Process.add_to_pipeline() | REMOVE | Wrong concept - no separate pipeline to add to |
| BusinessSeeder pipeline logic | REMOVE | Wrong - don't add to separate pipeline project |
| ADR-0098 (Dual Membership) | SUPERSEDE | Based on incorrect premise |
| ADR-0099 BusinessSeeder factory | MODIFY | Remove pipeline addition logic |
| Detection ProcessProjectRegistry check | REMOVE | Wrong concept |
| AUTOM8_PROCESS_PROJECT_* env vars | REMOVE or REPURPOSE | Wrong pattern |
| AUTOM8_SECTION_*_* env vars | EVALUATE | May still be useful for section GID lookup |

### MODIFY (Adjust Implementation)

| Component | Modification Needed |
|-----------|---------------------|
| Process.pipeline_state | Should read section from canonical project membership, not "pipeline project" |
| Process.process_type | Should be detected from which canonical project the Process belongs to |
| Process.PRIMARY_PROJECT_GID | Each ProcessType subclass should have its own PRIMARY_PROJECT_GID |
| BusinessSeeder | Remove add_to_project() call for pipeline; Process is already in canonical project |

---

## Revised Requirements

### FR-TYPE: ProcessType Enum (UNCHANGED)

All requirements remain valid. ProcessType represents the type of process workflow.

### FR-SECTION: ProcessSection Enum (UNCHANGED)

All requirements remain valid. ProcessSection represents states within the canonical project sections.

### FR-REG: ProcessProjectRegistry (DEPRECATED)

| ID | Original Requirement | New Status |
|----|---------------------|------------|
| FR-REG-001 | Singleton accessed via get_process_project_registry() | DEPRECATED - Remove |
| FR-REG-002 | Maps ProcessType to project GID | DEPRECATED - Use PRIMARY_PROJECT_GID instead |
| FR-REG-003 | Environment variable override pattern | DEPRECATED - Use standard entity env vars |
| FR-REG-004 | Reverse lookup (GID -> ProcessType) | DEPRECATED - Use ProjectTypeRegistry |
| FR-REG-005 | Lazy initialization | DEPRECATED - Remove |

### FR-STATE: Pipeline State Access (MODIFIED)

| ID | Original Requirement | Revised Requirement |
|----|---------------------|---------------------|
| FR-STATE-001 | pipeline_state returns ProcessSection or None | **KEEP** - Unchanged |
| FR-STATE-002 | Extracts state from cached memberships without API call | **KEEP** - Unchanged |
| FR-STATE-003 | Uses ProcessProjectRegistry to identify correct project | **REVISE**: Use canonical project membership (PRIMARY_PROJECT_GID) |
| FR-STATE-004 | Returns None if not in any pipeline project | **REVISE**: Returns None if not in canonical project |
| FR-STATE-005 | Returns None with warning if in multiple pipeline projects | **REMOVE** - Not applicable; entity is in one canonical project |
| FR-STATE-006 | process_type property returns detected ProcessType | **REVISE**: Detect from canonical project membership |
| FR-STATE-007 | Returns GENERIC if not in registered pipeline | **REVISE**: Returns based on canonical project match |
| FR-STATE-008 | Returns GENERIC with warning if in multiple pipelines | **REMOVE** - Not applicable |

### FR-DUAL: Dual Membership Support (DEPRECATED)

| ID | Original Requirement | New Status |
|----|---------------------|------------|
| FR-DUAL-001 | add_to_pipeline() queues add_to_project | DEPRECATED - Remove method |
| FR-DUAL-002 | add_to_pipeline looks up project GID | DEPRECATED - Remove |
| FR-DUAL-003 | add_to_pipeline accepts target section | DEPRECATED - Remove |
| FR-DUAL-004 | add_to_pipeline raises ValueError if not registered | DEPRECATED - Remove |
| FR-DUAL-005 | Detection recognizes dual-membership | DEPRECATED - No dual membership |

### FR-TRANS: State Transition Helpers (MODIFIED)

| ID | Original Requirement | Revised Requirement |
|----|---------------------|---------------------|
| FR-TRANS-001 | move_to_state() queues move_to_section | **KEEP** - Unchanged |
| FR-TRANS-002 | Looks up section GID in current pipeline project | **REVISE**: Looks up section GID in canonical project |
| FR-TRANS-003 | Raises ValueError if not in pipeline project | **REVISE**: Raises if not in canonical project |
| FR-TRANS-004 | Raises ValueError if section not found | **KEEP** - Unchanged |
| FR-TRANS-005 | Section GID lookup uses cached data | **KEEP** - Unchanged |

### FR-SEED: BusinessSeeder Factory (MODIFIED)

| ID | Original Requirement | Revised Requirement |
|----|---------------------|---------------------|
| FR-SEED-001 through FR-SEED-005 | Create Business, Unit, ProcessHolder, Process | **KEEP** - Unchanged |
| FR-SEED-006 | Adds Process to specified pipeline project | **REMOVE** - No separate pipeline project |
| FR-SEED-007 through FR-SEED-011 | Return SeederResult, use SaveSession, async, Contact, idempotent | **KEEP** - Unchanged (remove added_to_pipeline flag) |

---

## Cleanup Initiative

A cleanup initiative is required to:

1. Remove ProcessProjectRegistry and related code
2. Remove Process.add_to_pipeline() method
3. Modify BusinessSeeder to remove pipeline addition logic
4. Modify Process.pipeline_state to use canonical project
5. Modify Process.process_type detection
6. Supersede ADR-0098 with correction ADR
7. Update environment variable documentation
8. Update tests

See: [PROMPT-0-PROCESS-CLEANUP](../initiatives/PROMPT-0-PROCESS-CLEANUP.md)

---

## Assumptions (Revised)

| Assumption | Basis |
|------------|-------|
| Each ProcessType has one canonical project | Stakeholder clarification |
| Canonical project contains standard pipeline sections | Verified in Asana workspace |
| Process entities are added to canonical project at creation | Standard entity creation pattern |
| Section names are consistent within a canonical project | Design constraint |
| Process.PRIMARY_PROJECT_GID can vary by ProcessType | Future subclass pattern |

---

## Dependencies

| Dependency | Owner | Status |
|------------|-------|--------|
| Cleanup initiative execution | Principal Engineer | Pending |
| ADR supersession | Architect | Pending |
| Test updates | QA | Pending |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| How should Process.PRIMARY_PROJECT_GID work for different ProcessTypes? | Architect | TBD | May need ProcessType-specific subclasses with different PRIMARY_PROJECT_GID |
| Should ProcessProjectRegistry be completely removed or repurposed? | Architect | TBD | Likely remove; use existing ProjectTypeRegistry |
| How is process_type detected if not via separate registry? | Architect | TBD | Via canonical project membership in ProjectTypeRegistry |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-17 | Requirements Analyst | Initial amendment documenting architectural correction |
