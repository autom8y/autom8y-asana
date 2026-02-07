---
artifact_id: ADR-GAP-01-pipeline-vs-holder-manager
title: "ADR: Pipeline Phase vs Standalone HolderManager for Holder Auto-Creation"
created_at: "2026-02-07T17:00:00Z"
author: architect
status: accepted
supersedes: null
superseded_by: null
---

# ADR: Pipeline Phase vs Standalone HolderManager

## Status

**Accepted** (2026-02-07)

## Context

The save system needs to auto-create missing holder subtasks (ContactHolder, UnitHolder, etc.) when a consumer saves a Business or Unit with children. Today, `_track_recursive` silently skips unpopulated holders, causing children to be dropped.

Per PRD-GAP-01 stakeholder decisions, the architecture must choose between exactly two options:

1. **Option A: New SavePipeline phase** -- Add an ENSURE_HOLDERS phase to the existing six-phase pipeline, running before VALIDATE.
2. **Option B: Standalone HolderManager service** -- Create a new service class (similar to HealingManager) that SaveSession calls before commit.

Both options are viable. The decision affects where holder creation logic lives, how it interacts with the tracker and graph, and how maintainable the result is in 18 months.

## Decision

**Option A: New SavePipeline phase (ENSURE_HOLDERS).**

## Rationale

### Option A: Pipeline Phase

**Pros:**
- **Natural lifecycle position**: Holder creation must happen after tracking and before graph construction. The pipeline already orchestrates this exact lifecycle. Adding a phase at the start is a natural extension.
- **Direct access to collaborators**: The pipeline already has references to `ChangeTracker`, `DependencyGraph`, `BatchClient`, and `EventSystem`. A phase can use all of these without introducing new wiring.
- **Consistent mental model**: Developers working on the save system already understand the phase sequence (VALIDATE -> PREPARE -> EXECUTE -> ACTIONS -> CONFIRM). Adding ENSURE_HOLDERS as Phase 0 is easy to discover and reason about.
- **Atomic with the commit**: The phase runs inside `execute()` / `execute_with_actions()`, so it participates in the same error handling and result reporting as the rest of the pipeline. No separate error path needed.
- **Precedent**: The pipeline already evolved from 4 phases (TDD-0010) to 5 phases (TDD-0011 actions). Adding a 6th phase follows established practice.

**Cons:**
- **Pipeline grows**: One more phase increases the size of `pipeline.py`. Mitigated by extracting the logic into a `HolderEnsurer` collaborator class (SRP), leaving the pipeline as a thin orchestrator.
- **Coupling to pipeline internals**: The ENSURE_HOLDERS phase needs the tracker to register new entities. But the pipeline already uses the tracker (for `get_state`, `get_changed_fields`), so this is not new coupling.

### Option B: Standalone HolderManager

**Pros:**
- **Separation of concerns**: A standalone class like HealingManager keeps holder logic isolated.
- **Testable in isolation**: Can be tested without instantiating SavePipeline.

**Cons:**
- **Lifecycle orchestration burden on SaveSession**: SaveSession would need to call `holder_manager.ensure()` at the right moment in `commit_async()`, manage the result, and feed new entities back into the pipeline. This is the same orchestration the pipeline already does.
- **Awkward data flow**: The HolderManager would need to mutate the tracker (to register new entities) and the entity list (to add holders for graph construction), but it wouldn't own either. This creates a coordination problem where the caller (SaveSession) must stitch together HolderManager output with pipeline input.
- **Inconsistent with HealingManager**: Despite the name similarity, HealingManager is fundamentally different -- it runs AFTER CRUD and makes independent API calls (addProject). Holder creation must run BEFORE CRUD and its output feeds INTO the CRUD pipeline. The lifecycle positions are opposite, making the analogy misleading.
- **Duplicated error handling**: A standalone service would need its own partial-failure logic, cascading failure tracking, and result reporting. The pipeline already has all of this.
- **Discovery problem**: A developer debugging a save that creates holders would look in the pipeline first. Finding that the logic lives in a separate service requires knowing it exists.

### Decisive Factor

The key difference is **lifecycle position**. Holder creation produces entities that must participate in the CRUD pipeline (dependency graph, batch execution, GID resolution). A pipeline phase gets this for free. A standalone service must reconstruct the handoff.

HealingManager works as a standalone because its operations are fire-and-forget (addProject calls after all CRUD is done). Holder creation is the opposite: its output is the input to the next phase. This makes a pipeline phase the natural home.

## Consequences

### Enabled
- Holder creation is discoverable by reading the pipeline phases in order.
- New holders automatically participate in dependency graph, batch execution, GID resolution, and error handling without additional wiring.
- The `HolderEnsurer` collaborator class can still be tested in isolation (it's a POPO that the phase calls).
- Future enhancements (holder ordering, holder field population) can be added to the same phase.

### Constrained
- `SavePipeline` gains an `AsanaClient` dependency (for subtasks detection). Previously it only needed `BatchClient`. This is a minor widening of the interface.
- The pipeline phase sequence must be documented clearly so that the ENSURE_HOLDERS -> VALIDATE -> PREPARE -> EXECUTE ordering is understood.
- Pipeline tests grow to cover the new phase. Mitigated by the `HolderEnsurer` having its own unit tests.

### Risks
- If the pipeline grows beyond 6-7 phases, it may become unwieldy. At that point, consider a phase registry pattern. For now, 6 phases is manageable.

## Alternatives Considered

Only Option A and Option B were considered per stakeholder constraints. Two other options were explicitly excluded during requirements:
- Extending `_track_recursive` (rejected: conflates tracking with construction)
- Pre-commit hook (rejected: hooks are for validation, not entity creation)

## References

- PRD-GAP-01-hierarchical-save (OQ-2 resolution)
- TDD-GAP-01-hierarchical-save (companion design document)
- SavePipeline: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/pipeline.py`
- HealingManager: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/healing.py`
