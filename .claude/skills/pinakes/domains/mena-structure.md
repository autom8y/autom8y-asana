---
name: mena-structure-criteria
description: "Evaluation criteria for mena directory structure audits. Use when: theoros is auditing mena-structure domain, evaluating directory conventions and organization. Triggers: mena-structure audit criteria, directory convention evaluation, mena organization assessment."
---

# Mena Structure Audit Criteria

> The theoros evaluates mena directory organization against these standards to ensure consistent naming, proper INDEX usage, manifest registration, and clean dro/lego separation.

## Scope

**Target files**: `rites/*/mena/**/*` (source mena directories) and `rites/*/manifest.yaml` (registration)

**Evaluation focus**: Directory organization, file naming conventions (.dro.md vs .lego.md), INDEX file patterns, manifest registration, and progressive disclosure structure.

## Criteria

### Criterion 1: File Naming Convention (weight: 30%)

**What to evaluate**: All mena files must use the correct extension: `.dro.md` for dromena (commands) or `.lego.md` for legomena (skills). No bare `.md` files in mena directories (except companion files in subdirectories). Mixed dro/lego files in the same directory are a critical anti-pattern.

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | All top-level mena files use `.dro.md` or `.lego.md` extensions. No mixed dro/lego directories. Companion files in subdirectories use plain `.md`. Zero naming violations. |
| B | 80-89% | 95%+ of mena files use correct extensions. No mixed directories. 1-2 files with bare `.md` at top level. |
| C | 70-79% | 85-94% use correct extensions. 1 mixed dro/lego directory. Some bare `.md` files at top level. |
| D | 60-69% | 75-84% use correct extensions. 2+ mixed directories. Extension conventions inconsistent. |
| F | < 60% | Widespread naming violations. Mixed dro/lego directories are common. Extension convention not followed. |

**Evidence collection**: Use Glob to find all files in `rites/*/mena/`. Classify by extension (.dro.md, .lego.md, .md, other). For each directory, check if it contains both .dro.md and .lego.md files (mixed = anti-pattern). Count violations. List directories with mixed content.

---

### Criterion 2: INDEX File Structure (weight: 25%)

**What to evaluate**: Multi-file mena entries (directories) must have an INDEX file (INDEX.lego.md or INDEX.dro.md) as the entry point. INDEX files should provide overview, link to companion files, and enable progressive disclosure. Single-file mena entries don't need INDEX.

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | All multi-file mena directories have an INDEX file. INDEX files link to all companion files. Progressive disclosure is clear (overview -> detail). |
| B | 80-89% | 95%+ multi-file directories have INDEX files. Most INDEX files link to companions. Minor gaps in progressive disclosure. |
| C | 70-79% | 85-94% multi-file directories have INDEX files. Some INDEX files missing companion links. |
| D | 60-69% | 75-84% multi-file directories have INDEX files. INDEX files often incomplete or missing links. |
| F | < 60% | Many multi-file directories lack INDEX files. No clear entry point pattern. |

**Evidence collection**: Use Glob to find all mena directories (not files). For each directory, check for INDEX.lego.md or INDEX.dro.md. Read INDEX files and verify they contain links to companion files in the same directory. Count directories missing INDEX files.

---

### Criterion 3: Manifest Registration (weight: 25%)

**What to evaluate**: All mena entries (both dromena and legomena) should be registered in their rite's manifest.yaml under `dromena:` or `legomena:` lists. Unregistered mena entries are orphaned and won't materialize.

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | All mena directory entries appear in their rite's manifest. No orphaned entries. No ghost entries (manifest references without corresponding files). |
| B | 80-89% | 95%+ mena entries are registered. 1-2 orphaned entries. No ghost entries. |
| C | 70-79% | 85-94% registered. 3-5 orphaned entries. 1-2 ghost entries in manifests. |
| D | 60-69% | 75-84% registered. Multiple orphaned entries. Ghost entries present. |
| F | < 60% | Widespread registration gaps. Many orphaned mena entries. Manifest lists inaccurate. |

**Evidence collection**: For each rite, read manifest.yaml `dromena:` and `legomena:` lists. Glob for actual mena directories and top-level files. Cross-reference: flag entries in mena/ not in manifest (orphaned) and entries in manifest not in mena/ (ghosts). Count both directions.

---

### Criterion 4: Frontmatter Quality (weight: 20%)

**What to evaluate**: All mena files (INDEX and top-level) must have YAML frontmatter with `name` and `description`. Legomena descriptions must include "Use when:" and "Triggers:" for CC autonomous skill loading. Dromena descriptions should describe what the command does.

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | All mena files have frontmatter with name + description. All legomena have "Use when:" and "Triggers:". Dromena have action-oriented descriptions. |
| B | 80-89% | 95%+ have required frontmatter. Most legomena have trigger patterns. Minor description quality issues. |
| C | 70-79% | 85-94% have required frontmatter. Some legomena missing "Use when:" or "Triggers:". Descriptions sometimes vague. |
| D | 60-69% | 75-84% have required frontmatter. Many legomena lack trigger patterns. Descriptions frequently unclear. |
| F | < 60% | Widespread frontmatter gaps. Descriptions missing or generic. Trigger patterns absent. |

**Evidence collection**: Read frontmatter from all INDEX and top-level mena files. Check for `name` and `description` fields. For .lego.md files, grep description for "Use when:" and "Triggers:". Count compliance rates separately for dromena and legomena.

---

## Grading Calculation

Final grade is weighted average of all criteria midpoint scores (see `schemas/grading.lego.md`). Example:
- File Naming: A (midpoint 95%) x 30% = 28.5
- INDEX Structure: B (midpoint 85%) x 25% = 21.25
- Manifest Registration: B (midpoint 85%) x 25% = 21.25
- Frontmatter Quality: A (midpoint 95%) x 20% = 19.0
- **Total: 90.0 -> A**

## Related

- [Pinakes INDEX](../INDEX.lego.md) - Full audit system documentation
- [dromena-criteria](dromena.lego.md) - Evaluation criteria for slash commands
- [legomena-criteria](legomena.lego.md) - Evaluation criteria for skills
