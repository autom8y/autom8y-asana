# Merge Strategies

> **Purpose**: Decision framework for when to merge, split, or preserve separate documents during consolidation.

## Design Principles

1. **Information Preservation**: Never lose information during consolidation
2. **Authority Clarity**: Always identify which source is canonical
3. **Conflict Visibility**: Surface disagreements explicitly
4. **Token Efficiency**: Reduce redundancy without sacrificing completeness

---

## Merge Decision Framework

### Step 1: Measure Overlap

Calculate content overlap between candidate documents.

**Overlap Calculation:**

```python
def calculate_overlap(doc_a, doc_b):
    """
    Calculate semantic overlap between two documents.
    Returns: float between 0.0 (no overlap) and 1.0 (identical content)
    """
    concepts_a = extract_concepts(doc_a)  # Set of key concepts
    concepts_b = extract_concepts(doc_b)

    intersection = concepts_a & concepts_b
    union = concepts_a | concepts_b

    return len(intersection) / len(union) if union else 0.0
```

**Concept Extraction Signals:**

- Section headings (H1-H3)
- Bold/emphasized terms
- Code block identifiers (function names, config keys)
- Defined terms (first occurrence of technical vocabulary)

### Step 2: Apply Threshold Rules

| Overlap Score | Action | Rationale |
|---------------|--------|-----------|
| >= 0.7 | **Merge required** | Highly redundant; consolidate to single source |
| 0.5 - 0.7 | **Merge recommended** | Significant overlap; review for consolidation |
| 0.3 - 0.5 | **Cross-reference** | Related but distinct; link rather than merge |
| < 0.3 | **Keep separate** | Different concerns; maintain independence |

### Step 3: Determine Merge Direction

When merge is indicated, determine which document absorbs the other.

**Authority Hierarchy:**

```yaml
authority_ranking:
  1_highest:
    - "Implementation source (code comments, TDD)"
    - "Primary skill file (SKILL.md)"
  2_high:
    - "Design documents (TDD-*.md)"
    - "Architecture decisions (ADR-*.md)"
  3_medium:
    - "How-to guides"
    - "Reference documentation"
  4_low:
    - "README files"
    - "Changelogs"
  5_lowest:
    - "Meeting notes"
    - "Draft documents"
```

**Merge Direction Rules:**

1. Higher authority absorbs lower authority content
2. More recent document wins for contradicting facts (with exceptions)
3. More specific document absorbs generic content
4. Larger document typically absorbs smaller (fewer moves)

---

## Conflict Resolution

### Conflict Types

| Type | Definition | Resolution Strategy |
|------|------------|---------------------|
| **Contradiction** | Sources state opposite facts | Authority + recency determines winner |
| **Ambiguity** | Sources are unclear or incomplete | Synthesize from multiple, flag gaps |
| **Overlap** | Same information stated differently | Choose clearest expression |
| **Gap** | Information exists in one source only | Preserve unique information |

### Resolution Priority Matrix

```
                    Higher Authority
                    │
    ┌───────────────┼───────────────┐
    │ Use Higher    │ Use Higher    │
    │ Authority     │ Authority +   │
    │               │ Note Recency  │
Older ──────────────┼────────────── Newer
    │ Use Recent +  │ Use Recent    │
    │ Verify        │               │
    │               │               │
    └───────────────┼───────────────┘
                    │
                    Lower Authority
```

**Resolution Decision Tree:**

```
Conflict detected between Source A and Source B
  |
  v
[1] Is one source clearly higher authority?
  |-- Yes --> Use higher authority content
  |           Record: "Resolved per authority hierarchy"
  |-- No --> Continue to [2]
  |
  v
[2] Is one source significantly more recent? (>30 days)
  |-- Yes --> Use more recent, verify against implementation
  |           Record: "Resolved per recency; verify implementation"
  |-- No --> Continue to [3]
  |
  v
[3] Can both positions be synthesized?
  |-- Yes --> Synthesize nuanced statement covering both
  |           Record: "Synthesized from multiple sources"
  |-- No --> Continue to [4]
  |
  v
[4] Is this blocking consolidation?
  |-- Yes --> Escalate to human for resolution
  |           Mark conflict as "blocking"
  |-- No --> Document both positions, note disagreement
  |           Mark conflict as "deferred"
```

### Conflict Documentation Format

```yaml
conflicts:
  - id: "conflict-001"
    type: contradiction
    severity: significant  # blocking | significant | minor
    description: "Default array merge strategy differs between sources"

    sources:
      - path: ".claude/skills/doc-ecosystem/SKILL.md"
        position: "Arrays append by default"
        evidence: "Line 178: 'Arrays append by default...'"
        authority: primary
        last_modified: "2024-12-01"

      - path: "docs/design/TDD-0042-settings.md"
        position: "Arrays replace by default"
        evidence: "Line 85: 'replace (default)'"
        authority: secondary
        last_modified: "2024-12-15"

    resolution:
      status: resolved  # unresolved | resolved | deferred
      decision: "Default is 'replace' per TDD"
      rationale: "TDD reflects implementation; SKILL.md was aspirational"
      authority: "integration-engineer-2024-12-25"
      verification: "Confirmed via cem sync test"
```

---

## Information Preservation Guarantees

### What MUST Be Preserved

| Content Type | Preservation Requirement |
|--------------|-------------------------|
| **Facts** | All accurate facts from all sources |
| **Examples** | Best examples from each source (deduplicate similar) |
| **Warnings/Caveats** | All warnings, even if redundant |
| **Edge cases** | All edge case documentation |
| **Version-specific notes** | If still relevant to current version |

### What MAY Be Consolidated

| Content Type | Consolidation Approach |
|--------------|------------------------|
| **Redundant explanations** | Keep clearest version |
| **Overlapping examples** | Keep most comprehensive |
| **Historical notes** | Move to changelog/history section |
| **Deprecated information** | Remove if clearly superseded |

### Preservation Tracking

```yaml
preservation_audit:
  source: "docs/design/TDD-0042-settings.md"
  sections:
    - heading: "Merge Algorithm"
      status: preserved
      destination: "consolidated/settings-merge.md#algorithm"

    - heading: "Historical Context"
      status: moved
      destination: "consolidated/settings-merge.md#appendix-history"
      rationale: "Useful context but not primary content"

    - heading: "Deprecated V1 Behavior"
      status: removed
      rationale: "V1 no longer supported; documented in CHANGELOG"
      approved_by: "ecosystem-analyst"
```

---

## Merge Execution Strategies

### Strategy 1: Absorb and Extend

Use when one document is clearly primary.

```
Primary Document (keeper)
├── Original content preserved
├── + Unique content from secondary sources
├── + Best examples from all sources
└── + Cross-references to related topics

Secondary Documents (absorbed)
└── Archived or deleted after verification
```

### Strategy 2: Synthesize New

Use when no clear primary exists or significant restructuring needed.

```
Source A + Source B + Source C
           ↓
    New Consolidated Document
    ├── Reorganized structure
    ├── Synthesized content
    ├── Conflict resolutions documented
    └── Source attribution in metadata

Original Sources
└── Archived with reference to consolidated doc
```

### Strategy 3: Extract Common + Keep Specific

Use when sources have shared core but unique specifics.

```
Source A (Auth for API)  ─┐
                          ├── Common: auth-concepts.md
Source B (Auth for CLI)  ─┤
                          └── Specific: auth-api.md, auth-cli.md

Result:
├── auth-concepts.md (shared)
├── auth-api.md (extends concepts for API)
└── auth-cli.md (extends concepts for CLI)
```

---

## Quality Gates

### Pre-Merge Checklist

- [ ] Overlap score calculated and documented
- [ ] Authority hierarchy applied
- [ ] All conflicts identified and categorized
- [ ] Blocking conflicts resolved or escalated
- [ ] Merge direction determined
- [ ] Information preservation audit complete

### Post-Merge Verification

- [ ] No information lost (audit trail complete)
- [ ] Conflicts resolved or documented
- [ ] Cross-references updated
- [ ] Original sources archived appropriately
- [ ] Token count reduced (consolidation goal met)
- [ ] Stakeholder review for significant merges

---

## Anti-Patterns

### Do NOT

| Anti-Pattern | Why It's Wrong | Instead |
|--------------|----------------|---------|
| Silent resolution | Loses audit trail | Document every conflict resolution |
| Majority wins | May discard authoritative minority | Use authority hierarchy |
| Newest wins always | New docs may have errors | Verify against implementation |
| Merge everything | Over-consolidation harms navigation | Maintain logical separation |
| Keep all duplicates | Defeats consolidation purpose | Choose best, cite others |

### Warning Signs

- Merged document is longer than sum of sources (added too much)
- No conflicts documented (probably missed some)
- Original sources deleted before verification
- Single person resolved all conflicts (need review)
