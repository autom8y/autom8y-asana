---
name: advocatus-conventions-criteria
description: "Adversarial challenge criteria for .know/conventions.md accuracy. Use when: theoros is running advocatus diaboli challenge mode to find code that contradicts documented conventions. Triggers: advocatus conventions challenge, challenge conventions, conventions accuracy, adversarial conventions audit."
scope: adversarial
---

# advocatus-conventions Challenge Criteria

> **INVERTED GRADING — READ BEFORE PROCEEDING**
>
> This is an adversarial (advocatus diaboli) domain. Grading is the OPPOSITE of a standard audit.
>
> - **A (Excellent)** = FEW contradictions found — the conventions document is ACCURATE
> - **F (Failing)** = MANY contradictions found — the conventions document is INACCURATE
>
> The theoros role here is devil's advocate: actively seek code that CONTRADICTS `.know/conventions.md`. A high grade means the challenge found little to contradict. A low grade means the documented conventions do not match codebase reality.

## Scope

**Input file (the thing being challenged)**: `.know/conventions.md`

**Codebase scan** (30-40 representative files across all layers):
- `cmd/` — CLI entry points
- `internal/cmd/` — command implementations
- `internal/` — domain packages
- `*_test.go` files — testing convention adherence

**What to do**: Read `.know/conventions.md` in full. Extract every stated convention as a falsifiable claim. Then search the codebase for counterexamples that contradict each claim.

**What NOT to do**: Do not confirm conventions. The task is to find contradictions, not validate adherence.

**Challenge question**: "Find code that contradicts the documented conventions in `.know/conventions.md`."

## Challenge Output Format

Each finding must follow this structure:

| Field | Content |
|-------|---------|
| **Claim** | Exact quote or close paraphrase from `.know/conventions.md` |
| **Counter-evidence** | File path, approximate line, specific code that contradicts the claim |
| **Contradiction strength** | `strong` (clear violation), `moderate` (plausible exception), `weak` (ambiguous) |
| **Recommendation** | Update the knowledge document, fix the code, or accept as documented exception |

## Criteria

### Criterion 1: Claim Extraction Completeness (weight: 20%)

**What to evaluate**: Does the theoros extract every falsifiable convention claim from `.know/conventions.md`? Missed claims cannot be challenged. This is the prerequisite for all subsequent criteria.

**Evidence to collect**:
- Read `.know/conventions.md` completely
- List every convention as a falsifiable claim: category, claim text, what a contradiction looks like
- Note any conventions too vague to falsify (e.g., "write readable code") — flag these as uncheckable
- Count total checkable claims extracted

**INVERTED GRADING** — A = many claims extracted (high extraction quality means more challenge surface):

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of checkable conventions extracted as falsifiable claims | Complete claim inventory with contradiction indicators for each; vague conventions flagged separately |
| B | 80-89% of conventions extracted | Most claims captured; 1-3 conventions not broken down to falsifiable form |
| C | 70-79% of conventions extracted | Majority extracted; some conventions remain too vague to check against |
| D | 60-69% of conventions extracted | Less than 70% of conventions turned into checkable claims; challenge surface incomplete |
| F | < 60% of conventions extracted | Fewer than 60% of conventions extracted; adversarial analysis cannot proceed reliably |

---

### Criterion 2: Error Handling Convention Contradictions (weight: 30%)

**What to evaluate**: `.know/conventions.md` documents error handling patterns. Find code that violates these patterns: swallowed errors, missing wrapping, wrong sentinel values, inconsistent return styles.

**Evidence to collect**:
- Extract error handling conventions from `.know/conventions.md`
- Scan 15-20 Go source files in `internal/` and `cmd/` for error handling patterns
- Document each contradiction with file path and the specific violation
- Tally: total error sites sampled vs. sites with contradictions

**INVERTED GRADING** — A = few contradictions (conventions are accurate); F = many contradictions:

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | < 10% of sampled error sites contradict documented patterns | Contradiction count and percentage; specific non-conforming files listed |
| B | 10-20% of sampled error sites contradict documented patterns | Contradiction files listed with the specific violation described |
| C | 21-30% of sampled error sites contradict documented patterns | Majority of files follow conventions; contradictions documented with file paths |
| D | 31-40% of sampled error sites contradict documented patterns | Significant gap between documented and actual error handling; examples cited |
| F | > 40% of sampled error sites contradict documented patterns | Error handling conventions are substantially inaccurate; widespread contradictions with evidence |

---

### Criterion 3: Testing Convention Contradictions (weight: 25%)

**What to evaluate**: `.know/conventions.md` documents testing patterns (table-driven tests, naming conventions, helper usage, etc.). Find `*_test.go` files that contradict these patterns.

**Evidence to collect**:
- Extract testing conventions from `.know/conventions.md`
- Sample 10-15 `*_test.go` files across different packages
- For each sampled file, check each testing convention and document contradictions
- Note if patterns vary systematically by package (e.g., older packages vs newer)

**INVERTED GRADING** — A = few contradictions (testing conventions accurate); F = many contradictions:

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | < 10% of sampled test files contain contradictions | Test file list; contradiction count and percentage; specific violations described |
| B | 10-20% of sampled test files contain contradictions | Most test files follow conventions; non-conforming files identified |
| C | 21-30% of sampled test files contain contradictions | Majority conform; contradictions documented; pattern may suggest evolution not error |
| D | 31-40% of sampled test files contain contradictions | Testing conventions partially inaccurate; document may reflect aspirational not actual patterns |
| F | > 40% of sampled test files contain contradictions | Testing conventions substantially inaccurate; widespread contradictions evidenced |

---

### Criterion 4: Naming and Structure Convention Contradictions (weight: 25%)

**What to evaluate**: `.know/conventions.md` documents naming conventions (functions, variables, files, packages) and file organization patterns. Find naming or structural violations that contradict these claims.

**Evidence to collect**:
- Extract naming and structure conventions from `.know/conventions.md`
- Scan package names, exported function names, file names across 15-20 source files
- Document contradictions: specific identifier or file that violates the stated convention, with file path
- Note any systematic patterns (e.g., naming drift is concentrated in one package)

**INVERTED GRADING** — A = few contradictions (naming conventions accurate); F = many contradictions:

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | < 10% of sampled names/structures contradict documented conventions | Naming sample table; contradiction percentage; specific violations with file paths |
| B | 10-20% of sampled names/structures contradict documented conventions | Most naming follows conventions; violations identified and described |
| C | 21-30% contradict documented conventions | Contradictions concentrated; may indicate conventions evolved without documentation update |
| D | 31-40% contradict documented conventions | Naming conventions are partially inaccurate; evidence suggests stale documentation |
| F | > 40% contradict documented conventions | Naming conventions substantially inaccurate; widespread contradictions documented |

---

## Grading Calculation

Final grade is weighted average of all criteria midpoint scores (see `schemas/grading.lego.md`). Reminder: for this domain, LOWER grades indicate MORE contradictions found (less accurate documentation).

Example (well-maintained conventions document):

- Claim Extraction: A (midpoint 95%) x 20% = 19.0
- Error Handling Contradictions: A (midpoint 95%) x 30% = 28.5
- Testing Contradictions: B (midpoint 85%) x 25% = 21.25
- Naming/Structure Contradictions: A (midpoint 95%) x 25% = 23.75
- **Total: 92.5 -> A** (few contradictions found; conventions document is accurate)

Example (stale conventions document):

- Claim Extraction: B (midpoint 85%) x 20% = 17.0
- Error Handling Contradictions: D (midpoint 65%) x 30% = 19.5
- Testing Contradictions: C (midpoint 75%) x 25% = 18.75
- Naming/Structure Contradictions: D (midpoint 65%) x 25% = 16.25
- **Total: 71.5 -> C** (moderate contradictions found; conventions document has accuracy gaps)

## Related

- [Pinakes INDEX](../INDEX.lego.md) -- Full audit system documentation
- [conventions-criteria](conventions.lego.md) -- Direct adherence audit (confirmatory, not adversarial)
- [radar-convention-drift-criteria](radar-convention-drift.lego.md) -- Radar signal for convention drift
- [grading schema](../schemas/grading.lego.md) -- Grade calculation rules
