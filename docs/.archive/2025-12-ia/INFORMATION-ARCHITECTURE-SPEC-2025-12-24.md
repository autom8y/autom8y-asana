# Documentation Information Architecture Specification

Version: 1.0
Date: 2025-12-24
Author: Information Architect Agent

---

## Executive Summary

This specification defines the target documentation structure for the autom8_asana project based on the findings from the 2025-12-24 Documentation Audit. The design optimizes for the **30-second findability test**: Can an engineer find what they need in under 30 seconds?

**Key Problems Addressed:**
1. 15 PROMPT-* files (280K) misplaced in `/requirements/` instead of `/initiatives/`
2. INDEX.md status divergence from actual document frontmatter (10+ docs affected)
3. Sprint planning docs (PRD-SPRINT-*) mixed with formal requirements
4. Cache documentation redundancy across 9 PRDs/9 TDDs
5. Missing operational runbooks and directory READMEs

**Design Principles:**
- **Flat over deep**: Two-level hierarchy maximum for core documentation
- **Single source of truth**: Each concept documented once, cross-referenced elsewhere
- **Status accuracy**: INDEX.md reflects reality, not wishful thinking
- **Git history preservation**: Prefer moves over renames for numbered docs

---

## Taxonomy Overview

```
/docs/
├── requirements/          # Formal PRDs (what we're building and why)
├── design/               # Formal TDDs (how we're building it)
├── decisions/            # ADRs (why we chose this approach)
├── testing/              # Test Plans (how we verify it works)
├── validation/           # Validation Reports (proof that it works)
├── initiatives/          # PROMPT-* orchestrator files (work coordination)
├── planning/             # Sprint decomposition and temporary planning docs
├── reference/            # Authoritative reference data (entity types, field catalogs, cache algorithms)
├── runbooks/             # Operational troubleshooting guides
├── guides/               # User-facing how-tos and tutorials
├── analysis/             # Discovery and gap analysis artifacts
├── reports/              # Initiative completion reports
├── migration/            # Migration guides for breaking changes
├── architecture/         # High-level architecture diagrams and overviews
└── .archive/             # Completed/superseded/historical content
```

---

## Category Definitions

### `/requirements/` - Formal Product Requirements
**Purpose**: Document what features we're building and why they're valuable
**Audience**: Product owners, engineers (understanding context), stakeholders
**Entry point**: [INDEX.md](INDEX.md) PRDs section
**Content**: PRD-* files only (numbered and named)

**Naming Convention**:
- Numbered: `PRD-NNNN-descriptive-name.md` (e.g., PRD-0001-sdk-extraction.md)
- Named: `PRD-FEATURE-NAME.md` (e.g., PRD-CACHE-INTEGRATION.md)
- All lowercase with hyphens

**Status Values** (in frontmatter):
- `Draft` - Initial authoring, not yet approved
- `In Review` - Under review by stakeholders
- `Approved` - Approved for implementation
- `Active` - Currently being implemented
- `Implemented` - Code in production
- `Superseded` - Replaced by different approach (link to replacement)
- `Rejected` - Decided not to implement (link to decision)

**What Does NOT Belong Here**:
- PROMPT-* files (move to `/initiatives/`)
- Sprint decomposition docs (move to `/planning/`)
- Analysis documents (move to `/analysis/`)

### `/design/` - Technical Design Documents
**Purpose**: Document how features are implemented architecturally
**Audience**: Engineers (implementing and maintaining code)
**Entry point**: [INDEX.md](INDEX.md) TDDs section
**Content**: TDD-* files only (numbered and named), paired with PRDs

**Naming Convention**: Same as PRDs, prefixed with `TDD-`

**Status Values**: Same as PRDs, plus:
- `NO-GO` - Design explicitly rejected (e.g., TDD-0026-crud-base-class)

**Pairing**: Each TDD references its corresponding PRD. INDEX.md tracks pairings.

### `/decisions/` - Architecture Decision Records
**Purpose**: Document significant architectural decisions and their rationale
**Audience**: Engineers (understanding why system works this way)
**Entry point**: [INDEX.md](INDEX.md) ADRs section
**Content**: ADR-* files (numbered, topically organized)

**Status**: Immutable once published. Superseded ADRs remain for historical context.

### `/initiatives/` - Orchestrator Work Coordination
**Purpose**: Store PROMPT-0 and PROMPT-MINUS-1 orchestrator initialization files
**Audience**: Orchestrator agent, meta-planning workflows
**Entry point**: [INDEX.md](INDEX.md) Initiatives section
**Content**:
- `PROMPT-0-*.md` - Initiative kickoff prompts
- `PROMPT-MINUS-1-*.md` - Meta-initiative planning prompts

**Lifecycle**:
1. Created at initiative start
2. Active during implementation
3. Archived to `.archive/initiatives/YYYY-QN/` after completion

**What Belongs Here**: Work coordination files, NOT formal requirements (those go in `/requirements/`)

### `/planning/` - Temporary Planning Artifacts
**Purpose**: Store sprint decompositions and temporary planning documents
**Audience**: Engineering team during sprint planning
**Entry point**: [INDEX.md](INDEX.md) or sprint tracking system
**Content**:
- `/planning/sprints/` - Sprint decomposition docs (PRD-SPRINT-*, TDD-SPRINT-*)
- `/planning/sessions/` - Session notes and temporary analysis

**Lifecycle**:
- Created during sprint planning
- Referenced during sprint
- Archived to `.archive/planning/YYYY-QN/` after sprint completion (recommended: archive within 2 weeks of sprint end)

**Naming Convention**: `PRD-SPRINT-N-description.md`, `TDD-SPRINT-N-description.md`

### `/reference/` - Authoritative Reference Data
**Purpose**: Single source of truth for reference data used across multiple documents
**Audience**: Engineers (quick lookup during implementation)
**Entry point**: [INDEX.md](INDEX.md) Reference Data section
**Content**:
- Entity type hierarchies
- Custom field catalogs
- Cache algorithm specifications
- TTL strategy definitions
- Staleness detection algorithms

**Naming Convention**: `REF-topic-name.md` (e.g., `REF-cache-staleness-detection.md`)

**Key Principle**: Reference docs are extracted when 3+ PRDs/TDDs duplicate the same explanation. PRDs then link to reference docs instead of duplicating.

**Recommended New Reference Docs** (from cache cluster):
- `REF-cache-staleness-detection.md` - Staleness detection algorithms
- `REF-cache-ttl-strategy.md` - TTL calculation and progressive extension
- `REF-cache-provider-protocol.md` - CacheProvider protocol specification

### `/runbooks/` - Operational Troubleshooting
**Purpose**: Guide on-call engineers through debugging and resolving production issues
**Audience**: On-call engineers, SREs, incident responders
**Entry point**: Incident response playbook or on-call handbook
**Content**: Step-by-step troubleshooting procedures for operational issues

**Naming Convention**: `RUNBOOK-system-issue.md` (e.g., `RUNBOOK-cache-troubleshooting.md`)

**Structure**: Problem → Symptoms → Investigation Steps → Resolution → Prevention

**Recommended New Runbooks**:
- `RUNBOOK-cache-troubleshooting.md` - Cache failures, staleness issues, TTL problems
- `RUNBOOK-savesession-debugging.md` - SaveSession failures, dependency graph issues
- `RUNBOOK-detection-system-debugging.md` - Entity type detection failures

### `/testing/` - Test Plans
**Purpose**: Document test strategies and acceptance criteria for features
**Audience**: QA engineers, developers writing tests
**Entry point**: [INDEX.md](INDEX.md) Test Plans section
**Content**: TP-* test plans for formal features

**Status**: Draft → Approved → PASS/FAIL

### `/validation/` - Validation Reports
**Purpose**: Evidence that implemented features meet requirements
**Audience**: Stakeholders, compliance, retrospectives
**Entry point**: [INDEX.md](INDEX.md) Validation Reports section
**Content**: VP-* validation reports, point-in-time test results

**Status**: PASS, FAIL, APPROVED, Invalidated

### `/guides/` - User-Facing How-Tos
**Purpose**: Help engineers use the SDK and understand workflows
**Audience**: SDK users, new team members
**Entry point**: Project README or [INDEX.md](INDEX.md) Guides section
**Content**: Tutorials, quickstarts, concept explainers, pattern guides

**Stability**: High - guides should remain valid across versions

### `/analysis/` - Discovery Artifacts
**Purpose**: Capture discovery sessions, gap analyses, and investigative work
**Audience**: Engineers doing deep dives, retrospectives
**Entry point**: [INDEX.md](INDEX.md) Analysis Documents section
**Content**: DISCOVERY-*, GAP-ANALYSIS-*, ANALYSIS-*, IMPACT-* documents

**Lifecycle**: Created during discovery, referenced by PRDs/TDDs, eventually archived

### `/reports/` - Initiative Completion Reports
**Purpose**: Document outcomes and learnings from completed initiatives
**Audience**: Stakeholders, future engineers learning from past work
**Entry point**: [INDEX.md](INDEX.md) Initiative Reports section
**Content**: REPORT-* summary documents

### `/.archive/` - Historical Content
**Purpose**: Preserve completed/superseded content for historical reference
**Audience**: Archaeology, retrospectives, understanding decisions
**Structure**:
```
.archive/
├── initiatives/
│   └── 2025-Q4/          # Completed PROMPT-* files
├── planning/
│   └── 2025-Q4-sprints/  # Completed sprint docs
├── discovery/            # Old discovery artifacts
├── validation/           # Old validation reports
└── historical/           # Other archived content
```

**Archival Policy**:
- PROMPT-* files: Archive when initiative status = "Complete"
- Sprint docs: Archive within 2 weeks of sprint completion
- Superseded PRDs/TDDs: Do NOT archive - add supersession notice, keep in place for history
- Discovery docs: Archive after 1 year if not referenced

---

## Directory Structure (Target State)

```
/docs/
├── INDEX.md                          # Central registry (SSOT for doc status)
├── DOC-AUDIT-REPORT-*.md             # Audit artifacts
├── DOC-AUDIT-SUMMARY-*.md
├── DOC-INVENTORY-*.csv
├── INFORMATION-ARCHITECTURE-SPEC-*.md
├── MIGRATION-PLAN-*.md
├── CONTENT-BRIEFS-*.md
├── CONTRIBUTION-GUIDE.md             # How to add/update docs
│
├── requirements/                     # 47 PRDs (after PROMPT-* moved, SPRINT-* moved)
│   ├── README.md                     # (NEW) What PRDs are, naming conventions
│   ├── PRD-0001-*.md ... PRD-0024-*.md  # Numbered PRDs (preserved)
│   └── PRD-CACHE-*.md, PRD-DETECTION.md, etc.  # Named PRDs
│
├── design/                           # 53 TDDs (after SPRINT-* moved)
│   ├── README.md                     # (NEW) What TDDs are, PRD-TDD pairing
│   ├── TDD-0001-*.md ... TDD-0030-*.md  # Numbered TDDs (preserved)
│   └── TDD-CACHE-*.md, TDD-DETECTION.md, etc.  # Named TDDs
│
├── decisions/                        # 135 ADRs (no changes)
│   └── ADR-0001-*.md ... ADR-0134-*.md
│
├── testing/                          # 9 test plans (no changes)
│   └── TP-0001-*.md ... TP-0009-*.md
│
├── validation/                       # 8 validation reports (no changes)
│   └── VP-*.md, VALIDATION-*.md
│
├── initiatives/                      # 27 PROMPT files (15 moved from requirements/)
│   ├── README.md                     # (NEW) What PROMPT files are, lifecycle
│   ├── PROMPT-0-*.md                 # Initiative prompts
│   └── PROMPT-MINUS-1-*.md           # Meta-initiative prompts
│
├── planning/                         # (NEW) Sprint and temporary planning
│   ├── README.md                     # (NEW) Sprint planning process
│   └── sprints/
│       ├── PRD-SPRINT-*.md           # (MOVED from requirements/)
│       └── TDD-SPRINT-*.md           # (MOVED from design/)
│
├── reference/                        # Authoritative reference data
│   ├── README.md                     # (NEW) What reference docs are
│   ├── REF-entity-type-table.md      # Existing
│   ├── REF-custom-field-catalog.md   # Existing
│   ├── REF-cache-staleness-detection.md  # (NEW) Extracted from cache PRDs
│   ├── REF-cache-ttl-strategy.md     # (NEW) Extracted from cache PRDs
│   └── REF-cache-provider-protocol.md  # (NEW) Extracted from cache PRDs
│
├── runbooks/                         # (NEW) Operational troubleshooting
│   ├── README.md                     # (NEW) What runbooks are, when to use
│   ├── RUNBOOK-cache-troubleshooting.md  # (NEW)
│   ├── RUNBOOK-savesession-debugging.md  # (NEW)
│   └── RUNBOOK-detection-system-debugging.md  # (NEW)
│
├── guides/                           # 7 guides (no changes)
│   └── concepts.md, quickstart.md, workflows.md, etc.
│
├── analysis/                         # 21 analysis docs (no changes)
│   └── DISCOVERY-*.md, GAP-ANALYSIS-*.md, etc.
│
├── reports/                          # 1 report (no changes)
│   └── REPORT-CACHE-OPTIMIZATION-P2.md
│
├── migration/                        # 1 migration guide (no changes)
│   └── MIGRATION-ASYNC-METHOD.md
│
├── architecture/                     # Architecture overviews (no changes)
│
└── .archive/                         # Historical content
    ├── initiatives/
    │   └── 2025-Q4/                  # (MOVE) Completed PROMPT files
    │       ├── PROMPT-0-CACHE-OPTIMIZATION-PHASE2.md
    │       ├── PROMPT-0-CACHE-PERF-FETCH-PATH.md
    │       ├── PROMPT-0-WATERMARK-CACHE.md
    │       └── PROMPT-0-WORKSPACE-PROJECT-REGISTRY.md
    └── planning/
        └── 2025-Q4-sprints/          # (Future) Completed sprint docs
```

---

## Naming Conventions

### Document Naming

| Document Type | Pattern | Example |
|---------------|---------|---------|
| Numbered PRD | `PRD-NNNN-descriptive-name.md` | `PRD-0001-sdk-extraction.md` |
| Named PRD | `PRD-FEATURE-NAME.md` | `PRD-CACHE-INTEGRATION.md` |
| Numbered TDD | `TDD-NNNN-descriptive-name.md` | `TDD-0001-sdk-architecture.md` |
| Named TDD | `TDD-FEATURE-NAME.md` | `TDD-CACHE-INTEGRATION.md` |
| ADR | `ADR-NNNN-decision-name.md` | `ADR-0001-protocol-extensibility.md` |
| Test Plan | `TP-NNNN-feature-name.md` | `TP-0001-sdk-phase1-parity.md` |
| Validation Report | `VP-FEATURE-NAME.md` or `VALIDATION-FEATURE.md` | `VP-CACHE-OPTIMIZATION-P2.md` |
| Reference Doc | `REF-topic-name.md` | `REF-cache-staleness-detection.md` |
| Runbook | `RUNBOOK-system-issue.md` | `RUNBOOK-cache-troubleshooting.md` |
| Initiative Prompt | `PROMPT-0-INITIATIVE-NAME.md` | `PROMPT-0-CACHE-INTEGRATION.md` |
| Meta-Initiative | `PROMPT-MINUS-1-META-NAME.md` | `PROMPT-MINUS-1-CACHE-PERFORMANCE-META.md` |
| Sprint Planning | `PRD-SPRINT-N-description.md` | `PRD-SPRINT-1-PATTERN-COMPLETION.md` |
| Discovery | `DISCOVERY-TOPIC.md` | `DISCOVERY-PROCESS-PIPELINE.md` |
| Gap Analysis | `GAP-ANALYSIS-TOPIC.md` | `GAP-ANALYSIS-CACHE-UTILIZATION.md` |
| Report | `REPORT-INITIATIVE.md` | `REPORT-CACHE-OPTIMIZATION-P2.md` |

**Case Convention**: All lowercase with hyphens (kebab-case)

**Number Allocation**:
- PRDs: Next = PRD-0025 (prefer named going forward)
- TDDs: Next = TDD-0031 (prefer named going forward)
- ADRs: Next = ADR-0135 (numbered required for immutability)
- TPs: Next = TP-0010

**Naming Philosophy**:
- **Numbered** (legacy): Used for early sequential allocation. Preserves git history, but hard to search.
- **Named** (preferred): Descriptive, searchable, self-documenting. Use for all new docs unless numbering required.

### Frontmatter Requirements

All PRDs and TDDs MUST include:

```yaml
---
status: Draft|In Review|Approved|Active|Implemented|Superseded|Rejected|NO-GO
created: YYYY-MM-DD
updated: YYYY-MM-DD
pr: (optional) Link to implementing PR
superseded_by: (if Superseded) Link to replacement
decision: (if Rejected/NO-GO) Link to decision ADR
---
```

**Critical Rule**: INDEX.md status MUST match document frontmatter status. Divergence is a documentation bug.

---

## Navigation Design

### Primary Entry Points

| User Journey | Entry Point | Navigation Path |
|--------------|-------------|-----------------|
| **New engineer onboarding** | Project README → [guides/quickstart.md](guides/quickstart.md) | Concepts → Tutorials → Guides |
| **Feature development reference** | [INDEX.md](INDEX.md) → PRDs/TDDs | PRD (why) → TDD (how) → ADRs (decisions) |
| **Debugging production issue** | `/runbooks/README.md` → Specific runbook | Symptoms → Investigation → Resolution |
| **Understanding architecture** | [architecture/](architecture/) → ADRs | System overview → Decision rationale |
| **Contributing code** | [CONTRIBUTION-GUIDE.md](CONTRIBUTION-GUIDE.md) | Doc conventions → PR process |
| **Understanding why we made decision X** | [INDEX.md](INDEX.md) ADRs section → Topic | Topic index → Specific ADR |

### Cross-Reference Strategy

**Inline Links**: Use sparingly for critical context
- Format: `See [PRD-CACHE-INTEGRATION](../requirements/PRD-CACHE-INTEGRATION.md) for requirements.`

**See Also Sections**: Use at document end for related docs
```markdown
## Related Documentation
- **Requirements**: [PRD-CACHE-INTEGRATION](../requirements/PRD-CACHE-INTEGRATION.md)
- **Architecture**: [ADR-0123-cache-provider-selection](../decisions/ADR-0123-cache-provider-selection.md)
- **Reference**: [REF-cache-staleness-detection](../reference/REF-cache-staleness-detection.md)
```

**INDEX.md Pairing**: PRD-TDD pairs tracked in INDEX.md "PRD" column (source of truth)

**Supersession Notices**: At top of superseded documents
```markdown
> **SUPERSEDED**: This document has been superseded by [ADR-0101](../decisions/ADR-0101-process-pipeline-correction.md).
> Preserved for historical context. Do not implement.
```

### Search Optimization

**Keywords**: Include common search terms in document titles and first paragraphs
- Cache documents: "cache", "caching", "staleness", "TTL", "invalidation"
- SaveSession: "save", "unit of work", "orchestration", "dependency graph"
- Detection: "entity type", "detection", "membership", "tier"

**Aliases**: Use INDEX.md for alternative names
- "CRUD Base Class" → Links to PRD-0022 (Rejected)
- "Async Method Generator" → Links to PRD-0021 (Superseded by decorator)

---

## Consolidation Opportunities

### Cache Documentation Cluster (9 PRDs, 9 TDDs)

**Problem**: Staleness detection, TTL strategy, and cache provider protocol explained in 3-5+ documents each

**Solution**: Extract to reference docs, link from PRDs

**New Reference Docs**:
1. **REF-cache-staleness-detection.md**
   - Extract from: PRD-CACHE-LIGHTWEIGHT-STALENESS, PRD-CACHE-OPTIMIZATION-P2, PRD-WATERMARK-CACHE
   - Content: Staleness detection algorithms, heuristics, edge cases
   - Size: ~8-10K (comprehensive)

2. **REF-cache-ttl-strategy.md**
   - Extract from: PRD-CACHE-INTEGRATION, PRD-CACHE-OPTIMIZATION-P2, PRD-CACHE-LIGHTWEIGHT-STALENESS, PRD-WATERMARK-CACHE
   - Content: Base TTL calculation, progressive extension, entity type multipliers
   - Size: ~6-8K

3. **REF-cache-provider-protocol.md**
   - Extract from: PRD-CACHE-INTEGRATION, PRD-CACHE-PERF-FETCH-PATH, PRD-CACHE-PERF-DETECTION, PRD-CACHE-PERF-HYDRATION, PRD-CACHE-PERF-STORIES
   - Content: CacheProvider protocol spec, implementation examples, extension points
   - Size: ~10-12K

**Benefit**: Reduce duplication from ~100K to ~30K of reference docs, single source of truth

**Migration**: Tech Writer updates PRDs to replace explanations with:
```markdown
For staleness detection details, see [REF-cache-staleness-detection](../reference/REF-cache-staleness-detection.md).
```

---

## Metadata Schema

### Document Frontmatter (Required)

```yaml
---
status: <Status Value>       # See status values by doc type
created: YYYY-MM-DD          # Initial creation date
updated: YYYY-MM-DD          # Last significant update
author: <Name or Agent>      # Primary author (optional)
pr: <PR URL>                 # Implementing PR (optional)
superseded_by: <Doc Link>    # Replacement doc (if Superseded)
decision: <ADR Link>         # Decision rationale (if Rejected/NO-GO)
paired_with: <Doc Link>      # TDD→PRD or PRD→TDD (optional, INDEX.md is SSOT)
---
```

### INDEX.md Entry (Required for PRDs/TDDs/ADRs)

Every formal document MUST have an INDEX.md entry:
- PRD: Title, Status, Link
- TDD: Title, Paired PRD, Status, Link
- ADR: Included in count, linked from topic sections

**Validation Rule**: `status` in INDEX.md MUST equal `status` in document frontmatter

---

## Migration Sequencing

See [MIGRATION-PLAN-2025-12-24.md](MIGRATION-PLAN-2025-12-24.md) for detailed phasing.

**Summary**:
1. **Phase 1**: Create new directories, READMEs (no disruption)
2. **Phase 2**: Move PROMPT-* files to `/initiatives/`
3. **Phase 3**: Move sprint docs to `/planning/sprints/`
4. **Phase 4**: Archive completed PROMPT-* to `.archive/initiatives/2025-Q4/`
5. **Phase 5**: Create reference docs, update PRDs to link
6. **Phase 6**: Create runbooks
7. **Phase 7**: Fix INDEX.md status divergence
8. **Phase 8**: Add supersession notices

**Constraint**: Preserve git history by using `git mv` for all relocations

---

## Maintenance Processes

### Documentation Lifecycle

```
Draft → In Review → Approved → Active → Implemented
                                    ↓
                               Superseded → Archived (PROMPT-* only)
                                    ↓
                               Rejected
```

**Transition Criteria**:
- **Draft → In Review**: Author ready for review
- **In Review → Approved**: Stakeholder sign-off
- **Approved → Active**: Implementation started (commit exists)
- **Active → Implemented**: Code merged to main, feature in production
- *** → Superseded**: Different approach chosen (add supersession notice, link to replacement)
- *** → Rejected**: Decision not to implement (add decision link, keep for context)

### Status Synchronization

**Weekly Validation** (automated CI check recommended):
```bash
# Pseudo-script
for doc in $(find docs/requirements docs/design -name "*.md"); do
  frontmatter_status=$(grep "^status:" $doc | cut -d: -f2)
  index_status=$(grep $doc docs/INDEX.md | extract_status)
  if [ "$frontmatter_status" != "$index_status" ]; then
    echo "DIVERGENCE: $doc"
  fi
done
```

**Manual Review Trigger**: Any commit that changes PRD/TDD frontmatter status

### Archival Policy

| Content Type | Archive When | Destination |
|--------------|--------------|-------------|
| PROMPT-0-* (completed) | Initiative status = "Complete" | `.archive/initiatives/YYYY-QN/` |
| PROMPT-0-* (superseded) | Initiative abandoned | `.archive/initiatives/YYYY-QN/` |
| Sprint planning docs | 2 weeks after sprint end | `.archive/planning/YYYY-QN-sprints/` |
| Discovery docs | 1 year after creation, if unreferenced | `.archive/discovery/` |
| Validation reports | 1 year after creation | `.archive/validation/` |
| Superseded PRDs/TDDs | **NEVER** - keep in place with notice | N/A |

**Rationale**: Superseded PRDs/TDDs provide historical context for decisions. Archiving them loses git blame and discoverability.

---

## Success Metrics

Post-implementation, these should be true:

- [ ] INDEX.md status matches document frontmatter (100% accuracy)
- [ ] Zero PROMPT-* files in `/requirements/` directory
- [ ] All implemented features have `status: Implemented` in docs
- [ ] All superseded docs have prominent notices linking to replacements
- [ ] Cache concept duplication reduced from ~100K to ~30K
- [ ] Engineers can find doc status in INDEX.md in <10 seconds
- [ ] New engineers can find quickstart guide from README in <30 seconds
- [ ] On-call engineers can find cache troubleshooting runbook in <60 seconds
- [ ] All directories have README.md explaining their purpose

---

## Handoff to Tech Writer

See:
- [MIGRATION-PLAN-2025-12-24.md](MIGRATION-PLAN-2025-12-24.md) - Step-by-step migration actions
- [CONTENT-BRIEFS-2025-12-24.md](CONTENT-BRIEFS-2025-12-24.md) - New content specifications
- [CONTRIBUTION-GUIDE.md](CONTRIBUTION-GUIDE.md) - Documentation conventions (to be created)

**Priority Order**:
1. Fix INDEX.md status divergence (highest impact, fastest fix)
2. Relocate PROMPT-* files (reduces confusion)
3. Add supersession notices (prevents wasted time)
4. Create directory READMEs (improves navigation)
5. Extract cache reference docs (reduces duplication)
6. Create runbooks (operational necessity)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-24 | Initial specification based on audit findings |
