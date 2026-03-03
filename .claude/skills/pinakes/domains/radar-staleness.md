---
name: radar-staleness-criteria
description: "Radar signal criteria for detecting expired knowledge domains. Use when: theoros is running a knowledge radar scan to flag .know/ domains where generated_at + expires_after has passed. Triggers: radar staleness, knowledge expiry signal, stale knowledge domains, knowledge radar."
scope: radar
---

# radar-staleness Signal Criteria

> This is a radar signal domain. The theoros reads `.know/` frontmatter and flags domains whose knowledge has expired. Input is `.know/` file metadata, not raw source code. Stale knowledge is knowledge that was accurate when written but may no longer reflect the current codebase.

## Scope

**Input files**: All `.know/*.md` frontmatter fields
**What to read**: `generated_at`, `expires_after`, `domain` from each `.know/` file
**What NOT to do**: Do not scan source code. Do not read the body of `.know/` files. Frontmatter only.
**Current date**: Use today's date as the reference point for expiry calculation.

**Signal question**: Which knowledge domains have passed their expiry date and should be regenerated before being used for agent decision-making?

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

### Criterion 2: Expiry Calculation Correctness (weight: 50%)

**What to evaluate**: For each domain, is the expiry computed correctly? The formula is: `generated_at + expires_after < now`. Flag when the computed expiry date is in the past.

**Evidence to collect**:
- For each `.know/*.md` file: record `domain`, `generated_at`, `expires_after`, computed expiry date
- Flag entries where the expiry date has passed, showing the computation explicitly
- Handle missing fields: if `expires_after` is absent, flag as "expiry unknown — treat as stale"
- Handle missing `generated_at`: flag as "generation date unknown — treat as stale"

**Expiry field formats to support**:
- `expires_after` as duration string: `"7d"`, `"30d"`, `"90d"` — add to `generated_at`
- `expires_after` as date string: compare directly to today

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of domains have correct expiry determination | Complete table: domain, generated_at, expires_after, computed_expiry, stale (yes/no), days_overdue. Missing fields treated as stale. Calculation shown explicitly. |
| B | 80-89% of domains correctly evaluated | Most domains evaluated correctly; 1-2 edge cases (missing fields) handled inconsistently |
| C | 70-79% correctly evaluated | Majority evaluated; some domains skipped or duration parsing inconsistent |
| D | 60-69% correctly evaluated | Expiry formula applied to some domains; missing-field handling absent or wrong |
| F | < 60% correctly evaluated | Signal analysis incomplete; expiry calculation unreliable |

---

### Criterion 3: Routing Advice Quality (weight: 30%)

**What to evaluate**: For each stale domain, does the theoros produce actionable routing advice? The output must tell the user exactly what to do and how urgent the refresh is.

**Evidence to collect**:
- For each stale domain, draft routing advice including: domain name, days overdue, specific refresh command
- Prioritize by days overdue (most stale first)
- Include urgency framing: domains overdue by 30+ days are critical; 7-30 days are moderate; < 7 days are low urgency

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of stale domains have specific, prioritized advice | Each stale domain has: exact days overdue, urgency tier, specific `/know --force {domain}` command; list ordered by staleness severity |
| B | 80-89% of stale domains have actionable advice | Most domains have specific advice and refresh command; urgency ordering partially applied |
| C | 70-79% have actionable advice | Advice present with domain name but missing days-overdue or urgency framing |
| D | 60-69% have actionable advice | Advice vague or missing specific commands; no urgency prioritization |
| F | < 60% have actionable advice | No actionable advice produced; stale domains listed without recommendations |

---

## Grading Calculation

Final grade is weighted average of all criteria midpoint scores (see `schemas/grading.lego.md`). Example:

- Coverage: A (midpoint 95%) x 20% = 19.0
- Expiry Calculation: B (midpoint 85%) x 50% = 42.5
- Routing Advice: A (midpoint 95%) x 30% = 28.5
- **Total: 90.0 -> A**

## Related

- [Pinakes INDEX](../INDEX.lego.md) -- Full audit system documentation
- [radar-confidence-gaps-criteria](radar-confidence-gaps.lego.md) -- Companion signal: low-confidence domains
- [grading schema](../schemas/grading.lego.md) -- Grade calculation rules
