# ADR-0098: Dual Membership Model

## Metadata
- **Status**: Superseded by [ADR-0101](ADR-0101-process-pipeline-correction.md)
- **Author**: Architect
- **Date**: 2025-12-17
- **Deciders**: Architect, Requirements Analyst
- **Related**: [PRD-PROCESS-PIPELINE](../requirements/PRD-PROCESS-PIPELINE.md), [TDD-PROCESS-PIPELINE](../design/TDD-PROCESS-PIPELINE.md), [ADR-0096](ADR-0096-processtype-expansion.md), [ADR-0097](ADR-0097-processsection-state-machine.md)

---

## Context

Process entities currently exist only within the hierarchy:

```
Business > UnitHolder > Unit > ProcessHolder > Process
```

The Process is a subtask of ProcessHolder, which is a subtask of Unit, etc. This subtask relationship forms the **hierarchy membership**.

For pipeline functionality, Process entities must also appear in pipeline projects (e.g., "Sales Pipeline" project) to be visible in board views and track pipeline state via section membership.

**Forces at play**:

1. **Hierarchy preservation**: Navigation (process.unit.business) must continue to work
2. **Pipeline visibility**: Process must appear in pipeline project board view
3. **Detection priority**: Which project determines EntityType vs ProcessType?
4. **Multiple pipeline projects**: What if a Process is in multiple pipeline projects?
5. **Existing SaveSession capabilities**: `add_to_project()` already exists

Asana API supports tasks being members of multiple projects simultaneously. A task's `memberships` array contains one entry per project.

---

## Decision

**Process entities maintain dual membership: hierarchy (via subtask relationship) AND pipeline project (via add_to_project).**

**Detection uses hierarchy project for EntityType and pipeline project for ProcessType.**

**Multiple pipeline project membership is treated as an error condition: return None/GENERIC with warning log.**

The implementation:

1. **Hierarchy membership** (existing):
   - Process is subtask of ProcessHolder
   - Navigation works via cached `_process_holder`, `_unit`, `_business` refs
   - EntityType detection uses parent inference or structure inspection

2. **Pipeline membership** (new):
   - Process added to pipeline project via `add_to_project()`
   - Section membership tracked in `memberships` array
   - ProcessType detection uses ProcessProjectRegistry lookup

3. **add_to_pipeline() helper**:
   ```python
   def add_to_pipeline(
       self,
       session: SaveSession,
       process_type: ProcessType,
       *,
       section: ProcessSection | None = None,
   ) -> SaveSession:
       # Look up project GID from ProcessProjectRegistry
       # Queue add_to_project action
       # Optionally queue move_to_section for initial state
   ```

4. **Multi-pipeline error handling**:
   ```python
   # In pipeline_state property
   if len(pipeline_memberships) > 1:
       logger.warning(
           "Process in multiple pipeline projects",
           extra={"process_gid": self.gid, "pipeline_projects": [...]},
       )
       return None

   # In process_type property - return GENERIC with warning
   ```

---

## Rationale

**Why dual membership?**

| Approach | Hierarchy Preserved | Pipeline Visible | Complexity |
|----------|--------------------:|:----------------:|:----------:|
| Subtask only | Yes | No (not in board view) | Low |
| Project only | No (loses navigation) | Yes | Medium |
| Dual membership | Yes | Yes | Medium |

Dual membership is the only approach that satisfies both requirements.

**Why treat multi-pipeline as error?**

A Process in multiple pipeline projects creates ambiguity:
- Which ProcessType is correct?
- Which section represents the true state?

Rather than arbitrary resolution (e.g., "first match"), we:
1. Log a warning with details for debugging
2. Return None/GENERIC to indicate undefined state
3. Consumers can detect this condition and handle appropriately

This makes the error visible rather than silently choosing wrong values.

**Why not validate single pipeline at add_to_pipeline?**

- Process may already be in a pipeline project (created via Asana UI)
- Checking would require API call to fetch current memberships
- Validation at read time (pipeline_state) is sufficient

**Why hierarchy-first for EntityType detection?**

EntityType.PROCESS should be detected regardless of pipeline membership. A Process that isn't in any pipeline project is still a Process. The detection tiers (parent inference, structure inspection) work without pipeline project configuration.

ProcessType detection is separate: it specifically checks pipeline project membership.

---

## Alternatives Considered

### Alternative 1: Project-Only Model

- **Description**: Move Process out of hierarchy into pipeline project only
- **Pros**: Simpler membership model
- **Cons**: Breaks navigation (process.unit.business), loses hierarchy benefits, existing patterns break
- **Why not chosen**: Unacceptable breaking change to existing SDK patterns

### Alternative 2: Multi-Pipeline with Priority

- **Description**: Allow multiple pipeline projects, use first match or configured priority
- **Pros**: Flexible, no error condition
- **Cons**: Arbitrary resolution, hidden bugs, unclear semantics
- **Why not chosen**: Silent arbitrary behavior is worse than explicit error

### Alternative 3: Enforce Single Pipeline at Write Time

- **Description**: Validate and prevent adding to pipeline if already in one
- **Pros**: Prevents error condition from occurring
- **Cons**: Requires API call to check current memberships, may conflict with UI-created memberships
- **Why not chosen**: SDK shouldn't block legitimate operations; read-time detection is sufficient

### Alternative 4: Virtual Pipeline Membership

- **Description**: Track pipeline info in custom field instead of project membership
- **Pros**: No dual membership complexity
- **Cons**: Doesn't appear in Asana board view, not how stakeholders use pipelines
- **Why not chosen**: Doesn't satisfy visibility requirement

---

## Consequences

**Positive**:
- Preserves full hierarchy navigation
- Enables pipeline board view in Asana UI
- Clear error handling for edge cases
- Leverages existing SaveSession.add_to_project()
- No breaking changes to existing code

**Negative**:
- Process memberships array grows (2+ entries)
- Multi-pipeline detection adds complexity
- Error condition (multi-pipeline) requires consumer handling
- Detection logic must distinguish hierarchy vs pipeline projects

**Neutral**:
- Membership parsing slightly more complex
- add_to_pipeline() is convenience wrapper, not strictly necessary
- Pipeline membership optional (GENERIC still valid)

---

## Compliance

- [ ] add_to_pipeline() uses SaveSession.add_to_project() per FR-DUAL-001
- [ ] ProcessProjectRegistry lookup per FR-DUAL-002
- [ ] Optional section parameter per FR-DUAL-003
- [ ] ValueError for unconfigured ProcessType per FR-DUAL-004
- [ ] Detection recognizes dual-membership per FR-DUAL-005
- [ ] Multi-pipeline returns None with warning per FR-STATE-005/008
- [ ] Warning log includes process_gid and project GIDs
