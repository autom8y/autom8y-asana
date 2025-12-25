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

All documentation files must include YAML frontmatter with at minimum:

```yaml
---
id: "PRD-0001"
title: "Feature Name"
status: "Active"
created: "2025-01-15"
updated: "2025-01-20"
---
```

**Additional recommended fields:**

```yaml
---
id: "PRD-0001"
title: "Feature Name"
status: "Implemented"
created: "2025-01-15"
updated: "2025-01-20"
author: "name"
supersedes: "PRD-0000"      # If this replaces an older doc
superseded_by: "PRD-0002"   # If replaced by newer doc
related_adr: "ADR-0101"     # Decision records
paired_tdd: "TDD-0001"      # For PRDs: linked design
paired_prd: "PRD-0001"      # For TDDs: linked requirements
---
```

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

### PRDs (Product Requirements Documents)

- **Location**: `docs/requirements/`
- **Naming**: `PRD-XXXX-feature-name.md` (numbered) or `PRD-FEATURE-NAME.md` (named)
- **Examples**: `PRD-0002-intelligent-caching.md`, `PRD-CACHE-INTEGRATION.md`

### TDDs (Technical Design Documents)

- **Location**: `docs/design/`
- **Naming**: `TDD-XXXX-feature-name.md` (numbered) or `TDD-FEATURE-NAME.md` (named)
- **Pairing**: Each TDD should reference its paired PRD

### ADRs (Architecture Decision Records)

- **Location**: `docs/decisions/`
- **Naming**: `ADR-XXXX-decision-title.md`
- **Numbering**: Sequential, never reuse numbers

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
