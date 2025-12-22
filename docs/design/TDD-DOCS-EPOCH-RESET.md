# TDD: Documentation Epoch Reset

## Metadata

- **TDD ID**: TDD-DOCS-EPOCH-RESET
- **Status**: Draft
- **Author**: Architect (via Orchestrator)
- **Created**: 2025-12-17
- **Last Updated**: 2025-12-17
- **PRD Reference**: [PRD-DOCS-EPOCH-RESET](../requirements/PRD-DOCS-EPOCH-RESET.md)
- **Related TDDs**: None (documentation-only initiative)
- **Related ADRs**: ADR-PARADIGM-LOCATION (inline below)

---

## Overview

This TDD defines the information architecture and implementation sequence for the Documentation Epoch Reset initiative. The core design decision is where to place the Asana-as-database paradigm documentation, how to sequence updates to maintain cross-reference integrity, and how to establish a 2-click discoverability path from CLAUDE.md.

---

## Requirements Summary

From PRD-DOCS-EPOCH-RESET:

| Requirement | Priority | Summary |
|-------------|----------|---------|
| FR-STATUS-001/002/003 | Must | Remove "Prototype" claims from 3 files |
| FR-COVERAGE-001/002 | Must | Replace "~0%" with qualitative coverage descriptions |
| FR-ENTITY-001/002 | Must | Correct stub count from 4 to 3 |
| FR-PARADIGM-001/002 | Must | Document Asana-as-database, make discoverable in 2 clicks |
| FR-XREF-001/002 | Should | Verify links, update INDEX.md |

---

## System Context

This is a documentation-only initiative. The "system" is the `.claude/` skills architecture and `/docs/` registry.

```
                     +------------------+
                     |    CLAUDE.md     |  <-- Entry point
                     +--------+---------+
                              |
            +-----------------+-----------------+
            |                                   |
   +--------v---------+              +----------v---------+
   | PROJECT_CONTEXT  |              |      skills/       |
   | (overview)       |              |                    |
   +------------------+              +---------+----------+
                                               |
                     +-------------------------+-------------------------+
                     |                         |                         |
          +----------v----------+   +----------v----------+   +----------v----------+
          | autom8-asana-domain |   | autom8-asana-business|   |   documentation    |
          | (SDK infrastructure)|   | (entity model)       |   |   (templates)      |
          +---------------------+   +----------------------+   +--------------------+
                     |
    +----------------+----------------+----------------+
    |                |                |                |
+---v---+       +----v----+      +----v----+      +----v----+
|context|       |glossary |      |tech-stack|      |paradigm |  <-- NEW
+-------+       +---------+      +----------+      +---------+
```

---

## Design

### ADR: Paradigm Documentation Location

**Decision ID**: ADR-PARADIGM-LOCATION (inline)

#### Context

The Asana-as-database paradigm is the fundamental architectural insight that makes this project unique. It needs a canonical home. Four options were evaluated:

| Option | Location | Pros | Cons |
|--------|----------|------|------|
| **A** | `.claude/skills/autom8-asana-domain/paradigm.md` | Near SDK context; skill activation works; follows existing pattern | Another file in skills |
| **B** | New section in `.claude/PROJECT_CONTEXT.md` | Highest visibility; no new file | PROJECT_CONTEXT is meant to be brief overview; would bloat it |
| **C** | `/docs/concepts/asana-as-database.md` | Follows "docs for docs" pattern; proper place for conceptual content | Creates new concepts/ folder; further from agent context loading; breaks 2-click path |
| **D** | `.claude/skills/autom8-asana-business/paradigm.md` | Near entity model | Wrong conceptual home; paradigm is about infrastructure, not business entities |

#### Decision

**Option A**: Create `.claude/skills/autom8-asana-domain/paradigm.md`

#### Rationale

1. **Skill activation alignment**: The paradigm is about how Asana infrastructure supports the SDK. When agents load `autom8-asana-domain`, they should get this context.

2. **2-click discoverability**: CLAUDE.md "Getting Help" table links to skills. Skills have Quick Reference tables. Adding paradigm to Quick Reference = 2 clicks exactly.

3. **Pattern consistency**: The domain skill already has context.md, glossary.md, code-conventions.md. Adding paradigm.md follows this modular pattern.

4. **Appropriate coupling**: The business entities skill (`autom8-asana-business`) explains WHAT entities exist. The domain skill explains WHY they work (Asana-as-database enables typed entities). This separation is correct.

5. **No structural changes**: PRD constraint is to preserve existing skills architecture. Adding a file is additive, not restructuring.

#### Consequences

- **Positive**: Natural home for paradigm; discoverable; maintains skill modularity
- **Negative**: Users searching `/docs/` won't find paradigm directly (mitigated by INDEX.md cross-reference)
- **Neutral**: SKILL.md Quick Reference needs update to include paradigm link

---

### Paradigm Document Structure

**File**: `.claude/skills/autom8-asana-domain/paradigm.md`

```
# Asana-as-Database Paradigm

> The architectural foundation that enables typed business entities

---

## The Core Insight

[2-3 paragraphs explaining: Asana is not just a project management tool for this SDK -
it serves as the database layer. Why this was chosen. What it enables.]

---

## The Mapping

| Asana Concept | Database Analog | SDK Implementation |
|---------------|-----------------|-------------------|
| Task | Row | Entity (Business, Contact, Unit, Offer, etc.) |
| Custom Field | Column | Typed property descriptor |
| Subtask | Foreign key relationship | Holder pattern (ContactHolder, UnitHolder) |
| Project | Table / Index | Entity type registry (used for detection) |
| Asana UI | Admin interface | Free CRUD for operators |

---

## Visual Architecture

[ASCII diagram showing the layers:
  Asana Platform (Tasks, Projects, Custom Fields)
       |
  autom8_asana SDK (Typed entities, SaveSession, Detection)
       |
  Consumer Applications]

---

## Why This Architecture

[3-4 bullet points on benefits:
- No infrastructure to manage
- Free admin UI
- API-first by design
- Flexible schema via custom fields]

---

## Implications for Development

[Brief section on what developers need to know:
- Entities are Tasks with custom fields
- Detection uses project membership
- Hierarchy uses subtask relationships
- Persistence uses Asana API (not SQL)]

---

## Related

- [entity-lifecycle.md](../autom8-asana-business/entity-lifecycle.md) - How entities use this paradigm
- [detection.md](../autom8-asana-business/detection.md) - How project membership enables type detection
- [glossary.md](glossary.md) - SDK terminology
```

---

### Discoverability Path Design

**Requirement**: Paradigm must be reachable in 2 clicks from CLAUDE.md.

**Path 1 (Primary)**: Via Skills Table

```
CLAUDE.md
  -> Skills Architecture table -> autom8-asana-domain (click 1)
  -> SKILL.md Quick Reference -> paradigm.md (click 2)
```

**Path 2 (Alternative)**: Via Getting Help Table

```
CLAUDE.md
  -> Getting Help table -> "What is Asana-as-database?" row (click 1)
  -> Links to paradigm.md directly (click 2 is the content)
```

**Implementation**:

1. Add row to CLAUDE.md "Getting Help" table:
   ```markdown
   | What is Asana-as-database? | `autom8-asana-domain/paradigm.md` |
   ```

2. Add entry to SKILL.md Quick Reference:
   ```markdown
   | Understand Asana-as-database paradigm | [paradigm.md](paradigm.md) |
   ```

3. Update PROJECT_CONTEXT.md to mention paradigm:
   ```markdown
   See `autom8-asana-domain/paradigm.md` for the foundational architecture.
   ```

---

### Component Update Specifications

#### 1. PROJECT_CONTEXT.md Updates

| Line | Current | Target |
|------|---------|--------|
| 27 | `Stage | Prototype` | `Stage | Production` |
| Add after "What Is This?" | N/A | Brief mention of Asana-as-database paradigm with link |

**No changes to test coverage metrics** - PROJECT_CONTEXT.md already has qualitative description ("Extensive").

#### 2. context.md Updates

| Line | Current | Target |
|------|---------|--------|
| 15 | "Prototype for extracting other APIs" | "Production SDK; demonstrates extraction pattern for other APIs" |
| 57 | `**Stage**: Prototype (greenfield extraction)` | `**Stage**: Production` |
| 61 | `Test coverage | ~0% (test infrastructure being built)` | `Test coverage | Comprehensive (business model, detection, persistence)` |
| 127 | `Test coverage | >=80% core modules | ~0%` | `Test coverage | Comprehensive | Achieved` |

**Remove entire "Success Metrics" table rows with percentages** - Replace with qualitative descriptions per PRD constraint.

#### 3. tech-stack.md Updates

| Line | Current | Target |
|------|---------|--------|
| 61 | `Version | 0.1.0 (prototype)` | `Version | 0.1.0` |

#### 4. entity-reference.md Updates

| Line | Current | Target |
|------|---------|--------|
| 22 | `+-- DNAHolder, ReconciliationsHolder, AssetEditHolder, VideographyHolder (stubs)` | `+-- DNAHolder, ReconciliationHolder, VideographyHolder (stubs)` |

**Add clarification section** after hierarchy diagram:

```markdown
### Stub Definition

A **stub entity** provides navigation structure only - no custom field accessors.
Per TDD-HARDENING-A (FR-STUB-001/002/003), these entities exist for hierarchy
completion but are not yet fully implemented:

| Stub | Lines | Status |
|------|-------|--------|
| DNAHolder | ~57 | Navigation only |
| ReconciliationHolder | ~78 | Navigation only |
| VideographyHolder | ~57 | Navigation only |

**Note**: AssetEdit is fully implemented (681 lines, 11 typed fields).
```

#### 5. SKILL.md Updates (autom8-asana-domain)

**Quick Reference table** - Add row:

```markdown
| Understand Asana-as-database paradigm | [paradigm.md](paradigm.md) |
```

**No framing changes needed** - Current SKILL.md does not claim "pure API wrapper" incorrectly. The constraint about "no business logic" refers to the SDK layer, not the business model layer (which is a separate skill).

#### 6. CLAUDE.md Updates

**Getting Help table** - Add row:

```markdown
| What is Asana-as-database? | `autom8-asana-domain/paradigm.md` |
```

#### 7. INDEX.md Updates

**Document Number Allocation** section - Update:

```markdown
| Type | Current Max | Next Available |
|------|-------------|----------------|
| PRD | PRD-0024 | PRD-0025 |  # After adding PRD-DOCS-EPOCH-RESET
```

**PRDs table** - Add row:

```markdown
| [PRD-DOCS-EPOCH-RESET](requirements/PRD-DOCS-EPOCH-RESET.md) | Documentation Epoch Reset | Active |
```

---

### Implementation Sequence

**Rationale for ordering**: Updates should flow from foundational files (that others reference) to dependent files, with new content created before cross-references that point to it.

| Phase | Order | File | Action | Dependency |
|-------|-------|------|--------|------------|
| 1 | 1.1 | `context.md` | Remove "~0%", update stage | None |
| 1 | 1.2 | `tech-stack.md` | Remove "(prototype)" | None |
| 1 | 1.3 | `PROJECT_CONTEXT.md` | Update stage, add paradigm mention | Paradigm file must exist (Phase 2) |
| 2 | 2.1 | `paradigm.md` | Create new file | None |
| 2 | 2.2 | `entity-reference.md` | Fix stub count, add clarification | None |
| 3 | 3.1 | `SKILL.md` | Add paradigm to Quick Reference | paradigm.md exists |
| 3 | 3.2 | `CLAUDE.md` | Add Getting Help row | paradigm.md exists |
| 3 | 3.3 | `INDEX.md` | Add PRD reference | PRD exists |

**Revised sequence** (accounting for dependency):

1. **Phase 1A: Status updates (no dependencies)**
   - context.md: Lines 15, 57, 61, 127
   - tech-stack.md: Line 61

2. **Phase 2: New content creation**
   - paradigm.md: Create complete file

3. **Phase 1B: Status updates (depend on Phase 2)**
   - PROJECT_CONTEXT.md: Line 27, add paradigm reference

4. **Phase 3: Entity corrections**
   - entity-reference.md: Line 22, add stub definition section

5. **Phase 4: Cross-reference updates**
   - SKILL.md: Add Quick Reference row
   - CLAUDE.md: Add Getting Help row
   - INDEX.md: Add PRD row, update allocation numbers

---

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Paradigm file location | `.claude/skills/autom8-asana-domain/paradigm.md` | Skill alignment, 2-click path, pattern consistency | ADR-PARADIGM-LOCATION (inline above) |
| Test coverage language | "Comprehensive" not percentages | User constraint; avoids maintenance burden | Per PRD-DOCS-EPOCH-RESET |
| Stub count | 3 (DNA, Reconciliation, Videography) | Verified against codebase; AssetEdit is 681 lines | Per PRD audit |
| Update sequence | Status first, new content, then cross-refs | Ensures targets exist before links point to them | Design decision |

---

## Complexity Assessment

**Level**: Script/Module

This is a documentation update initiative with:
- 7 files to modify
- 1 new file to create
- No code changes
- No architectural changes to skills structure
- Sequential but simple dependencies

The complexity is appropriate for the scope. No elaborate tooling, validation frameworks, or infrastructure changes are needed.

---

## Implementation Plan

### Phases

| Phase | Deliverable | Dependencies | Estimate |
|-------|-------------|--------------|----------|
| 1A | Status updates (context.md, tech-stack.md) | None | 15 min |
| 2 | paradigm.md creation | None | 30 min |
| 1B | PROJECT_CONTEXT.md updates | Phase 2 | 10 min |
| 3 | entity-reference.md corrections | None | 15 min |
| 4 | Cross-reference updates (SKILL.md, CLAUDE.md, INDEX.md) | Phases 1-3 | 15 min |
| 5 | Validation | Phases 1-4 | 20 min |

**Total**: ~2 hours

### Migration Strategy

N/A - No migration required. Updates are in-place modifications.

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Broken internal links after updates | Medium | Low | Phase 4 includes link validation; update targets before sources |
| Paradigm content is inaccurate | High | Low | Content based on codebase evidence; QA validation phase |
| Missing a "prototype" reference | Low | Medium | Grep for "prototype", "Prototype", "~0%" before marking complete |
| Entity stub count changes again | Low | Low | Use "currently 3 stubs" language; reference TDD-HARDENING-A |

---

## Observability

N/A - Documentation initiative. No runtime monitoring needed.

**Validation observability**:
- Grep commands to verify no stale claims remain
- Link checker to verify cross-references
- Manual walkthrough of 2-click path

---

## Testing Strategy

### Validation Checklist

1. **Accuracy validation**:
   - `grep -r "Prototype" .claude/` returns 0 hits (case-insensitive)
   - `grep -r "~0%" .claude/` returns 0 hits
   - `grep -r "4 stub" .claude/` returns 0 hits (or only historical references)

2. **Discoverability validation**:
   - Starting from CLAUDE.md, navigate to paradigm.md in exactly 2 clicks
   - Path documented and walkable

3. **Cross-reference validation**:
   - All markdown links in updated files resolve
   - INDEX.md includes PRD-DOCS-EPOCH-RESET

4. **Content validation**:
   - paradigm.md accurately describes Asana-as-database
   - Entity stub count matches codebase (3, not 4)
   - No specific percentages in test coverage claims

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| None | - | - | All questions resolved in this TDD |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-17 | Architect | Initial TDD |

---

## Quality Gates Checklist

- [x] Traces to approved PRD (PRD-DOCS-EPOCH-RESET)
- [x] All significant decisions have ADRs (ADR-PARADIGM-LOCATION inline)
- [x] Component responsibilities are clear (file-by-file specification)
- [x] Interfaces are defined (discoverability paths documented)
- [x] Complexity level is justified (Script/Module - appropriate for scope)
- [x] Risks identified with mitigations
- [x] Implementation plan is actionable (phased with dependencies)

---

## Appendix: File Change Summary

### Files to Modify

| File | Lines to Change | Nature of Change |
|------|-----------------|------------------|
| `.claude/skills/autom8-asana-domain/context.md` | 15, 57, 61, 127+ | Remove prototype/0% claims |
| `.claude/skills/autom8-asana-domain/tech-stack.md` | 61 | Remove "(prototype)" |
| `.claude/PROJECT_CONTEXT.md` | 27, add section | Update stage, add paradigm link |
| `.claude/skills/autom8-asana-business/entity-reference.md` | 22, add section | Fix stub count, add definition |
| `.claude/skills/autom8-asana-domain/SKILL.md` | Quick Reference table | Add paradigm row |
| `.claude/CLAUDE.md` | Getting Help table | Add paradigm row |
| `/docs/INDEX.md` | PRDs table, allocation | Add PRD entry |

### Files to Create

| File | Purpose |
|------|---------|
| `.claude/skills/autom8-asana-domain/paradigm.md` | Asana-as-database paradigm documentation |

---

## Appendix: paradigm.md Template

Principal Engineer should use this as starting structure:

```markdown
# Asana-as-Database Paradigm

> The architectural foundation that enables typed business entities

---

## The Core Insight

autom8_asana treats Asana as a database, not just a project management tool. This paradigm enables:
- Typed business entities (Business, Contact, Unit, Offer)
- Custom field properties with type safety
- Hierarchical relationships via subtasks
- Entity type detection via project membership

[Expand with context from codebase evidence]

---

## The Mapping

| Asana Concept | Database Analog | SDK Implementation |
|---------------|-----------------|-------------------|
| Task | Row | Entity instance (Business, Contact, etc.) |
| Custom Field | Column | Typed property descriptor (`@custom_field`) |
| Subtask | FK / Child row | Holder children (ContactHolder -> Contact[]) |
| Project membership | Table membership | Entity type registry (detection tier) |
| Section | Index / Partition | Optional grouping |
| Asana UI | Admin interface | Free CRUD for operators |

---

## Architecture Layers

```
+------------------------------------------+
|           Consumer Applications          |
|        (autom8 platform, services)       |
+------------------------------------------+
                    |
+------------------------------------------+
|           autom8_asana SDK               |
|  +------------------------------------+  |
|  | Business Model Layer               |  |
|  | Business > Unit > Offer            |  |
|  | Contact, Address, Hours            |  |
|  | 127+ Custom Field Descriptors      |  |
|  +------------------------------------+  |
|  +------------------------------------+  |
|  | Persistence Layer                  |  |
|  | SaveSession (Unit of Work)         |  |
|  | Change Tracking, Batch Operations  |  |
|  +------------------------------------+  |
|  +------------------------------------+  |
|  | Detection Layer                    |  |
|  | 5-Tier Entity Type Detection       |  |
|  | Project Membership Registry        |  |
|  +------------------------------------+  |
+------------------------------------------+
                    |
                    | Asana REST API
                    v
+------------------------------------------+
|           Asana Platform                 |
|  Tasks, Projects, Custom Fields          |
|  Subtasks, Sections, Tags                |
+------------------------------------------+
```

---

## Why This Architecture

1. **Zero infrastructure overhead**: No database to manage, scale, or backup
2. **Free admin interface**: Asana's UI provides CRUD for operators without custom tooling
3. **API-first design**: Every operation is available via REST API
4. **Flexible schema**: Custom fields allow entity evolution without migrations
5. **Built-in collaboration**: Asana's commenting, assignments, and history come free

---

## Implications for Development

When working with autom8_asana:

- **Entities are Tasks**: Every Business, Contact, Unit, Offer is an Asana Task under the hood
- **Fields are Custom Fields**: Typed properties map to Asana custom field definitions
- **Hierarchy uses Subtasks**: Holders contain children as subtask relationships
- **Detection uses Projects**: Entity type determined by which projects a task belongs to
- **Persistence uses Asana API**: SaveSession batches changes to Asana, not a SQL database

---

## Related

- [context.md](context.md) - SDK extraction context
- [entity-lifecycle.md](../autom8-asana-business/entity-lifecycle.md) - How entities use this paradigm
- [detection.md](../autom8-asana-business/detection.md) - Project-based type detection
- [savesession.md](../autom8-asana-business/savesession.md) - Persistence patterns
```
