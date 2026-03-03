---
name: advocatus-scar-tissue-criteria
description: "Adversarial challenge criteria for .know/scar-tissue.md accuracy. Use when: theoros is running advocatus diaboli challenge mode to find undocumented scars or scars whose fixes have regressed. Triggers: advocatus scar-tissue challenge, challenge scar tissue, scar regression, undocumented scars, adversarial scar audit."
scope: adversarial
---

# advocatus-scar-tissue Challenge Criteria

> **INVERTED GRADING — READ BEFORE PROCEEDING**
>
> This is an adversarial (advocatus diaboli) domain. Grading is the OPPOSITE of a standard audit.
>
> - **A (Excellent)** = FEW problems found — the scar-tissue document is ACCURATE and fixes are holding
> - **F (Failing)** = MANY problems found — scars have regressed, or significant scars are undocumented
>
> The theoros role here is devil's advocate: actively seek (1) documented scars whose defensive fixes have been removed or weakened, and (2) code patterns suggesting NEW undocumented scars. A high grade means fixes are in place and documentation is complete. A low grade means regressions or gaps have been found.

## Scope

**Input file (the thing being challenged)**: `.know/scar-tissue.md`

**Codebase scan**:
- Defensive patterns: guard clauses, explicit error checks, nil guards, special-case handling
- Comments: `// SCAR`, `// NOTE`, `// HACK`, `// BUG`, `// FIXME`, `// WORKAROUND`, `// defensive`
- Test files: tests specifically guarding known failure modes
- Bug fix commits: patterns suggesting past pain in current code (though source history is secondary; focus on current code)

**What to do**: Read `.know/scar-tissue.md` completely. For each documented SCAR, verify its defensive fix still exists in the codebase. Additionally, scan for code patterns suggesting undocumented scars: defensive code without a SCAR entry, comments signaling pain points, or workarounds without documentation.

**What NOT to do**: Do not validate that scars were correctly diagnosed originally. Challenge whether fixes are still in place and whether new scars have emerged.

**Challenge question**: "Find undocumented scars or documented scars whose fixes have regressed."

## Challenge Output Format

Each finding must follow this structure:

| Field | Content |
|-------|---------|
| **Claim** | For regressions: the documented fix from `.know/scar-tissue.md`. For undocumented scars: description of the defensive pattern or comment found. |
| **Counter-evidence** | File path, approximate line, specific code showing the fix is absent (regression) or a new defensive pattern exists (undocumented scar) |
| **Contradiction strength** | `strong` (fix clearly removed or pattern clearly undocumented), `moderate` (fix weakened or pattern ambiguous), `weak` (possible exception or false positive) |
| **Recommendation** | Re-apply the fix, add new SCAR entry to `.know/scar-tissue.md`, or accept as intentional removal with documentation |

## Criteria

### Criterion 1: Documented Scar Inventory (weight: 15%)

**What to evaluate**: Does the theoros correctly inventory every SCAR documented in `.know/scar-tissue.md`? Missed SCARs cannot be checked for regression.

**Evidence to collect**:
- Read `.know/scar-tissue.md` completely
- Extract every SCAR entry: ID (if present), description, affected location, stated defensive fix
- Count total SCARs documented
- Note SCARs where the defensive fix is described concretely (checkable) vs. vaguely (hard to verify)

**INVERTED GRADING** — A = complete inventory (enables thorough regression checking):

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 100% of documented SCARs inventoried with location and fix description | Complete SCAR table: ID, location, fix mechanism; checkable vs. uncheckable classified |
| B | 90-99% of documented SCARs inventoried | All but 1-2 SCARs inventoried; missed entries documented |
| C | 80-89% of documented SCARs inventoried | Most SCARs captured; some entries lack sufficient detail to check for regression |
| D | 70-79% of documented SCARs inventoried | Notable gaps in inventory; regression checking will be incomplete |
| F | < 70% of documented SCARs inventoried | Incomplete inventory; regression analysis unreliable |

---

### Criterion 2: Fix Regression Detection (weight: 40%)

**What to evaluate**: For each documented SCAR with a concrete defensive fix, is the fix still present in the codebase? A regression means the fix was removed or weakened — the scar is now unguarded.

**Evidence to collect**:
- For each SCAR with a concrete fix: locate the affected file(s) and check whether the defensive mechanism is present
- Document regressions: SCAR ID/description, fix that should be present, evidence it is absent or weakened
- Document confirmed fixes: SCAR ID/description, fix location in current code
- Calculate: total SCARs checked vs. regressions found

**INVERTED GRADING** — A = no regressions (all fixes in place); F = many regressions:

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 0 regressions found | All checkable SCARs verified as present; file paths and code cited for each confirmation |
| B | 1 regression found | One fix absent or weakened; specific file and missing pattern documented |
| C | 2-3 regressions found | A few fixes have been removed or weakened; each documented with evidence |
| D | 4-5 regressions found | Multiple scars are unguarded; significant regression risk |
| F | 6+ regressions found | Defensive fixes have been systematically removed; scar documentation is dangerously outdated |

---

### Criterion 3: Undocumented Scar Detection (weight: 35%)

**What to evaluate**: Are there defensive patterns, workaround comments, or special-case handling in the codebase that suggest undocumented scars? These are signals that pain was experienced and code was hardened, but `.know/scar-tissue.md` was not updated.

**Evidence to collect**:
- Scan source files for scar-signal comments: `// HACK`, `// WORKAROUND`, `// defensive`, `// BUG`, `// FIXME`, `// NOTE:`, `// TODO:`, or explanatory comments beginning with "We need to..." or "This is because..."
- Look for guard clauses that are unusually specific (e.g., `if x == nil || x.field == "" { return errSpecificThing }`) suggesting a past failure mode
- Look for retry logic, error recovery, or fallback paths that lack documentation
- For each candidate: check whether `.know/scar-tissue.md` has a corresponding entry
- Classify each candidate: likely undocumented scar (warrants new entry) vs. normal defensive code

**INVERTED GRADING** — A = few undocumented scars found (documentation is complete); F = many undocumented scars:

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 0-1 likely undocumented scars found | Files scanned listed; any candidates evaluated and dismissed with reasoning; any single finding described |
| B | 2-3 likely undocumented scars found | Candidates described with file path, code snippet, and why it suggests an undocumented scar |
| C | 4-6 likely undocumented scars found | Multiple undocumented patterns; documentation has coverage gaps |
| D | 7-10 likely undocumented scars found | Scar documentation substantially incomplete; many hardened areas lack entries |
| F | > 10 likely undocumented scars found | Scar documentation is a significant underrepresentation of actual defensive code |

---

### Criterion 4: Scar Location Accuracy (weight: 10%)

**What to evaluate**: For documented SCARs that cite specific files or packages as affected locations, do those locations still match the current codebase? Refactoring may have moved code, making the documented locations stale.

**Evidence to collect**:
- For each SCAR that references a specific file, function, or package: verify the location exists and the referenced code is present
- Document SCARs with stale locations: what the document says vs. where the code actually lives now
- Note if the SCAR's core concern is still valid even if the location changed

**INVERTED GRADING** — A = all locations accurate; F = many stale locations:

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of SCAR locations are accurate | Each location-specific SCAR verified; any discrepancies explained (refactor moved it) |
| B | 80-89% of SCAR locations accurate | Most locations valid; 1-2 SCARs point to moved or renamed code |
| C | 70-79% of SCAR locations accurate | Several SCARs have stale locations; document may confuse future readers |
| D | 60-69% of SCAR locations accurate | Significant location drift; SCARs cannot be acted on without additional investigation |
| F | < 60% of SCAR locations accurate | SCAR location data is substantially stale; document is unreliable as a reference |

---

## Grading Calculation

Final grade is weighted average of all criteria midpoint scores (see `schemas/grading.lego.md`). Reminder: for this domain, LOWER grades indicate MORE problems found (regressions, undocumented scars, stale locations).

Example (well-maintained scar documentation with fixes in place):

- Documented Scar Inventory: A (midpoint 95%) x 15% = 14.25
- Fix Regression Detection: A (midpoint 95%) x 40% = 38.0
- Undocumented Scar Detection: B (midpoint 85%) x 35% = 29.75
- Scar Location Accuracy: A (midpoint 95%) x 10% = 9.5
- **Total: 91.5 -> A** (few problems found; scar documentation is accurate and fixes are holding)

Example (scar documentation with regressions and gaps):

- Documented Scar Inventory: B (midpoint 85%) x 15% = 12.75
- Fix Regression Detection: D (midpoint 65%) x 40% = 26.0
- Undocumented Scar Detection: C (midpoint 75%) x 35% = 26.25
- Scar Location Accuracy: C (midpoint 75%) x 10% = 7.5
- **Total: 72.5 -> C** (moderate problems; some fixes have regressed and documentation has gaps)

## Related

- [Pinakes INDEX](../INDEX.lego.md) -- Full audit system documentation
- [scar-tissue-criteria](scar-tissue.lego.md) -- Direct scar-tissue audit (confirmatory, not adversarial)
- [radar-unguarded-scars-criteria](radar-unguarded-scars.lego.md) -- Radar signal: scars lacking test coverage
- [radar-recurring-scars-criteria](radar-recurring-scars.lego.md) -- Radar signal: systemic scar categories
- [grading schema](../schemas/grading.lego.md) -- Grade calculation rules
