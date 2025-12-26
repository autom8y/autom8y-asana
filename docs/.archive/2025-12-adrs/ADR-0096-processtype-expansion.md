# ADR-0096: ProcessType Expansion and Detection

> **SUPERSESSION NOTICE (2025-12-19)**
>
> The `ProcessProjectRegistry` portion of this ADR has been **superseded** by [ADR-0101](ADR-0101-process-pipeline-correction.md). The ProcessProjectRegistry was never implemented. Pipeline project detection now uses `WorkspaceProjectRegistry` for dynamic discovery, which registers pipeline projects as `EntityType.PROCESS` in the existing `ProjectTypeRegistry`.
>
> **Superseded**: ProcessProjectRegistry design (Section "Decision", implementation details)
>
> **Still valid**: ProcessType enum expansion (SALES, OUTREACH, ONBOARDING, etc.), GENERIC fallback

## Metadata
- **Status**: Partially Superseded
- **Author**: Architect
- **Date**: 2025-12-17
- **Deciders**: Architect, Requirements Analyst
- **Superseded By**: [ADR-0101](ADR-0101-process-pipeline-correction.md) (ProcessProjectRegistry removal)
- **Related**: [PRD-PROCESS-PIPELINE](../requirements/PRD-PROCESS-PIPELINE.md), [TDD-PROCESS-PIPELINE](../design/TDD-PROCESS-PIPELINE.md), [ADR-0093](ADR-0093-project-type-registry.md)

---

## Context

The current `ProcessType` enum contains only `GENERIC` as a placeholder for future process type differentiation. Per PRD-PROCESS-PIPELINE, stakeholders require 6 specific pipeline process types:

- SALES (sales opportunities)
- OUTREACH (marketing campaigns)
- ONBOARDING (customer onboarding)
- IMPLEMENTATION (service implementation)
- RETENTION (customer retention efforts)
- REACTIVATION (dormant customer reactivation)

**Forces at play**:

1. **Backward compatibility**: Existing code uses `ProcessType.GENERIC` and must continue to work
2. **Detection mechanism**: Need a reliable way to determine ProcessType from task data
3. **Configuration flexibility**: Pipeline project GIDs vary between environments (dev/staging/prod)
4. **Pattern consistency**: Should follow established ProjectTypeRegistry pattern for entity type detection
5. **Performance**: ProcessType detection must be fast (<1ms) without API calls

The existing `ProjectTypeRegistry` (per ADR-0093) maps project GIDs to `EntityType`. A similar pattern could map project GIDs to `ProcessType`.

---

## Decision

**Expand ProcessType enum with 6 stakeholder-aligned values while preserving GENERIC as fallback.**

**Detect ProcessType via pipeline project membership using a new ProcessProjectRegistry singleton.**

The implementation:

1. **ProcessType enum expansion**:
   ```python
   class ProcessType(str, Enum):
       SALES = "sales"
       OUTREACH = "outreach"
       ONBOARDING = "onboarding"
       IMPLEMENTATION = "implementation"
       RETENTION = "retention"
       REACTIVATION = "reactivation"
       GENERIC = "generic"  # Fallback
   ```

2. **ProcessProjectRegistry** (new singleton):
   - Maps `ProcessType` -> `project_gid`
   - Reverse lookup: `project_gid` -> `ProcessType`
   - Environment variable configuration: `ASANA_PROCESS_PROJECT_{TYPE}`
   - Lazy initialization

3. **Process.process_type property**:
   - Checks memberships against ProcessProjectRegistry
   - Returns detected ProcessType if in registered pipeline
   - Returns GENERIC if not in any registered pipeline (backward compatible)

---

## Rationale

**Why project membership over custom field?**

| Detection Method | Pros | Cons |
|------------------|------|------|
| Project membership | O(1) lookup, no API needed, matches Asana UI | Requires project GID configuration |
| Custom field value | Explicit per-entity | Requires API call to read, inconsistent if field missing |
| Task name pattern | No configuration | Unreliable, easily broken by user edits |

Project membership is:
- Already available in `Task.memberships` (populated by default)
- The source of truth for pipeline view in Asana UI
- Consistent with Tier 1 detection pattern for EntityType

**Why separate ProcessProjectRegistry vs. extending ProjectTypeRegistry?**

ProcessType (workflow type) is orthogonal to EntityType (model type):
- A Process is always EntityType.PROCESS
- A Process may be ProcessType.SALES, ONBOARDING, etc.

Separate registries maintain single responsibility and allow independent evolution.

**Why GENERIC as fallback?**

- Preserves backward compatibility (all existing processes are GENERIC)
- Provides safe default for processes not in registered pipelines
- Clear semantic: "process without specific pipeline assignment"

---

## Alternatives Considered

### Alternative 1: Custom Field for ProcessType

- **Description**: Add a "Process Type" custom field to Process entities, read value to determine type.
- **Pros**: Explicit per-entity, survives project membership changes
- **Cons**: Requires API call to read custom fields, must maintain custom field in Asana, sync issues between field and project membership
- **Why not chosen**: Adds complexity, violates <1ms performance requirement, doesn't match how stakeholders use Asana (they organize by project, not custom field)

### Alternative 2: Extend ProjectTypeRegistry

- **Description**: Add ProcessType mappings to existing ProjectTypeRegistry
- **Pros**: Single registry, less code
- **Cons**: Conflates EntityType and ProcessType, registry responsibilities become unclear, harder to maintain
- **Why not chosen**: Violates single responsibility, ProcessType and EntityType are orthogonal concepts

### Alternative 3: Process Subclasses per Type

- **Description**: Create SalesProcess, OnboardingProcess, etc. subclasses
- **Pros**: Type safety via class hierarchy
- **Cons**: Explosion of classes, complex factory logic, harder to add new types
- **Why not chosen**: Over-engineering for current requirements; enum provides sufficient type safety

---

## Consequences

**Positive**:
- Clear type differentiation for pipeline processes
- Fast O(1) detection without API calls
- Flexible environment-based configuration
- Backward compatible (GENERIC preserved)
- Follows established registry pattern

**Negative**:
- Requires environment variable configuration per environment
- Process entities in unregistered projects default to GENERIC (may mask configuration issues)
- ProcessProjectRegistry is another singleton to manage in tests

**Neutral**:
- ProcessType enum grows from 1 to 7 values
- Test `test_process_type_enum_member_count` must be updated
- Detection code path slightly longer for processes (check both registries)

---

## Compliance

- [ ] ProcessType enum values match PRD-PROCESS-PIPELINE stakeholder list
- [ ] Environment variable naming follows `ASANA_PROCESS_PROJECT_{TYPE}` pattern
- [ ] ProcessProjectRegistry follows singleton pattern per ADR-0093
- [ ] Update test_process_type_enum_member_count to expect 7 values
- [ ] Document environment variables in SDK README
