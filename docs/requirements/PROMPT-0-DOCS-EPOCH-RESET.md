# Orchestrator Initialization: Documentation Epoch Reset Initiative

> **Initiative Type**: Major Documentation Overhaul
> **Target Repository**: autom8_asana
> **Created**: 2025-12-17
> **Triggered By**: 4-agent deep analysis revealing critical documentation-reality mismatch

---

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`documentation`** — PRD/TDD/ADR templates, workflow pipeline, quality gates
  - Activates when: Creating/reviewing PRD, TDD, ADR, or Test Plan

- **`standards`** — Tech stack decisions, code conventions, repository structure
  - Activates when: Writing code, choosing libraries, organizing files

- **`10x-workflow`** — Agent coordination, session protocol, quality gates
  - Activates when: Planning phases, coordinating handoffs, checking quality criteria

- **`prompting`** — Agent invocation patterns, workflow examples
  - Activates when: Invoking agents, structuring prompts

- **`autom8-asana-domain`** — SDK patterns, SaveSession, Asana resources
  - Activates when: Understanding SDK architecture, implementation details

- **`autom8-asana-business`** — Business entities, holders, detection, custom fields
  - Activates when: Understanding the CRM data model and business logic

**How Skills Work**: Skills load automatically based on your current task. When you need template formats, the `documentation` skill activates. When you need coding conventions, the `standards` skill activates.

---

## Your Role: Orchestrator

You coordinate a 4-agent development workflow. You plan, delegate, coordinate, and verify—you do not implement directly.

## Your Specialist Agents

| Agent | Invocation | Responsibility |
|-------|------------|----------------|
| **Requirements Analyst** | `@requirements-analyst` | Documentation requirements, acceptance criteria, scope boundaries |
| **Architect** | `@architect` | Information architecture, document structure, narrative design |
| **Principal Engineer** | `@principal-engineer` | Content authoring, skill file updates, cross-reference maintenance |
| **QA/Adversary** | `@qa-adversary` | Documentation accuracy validation, completeness review, onboarding testing |

---

## The Mission: Reset Documentation to Match Production Reality

The autom8_asana documentation describes "Day 30" of the project while the codebase has matured to "Day 300." This documentation-reality mismatch causes AI agents and human developers to fundamentally misunderstand the project's maturity, capabilities, and purpose.

### Why This Initiative?

- **AI Agents Are Miscontextualized**: Claude Code operating with current documentation treats a production-grade SDK as a prototype, leading to inappropriate recommendations and missed capabilities
- **Onboarding Is Broken**: New developers reading the docs expect a simple API wrapper and discover a full CRM platform with sophisticated patterns
- **The Core Paradigm Is Undocumented**: Asana-as-database (the fundamental architectural insight) appears nowhere in documentation
- **Capability Discovery Fails**: 127+ custom fields, 7+ entity types, cascade logic, resolution strategies—none of this is discoverable from docs

### What Triggered This

Four specialist agents (2 Engineers, 2 Architects) performed deep codebase analysis and produced unanimous findings:

**What Documentation Claims:**
| Claim | Source |
|-------|--------|
| "Prototype" status | context.md, PROJECT_CONTEXT.md |
| "~0% test coverage" | context.md (line 62) |
| "Pure API wrapper with no business logic" | Multiple skill files |
| "4 stub entity types" | entity-reference.md |

**What Actually Exists:**
| Reality | Evidence |
|---------|----------|
| Production-grade SDK | 95 ADRs, 32 TDDs documenting mature decisions |
| 68,358 lines of test code | 129 test files across all modules |
| Full CRM platform | 150+ custom fields, cascade logic, resolution strategies |
| Only 3 stubs remaining | AssetEdit alone is 681 lines with 11 typed fields |

---

### Current State

**.claude Skills Architecture (Outdated)**:
- `autom8-asana-domain/context.md` claims "Prototype" stage and "~0% test coverage"
- `autom8-asana-business/entity-reference.md` lists "4 stub entity types" when only 3 remain
- No documentation of the Asana-as-database paradigm
- Business model docs describe 7 entity types but understate their sophistication
- PROJECT_CONTEXT.md still references prototype status

**What Actually Exists (Codebase Evidence)**:
- 95 ADR files in `/docs/decisions/`
- 32 TDD files in `/docs/design/`
- 129 test files totaling 68,358 lines of test code
- 7,733 lines in `/src/autom8_asana/models/business/` alone
- AssetEdit: 681 lines, 11 typed fields (not a "stub")
- 5-tier detection system (TDD-DETECTION, ADR-0093/0094/0095)
- SaveSession with dependency graphs, change tracking, batch execution

**What's Missing**:

```
# The core paradigm that makes this project unique:

ASANA-AS-DATABASE ARCHITECTURE

Tasks     = Entity rows (Business, Contact, Unit, Offer, etc.)
Fields    = Typed columns (127+ custom fields with cascade logic)
Subtasks  = Relationships (holders containing child entities)
Projects  = Tables/collections (entity type registries)
Asana UI  = Free admin interface (built-in CRUD for operators)

# This is nowhere in the documentation.
```

---

### Project Reality Profile

| Attribute | Documented Value | Actual Value |
|-----------|------------------|--------------|
| Project Stage | Prototype | Production-Grade SDK |
| Test Coverage | ~0% | 68,358 lines / 129 files |
| Entity Types | 4 stubs | 7 full implementations (3 stubs: DNA, Reconciliations, Videography) |
| Custom Fields | "some fields" | 127+ typed fields with descriptors |
| Business Logic | "None - pure API wrapper" | Full CRM with cascade, resolution, detection |
| ADRs | "Some documented" | 95 architectural decisions |
| TDDs | "Some documented" | 32 technical design documents |

---

### Target Narrative

The documentation should convey:

```
autom8_asana: A Production CRM Platform Built on Asana

                    +---------------------------+
                    |      Asana Platform       |
                    |  (Tasks, Projects, Fields)|
                    +---------------------------+
                              |
                              | Asana REST API
                              v
    +---------------------------------------------------+
    |              autom8_asana SDK                      |
    |  +--------------------------------------------+   |
    |  |  Typed Entity Layer                        |   |
    |  |  Business > Unit > Offer                   |   |
    |  |  Contact, Address, Hours                   |   |
    |  |  127+ Custom Field Descriptors             |   |
    |  +--------------------------------------------+   |
    |  +--------------------------------------------+   |
    |  |  Persistence Layer                         |   |
    |  |  SaveSession (Unit of Work)                |   |
    |  |  Change Tracking, Dependency Graphs        |   |
    |  |  Batch Operations, Action Executors        |   |
    |  +--------------------------------------------+   |
    |  +--------------------------------------------+   |
    |  |  Detection & Resolution                    |   |
    |  |  5-Tier Entity Detection                   |   |
    |  |  Field Cascade Logic                       |   |
    |  |  Conflict Resolution Strategies            |   |
    |  +--------------------------------------------+   |
    +---------------------------------------------------+
                              |
                              v
                    +---------------------------+
                    |   Consumer Applications   |
                    |   (autom8 platform, etc.) |
                    +---------------------------+
```

---

### Key Constraints

- **No Code Changes**: This initiative touches documentation only; codebase remains unchanged
- **Preserve Existing Structure**: The skills architecture is sound; content needs updating, not restructuring
- **Maintain Accuracy**: All claims must be verifiable against current codebase state
- **Progressive Disclosure**: Keep the layered skill loading approach; don't flatten into monolithic docs
- **Cross-Reference Integrity**: All internal links must remain valid post-update
- **Living Documentation Compatibility**: Updates must integrate with existing /docs/INDEX.md registry

---

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Update PROJECT_CONTEXT.md to reflect production status | Must |
| Update context.md with accurate test coverage and maturity | Must |
| Document Asana-as-database paradigm in architectural context | Must |
| Update entity-reference.md with actual entity status (3 stubs, not 4) | Must |
| Document the 127+ custom fields with categorization | Must |
| Document cascade logic and resolution strategies | Must |
| Add "What This Project Actually Is" section to key entry points | Must |
| Update detection system documentation to reflect 5-tier implementation | Should |
| Create visual diagrams of entity hierarchy and relationships | Should |
| Add "Quick Reality Check" tables comparing old claims to actual state | Should |
| Document SaveSession sophistication (dependency graphs, batch execution) | Should |
| Update all "prototype" references to accurate status | Could |

---

### Success Criteria

1. **PROJECT_CONTEXT.md** accurately describes production-grade status
2. **context.md** shows real test metrics (68K+ lines, 129 files)
3. **Asana-as-database paradigm** is documented and discoverable within 2 clicks from CLAUDE.md
4. **Entity status** accurately reflects 7 implementations with 3 stubs
5. **Custom field count** documented as 127+ with categorization
6. **Cascade/resolution logic** has dedicated documentation section
7. **New developer** reading docs understands this is a CRM platform, not a simple wrapper
8. **AI agents** receive accurate context about project maturity and capabilities

### Validation Criteria

An external agent given only the updated documentation should be able to answer:

1. "Is this a prototype or production system?" — Answer: Production-grade SDK
2. "How much test coverage exists?" — Answer: 68K+ lines across 129 files
3. "What is Asana-as-database?" — Answer: Clear explanation of the paradigm
4. "How many entity types and which are stubs?" — Answer: 7 types, 3 stubs
5. "What makes this more than an API wrapper?" — Answer: Cascade logic, detection, resolution, typed fields

---

### Performance Targets

| Metric | Current State | Target State |
|--------|---------------|--------------|
| Documentation accuracy | ~30% (major claims false) | 100% (all claims verifiable) |
| Paradigm discoverability | 0 (undocumented) | 2 clicks from CLAUDE.md |
| Entity status accuracy | 57% (4/7 stubs claimed) | 100% (3/7 stubs actual) |
| Test coverage documentation | 0% accurate | 100% accurate |
| Onboarding comprehension | Misleading | Accurate |

---

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | Comprehensive audit of all outdated documentation with specific line-level citations |
| **2: Requirements** | Requirements Analyst | PRD-DOCS-EPOCH-RESET with acceptance criteria per document |
| **3: Architecture** | Architect | Information architecture TDD: document hierarchy, narrative flow, cross-reference map |
| **4: Implementation P1** | Principal Engineer | Core updates: PROJECT_CONTEXT.md, context.md, entity-reference.md |
| **5: Implementation P2** | Principal Engineer | New content: Asana-as-database documentation, custom field catalog |
| **6: Implementation P3** | Principal Engineer | Cross-reference updates, INDEX.md sync, link validation |
| **7: Validation** | QA/Adversary | Documentation accuracy testing, onboarding simulation, agent comprehension test |

---

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rule**: Never execute without explicit confirmation.

---

## Discovery Phase: What Must Be Explored

Before requirements can be finalized, the **Requirements Analyst** must explore:

### Documentation Audit

| File/Area | Questions to Answer |
|-----------|---------------------|
| `.claude/PROJECT_CONTEXT.md` | What specific claims are outdated? Line numbers? |
| `.claude/skills/autom8-asana-domain/context.md` | Which metrics are wrong? What's the actual state? |
| `.claude/skills/autom8-asana-business/entity-reference.md` | Which entities are marked as stubs that aren't? |
| `.claude/skills/autom8-asana-domain/SKILL.md` | Does the activation trigger text mislead about capabilities? |
| `.claude/CLAUDE.md` | Does the entry point give accurate first impression? |

### Codebase Reality Verification

| Resource/System | Questions to Answer |
|-----------------|---------------------|
| `/docs/decisions/ADR*.md` | Exact count? What decisions are documented? |
| `/docs/design/TDD*.md` | Exact count? What designs are documented? |
| `/tests/**/*.py` | Line count verification? Module breakdown? |
| `/src/autom8_asana/models/business/*.py` | Entity implementation status? Field counts? |
| Custom field definitions | Where defined? How many per entity? |
| Cascade logic | Where implemented? What patterns? |

### Gap Analysis

| Area | Questions |
|------|-----------|
| Asana-as-database | Where should this be documented? What format? |
| Entity maturity | What distinguishes "stub" from "implemented"? |
| Test sophistication | What testing patterns exist beyond line count? |
| SaveSession depth | What advanced features are undocumented? |

---

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins, the following questions need answers:

### Scope Questions

1. **Stub definition**: What criteria determine "stub" vs "implemented"? (line count? field count? test coverage?)
2. **Documentation depth**: How much implementation detail belongs in skills vs. separate reference docs?
3. **Historical preservation**: Should we maintain an "evolution" section showing old claims vs new reality?

### Strategic Questions

4. **Audience priority**: Is the primary audience AI agents, human developers, or both equally?
5. **Paradigm placement**: Should Asana-as-database be a standalone document or woven throughout?
6. **Visual assets**: Should we create diagrams, or is ASCII art sufficient?

### Process Questions

7. **Validation method**: How do we test that an external agent correctly understands the updated docs?
8. **Rollback plan**: If updates cause issues, what's the recovery strategy?

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Incomplete audit misses outdated content | Medium | High | Systematic file-by-file review with codebase verification |
| Updates break existing cross-references | Medium | Medium | Link validation script in Session 6 |
| Over-documentation creates maintenance burden | Low | Medium | Stick to progressive disclosure; update existing files |
| Accuracy claims are still wrong post-update | Low | High | QA phase includes codebase verification of every claim |
| New narrative is confusing or unhelpful | Low | Medium | Onboarding simulation with fresh context test |

---

## Key Stakeholders

| Stakeholder | What They Need |
|-------------|----------------|
| **Claude Code (AI agents)** | Accurate context loading for appropriate recommendations |
| **Human developers** | Truthful onboarding that matches what they'll find in code |
| **Project maintainers** | Documentation that requires minimal ongoing correction |
| **Future initiatives** | Solid foundation for additional documentation work |

---

## Artifacts to Update

### Primary (Must Update)

| File | Current Issue | Target State |
|------|---------------|--------------|
| `.claude/PROJECT_CONTEXT.md` | "Prototype" claim | "Production-grade" with evidence |
| `.claude/skills/autom8-asana-domain/context.md` | "~0% test coverage" | "68K+ lines / 129 files" |
| `.claude/skills/autom8-asana-business/entity-reference.md` | "4 stubs" | "3 stubs: DNA, Reconciliations, Videography" |

### Secondary (Should Update)

| File | Current Issue | Target State |
|------|---------------|--------------|
| `.claude/CLAUDE.md` | No paradigm mention | Link to Asana-as-database explanation |
| `.claude/skills/autom8-asana-domain/SKILL.md` | "Pure API wrapper" framing | Accurate capability description |
| `/docs/INDEX.md` | May not reflect doc updates | Synchronized with all changes |

### New Content (To Create)

| File | Purpose |
|------|---------|
| `.claude/skills/autom8-asana-domain/paradigm.md` OR section in existing file | Asana-as-database architectural explanation |
| Custom field catalog (location TBD) | Comprehensive field documentation |

---

## Your First Task

Confirm understanding by:

1. Summarizing the documentation epoch reset goal in 2-3 sentences
2. Listing the 7 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step before requirements
4. Confirming which files must be audited for outdated content
5. Listing which open questions you need answered before Session 2

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

# Session Trigger Prompts

## Session 1: Discovery

```markdown
Begin Session 1: Documentation Accuracy Audit

Work with the @requirements-analyst agent to audit all .claude documentation and verify against codebase reality.

**Goals:**
1. Identify every file containing outdated claims (prototype status, test coverage, entity stubs)
2. Document specific line numbers and incorrect statements
3. Verify codebase reality for each claim (actual test count, entity status, feature implementation)
4. Catalog all references to "prototype" or "~0% coverage"
5. Map the absence of Asana-as-database documentation
6. Identify all cross-references that may need updating
7. Produce prioritized list of updates needed

**Files to Analyze:**
- `.claude/PROJECT_CONTEXT.md` — Status claims, test coverage
- `.claude/skills/autom8-asana-domain/context.md` — Prototype claims, coverage metrics
- `.claude/skills/autom8-asana-business/entity-reference.md` — Stub claims
- `.claude/CLAUDE.md` — Entry point accuracy
- All SKILL.md files — Activation trigger accuracy

**Codebase to Verify Against:**
- `/docs/decisions/ADR*.md` — Count and categorize
- `/docs/design/TDD*.md` — Count and categorize
- `/tests/**/*.py` — Line counts, file counts, module breakdown
- `/src/autom8_asana/models/business/*.py` — Entity implementation status

**Deliverable:**
A discovery document with:
- Table of incorrect claims with file:line citations
- Codebase verification for each claim
- Prioritized update list
- Identified gaps (e.g., missing paradigm documentation)
- Cross-reference dependency map
- Recommended update sequence

Create the analysis plan first. I'll review before you execute.
```

## Session 2: Requirements

```markdown
Begin Session 2: Documentation Update Requirements

Work with the @requirements-analyst agent to create PRD-DOCS-EPOCH-RESET.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Define specific acceptance criteria for each file update
2. Define content requirements for Asana-as-database documentation
3. Define accuracy verification criteria
4. Define cross-reference validation requirements
5. Define onboarding test scenarios
6. Define agent comprehension test scenarios
7. Prioritize updates using MoSCoW

**Key Questions to Address:**
- What makes documentation "accurate enough"?
- What verification proves each claim is correct?
- How do we test agent comprehension?
- What's the minimum viable update set?

**PRD Organization:**
- FR-ACCURACY-*: Claim correction requirements
- FR-PARADIGM-*: Asana-as-database documentation requirements
- FR-ENTITY-*: Entity status accuracy requirements
- FR-METRICS-*: Test coverage and maturity metrics requirements
- FR-CROSSREF-*: Cross-reference integrity requirements
- NFR-*: Maintainability, discoverability requirements

Create the plan first. I'll review before you execute.
```

## Session 3: Architecture

```markdown
Begin Session 3: Information Architecture Design

Work with the @architect agent to design the documentation structure and narrative flow.

**Prerequisites:**
- PRD-DOCS-EPOCH-RESET approved

**Goals:**
1. Design information hierarchy for Asana-as-database paradigm
2. Design update strategy for existing files (in-place vs. restructure)
3. Design cross-reference architecture
4. Design discoverability paths (2 clicks to paradigm from CLAUDE.md)
5. Design progressive disclosure layers
6. Design validation test architecture

**Required Decisions:**
- TDD-DOCS-EPOCH-RESET: Overall documentation update design
- ADR-PARADIGM-LOCATION: Where Asana-as-database documentation lives
- ADR-STUB-CRITERIA: Formal definition of "stub" vs "implemented"
- ADR-METRIC-SOURCES: How to maintain accurate test metrics

**Structure Considerations:**

```
.claude/
    CLAUDE.md           <-- Entry point (add paradigm link)
    PROJECT_CONTEXT.md  <-- Reality update
    skills/
        autom8-asana-domain/
            context.md      <-- Metrics update
            paradigm.md     <-- NEW: Asana-as-database
            SKILL.md        <-- Framing update
        autom8-asana-business/
            entity-reference.md  <-- Stub status update
```

Create the plan first. I'll review before you execute.
```

## Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - Core Corrections

Work with the @principal-engineer agent to update core documentation files.

**Prerequisites:**
- PRD-DOCS-EPOCH-RESET approved
- TDD-DOCS-EPOCH-RESET approved

**Phase 1 Scope:**
1. Update PROJECT_CONTEXT.md with production status
2. Update context.md with accurate test metrics
3. Update entity-reference.md with correct stub count
4. Remove or update all "prototype" references in updated files
5. Add "Documentation Updated" header with date and reason
6. Verify all claims against codebase before finalizing

**Hard Constraints:**
- Every metric must be verifiable with a command or file reference
- No aspirational language ("will be", "planned to")
- All claims must reflect current state only

**Explicitly OUT of Phase 1:**
- Asana-as-database paradigm documentation (Phase 2)
- Custom field catalog (Phase 2)
- Cross-reference updates (Phase 3)
- Link validation (Phase 3)

Create the plan first. I'll review before you execute.
```

## Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - New Content

Work with the @principal-engineer agent to create Asana-as-database documentation.

**Prerequisites:**
- Phase 1 complete and verified

**Phase 2 Scope:**
1. Create paradigm.md (or designated location per ADR)
2. Document Asana-as-database concept with clear explanation
3. Document the mapping: Tasks=Rows, Fields=Columns, Subtasks=Relations, Projects=Tables
4. Add visual diagram (ASCII) of the architecture
5. Document business implications and use cases
6. Link from CLAUDE.md to paradigm documentation

**Integration Points:**
- Link from PROJECT_CONTEXT.md
- Link from SKILL.md entry points
- Cross-reference in entity documentation

Create the plan first. I'll review before you execute.
```

## Session 6: Implementation Phase 3

```markdown
Begin Session 6: Implementation Phase 3 - Cross-Reference & Validation

Work with the @principal-engineer agent to ensure cross-reference integrity.

**Prerequisites:**
- Phase 2 complete and verified

**Phase 3 Scope:**
1. Validate all internal documentation links
2. Update /docs/INDEX.md with any new documents
3. Verify SKILL.md activation triggers are accurate
4. Ensure all "See also" and "Related" sections are current
5. Add "Last verified" timestamps where appropriate
6. Create simple validation script if useful for ongoing maintenance

**Validation Checklist:**
- All .md internal links resolve
- INDEX.md reflects current document state
- No orphaned references to old content
- Consistent terminology across updated docs

Create the plan first. I'll review before you execute.
```

## Session 7: Validation

```markdown
Begin Session 7: Documentation Validation

Work with the @qa-adversary agent to validate the updated documentation.

**Prerequisites:**
- All implementation phases complete

**Goals:**

**Part 1: Accuracy Validation**
- Verify every metric claim against codebase (test counts, ADR counts, entity status)
- Verify Asana-as-database description matches implementation
- Verify entity stub status matches code reality
- Verify all internal links resolve

**Part 2: Comprehension Testing**
- Simulate fresh agent context: Given only updated docs, can agent correctly answer:
  1. "Is this a prototype?" (Expected: No, production-grade)
  2. "What's the test coverage?" (Expected: 68K+ lines)
  3. "What is Asana-as-database?" (Expected: Clear paradigm explanation)
  4. "Which entities are stubs?" (Expected: DNA, Reconciliations, Videography)

**Part 3: Onboarding Simulation**
- Read CLAUDE.md -> Can you find paradigm within 2 clicks?
- Read PROJECT_CONTEXT.md -> Is first impression accurate?
- Read entity-reference.md -> Is entity status clear?

**Part 4: Regression Check**
- No broken links introduced
- No conflicting claims between documents
- INDEX.md synchronized

Create the plan first. I'll review before you execute.
```

---

# Context Gathering Checklist

Before starting, gather:

**Documentation State:**
- [ ] `.claude/PROJECT_CONTEXT.md` — Current status claims
- [ ] `.claude/skills/autom8-asana-domain/context.md` — Test coverage claims
- [ ] `.claude/skills/autom8-asana-business/entity-reference.md` — Entity stub claims
- [ ] All files containing "prototype" or "~0%" strings

**Codebase Reality:**
- [ ] `find docs/decisions -name "ADR*.md" | wc -l` — ADR count
- [ ] `find docs/design -name "TDD*.md" | wc -l` — TDD count
- [ ] `find tests -name "*.py" | wc -l` — Test file count
- [ ] `wc -l tests/**/*.py | tail -1` — Test line count
- [ ] `/src/autom8_asana/models/business/*.py` — Entity implementation status
- [ ] Custom field definitions per entity

**Cross-References:**
- [ ] All "See also" sections in .claude docs
- [ ] All relative links in skill files
- [ ] /docs/INDEX.md current state

**Validation Baseline:**
- [ ] Current agent comprehension (ask test questions before updates)
- [ ] Current link validity state
- [ ] Current INDEX.md synchronization state
