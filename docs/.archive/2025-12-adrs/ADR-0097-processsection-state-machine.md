# ADR-0097: ProcessSection State Machine Pattern

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-17
- **Deciders**: Architect, Requirements Analyst
- **Related**: [PRD-PROCESS-PIPELINE](../requirements/PRD-PROCESS-PIPELINE.md), [TDD-PROCESS-PIPELINE](../design/TDD-PROCESS-PIPELINE.md), [ADR-0096](ADR-0096-processtype-expansion.md)

---

## Context

Pipeline processes move through stages: Opportunity -> Active -> Scheduled -> Converted (or Did Not Convert). In Asana, these stages are represented as **sections** within a project. A task's position in a section determines its pipeline state.

**Forces at play**:

1. **State representation**: Need a typed enum for pipeline states
2. **State extraction**: Must read current state from task data without API call
3. **Name matching**: Section names in Asana may vary slightly ("Did Not Convert" vs "Lost")
4. **State machine enforcement**: Should SDK enforce valid state transitions?
5. **Custom sections**: Some projects may have additional sections not in standard list

The `Task.memberships` attribute contains section information:
```python
memberships = [
    {
        "project": {"gid": "123", "name": "Sales Pipeline"},
        "section": {"gid": "456", "name": "Opportunity"}
    }
]
```

---

## Decision

**Represent pipeline states via ProcessSection enum with section membership as the source of truth.**

**Provide from_name() method for case-insensitive matching with OTHER fallback.**

**Do NOT enforce state transition rules in the SDK.**

The implementation:

1. **ProcessSection enum**:
   ```python
   class ProcessSection(str, Enum):
       OPPORTUNITY = "opportunity"
       DELAYED = "delayed"
       ACTIVE = "active"
       SCHEDULED = "scheduled"
       CONVERTED = "converted"
       DID_NOT_CONVERT = "did_not_convert"
       OTHER = "other"
   ```

2. **from_name() classmethod**:
   ```python
   @classmethod
   def from_name(cls, name: str | None) -> ProcessSection | None:
       # Normalize: lowercase, replace spaces/hyphens with underscores
       # Match against enum values
       # Support aliases ("Lost" -> DID_NOT_CONVERT)
       # Return OTHER for unrecognized names
       # Return None for None input
   ```

3. **pipeline_state property** on Process:
   ```python
   @property
   def pipeline_state(self) -> ProcessSection | None:
       # Find pipeline project membership via ProcessProjectRegistry
       # Extract section name
       # Return ProcessSection.from_name(section_name)
   ```

---

## Rationale

**Why section membership as state source?**

| State Source | Pros | Cons |
|--------------|------|------|
| Section membership | Matches Asana UI, already in memberships | Requires project GID to identify correct membership |
| Custom field | Explicit, independent of project | Requires API call, may be out of sync with section |
| Task property | Built into Task model | No such property exists in Asana API |

Section membership is the canonical representation of pipeline state in Asana. The board view, which stakeholders use to manage pipelines, is a section-based view.

**Why no state machine enforcement?**

Per PRD-PROCESS-PIPELINE scope: "State machine enforcement - SDK enables transitions, does not enforce valid sequences."

Reasons:
- Different workflows have different valid transitions
- Business rules belong in consumers, not SDK
- Enforcement would require maintaining transition rules per ProcessType
- Stakeholders may legitimately skip states

The SDK provides the primitive (`move_to_state`), consumers implement the rules.

**Why OTHER fallback?**

- Projects may have custom sections not in standard list
- Better to return a value than throw an error for unknown sections
- Consumers can check for OTHER and handle accordingly

**Why aliases in from_name()?**

Section names may vary between projects or be renamed by users:
- "Did Not Convert" vs "Lost" vs "Didn't Convert"
- "Active" vs "In Progress"

Supporting common aliases improves reliability without requiring exact configuration.

---

## Alternatives Considered

### Alternative 1: State Machine with Validation

- **Description**: Define valid state transitions per ProcessType, raise error on invalid moves
- **Pros**: Prevents invalid states, self-documenting rules
- **Cons**: SDK must know all business rules, inflexible, different workflows have different rules
- **Why not chosen**: Business logic belongs in consumers; SDK is a data layer, not a workflow engine

### Alternative 2: Custom Field for State

- **Description**: Use a "Pipeline State" custom field instead of section membership
- **Pros**: Independent of section, explicit value
- **Cons**: Requires API call, can become out of sync with section position, doesn't match Asana UI
- **Why not chosen**: Section membership is the source of truth in Asana's pipeline view

### Alternative 3: Strict Section Name Matching

- **Description**: Only accept exact section names, error on mismatch
- **Pros**: Explicit, catches configuration errors
- **Cons**: Brittle, breaks if user renames section
- **Why not chosen**: Too fragile; from_name() with normalization is more robust

### Alternative 4: Dynamic Section Enum

- **Description**: Generate ProcessSection from actual sections in pipeline projects
- **Pros**: Always matches reality
- **Cons**: Requires API call at import time, enum values not predictable, no IDE support
- **Why not chosen**: Over-engineering; fixed enum with OTHER fallback covers requirements

---

## Consequences

**Positive**:
- Clear type safety for pipeline states
- Matches Asana UI (board view sections)
- Robust name matching with aliases
- No API calls for state extraction
- Flexible: OTHER handles custom sections

**Negative**:
- SDK does not enforce valid transitions (consumer responsibility)
- Alias list may need maintenance as users create new section names
- OTHER provides less information than specific state

**Neutral**:
- from_name() adds small overhead (string normalization)
- Section GID configuration optional (name matching sufficient for most cases)

---

## Compliance

- [ ] ProcessSection enum has 7 values per PRD
- [ ] from_name() is case-insensitive per FR-SECTION-002
- [ ] from_name() returns OTHER for unrecognized per FR-SECTION-003
- [ ] from_name() returns None for None input per FR-SECTION-004
- [ ] No state transition validation in SDK (out of scope per PRD)
- [ ] Alias list documented in code comments
