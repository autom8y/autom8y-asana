# Information Architecture Specification: BusinessSeeder v2

> **Initiative**: BusinessSeeder v2 Documentation
> **Architect**: information-architect
> **Date**: 2025-12-28
> **Status**: Ready for Tech Writer

---

## Executive Summary

This specification defines the documentation structure for BusinessSeeder v2 composite matching capabilities. The design addresses 16 undocumented environment variables, 7 new matching module files (~1,779 lines), and orphaned code references (FR-M-001 through FR-M-012, ADR-SEEDER-003/004).

**Core Decision**: Amend existing documents rather than create new ones. BusinessSeeder v2 is an enhancement to the existing business domain, not a separate system.

**Rationale**:
1. PRD-06 and TDD-08 already cover BusinessSeeder; v2 extends this architecture
2. Creating PRD-12/TDD-13 would fragment related content and complicate navigation
3. Amendment preserves the "30-second findability" principle - engineers look for seeder docs in business domain
4. New ADR required for Fellegi-Sunter decision (significant architectural choice)
5. New reference doc for configuration (follows established REF-* pattern)

---

## 1. Architecture Decision: Amend vs Create

### Recommendation: AMEND existing PRD-06/TDD-08

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Amend PRD-06/TDD-08** | Single source of truth; existing navigation works; follows consolidation pattern | Larger documents | **RECOMMENDED** |
| Create PRD-12/TDD-13 | Smaller documents; clear v1/v2 boundary | Fragments seeder docs; complicates navigation; breaks established pattern | Not recommended |
| Create PRD-06-AMENDMENT | Preserves original; explicit versioning | Requires reading 2 docs for complete picture; hard to maintain | Not recommended |

**Exception: ADR-0058** - Create new ADR for Fellegi-Sunter matching decision. ADRs are immutable historical records; amendments violate their purpose.

---

## 2. Target Document Structure

### 2.1 Documents to Amend

| Document | Amendment Scope | New Content Size (est) |
|----------|-----------------|------------------------|
| `/docs/requirements/PRD-06-business-domain.md` | Add FR-M-* requirements section, user stories | +3K |
| `/docs/design/TDD-08-business-domain.md` | Add Section 8: Composite Matching Architecture | +5K |

### 2.2 Documents to Create

| Document | Location | Purpose | Size (est) |
|----------|----------|---------|------------|
| `ADR-0058-fellegi-sunter-matching.md` | `/docs/decisions/` | Architectural decision for probabilistic matching | 4K |
| `REF-seeder-matching-config.md` | `/docs/reference/` | Configuration reference for 16 SEEDER_* variables | 3K |
| `GUIDE-businessseeder-v2.md` | `/docs/guides/` | Integration guide for v2 usage | 4K |

### 2.3 Documents NOT to Create

| Document | Reason |
|----------|--------|
| PRD-12-matching | Would fragment BusinessSeeder docs; v2 extends existing PRD-06 |
| TDD-13-matching | Would fragment design docs; matching is part of TDD-08 |
| ADR-SEEDER-003/004 | Code references these; create as ADR-0058/0059 following numbering convention |
| RUNBOOK-matching | Lower priority; defer to Tier 3 |

---

## 3. Amendment Specifications

### 3.1 PRD-06-business-domain.md Amendments

**Location**: After existing FR-SEED section (line ~197)

**New Section**: `### FR-M: Composite Matching Requirements`

```markdown
### FR-M: Composite Matching Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-M-001 | MatchingEngine uses Fellegi-Sunter log-odds model for probabilistic matching | Must | Implemented |
| FR-M-002 | Composite field comparison across email, phone, name, domain, address | Must | Implemented |
| FR-M-003 | Normalizers transform input fields to canonical form before comparison | Must | Implemented |
| FR-M-004 | Blocking rules reduce candidate set for O(n) performance | Must | Implemented |
| FR-M-005 | Configuration via SEEDER_* environment variables | Must | Implemented |
| FR-M-006 | Term frequency adjustment for common value discrimination | Should | Implemented |
| FR-M-007 | Fuzzy matching with configurable Jaro-Winkler thresholds | Must | Implemented |
| FR-M-008 | Match result includes field-level comparison detail | Must | Implemented |
| FR-M-009 | Graceful degradation on search failures | Must | Implemented |
| FR-M-010 | Three-tier matching: exact company_id, composite matching, create new | Must | Implemented |
| FR-M-011 | Audit logging for match decisions | Should | Implemented |
| FR-M-012 | 12-factor configuration via pydantic-settings | Must | Implemented |
```

**Additional Amendments**:
1. Update FR-SEED-002 to reference three-tier matching (currently says "company_id or name")
2. Add user stories from executive summary to UC section
3. Add matching module to Appendix D Package Structure

### 3.2 TDD-08-business-domain.md Amendments

**Location**: After Section 6 (BusinessSeeder Factory)

**New Section**: `## 8. Composite Matching Architecture`

Content structure:
1. Three-tier matching pipeline diagram
2. MatchingEngine class design
3. Normalizer chain (phone, email, name, domain, address)
4. Comparator patterns (exact, fuzzy, term frequency)
5. Blocking strategy for O(n) candidate reduction
6. Log-odds scoring algorithm
7. Configuration integration (link to REF-seeder-matching-config)

**Additional Amendments**:
1. Update Section 6 BusinessSeeder to show integration with MatchingEngine
2. Add matching/* to Package Structure diagram
3. Update Related ADRs section to include ADR-0058

---

## 4. New Document Specifications

### 4.1 ADR-0058-fellegi-sunter-matching.md

**Path**: `/docs/decisions/ADR-0058-fellegi-sunter-matching.md`

**Content Brief**:

```markdown
# ADR-0058: Fellegi-Sunter Probabilistic Matching for Business Deduplication

## Metadata
- Status: Accepted
- Date: 2025-12-28
- Deciders: Architect
- Related: PRD-06-business-domain, TDD-08-business-domain

## Context
BusinessSeeder v1 used exact matching (company_id, then name) which:
- Missed legitimate duplicates with typos or variations
- Required manual intervention for edge cases
- Lacked confidence scoring for match decisions

## Decision
Implement Fellegi-Sunter probabilistic record linkage:
- Log-odds scoring for each field comparison
- Configurable weights per field type
- Term frequency adjustment for common values
- Blocking rules for O(n) candidate reduction

## Alternatives Considered
1. ML-based matching (too complex for current scale)
2. Rule-based exact matching (current v1, insufficient)
3. Edit distance only (no field-specific weighting)

## Consequences
Positive:
- Catches duplicates with name variations
- Configurable thresholds per deployment
- Explainable match decisions

Negative:
- Added complexity in matching module
- Requires threshold tuning for new domains
- False positives possible if thresholds too lenient
```

### 4.2 REF-seeder-matching-config.md

**Path**: `/docs/reference/REF-seeder-matching-config.md`

**Content Brief**:

```markdown
# Seeder Matching Configuration Reference

> Environment variable reference for BusinessSeeder v2 composite matching.

## Quick Reference

| Variable | Default | Description |
|----------|---------|-------------|
| SEEDER_MATCH_THRESHOLD | 0.80 | Probability threshold for match decision |
| SEEDER_MIN_FIELDS | 2 | Minimum non-null field comparisons |
| ... (all 16 variables) |

## Threshold Tuning Guide

### Strict Matching (Avoid False Positives)
```bash
export SEEDER_MATCH_THRESHOLD=0.90
export SEEDER_MIN_FIELDS=3
```

### Lenient Matching (Catch More Duplicates)
```bash
export SEEDER_MATCH_THRESHOLD=0.70
export SEEDER_MIN_FIELDS=2
```

## Field Weights

Weights use log-odds scale. Higher = more discriminative.

| Field | Match Weight | Non-Match Weight | Rationale |
|-------|--------------|------------------|-----------|
| Email | 8.0 | -4.0 | Highly unique identifier |
| Phone | 7.0 | -4.0 | Unique but formatting varies |
| Name | 6.0 | -3.0 | Common names reduce weight |
| Domain | 5.0 | -2.0 | Less unique than email |
| Address | 4.0 | -2.0 | Often incomplete |

## See Also
- [PRD-06 FR-M Requirements](../requirements/PRD-06-business-domain.md#fr-m-composite-matching-requirements)
- [TDD-08 Matching Architecture](../design/TDD-08-business-domain.md#8-composite-matching-architecture)
- [ADR-0058 Fellegi-Sunter Decision](../decisions/ADR-0058-fellegi-sunter-matching.md)
```

### 4.3 GUIDE-businessseeder-v2.md

**Path**: `/docs/guides/GUIDE-businessseeder-v2.md`

**Content Brief**:

```markdown
# BusinessSeeder v2 Integration Guide

> How to use composite matching for business deduplication.

## When to Use v2 Matching

Use composite matching when:
- Input data has name variations or typos
- Multiple corroborating fields available (email, phone, domain)
- False positives are acceptable with review workflow

Use exact matching (v1) when:
- company_id is reliable and always present
- Zero false positive tolerance
- Performance is critical (skip candidate search)

## Matching Pipeline

[Diagram: Tier 1 -> Tier 2 -> Tier 3]

## Configuration Examples

### E-commerce (Strict)
### Professional Services (Standard)
### Lead Aggregation (Lenient)

## Debugging Match Decisions

Enable debug logging to see field-level comparison:
```python
import logging
logging.getLogger("autom8_asana.models.business.matching").setLevel(logging.DEBUG)
```

## See Also
- Configuration: [REF-seeder-matching-config](../reference/REF-seeder-matching-config.md)
- Architecture: [TDD-08 Section 8](../design/TDD-08-business-domain.md#8-composite-matching-architecture)
```

---

## 5. Cross-Reference Strategy

### 5.1 Inline Links (Minimal)

Use sparingly for critical context only:

| From Document | Link To | Context |
|---------------|---------|---------|
| PRD-06 FR-M section | REF-seeder-matching-config | "See [configuration reference](...) for threshold tuning" |
| TDD-08 Section 8 | ADR-0058 | "Per [ADR-0058](...), we chose Fellegi-Sunter..." |

### 5.2 See Also Sections

Each new/amended document gets a "See Also" section:

```markdown
## See Also
- **Requirements**: [PRD-06 FR-M Section](../requirements/PRD-06-business-domain.md)
- **Architecture**: [TDD-08 Matching Section](../design/TDD-08-business-domain.md)
- **Decision**: [ADR-0058 Fellegi-Sunter](../decisions/ADR-0058-fellegi-sunter-matching.md)
- **Configuration**: [REF-seeder-matching-config](../reference/REF-seeder-matching-config.md)
- **Integration**: [GUIDE-businessseeder-v2](../guides/GUIDE-businessseeder-v2.md)
```

### 5.3 Code Reference Alignment

Update code comments to reference correct document locations:

| Current Code Reference | Correct Reference |
|------------------------|-------------------|
| `TDD FR-M-001` | `See PRD-06 FR-M-001` |
| `TDD ADR-SEEDER-003` | `See ADR-0058` |
| `TDD ADR-SEEDER-004` | `See TDD-08 Section 8.4 Blocking Strategy` |

---

## 6. Priority Order for Tech Writer

### Tier 1: Essential (Before Next Sprint)

| Priority | Deliverable | Effort | Dependencies |
|----------|-------------|--------|--------------|
| P1.1 | REF-seeder-matching-config.md | 2h | None (standalone) |
| P1.2 | TDD-08 Section 8 amendment | 4h | REF-seeder-matching-config |
| P1.3 | PRD-06 FR-M section amendment | 3h | TDD-08 Section 8 |

**Rationale**: Configuration reference first enables TDD to link to it; TDD before PRD because requirements reference design.

### Tier 2: Important (Within 2 Weeks)

| Priority | Deliverable | Effort | Dependencies |
|----------|-------------|--------|--------------|
| P2.1 | ADR-0058-fellegi-sunter-matching.md | 2h | TDD-08 Section 8 |
| P2.2 | GUIDE-businessseeder-v2.md | 3h | All Tier 1 |

### Tier 3: Nice-to-Have (Defer)

| Priority | Deliverable | Effort | Dependencies |
|----------|-------------|--------|--------------|
| P3.1 | RUNBOOK-matching-troubleshooting.md | 2h | Guide complete |
| P3.2 | Matching pipeline architecture diagram | 1h | TDD-08 Section 8 |

---

## 7. Migration Plan

### 7.1 File Operations

| Operation | Source | Destination | Action |
|-----------|--------|-------------|--------|
| CREATE | N/A | `/docs/reference/REF-seeder-matching-config.md` | Write new file |
| CREATE | N/A | `/docs/decisions/ADR-0058-fellegi-sunter-matching.md` | Write new file |
| CREATE | N/A | `/docs/guides/GUIDE-businessseeder-v2.md` | Write new file |
| AMEND | `/docs/requirements/PRD-06-business-domain.md` | (same) | Add FR-M section |
| AMEND | `/docs/design/TDD-08-business-domain.md` | (same) | Add Section 8 |

### 7.2 Index Updates

After all documents created/amended:

1. Update `/docs/reference/README.md` to add REF-seeder-matching-config
2. Update `/docs/decisions/INDEX.md` to add ADR-0058
3. Update `/docs/guides/README.md` to add GUIDE-businessseeder-v2
4. Update `/docs/INDEX.md` if it exists

### 7.3 Code Comment Updates

After documentation complete, update code references:

| File | Line | Current | Target |
|------|------|---------|--------|
| `matching/engine.py` | ~15 | `Per TDD FR-M-001` | `Per PRD-06 FR-M-001` |
| `matching/config.py` | ~4 | `Per TDD FR-M-012` | `Per PRD-06 FR-M-012` |
| `matching/engine.py` | ~45 | `Per TDD ADR-SEEDER-003` | `Per ADR-0058` |
| `matching/blocking.py` | ~8 | `Per TDD ADR-SEEDER-004` | `Per TDD-08 Section 8.4` |

---

## 8. Naming Conventions

Following established patterns from INFORMATION-ARCHITECTURE-SPEC-2025-12-24.md:

| Document Type | Pattern | Example |
|---------------|---------|---------|
| Reference | `REF-topic-name.md` | `REF-seeder-matching-config.md` |
| ADR | `ADR-NNNN-decision-name.md` | `ADR-0058-fellegi-sunter-matching.md` |
| Guide | `GUIDE-feature-name.md` | `GUIDE-businessseeder-v2.md` |
| Runbook | `RUNBOOK-system-issue.md` | `RUNBOOK-matching-troubleshooting.md` |

---

## 9. Success Metrics

Post-implementation validation:

- [ ] PRD-06 includes complete FR-M-001 through FR-M-012 requirements
- [ ] TDD-08 Section 8 documents matching architecture
- [ ] ADR-0058 explains Fellegi-Sunter decision with alternatives
- [ ] REF-seeder-matching-config documents all 16 SEEDER_* variables
- [ ] GUIDE-businessseeder-v2 provides integration examples
- [ ] All cross-references valid (no broken links)
- [ ] Code references updated to correct document paths
- [ ] Engineer can find matching configuration in <30 seconds

---

## 10. Handoff Checklist

This specification is ready for Tech Writer when:

- [x] Amend vs create decision documented with rationale
- [x] All target documents identified with paths
- [x] Amendment scope defined for PRD-06 and TDD-08
- [x] Content briefs provided for new documents
- [x] Cross-reference strategy specified
- [x] Priority order established with effort estimates
- [x] Migration plan includes all file operations
- [x] Naming conventions confirmed
- [x] Success metrics defined

---

## Attestation Table

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| This Spec | `/Users/tomtenuta/Code/autom8_asana/.claude/sessions/session-20251228-002313-267bc29d/artifacts/INFO-ARCH-businessseeder-v2.md` | Yes |
| Audit Report | `/Users/tomtenuta/Code/autom8_asana/.claude/sessions/session-20251228-002313-267bc29d/artifacts/AUDIT-businessseeder-v2-documentation.md` | Yes |

---

*Generated by information-architect | BusinessSeeder v2 Documentation Initiative*
