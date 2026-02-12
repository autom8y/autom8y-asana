---
name: legomena-criteria
description: "Evaluation criteria for legomena (skill) audits. Use when: theoros is auditing legomena domain, evaluating skill quality and autonomous loading triggers. Triggers: legomena audit criteria, skill evaluation, knowledge base assessment."
---

# Legomena Audit Criteria

> The theoros evaluates skills against these standards to ensure Claude Code autonomously loads the right knowledge at the right time.

## Scope

**Target files**: `.claude/skills/**/*.md` (projected from `rites/*/mena/**/*.lego.md`)

**Evaluation focus**: Skills that Claude Code loads autonomously based on description triggers. Quality here determines whether skills are discovered and used.

## Criteria

### Criterion 1: Description Precision (weight: 35%)

**What to evaluate**: Frontmatter description must include "Use when:" clause and "Triggers:" keyword list. These are the ONLY mechanism for autonomous skill loading. Vague descriptions = skill never loads.

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | All skills have "Use when:" clause describing specific scenarios. All have "Triggers:" with 3+ relevant keywords/phrases. Descriptions are precise and scenario-based. |
| B | 80-89% | 95%+ have "Use when:" clause. 90%+ have "Triggers:" with 2+ keywords. Minor vagueness in scenarios. |
| C | 70-79% | 85-94% have "Use when:" clause. Some "Triggers:" lists are too short (1 keyword) or generic. |
| D | 60-69% | 70-84% have "Use when:" clause. Many missing "Triggers:" or using generic terms ("help", "info"). |
| F | < 60% | More than 30% lack "Use when:" or "Triggers:". Descriptions are generic ("Provides information about..."). Skills are undiscoverable. |

**Evidence collection**: Read each skill frontmatter. Extract `description` field. Search for "Use when:" and "Triggers:" strings. Count keywords in "Triggers:" list. Evaluate scenario specificity in "Use when:" clause. Flag generic patterns.

---

### Criterion 2: Frontmatter Completeness (weight: 20%)

**What to evaluate**: Required fields are `name` and `description`. File name must follow convention: `{name}.lego.md` or `{category}/{name}.lego.md`.

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | All skills have `name` + `description`. File names match `{name}.lego.md` pattern or use category subdirectories correctly. |
| B | 80-89% | 95%+ have required fields. File naming is mostly consistent with minor deviations. |
| C | 70-79% | 90-94% have required fields. Some file naming inconsistencies (missing `.lego.md` suffix). |
| D | 60-69% | 85-89% have required fields. Frequent file naming issues. |
| F | < 60% | More than 15% missing `name` or `description`. File naming is chaotic or doesn't use `.lego.md` convention. |

**Evidence collection**: Use Glob to find all `.claude/skills/**/*.md` files. Read frontmatter. Check for `name` and `description`. Verify file path matches `{name}.lego.md` or `{category}/{name}.lego.md`. Calculate compliance percentage.

---

### Criterion 3: Progressive Disclosure (weight: 25%)

**What to evaluate**: INDEX files should provide quick reference and link to companion files for depth. Companion files should be focused on one topic. No monolithic skills (>500 lines).

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | Multi-topic skills use INDEX + companions. INDEX files are concise (<200 lines), provide overview tables, link to all companions. Companion files are focused (<400 lines each). No monoliths. |
| B | 80-89% | INDEX pattern used for most multi-topic skills. INDEX files sometimes exceed 200 lines. Companion files mostly focused but some exceed 400 lines. |
| C | 70-79% | INDEX pattern present but inconsistent. Some INDEX files are too detailed (>300 lines). Some companion files are unfocused (>500 lines). |
| D | 60-69% | INDEX pattern rarely used. Many monolithic skills (>500 lines). Companion files not clearly scoped. |
| F | < 60% | No INDEX pattern. Monolithic skills dominate (>800 lines). No progressive disclosure strategy. |

**Evidence collection**: Use Glob to identify INDEX.md files in `.claude/skills/`. Read each INDEX to check length and verify companion links. For multi-file skill sets, check that companions are linked from INDEX. Count lines in each skill file. Flag files >500 lines. Verify companion files have focused topics.

---

### Criterion 4: Consumer Documentation (weight: 20%)

**What to evaluate**: Skills should identify which agents/dromena consume them. "When to Use" tables map scenarios to specific files for multi-file skill sets.

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | All skills document consumers (agents or dromena that load them). INDEX files have "When to Use" tables mapping scenarios to companion files. Clear usage guidance. |
| B | 80-89% | 90%+ document consumers. Most INDEX files have "When to Use" tables. Minor gaps in usage guidance. |
| C | 70-79% | 80-89% document consumers. Some INDEX files lack "When to Use" tables. Usage guidance is vague. |
| D | 60-69% | 70-79% document consumers. Many INDEX files lack usage guidance. Unclear which agents use which skills. |
| F | < 60% | Consumer documentation is rare or absent. No "When to Use" tables. Skills exist in isolation without clear consumption patterns. |

**Evidence collection**: Read each skill body. Search for sections like "Consumers", "Used by", "When to Use". In INDEX files, verify presence of scenario-to-file mapping tables. Cross-reference agent prompts (`.claude/agents/*.md`) to verify documented consumer relationships. Use Grep to find agent references to specific skills.

---

## Grading Calculation

Final grade is weighted average of all criteria midpoint scores (see `schemas/grading.lego.md`). Example:
- Description Precision: A (midpoint 95%) × 35% = 33.25
- Frontmatter Completeness: A (midpoint 95%) × 20% = 19.0
- Progressive Disclosure: B (midpoint 85%) × 25% = 21.25
- Consumer Documentation: C (midpoint 75%) × 20% = 15.0
- **Total: 88.5 → B**

## Related

- [Pinakes INDEX](../INDEX.lego.md) — Full audit system documentation
- [dromena-criteria](dromena.lego.md) — Evaluation criteria for slash commands
- [agents-criteria](agents.lego.md) — Evaluation criteria for agent prompts
