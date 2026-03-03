---
name: radar-confidence-gaps-criteria
description: "Radar signal criteria for detecting low-confidence knowledge domains. Use when: theoros is running a knowledge radar scan to flag .know/ domains with confidence below acceptable threshold. Triggers: radar confidence gaps, knowledge quality signal, low confidence domains, knowledge radar."
scope: radar
---

# radar-confidence-gaps Signal Criteria

> This is a radar signal domain. The theoros reads `.know/` frontmatter and flags domains where knowledge quality has degraded below a usable threshold. Input is `.know/` file metadata, not raw source code.

## Scope

**Input files**: All `.know/*.md` frontmatter fields
**What to read**: `confidence`, `generated_at`, `domain`, `generator` from each `.know/` file
**What NOT to do**: Do not scan source code. Do not read the body of `.know/` files. Frontmatter only.

**Signal question**: Which knowledge domains have confidence below 0.80 and therefore cannot be reliably used for agent decision-making?

## Criteria

### Criterion 1: Coverage — All Domains Scanned (weight: 20%)

**What to evaluate**: Did the theoros successfully read frontmatter from every `.know/*.md` file present? A partial scan produces an incomplete signal.

**Evidence to collect**:
- Glob `.know/*.md` and count files found
- Attempt to parse frontmatter from each
- Record any files where frontmatter was missing or malformed

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of .know/ files successfully parsed | All files enumerated; frontmatter read from all; no parse failures noted |
| B | 80-89% parsed | Most files scanned; 1-2 parse failures documented with reason |
| C | 70-79% parsed | Majority scanned; several failures or missing files noted |
| D | 60-69% parsed | Significant gaps in scan coverage; unclear which domains were missed |
| F | < 60% parsed | Fewer than half the knowledge files scanned; results unreliable |

---

### Criterion 2: Gap Identification — Domains Below 0.80 (weight: 50%)

**What to evaluate**: For each scanned domain, is the confidence value present and is the threshold check applied correctly? The primary signal: flag every domain with `confidence < 0.80`.

**Evidence to collect**:
- For each `.know/*.md` file: record `domain` name and `confidence` value
- Flag entries where `confidence < 0.80` with the exact value
- Note entries where `confidence` field is missing entirely (treat as failing = flag for refresh)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | All below-threshold domains identified with exact values | Complete table: domain, confidence, flag (yes/no). No domain with confidence < 0.80 missed. Missing confidence fields treated as flags. |
| B | 80-89% of below-threshold domains identified | Most gaps found; 1-2 domains may have been missed or misclassified |
| C | 70-79% identified | Majority of gaps found; some domains skipped or threshold applied inconsistently |
| D | 60-69% identified | Gaps found but threshold inconsistently applied; missing-field handling absent |
| F | < 60% identified | Signal analysis incomplete; significant gaps in threshold checking |

---

### Criterion 3: Routing Advice Quality (weight: 30%)

**What to evaluate**: For each flagged domain, does the theoros produce actionable routing advice? The output must tell the user exactly what to do to resolve the gap.

**Evidence to collect**:
- For each flagged domain, draft routing advice of the form: "Domain `{domain}` has confidence {value} (below 0.80). Consider refreshing with `/know --force {domain}`."
- Advice must reference the specific domain name and the exact confidence value observed
- Advice must include the specific refresh command

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of flagged domains have specific, actionable advice | Each flagged domain has: exact confidence value cited, domain-specific `/know --force` command, brief note on what low confidence means for that domain |
| B | 80-89% of flagged domains have actionable advice | Most domains have specific advice; minor gaps in domain-specific context |
| C | 70-79% have actionable advice | Advice present but generic ("refresh your knowledge files") rather than domain-specific |
| D | 60-69% have actionable advice | Advice vague or missing the specific command; user cannot act without additional investigation |
| F | < 60% have actionable advice | No actionable advice produced; findings presented without recommendations |

---

## Grading Calculation

Final grade is weighted average of all criteria midpoint scores (see `schemas/grading.lego.md`). Example:

- Coverage: B (midpoint 85%) x 20% = 17.0
- Gap Identification: A (midpoint 95%) x 50% = 47.5
- Routing Advice: B (midpoint 85%) x 30% = 25.5
- **Total: 90.0 -> A**

## Related

- [Pinakes INDEX](../INDEX.lego.md) -- Full audit system documentation
- [radar-staleness-criteria](radar-staleness.lego.md) -- Companion signal: expired domains
- [grading schema](../schemas/grading.lego.md) -- Grade calculation rules
