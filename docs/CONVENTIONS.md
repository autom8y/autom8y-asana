# Documentation Conventions

> Canonical standards for documentation in the autom8_asana project.

## Documentation Status Lifecycle

All PRDs, TDDs, and initiative documents use a standardized status lifecycle. The **frontmatter `status` field is the canonical source of truth**. INDEX.md must be derived from or validated against frontmatter.

### Canonical Status Values

| Status | Meaning | Applies To |
|--------|---------|------------|
| **Draft** | Requirements gathering or design in progress. Not approved for implementation. | PRD, TDD, PROMPT-0 |
| **Active** | Approved for implementation. Work may be in progress. | PRD, TDD, PROMPT-0 |
| **Implemented** | Code complete, feature shipped. All acceptance criteria met. | PRD, TDD |
| **Validated** | Passed QA validation. Use for initiatives that completed validation. | PROMPT-0, VP |
| **Superseded** | Replaced by newer design/requirement. Must link to replacement. | PRD, TDD, ADR |
| **Rejected** | Decided not to implement. Must link to ADR documenting decision. | PRD, TDD |
| **Archived** | Historical record. Implementation complete and stable. Moved to `.archive/`. | All types |

### Status Transitions

```
┌─────────┐
│  Draft  │
└────┬────┘
     │ Approval
     ▼
┌─────────┐
│ Active  │──────────────────────────┐
└────┬────┘                          │
     │ Code complete                 │ Decision to not implement
     ▼                               ▼
┌────────────┐                 ┌──────────┐
│Implemented │                 │ Rejected │
└─────┬──────┘                 └──────────┘
      │ Stabilization               │
      ▼                             │ (link to ADR)
┌──────────┐                        │
│ Archived │◄───────────────────────┘
└──────────┘

At any point:
  Any Status ──► Superseded (when replaced by newer design)
```

### Frontmatter Format

**Two frontmatter styles are accepted:**

#### Option 1: YAML Frontmatter (Recommended for new documents)

All documentation files should include YAML frontmatter at the top of the file.

**Minimal required fields:**

```yaml
---
status: "Active"
---
```

**Standard frontmatter for PRDs:**

```yaml
---
id: "PRD-0013"
title: "Hierarchy Hydration"
status: "Implemented"
created: "2025-01-15"
updated: "2025-01-20"
author: "Requirements Analyst"
paired_tdd: "TDD-0017"
related_adr: ["ADR-0068", "ADR-0069"]
---
```

**Standard frontmatter for TDDs:**

```yaml
---
id: "TDD-0017"
title: "Hierarchy Hydration Design"
status: "Implemented"
created: "2025-01-15"
updated: "2025-01-20"
author: "Architect"
paired_prd: "PRD-0013"
related_adr: ["ADR-0068", "ADR-0069", "ADR-0071"]
---
```

**Standard frontmatter for ADRs:**

```yaml
---
status: "Accepted"
author: "Architect"
date: "2025-01-15"
deciders: ["Architect", "Principal Engineer"]
related: ["PRD-0013", "TDD-0017", "ADR-0067"]
---
```

**Standard frontmatter for PROMPT-0 initiatives:**

```yaml
---
id: "PROMPT-0-CACHE-INTEGRATION"
title: "Cache Integration Initiative"
status: "Validated"
created: "2025-12-22"
validated: "2025-12-24"
author: "Orchestrator"
related_prd: ["PRD-CACHE-INTEGRATION", "PRD-CACHE-PERF-FETCH-PATH"]
validation_report: "VP-CACHE-INTEGRATION"
---
```

#### Option 2: Metadata Section (Legacy, still supported)

Some documents use a `## Metadata` section instead of YAML frontmatter:

```markdown
## Metadata
- **PRD ID**: PRD-0002
- **Status**: Superseded
- **Author**: Requirements Analyst
- **Created**: 2025-12-09
- **Last Updated**: 2025-12-24
- **Related PRDs**: [PRD-0001](PRD-0001-sdk-extraction.md)
```

**Migration guidance**: When editing documents with metadata sections, optionally convert to YAML frontmatter for consistency. Not required for minor edits.

#### Frontmatter Field Reference

**Common fields:**

| Field | Required | Values | Used In |
|-------|----------|--------|---------|
| `status` | Yes | See status lifecycle above | All docs |
| `id` | No | Document ID (e.g., "PRD-0013") | PRD, TDD, ADR |
| `title` | No | Human-readable title | All docs |
| `created` | No | ISO date (YYYY-MM-DD) | All docs |
| `updated` | No | ISO date (YYYY-MM-DD) | All docs |
| `author` | No | Agent or person name | All docs |

**Relationship fields:**

| Field | Used In | Purpose | Example |
|-------|---------|---------|---------|
| `paired_prd` | TDD | Link to requirements | `"PRD-0013"` |
| `paired_tdd` | PRD | Link to design | `"TDD-0017"` |
| `related_adr` | PRD, TDD | Decision records | `["ADR-0068", "ADR-0069"]` |
| `related` | ADR | Related docs | `["PRD-0013", "TDD-0017"]` |
| `supersedes` | All | Document this replaces | `"PRD-0001"` |
| `superseded_by` | All | Document that replaces this | `"PRD-0025"` |

**Lifecycle fields:**

| Field | Used In | Purpose | Example |
|-------|---------|---------|---------|
| `superseded_date` | All | When superseded | `"2025-12-24"` |
| `validated` | PROMPT-0 | Validation completion date | `"2025-12-24"` |
| `validation_report` | PROMPT-0 | Link to VP doc | `"VP-CACHE-INTEGRATION"` |
| `deciders` | ADR | Who approved | `["Architect", "Principal Engineer"]` |

### Supersession Notices

When marking a document as **Superseded**:

1. Update frontmatter: `status: "Superseded"`
2. Add `superseded_by` field with replacement document ID
3. Add prominent notice at top of document (after frontmatter):

```markdown
> **SUPERSESSION NOTICE**: This document has been superseded by [PRD-0002](PRD-0002.md).
> The requirements below are no longer active. Refer to the replacement document for current design.
```

### Rejection Notices

When marking a document as **Rejected**:

1. Update frontmatter: `status: "Rejected"`
2. Add `related_adr` field with decision record
3. Add prominent notice:

```markdown
> **REJECTION NOTICE**: This feature was rejected per [ADR-0101](../decisions/ADR-0101.md).
> See the ADR for rationale. This document is retained for historical reference.
```

## INDEX.md Maintenance

`docs/INDEX.md` provides navigation and status overview. It must stay synchronized with document frontmatter.

### Accuracy Requirements

1. **Status column** must match document frontmatter `status` field
2. **Paths** must be correct (use relative paths from docs/)
3. **Superseded/Rejected** items should link to replacement or ADR

### Validation

Periodically validate INDEX.md accuracy:

```bash
# Find status mismatches (pseudocode)
for each PRD in docs/requirements/PRD-*.md:
    frontmatter_status = extract_status(PRD)
    index_status = find_in_index(PRD)
    if frontmatter_status != index_status:
        report_mismatch(PRD)
```

## File Naming Conventions

### When to Use Numbered vs Named Format

**Use numbered format (XXXX)** when:
- Creating standalone feature documentation with no clear initiative scope
- Documenting core SDK features that are permanent additions
- Creating documents that are independent of any broader initiative
- Allocating a sequential ID for long-term reference and traceability

**Use named format (DESCRIPTIVE-NAME)** when:
- Multiple documents belong to the same initiative or feature area
- Documents are part of a cohesive effort (e.g., cache optimization)
- Descriptive naming improves discoverability (e.g., all cache docs start with `CACHE-`)
- Sub-initiatives under a meta-initiative (e.g., `CACHE-PERF-DETECTION` under cache performance)

**Consistency within initiatives**: All documents for the same initiative should use the same format. If PRD uses named format, its paired TDD should also use named format.

### PRDs (Product Requirements Documents)

- **Location**: `docs/requirements/`
- **Numbered format**: `PRD-XXXX-feature-name.md`
  - Example: `PRD-0002-intelligent-caching.md`, `PRD-0013-hierarchy-hydration.md`
  - Use 4-digit zero-padded numbers (0001, 0002, etc.)
  - Allocate next sequential number from INDEX.md
- **Named format**: `PRD-DESCRIPTIVE-NAME.md`
  - Example: `PRD-CACHE-INTEGRATION.md`, `PRD-DETECTION.md`
  - Use ALL-CAPS with hyphens for word separation
  - Group related docs with common prefix (e.g., `PRD-CACHE-*` for cache initiative)

### TDDs (Technical Design Documents)

- **Location**: `docs/design/`
- **Numbered format**: `TDD-XXXX-feature-name.md`
  - Example: `TDD-0008-intelligent-caching.md`, `TDD-0017-hierarchy-hydration.md`
- **Named format**: `TDD-DESCRIPTIVE-NAME.md`
  - Example: `TDD-CACHE-INTEGRATION.md`, `TDD-DETECTION.md`
- **Pairing rule**: TDD naming format must match its paired PRD
  - If PRD is `PRD-0013-hierarchy-hydration.md`, TDD is `TDD-0017-hierarchy-hydration.md`
  - If PRD is `PRD-CACHE-INTEGRATION.md`, TDD is `TDD-CACHE-INTEGRATION.md`

### ADRs (Architecture Decision Records)

- **Location**: `docs/decisions/`
- **Naming**: `ADR-XXXX-decision-title.md` (always numbered)
- **Format**: 4-digit zero-padded sequential numbers (ADR-0001, ADR-0002, etc.)
- **Numbering**: Sequential, never reuse numbers, never skip numbers
- **Allocation**: Check INDEX.md for current highest number, use next available
- **No named format**: ADRs always use numbered format for chronological ordering

### Initiatives (PROMPT-0)

- **Location**: `docs/initiatives/`
- **Naming**: `PROMPT-0-INITIATIVE-NAME.md` or `PROMPT-MINUS-1-INITIATIVE-NAME.md`
- **Archival**: Move to `.archive/initiatives/YYYY-QN/` after validation

### Validation Reports

- **Location**: `docs/testing/`
- **Naming**: `VP-FEATURE-NAME.md` (Validation Plan/Report)
- **Status**: `APPROVED`, `APPROVED-WITH-RESERVATIONS`, `REJECTED`, `INVALIDATED`

## Archival Policy

### When to Archive

Archive documents when:
1. **Initiative completed**: PROMPT-0 validated PASS/APPROVED
2. **Feature stable**: Implementation complete, no active changes for 90+ days
3. **Superseded**: Replaced by newer version (archive after replacement validated)
4. **Invalidated**: Validation report for feature that was never implemented

### Archive Structure

```
docs/.archive/
├── initiatives/
│   └── 2025-Q4/
│       └── PROMPT-0-COMPLETED-FEATURE.md
├── requirements/
│   └── PRD-0001-deprecated-feature.md
├── design/
│   └── TDD-0001-deprecated-design.md
└── validation/
    └── VP-INVALIDATED-FEATURE.md
```

### Archive Process

1. Move file preserving git history: `git mv docs/requirements/PRD-old.md docs/.archive/requirements/`
2. Update INDEX.md: Move entry to "Archived" section
3. Update any internal links to point to archive location
4. Add archive note to document header

---

## Quick Reference

### Status Values (copy-paste ready)

```yaml
status: "Draft"
status: "Active"
status: "Implemented"
status: "Validated"
status: "Superseded"
status: "Rejected"
status: "Archived"
```

### Supersession Template

```markdown
> **SUPERSESSION NOTICE**: This document has been superseded by [REPLACEMENT](path).
> Reason: [brief explanation]. See replacement for current design.
```

### Rejection Template

```markdown
> **REJECTION NOTICE**: This feature was rejected per [ADR-XXXX](path).
> Reason: [brief explanation]. Document retained for historical reference.
```
