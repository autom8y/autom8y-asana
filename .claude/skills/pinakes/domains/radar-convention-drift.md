---
name: radar-convention-drift-criteria
description: "Radar signal criteria for detecting adherence gaps between documented conventions and codebase reality. Use when: theoros is cross-referencing conventions.md against a codebase sample to detect convention drift. Triggers: radar convention drift, convention adherence signal, code style drift, knowledge radar."
scope: radar
---

# radar-convention-drift Signal Criteria

> This is a radar signal domain. The theoros reads `.know/conventions.md` to extract documented patterns (error handling, testing style, naming, file organization), then samples the codebase to check adherence. The primary input is `.know/conventions.md`; codebase checks are sampling-based (10-15 representative files), not exhaustive.

## Scope

**Input files**:
- `.know/conventions.md` — body text documenting code conventions, patterns, and idioms

**Codebase sample** (10-15 representative files, not a full scan):
- Prefer files that have been recently changed (if detectable)
- Cover multiple packages to detect cross-cutting drift
- Include at least one file from each major layer: `cmd/`, `internal/cmd/`, `internal/` domain packages

**What NOT to do**: Do not audit every file. Sampling is sufficient for a drift signal. Exhaustive audit belongs in `/theoria conventions`.

**Signal question**: Are the documented conventions being followed in representative areas of the codebase, or has drift crept in since the conventions were last documented?

## Criteria

### Criterion 1: Convention Extraction (weight: 20%)

**What to evaluate**: Does the theoros correctly extract specific, checkable conventions from `.know/conventions.md`? Vague conventions ("write clean code") cannot be checked; specific conventions can.

**Evidence to collect**:
- Read `.know/conventions.md` in full
- Extract conventions as checkable rules: category, rule description, what violation looks like
- Categories to look for: error handling patterns, testing patterns, naming conventions, file organization, import style
- Note any conventions that are too vague to check with a sampling approach

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of conventions extracted as checkable rules | Complete convention inventory: category, specific rule, what a violation looks like. All checkable conventions listed. Vague conventions flagged as not-checkable with reason. |
| B | 80-89% of conventions extracted | Most conventions extracted as checkable rules; 1-2 too vague or ambiguous |
| C | 70-79% of conventions extracted | Majority extracted; several conventions paraphrased rather than made checkable |
| D | 60-69% of conventions extracted | More than 30% of conventions not extracted or remain too vague to check |
| F | < 60% of conventions extracted | Convention list incomplete; drift checking cannot proceed reliably |

---

### Criterion 2: Sample Selection Quality (weight: 15%)

**What to evaluate**: Does the sample of files chosen for checking represent the codebase well? A biased sample (e.g., only test files, only one package) produces an unreliable drift signal.

**Evidence to collect**:
- List the 10-15 files sampled with their package paths
- Document the selection rationale (why these files)
- Confirm coverage across at least 3 different packages or layers

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | Sample covers 4+ packages/layers with clear rationale | File list provided with package paths; layers represented (cmd, internal command, internal domain); rationale stated |
| B | Sample covers 3+ packages/layers | File list provided; 3 or more distinct packages represented |
| C | Sample covers 2 packages/layers | File list provided but concentrated in 1-2 areas; may miss layer-specific drift |
| D | Sample covers only 1 package | Most files from one package; sample bias likely affects findings |
| F | Sample not documented | Files sampled but not listed; results not reproducible |

---

### Criterion 3: Adherence Check Accuracy (weight: 40%)

**What to evaluate**: For each convention checked against the sample, is the adherence/drift finding accurate and evidenced? This is the core of the drift signal.

**Evidence to collect**:
- For each convention × sampled file where a check was performed: result (adheres / drifts / N/A), with specific evidence
- For drift findings: quote or describe the specific violation with file path and approximate location
- Compute an adherence ratio per convention: `(files adhering) / (files where convention applies)`
- Identify which conventions show the highest drift rates

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of convention checks are evidenced | Per-convention adherence table: convention name, files checked, adherent count, drift count, adherence ratio, sample violations with file paths |
| B | 80-89% of convention checks are evidenced | Most checks evidenced; 1-2 findings asserted without specific file reference |
| C | 70-79% of convention checks are evidenced | Majority evidenced; some conclusions are plausible assessments without quoted evidence |
| D | 60-69% of convention checks are evidenced | More than 30% of findings lack file-level evidence; signal reliability questionable |
| F | < 60% of convention checks are evidenced | Most findings unsubstantiated; drift signal not trustworthy |

---

### Criterion 4: Routing Advice Quality (weight: 25%)

**What to evaluate**: For each convention showing notable drift (adherence ratio below 70%), does the theoros produce actionable routing advice?

**Evidence to collect**:
- For each convention with >30% drift in sample: specific advice on what to address
- Routing advice should specify the appropriate rite: debt-triage for systemic drift, hygiene session for scattered violations
- Prioritize by drift severity and convention category (error handling drift is more critical than naming drift)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of drift conventions have specific, prioritized advice | Each drifting convention: adherence ratio cited, severity (critical/moderate/low), specific rite recommendation, rationale for priority |
| B | 80-89% of drift conventions have actionable advice | Most drifting conventions have specific advice; priority ordering partially applied |
| C | 70-79% have actionable advice | Advice present with convention name but missing severity framing or rite specificity |
| D | 60-69% have actionable advice | Advice vague ("fix convention adherence"); no prioritization |
| F | < 60% have actionable advice | No actionable advice; drift findings listed without recommendations |

---

## Grading Calculation

Final grade is weighted average of all criteria midpoint scores (see `schemas/grading.lego.md`). Example:

- Convention Extraction: A (midpoint 95%) x 20% = 19.0
- Sample Selection: B (midpoint 85%) x 15% = 12.75
- Adherence Check Accuracy: B (midpoint 85%) x 40% = 34.0
- Routing Advice: A (midpoint 95%) x 25% = 23.75
- **Total: 89.5 -> B**

## Related

- [Pinakes INDEX](../INDEX.lego.md) -- Full audit system documentation
- [conventions-criteria](conventions.lego.md) -- Direct codebase audit of convention compliance (exhaustive)
- [radar-architecture-decay-criteria](radar-architecture-decay.lego.md) -- Companion signal: structural violations
- [grading schema](../schemas/grading.lego.md) -- Grade calculation rules
