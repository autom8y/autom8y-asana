# ADR-0101: Process Pipeline Architecture Correction

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-17
- **Deciders**: Architect, Principal Engineer
- **Supersedes**: [ADR-0098](ADR-0098-dual-membership-model.md) (Dual Membership Model)
- **Related**: [ADR-0096](ADR-0096-processtype-expansion.md), [ADR-0097](ADR-0097-processsection-state-machine.md), [ADR-0099](ADR-0099-businessseeder-factory.md), [ADR-0100](ADR-0100-state-transition-composition.md), [IMPACT-PROCESS-CLEANUP](../analysis/IMPACT-PROCESS-CLEANUP.md)

---

## Context

During implementation of the Process Pipeline feature (ADR-0098), we built a "dual membership" architecture assuming:

1. Processes exist in the hierarchy (Business > Unit > ProcessHolder > Process)
2. Processes must be **added** to separate "pipeline projects" (e.g., "Sales Pipeline")

**This assumption was incorrect.**

The canonical entity project (e.g., "Sales") **IS** the pipeline. There are no separate pipeline projects. Process projects are named "Sales", "Onboarding", "Implementation" (not "Sales Processes" or "Sales Pipeline"). When a Process is created, it becomes a member of its canonical project through the normal creation flow.

**Evidence from domain analysis:**
- Asana project named "Sales" contains Processes in sections: Opportunity, Active, Scheduled, etc.
- These sections ARE the pipeline states
- No separate "Sales Pipeline" project exists
- The project IS both the entity registry AND the pipeline view

**Impact of the incorrect implementation:**
- `ProcessProjectRegistry` singleton: Wrong concept (maps ProcessType to non-existent "pipeline projects")
- `add_to_pipeline()` method: Adds to non-existent projects
- `process_type` property: Uses registry lookup for something derivable from canonical project
- `pipeline_state` property: Correct concept, wrong implementation (uses registry)
- `move_to_state()` method: Correct concept, wrong implementation (uses registry for section GIDs)
- BusinessSeeder: Adds unnecessary pipeline project logic

---

## Decision

**Remove ProcessProjectRegistry entirely. The canonical project IS the pipeline.**

### 1. No Separate Pipeline Projects

The fundamental correction:

```
INCORRECT (ADR-0098):
  Process
    ├── Hierarchy: subtask of ProcessHolder
    └── Pipeline: ADDED to separate "Sales Pipeline" project

CORRECT:
  Process
    ├── Hierarchy: subtask of ProcessHolder
    └── Pipeline: MEMBER of canonical project (e.g., "Sales")
                  The canonical project HAS sections = pipeline states
```

Process entities receive their project membership through:
1. Creation in the canonical project (via BusinessSeeder or API)
2. Inheritance from parent Unit context (Unit.PRIMARY_PROJECT_GID determines which canonical project)

### 2. ProcessProjectRegistry Removal

**Remove entirely:**
- Delete `src/autom8_asana/models/business/process_registry.py`
- Delete `tests/unit/models/business/test_process_registry.py`
- Remove exports from `__init__.py`
- No `AUTOM8_PROCESS_PROJECT_*` environment variables needed

**Rationale:** The registry mapped ProcessType to "pipeline project GIDs" that don't exist. Detection of Process entities uses ProjectTypeRegistry only (Tier 1 detection via project membership).

### 3. pipeline_state Implementation

**Keep the concept. Simplify the implementation.**

Extract from membership in the canonical project:

```python
@property
def pipeline_state(self) -> ProcessSection | None:
    """Get current pipeline state from canonical project section membership."""
    if not self.memberships:
        return None

    # Find membership in canonical project (primary project for this entity)
    for membership in self.memberships:
        project_gid = membership.get("project", {}).get("gid")
        # The canonical project contains sections = pipeline states
        section_name = membership.get("section", {}).get("name")
        if section_name:
            return ProcessSection.from_name(section_name)

    return None
```

**Key insight:** Every Process is a member of exactly one canonical project (e.g., "Sales"). That project's sections ARE the pipeline states. No registry lookup needed - just read the section from memberships.

**Decision on multi-project handling:** If a Process appears in multiple projects, use the first membership with a section. Log a warning for debugging. This is simpler than the error-condition approach in ADR-0098.

### 4. process_type Implementation

**Recommendation: Derive from canonical project name.**

**Options evaluated:**

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Project name -> ProcessType | Simple, no config, matches domain | Fragile if projects renamed |
| B | ProjectTypeRegistry metadata | Type-safe, explicit | Registry expansion complexity |
| C | Derive from parent Unit | Consistent with hierarchy | Requires Unit context available |
| D | Remove ProcessType entirely | Simplest | Loses type differentiation |

**Chosen: Option A with fallback.**

```python
@property
def process_type(self) -> ProcessType:
    """Derive process type from canonical project name."""
    if not self.memberships:
        return ProcessType.GENERIC

    for membership in self.memberships:
        project_name = membership.get("project", {}).get("name", "").lower()

        # Direct name matching
        for pt in ProcessType:
            if pt != ProcessType.GENERIC and pt.value in project_name:
                return pt

    return ProcessType.GENERIC
```

**Rationale:**
- Projects are named "Sales", "Onboarding", etc. - direct match to ProcessType enum values
- GENERIC fallback preserves backward compatibility
- No configuration required
- If stakeholders rename projects (rare), enum values still work for common variations

### 5. move_to_state Implementation

**Recommendation: Option D - Remove wrapper, use SaveSession.move_to_section() directly.**

**Options evaluated:**

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Section GID parameter | Caller responsibility | Not ergonomic |
| B | Fetch sections on demand | Always correct | API latency, async complexity |
| C | Section GID in config | Fast lookup | Configuration burden |
| D | Remove wrapper | Simplest | Caller needs section GID |

**Chosen: Option D.**

**Remove `move_to_state()` method entirely.** Consumers use SaveSession directly:

```python
# Consumer code
section_gid = lookup_section_gid(project_gid, "Converted")  # Consumer's responsibility
session.move_to_section(process, section_gid)
```

**Rationale:**
- The wrapper added complexity for minimal benefit
- Section GIDs vary between Asana workspaces - not SDK's concern
- SaveSession.move_to_section() already exists and works
- Consumer applications (autom8 platform) can maintain section GID mappings appropriate to their deployment
- ProcessSection enum remains useful for parsing (from_name) but not for GID lookup

**Alternative (if move_to_state() is desired):** Require section GID parameter:

```python
def move_to_state(
    self,
    session: SaveSession,
    section_gid: str,  # Caller provides
) -> SaveSession:
    session.move_to_section(self, section_gid)
    return session
```

This is thin enough that the method adds no value - just use move_to_section().

### 6. add_to_pipeline() Removal

**Remove entirely.** The concept is wrong.

Process entities get project membership through:
1. Being created as subtasks of ProcessHolder (which is in a project)
2. SaveSession.add_to_project() if explicit addition needed

No special "add to pipeline" operation exists because the canonical project IS the pipeline.

### 7. BusinessSeeder Simplification

**Remove pipeline-specific logic:**

```python
# REMOVE from seed_async():
# - ProcessProjectRegistry import
# - registry.get_project_gid(process_type) lookup
# - session.add_to_project(proc, project_gid) for pipeline
# - section_gid lookup and move_to_section

# KEEP:
# - Find-or-create Business, Unit, ProcessHolder
# - Create Process as subtask of ProcessHolder
# - Process inherits project membership from hierarchy
```

**Updated SeederResult:**
- Remove `added_to_pipeline: bool` field
- Keep all other fields

**Process project membership:** The Process becomes a member of the appropriate project when created. If the Unit belongs to "Sales" project, the Process (as a subtask chain) inherits that membership.

---

## Consequences

### Positive

- **~1,000 lines of code removed** (process_registry.py, tests, consumers)
- **Simpler mental model**: Canonical project IS the pipeline
- **No configuration burden**: No AUTOM8_PROCESS_PROJECT_* env vars
- **Cleaner detection**: Only ProjectTypeRegistry needed for entity detection
- **Preserved functionality**: pipeline_state still works, ProcessSection.from_name() unchanged
- **Backward compatible**: ProcessType.GENERIC still valid, existing processes unaffected

### Negative

- **move_to_state() removed**: Consumers need section GIDs (minor burden)
- **process_type detection is heuristic**: Based on project name matching (acceptable for current domain)
- **Multi-project edge case**: If Process in multiple projects, behavior is undefined (log warning)

### Neutral

- **ProcessType enum retained**: Still useful for categorization, derived differently
- **ProcessSection enum retained**: from_name() parsing remains valuable
- **ADR-0096, ADR-0097 still valid**: Enum definitions correct, just detection mechanism changed
- **ADR-0099, ADR-0100 need updates**: Seeder and state transition patterns simplified

---

## Implementation Guidance

### Phase 1: Registry Removal
1. Delete `process_registry.py`
2. Delete `test_process_registry.py`
3. Remove exports from `models/business/__init__.py`
4. Update `clean_registry` fixtures in test files (remove ProcessProjectRegistry.reset())

### Phase 2: Detection System Update
1. Remove ProcessProjectRegistry check from `_detect_tier1_project_membership()`
2. Ensure Process projects registered in ProjectTypeRegistry (if not already)
3. Update TestPipelineDetection tests (remove registry mocking)

### Phase 3: Process Entity Cleanup
1. Remove `add_to_pipeline()` method
2. Simplify `pipeline_state` property (remove registry lookup)
3. Simplify `process_type` property (derive from project name)
4. Remove `move_to_state()` method
5. Update tests: delete TestAddToPipeline, TestMoveToState

### Phase 4: Seeder Simplification
1. Remove registry imports and usage from `seed_async()`
2. Remove `added_to_pipeline` from SeederResult
3. Verify Process inherits project membership from hierarchy
4. Update seeder tests

### Phase 5: Documentation
1. Mark ADR-0098 as superseded
2. Update docs/INDEX.md
3. Archive TDD-PROCESS-PIPELINE, PRD-PROCESS-PIPELINE as superseded

---

## Related Decisions

- **ADR-0096**: ProcessType Expansion - **Remains valid** (enum values correct)
- **ADR-0097**: ProcessSection State Machine - **Remains valid** (from_name() unchanged)
- **ADR-0098**: Dual Membership Model - **SUPERSEDED by this ADR**
- **ADR-0099**: BusinessSeeder Factory - **Needs update** (remove pipeline logic)
- **ADR-0100**: State Transition Composition - **SUPERSEDED** (move_to_state removed)

---

## Compliance

- [ ] ProcessProjectRegistry deleted per Phase 1
- [ ] Detection uses only ProjectTypeRegistry per Phase 2
- [ ] add_to_pipeline() removed per Phase 3
- [ ] pipeline_state simplified per Phase 3
- [ ] process_type derives from project name per Phase 3
- [ ] move_to_state() removed per Phase 3
- [ ] BusinessSeeder simplified per Phase 4
- [ ] ADR-0098 marked superseded
- [ ] All tests pass after cleanup
