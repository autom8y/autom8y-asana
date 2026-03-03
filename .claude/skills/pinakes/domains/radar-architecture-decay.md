---
name: radar-architecture-decay-criteria
description: "Radar signal criteria for detecting import violations against the documented layer model. Use when: theoros is cross-referencing architecture.md layer model against the import graph to detect architectural decay. Triggers: radar architecture decay, import violations, layer boundary violations, knowledge radar."
scope: radar
---

# radar-architecture-decay Signal Criteria

> This is a radar signal domain. The theoros reads `.know/architecture.md` to extract the documented layer model, then examines the actual import graph to identify violations: hub packages importing leaf packages, circular dependencies, and undocumented cross-cutting imports. Input is `.know/architecture.md` + targeted import scanning; not a full codebase audit.

## Scope

**Input files**:
- `.know/architecture.md` — body text documenting the layer model, package hierarchy, and documented cross-cutting patterns

**Import graph checks** (targeted, not exhaustive):
- Scan `import` statements in packages that the layer model identifies as "leaf" or "domain" packages
- Check for reverse-direction imports (low-level packages importing high-level packages)
- Check hub packages for imports that cross documented boundaries
- Look for undocumented cross-cutting imports (packages outside the stated dependency direction)

**What NOT to do**: Do not scan every import in every file. Focus on boundaries identified in the layer model. Exhaustive import audit belongs in `/theoria architecture`.

**Signal question**: Are the import relationships in the codebase consistent with the layer model documented in architecture.md, or have boundary violations crept in?

## Criteria

### Criterion 1: Layer Model Extraction (weight: 20%)

**What to evaluate**: Does the theoros correctly extract the layer model from `.know/architecture.md`? The model must be specific enough to define which packages should and should not import each other.

**Evidence to collect**:
- Read `.know/architecture.md` in full
- Extract the layer hierarchy: list each layer, its packages, and the stated import direction
- Identify packages explicitly documented as "leaf" (should not import siblings), "hub" (imports many), or "cross-cutting" (intentional multi-layer usage)
- Note any packages or relationships that the architecture document does not clearly classify

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of documented packages classified with clear import direction | Complete layer table: layer name, member packages, allowed import directions, documented exceptions. Unclassified packages explicitly noted. |
| B | 80-89% of packages classified | Most packages classified; 1-2 have ambiguous layer assignment |
| C | 70-79% of packages classified | Majority classified; several packages not clearly assigned to a layer |
| D | 60-69% of packages classified | More than 30% of packages not classifiable from the architecture document |
| F | < 60% of packages classified | Layer model too vague to support import graph checking |

---

### Criterion 2: Import Graph Check Coverage (weight: 30%)

**What to evaluate**: For each layer boundary identified, does the theoros check the relevant packages for violations? Coverage means: an import scan was attempted for the key boundary packages.

**Evidence to collect**:
- For each layer boundary: which packages were checked, what import patterns were scanned for
- For leaf packages: scan for imports of hub or CLI-layer packages
- For hub packages: scan for circular or upward imports
- Document which boundaries could not be checked and why (e.g., package does not exist yet)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of layer boundaries have documented checks | Each boundary: what was checked (package list), what was looked for (disallowed import patterns), outcome (clean / violation). All key boundaries attempted. |
| B | 80-89% of boundaries checked | Most boundaries checked; 1-2 skipped with reason documented |
| C | 70-79% of boundaries checked | Majority checked; some boundaries skipped without explanation |
| D | 60-69% checked | More than 30% of boundaries not checked; coverage insufficient for reliable signal |
| F | < 60% checked | Fewer than half of boundaries checked; signal unreliable |

---

### Criterion 3: Violation Detection Accuracy (weight: 30%)

**What to evaluate**: Where import checks were performed, were violations correctly identified? A violation is an import that contradicts the documented layer model and is not listed as a documented exception.

**Evidence to collect**:
- For each checked boundary: list of violations found with specific import statements, source package, imported package
- For each violation: confirm it is not a documented exception in `architecture.md`
- For clean boundaries: brief description of what was observed confirming compliance
- Classify violations: `CRITICAL` (hub importing leaf, circular dep), `MODERATE` (undocumented cross-cutting), `LOW` (minor boundary ambiguity)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of checks produce evidenced conclusions | Each check: clear conclusion with specific import evidence. Violations include source file, import path. Exceptions documented in architecture.md correctly excluded. Severity classification applied. |
| B | 80-89% of checks are evidenced | Most checks evidenced; 1-2 violations identified without specific file reference |
| C | 70-79% of checks are evidenced | Majority evidenced; some conclusions based on inference rather than specific import observation |
| D | 60-69% of checks are evidenced | More than 30% of conclusions lack specific import evidence |
| F | < 60% of checks are evidenced | Most conclusions unsubstantiated; signal not trustworthy |

---

### Criterion 4: Routing Advice Quality (weight: 20%)

**What to evaluate**: For each detected boundary violation, does the theoros produce actionable routing advice?

**Evidence to collect**:
- For each CRITICAL violation: specific arch review recommendation with the two packages named
- For each MODERATE violation: advisory with suggested review approach
- Advice should reference the specific architecture layer model being violated
- Note whether the violation might indicate the architecture document needs updating vs. the code needs fixing

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of violations have specific, actionable advice | Each violation: specific packages named, layer model reference cited, concrete recommendation (arch review / code fix / documentation update), reasoning for classification |
| B | 80-89% of violations have actionable advice | Most violations have specific advice; minor gaps in recommendation specificity |
| C | 70-79% have actionable advice | Advice present but generic ("review the architecture") rather than violation-specific |
| D | 60-69% have actionable advice | Advice vague; packages not specifically named in recommendations |
| F | < 60% have actionable advice | No actionable advice; violations listed without recommendations |

---

## Grading Calculation

Final grade is weighted average of all criteria midpoint scores (see `schemas/grading.lego.md`). Example:

- Layer Model Extraction: B (midpoint 85%) x 20% = 17.0
- Import Graph Check Coverage: B (midpoint 85%) x 30% = 25.5
- Violation Detection Accuracy: A (midpoint 95%) x 30% = 28.5
- Routing Advice: B (midpoint 85%) x 20% = 17.0
- **Total: 88.0 -> B**

## Related

- [Pinakes INDEX](../INDEX.lego.md) -- Full audit system documentation
- [architecture-criteria](architecture.lego.md) -- Direct codebase audit of architecture documentation completeness
- [radar-constraint-violations-criteria](radar-constraint-violations.lego.md) -- Companion signal: constraint violations
- [grading schema](../schemas/grading.lego.md) -- Grade calculation rules
