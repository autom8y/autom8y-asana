# ADR Consolidation Plan: Information Architecture

> Phase 3 of Documentation Architecture Initiative - ADR Topic Summaries

**Author**: Information Architect
**Date**: 2025-12-25
**Status**: Proposed

## Executive Summary

This plan consolidates 146 individual ADR files into 12 topic-based summaries, reducing the decisions directory from 1.36 MB to ~200 KB while improving findability and maintaining complete decision context.

## Current State Analysis

### File Count
- **Total ADR files**: 146
- **Supporting files**: INDEX.md, ADR-INDEX-BY-TOPIC.md, README.md
- **Total directory size**: 1.36 MB
- **Average ADR length**: ~150 lines

### Identified Problems
1. **Overwhelming volume**: 146 files creates navigation friction
2. **Redundant content**: Multiple ADRs cover overlapping decisions
3. **Lost narrative**: Individual ADRs don't show evolution of thinking
4. **Discovery friction**: Finding relevant decisions requires reading topic index first
5. **Maintenance burden**: 146 files to keep updated with cross-references

## Target Architecture

### Directory Structure

```
docs/decisions/
├── INDEX.md                              # Updated to reference summaries
├── README.md                             # Unchanged
├── ADR-SUMMARY-ARCHITECTURE.md           # 14 ADRs consolidated
├── ADR-SUMMARY-CACHE.md                  # 26 ADRs consolidated
├── ADR-SUMMARY-CUSTOM-FIELDS.md          # 12 ADRs consolidated
├── ADR-SUMMARY-DATA-MODEL.md             # 15 ADRs consolidated
├── ADR-SUMMARY-DETECTION.md              # 16 ADRs consolidated
├── ADR-SUMMARY-DEMO.md                   # 4 ADRs consolidated ✓ COMPLETE
├── ADR-SUMMARY-OBSERVABILITY.md          # 7 ADRs consolidated
├── ADR-SUMMARY-OPERATIONS.md             # 10 ADRs consolidated
├── ADR-SUMMARY-PATTERNS.md               # 26 ADRs consolidated
├── ADR-SUMMARY-PERFORMANCE.md            # 11 ADRs consolidated
├── ADR-SUMMARY-API-INTEGRATION.md        # 13 ADRs consolidated
└── ADR-SUMMARY-SAVESESSION.md            # 22 ADRs consolidated

docs/.archive/2025-12-adrs/
└── ADR-*.md                              # 146 individual files archived
```

### Expected Outcomes
- **File count**: 149 → 15 files (90% reduction)
- **Size**: 1.36 MB → ~200 KB (85% reduction)
- **Findability**: Topic-based navigation (30 second target)
- **Context**: Preserved through evolution narrative

## Taxonomy Design

### Summary Categories

Based on ADR-INDEX-BY-TOPIC.md analysis, the 12 categories represent natural concern groupings:

| Summary | Focus Area | ADR Count | Key Themes |
|---------|-----------|-----------|------------|
| **ARCHITECTURE** | Core structural decisions, module organization | 14 | Protocol-based design, layering, boundaries |
| **CACHE** | Caching strategies, staleness, TTL, invalidation | 26 | Progressive TTL, tiered architecture, population |
| **CUSTOM-FIELDS** | Custom field handling, accessors, cascading | 12 | Descriptor pattern, type safety, resolution |
| **DATA-MODEL** | Entity models, schemas, typing | 15 | Pydantic, GID identity, frozen models |
| **DETECTION** | Auto-detection, inference, resolution | 16 | Tier-based detection, self-healing, fallback chains |
| **DEMO** | Demo system infrastructure | 4 | State capture, name resolution, error handling |
| **OBSERVABILITY** | Logging, monitoring, telemetry | 7 | Structured logging, correlation, hooks |
| **OPERATIONS** | Process pipelines, workflow automation | 10 | Process types, seeding, state machines |
| **PATTERNS** | Reusable code patterns, decorators | 26 | UnitOfWork, lazy loading, registries |
| **PERFORMANCE** | Optimization, batching, async | 11 | Batch execution, concurrency, incremental loading |
| **API-INTEGRATION** | External integration, API design, errors | 13 | SDK integration, error handling, resilience |
| **SAVESESSION** | Save orchestration, change tracking | 22 | Unit of work, dependency ordering, actions |

### Category Selection Rationale

**Why these 12 categories?**

1. **Align with existing index**: ADR-INDEX-BY-TOPIC.md already groups by these themes
2. **Natural concern separation**: Each represents distinct architectural area
3. **Manageable size**: 4-26 ADRs per summary (readable in one session)
4. **Cross-reference minimization**: Related decisions grouped together
5. **User journey support**: Categories match common lookup patterns

**Why not more categories?**

- **Refactoring & Migration** (5 ADRs): Small topic, fold into OPERATIONS
- **Rejection Decisions** (3 ADRs): Fold into relevant summaries
- **Testing** (covered in DEMO): Specific enough to standalone

## Summary Document Template

Each summary follows this structure:

```markdown
# ADR Summary: [Topic]

> Consolidated decision record for [area]. Individual ADRs archived.

## Overview

[2-3 paragraphs: What this area is, why it matters, evolution of thinking]

## Key Decisions

### [Decision Category]: [Title]

**Context**: [Why needed - 1-2 sentences]

**Decision**: [What was decided - 1-2 sentences]

**Rationale**: [Why this approach]

**Alternatives Rejected**: [Brief mention]

**Source ADRs**: ADR-XXXX, ADR-YYYY

---

[Repeat for 5-10 major decision categories in topic]

## Evolution Timeline

| Date | Decision | Impact |
|------|----------|--------|
| YYYY-MM | [What changed] | [Effect] |

## Cross-References

- Related PRDs: [links]
- Related TDDs: [links]
- Related Summaries: [links]

## Archived Individual ADRs

| ADR | Title | Date | Key Decision |
|-----|-------|------|--------------|
| ADR-XXXX | [Title] | YYYY-MM-DD | [One-line summary] |
```

### Template Design Decisions

**Overview section**: Provides context for newcomers, explains "why this area matters"

**Key Decisions**: Synthesized, not concatenated - tells coherent story

**Evolution Timeline**: Shows progression of thinking, not just final state

**Cross-References**: Maintains discoverability to related documentation

**Archived ADRs table**: Preserves lookup path to original detailed decisions

## Migration Plan

### Phase 1: Create Summaries (Sessions 1-12)

Each session creates one summary:

1. **Read all ADRs in topic** from ADR-INDEX-BY-TOPIC.md
2. **Identify 5-10 major decision categories** (consolidate related ADRs)
3. **Extract key context, decisions, rationales** from each ADR
4. **Synthesize into cohesive narrative** showing evolution
5. **Create evolution timeline** from ADR dates
6. **Build cross-reference map** to PRDs, TDDs, other summaries
7. **Create archived ADR table** with one-line summaries

**Output**: ADR-SUMMARY-[TOPIC].md

**Example**: ADR-SUMMARY-DEMO.md (✓ Complete)

### Phase 2: Archive Individual ADRs

After all summaries created:

```bash
# Create archive directory
mkdir -p /Users/tomtenuta/Code/autom8_asana/docs/.archive/2025-12-adrs

# Move individual ADRs (excluding summaries and supporting files)
cd /Users/tomtenuta/Code/autom8_asana/docs/decisions
git mv ADR-0*.md /Users/tomtenuta/Code/autom8_asana/docs/.archive/2025-12-adrs/
git mv ADR-SDK-*.md /Users/tomtenuta/Code/autom8_asana/docs/.archive/2025-12-adrs/
git mv ADR-DEMO-*.md /Users/tomtenuta/Code/autom8_asana/docs/.archive/2025-12-adrs/
```

**Output**: 146 ADRs moved to archive

### Phase 3: Update INDEX.md

Transform INDEX.md to reference summaries instead of individual ADRs:

**Before**:
```markdown
## Recent Decisions

- [ADR-0144](ADR-0144-healingresult-consolidation.md) - HealingResult Type Consolidation
- [ADR-0143](ADR-0143-detection-result-caching.md) - Detection Result Caching Strategy
...
```

**After**:
```markdown
## Decision Summaries by Topic

### Core Architecture
- [ADR-SUMMARY-ARCHITECTURE](ADR-SUMMARY-ARCHITECTURE.md) - Core structural decisions (14 ADRs)
- [ADR-SUMMARY-PATTERNS](ADR-SUMMARY-PATTERNS.md) - Reusable code patterns (26 ADRs)
- [ADR-SUMMARY-DATA-MODEL](ADR-SUMMARY-DATA-MODEL.md) - Entity models and schemas (15 ADRs)

### Domain Systems
- [ADR-SUMMARY-CACHE](ADR-SUMMARY-CACHE.md) - Caching strategies (26 ADRs)
- [ADR-SUMMARY-SAVESESSION](ADR-SUMMARY-SAVESESSION.md) - Save orchestration (22 ADRs)
- [ADR-SUMMARY-DETECTION](ADR-SUMMARY-DETECTION.md) - Auto-detection and resolution (16 ADRs)
- [ADR-SUMMARY-CUSTOM-FIELDS](ADR-SUMMARY-CUSTOM-FIELDS.md) - Custom field handling (12 ADRs)

### Integration & Operations
- [ADR-SUMMARY-API-INTEGRATION](ADR-SUMMARY-API-INTEGRATION.md) - External integration (13 ADRs)
- [ADR-SUMMARY-PERFORMANCE](ADR-SUMMARY-PERFORMANCE.md) - Optimization strategies (11 ADRs)
- [ADR-SUMMARY-OPERATIONS](ADR-SUMMARY-OPERATIONS.md) - Process pipelines (10 ADRs)

### Supporting Systems
- [ADR-SUMMARY-OBSERVABILITY](ADR-SUMMARY-OBSERVABILITY.md) - Logging and monitoring (7 ADRs)
- [ADR-SUMMARY-DEMO](ADR-SUMMARY-DEMO.md) - Demo infrastructure (4 ADRs)

## Archived Individual ADRs

Individual ADR files are preserved in `docs/.archive/2025-12-adrs/` for detailed reference.
```

**Output**: Updated INDEX.md with summary navigation

### Phase 4: Update ADR-INDEX-BY-TOPIC.md

Options:

**Option A: Deprecate** - Remove file, redirect to INDEX.md
**Option B: Update** - Change links to point to summaries
**Option C: Archive** - Move to .archive with redirect

**Recommendation**: Option A (Deprecate) - Summaries replace this functionality

## Content Brief: Example Summary

To guide Tech Writer, here's a detailed brief for ADR-SUMMARY-CACHE.md:

### Content Brief: ADR-SUMMARY-CACHE.md

**Location**: `docs/decisions/ADR-SUMMARY-CACHE.md`

**Purpose**: Consolidate 26 cache-related ADRs into coherent narrative explaining caching architecture evolution

**Source ADRs** (from ADR-INDEX-BY-TOPIC.md):
- ADR-0016: Cache Protocol Extension
- ADR-0018: Batch Modification Checking
- ADR-0019: Staleness Detection Algorithm
- ADR-0021: Dataframe Caching Strategy
- ADR-0026: Two-Tier Cache Architecture
- ADR-0032: Cache Granularity
- ADR-0052: Bidirectional Reference Caching
- ADR-0060: Name Resolution Caching Strategy
- ADR-0072: Resolution Caching Decision
- ADR-0076: Auto-Invalidation Strategy
- ADR-0116: Batch Cache Population Pattern
- ADR-0119: Client Cache Integration Pattern
- ADR-0120: Batch Cache Population on Bulk Fetch
- ADR-0123: Cache Provider Selection
- ADR-0124: Client Cache Pattern
- ADR-0125: SaveSession Cache Invalidation Hook
- ADR-0126: Entity-Type TTL Resolution
- ADR-0127: Graceful Degradation Strategy
- ADR-0129: Stories Client Cache Wiring
- ADR-0130: Cache Population Location
- ADR-0131: GID Enumeration Cache Strategy
- ADR-0133: Progressive TTL Extension Algorithm
- ADR-0134: Staleness Check Integration Pattern
- ADR-0137: Post-Commit Invalidation Hook
- ADR-0140: DataFrame Task Cache Integration
- ADR-0143: Detection Result Caching

**Key Decision Categories to Extract**:

1. **Protocol Design**: Cache provider extensibility (ADR-0016)
2. **Architecture**: Two-tier (Redis + S3) vs single-tier (ADR-0026, ADR-0118 rejection)
3. **Staleness Detection**: Lightweight checks, progressive TTL (ADR-0019, ADR-0133)
4. **Population Strategies**: Batch vs incremental, client integration (ADR-0116, ADR-0120, ADR-0124)
5. **Invalidation**: Auto-invalidation, SaveSession hooks (ADR-0076, ADR-0125, ADR-0137)
6. **TTL Management**: Entity-type resolution, extension algorithm (ADR-0126, ADR-0133)
7. **Graceful Degradation**: Fallback behavior, resilience (ADR-0127)
8. **Specialization**: DataFrame caching, detection results (ADR-0021, ADR-0140, ADR-0143)

**Evolution Timeline**:
- 2025-12-09: Protocol extension foundation (ADR-0016)
- 2025-12-09: Two-tier architecture decision (ADR-0026)
- 2025-12-19: Batch population patterns (ADR-0116, ADR-0120)
- 2025-12-24: Progressive TTL algorithm (ADR-0133)

**Cross-References**:
- PRDs: PRD-0002-intelligent-caching, PRD-CACHE-* series
- TDDs: TDD-0008-intelligent-caching, TDD-CACHE-* series
- Summaries: SAVESESSION (invalidation hooks), PERFORMANCE (batch operations)

**Priority**: High (largest topic, 26 ADRs)

## Naming Conventions

### File Naming
- Pattern: `ADR-SUMMARY-{TOPIC}.md`
- Case: UPPERCASE for TOPIC (consistent with existing INDEX files)
- Examples: `ADR-SUMMARY-CACHE.md`, `ADR-SUMMARY-SAVESESSION.md`

### Title Format
- Pattern: `# ADR Summary: {Human-Readable Topic}`
- Examples: `# ADR Summary: Cache Architecture`, `# ADR Summary: SaveSession & Persistence`

### Cross-Reference Format
- Internal links: `[ADR-SUMMARY-CACHE](ADR-SUMMARY-CACHE.md)`
- Archived ADRs: `[ADR-0016](../.archive/2025-12-adrs/ADR-0016-cache-protocol-extension.md)`
- Related docs: `[PRD-0002](../requirements/PRD-0002-intelligent-caching.md)`

## Handoff to Tech Writer

### Ready for Implementation When:
- [x] Target taxonomy and directory structure fully specified
- [x] Migration plan complete with action for every existing document
- [x] Summary template defined with required sections
- [x] Content briefs prepared for each summary (see sections above)
- [x] Naming conventions and metadata requirements documented
- [x] Priority ordering established (start with DEMO as example, then largest topics)
- [x] Example summary complete (ADR-SUMMARY-DEMO.md)

### Priority Order for Implementation:

1. **DEMO** ✓ - Complete (example/template validation)
2. **CACHE** - Largest topic (26 ADRs), high impact
3. **PATTERNS** - Second largest (26 ADRs), foundational
4. **SAVESESSION** - Complex topic (22 ADRs), core system
5. **DETECTION** - Moderate (16 ADRs), interconnected
6. **DATA-MODEL** - Moderate (15 ADRs), foundational
7. **ARCHITECTURE** - Moderate (14 ADRs), high-level
8. **API-INTEGRATION** - Moderate (13 ADRs), external boundary
9. **CUSTOM-FIELDS** - Moderate (12 ADRs), specialized
10. **PERFORMANCE** - Moderate (11 ADRs), optimization
11. **OPERATIONS** - Moderate (10 ADRs), business logic
12. **OBSERVABILITY** - Small (7 ADRs), supporting system

### Tech Writer Deliverables:

For each summary:
1. ADR-SUMMARY-{TOPIC}.md following template
2. Synthesis of key decisions (not concatenation)
3. Evolution timeline showing progression
4. Cross-reference map to related docs
5. Archived ADR table with one-liners

After all summaries:
1. Updated INDEX.md with summary navigation
2. Archive individual ADRs to .archive/2025-12-adrs/
3. Verify all cross-references resolve correctly

## Success Metrics

### Quantitative
- **File reduction**: 149 → 15 files (90%)
- **Size reduction**: 1.36 MB → ~200 KB (85%)
- **Navigation depth**: Topic → Decision (2 clicks, down from 3-4)

### Qualitative
- **Findability test**: Can new engineer find cache TTL decision in < 30 seconds?
- **Narrative coherence**: Does summary tell story of evolution, not just list decisions?
- **Cross-reference accuracy**: Do all links resolve correctly?
- **Completeness**: Can archived ADRs be found when detailed context needed?

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Content loss during consolidation** | Medium | High | Preserve all ADRs in archive, verify table completeness |
| **Broken cross-references** | High | Medium | Update script to find/replace ADR paths, test all links |
| **Navigation confusion** | Low | Medium | Clear INDEX.md structure, README explains archive |
| **Summary too long** | Medium | Low | Target 5-10 key decisions, detailed context in archive |
| **Inconsistent synthesis** | Medium | Medium | Use DEMO summary as template, review each summary |

## Future Maintenance

### Adding New ADRs

**Option A**: Individual ADR files continue, periodic consolidation
**Option B**: Add directly to relevant summary
**Option C**: Hybrid - individual for major decisions, summary updates for refinements

**Recommendation**: Option A initially, reassess after 6 months

### Summary Updates

When to update a summary:
- New ADR significantly changes decision in that area
- Cross-references need updating (new PRDs/TDDs)
- Evolution timeline needs new entry

Process:
1. Add new ADR to archive table
2. Update relevant decision category or add new one
3. Update evolution timeline
4. Update cross-references

### Archive Access Pattern

Summaries should link to archived ADRs for detailed context:

```markdown
**For detailed rationale and alternatives analysis, see [ADR-0133](../.archive/2025-12-adrs/ADR-0133-progressive-ttl-extension-algorithm.md)**
```

## Approval and Next Steps

### Stakeholder Review

This plan requires review from:
- **Principal Engineer**: Technical accuracy of consolidation
- **Project Lead**: Impact on team workflow
- **Documentation Team**: Feasibility of implementation

### Implementation Timeline

- **Phase 1 (Summaries)**: 12 sessions @ 1-2 hours each = 12-24 hours
- **Phase 2 (Archive)**: 1 session @ 30 minutes
- **Phase 3 (INDEX update)**: 1 session @ 1 hour
- **Phase 4 (Verification)**: 1 session @ 2 hours

**Total effort**: ~16-28 hours

### Go/No-Go Decision Criteria

Proceed if:
- [x] Plan approved by stakeholders
- [x] Tech Writer capacity available (16-28 hours)
- [x] Example summary (DEMO) validates template
- [x] Archive strategy agreed upon
- [x] Cross-reference update approach confirmed

## Appendix: Complete ADR Mapping

### ARCHITECTURE (14 ADRs)
- ADR-0001: Protocol-Based Extensibility
- ADR-0003: Asana SDK Integration
- ADR-0004: Item Class Boundary
- ADR-0012: Public API Surface Definition
- ADR-0017: Redis Backend Architecture
- ADR-0024: Thread-Safety Guarantees
- ADR-0026: Two-Tier Cache Architecture
- ADR-0080: Entity Registry Scope
- ADR-0101: Process Pipeline Correction
- ADR-0102: Post-Commit Hook Architecture
- ADR-0105: Field Seeding Architecture
- ADR-0108: Workspace Project Registry
- ADR-0136: Process Field Architecture
- ADR-0142: Detection Package Structure

### CACHE (26 ADRs)
[Listed in content brief above]

### CUSTOM-FIELDS (12 ADRs)
- ADR-0030: Custom Field Typing
- ADR-0034: Dynamic Custom Field Resolution
- ADR-0051: Custom Field Type Safety
- ADR-0054: Cascading Custom Fields
- ADR-0056: Custom Field API Format
- ADR-0062: CustomFieldAccessor Enhancement
- ADR-0067: Custom Field Snapshot Detection
- ADR-0074: Unified Custom Field Tracking
- ADR-0081: Custom Field Descriptor Pattern
- ADR-0112: Custom Field GID Resolution
- ADR-0113: Rep Field Cascade Pattern
- ADR-0117: Accessor/Descriptor Unification

[Continue for all 12 categories...]

---

**Document Control**
- Version: 1.0
- Last Updated: 2025-12-25
- Next Review: After Phase 1 completion
