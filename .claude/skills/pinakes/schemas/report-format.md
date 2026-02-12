---
name: theoria-report-format
description: "Report format specification for theoria audit outputs. Use when: formatting audit reports, understanding report structure, producing synkrisis synthesis. Triggers: report format, audit report, synkrisis report, state of the X format."
---

# Theoria Report Format

Standardized output formats for domain assessments and synkrisis synthesis reports.

## Report Types

| Type | Producer | Scope | Output Location |
|------|----------|-------|-----------------|
| **Domain Assessment** | theoros agent | Single domain | Returned to /theoria |
| **Synkrisis Report** | /theoria dromena | Cross-domain synthesis | `.wip/STATE-OF-{TARGET}-{YYYY-MM-DD}.md` |

## Domain Assessment Format

Produced by theoros agent for a single domain evaluation. This format aligns with the theoros output schema.

### Template

```markdown
## Domain Assessment: {domain_name}

**Overall Grade: {letter}** ({percentage}% criteria met)

**Audit Scope:** {scope_description}
**Artifacts Evaluated:** {count} files, {other_counts}
**Evaluation Date:** {YYYY-MM-DD}

### Criteria Results

| Criterion | Grade | Evidence | Notes |
|-----------|-------|----------|-------|
| {criterion_name} | {A-F} ({pct}%) | {file_count} files, {specifics} | {justification} |
| {criterion_name} | {A-F} ({pct}%) | {specifics} | {justification} |

### Findings

#### Strengths

- **{strength_title}**: {description_with_evidence}
- **{strength_title}**: {description_with_evidence}

#### Weaknesses

- **{weakness_title}**: {description_with_evidence}
- **{weakness_title}**: {description_with_evidence}

#### Recommendations

1. **{recommendation_title}**: {specific_action_with_scope}
2. **{recommendation_title}**: {specific_action_with_scope}

### Appendix: Evidence Details

{optional_section_with_file_paths_line_numbers_excerpts}
```

### Domain Assessment Rules

**Required Elements:**

- Overall grade with percentage calculation
- Audit scope (what was evaluated)
- Artifact counts (files, items, etc.)
- Evaluation date (YYYY-MM-DD format)
- Criteria results table with all criteria
- Findings organized by strengths/weaknesses/recommendations

**Grade Display:**

- Always show letter and percentage: "B (85.0%)"
- Criterion grades include percentage and evidence count: "B (83.3%, 5 of 6 comply)"
- Never use subjective qualifiers: no "pretty good", "mostly okay"

**Evidence Requirements:**

- Use specific counts: "7 of 12 files" not "most files"
- Reference file paths when relevant: `rites/shared/agents/theoros.md`
- Include line numbers for specific issues: `theoros.md:42`
- Excerpts in appendix when needed for clarity

**Recommendations Must Be:**

- Specific and actionable (not "improve X")
- Scoped to artifacts that can be changed
- Prioritized (most important first)

**Example Criterion Row:**

```markdown
| Frontmatter Completeness | B (83.3%) | 5 of 6 agents | orchestrator.md missing description field |
```

## Synkrisis Report Format

The aggregate synthesis report produced by /theoria combining multiple domain assessments.

### Template

```markdown
# State of the {target}: {date}

**Overall Grade: {letter}** (across {N} domains)

## Executive Summary

{2-3_sentence_overview_of_overall_state}

{highlight_most_critical_finding_or_pattern}

## Domain Grades

| Domain | Grade | Key Finding |
|--------|-------|-------------|
| {domain_name} | {A-F} ({pct}%) | {one_sentence_summary} |
| {domain_name} | {A-F} ({pct}%) | {one_sentence_summary} |

## Cross-Domain Findings

### Systemic Strengths

- **{strength_theme}**: {description_with_examples_across_domains}
- **{strength_theme}**: {description_with_examples_across_domains}

### Systemic Weaknesses

- **{weakness_theme}**: {description_with_impact_across_domains}
- **{weakness_theme}**: {description_with_impact_across_domains}

### Priority Recommendations

1. **{recommendation}**: {specific_action_with_cross_domain_scope}
2. **{recommendation}**: {specific_action_with_cross_domain_scope}
3. **{recommendation}**: {specific_action_with_cross_domain_scope}

## Domain Details

{embedded_domain_assessment_1}

---

{embedded_domain_assessment_2}

---

{embedded_domain_assessment_3}

## Methodology

- **Domains evaluated**: {comma_separated_list}
- **Grading scale**: A-F (see `pinakes/schemas/grading.lego.md`)
- **Evaluation date**: {YYYY-MM-DD}
- **Aggregation method**: {equal_weighting_or_custom_description}
```

### Synkrisis Report Rules

**Overall Grade Calculation:**

- Default: equal weighting across domains
- Convert each domain letter to midpoint percentage (A=95, B=85, C=75, D=65, F=40)
- Compute average, map back to letter grade
- See `grading.lego.md` for detailed aggregation rules

**Executive Summary:**

- 2-3 sentences maximum
- Focus on overall state and most critical finding
- Avoid jargon, use plain language

**Cross-Domain Findings:**

- Identify patterns that appear in multiple domains
- Systemic strengths: capabilities present across domains
- Systemic weaknesses: gaps appearing in multiple areas
- Priority recommendations: actions with cross-domain impact

**Domain Details Section:**

- Embed full domain assessments with separators (`---`)
- Preserve all criterion detail from domain reports
- Maintain consistent formatting

**Methodology Section:**

- List all domains evaluated
- Reference grading schema explicitly
- Document any custom weighting or evaluation rules

### Output Location

Synkrisis reports are written to:

```
.wip/STATE-OF-{TARGET}-{YYYY-MM-DD}.md
```

**Examples:**

- `.wip/STATE-OF-ECOSYSTEM-2026-02-10.md`
- `.wip/STATE-OF-AGENTS-2026-02-10.md`
- `.wip/STATE-OF-DOCUMENTATION-2026-02-10.md`

## Format Rules

### Universal Standards

**Grade Display:**

- Always include percentage calculation
- Format: `Grade: {letter} ({percentage}%)`
- Criterion level: `{letter} ({percentage}%, {evidence_count})`

**Evidence Standards:**

- Specific file paths: `rites/shared/agents/theoros.md`
- Line numbers when relevant: `theoros.md:42-48`
- Counts over qualifiers: "7 of 12" not "most"
- No subjective language: avoid "good", "bad", "pretty"

**Recommendation Standards:**

- Actionable: start with verb (Add, Update, Remove, Rename)
- Specific: name files, sections, artifacts
- Scoped: define clear boundaries
- Example: "Add description field to orchestrator.md frontmatter" not "Improve agent documentation"

**Table Formatting:**

- Use markdown tables consistently
- Align columns for readability
- Include headers always
- Criterion table: Criterion | Grade | Evidence | Notes
- Domain table: Domain | Grade | Key Finding

**Date Format:**

- Always YYYY-MM-DD (ISO 8601)
- Use evaluation date, not report generation date (if different)

### Prohibited Patterns

Do NOT use:

- Subjective qualifiers: "pretty good", "mostly okay", "fairly complete"
- Vague quantities: "most", "some", "many" (use counts)
- Generic recommendations: "improve documentation", "fix issues"
- Grade modifiers: B+ or A- (use simple letters only)
- Percentage ranges: "80-85%" (use single value: "82.5%")

## Integration with Grading System

This report format implements the grading system defined in `grading.lego.md`:

- **Grade display** follows canonical scale (A-F, no modifiers)
- **Percentage calculations** use midpoint conversion for aggregation
- **Domain aggregation** uses weighted average of criteria
- **Synkrisis aggregation** uses average of domain percentages

All grades in reports MUST be calculable using the rules in `grading.lego.md`.

## Related

- `grading.lego.md` — Canonical grading scale and aggregation rules
- `../INDEX.lego.md` — Pinakes overview
- `../../../agents/theoros.md` — Agent that produces domain assessments
- `../domains/*.lego.md` — Domain criteria definitions
