---
name: radar-constraint-violations-criteria
description: "Radar signal criteria for detecting code that violates documented design constraints. Use when: theoros is cross-referencing design-constraints.md against codebase patterns to identify constraint violations. Triggers: radar constraint violations, design tension violations, frozen area violations, knowledge radar."
scope: radar
---

# radar-constraint-violations Signal Criteria

> This is a radar signal domain. The theoros reads `.know/design-constraints.md` to extract documented tensions and frozen areas, then performs targeted codebase checks to detect patterns that contradict those constraints. The primary input is `.know/design-constraints.md`; codebase checks are narrow and targeted (not a full scan).

## Scope

**Input files**:
- `.know/design-constraints.md` — body text listing TENSION-NNN entries and frozen areas

**Codebase checks** (targeted, not full scan):
- Import statements in packages identified as constrained
- File presence/absence in frozen directories
- Pattern matches for anti-patterns named in constraint descriptions

**What NOT to do**: Do not perform a full codebase audit. Only check the specific patterns and locations called out in the constraints document.

**Signal question**: Are the documented design constraints and frozen areas currently being respected in the codebase, or has code drift violated them?

## Criteria

### Criterion 1: Constraint Extraction (weight: 20%)

**What to evaluate**: Does the theoros correctly extract all TENSION-NNN entries and frozen area declarations from `.know/design-constraints.md`?

**Evidence to collect**:
- Read `.know/design-constraints.md` in full
- Extract all TENSION-NNN entries: ID, description, what violates it, relevant packages
- Extract all frozen area declarations: path or pattern, reason for freeze
- Note any constraints that are ambiguous or lack specific locations to check

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of constraints extracted with checkable specifics | Complete constraint inventory: ID, description, violation pattern, affected scope. Frozen areas listed with paths. Ambiguous constraints flagged. |
| B | 80-89% of constraints extracted | Most constraints extracted; 1-2 have incomplete location or violation pattern |
| C | 70-79% of constraints extracted | Majority extracted; several constraints missing enough specifics for a targeted check |
| D | 60-69% of constraints extracted | More than 30% of constraints not extracted or unusable for checking |
| F | < 60% of constraints extracted | Constraint inventory incomplete; checking cannot proceed reliably |

---

### Criterion 2: Targeted Check Coverage (weight: 30%)

**What to evaluate**: For each extracted constraint with a checkable location, does the theoros perform the targeted check? Coverage means: attempted a check for each constraint, not that no violations were found.

**Evidence to collect**:
- For each constraint, document what check was performed and what it looked for
- For import constraints: which packages were checked for disallowed imports
- For frozen areas: whether files were added to frozen paths
- For structural constraints: what code patterns were searched

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of checkable constraints have documented checks | Each constraint: what was checked, how (file read / import scan / grep), result (clean / violation found / inconclusive). All checkable constraints attempted. |
| B | 80-89% of checkable constraints checked | Most constraints checked; 1-2 skipped with reason documented |
| C | 70-79% of checkable constraints checked | Majority checked; some constraints skipped without explanation |
| D | 60-69% checked | More than 30% of constraints not checked; coverage insufficient for reliable signal |
| F | < 60% checked | Fewer than half checked; signal unreliable |

---

### Criterion 3: Violation Detection Accuracy (weight: 30%)

**What to evaluate**: Where checks were performed, were violations correctly identified or correctly confirmed as absent? False negatives (missed violations) are worse than false positives.

**Evidence to collect**:
- For each check performed: result (violation / clean), evidence (file path, line reference, or import statement)
- For violations: the specific code location and how it contradicts the constraint
- For clean checks: brief statement of what was observed that confirms compliance

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of checks produce evidenced conclusions | Each check: clear conclusion with specific evidence. Violations include file path and line context. Clean results describe what was observed. No unsupported assertions. |
| B | 80-89% of checks are evidenced | Most checks evidenced; 1-2 conclusions asserted without specific file/line support |
| C | 70-79% of checks are evidenced | Majority evidenced; several conclusions are plausible but not grounded in specific observations |
| D | 60-69% of checks are evidenced | More than 30% of conclusions lack supporting evidence; reliability questionable |
| F | < 60% of checks are evidenced | Most conclusions unsubstantiated; signal not trustworthy |

---

### Criterion 4: Routing Advice Quality (weight: 20%)

**What to evaluate**: For each detected violation, does the theoros produce actionable routing advice?

**Evidence to collect**:
- For each violation: cite the TENSION-NNN or frozen area name, describe the specific violation, recommend the appropriate next step
- Routing advice should specify the appropriate rite: arch review for structural violations, debt-triage for drift, hygiene for minor inconsistencies

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of violations have specific, actionable advice | Each violation: constraint cited by ID, specific code location named, concrete next step with rite recommendation and rationale |
| B | 80-89% of violations have actionable advice | Most violations have specific advice; minor gaps in rite recommendation specificity |
| C | 70-79% have actionable advice | Advice present but generic ("review this area") rather than violation-specific |
| D | 60-69% have actionable advice | Advice vague or missing the specific command or rite |
| F | < 60% have actionable advice | No actionable advice; violations listed without recommendations |

---

## Grading Calculation

Final grade is weighted average of all criteria midpoint scores (see `schemas/grading.lego.md`). Example:

- Constraint Extraction: A (midpoint 95%) x 20% = 19.0
- Targeted Check Coverage: B (midpoint 85%) x 30% = 25.5
- Violation Detection Accuracy: B (midpoint 85%) x 30% = 25.5
- Routing Advice: A (midpoint 95%) x 20% = 19.0
- **Total: 89.0 -> B**

## Related

- [Pinakes INDEX](../INDEX.lego.md) -- Full audit system documentation
- [radar-architecture-decay-criteria](radar-architecture-decay.lego.md) -- Companion signal: import graph violations
- [design-constraints-criteria](design-constraints.lego.md) -- Direct codebase audit of design constraints documentation quality
- [grading schema](../schemas/grading.lego.md) -- Grade calculation rules
