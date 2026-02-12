---
name: dromena-criteria
description: "Evaluation criteria for dromena (slash command) audits. Use when: theoros is auditing dromena domain, evaluating slash command quality. Triggers: dromena audit criteria, slash command evaluation, command quality assessment."
---

# Dromena Audit Criteria

> The theoros evaluates slash commands against these standards to ensure discoverable, well-documented user interactions.

## Scope

**Target files**: `.claude/commands/**/*.md` (projected from `rites/*/mena/**/*.dro.md`)

**Evaluation focus**: Slash commands that users invoke directly via `/command-name` syntax.

## Criteria

### Criterion 1: Frontmatter Completeness (weight: 30%)

**What to evaluate**: Presence and quality of required frontmatter fields. All dromena must have `name` and `description`. Optional but valued fields: `argument-hint`, `allowed-tools`, `model`, `context`.

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | All commands have `name` + `description`. 90%+ have at least one optional field (`argument-hint`, `allowed-tools`, `model`, or `context`) when applicable. |
| B | 80-89% | All commands have `name` + `description`. 80-89% have at least one optional field when applicable. |
| C | 70-79% | 95%+ have `name` + `description`. Some optional fields missing where they would add clarity. |
| D | 60-69% | 90-94% have required fields. Many optional fields missing. |
| F | < 60% | More than 10% of commands missing `name` or `description`. Critical metadata gaps. |

**Evidence collection**: Use Glob to find all `.claude/commands/**/*.md` files. Read each file. Check frontmatter for required and optional fields. Calculate percentage compliance.

---

### Criterion 2: Description Quality (weight: 25%)

**What to evaluate**: Dromena descriptions should be concise (1-2 sentences, under 200 characters), describe what the command DOES (not what it is), and avoid jargon without context.

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | Descriptions are action-oriented ("Creates...", "Analyzes...", "Routes..."), under 200 chars, immediately comprehensible. No unexplained jargon. |
| B | 80-89% | Most descriptions are action-oriented and concise. Minor jargon issues or slight verbosity (200-250 chars). |
| C | 70-79% | Descriptions present but often vague ("Handles...", "Manages..."). Some exceed 250 chars. Some jargon without context. |
| D | 60-69% | Descriptions exist but are frequently unclear, overly long (>300 chars), or use internal jargon without explanation. |
| F | < 60% | Descriptions missing, incomprehensible, or completely generic ("Performs command operations"). |

**Evidence collection**: Read each dromena frontmatter. Extract `description` field. Check length, verb usage, clarity. Flag jargon terms (rite, satellite, theoros, legomena, etc.) used without context in description.

---

### Criterion 3: Body Structure (weight: 25%)

**What to evaluate**: Command body should include task/behavior section and output section. Progressive disclosure: INDEX files introduce multi-file dromena and link to companion files.

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | All commands have clear task/behavior section and output specification. INDEX files provide overview + links to companion files. Bonus: examples, pre-flight checks, error handling. |
| B | 80-89% | All commands have task and output sections. INDEX files present. Minor gaps in examples or pre-flight checks. |
| C | 70-79% | Most commands have task/output sections. Some INDEX files missing or incomplete. Limited examples. |
| D | 60-69% | Task or output sections frequently missing. INDEX files present but don't effectively introduce companion structure. |
| F | < 60% | Body structure is ad-hoc. No consistent task/output pattern. INDEX files absent or misleading. |

**Evidence collection**: Read each dromena body. Identify sections: look for headings like "Task", "Behavior", "Output", "Examples". For INDEX.md files, check for companion file links and structural overview. Use Grep to find section patterns.

---

### Criterion 4: Naming Convention (weight: 20%)

**What to evaluate**: File name should match frontmatter `name` field. Category-based directory structure. Multi-file dromena should use INDEX.md pattern.

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | File names match `name` field exactly. Directory structure reflects logical categories. All multi-file dromena use INDEX.md + companions. |
| B | 80-89% | File names match `name` field in 95%+ of cases. Directory structure mostly logical. INDEX.md pattern used correctly. |
| C | 70-79% | File names match `name` field in 85-94% of cases. Some directory organization issues. INDEX.md pattern present but inconsistent. |
| D | 60-69% | Frequent name mismatches. Disorganized directory structure. INDEX.md pattern not used where needed. |
| F | < 60% | Widespread name mismatches. No clear directory structure. Multi-file dromena lack INDEX.md. |

**Evidence collection**: Use Glob to get file paths. Read frontmatter `name` from each. Compare file basename (minus `.md`) to `name` field. Check directory depth and categorization. Identify multi-file dromena (multiple files with same prefix) and verify INDEX.md exists.

---

## Grading Calculation

Final grade is weighted average of all criteria midpoint scores (see `schemas/grading.lego.md`). Example:
- Frontmatter: A (midpoint 95%) × 30% = 28.5
- Description: B (midpoint 85%) × 25% = 21.25
- Body Structure: B (midpoint 85%) × 25% = 21.25
- Naming: A (midpoint 95%) × 20% = 19.0
- **Total: 90.0 → A**

## Related

- [Pinakes INDEX](../INDEX.lego.md) — Full audit system documentation
- [legomena-criteria](legomena.lego.md) — Evaluation criteria for skills
- [agents-criteria](agents.lego.md) — Evaluation criteria for agent prompts
