---
name: radar-recurring-scars-criteria
description: "Radar signal criteria for detecting systemic scar patterns by category. Use when: theoros is analyzing scar-tissue.md to count SCARs by category and flag categories with 3+ entries as systemic issues. Triggers: radar recurring scars, systemic scar patterns, scar category analysis, knowledge radar."
scope: radar
---

# radar-recurring-scars Signal Criteria

> This is a radar signal domain. The theoros reads `.know/scar-tissue.md` body, counts SCAR entries by category, and flags categories with 3 or more entries as systemic patterns requiring attention beyond individual scar management. Single-source analysis — no codebase scanning required.

## Scope

**Input files**:
- `.know/scar-tissue.md` — body text listing SCAR entries with categories

**What to read**: Body content only (categories and counts)
**What NOT to do**: Do not scan source code. Do not cross-reference other knowledge files. This is single-source analysis.

**Signal question**: Which scar categories appear 3 or more times, indicating a systemic issue that warrants a root-cause investigation rather than individual scar fixes?

## Criteria

### Criterion 1: Scar Inventory Completeness (weight: 30%)

**What to evaluate**: Does the theoros extract all SCAR entries from `.know/scar-tissue.md` with their category classifications? Missing SCARs will skew category counts.

**Evidence to collect**:
- Read `.know/scar-tissue.md` in full
- Extract all SCAR entries: SCAR ID, category, brief description
- Report total SCAR count found
- Note any entries that lack a clear category classification (these cannot be counted by category)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of SCARs extracted with category | Complete SCAR inventory table: ID, category, one-line description. Total count stated. Uncategorized SCARs listed separately. |
| B | 80-89% of SCARs extracted with category | Most SCARs extracted; 1-2 missing categories noted |
| C | 70-79% of SCARs extracted with category | Majority extracted; several SCARs have ambiguous or missing category |
| D | 60-69% of SCARs extracted with category | More than 30% of SCARs not usable for category analysis |
| F | < 60% of SCARs extracted with category | Inventory incomplete; category counts unreliable |

---

### Criterion 2: Category Count Accuracy (weight: 40%)

**What to evaluate**: Are SCAR counts aggregated correctly by category? The threshold for a systemic flag is 3 or more SCARs in a single category.

**Evidence to collect**:
- Produce a category frequency table: category name, count, SCAR IDs in that category
- Flag all categories with count >= 3 as systemic patterns
- Sort by count descending for prioritization
- Note categories with count = 2 as "approaching threshold" (advisory, not flagged)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% category counts accurate | Category frequency table provided: name, count, SCAR IDs listed. All categories with 3+ entries flagged. Count=2 categories noted as approaching threshold. Sorted by count. |
| B | 80-89% category counts accurate | Frequency table present; most categories correctly counted; 1-2 SCAR IDs missing from a category listing |
| C | 70-79% category counts accurate | Counts present but SCAR ID listings incomplete; threshold flagging applied inconsistently |
| D | 60-69% category counts accurate | Category names listed with approximate counts but without supporting SCAR IDs; counts not verifiable |
| F | < 60% category counts accurate | Category counts not computed or not evidenced; analysis unreliable |

---

### Criterion 3: Systemic Pattern Characterization (weight: 15%)

**What to evaluate**: For each flagged systemic category (3+ SCARs), does the theoros provide a brief characterization of what makes it systemic? Naming the pattern helps with root-cause work.

**Evidence to collect**:
- For each flagged category: describe what the scars have in common beyond just the category label
- Identify if there is a common root area (all in same package, all related to same operation type, all from similar time period)
- Characterization should be 1-2 sentences, factual, based on the SCAR descriptions observed

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of flagged categories have meaningful characterization | Each flagged category: what the scars share, any common package or operation pattern, 1-2 sentence synthesis based on actual SCAR descriptions |
| B | 80-89% of flagged categories characterized | Most categories have characterization; 1-2 have only the category label without synthesis |
| C | 70-79% characterized | Majority characterized; some characterizations are generic ("multiple errors of this type") without specific synthesis |
| D | 60-69% characterized | Characterization attempted but not grounded in SCAR specifics; reads as filler |
| F | < 60% characterized | No characterization beyond category count; pattern identification not attempted |

---

### Criterion 4: Routing Advice Quality (weight: 15%)

**What to evaluate**: For each flagged systemic category, does the theoros produce actionable routing advice that goes beyond "look at this category"?

**Evidence to collect**:
- For each flagged category: specific recommendation referencing the category name, count, and suggested next action
- Routing advice must suggest the appropriate rite: debt-triage for root-cause investigation, hygiene for concentrated cleanup
- Distinguish between high-priority (5+ SCARs) and standard (3-4 SCARs) systemic flags

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of flagged categories have specific, prioritized advice | Each flagged category: count cited, priority tier (high >= 5, standard 3-4), specific rite recommendation, brief rationale for why root-cause investigation is warranted |
| B | 80-89% of flagged categories have actionable advice | Most categories have specific advice with rite recommendation; priority tiers partially applied |
| C | 70-79% have actionable advice | Advice present with category name but missing rite specificity or priority framing |
| D | 60-69% have actionable advice | Advice vague ("investigate this pattern"); no rite recommendation or prioritization |
| F | < 60% have actionable advice | No actionable advice; systemic flags listed without recommendations |

---

## Grading Calculation

Final grade is weighted average of all criteria midpoint scores (see `schemas/grading.lego.md`). Example:

- Scar Inventory Completeness: A (midpoint 95%) x 30% = 28.5
- Category Count Accuracy: A (midpoint 95%) x 40% = 38.0
- Systemic Pattern Characterization: B (midpoint 85%) x 15% = 12.75
- Routing Advice: B (midpoint 85%) x 15% = 12.75
- **Total: 92.0 -> A**

## Related

- [Pinakes INDEX](../INDEX.lego.md) -- Full audit system documentation
- [radar-unguarded-scars-criteria](radar-unguarded-scars.lego.md) -- Companion signal: scars in untested code
- [scar-tissue-criteria](scar-tissue.lego.md) -- Direct codebase audit of scar documentation quality
- [grading schema](../schemas/grading.lego.md) -- Grade calculation rules
