# Documentation Content Briefs

Version: 1.0
Date: 2025-12-24
Author: Information Architect Agent
For: Tech Writer

---

## Overview

This document provides detailed briefs for all new content to be created as part of the documentation restructuring. Each brief specifies location, purpose, audience, scope, source material, and priority.

Total new documents: 13 files (7 READMEs + 3 Reference Docs + 3 Runbooks)

---

## Directory READMEs (7 files)

### CB-001: requirements/README.md

**Location**: `/docs/requirements/README.md`

**Purpose**: Explain what PRDs are, when to create them, and how they're organized

**Audience**: Engineers creating new PRDs, new team members understanding doc structure

**Scope**:
- What is a PRD (Product Requirements Document)
- When to create a PRD vs. other doc types
- Naming conventions (numbered vs. named)
- Status lifecycle (Draft → In Review → Approved → Active → Implemented)
- How PRDs relate to TDDs and ADRs
- Where PROMPT files went (moved to /initiatives/)

**Source Material**:
- [INFORMATION-ARCHITECTURE-SPEC-2025-12-24.md](INFORMATION-ARCHITECTURE-SPEC-2025-12-24.md) - Requirements section
- [INDEX.md](INDEX.md) - PRDs section for examples
- Existing PRD frontmatter for status values

**Priority**: HIGH (Phase 1 - foundation)

**Template**:
```markdown
# Product Requirements Documents (PRDs)

## What Are PRDs?

Product Requirements Documents (PRDs) define **what** we're building and **why** it's valuable. They capture the business need, user stories, success criteria, and feature specifications before implementation begins.

## When to Create a PRD

Create a PRD for:
- New features or capabilities
- Significant enhancements to existing features
- Cross-cutting infrastructure changes
- Features requiring stakeholder approval

Do NOT create a PRD for:
- Bug fixes (unless architectural)
- Refactoring (use ADR instead)
- Documentation updates
- Dependency upgrades

## Naming Conventions

### Numbered PRDs (Legacy)
Format: `PRD-NNNN-descriptive-name.md`
Example: `PRD-0001-sdk-extraction.md`

Used for early sequential allocation. Preserved for git history.

### Named PRDs (Preferred)
Format: `PRD-FEATURE-NAME.md`
Example: `PRD-CACHE-INTEGRATION.md`

**Use named PRDs for all new documents.** They are:
- More searchable
- Self-documenting
- Easier to reference

## Status Lifecycle

Every PRD has a `status:` field in frontmatter:

1. **Draft** - Initial authoring, not yet reviewed
2. **In Review** - Under stakeholder review
3. **Approved** - Approved for implementation
4. **Active** - Currently being implemented
5. **Implemented** - Code in production, feature live
6. **Superseded** - Replaced by different approach (includes link to replacement)
7. **Rejected** - Decided not to implement (includes decision rationale)

**Critical Rule**: STATUS in INDEX.md MUST match status in document frontmatter.

## PRD-TDD Pairing

Every PRD should have a corresponding TDD (Technical Design Document):
- PRD defines WHAT and WHY
- TDD defines HOW

Pairings are tracked in [INDEX.md](../INDEX.md) "PRD" column.

## What Happened to PROMPT-* Files?

PROMPT-0-* and PROMPT-MINUS-1-* files are **orchestrator work coordination files**, not requirements. They have been moved to [`/docs/initiatives/`](../initiatives/).

If you're looking for an initiative kickoff prompt, check `/docs/initiatives/`.

## Creating a New PRD

1. Copy template from existing PRD (e.g., PRD-CACHE-INTEGRATION.md)
2. Use named format: `PRD-FEATURE-NAME.md`
3. Fill out frontmatter (status, created, updated)
4. Write sections: Problem, Solution, Requirements, Success Criteria
5. Add entry to [INDEX.md](../INDEX.md)
6. Create corresponding TDD in `/docs/design/`

## See Also

- [TDD README](../design/README.md) - How PRDs relate to TDDs
- [INDEX.md](../INDEX.md) - Full PRD registry
- [CONTRIBUTION-GUIDE.md](../CONTRIBUTION-GUIDE.md) - Documentation standards
```

---

### CB-002: design/README.md

**Location**: `/docs/design/README.md`

**Purpose**: Explain what TDDs are, how they pair with PRDs, and design doc conventions

**Audience**: Engineers creating technical designs, architects

**Scope**:
- What is a TDD (Technical Design Document)
- PRD-TDD pairing (INDEX.md is source of truth)
- When TDD precedes PRD (exploratory design)
- Status lifecycle (same as PRD, plus NO-GO)
- Architecture vs. Implementation TDDs

**Source Material**:
- [INFORMATION-ARCHITECTURE-SPEC-2025-12-24.md](INFORMATION-ARCHITECTURE-SPEC-2025-12-24.md) - Design section
- [INDEX.md](INDEX.md) - TDDs section
- TDD-0026-crud-base-class-evaluation.md (example of NO-GO)

**Priority**: HIGH (Phase 1 - foundation)

**Template**: Similar structure to CB-001, emphasize PRD-TDD relationship

---

### CB-003: initiatives/README.md

**Location**: `/docs/initiatives/README.md`

**Purpose**: Explain what PROMPT files are, their lifecycle, and archival policy

**Audience**: Users of orchestrator workflow, engineers wondering what PROMPT files are

**Scope**:
- What are PROMPT-0 and PROMPT-MINUS-1 files
- How they differ from PRDs
- Initiative lifecycle (Active → Complete → Archived)
- Archival policy (move to .archive/initiatives/YYYY-QN/)
- How to find archived initiatives

**Source Material**:
- [INFORMATION-ARCHITECTURE-SPEC-2025-12-24.md](INFORMATION-ARCHITECTURE-SPEC-2025-12-24.md) - Initiatives section
- Existing PROMPT-0 files for examples
- [INDEX.md](INDEX.md) - Initiatives section

**Priority**: HIGH (Phase 1 - foundation)

**Template**:
```markdown
# Initiative Coordination Files

## What Are PROMPT Files?

PROMPT files are orchestrator initialization instructions that coordinate multi-agent work on complex initiatives. They are NOT product requirements.

### PROMPT-0 Files
Format: `PROMPT-0-INITIATIVE-NAME.md`

Kickoff prompts for specific initiatives. Contain:
- Initiative context
- Specialist agent assignments
- Phase breakdown
- Success criteria

Example: `PROMPT-0-CACHE-INTEGRATION.md`

### PROMPT-MINUS-1 Files
Format: `PROMPT-MINUS-1-META-NAME.md`

Meta-initiative planning prompts that span multiple related initiatives.

Example: `PROMPT-MINUS-1-CACHE-PERFORMANCE-META.md`

## How PROMPT Files Differ from PRDs

| PROMPT-0 | PRD |
|----------|-----|
| Work coordination | Requirements specification |
| For orchestrator agent | For humans and engineers |
| Temporary (archived when complete) | Permanent (preserved for history) |
| Contains agent instructions | Contains feature specifications |

**If you need feature requirements**, look in [`/docs/requirements/`](../requirements/). Each initiative has a corresponding PRD.

## Initiative Lifecycle

```
Created → Active → Complete → Archived
```

1. **Created**: Initiative kicked off, PROMPT file created
2. **Active**: Work in progress, referenced by agents
3. **Complete**: Initiative finished, validated
4. **Archived**: Moved to `.archive/initiatives/YYYY-QN/`

## Archival Policy

When an initiative status reaches "Complete" (validated with VP-* report), archive the PROMPT file:

```bash
git mv initiatives/PROMPT-0-INITIATIVE-NAME.md .archive/initiatives/2025-Q4/
```

Update [INDEX.md](../INDEX.md) to reflect archive location or remove from active section.

**Completed Initiatives** (archived 2025-Q4):
- PROMPT-0-CACHE-OPTIMIZATION-PHASE2 (VP PASS)
- PROMPT-0-CACHE-PERF-FETCH-PATH (VP PASS)
- PROMPT-0-WATERMARK-CACHE (VALIDATION PASS)
- PROMPT-0-WORKSPACE-PROJECT-REGISTRY (VP APPROVED)

## Finding Archived Initiatives

Check [`.archive/initiatives/`](../.archive/initiatives/) for historical initiative files.

## See Also

- [PRD README](../requirements/README.md) - Formal requirements documents
- [INDEX.md](../INDEX.md) - Active initiatives registry
```

---

### CB-004: planning/README.md

**Location**: `/docs/planning/README.md`

**Purpose**: Explain what planning docs are and when they're archived

**Audience**: Engineers doing sprint planning, looking for sprint decompositions

**Scope**:
- What planning docs contain (sprint decompositions, session notes)
- How sprint docs differ from PRDs
- Archival policy (2 weeks after sprint end)
- Where to find completed sprint docs

**Source Material**:
- Existing PRD-SPRINT-* files for examples
- [INFORMATION-ARCHITECTURE-SPEC-2025-12-24.md](INFORMATION-ARCHITECTURE-SPEC-2025-12-24.md) - Planning section

**Priority**: MEDIUM (Phase 1)

---

### CB-005: planning/sprints/README.md

**Location**: `/docs/planning/sprints/README.md`

**Purpose**: Explain sprint decomposition docs

**Audience**: Sprint participants, engineers referencing past sprint plans

**Scope**:
- What sprint decomposition docs contain
- PRD-SPRINT vs. TDD-SPRINT structure
- How they relate to formal PRDs
- When to archive (2 weeks after sprint completion)

**Source Material**:
- PRD-SPRINT-1-PATTERN-COMPLETION.md (example structure)
- [INFORMATION-ARCHITECTURE-SPEC-2025-12-24.md](INFORMATION-ARCHITECTURE-SPEC-2025-12-24.md)

**Priority**: MEDIUM (Phase 1)

---

### CB-006: reference/README.md

**Location**: `/docs/reference/README.md`

**Purpose**: Explain what reference docs are and when to create them

**Audience**: Engineers implementing features, looking up reference data

**Scope**:
- What reference docs contain (authoritative reference data)
- When to extract to reference (3+ duplication rule)
- How PRDs should link to reference docs
- List of current reference docs

**Source Material**:
- Existing REF-entity-type-table.md, REF-custom-field-catalog.md
- [INFORMATION-ARCHITECTURE-SPEC-2025-12-24.md](INFORMATION-ARCHITECTURE-SPEC-2025-12-24.md) - Reference section

**Priority**: MEDIUM (Phase 1)

**Template**:
```markdown
# Reference Documentation

## What Are Reference Docs?

Reference docs provide **authoritative, single-source-of-truth reference data** used across multiple features and documents. They are extracted when 3+ PRDs/TDDs duplicate the same explanation.

## When to Create a Reference Doc

Extract to reference when:
- Same concept explained in 3+ PRDs or TDDs
- Reference data needed by multiple systems (entity types, field catalogs)
- Algorithm specification used across features (cache staleness, TTL calculation)
- Protocol or interface shared by multiple clients

## Reference Doc Types

### Data Catalogs
Authoritative lists of entities, fields, or resources.

Examples:
- [REF-entity-type-table.md](REF-entity-type-table.md) - Business model hierarchy
- [REF-custom-field-catalog.md](REF-custom-field-catalog.md) - 108 custom fields

### Algorithm Specifications
Detailed specifications of algorithms used across features.

Examples:
- [REF-cache-staleness-detection.md](REF-cache-staleness-detection.md) - Staleness algorithms
- [REF-cache-ttl-strategy.md](REF-cache-ttl-strategy.md) - TTL calculation rules

### Protocol Specifications
Interface contracts and protocol definitions.

Examples:
- [REF-cache-provider-protocol.md](REF-cache-provider-protocol.md) - CacheProvider interface

## How to Use Reference Docs

### In PRDs/TDDs
Instead of duplicating explanations, link to reference:

**Before** (duplicated in 5 PRDs):
```markdown
## TTL Calculation
Base TTL is 3600 seconds for tasks, 7200 for projects...
[500 words of TTL logic]
```

**After** (single reference):
```markdown
## TTL Calculation
See [REF-cache-ttl-strategy](../reference/REF-cache-ttl-strategy.md) for TTL calculation details.
```

## Current Reference Docs

| Document | Type | Description |
|----------|------|-------------|
| [REF-entity-type-table.md](REF-entity-type-table.md) | Data Catalog | Business model entity hierarchy |
| [REF-custom-field-catalog.md](REF-custom-field-catalog.md) | Data Catalog | 108 custom fields across 5 models |
| [REF-cache-staleness-detection.md](REF-cache-staleness-detection.md) | Algorithm | Staleness detection algorithms |
| [REF-cache-ttl-strategy.md](REF-cache-ttl-strategy.md) | Algorithm | TTL calculation and progressive extension |
| [REF-cache-provider-protocol.md](REF-cache-provider-protocol.md) | Protocol | CacheProvider interface specification |

## Creating a New Reference Doc

1. Identify duplication across 3+ PRDs/TDDs
2. Extract common content to `REF-topic-name.md`
3. Write comprehensive, authoritative version
4. Update source PRDs/TDDs to link instead of duplicate
5. Add entry to this README and [INDEX.md](../INDEX.md)

## See Also

- [PRD README](../requirements/README.md) - When to create PRDs
- [INDEX.md](../INDEX.md) - Full documentation registry
```

---

### CB-007: runbooks/README.md

**Location**: `/docs/runbooks/README.md`

**Purpose**: Explain what runbooks are and when to use them

**Audience**: On-call engineers, SREs, incident responders

**Scope**:
- What runbooks contain (troubleshooting procedures)
- When to use a runbook vs. reading TDDs
- Runbook structure (Problem → Symptoms → Investigation → Resolution)
- List of current runbooks

**Source Material**:
- [INFORMATION-ARCHITECTURE-SPEC-2025-12-24.md](INFORMATION-ARCHITECTURE-SPEC-2025-12-24.md) - Runbooks section
- Incident response best practices

**Priority**: HIGH (created in Phase 1, runbooks in Phase 6)

**Template**:
```markdown
# Operational Runbooks

## What Are Runbooks?

Runbooks are **step-by-step troubleshooting guides** for diagnosing and resolving production issues. They are written for on-call engineers responding to incidents.

## When to Use a Runbook

Use a runbook when:
- Production system is failing or degraded
- Alert fired and you need to investigate
- User reported issue and you need to diagnose
- You need quick operational guidance (not deep architecture understanding)

**For architectural understanding**, see TDDs in [`/docs/design/`](../design/).
**For feature context**, see PRDs in [`/docs/requirements/`](../requirements/).

## Runbook Structure

All runbooks follow this format:

1. **Problem Statement** - What is failing?
2. **Symptoms** - How do you know it's this problem?
3. **Investigation Steps** - How to diagnose the root cause
4. **Resolution** - How to fix it
5. **Prevention** - How to prevent recurrence

## Current Runbooks

| Runbook | System | Use When |
|---------|--------|----------|
| [RUNBOOK-cache-troubleshooting.md](RUNBOOK-cache-troubleshooting.md) | Cache | Cache misses, staleness issues, TTL problems, degraded performance |
| [RUNBOOK-savesession-debugging.md](RUNBOOK-savesession-debugging.md) | SaveSession | Save failures, dependency graph errors, partial failures, healing system issues |
| [RUNBOOK-detection-system-debugging.md](RUNBOOK-detection-system-debugging.md) | Detection | Entity type detection failures, tier fallback issues |

## Creating a New Runbook

1. Identify recurring production issue
2. Document symptoms and investigation steps
3. Write resolution procedures
4. Test runbook during next incident
5. Add entry to this README and incident response playbook

## See Also

- [TDDs](../design/) - For architectural deep dives
- [ADRs](../decisions/) - For understanding why system works this way
```

---

## Reference Documentation (3 files)

### CB-008: REF-cache-staleness-detection.md

**Location**: `/docs/reference/REF-cache-staleness-detection.md`

**Purpose**: Single source of truth for cache staleness detection algorithms and heuristics

**Audience**: Engineers implementing cache integration, debugging staleness issues

**Scope**:
- Include: Staleness detection algorithms (watermark, TTL, progressive extension), heuristics, edge cases, when to use each approach
- Exclude: Implementation details (those stay in TDDs), deployment procedures (those go in runbooks)

**Source Material**:
- PRD-CACHE-LIGHTWEIGHT-STALENESS.md - Lightweight staleness section
- PRD-CACHE-OPTIMIZATION-P2.md - Staleness heuristics
- PRD-WATERMARK-CACHE.md - Watermark-based staleness
- TDD-CACHE-LIGHTWEIGHT-STALENESS.md - Algorithm details
- ADR-0019-staleness-detection-algorithm.md - Original decision
- ADR-0133-progressive-ttl-extension-algorithm.md - Progressive extension
- ADR-0134-staleness-check-integration-pattern.md - Integration patterns

**Related Documentation**:
- REF-cache-ttl-strategy.md (TTL calculation)
- REF-cache-provider-protocol.md (Integration)
- RUNBOOK-cache-troubleshooting.md (Operations)

**Priority**: HIGH (Phase 5 - consolidation)

**Estimated Size**: 8-10K

**Structure**:
```markdown
# Cache Staleness Detection Reference

## Overview
[What staleness detection is and why it matters]

## Staleness Detection Approaches

### 1. TTL-Based Staleness
[When TTL expires, data is stale]

### 2. Watermark-Based Staleness
[Track modification timestamps]

### 3. Progressive TTL Extension
[Extend TTL when data unchanged]

## Algorithms

### Lightweight Staleness Detection
[Algorithm specification from ADR-0133]

### Watermark Staleness Check
[Algorithm from PRD-WATERMARK-CACHE]

## Heuristics

### When to Check Staleness
- On cache hit (lightweight check)
- Before returning cached data (full check)
- Background refresh (proactive)

### Trade-offs
| Approach | Accuracy | Performance | Use Case |
|----------|----------|-------------|----------|
| TTL-based | Medium | High | General purpose |
| Watermark | High | Medium | Critical data |
| Progressive | High | High | Stable data |

## Edge Cases

### Race Conditions
[How staleness detection handles concurrent updates]

### Clock Skew
[How TTL handles clock drift]

### Cache Invalidation
[Relationship between staleness and explicit invalidation]

## Integration Patterns

[How to integrate staleness checks - reference ADR-0134]

## Related Documentation

- [REF-cache-ttl-strategy.md](REF-cache-ttl-strategy.md) - TTL calculation
- [ADR-0019](../decisions/ADR-0019-staleness-detection-algorithm.md) - Original decision
- [ADR-0133](../decisions/ADR-0133-progressive-ttl-extension-algorithm.md) - Progressive extension
- [RUNBOOK-cache-troubleshooting.md](../runbooks/RUNBOOK-cache-troubleshooting.md) - Troubleshooting
```

---

### CB-009: REF-cache-ttl-strategy.md

**Location**: `/docs/reference/REF-cache-ttl-strategy.md`

**Purpose**: Single source of truth for TTL calculation and progressive extension

**Audience**: Engineers implementing cache clients, tuning cache performance

**Scope**:
- Include: Base TTL calculation, entity type multipliers, progressive extension algorithm, TTL tuning guidelines
- Exclude: Staleness detection (see REF-cache-staleness-detection.md), implementation code

**Source Material**:
- PRD-CACHE-INTEGRATION.md - Base TTL section
- PRD-CACHE-LIGHTWEIGHT-STALENESS.md - Progressive TTL extension
- PRD-CACHE-OPTIMIZATION-P2.md - TTL tuning
- PRD-WATERMARK-CACHE.md - Watermark TTL
- TDD-CACHE-INTEGRATION.md - TTL implementation
- ADR-0126-entity-ttl-resolution.md - Entity-specific TTL
- ADR-0133-progressive-ttl-extension-algorithm.md - Extension algorithm

**Related Documentation**:
- REF-cache-staleness-detection.md (Staleness algorithms)
- REF-cache-provider-protocol.md (Cache integration)

**Priority**: HIGH (Phase 5 - consolidation)

**Estimated Size**: 6-8K

**Structure**:
```markdown
# Cache TTL Strategy Reference

## Overview
[What TTL is and how it controls cache lifetime]

## Base TTL Calculation

### Default TTL Values
| Entity Type | Base TTL | Rationale |
|-------------|----------|-----------|
| Task | 3600s (1h) | Frequently modified |
| Project | 7200s (2h) | Less frequently modified |
| Portfolio | 14400s (4h) | Rarely modified |
| Custom Field Defs | 86400s (24h) | Stable |

### Entity Type Multipliers
[How entity type affects TTL]

## Progressive TTL Extension

### Algorithm
[From ADR-0133: How TTL extends when data remains unchanged]

### Extension Rules
- First access: Base TTL
- Second access (unchanged): Base TTL * 1.5
- Third access (unchanged): Base TTL * 2.0
- Max extension: Base TTL * 4.0

### Reset Conditions
[When TTL resets to base value]

## TTL Tuning Guidelines

### When to Increase TTL
- Data changes infrequently
- Acceptable staleness window is large
- Performance is priority over freshness

### When to Decrease TTL
- Data changes frequently
- Freshness is critical
- Staleness causes user-facing issues

## TTL vs. Staleness Detection

| Mechanism | Purpose | When Used |
|-----------|---------|-----------|
| TTL | Define cache lifetime | Always (passive) |
| Staleness Detection | Verify freshness | On access (active) |

TTL sets upper bound, staleness detection provides early detection.

## Implementation Notes

[How to calculate TTL in CacheProvider implementations]

## Related Documentation

- [REF-cache-staleness-detection.md](REF-cache-staleness-detection.md) - Staleness algorithms
- [ADR-0126](../decisions/ADR-0126-entity-ttl-resolution.md) - Entity TTL resolution
- [ADR-0133](../decisions/ADR-0133-progressive-ttl-extension-algorithm.md) - Progressive extension
```

---

### CB-010: REF-cache-provider-protocol.md

**Location**: `/docs/reference/REF-cache-provider-protocol.md`

**Purpose**: CacheProvider protocol specification for cache integrations

**Audience**: Engineers implementing cache clients, integrating caching into new systems

**Scope**:
- Include: CacheProvider protocol methods, integration patterns, extension points, implementation examples
- Exclude: Specific cache backends (Redis, S3), deployment procedures

**Source Material**:
- PRD-CACHE-INTEGRATION.md - CacheProvider definition
- PRD-CACHE-PERF-FETCH-PATH.md - Fetch path integration
- PRD-CACHE-PERF-DETECTION.md - Detection caching
- PRD-CACHE-PERF-HYDRATION.md - Hydration caching
- PRD-CACHE-PERF-STORIES.md - Stories caching
- TDD-CACHE-INTEGRATION.md - Protocol implementation
- ADR-0123-cache-provider-selection.md - Provider selection
- ADR-0124-client-cache-pattern.md - Client integration pattern

**Related Documentation**:
- REF-cache-staleness-detection.md
- REF-cache-ttl-strategy.md

**Priority**: HIGH (Phase 5 - consolidation)

**Estimated Size**: 10-12K

**Structure**:
```markdown
# Cache Provider Protocol Reference

## Overview
[What CacheProvider is and why it exists]

## Protocol Definition

### Core Methods

#### get(key: str, default: T = None) -> Optional[T]
[Get cached value by key]

#### set(key: str, value: T, ttl: int = None) -> None
[Set cached value with optional TTL]

#### delete(key: str) -> None
[Delete cached value]

#### exists(key: str) -> bool
[Check if key exists]

#### get_multi(keys: List[str]) -> Dict[str, T]
[Batch get operation]

#### set_multi(items: Dict[str, T], ttl: int = None) -> None
[Batch set operation]

### Extension Methods

[Optional methods for advanced functionality]

## Integration Patterns

### Client Cache Pattern
[From ADR-0124: How to integrate caching into resource clients]

### Post-Commit Hook Pattern
[How to invalidate cache on data changes]

### Batch Population Pattern
[How to populate cache efficiently]

## Implementation Examples

### Minimal CacheProvider
```python
class SimpleCacheProvider(CacheProvider):
    def get(self, key: str, default=None):
        # Implementation

    def set(self, key: str, value, ttl=None):
        # Implementation
```

### With Staleness Detection
[Integration with staleness checks]

### With TTL Extension
[Integration with progressive TTL]

## Cache Key Conventions

### Entity Keys
Format: `{entity_type}:{gid}`
Example: `task:1234567890123456`

### Collection Keys
Format: `{entity_type}:collection:{scope}:{id}`
Example: `task:collection:project:9876543210987654`

### Custom Keys
[Guidelines for non-entity keys]

## Error Handling

### Graceful Degradation
[From ADR-0127: How to handle cache failures]

### Fallback Strategies
- Cache miss → Fetch from API
- Cache error → Bypass cache, log error
- Cache unavailable → Operate without cache

## Performance Considerations

### Serialization
[How data is serialized/deserialized]

### Batch Operations
[When to use get_multi vs. individual gets]

## Related Documentation

- [PRD-CACHE-INTEGRATION](../requirements/PRD-CACHE-INTEGRATION.md) - Cache requirements
- [TDD-CACHE-INTEGRATION](../design/TDD-CACHE-INTEGRATION.md) - Implementation details
- [ADR-0123](../decisions/ADR-0123-cache-provider-selection.md) - Provider selection
- [ADR-0124](../decisions/ADR-0124-client-cache-pattern.md) - Client integration
```

---

## Runbooks (3 files)

### CB-011: RUNBOOK-cache-troubleshooting.md

**Location**: `/docs/runbooks/RUNBOOK-cache-troubleshooting.md`

**Purpose**: Guide on-call engineers through diagnosing and resolving cache issues

**Audience**: On-call engineers, SREs responding to cache-related incidents

**Scope**:
- Include: Symptoms, investigation steps, resolution procedures, prevention
- Exclude: Architecture deep dives (link to TDDs instead)

**Source Material**:
- TDD-CACHE-INTEGRATION.md - Error handling section
- ADR-0127-graceful-degradation.md - Fallback strategies
- Recent cache-related incidents (if available)
- Interview with engineer who built cache system

**Related Documentation**:
- REF-cache-staleness-detection.md
- REF-cache-ttl-strategy.md
- TDD-CACHE-INTEGRATION.md

**Priority**: HIGH (Phase 6 - operational necessity)

**Estimated Time**: 1 hour (includes SME interview)

**Structure**:
```markdown
# Cache Troubleshooting Runbook

## Quick Diagnosis

| Symptom | Likely Cause | Jump To |
|---------|--------------|---------|
| High cache miss rate | TTL too short, invalidation too aggressive | [Section: Cache Misses](#cache-misses) |
| Stale data served | Staleness detection disabled, TTL too long | [Section: Stale Data](#stale-data) |
| Cache errors in logs | Redis connection issues, serialization failures | [Section: Cache Errors](#cache-errors) |
| Slow API calls despite cache | Cache not being populated, keys mismatch | [Section: Cache Not Working](#cache-not-working) |

## Problem 1: Cache Misses

### Symptoms
- Metrics show high miss rate (>50%)
- API latency increased
- Logs show "cache miss" frequently

### Investigation Steps

1. Check cache hit rate metrics
   ```bash
   # Redis CLI
   INFO stats
   # Look for: keyspace_hits, keyspace_misses
   ```

2. Check TTL configuration
   ```python
   # In code or config
   DEFAULT_TTL_SECONDS = ?
   ```

3. Check cache key consistency
   ```bash
   # Redis CLI
   KEYS task:*
   # Verify expected keys exist
   ```

4. Check invalidation strategy
   [Where is cache being invalidated?]

### Resolution

**If TTL too short**:
- Increase base TTL (see [REF-cache-ttl-strategy](../reference/REF-cache-ttl-strategy.md))
- Enable progressive TTL extension

**If keys mismatch**:
- Fix cache key generation
- Clear cache and repopulate

**If over-invalidation**:
- Review invalidation hooks
- Reduce invalidation scope

### Prevention
- Monitor cache hit rate (alert if <70%)
- Set TTL based on data change frequency
- Use progressive TTL for stable data

## Problem 2: Stale Data

### Symptoms
- Users see outdated data
- Changes not reflected immediately
- Staleness detection logs show stale hits

### Investigation Steps

1. Check when data was last updated
   ```bash
   # Redis CLI
   TTL task:1234567890123456
   # If high TTL, might be stale
   ```

2. Check staleness detection
   [Is it enabled? What's the threshold?]

3. Check cache invalidation
   [Was cache invalidated on update?]

### Resolution

**If staleness detection disabled**:
- Enable lightweight staleness checks
- See [REF-cache-staleness-detection](../reference/REF-cache-staleness-detection.md)

**If TTL too long**:
- Reduce base TTL for frequently changing entities
- Use watermark-based staleness

**If invalidation missing**:
- Add post-commit invalidation hook
- See [ADR-0137](../decisions/ADR-0137-post-commit-invalidation-hook.md)

### Prevention
- Enable staleness detection for critical data
- Set appropriate TTL based on data volatility
- Monitor staleness metrics

## Problem 3: Cache Errors

### Symptoms
- Exceptions in logs: `CacheError`, `SerializationError`
- Cache operations failing
- Fallback to API working

### Investigation Steps

1. Check cache connectivity
   ```bash
   # Redis CLI
   PING
   # Should return PONG
   ```

2. Check logs for error details
   ```bash
   grep "CacheError" application.log
   ```

3. Check serialization
   [What data failed to serialize?]

### Resolution

**If Redis unavailable**:
- Check Redis server status
- Verify network connectivity
- Graceful degradation should be active (see [ADR-0127](../decisions/ADR-0127-graceful-degradation.md))

**If serialization error**:
- Check data types being cached
- Ensure all cached objects are serializable
- Update serialization logic if needed

### Prevention
- Monitor Redis health
- Alert on cache error rate >1%
- Test serialization for new entity types

## Problem 4: Cache Not Working

### Symptoms
- Cache appears healthy
- API calls slow despite cache enabled
- No cache hits in metrics

### Investigation Steps

1. Check if cache is wired in code
   ```python
   # In client code
   self.cache = cache_provider  # Is this set?
   ```

2. Check cache key generation
   ```python
   # Print generated keys
   print(f"Cache key: {key}")
   ```

3. Check cache population
   [Is data being set in cache after fetch?]

### Resolution

**If cache not wired**:
- Integrate CacheProvider (see [REF-cache-provider-protocol](../reference/REF-cache-provider-protocol.md))
- Follow client cache pattern ([ADR-0124](../decisions/ADR-0124-client-cache-pattern.md))

**If cache not populated**:
- Add cache.set() after API fetch
- Use batch population for collections

### Prevention
- Test cache integration in new clients
- Monitor cache population rate

## Emergency Procedures

### Clear Entire Cache
```bash
# Redis CLI
FLUSHDB
```
**Use only as last resort.** Cache will rebuild gradually.

### Disable Cache (Emergency)
```python
# In config or environment
CACHE_ENABLED = False
```
Application will fall back to API calls.

## Related Documentation

- [TDD-CACHE-INTEGRATION](../design/TDD-CACHE-INTEGRATION.md) - Architecture
- [REF-cache-staleness-detection](../reference/REF-cache-staleness-detection.md) - Staleness algorithms
- [REF-cache-ttl-strategy](../reference/REF-cache-ttl-strategy.md) - TTL tuning
- [ADR-0127](../decisions/ADR-0127-graceful-degradation.md) - Graceful degradation
```

---

### CB-012: RUNBOOK-savesession-debugging.md

**Location**: `/docs/runbooks/RUNBOOK-savesession-debugging.md`

**Purpose**: Guide engineers through debugging SaveSession failures

**Audience**: Engineers debugging save failures, on-call responding to save incidents

**Scope**:
- Include: Common save failures, dependency graph errors, partial failure handling, healing system issues
- Exclude: SaveSession architecture (link to TDD-0010)

**Source Material**:
- TDD-0010-save-orchestration.md - Error handling, dependency graph
- PRD-0018-savesession-reliability.md - Reliability requirements
- ADR-0035-unit-of-work-pattern.md - Unit of Work pattern
- ADR-0040-partial-failure-handling.md - Partial failure strategies
- SaveSession code in `src/autom8_asana/save/`

**Related Documentation**:
- TDD-0010-save-orchestration.md
- PRD-0018-savesession-reliability.md

**Priority**: HIGH (Phase 6 - operational necessity)

**Estimated Time**: 1 hour

**Structure**: Similar to CB-011, focus on save failures, dependency graph errors, healing system

---

### CB-013: RUNBOOK-detection-system-debugging.md

**Location**: `/docs/runbooks/RUNBOOK-detection-system-debugging.md`

**Purpose**: Guide engineers through debugging entity type detection failures

**Audience**: Engineers debugging detection issues, on-call responding to type detection failures

**Scope**:
- Include: Detection tier system, fallback failures, membership resolution issues
- Exclude: Detection architecture (link to TDD-DETECTION)

**Source Material**:
- TDD-DETECTION.md - Tier system, error handling
- PRD-DETECTION.md - Detection requirements
- ADR-0068-type-detection-strategy.md - Detection strategy
- Detection code in `src/autom8_asana/detection/`

**Related Documentation**:
- TDD-DETECTION.md
- PRD-DETECTION.md

**Priority**: MEDIUM (Phase 6)

**Estimated Time**: 1 hour

**Structure**: Similar to CB-011, focus on tier fallback, membership resolution, type ambiguity

---

## Consolidated Summary

| Brief ID | Document | Type | Priority | Estimated Time | Phase |
|----------|----------|------|----------|----------------|-------|
| CB-001 | requirements/README.md | Directory README | HIGH | 30 min | 1 |
| CB-002 | design/README.md | Directory README | HIGH | 30 min | 1 |
| CB-003 | initiatives/README.md | Directory README | HIGH | 30 min | 1 |
| CB-004 | planning/README.md | Directory README | MEDIUM | 15 min | 1 |
| CB-005 | planning/sprints/README.md | Directory README | MEDIUM | 15 min | 1 |
| CB-006 | reference/README.md | Directory README | MEDIUM | 20 min | 1 |
| CB-007 | runbooks/README.md | Directory README | HIGH | 20 min | 1 |
| CB-008 | REF-cache-staleness-detection.md | Reference Doc | HIGH | 45 min | 5 |
| CB-009 | REF-cache-ttl-strategy.md | Reference Doc | HIGH | 30 min | 5 |
| CB-010 | REF-cache-provider-protocol.md | Reference Doc | HIGH | 45 min | 5 |
| CB-011 | RUNBOOK-cache-troubleshooting.md | Runbook | HIGH | 1 hour | 6 |
| CB-012 | RUNBOOK-savesession-debugging.md | Runbook | HIGH | 1 hour | 6 |
| CB-013 | RUNBOOK-detection-system-debugging.md | Runbook | MEDIUM | 1 hour | 6 |

**Total Estimated Time**: 7-8 hours

---

## Handoff to Tech Writer

**Priority Order**:
1. **Phase 1** (2 hours): Create all 7 directory READMEs - foundation for navigation
2. **Phase 5** (2 hours): Create 3 cache reference docs - reduce duplication
3. **Phase 6** (3 hours): Create 3 runbooks - operational necessity

**Deliverables**:
- 13 new markdown files
- All files linked from INDEX.md
- Cross-references added to related documents

**Quality Criteria**:
- READMEs explain what belongs in directory and how to use it
- Reference docs consolidate duplicated content from source PRDs
- Runbooks provide actionable troubleshooting steps
- All documents have proper frontmatter
- All documents linked from INDEX.md

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-24 | Initial content briefs based on IA spec |
