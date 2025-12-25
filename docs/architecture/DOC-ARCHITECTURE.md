# Documentation Information Architecture

**Version**: 1.0
**Date**: 2025-12-24
**Status**: Proposed
**Author**: Information Architect Agent

---

## Executive Summary

This document defines the target information architecture for autom8_asana documentation based on SOLID principles. The architecture addresses critical findings from the documentation synthesis audit:

- **18 cache-related files** with 60% redundancy → **3 canonical references**
- **21 command/skill-ref pairs** with 40-60% overlap → **Thin commands + focused skills**
- **12 fragmented glossaries** → **1 hierarchical glossary**
- **6 responsibilities in CLAUDE.md** → **Single-purpose routing document**

**Target Outcomes**:
- 30% reduction in documentation volume (~1M saved)
- 30-second findability test: 40% → 85% pass rate
- Single source of truth for all concepts
- SOLID score: 5.0/10 → 8.5/10

---

## SOLID Principles Applied to Documentation

### Single Responsibility Principle (SRP)
**One document, one purpose, one audience, one reason to change.**

- **Entry documents** (CLAUDE.md, README.md): Pure routing logic only
- **Reference documents**: Canonical definitions, no implementation details
- **Design documents** (TDDs): Design decisions only, extract implementation guides
- **Requirement documents** (PRDs): Requirements only, no design rationale
- **Skills**: Domain context for agent execution, no command invocation patterns
- **Commands**: Actionable prompts only (20-50 lines), reference skills for details

### Open/Closed Principle (OCP)
**Open for extension, closed for modification.**

- **Single hierarchical glossary**: New terms added as new entries, existing entries never change
- **ADR immutability**: New decisions = new files, old ADRs never modified
- **Reference docs**: Abstract concepts, specific implementations reference them
- **Template-based structures**: New documents follow templates without restructuring

### Liskov Substitution Principle (LSP)
**Documents of the same type are interchangeable.**

- **Consistent frontmatter**: All PRDs, TDDs, ADRs follow identical metadata schemas
- **Template compliance**: All commands use YAML frontmatter, all skills use consistent structure
- **Status taxonomy standardization**: Unified status values (Draft, Active, Implemented, Superseded)

### Interface Segregation Principle (ISP)
**Readers consume only what they need.**

- **Focused documents**: No monoliths >800 lines
- **Progressive disclosure**: Simple → detailed via cross-references
- **Audience-specific paths**: Onboarding, debugging, contributing, operating
- **Split responsibilities**: 2196-line TDD → 500-line design + reference docs + migration guide

### Dependency Inversion Principle (DIP)
**Documents depend on abstractions, not concretions.**

- **Concept-based references**: "@SaveSession skill" not "skills/autom8-asana/persistence.md:450"
- **Abstract roles**: "Requirements agent" not "requirements-analyst"
- **Canonical abstractions**: Create REF-* documents for repeated patterns (entity lifecycle, batch operations, etc.)
- **Link resolver**: Maps concepts to current locations (prevents link rot)

---

## Target Directory Structure

```
autom8_asana/
├── .claude/                                    # Agent execution context
│   ├── CLAUDE.md                              # Pure router (50 lines) ← THIN
│   ├── ENTRY.md                               # NEW: Entry point decision logic
│   ├── ARCHITECTURE.md                        # NEW: Skills/agents architecture
│   ├── FAQ.md                                 # NEW: Quick reference
│   ├── COMMAND_REGISTRY.md                    # Auto-generated from frontmatter
│   ├── GLOSSARY.md                            # → Pointer to /docs/reference/GLOSSARY.md
│   ├── PROJECT_CONTEXT.md                     # High-level overview only
│   ├── ACTIVE_TEAM                            # Current team pointer
│   │
│   ├── agents/                                # Agent definitions
│   │   ├── doc-auditor.md
│   │   ├── information-architect.md
│   │   ├── tech-writer.md
│   │   └── doc-reviewer.md
│   │
│   ├── commands/                              # Actionable prompts (20-50 lines each)
│   │   ├── 10x.md                             # Team switching
│   │   ├── docs.md                            # Doc team
│   │   ├── task.md                            # Task execution
│   │   ├── sprint.md                          # Sprint planning
│   │   ├── hotfix.md                          # Hotfix workflow
│   │   └── ... (21 total)
│   │
│   ├── skills/                                # Domain context for agents
│   │   ├── 10x-ref/
│   │   │   └── skill.md                       # Full reference (200-400 lines)
│   │   ├── docs-ref/
│   │   │   └── skill.md
│   │   ├── documentation/
│   │   │   ├── SKILL.md                       # Router to templates/
│   │   │   ├── workflow.md
│   │   │   └── templates/
│   │   │       ├── prd.md
│   │   │       ├── tdd.md
│   │   │       ├── adr.md
│   │   │       └── test-plan.md
│   │   ├── standards/
│   │   │   ├── SKILL.md                       # Router only
│   │   │   ├── code-conventions.md
│   │   │   ├── testing-standards.md
│   │   │   └── tech-stack.md
│   │   ├── initiative-scoping/
│   │   │   ├── SKILL.md
│   │   │   ├── session-0-protocol.md
│   │   │   └── session-minus-1-protocol.md
│   │   ├── team-development/
│   │   │   ├── SKILL.md
│   │   │   └── TEAMS.md                       # NEW: Canonical team rosters
│   │   └── ... (27 skills, no duplicated command content)
│   │
│   └── sessions/                              # Session tracking
│       └── session-YYYYMMDD-HHMMSS-*/
│
├── docs/                                       # Formal documentation
│   ├── INDEX.md                               # Registry + navigation
│   │
│   ├── reference/                             # CANONICAL SINGLE SOURCES OF TRUTH
│   │   ├── README.md                          # Reference index
│   │   ├── GLOSSARY.md                        # UNIFIED: All terms (300 lines)
│   │   │
│   │   ├── REF-entity-type-table.md           # ✅ Already exists
│   │   ├── REF-custom-field-catalog.md        # ✅ Already exists
│   │   │
│   │   ├── REF-cache-architecture.md          # NEW: Cache system overview
│   │   ├── REF-cache-staleness-detection.md   # ✅ Already exists
│   │   ├── REF-cache-ttl-strategy.md          # ✅ Already exists
│   │   ├── REF-cache-provider-protocol.md     # ✅ Already exists
│   │   │
│   │   ├── REF-entity-lifecycle.md            # NEW: Define→Detect→Populate→Navigate→Persist
│   │   ├── REF-savesession-lifecycle.md       # NEW: Track→Modify→Commit→Validate
│   │   ├── REF-detection-tiers.md             # NEW: 5-tier detection system
│   │   ├── REF-batch-operations.md            # NEW: Chunking, parallelization, error handling
│   │   ├── REF-asana-hierarchy.md             # NEW: Workspace→Project→Section→Task→Subtask
│   │   ├── REF-workflow-phases.md             # NEW: Requirements→Design→Implementation→Testing
│   │   └── REF-command-decision-tree.md       # NEW: When to use /task vs /sprint vs /hotfix
│   │
│   ├── requirements/                          # PRDs (400-600 lines each, no design details)
│   │   ├── PRD-0001-sdk-extraction.md
│   │   ├── PRD-0002-intelligent-caching.md
│   │   ├── ... (44 PRDs)
│   │   └── [Cache PRDs reference docs/reference/REF-cache-*.md]
│   │
│   ├── design/                                # TDDs (500-800 lines each, no reference material)
│   │   ├── TDD-0001-sdk-architecture.md
│   │   ├── TDD-0002-models-pagination.md
│   │   ├── ... (50 TDDs)
│   │   └── [Cache TDDs reference docs/reference/REF-cache-*.md]
│   │
│   ├── decisions/                             # ADRs (immutable, one decision per file)
│   │   ├── ADR-0001-protocol-extensibility.md
│   │   ├── ... (135 ADRs)
│   │   └── [Cache ADRs remain as-is]
│   │
│   ├── testing/                               # Test plans and validation reports
│   │   ├── TP-0001-sdk-phase1-parity.md
│   │   └── ... (28 files)
│   │
│   ├── guides/                                # User-facing how-to guides
│   │   ├── concepts.md                        # Core SDK concepts
│   │   ├── quickstart.md                      # Get started in 5 minutes
│   │   ├── workflows.md                       # Common task recipes
│   │   ├── patterns.md                        # Best practices
│   │   ├── save-session.md                    # SaveSession guide
│   │   ├── sdk-adoption.md                    # Migration guide
│   │   └── autom8-migration.md
│   │
│   ├── runbooks/                              # Operational troubleshooting
│   │   ├── RUNBOOK-cache-troubleshooting.md
│   │   ├── RUNBOOK-savesession-debugging.md
│   │   └── RUNBOOK-detection-troubleshooting.md
│   │
│   ├── migration/                             # Migration guides for breaking changes
│   │   └── MIGRATION-ASYNC-METHOD.md
│   │
│   ├── initiatives/                           # PROMPT-0, PROMPT-MINUS-1 session plans
│   │   ├── PROMPT-0-*.md
│   │   └── PROMPT-MINUS-1-*.md
│   │
│   ├── analysis/                              # Discovery, gap analysis, impact analysis
│   │   ├── DISCOVERY-*.md
│   │   ├── GAP-ANALYSIS-*.md
│   │   └── IMPACT-*.md
│   │
│   ├── planning/                              # Sprint decompositions
│   │   └── sprints/
│   │
│   ├── reports/                               # Initiative completion reports
│   │   └── REPORT-*.md
│   │
│   ├── architecture/                          # Architecture specifications
│   │   ├── DOC-ARCHITECTURE.md                # THIS FILE
│   │   └── [Future architecture specs]
│   │
│   ├── audits/                                # Documentation audits
│   │   ├── AUDIT-doc-synthesis.md
│   │   └── [Future audits]
│   │
│   ├── validation/                            # Validation reports
│   │   └── VP-*.md
│   │
│   └── .archive/                              # Completed/superseded documentation
│       ├── initiatives/2025-Q4/               # Completed Q4 initiatives
│       ├── discovery/                         # Archived discovery docs
│       ├── validation/                        # Point-in-time validation
│       ├── historical/                        # Other completed work
│       └── architecture/                      # Superseded architecture
│
└── runbooks/atuin/                            # Atuin desktop runbooks
    └── ... (6 files)
```

---

## File Naming Conventions

### Commands (.claude/commands/)
- **Pattern**: `{verb}.md` or `{workflow}.md`
- **Examples**: `task.md`, `sprint.md`, `hotfix.md`, `10x.md`
- **Length**: 20-50 lines
- **Frontmatter**: YAML with description, argument-hint, allowed-tools

### Skills (.claude/skills/)
- **Pattern**: `{domain}-ref/skill.md` or `{domain}/SKILL.md`
- **Examples**: `10x-ref/skill.md`, `documentation/SKILL.md`
- **Length**: 200-400 lines for `-ref` skills, <100 lines for routers
- **Purpose**: Domain context, NOT command duplication

### PRDs (docs/requirements/)
- **Pattern**: `PRD-{NNNN}-{slug}.md` or `PRD-{TOPIC}-{slug}.md`
- **Examples**: `PRD-0024-custom-field-remediation.md`, `PRD-CACHE-INTEGRATION.md`
- **Length**: 400-600 lines (requirements only, no design)
- **Status**: Draft, Active, Approved, Implemented, Superseded

### TDDs (docs/design/)
- **Pattern**: `TDD-{NNNN}-{slug}.md` or `TDD-{TOPIC}-{slug}.md`
- **Examples**: `TDD-0030-custom-field-remediation.md`, `TDD-CACHE-INTEGRATION.md`
- **Length**: 500-800 lines (design decisions only, reference extracted)
- **Status**: Draft, Active, Ready, Implemented, Superseded

### ADRs (docs/decisions/)
- **Pattern**: `ADR-{NNNN}-{slug}.md`
- **Examples**: `ADR-0135-next-decision.md`
- **Length**: 200-400 lines
- **Immutability**: Never modify after approval, use "Superseded by" references

### Reference Docs (docs/reference/)
- **Pattern**: `REF-{concept}.md`
- **Examples**: `REF-entity-lifecycle.md`, `REF-cache-architecture.md`
- **Length**: 200-400 lines
- **Purpose**: Single source of truth for cross-cutting concepts
- **Status**: Living documents, updated as system evolves

### Initiatives (docs/initiatives/)
- **Pattern**: `PROMPT-{N}-{slug}.md` where N ∈ {-1, 0}
- **Examples**: `PROMPT-0-AUTOMATION-LAYER.md`, `PROMPT-MINUS-1-CACHE-PERFORMANCE-META.md`
- **Purpose**: Session planning documents
- **Archival**: Move to `.archive/initiatives/YYYY-QN/` when complete

### Analysis (docs/analysis/)
- **Pattern**: `{TYPE}-{slug}.md` where TYPE ∈ {DISCOVERY, GAP-ANALYSIS, IMPACT}
- **Examples**: `DISCOVERY-PROCESS-PIPELINE.md`, `GAP-ANALYSIS-CACHE-UTILIZATION.md`
- **Purpose**: Investigation and analysis artifacts
- **Lifecycle**: Reference from PRDs/TDDs, archive when superseded

---

## Content Boundaries (Single Responsibility)

### Document Type Responsibilities

| Type | Contains | Does NOT Contain |
|------|----------|------------------|
| **Command** | Actionable prompt (20-50 lines), context injection, task specification | Team rosters, examples, workflow patterns, reference material |
| **Skill** | Domain context, reference material, patterns | Command invocation logic, team rosters (except TEAMS.md) |
| **PRD** | Requirements, user stories, acceptance criteria, success metrics | Design decisions, implementation details, architecture rationale |
| **TDD** | Design decisions, component interactions, API contracts | Requirements justification, implementation guides, reference material |
| **ADR** | Single architectural decision, context, consequences | Multiple decisions, implementation details, usage examples |
| **Reference** | Canonical definition of concept, algorithm, or pattern | Implementation details, project-specific decisions |
| **Guide** | Task-oriented how-to for end users | Architecture details, design rationale, API reference |
| **Runbook** | Operational troubleshooting steps | Architecture explanations, design decisions |

### Specific Violations to Fix

#### CLAUDE.md (Currently 6 responsibilities → 1)
**Current** (150 lines):
- Entry point routing
- Skills architecture
- Agent hierarchy
- Quick reference FAQ
- Development commands
- Project philosophy

**Target** (50 lines):
- Pure routing logic ONLY
- Decision tree: simple question vs. invoke orchestrator
- References to ENTRY.md, ARCHITECTURE.md, FAQ.md

**New files**:
- `.claude/ENTRY.md`: Entry point decision logic, examples
- `.claude/ARCHITECTURE.md`: Skills/agents structure, activation triggers
- `.claude/FAQ.md`: Quick reference questions

#### TDD-0010-save-orchestration.md (Currently 2196 lines → 500)
**Extract**:
- Lines 1-200 (problem statement) → Already in PRD-0005
- Lines 800-1000 (API reference) → `docs/reference/REF-savesession-api.md`
- Lines 1000-1500 (examples) → `docs/guides/save-session.md`
- Lines 1500-2196 (migration guide) → `docs/migration/MIGRATION-SAVESESSION.md`

**Keep**:
- Lines 200-800 (design decisions) → 500 lines focused on design

#### TDD-0004-tier2-clients.md (Currently 2179 lines → 6 files)
**Split into**:
- `TDD-0004-tier2-clients-overview.md` (300 lines): Tier 2 architecture
- `TDD-0004.1-tasks-client.md` (350 lines): Tasks client design
- `TDD-0004.2-projects-client.md` (350 lines): Projects client design
- `TDD-0004.3-sections-client.md` (350 lines): Sections client design
- `TDD-0004.4-users-client.md` (350 lines): Users client design
- `TDD-0004.5-custom-fields-client.md` (350 lines): Custom fields client design
- `TDD-0004.6-workspaces-client.md` (350 lines): Workspaces client design

---

## Consolidation Plan

### Priority 1: Cache Documentation Cluster (18 files → 3 references)

**Impact**: CRITICAL - 640KB → 240KB (62% reduction), massively improved discoverability

#### Step 1: Create Canonical References (NEW)

**1.1 Create `docs/reference/REF-cache-architecture.md`** (400 lines)

**Source material** (consolidate from):
- TDD-CACHE-INTEGRATION.md (lines 1-200, 800-1000)
- PRD-CACHE-INTEGRATION.md (lines 1-150)
- TDD-0008-intelligent-caching.md (lines 50-200)
- ADR-0123-cache-provider-selection.md (full)
- ADR-0017-redis-backend-architecture.md (full)

**Contents**:
- Architecture overview (cache layers, data flow)
- Provider protocol specification
- Backend selection rationale (Redis vs S3)
- Integration patterns (client cache pattern, population strategy)
- Performance characteristics
- Extension points

**Cross-references from**: All 18 cache PRDs/TDDs

---

**1.2 Enhance `docs/reference/REF-cache-staleness-detection.md`** (already exists, 300 lines)

**Additional source material**:
- TDD-CACHE-LIGHTWEIGHT-STALENESS.md (lines 200-500)
- PRD-CACHE-LIGHTWEIGHT-STALENESS.md (lines 100-250)
- ADR-0019-staleness-detection-algorithm.md (reference)
- ADR-0134-staleness-check-integration-pattern.md (reference)

**Enhance with**:
- Lightweight staleness detection algorithm
- Modified-since header approach
- Batch coalescing strategy
- Performance characteristics
- API rate limit considerations

---

**1.3 Enhance `docs/reference/REF-cache-ttl-strategy.md`** (already exists, 250 lines)

**Additional source material**:
- TDD-CACHE-OPTIMIZATION-P2.md (lines 300-500)
- TDD-CACHE-OPTIMIZATION-P3.md (lines 200-400)
- PRD-CACHE-OPTIMIZATION-P2.md (lines 150-300)
- ADR-0133-progressive-ttl-extension-algorithm.md (reference)
- ADR-0126-entity-ttl-resolution.md (reference)

**Enhance with**:
- Progressive TTL algorithm (extension formula)
- Watermark strategy
- Max TTL calculation
- GID enumeration caching
- Edge cases and tuning

---

#### Step 2: Update PRDs/TDDs to Reference (NOT duplicate)

**Pattern** (apply to all 18 cache files):

**Before**:
```markdown
## Cache Architecture

The cache system uses a two-tier architecture with Redis as the backend...
[200 lines of architecture explanation]

## Progressive TTL

The TTL extension algorithm uses the formula...
[150 lines of TTL details]
```

**After**:
```markdown
## Cache Architecture

See **[REF-cache-architecture.md](../reference/REF-cache-architecture.md)** for cache system overview, provider protocol, and integration patterns.

This document focuses on [SPECIFIC ASPECT relevant to this PRD/TDD].

## Progressive TTL Strategy

See **[REF-cache-ttl-strategy.md](../reference/REF-cache-ttl-strategy.md)** for progressive TTL algorithm and watermark strategy.

This PRD/TDD applies the strategy to [SPECIFIC USE CASE].
```

**Files to update**:

PRDs (9 files):
- PRD-CACHE-INTEGRATION.md: Remove architecture overview (lines 1-150), reference REF-cache-architecture.md
- PRD-0008-intelligent-caching.md: Remove cache basics, reference REF files
- PRD-CACHE-LIGHTWEIGHT-STALENESS.md: Remove staleness algorithm (lines 100-250), reference REF-cache-staleness-detection.md
- PRD-CACHE-OPTIMIZATION-P2.md: Remove TTL details, reference REF-cache-ttl-strategy.md
- PRD-CACHE-OPTIMIZATION-P3.md: Remove GID enumeration details, reference REF-cache-ttl-strategy.md
- PRD-CACHE-PERF-DETECTION.md: Remove cache architecture, reference REF-cache-architecture.md
- PRD-CACHE-PERF-HYDRATION.md: Remove cache architecture, reference REF-cache-architecture.md
- PRD-CACHE-UTILIZATION.md: Remove architecture, reference REF-cache-architecture.md
- PRD-WATERMARK-CACHE.md: Remove watermark algorithm, reference REF-cache-ttl-strategy.md

TDDs (9 files):
- TDD-CACHE-INTEGRATION.md: Extract lines 1-200, 800-1000 → REF-cache-architecture.md
- TDD-0008-intelligent-caching.md: Extract lines 50-200 → REF-cache-architecture.md
- TDD-CACHE-LIGHTWEIGHT-STALENESS.md: Extract lines 200-500 → REF-cache-staleness-detection.md
- TDD-CACHE-OPTIMIZATION-P2.md: Extract lines 300-500 → REF-cache-ttl-strategy.md
- TDD-CACHE-OPTIMIZATION-P3.md: Extract lines 200-400 → REF-cache-ttl-strategy.md
- TDD-CACHE-PERF-DETECTION.md: Reference REF-cache-architecture.md
- TDD-CACHE-PERF-HYDRATION.md: Reference REF-cache-architecture.md
- TDD-CACHE-UTILIZATION.md: Reference REF-cache-architecture.md
- TDD-WATERMARK-CACHE.md: Reference REF-cache-ttl-strategy.md

**Estimated reduction**: 640KB → 240KB (62% reduction, ~400KB saved)

---

### Priority 2: Command/Skill-Ref Duplication (21 pairs, 110KB → 30KB)

**Impact**: HIGH - 73% reduction, clear separation of concerns

#### Pattern (apply to all 21 pairs)

**Commands**: Thin to 20-50 lines (pure actionable prompt)
**Skills**: Preserve full reference (200-400 lines, remove command duplication)

#### Example: `/10x` command

**Before**:
- `.claude/commands/10x.md`: 320 lines (purpose, team details, examples, workflows, related commands)
- `.claude/skills/10x-ref/skill.md`: 320 lines (same content, 80% overlap)

**After**:

`.claude/commands/10x.md` (50 lines):
```markdown
---
description: Switch to 10x-dev-pack team
argument-hint: ""
allowed-tools: Bash, Read
---

## Context
!`cat .claude/ACTIVE_TEAM`

## Your Task
Switch to 10x-dev-pack and display team roster.

## Behavior
1. Execute: ~/Code/roster/swap-team.sh 10x-dev-pack
2. Show team roster with agent roles and responsibilities
3. Update SESSION_CONTEXT if active session exists

## Reference
Full documentation: .claude/skills/10x-ref/skill.md
Team roster: .claude/skills/team-development/TEAMS.md
Workflow lifecycle: .claude/skills/10x-ref/lifecycle.md
```

`.claude/skills/10x-ref/skill.md` (300 lines - existing content, remove duplication):
```markdown
# 10x Development Pack Reference

## Overview
[Full reference material preserved]

## Agent Roster
See `.claude/skills/team-development/TEAMS.md` for canonical team roster.

## Workflow Lifecycle
[Reference to lifecycle.md]

## Examples
[Full examples preserved here, not in command]

## Related Commands
[Links to related commands]
```

`.claude/skills/team-development/TEAMS.md` (NEW, 200 lines):
```markdown
# Team Rosters

## 10x-dev-pack
- orchestrator: Coordinates multi-phase workflows across specialist agents
- requirements-analyst: Produces PRDs, clarifies intent, validates acceptance criteria
- architect: Produces TDDs and ADRs, designs solutions, makes architectural decisions
- principal-engineer: Implements code with craft and discipline, writes tests
- qa-adversary: Validates quality, finds edge cases, produces test plans

## doc-team-pack
[Doc team roster]

## hygiene-team-pack
[Hygiene team roster]

## debt-team-pack
[Debt team roster]

## sre-team-pack
[SRE team roster]
```

#### Files to Update (21 pairs)

Commands (thin to 20-50 lines each):
- 10x.md, docs.md, task.md, sprint.md, hotfix.md, wrap.md, pr.md, qa.md, debt.md, park.md, build.md, code-review.md, sessions.md, start.md, team.md, sre.md, handoff.md, architect.md, continue.md, spike.md, hygiene.md

Skills (remove command duplication, preserve reference):
- 10x-ref/skill.md, docs-ref/skill.md, task-ref/skill.md, sprint-ref/skill.md, hotfix-ref/skill.md, wrap-ref/skill.md, pr-ref/skill.md, qa-ref/skill.md, debt-ref/skill.md, park-ref/skill.md, build-ref/skill.md, review-ref/skill.md, start-ref/skill.md, team-ref/skill.md, sre-ref/skill.md, handoff-ref/skill.md, architect-ref/skill.md, spike-ref/skill.md, hygiene-ref/skill.md

New file:
- `.claude/skills/team-development/TEAMS.md` (canonical team rosters)

**Estimated reduction**: 110KB → 30KB (73% reduction, ~80KB saved)

---

### Priority 3: Glossary Unification (12 files → 1)

**Impact**: HIGH - Single source of truth, 67% reduction

#### Create `docs/reference/GLOSSARY.md` (300 lines, hierarchical)

**Consolidate from**:
- `.claude/GLOSSARY.md` (pointer file → becomes pointer to docs/reference/GLOSSARY.md)
- `10x-workflow/glossary-index.md` (navigation)
- `10x-workflow/glossary-agents.md` (15 terms)
- `10x-workflow/glossary-process.md` (22 terms)
- `10x-workflow/glossary-quality.md` (18 terms)
- `team-development/glossary/index.md` (navigation)
- `team-development/glossary/agents.md` (17 terms)
- `team-development/glossary/artifacts.md` (12 terms)
- `team-development/glossary/workflows.md` (14 terms)
- `skills/.archive/glossary.md` (45 terms, 60% still relevant)

**Structure**:
```markdown
# autom8_asana Glossary

> Canonical definitions for all project concepts.
> **Location**: docs/reference/GLOSSARY.md
> **Alias**: .claude/GLOSSARY.md (pointer)

---

## Navigation
- [Agent Roles](#agent-roles)
- [Workflow Concepts](#workflow-concepts)
- [Artifacts](#artifacts)
- [Quality Gates](#quality-gates)
- [Cache Architecture](#cache-architecture)
- [Asana Domain](#asana-domain)
- [SDK Concepts](#sdk-concepts)

---

## Agent Roles

### Orchestrator
**Definition**: Coordinates multi-phase workflows across specialist agents.
**Artifacts**: PROMPT-0, PROMPT-MINUS-1, SESSION_CONTEXT
**Authority**: Session planning, quality gate validation, adaptive routing
**References**: [10x-workflow skill](.claude/skills/10x-ref/skill.md)

### Requirements Analyst
**Definition**: Produces PRDs, clarifies user intent, validates acceptance criteria.
**Artifacts**: PRD-NNNN, user stories, success metrics
**Authority**: Requirements validation, scope definition
**References**: [documentation/templates/prd.md](.claude/skills/documentation/templates/prd.md)

[... all agent roles ...]

---

## Workflow Concepts

### Session -1 (Initiative Assessment)
**Definition**: High-level initiative analysis before detailed planning.
**Artifacts**: PROMPT-MINUS-1
**Purpose**: Validate initiative scope, identify risks, estimate effort
**References**: [initiative-scoping/session-minus-1-protocol.md](.claude/skills/initiative-scoping/session-minus-1-protocol.md)

### Session 0 (Initiative Planning)
**Definition**: Detailed initiative planning and phase decomposition.
**Artifacts**: PROMPT-0, phase breakdown, acceptance criteria
**Purpose**: Create actionable plan for multi-phase work
**References**: [initiative-scoping/session-0-protocol.md](.claude/skills/initiative-scoping/session-0-protocol.md)

[... all workflow concepts ...]

---

## Artifacts

### PRD (Product Requirements Document)
**Definition**: Formal requirements specification for a feature or initiative.
**Template**: [documentation/templates/prd.md](.claude/skills/documentation/templates/prd.md)
**Naming**: PRD-NNNN-{slug}.md or PRD-{TOPIC}-{slug}.md
**Location**: docs/requirements/
**Status Values**: Draft, Active, Approved, Implemented, Superseded

[... all artifact types ...]

---

## Quality Gates

### Requirements Quality Gate
**Definition**: Criteria PRD must meet before architect begins design.
**Criteria**: Clear acceptance criteria, success metrics, edge cases identified, dependencies documented
**References**: [10x-workflow/quality-gates.md](.claude/skills/10x-workflow/quality-gates.md)

[... all quality gates ...]

---

## Cache Architecture

### Progressive TTL
**Definition**: TTL extension algorithm that increases cache lifetime based on access patterns.
**Algorithm**: See [REF-cache-ttl-strategy.md](./REF-cache-ttl-strategy.md)
**Use Cases**: Frequently accessed entities, stable data
**References**: [ADR-0133](../decisions/ADR-0133-progressive-ttl-extension-algorithm.md)

### Watermark Strategy
**Definition**: Parallel fetch optimization using high-water marks to resume interrupted operations.
**Algorithm**: See [REF-cache-ttl-strategy.md](./REF-cache-ttl-strategy.md#watermark-strategy)
**References**: [TDD-WATERMARK-CACHE](../design/TDD-WATERMARK-CACHE.md)

[... all cache terms ...]

---

## Asana Domain

### SaveSession
**Definition**: Unit of Work pattern for batch Asana operations with dependency tracking.
**Lifecycle**: Track → Modify → Commit → Validate
**References**: [REF-savesession-lifecycle.md](./REF-savesession-lifecycle.md), [TDD-0010](../design/TDD-0010-save-orchestration.md)

### Business Model
**Definition**: Higher-order entities representing business concepts (Business, Contact, Unit, Offer).
**Hierarchy**: Business → Unit → Contact, Offer
**References**: [REF-entity-type-table.md](./REF-entity-type-table.md), [TDD-0027](../design/TDD-0027-business-model-architecture.md)

[... all Asana/SDK terms ...]

---

## SDK Concepts

### Entity Lifecycle
**Definition**: Canonical pattern for entity management: Define → Detect → Populate → Navigate → Persist.
**References**: [REF-entity-lifecycle.md](./REF-entity-lifecycle.md)

### Detection Tiers
**Definition**: 5-tier system for entity type detection (GID, Custom Field, Name, Heuristics, Explicit).
**References**: [REF-detection-tiers.md](./REF-detection-tiers.md), [TDD-DETECTION](../design/TDD-DETECTION.md)

[... all SDK terms ...]
```

#### Delete Fragmented Glossaries

**Files to delete**:
- `.claude/skills/10x-workflow/glossary-index.md`
- `.claude/skills/10x-workflow/glossary-agents.md`
- `.claude/skills/10x-workflow/glossary-process.md`
- `.claude/skills/10x-workflow/glossary-quality.md`
- `.claude/skills/team-development/glossary/index.md`
- `.claude/skills/team-development/glossary/agents.md`
- `.claude/skills/team-development/glossary/artifacts.md`
- `.claude/skills/team-development/glossary/workflows.md`
- `.claude/skills/.archive/glossary.md` (already archived)

**Update `.claude/GLOSSARY.md`** (pointer file):
```markdown
# Glossary

The canonical glossary is located at:

**[docs/reference/GLOSSARY.md](../docs/reference/GLOSSARY.md)**

All project terms are defined there in hierarchical sections:
- Agent Roles
- Workflow Concepts
- Artifacts
- Quality Gates
- Cache Architecture
- Asana Domain
- SDK Concepts

This file is a pointer to prevent duplication.
```

**Estimated reduction**: 12 files (~60KB) → 1 file (~20KB), 67% reduction

---

### Priority 4: Monolithic CLAUDE.md Split (150 lines → 50 lines)

**Impact**: HIGH - Clear single responsibility, improved maintainability

#### Create New Files

**1. `.claude/ENTRY.md`** (100 lines)
```markdown
# Claude Code Entry Point

## Decision Tree

User Request
    |
    v
Is this a simple question/lookup?
    |
  YES --> Answer directly (check skills/docs first)
    |
   NO --> Invoke @orchestrator with full context

## Examples

### Simple Questions (Answer Directly)
- "What's SaveSession?" → Check autom8-asana skill, answer directly
- "Where does SDK code go?" → Check autom8-asana/infrastructure.md
- "What's the tech stack?" → Check standards/tech-stack.md
- "How do I write a PRD?" → Check documentation/templates/prd.md

### Tasks (Invoke @orchestrator)
- "Add rate limiting" → @orchestrator
- "Implement cache invalidation" → @orchestrator
- "Fix the SaveSession bug" → @orchestrator (after clarifying which bug)
- "Create a new client" → @orchestrator

### Ambiguous (Ask for Clarification)
- "Fix the bug" → Which bug? Where? What symptoms?
- "Update the docs" → Which docs? What changes?
- "Optimize performance" → What system? What metric?

## Invocation Pattern

When routing to @orchestrator:

```
@orchestrator

**User Request**: [What the user asked for]

**Context**:
- [Relevant files or systems]
- [Constraints or requirements mentioned]

Please analyze this task, create a phased plan, and coordinate execution.
```

## Quick Help Routing

| Question | Where to Look |
|----------|---------------|
| What is SaveSession? | autom8-asana skill |
| How do Asana batch ops work? | autom8-asana/persistence.md |
| Where does SDK code go? | autom8-asana/infrastructure.md |
| What's the tech stack? | standards/tech-stack.md |
| How does Business/Contact/Unit work? | autom8-asana/entities.md |
| How do I detect entity types? | autom8-asana/entities.md#detection |
| PRD/TDD templates? | documentation skill |
| Agent workflow patterns? | 10x-workflow skill |
| Project overview? | PROJECT_CONTEXT.md |
| Domain glossary? | docs/reference/GLOSSARY.md |
```

**2. `.claude/ARCHITECTURE.md`** (150 lines)
```markdown
# Skills and Agents Architecture

## Skills System

Skills load context on-demand. Use the appropriate skill for domain knowledge.

| Skill | When to Activate |
|-------|------------------|
| **autom8-asana** | SDK patterns, SaveSession, Business entities, detection, batch operations |
| **standards** | General Python/testing patterns (note: generic, not SDK-specific) |
| **documentation** | PRD/TDD/ADR templates, documentation workflows |
| **10x-workflow** | Full lifecycle, quality gates, agent glossary |
| **initiative-scoping** | Prompt -1, Prompt 0 patterns |

### Activation Triggers

**autom8-asana** activates on:
- Keywords: SaveSession, Business, Contact, Unit, Offer, holder, detect_entity_type, cascade_field, ActionOperation, batch operation, async client
- File patterns: `src/autom8_asana/**/*.py`, `tests/**/*.py`
- Tasks: SDK implementation, Asana API integration, entity operations, hierarchy navigation

[... similar for other skills ...]

## Agent Hierarchy

```
Main Thread (You)
    |
    v (invoke @orchestrator)
@orchestrator
    |
    v (coordinates)
@requirements-analyst  --> PRD
@architect             --> TDD, ADRs
@principal-engineer    --> Code
@qa-adversary          --> Test Plan
```

## Agent Responsibilities

### @orchestrator
**Role**: Multi-phase workflow coordination
**Artifacts**: PROMPT-0, PROMPT-MINUS-1, SESSION_CONTEXT
**Authority**: Session planning, quality gates, adaptive routing

### @requirements-analyst
**Role**: Requirements specification
**Artifacts**: PRD-NNNN
**Authority**: Scope definition, acceptance criteria

[... all agents ...]

## Team Packs

See `.claude/skills/team-development/TEAMS.md` for canonical team rosters.

Available teams:
- 10x-dev-pack (full lifecycle development)
- doc-team-pack (documentation workflows)
- hygiene-team-pack (code quality, refactoring)
- debt-team-pack (technical debt triage)
- sre-team-pack (operational reliability)
```

**3. `.claude/FAQ.md`** (100 lines)
```markdown
# Frequently Asked Questions

## Quick Reference

### Getting Started
Q: How do I run tests?
A: `pytest` (full suite) or `pytest tests/path/to/test.py` (specific)

Q: How do I install dev dependencies?
A: `pip install -e ".[dev]"`

Q: Where is the main README?
A: Root `README.md` file

### Finding Documentation
Q: Where are PRDs?
A: `docs/requirements/PRD-*.md`

Q: Where are TDDs?
A: `docs/design/TDD-*.md`

Q: Where is the glossary?
A: `docs/reference/GLOSSARY.md`

Q: How do I find a specific ADR?
A: Check `docs/INDEX.md` for categorized ADR list

### Common Tasks
Q: How do I switch teams?
A: `/10x`, `/docs`, `/hygiene`, `/debt`, `/sre` commands

Q: How do I start a new task?
A: `/task "description"`

Q: How do I create a hotfix?
A: `/hotfix "description"`

### Skills and Context
Q: Which skill for SaveSession questions?
A: `autom8-asana` skill

Q: Which skill for cache questions?
A: Check `docs/reference/REF-cache-*.md` files

Q: Which skill for workflow questions?
A: `10x-workflow` skill

### Development Commands

```bash
# Development
pip install -e ".[dev]"   # Install dev dependencies
pytest                    # Run tests
pytest --cov              # Run with coverage
mypy src/autom8_asana     # Type check
ruff check src/           # Lint
ruff format src/          # Format
```

[... more FAQs ...]
```

#### Update CLAUDE.md (Thin to 50 lines)

```markdown
# CLAUDE.md

> Entry point for Claude Code. Routes to specialist agents.

---

## You Are the Main Thread

You receive user requests and route to the appropriate agent.

**Decision Tree**: See [ENTRY.md](ENTRY.md)
**Skills/Agents**: See [ARCHITECTURE.md](ARCHITECTURE.md)
**Quick Help**: See [FAQ.md](FAQ.md)

## Quick Routing

**Simple question?** → Answer directly (check skills/docs first)
**Substantive task?** → Invoke @orchestrator

## The Prime Directive

```
User --> Main Thread --> @orchestrator --> @specialists --> Deliverables
```

**You are a router, not a worker.**
Understand user intent. Invoke the right agent.
Trust the system.

---

## Essential References

| Need | See |
|------|-----|
| Entry logic | [ENTRY.md](ENTRY.md) |
| Architecture | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Quick answers | [FAQ.md](FAQ.md) |
| Project overview | [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) |
| Glossary | [../docs/reference/GLOSSARY.md](../docs/reference/GLOSSARY.md) |
| Documentation index | [../docs/INDEX.md](../docs/INDEX.md) |
```

**Estimated impact**: 150 lines → 50 lines router + 3 focused files (350 lines total)
**Benefit**: Clear single responsibility, easier maintenance, better discoverability

---

### Priority 5: Create Missing Reference Abstractions

**Impact**: HIGH - Foundation for future consistency

#### New Reference Documents

**1. `docs/reference/REF-entity-lifecycle.md`** (300 lines)

**Source material** (concept appears in 25+ places):
- TDD-0027-business-model-architecture.md
- TDD-DETECTION.md
- TDD-0017-hierarchy-hydration.md
- 8 other TDDs
- 5 PRDs
- 12 test files (as comments)

**Contents**:
```markdown
# Entity Lifecycle Pattern

## Overview
Canonical pattern for entity management in autom8_asana SDK.

## The Five Phases

### 1. Define
**Purpose**: Declare entity types and their structure.
**Artifacts**: Pydantic models, holder classes, custom field descriptors
**References**: [TDD-0027](../design/TDD-0027-business-model-architecture.md)

### 2. Detect
**Purpose**: Identify entity type from Asana task.
**Mechanism**: 5-tier detection system (GID, Custom Field, Name, Heuristics, Explicit)
**References**: [REF-detection-tiers.md](./REF-detection-tiers.md), [TDD-DETECTION](../design/TDD-DETECTION.md)

### 3. Populate
**Purpose**: Hydrate entity with data from Asana.
**Mechanisms**: Direct fetch, batch fetch, cache-optimized fetch
**References**: [TDD-0017](../design/TDD-0017-hierarchy-hydration.md)

### 4. Navigate
**Purpose**: Traverse entity relationships.
**Patterns**: Lazy loading, eager loading, bidirectional references
**References**: [ADR-0050](../decisions/ADR-0050-holder-lazy-loading-strategy.md)

### 5. Persist
**Purpose**: Save entity changes back to Asana.
**Mechanism**: SaveSession unit of work pattern
**References**: [REF-savesession-lifecycle.md](./REF-savesession-lifecycle.md), [TDD-0010](../design/TDD-0010-save-orchestration.md)

## Lifecycle Diagram

[Diagram showing Define → Detect → Populate → Navigate → Persist cycle]

## Implementation Patterns

[Code examples showing each phase]

## Common Pitfalls

[Anti-patterns and how to avoid them]
```

---

**2. `docs/reference/REF-savesession-lifecycle.md`** (350 lines)

**Source material** (extracted from):
- TDD-0010-save-orchestration.md (lines 200-500)
- PRD-0005-save-orchestration.md
- TDD-0022-savesession-reliability.md
- 8 other docs

**Contents**:
```markdown
# SaveSession Lifecycle

## Overview
Unit of Work pattern for batch Asana operations with dependency tracking.

## The Four Phases

### 1. Track
**Purpose**: Monitor entity changes.
**Mechanism**: Change detection, dirty tracking
**API**: `session.track(entity)`

### 2. Modify
**Purpose**: Make changes to tracked entities.
**Mechanisms**: Direct modification, cascade operations, batch updates
**API**: Entity setters, `entity.cascade_field()`

### 3. Commit
**Purpose**: Persist all changes to Asana.
**Mechanism**: Dependency graph resolution, batch API calls, error handling
**API**: `await session.commit()`

### 4. Validate
**Purpose**: Verify all changes applied correctly.
**Mechanism**: Optimistic concurrency, partial failure handling, healing
**API**: Automatic validation in commit

## Lifecycle Diagram

[Diagram showing Track → Modify → Commit → Validate cycle]

## Dependency Graph Algorithm

[Explain ADR-0037 dependency resolution]

## Error Handling

### Partial Failures
[How SaveSession handles partial failures]

### Healing Strategies
[Retry, rollback, manual intervention]

## Advanced Patterns

### Nested Sessions
[When and how to use nested SaveSessions]

### Cross-Holder Operations
[Resolving dependencies across holder hierarchies]

## Implementation Guide

[Code examples for common scenarios]

## Troubleshooting

See [RUNBOOK-savesession-debugging.md](../runbooks/RUNBOOK-savesession-debugging.md)
```

---

**3. `docs/reference/REF-detection-tiers.md`** (300 lines)

**Source material**:
- TDD-DETECTION.md (extraction)
- PRD-DETECTION.md
- 6 other docs

**Contents**:
```markdown
# Entity Detection Tier System

## Overview
5-tier system for detecting entity type from Asana task.

## Tier 1: GID-Based Detection (Highest Confidence)
**Mechanism**: Direct GID lookup in registry
**Confidence**: 100%
**Performance**: O(1) lookup
**Example**: Task GID found in Business registry → Business entity

## Tier 2: Custom Field Detection (High Confidence)
**Mechanism**: Presence of type-specific custom fields
**Confidence**: 95%+
**Performance**: O(n) field scan
**Example**: Task has "Rep" field → Contact entity

## Tier 3: Name Pattern Detection (Medium Confidence)
**Mechanism**: Regex matching on task name
**Confidence**: 70-80%
**Performance**: O(1) regex match
**Example**: Task name matches "^BUSINESS:" → Business entity

## Tier 4: Heuristics (Low Confidence)
**Mechanism**: Contextual inference (parent type, project membership)
**Confidence**: 50-60%
**Performance**: O(1) parent lookup
**Example**: Parent is Business, name has no colon → Unit entity

## Tier 5: Explicit Declaration (Fallback)
**Mechanism**: User explicitly specifies type
**Confidence**: 100% (user intent)
**Performance**: O(1)
**Example**: `detect_entity_type(task_gid, explicit_type=EntityType.CONTACT)`

## Decision Algorithm

```python
def detect_entity_type(task_gid: str, explicit_type: Optional[EntityType] = None) -> EntityType:
    # Tier 5: Explicit
    if explicit_type:
        return explicit_type

    # Tier 1: GID
    if entity_type := lookup_in_registry(task_gid):
        return entity_type

    # Tier 2: Custom Field
    if entity_type := detect_by_custom_fields(task_gid):
        return entity_type

    # Tier 3: Name Pattern
    if entity_type := detect_by_name_pattern(task_gid):
        return entity_type

    # Tier 4: Heuristics
    if entity_type := detect_by_heuristics(task_gid):
        return entity_type

    # Fallback
    raise UndetectableEntityError(task_gid)
```

## Confidence Scores

[Table showing confidence by tier]

## Performance Characteristics

[Benchmarks for each tier]

## Implementation Details

See [TDD-DETECTION](../design/TDD-DETECTION.md)

## Troubleshooting

See [RUNBOOK-detection-troubleshooting.md](../runbooks/RUNBOOK-detection-troubleshooting.md)
```

---

**4. `docs/reference/REF-batch-operations.md`** (250 lines)

**Source material** (appears in 10+ TDDs):
- TDD-0005-batch-api.md
- TDD-0017-hierarchy-hydration.md
- TDD-CACHE-OPTIMIZATION-P2.md
- Others

**Contents**:
```markdown
# Batch Operation Patterns

## Overview
Standard patterns for chunking, parallelization, and error handling in batch operations.

## Chunking Strategy

### Chunk Size Determination
**Default**: 50 items per chunk (Asana API limit: 100)
**Rationale**: ADR-0XXX (create if doesn't exist)

### Chunk Boundaries
[How to split operations into chunks]

## Parallelization

### Concurrency Limits
**Default**: 5 concurrent requests
**Tuning**: Based on rate limits, system resources

### AsyncIO Patterns
[Code examples using asyncio.gather, semaphores]

## Error Handling

### Partial Failures
**Strategy**: Fail fast vs. best effort
**Implementation**: [Examples]

### Retry Logic
**Backoff**: Exponential with jitter
**Max Retries**: 3
**Retry Conditions**: Transient errors only

## Coalescing Strategy

### Request Deduplication
[How to detect duplicate requests in batch]

### Response Merging
[How to merge responses from multiple batches]

## Performance Optimization

### Cache-Aware Batching
[Integration with cache system]

### Watermark Strategy
[Resume interrupted batch operations]

## Implementation Examples

[Code examples for common patterns]
```

---

**5. `docs/reference/REF-asana-hierarchy.md`** (200 lines)

**Source material** (appears in 15+ PRDs/TDDs):
- Multiple TDDs explaining hierarchy

**Contents**:
```markdown
# Asana Resource Hierarchy

## Overview
Canonical reference for Asana's resource hierarchy and navigation patterns.

## Hierarchy Structure

```
Workspace
  ├── Project
  │     ├── Section
  │     │     ├── Task
  │     │     │     ├── Subtask (Task)
  │     │     │     ├── Subtask (Task)
  │     │     │     └── ...
  │     │     ├── Task
  │     │     └── ...
  │     ├── Section
  │     └── ...
  ├── Project
  └── ...
```

## Resource Types

### Workspace
**Purpose**: Top-level container for organization
**Key Fields**: name, gid
**Navigation**: → Projects, → Custom Fields

### Project
**Purpose**: Collection of related tasks
**Key Fields**: name, gid, workspace
**Navigation**: → Sections, → Tasks, ← Workspace

### Section
**Purpose**: Logical grouping within project
**Key Fields**: name, gid, project
**Navigation**: → Tasks, ← Project

### Task
**Purpose**: Work item
**Key Fields**: name, gid, projects (plural!), parent (for subtasks)
**Navigation**: → Subtasks, → Custom Fields, ← Section, ← Parent

### Subtask
**Note**: Subtasks are Tasks with a `parent` field set
**Navigation**: → Parent Task

## Navigation Patterns

### Downward Navigation (Container → Contents)
[Examples: Workspace → Projects, Project → Tasks]

### Upward Navigation (Contents → Container)
[Examples: Task → Project, Section → Project]

### Lateral Navigation (Siblings)
[Examples: Task → Sibling Tasks in Section]

## Multi-Homing

**Key Insight**: Tasks can belong to MULTIPLE projects!

[Explain memberships, implications]

## Custom Fields

**Workspace-Level**: Custom fields defined at workspace
**Task-Level**: Custom field values on tasks

[Explain custom field hierarchy]

## Implementation Guide

[Code examples using SDK clients]
```

---

**6. `docs/reference/REF-workflow-phases.md`** (250 lines)

**Source material**:
- 10x-workflow/lifecycle.md (canonical)
- Duplicated in 7 other places

**Contents**:
```markdown
# Workflow Phase Transitions

## Overview
Canonical lifecycle for feature development in autom8_asana.

## The Five Phases

### Phase 1: Requirements
**Agent**: @requirements-analyst
**Artifact**: PRD-NNNN
**Entry Criteria**: User request, initiative scope
**Exit Criteria**: Requirements quality gate passed

**Quality Gate**:
- Clear acceptance criteria
- Success metrics defined
- Edge cases identified
- Dependencies documented

**Handoff to**: Phase 2 (Design)

---

### Phase 2: Design
**Agent**: @architect
**Artifacts**: TDD-NNNN, ADR-NNNN+
**Entry Criteria**: Approved PRD
**Exit Criteria**: Design quality gate passed

**Quality Gate**:
- Component boundaries defined
- API contracts specified
- Data flow documented
- Non-functional requirements addressed

**Handoff to**: Phase 3 (Implementation)

---

### Phase 3: Implementation
**Agent**: @principal-engineer
**Artifacts**: Code, tests, migration scripts
**Entry Criteria**: Approved TDD
**Exit Criteria**: Implementation quality gate passed

**Quality Gate**:
- All tests passing
- Type checking passing
- Linting passing
- Coverage ≥ target

**Handoff to**: Phase 4 (Validation)

---

### Phase 4: Validation
**Agent**: @qa-adversary
**Artifacts**: Test Plan, Validation Report
**Entry Criteria**: Implemented code
**Exit Criteria**: Validation quality gate passed

**Quality Gate**:
- Test plan executed
- Edge cases validated
- Performance acceptable
- Documentation updated

**Handoff to**: Phase 5 (Deployment)

---

### Phase 5: Deployment
**Agent**: @sre-team or @principal-engineer
**Artifacts**: Deployment log, runbook updates
**Entry Criteria**: Validated code
**Exit Criteria**: Deployed to production

**Quality Gate**:
- Deployment successful
- Monitoring in place
- Rollback plan tested

---

## Phase Transition Criteria

[Table showing entry/exit for each phase]

## Fast-Track Scenarios

### Hotfix (Bypass Design)
Requirements → Implementation → Validation → Deployment

### Spike (Investigation Only)
Requirements → Investigation → Report (no implementation)

## Iteration Patterns

### Design Iteration
If implementation reveals design flaws → back to Phase 2

### Requirements Iteration
If validation reveals missing requirements → back to Phase 1

## Workflow Diagram

[Diagram showing phase flow with iteration loops]

## Reference

Full lifecycle details: [10x-workflow/lifecycle.md](../../.claude/skills/10x-workflow/lifecycle.md)
```

---

**7. `docs/reference/REF-command-decision-tree.md`** (200 lines)

**Source material**:
- Explained separately in each command
- No single canonical reference

**Contents**:
```markdown
# Command Decision Tree

## Overview
When to use which command for common workflows.

## Development Workflow Commands

### `/task` - Single Task Execution
**Use when**: Implementing a well-defined, single-phase task
**Team**: 10x-dev-pack
**Phases**: Requirements → Design → Implementation → Validation
**Output**: PRD, TDD, Code, Tests, Validation Report
**Example**: "Implement cache invalidation hook"

### `/sprint` - Multi-Task Sprint Planning
**Use when**: Planning multiple related tasks in a sprint
**Team**: 10x-dev-pack
**Phases**: Sprint planning → Task decomposition → Execution
**Output**: Sprint plan, task breakdown, prioritization
**Example**: "Plan Sprint 3: Detection system implementation"

### `/hotfix` - Emergency Fix
**Use when**: Critical bug requiring immediate fix
**Team**: 10x-dev-pack (fast-track)
**Phases**: Requirements → Implementation → Validation → Deployment (no TDD)
**Output**: Minimal PRD, Code, Tests, Hotfix log
**Example**: "Fix production cache corruption bug"

---

## Team Management Commands

### `/10x` - Switch to 10x Development Pack
**Use when**: Full-cycle feature development
**Team**: orchestrator, requirements-analyst, architect, principal-engineer, qa-adversary

### `/docs` - Switch to Documentation Team
**Use when**: Documentation-focused work (audits, writing, review)
**Team**: doc-auditor, information-architect, tech-writer, doc-reviewer

### `/hygiene` - Switch to Hygiene Team
**Use when**: Code quality, refactoring, test improvements
**Team**: hygiene-focused agents

### `/debt` - Switch to Debt Triage Team
**Use when**: Technical debt assessment and prioritization
**Team**: debt-triage-focused agents

### `/sre` - Switch to SRE Team
**Use when**: Operational reliability, monitoring, runbooks
**Team**: sre-focused agents

---

## Workflow Support Commands

### `/start` - Start New Session
**Use when**: Beginning work on an initiative
**Output**: SESSION_CONTEXT created

### `/wrap` - Complete Session
**Use when**: Finishing work, creating handoff
**Output**: Summary, artifacts list, handoff notes

### `/park` - Pause Session
**Use when**: Temporarily pausing work
**Output**: Current state saved, resumption notes

### `/continue` - Resume Session
**Use when**: Resuming paused work
**Input**: Previous SESSION_CONTEXT

---

## Quality Assurance Commands

### `/qa` - Quality Adversarial Testing
**Use when**: Deep testing, edge case validation
**Team**: qa-adversary
**Output**: Test Plan, Validation Report

### `/code-review` - Code Review
**Use when**: Reviewing pull request or code changes
**Output**: Review comments, approval/rejection

### `/pr` - Create Pull Request
**Use when**: Ready to merge code
**Output**: GitHub PR with description, test plan

---

## Documentation Commands

### `/architect` - Architecture Design Session
**Use when**: Designing system architecture, making ADRs
**Team**: architect
**Output**: TDD, ADRs

---

## Investigation Commands

### `/spike` - Technical Spike
**Use when**: Investigating unknown territory
**Output**: Spike report, findings, recommendations

---

## Decision Matrix

| Scenario | Command | Team |
|----------|---------|------|
| New feature (well-scoped) | `/task` | 10x |
| Sprint planning | `/sprint` | 10x |
| Production bug | `/hotfix` | 10x |
| Documentation work | `/docs` | docs |
| Code cleanup | `/hygiene` | hygiene |
| Debt assessment | `/debt` | debt |
| Infrastructure | `/sre` | sre |
| Deep investigation | `/spike` | 10x |
| Testing edge cases | `/qa` | 10x (qa-adversary) |

---

## Examples

### "I need to add a new feature"
→ `/task "Add feature X"` (if well-defined)
→ `/spike "Investigate feature X"` (if undefined)

### "We have a production issue"
→ `/hotfix "Fix production issue X"`

### "Planning next sprint"
→ `/sprint "Sprint N planning"`

### "Documentation is out of date"
→ `/docs` then describe documentation work

### "Code is messy, need cleanup"
→ `/hygiene` then describe cleanup scope
```

---

## Navigation Design

### Entry Points by User Journey

#### Journey 1: New Engineer Onboarding
**Goal**: Understand project, set up environment, make first contribution

**Path**:
1. **Entry**: `README.md` (root)
2. **Overview**: `PROJECT_CONTEXT.md`
3. **Concepts**: `docs/guides/concepts.md`
4. **Quickstart**: `docs/guides/quickstart.md`
5. **First task**: `docs/guides/workflows.md` → Common patterns
6. **Deep dive**: `docs/reference/GLOSSARY.md` → Terms as needed

**Success metric**: First commit within 1 day

---

#### Journey 2: Debugging Production Issue
**Goal**: Understand error, find root cause, implement fix

**Path**:
1. **Entry**: Error message or symptom
2. **Troubleshooting**: `docs/runbooks/RUNBOOK-{system}-troubleshooting.md`
3. **Architecture**: Referenced ADRs or TDDs from runbook
4. **Reference**: `docs/reference/REF-{concept}.md` for deep dive
5. **Fix**: Implement using patterns from architecture docs

**Success metric**: Root cause identified within 30 minutes

---

#### Journey 3: Contributing New Feature
**Goal**: Understand workflow, produce artifacts, get code merged

**Path**:
1. **Entry**: Feature request or user need
2. **Workflow**: `.claude/ENTRY.md` → Route to @orchestrator
3. **Templates**: `docs/skills/documentation/templates/` → PRD, TDD templates
4. **Quality Gates**: `.claude/skills/10x-workflow/quality-gates.md`
5. **Reference**: `docs/reference/GLOSSARY.md`, `REF-*.md` as needed
6. **Completion**: `/wrap` command → Handoff artifacts

**Success metric**: PRD approved within 1 day, code merged within 1 week

---

#### Journey 4: Understanding System Architecture
**Goal**: Learn how system works, make informed design decisions

**Path**:
1. **Entry**: `PROJECT_CONTEXT.md` (high-level)
2. **Architecture**: `docs/design/TDD-0001-sdk-architecture.md` (system overview)
3. **Decisions**: `docs/decisions/ADR-*` (specific decisions by topic)
4. **Reference**: `docs/reference/REF-*.md` (canonical patterns)
5. **Deep dive**: Specific TDDs for subsystems

**Success metric**: Can explain system to colleague within 2 hours

---

### Cross-Reference Strategy

#### Inline Links (Contextual)
Use when referencing specific related concept in flow of document.

**Pattern**:
```markdown
The cache uses a [progressive TTL strategy](../reference/REF-cache-ttl-strategy.md) to extend lifetimes.
```

#### See Also Sections (Related Topics)
Use at end of document to point to related but not essential reading.

**Pattern**:
```markdown
## See Also
- [REF-cache-architecture.md](../reference/REF-cache-architecture.md) - Cache system overview
- [ADR-0133](../decisions/ADR-0133-progressive-ttl-extension-algorithm.md) - Progressive TTL decision
- [TDD-CACHE-OPTIMIZATION-P2](./TDD-CACHE-OPTIMIZATION-P2.md) - P2 optimization details
```

#### Reference Sections (Canonical Sources)
Use when document depends heavily on external concept, point to single source of truth.

**Pattern**:
```markdown
## References

This document builds on these canonical references:
- **Cache Architecture**: [REF-cache-architecture.md](../reference/REF-cache-architecture.md)
- **Entity Lifecycle**: [REF-entity-lifecycle.md](../reference/REF-entity-lifecycle.md)
- **SaveSession Lifecycle**: [REF-savesession-lifecycle.md](../reference/REF-savesession-lifecycle.md)
```

#### Glossary Links (Term Definitions)
Use when introducing domain-specific term for first time.

**Pattern**:
```markdown
The [SaveSession](../reference/GLOSSARY.md#savesession) tracks entity changes...
```

---

### Index and Registry Structure

#### `docs/INDEX.md` (Central Registry)
**Purpose**: Single entry point for all formal documentation
**Contents**:
- Quick navigation table
- PRD list with status
- TDD list with status
- ADR list by topic
- Test Plan list
- Initiative list
- Reference document list
- Guide list

**Update frequency**: After every new document

---

#### `docs/reference/README.md` (Reference Index)
**Purpose**: Guide to reference documents
**Contents**:
```markdown
# Reference Documentation Index

Canonical single sources of truth for cross-cutting concepts.

## Cache System
- [REF-cache-architecture.md](./REF-cache-architecture.md) - System overview, provider protocol
- [REF-cache-staleness-detection.md](./REF-cache-staleness-detection.md) - Detection algorithms
- [REF-cache-ttl-strategy.md](./REF-cache-ttl-strategy.md) - TTL and watermark strategies
- [REF-cache-provider-protocol.md](./REF-cache-provider-protocol.md) - Provider interface

## Entity Management
- [REF-entity-lifecycle.md](./REF-entity-lifecycle.md) - Define→Detect→Populate→Navigate→Persist
- [REF-detection-tiers.md](./REF-detection-tiers.md) - 5-tier detection system
- [REF-entity-type-table.md](./REF-entity-type-table.md) - Entity hierarchy

## SaveSession
- [REF-savesession-lifecycle.md](./REF-savesession-lifecycle.md) - Track→Modify→Commit→Validate

## Batch Operations
- [REF-batch-operations.md](./REF-batch-operations.md) - Chunking, parallelization, error handling

## Asana Domain
- [REF-asana-hierarchy.md](./REF-asana-hierarchy.md) - Workspace→Project→Section→Task
- [REF-custom-field-catalog.md](./REF-custom-field-catalog.md) - 108 custom fields

## Workflow
- [REF-workflow-phases.md](./REF-workflow-phases.md) - Phase transitions and quality gates
- [REF-command-decision-tree.md](./REF-command-decision-tree.md) - Which command to use

## Glossary
- [GLOSSARY.md](./GLOSSARY.md) - All project terms
```

---

#### `.claude/COMMAND_REGISTRY.md` (Command Index)
**Purpose**: Auto-generated index of all commands
**Generation**: From command frontmatter (YAML)
**Update**: Pre-commit hook or manual script

**Format**:
```markdown
# Command Registry

Auto-generated from command frontmatter.

| Command | Description | Allowed Tools |
|---------|-------------|---------------|
| `/10x` | Switch to 10x-dev-pack team | Bash, Read |
| `/docs` | Switch to doc-team-pack | Bash, Read |
| ... | ... | ... |

## By Category

### Team Management
- `/10x`, `/docs`, `/hygiene`, `/debt`, `/sre`, `/team`

### Workflow
- `/task`, `/sprint`, `/hotfix`, `/start`, `/wrap`, `/park`, `/continue`

### Quality
- `/qa`, `/code-review`, `/pr`, `/build`

### Investigation
- `/spike`, `/architect`
```

---

## Migration Sequence

### Phase 1: Foundation (Week 1)
**Goal**: Create canonical references, no disruption

**Tasks**:
1. Create `docs/reference/REF-cache-architecture.md` (consolidate from 18 files)
2. Enhance `docs/reference/REF-cache-staleness-detection.md`
3. Enhance `docs/reference/REF-cache-ttl-strategy.md`
4. Create `docs/reference/GLOSSARY.md` (consolidate from 12 files)
5. Create `.claude/skills/team-development/TEAMS.md` (team rosters)
6. Create `docs/reference/README.md` (reference index)

**Validation**: All new files reviewed and approved

**Rollback**: Delete new files (no existing docs modified)

---

### Phase 2: Update Cross-References (Week 2)
**Goal**: PRDs/TDDs reference canonical sources instead of duplicating

**Tasks**:
1. Update 9 cache PRDs to reference `docs/reference/REF-cache-*.md`
2. Update 9 cache TDDs to reference `docs/reference/REF-cache-*.md`
3. Update 21 commands to reference skills (remove duplication)
4. Update skills to reference TEAMS.md (remove roster duplication)
5. Update `.claude/GLOSSARY.md` to point to `docs/reference/GLOSSARY.md`

**Validation**: All references valid, no broken links

**Rollback**: Git revert (all changes are edits, not deletions)

---

### Phase 3: Thin Commands (Week 2-3)
**Goal**: Commands reduced to 20-50 lines, skills preserve reference

**Tasks**:
1. Thin 21 commands (extract to skills)
2. Update 21 skills (remove command duplication, preserve reference)
3. Update `COMMAND_REGISTRY.md` (may be auto-generated)

**Validation**: Commands functional, skills complete

**Rollback**: Git revert

---

### Phase 4: Split CLAUDE.md (Week 3)
**Goal**: Single responsibility, clear routing

**Tasks**:
1. Create `.claude/ENTRY.md`
2. Create `.claude/ARCHITECTURE.md`
3. Create `.claude/FAQ.md`
4. Update `CLAUDE.md` to 50-line router

**Validation**: Entry logic functional, no broken references

**Rollback**: Git revert, restore old CLAUDE.md

---

### Phase 5: Delete Fragmented Glossaries (Week 3)
**Goal**: Single source of truth

**Tasks**:
1. Delete 8 glossary files from `.claude/skills/10x-workflow/`
2. Delete 4 glossary files from `.claude/skills/team-development/`
3. Verify no references to deleted files

**Validation**: Grep for references to deleted files returns empty

**Rollback**: Git restore deleted files

---

### Phase 6: Create Missing References (Week 4)
**Goal**: Foundation abstractions for future consistency

**Tasks**:
1. Create `docs/reference/REF-entity-lifecycle.md`
2. Create `docs/reference/REF-savesession-lifecycle.md`
3. Create `docs/reference/REF-detection-tiers.md`
4. Create `docs/reference/REF-batch-operations.md`
5. Create `docs/reference/REF-asana-hierarchy.md`
6. Create `docs/reference/REF-workflow-phases.md`
7. Create `docs/reference/REF-command-decision-tree.md`

**Validation**: All references reviewed and approved

**Rollback**: Delete new files

---

### Phase 7: Split Monolithic TDDs (Week 5-6)
**Goal**: Focused design docs, extracted references

**Tasks**:
1. Split `TDD-0010-save-orchestration.md` (2196 → 500 lines + extracted references)
2. Split `TDD-0004-tier2-clients.md` (2179 → 6 files)
3. Split `TDD-AUTOMATION-LAYER.md` (1691 → 3 files)
4. Update cross-references

**Validation**: All extracted content accessible, no loss of information

**Rollback**: Git revert (keep monolithic versions)

---

### Phase 8: Validation and Cleanup (Week 7)
**Goal**: Verify migration complete, measure success

**Tasks**:
1. Run 30-second findability tests (target 85% pass rate)
2. Validate all cross-references (no broken links)
3. Update `docs/INDEX.md` (reflect new structure)
4. Archive superseded documentation to `.archive/`
5. Generate metrics report (volume reduction, SOLID scores)

**Validation**: All metrics meet targets

**Rollback**: N/A (measurement phase)

---

## Rollback Considerations

### Git-Based Rollback
All changes are git-tracked. Rollback = `git revert` or `git restore`.

**Safe operations** (create new files):
- Phase 1: Create references
- Phase 6: Create abstractions

**Moderate risk** (edit existing files):
- Phase 2: Update cross-references
- Phase 3: Thin commands
- Phase 4: Split CLAUDE.md

**Higher risk** (delete files):
- Phase 5: Delete glossaries (only after verifying no references)
- Phase 7: Split monolithic TDDs (keep originals in `.archive/`)

### Preserve History
**Strategy**: Move, don't delete
- Monolithic TDDs → `.archive/design/pre-split/`
- Fragmented glossaries → `.archive/glossaries/`
- Old CLAUDE.md → `.archive/CLAUDE.md.pre-split`

### Validation Gates
**Before each phase**:
1. Commit all current work
2. Create feature branch for phase
3. Run validation tests
4. Merge to main only if validation passes

---

## Success Metrics

### Before (Current State - Per Audit)
- **Total documentation**: 572 files, 3.2M
- **Duplication rate**: ~35% (1.1M redundant)
- **30-second findability test**: 40% pass rate
- **Average doc length**: 1200 lines (TDDs), 800 lines (PRDs)
- **Glossary fragmentation**: 12 separate glossaries
- **Broken links**: 40+ in .archive/
- **SOLID score**: 5.0/10 (D)

### After Phase 1-5 (Priority 1 Complete)
- **Total documentation**: ~420 files, 2.3M (-28%)
- **Duplication rate**: ~18% (400KB redundant)
- **30-second findability test**: 70% pass rate (+75% improvement)
- **Average doc length**: 700 lines (TDDs), 500 lines (PRDs)
- **Glossary fragmentation**: 1 canonical glossary
- **Broken links**: <10
- **SOLID score**: 7.5/10 (B-)

### After Phase 6-8 (All Priorities Complete)
- **Total documentation**: ~400 files, 2.0M (-38%)
- **Duplication rate**: ~5% (100KB redundant)
- **30-second findability test**: 85% pass rate (+113% improvement)
- **Average doc length**: 550 lines (TDDs), 400 lines (PRDs)
- **Glossary fragmentation**: 1 canonical glossary
- **Broken links**: 0
- **SOLID score**: 8.5/10 (A-)

### Measurement Method

#### 30-Second Findability Test
**Sample queries** (15 questions):
1. "What is SaveSession?" → Should reach `docs/reference/GLOSSARY.md#savesession` in <30s
2. "How does progressive TTL work?" → Should reach `docs/reference/REF-cache-ttl-strategy.md` in <30s
3. "How do I detect entity type?" → Should reach `docs/reference/REF-detection-tiers.md` in <30s
4. "What command do I use for a hotfix?" → Should reach `docs/reference/REF-command-decision-tree.md` in <30s
5. "How does the dependency graph work?" → Should reach `docs/reference/REF-savesession-lifecycle.md` in <30s
6. ... (15 total)

**Pass rate**: % of queries answered in <30 seconds

**Target**: 85% (13/15 queries)

---

## Governance and Maintenance

### Documentation Review Process

**Before merge**:
1. Author creates PR with documentation changes
2. Run validation checks:
   - Frontmatter valid (status, date, author)
   - No broken links (link checker)
   - Follows template (if PRD/TDD/ADR)
   - No duplication (grep for copied paragraphs)
3. Doc reviewer approves
4. Merge to main

### Preventing Future Duplication

**Rule 1: One Concept, One Location**
Before adding concept explanation to a document, check if it exists in `docs/reference/`. If yes, link to it. If no, consider creating it.

**Rule 2: Commands ≤ 50 Lines**
If command exceeds 50 lines, extract reference material to skill.

**Rule 3: Glossary First**
Before defining a term in a doc, add it to `docs/reference/GLOSSARY.md` first, then reference.

**Rule 4: TDDs ≤ 800 Lines**
If TDD exceeds 800 lines, extract reference material or split into multiple TDDs.

### Automation Opportunities

**Auto-generate**:
- `COMMAND_REGISTRY.md` from command frontmatter (pre-commit hook)
- Link validation report (CI check)
- Document length report (CI check, warn if >800 lines)
- Duplication detection (grep for repeated paragraphs)

**Pre-commit hooks**:
- Validate frontmatter YAML
- Check for broken links
- Warn if document exceeds length threshold
- Check for TODO/FIXME markers

---

## Open Questions for User

### 1. Cache Reference Granularity
**Question**: Should we extract 3 references (architecture, staleness, TTL) or more granular (5-7 references)?

**Option A (Recommended)**: 3 references
- REF-cache-architecture.md (400 lines)
- REF-cache-staleness-detection.md (300 lines)
- REF-cache-ttl-strategy.md (250 lines)

**Option B**: 5-7 references (more granular)
- REF-cache-architecture.md (200 lines - overview only)
- REF-cache-provider-protocol.md (150 lines - already exists)
- REF-cache-staleness-detection.md (300 lines)
- REF-cache-ttl-strategy.md (250 lines)
- REF-cache-population-patterns.md (200 lines - NEW)
- REF-cache-invalidation-strategies.md (150 lines - NEW)

**Trade-off**: Fewer, longer docs vs. more, focused docs

---

### 2. Monolithic TDD Splitting Strategy
**Question**: Should we split TDD-0004-tier2-clients.md into 6 separate TDDs or keep monolithic with better navigation?

**Option A (Recommended)**: Split into 6 TDDs
- TDD-0004-tier2-clients-overview.md (300 lines)
- TDD-0004.1-tasks-client.md through TDD-0004.6-workspaces-client.md (6 × 350 lines)

**Option B**: Keep monolithic, improve navigation
- Add table of contents
- Add jump links
- Keep as single 2179-line file

**Trade-off**: Findability vs. maintaining coherence

---

### 3. Reference Document Location
**Question**: Should reference docs live in `/docs/reference/` or `.claude/reference/`?

**Option A (Recommended)**: `/docs/reference/`
- Formal documentation location
- Accessible outside Claude Code
- Follows existing pattern (REF-* already in docs/reference/)

**Option B**: `.claude/reference/`
- Closer to skills (agent context)
- Separate from formal docs

**Trade-off**: Accessibility vs. agent context co-location

---

### 4. Migration Timeline
**Question**: Should we execute all phases (8 weeks) or stop after Priority 1 (3 weeks)?

**Option A (Recommended)**: Complete all phases
- Maximum benefit (85% findability, 8.5/10 SOLID)
- Prevent future accumulation

**Option B**: Stop after Priority 1
- Quick wins (70% findability, 7.5/10 SOLID)
- Lower effort (10 hours vs. 35 hours)

**Trade-off**: Time investment vs. completeness

---

### 5. Glossary Structure
**Question**: Should the unified glossary be a single file or a directory with sub-files?

**Option A (Recommended)**: Single hierarchical file
- `docs/reference/GLOSSARY.md` (300 lines, sections with anchors)
- Easy to search (Ctrl+F)

**Option B**: Directory with sub-files
- `docs/reference/glossary/agents.md`
- `docs/reference/glossary/workflows.md`
- `docs/reference/glossary/cache.md`
- Easier to navigate if very large

**Trade-off**: Search convenience vs. organization

---

## Next Steps

### For Tech Writer

After Information Architect approval, Tech Writer should:

1. **Review consolidation specs** (Priority 1-3)
2. **Execute Phase 1** (create canonical references)
3. **Execute Phase 2** (update cross-references)
4. **Execute Phase 3** (thin commands)
5. **Execute Phase 4** (split CLAUDE.md)
6. **Execute Phase 5** (delete fragmented glossaries)

**Handoff artifacts**:
- This architecture document (DOC-ARCHITECTURE.md)
- Audit report (AUDIT-doc-synthesis.md)
- Content briefs (embedded in consolidation sections above)

### For Doc Reviewer

After Tech Writer execution, Doc Reviewer should:

1. **Validate 30-second findability** (run test queries)
2. **Validate cross-references** (no broken links)
3. **Validate SOLID compliance** (spot-check violations)
4. **Approve or request revisions**

**Validation report**: `docs/audits/VALIDATION-REPORT-DOC-ARCHITECTURE.md`

---

## Appendix: SOLID Scorecard (Target State)

| Principle | Current | Target | How We Get There |
|-----------|---------|--------|------------------|
| **Single Responsibility** | 3/10 | 9/10 | Split CLAUDE.md, thin commands, extract references from TDDs |
| **Open/Closed** | 6/10 | 9/10 | Unified glossary, canonical references, template-based docs |
| **Liskov Substitution** | 7/10 | 9/10 | Complete command format migration, standardize frontmatter |
| **Interface Segregation** | 4/10 | 9/10 | Thin commands, focused skills, split monolithic TDDs |
| **Dependency Inversion** | 5/10 | 8/10 | Create REF-* abstractions, concept-based references |
| **Overall SOLID Score** | 5.0/10 (D) | 8.8/10 (A-) | Execute all 8 migration phases |

---

**End of Information Architecture Specification**

**Status**: Proposed (awaiting user feedback on open questions)
**Next**: User review → Tech Writer execution → Doc Reviewer validation
