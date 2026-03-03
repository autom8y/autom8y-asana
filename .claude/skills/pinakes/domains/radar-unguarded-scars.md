---
name: radar-unguarded-scars-criteria
description: "Radar signal criteria for detecting scars in untested code. Use when: theoros is cross-referencing scar-tissue.md against test-coverage.md to identify regression risks. Triggers: radar unguarded scars, scar regression risk, untested scar locations, knowledge radar."
scope: radar
---

# radar-unguarded-scars Signal Criteria

> This is a radar signal domain. The theoros cross-references `.know/scar-tissue.md` body against `.know/test-coverage.md` body to identify scars that exist in packages lacking test coverage. Scars in untested code are unguarded regressions — they can silently revert.

## Scope

**Input files**:
- `.know/scar-tissue.md` — body text listing SCAR entries with package/file locations
- `.know/test-coverage.md` — body text listing packages with coverage status

**What to read**: Body content of both files (not just frontmatter)
**What NOT to do**: Do not scan source code directly. Work only from the knowledge files.

**Signal question**: Which documented scars exist in packages that test-coverage.md identifies as untested or under-tested? These represent unguarded regression risks.

## Criteria

### Criterion 1: Scar Location Extraction (weight: 25%)

**What to evaluate**: Does the theoros correctly extract SCAR entries from `.know/scar-tissue.md` with their associated package/file locations? Each SCAR entry must have a location for the cross-reference to work.

**Evidence to collect**:
- Read `.know/scar-tissue.md` in full
- Extract all SCAR entries — typically formatted as `SCAR-NNN` with a location field (package path, file name, or both)
- Record: SCAR ID, location (package or file path), category
- Note any SCARs without extractable locations (these cannot be cross-referenced)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of SCARs have location extracted | Complete SCAR inventory with ID, location, category. No SCARs skipped. Location format normalized to package path where possible. |
| B | 80-89% of SCARs have location extracted | Most SCARs extracted; 1-2 skipped with reason documented |
| C | 70-79% of SCARs have location extracted | Majority extracted; some missing locations or location format inconsistent |
| D | 60-69% of SCARs have location extracted | More than 30% of SCARs missing locations; cross-reference unreliable |
| F | < 60% of SCARs have location extracted | Fewer than half of SCARs usable; scar inventory incomplete |

---

### Criterion 2: Coverage Gap Extraction (weight: 25%)

**What to evaluate**: Does the theoros correctly extract the list of untested and under-tested packages from `.know/test-coverage.md`?

**Evidence to collect**:
- Read `.know/test-coverage.md` in full
- Extract packages identified as: no coverage, low coverage, or explicitly flagged as gaps
- Record: package path, coverage status (none / low / partial / adequate)
- Note any packages where coverage status is ambiguous

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of coverage gaps extracted with status | Complete gap inventory: package path + coverage status for all flagged packages. Ambiguous entries noted. |
| B | 80-89% of coverage gaps extracted | Most gaps extracted; 1-2 ambiguous entries handled inconsistently |
| C | 70-79% of coverage gaps extracted | Majority extracted; some packages with unclear status omitted |
| D | 60-69% of coverage gaps extracted | Significant gaps in coverage inventory; results unreliable for cross-reference |
| F | < 60% of coverage gaps extracted | Coverage gap list incomplete; cross-reference cannot proceed meaningfully |

---

### Criterion 3: Cross-Reference Accuracy (weight: 30%)

**What to evaluate**: Does the theoros correctly match SCAR locations against untested packages? The cross-reference identifies SCARs whose location falls within a package that has no or low test coverage.

**Evidence to collect**:
- For each SCAR with a known location, check whether its package appears in the coverage gap list
- Match on package path prefix (e.g., SCAR in `internal/sync/materialize.go` matches gap in `internal/sync`)
- Produce a list: SCAR ID, location, coverage status at that location, risk classification
- Risk classification: `HIGH` = no coverage, `MODERATE` = low coverage, `LOW` = partial coverage

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of cross-referenceable SCARs matched | Full match table: SCAR ID, location, coverage status, risk tier. Prefix matching applied. All matched and unmatched SCARs accounted for. |
| B | 80-89% of SCARs correctly matched | Most matches correct; minor prefix matching gaps or 1-2 SCARs incorrectly classified |
| C | 70-79% correctly matched | Majority matched; prefix matching inconsistent or risk classification absent |
| D | 60-69% correctly matched | More than 30% of SCARs not cross-referenced; matching logic unclear |
| F | < 60% correctly matched | Cross-reference incomplete or unreliable; matches not evidenced |

---

### Criterion 4: Routing Advice Quality (weight: 20%)

**What to evaluate**: For each unguarded scar (HIGH or MODERATE risk), does the theoros produce actionable routing advice?

**Evidence to collect**:
- For each HIGH-risk unguarded scar: advice to target that package with test coverage in a hygiene session
- For each MODERATE-risk unguarded scar: advisory note with suggested action
- Advice must name the specific SCAR ID, package, and suggest the appropriate rite (hygiene or debt-triage)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of HIGH/MODERATE risk SCARs have specific advice | Each unguarded scar: SCAR ID cited, package named, specific rite recommendation, brief rationale for urgency |
| B | 80-89% of unguarded SCARs have actionable advice | Most SCARs have specific advice; minor gaps in rite recommendation specificity |
| C | 70-79% have actionable advice | Advice present but generic ("add tests") rather than package-specific |
| D | 60-69% have actionable advice | Advice vague or missing; user cannot act without significant additional investigation |
| F | < 60% have actionable advice | No actionable advice; findings listed without recommendations |

---

## Grading Calculation

Final grade is weighted average of all criteria midpoint scores (see `schemas/grading.lego.md`). Example:

- Scar Location Extraction: A (midpoint 95%) x 25% = 23.75
- Coverage Gap Extraction: B (midpoint 85%) x 25% = 21.25
- Cross-Reference Accuracy: B (midpoint 85%) x 30% = 25.5
- Routing Advice: A (midpoint 95%) x 20% = 19.0
- **Total: 89.5 -> B**

## Related

- [Pinakes INDEX](../INDEX.lego.md) -- Full audit system documentation
- [radar-recurring-scars-criteria](radar-recurring-scars.lego.md) -- Companion signal: systemic scar patterns
- [scar-tissue-criteria](scar-tissue.lego.md) -- Direct codebase audit of scar documentation quality
- [test-coverage-criteria](test-coverage.lego.md) -- Direct codebase audit of test coverage quality
- [grading schema](../schemas/grading.lego.md) -- Grade calculation rules
