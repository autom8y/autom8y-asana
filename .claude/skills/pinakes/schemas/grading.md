---
name: theoria-grading
description: "Canonical grading scale and aggregation rules for theoria audits. Use when: understanding grade calculations, aggregating domain grades into overall assessment. Triggers: grading scale, grade aggregation, theoria grades, letter grades."
---

# Theoria Grading System

Canonical grading standards for all domain audits. This is the single source of truth for grade calculation and aggregation.

## Canonical Grading Scale

| Grade | Label | Threshold | Meaning |
|-------|-------|-----------|---------|
| **A** | Excellent | 90-100% | Exceeds requirements |
| **B** | Good | 80-89% | Meets requirements with minor gaps |
| **C** | Adequate | 70-79% | Meets minimum requirements |
| **D** | Below Standard | 60-69% | Below minimum, significant gaps |
| **F** | Failing | Below 60% | Does not meet minimum requirements |

**No +/- modifiers.** Simple letter grades only.

**Threshold Rule:** Use >= for lower bound. 80.0% is B. 79.9% is C.

## Criterion-Level Grading

Individual criteria within a domain are graded by compliance ratio:

1. **Count items**: Total items in scope for this criterion
2. **Count compliant**: Items that pass the criterion
3. **Calculate percentage**: `(compliant / total) × 100`
4. **Map to letter grade** using canonical scale above
5. **Show calculation**: Always display work

**Example:**
```
Criterion: Agent files have valid frontmatter
Scope: 6 agent files
Compliant: 5 files (1 missing description field)
Percentage: 5/6 = 83.3%
Grade: B (83.3% meets 80-89% threshold)
Display: "B (83.3%, 5 of 6 comply)"
```

### Edge Cases

| Scenario | Handling |
|----------|----------|
| 0 items in scope | Grade as **N/A**, add note explaining scope |
| Criterion not evaluable | Exclude from domain weighted average, document why |
| All items fail | Grade is **F (0%)**, no softening |
| Referenced artifact missing | Grade criterion **F**, note in evidence |

## Domain-Level Aggregation

Domain overall grade = weighted average of criterion grades.

**Process:**

1. **Verify weights sum to 100%** across all criteria in domain
2. **Convert each criterion letter to midpoint percentage:**
   - A = 95% (midpoint of 90-100)
   - B = 85% (midpoint of 80-89)
   - C = 75% (midpoint of 70-79)
   - D = 65% (midpoint of 60-69)
   - F = 40% (below 60, use 40 as floor)
   - N/A = exclude from calculation, redistribute weight
3. **Compute weighted sum:** `Σ(criterion_percentage × criterion_weight)`
4. **Map result to letter grade** using canonical scale

**Worked Example:**

Domain with 3 criteria:

| Criterion | Grade | Midpoint % | Weight | Contribution |
|-----------|-------|------------|--------|--------------|
| Naming Consistency | B | 85% | 40% | 34.0 |
| Frontmatter Completeness | A | 95% | 30% | 28.5 |
| Documentation Quality | C | 75% | 30% | 22.5 |
| **Weighted Sum** | | | | **85.0%** |

Result: 85.0% → **B** (in 80-89% range)

Display: `"Overall Grade: B (85.0% criteria met)"`

### Handling N/A Criteria

If a criterion is graded N/A (not applicable):

1. Exclude it from weighted average
2. Redistribute its weight proportionally across remaining criteria
3. Document the exclusion in the report

**Example:** If 30% weight criterion is N/A, remaining criteria with 40% and 30% weights become 57.1% and 42.9%.

## Cross-Domain Aggregation (Synkrisis)

The synkrisis synthesis computes an overall "State of the X" grade across multiple domains.

**Default: Equal Weighting** across domains unless /theoria specifies otherwise.

**Process:**

1. **Convert each domain grade to midpoint percentage** (same as criterion aggregation)
2. **Compute simple average:** `Σ(domain_percentage) / N_domains`
3. **Map to letter grade** using canonical scale
4. **Show both per-domain and aggregate** in synkrisis report

**Worked Example:**

State of the Rite with 3 domains:

| Domain | Grade | Midpoint % |
|--------|-------|------------|
| Agents | B | 85% |
| Mena | A | 95% |
| Orchestration | C | 75% |
| **Average** | | **85.0%** |

Result: 85.0% → **B**

Display in synkrisis:
```markdown
**Overall Grade: B** (across 3 domains)

## Domain Grades
| Domain | Grade | Key Finding |
|--------|-------|-------------|
| Agents | B | 5 of 6 agents have complete frontmatter |
| Mena | A | All primitives correctly categorized |
| Orchestration | C | 3 of 5 routing rules lack examples |
```

## Grading Philosophy

### Principles

- **Grade on REALITY, not potential**: What exists now, not what could exist
- **No grade inflation**: F means failing, use it when appropriate
- **Partial credit is transparent**: Show "7 of 12 pass" even if grade is F
- **Grades are diagnostic, not punitive**: Purpose is to identify gaps, not blame
- **Precision matters**: Always show calculations and percentages
- **Ties use threshold**: 80.0% is B. 79.9% is C. No rounding up.

### When Multiple Interpretations Exist

If a criterion could be interpreted multiple ways:

1. Document your interpretation in the report
2. Grade consistently using that interpretation
3. Note alternative interpretations if they would materially change the grade

### Grade Semantics

- **A (Excellent)**: Exceeds baseline requirements, exemplary quality
- **B (Good)**: Meets requirements with only minor gaps, production-ready
- **C (Adequate)**: Meets minimum bar but has clear room for improvement
- **D (Below Standard)**: Below minimum standards but not completely absent
- **F (Failing)**: Does not meet minimum requirements or artifact missing

An F grade means "this needs work before it's acceptable," not "this is worthless."

## Related

- `report-format.lego.md` — Report structure using these grades
- `../INDEX.lego.md` — Pinakes overview
- `../../../agents/theoros.md` — Agent that applies these rules
