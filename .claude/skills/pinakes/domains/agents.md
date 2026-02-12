---
name: agents-criteria
description: "Evaluation criteria for agent prompt audits. Use when: theoros is auditing agents domain, evaluating agent prompt quality and behavioral clarity. Triggers: agents audit criteria, agent evaluation, prompt quality assessment."
---

# Agents Audit Criteria

> The theoros evaluates agent prompts against these standards to ensure clear roles, behavioral constraints, and reliable handoffs.

## Scope

**Target files**: `.claude/agents/*.md` (projected from `rites/*/agents/*.md`)

**Evaluation focus**: Agent prompts that define subagent behavior when invoked via Task tool. Quality here determines agent autonomy, reliability, and ecosystem coordination.

## Criteria

### Criterion 1: Role Clarity (weight: 25%)

**What to evaluate**: Core Purpose section clearly defines what this agent does and when invoked. Frontmatter one-line description is precise and actionable.

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | All agents have "Core Purpose" section defining role, invocation conditions, and scope. Frontmatter descriptions are one sentence, under 120 chars, action-oriented. No ambiguity. |
| B | 80-89% | 95%+ have "Core Purpose" section. Descriptions are mostly concise (under 150 chars). Minor ambiguity in scope. |
| C | 70-79% | 85-94% have "Core Purpose" section. Some descriptions are verbose (>150 chars) or vague ("handles tasks"). |
| D | 60-69% | 75-84% have "Core Purpose" section. Descriptions often lack clarity or exceed 200 chars. |
| F | < 60% | More than 25% lack "Core Purpose" section. Descriptions are generic, overly long, or missing. |

**Evidence collection**: Read each agent prompt. Verify presence of "Core Purpose" section (or "Purpose", "Role"). Extract frontmatter `description`. Check length and clarity. Flag vague verbs ("manages", "handles", "works with"). Count agents with clear invocation conditions.

---

### Criterion 2: Behavioral Constraints (weight: 25%)

**What to evaluate**: "You Decide / You Escalate / You Route To" authority sections define decision boundaries. Anti-patterns section provides WRONG/RIGHT examples to prevent common mistakes.

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | All agents have authority sections ("You Decide", "You Escalate", "You Route To" or equivalent). Anti-patterns section with concrete examples (WRONG/RIGHT or similar). Clear boundaries. |
| B | 80-89% | 95%+ have authority sections. 85%+ have anti-patterns section. Some examples could be more concrete. |
| C | 70-79% | 85-94% have authority sections. 70-84% have anti-patterns section. Examples are present but vague. |
| D | 60-69% | 75-84% have authority sections. Anti-patterns section often missing or generic. Boundaries unclear. |
| F | < 60% | More than 25% lack authority sections. Anti-patterns section rare or absent. Agents have no clear behavioral constraints. |

**Evidence collection**: Read each agent prompt. Search for sections: "You Decide", "You Escalate", "You Do NOT Decide", "You Route To", "Domain Authority", "Anti-Patterns". Verify anti-patterns have examples (grep for "WRONG", "RIGHT", "DON'T", "INSTEAD"). Count agents with all authority sections.

---

### Criterion 3: Frontmatter Schema (weight: 20%)

**What to evaluate**: Required fields are `name`, `description`, `type`, `tools`, `model`. Optional fields: `color`, `maxTurns`, `disallowedTools`. Description must include "Use when:" and "Triggers:".

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | All agents have required fields. Descriptions include "Use when:" and "Triggers:". `tools` list is complete. `model` is specified. Optional fields used appropriately. |
| B | 80-89% | 95%+ have all required fields. 90%+ have "Use when:" and "Triggers:". Some `tools` lists incomplete. |
| C | 70-79% | 90-94% have required fields. Some missing "Use when:" or "Triggers:". `tools` lists often incomplete. |
| D | 60-69% | 85-89% have required fields. Many missing "Use when:" or "Triggers:". `tools` lists frequently wrong or empty. |
| F | < 60% | More than 15% missing required fields. Descriptions lack "Use when:" and "Triggers:". Frontmatter schema is inconsistent. |

**Evidence collection**: Read each agent frontmatter. Check for `name`, `description`, `type`, `tools`, `model`. Verify `description` contains "Use when:" and "Triggers:". Validate `tools` is array of valid tool names. Check `model` is specified. Count compliance for required vs. optional fields.

---

### Criterion 4: Output Specification (weight: 15%)

**What to evaluate**: Clear output schema or format definition so consuming agents know what to expect. File paths, artifact types, or data structures should be documented.

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | All agents have "Output" or "Deliverables" section specifying format, file paths, artifact types. Schema examples provided for structured data. |
| B | 80-89% | 90%+ have output specification. Formats are clear but some lack schema examples. |
| C | 70-79% | 80-89% have output specification. Many are vague ("produces analysis") without format details. |
| D | 60-69% | 70-79% have output specification. Frequently unclear what artifacts are produced or where they're written. |
| F | < 60% | More than 30% lack output specification. Consuming agents cannot predict output format. |

**Evidence collection**: Read each agent prompt. Search for sections: "Output", "Deliverables", "Produces", "Handoff Criteria". Verify concrete format specifications (file paths, JSON schemas, markdown structure). Flag vague outputs. Count agents with clear schema definitions.

---

### Criterion 5: Handoff Criteria (weight: 15%)

**What to evaluate**: When to escalate vs. when to complete. Dependencies on other agents are documented. Completion criteria are checkboxes or explicit conditions.

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | All agents have "Handoff Criteria" or "Completion Criteria" section with checkboxes or explicit conditions. Dependencies documented in "You Route To" section. Escalation triggers clear. |
| B | 80-89% | 90%+ have handoff criteria. 85%+ document dependencies. Some escalation triggers vague. |
| C | 70-79% | 80-89% have handoff criteria. Dependencies present but not comprehensive. Escalation conditions unclear. |
| D | 60-69% | 70-79% have handoff criteria. Dependencies poorly documented. Escalation vs. completion boundary fuzzy. |
| F | < 60% | More than 30% lack handoff criteria. No clear completion conditions. Dependencies undocumented. |

**Evidence collection**: Read each agent prompt. Search for sections: "Handoff Criteria", "Completion Criteria", "When to Escalate". Verify presence of checklists (grep for `[ ]` or bullet points with concrete tasks). Check "You Route To" section for dependency documentation. Count agents with clear handoff conditions.

---

## Grading Calculation

Final grade is weighted average of all criteria midpoint scores (see `schemas/grading.lego.md`). Example:
- Role Clarity: A (midpoint 95%) × 25% = 23.75
- Behavioral Constraints: B (midpoint 85%) × 25% = 21.25
- Frontmatter Schema: A (midpoint 95%) × 20% = 19.0
- Output Specification: B (midpoint 85%) × 15% = 12.75
- Handoff Criteria: B (midpoint 85%) × 15% = 12.75
- **Total: 89.5 → B**

## Related

- [Pinakes INDEX](../INDEX.lego.md) — Full audit system documentation
- [dromena-criteria](dromena.lego.md) — Evaluation criteria for slash commands
- [legomena-criteria](legomena.lego.md) — Evaluation criteria for skills
