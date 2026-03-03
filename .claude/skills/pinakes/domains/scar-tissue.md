---
name: scar-tissue-criteria
description: "Observation criteria for codebase scar tissue knowledge capture. Use when: theoros is producing scar tissue knowledge for .know/, documenting past bugs, regressions, and defensive code born from production failures. Triggers: scar tissue knowledge criteria, failure history observation, bug catalog documentation, regression history, production failure patterns."
---

# Scar Tissue Observation Criteria

> The theoros observes and documents codebase scar tissue -- producing a knowledge reference that catalogs past failures, their fixes, and the defensive patterns they spawned, enabling any CC agent to avoid re-introducing known failure modes.

## Language Detection

Before beginning observation, identify the primary language(s) in the project:
- Check for: `go.mod` (Go), `package.json` (JS/TS), `pyproject.toml`/`setup.py` (Python),
  `Cargo.toml` (Rust), `pom.xml`/`build.gradle` (Java/Kotlin)
- Adapt scope targets, evidence collection, and tooling references accordingly

### Scope Adaptation

| Criteria Element | Go | TypeScript | Python |
|---|---|---|---|
| Source directories | `cmd/`, `internal/` | `src/`, `lib/` | `src/`, `app/` |
| Test files | `*_test.go` | `*.test.ts`, `*.spec.ts` | `test_*.py`, `*_test.py` |
| Code markers | `CRITICAL`, `HACK`, `FIXME`, `BUG-`, `SCAR-`, `DEF-`, `WORKAROUND` | same markers apply | same markers apply |
| Git evidence | `git log --oneline` filtered for fix/bug/regression/revert/hotfix | same command | same command |

## Scope

**Target files**: Primary source directories, test files, git commit history (see Scope Adaptation table)

**Observation focus**: Past bugs, regressions, defensive code born from production failures, fix locations, and the failure mode categories they represent. Evidence from git log (fix/bug/revert commits), code comments (CRITICAL, HACK, FIXME, BUG-, SCAR-, DEF-, WORKAROUND markers), and regression test names.

**NOTE**: This domain uses knowledge-capture grading. Instead of grading compliance ratios, grade the COMPLETENESS of the knowledge reference produced. A = comprehensive documentation of scar tissue with evidence. F = incomplete or inaccurate documentation.

## Criteria

### Criterion 1: Failure Catalog Completeness (weight: 30%)

**What to observe**: Exhaustive identification of past bugs, regressions, reverts, and hotfixes from git history and code markers. The knowledge reference must give a reader a catalog of every known failure mode the codebase has encountered.

**Evidence to collect**:
- Run `git log --oneline` filtered for fix, bug, regression, revert, hotfix keywords
- Scan code comments for CRITICAL, HACK, FIXME, BUG-, SCAR-, DEF-, WORKAROUND markers
- Identify numbered SCAR-NNN entries and cross-reference across files
- Record for each scar: what failed, when (commit hash), how it was fixed, what marker identifies it today

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% completeness | Every scar found via git history and code markers documented with entry number, failure description, fix commit, and current marker. Numbered SCAR-NNN entries catalogued. No known failure modes omitted. |
| B | 80-89% completeness | Most scars documented. Git history and marker scans complete. Minor gaps in cross-referencing numbered entries to fix commits. |
| C | 70-79% completeness | Key scars documented but some found only through one evidence source (git OR markers, not both). Catalog not exhaustive. |
| D | 60-69% completeness | Some scars listed without systematic search. Catalog assembled from memory or partial scan rather than full evidence pass. |
| F | < 60% completeness | Fewer than half the observable scars documented, or catalog assembled without searching git history and code markers. |

---

### Criterion 2: Category Coverage (weight: 25%)

**What to observe**: Classification breadth across failure mode categories. The knowledge reference must show that scars have been organized into categories so agents can recognize pattern recurrence, not just isolated incidents.

**Evidence to collect**:
- Assign each scar to a failure mode category: data corruption, race condition, integration failure, config drift, security, performance cliff, schema evolution, or other
- Verify at least 3 distinct categories are represented in the catalog
- For each category, confirm at least 2 scars or explicitly note "only 1 observed" vs "not searched"
- Document any categories searched but not found (explicit absence is evidence)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% completeness | At least 5 distinct failure categories documented, each with 2+ scars or explicit "not observed" notation. Category taxonomy applied consistently. Gaps (searched but not found) distinguished from unknowns (not searched). |
| B | 80-89% completeness | At least 3 distinct categories documented with evidence. Most have 2+ scars. Minor gaps in distinguishing "not found" from "not searched." |
| C | 70-79% completeness | Categories present but inconsistently applied. Some scars uncategorized. Explicit absence notation missing. |
| D | 60-69% completeness | Categories listed without systematic mapping. Most scars not assigned to categories. |
| F | < 60% completeness | No category structure applied, or fewer than 2 categories represented. |

---

### Criterion 3: Fix-Location Mapping (weight: 20%)

**What to observe**: Precise mapping from each scar to its fix location(s) in the current codebase. The knowledge reference must let an agent find exactly where the fix lives, not just know that a fix exists.

**Evidence to collect**:
- For each scar, identify the file path(s) and function name(s) where the fix was applied
- Verify file paths still exist (flag moved or deleted fix locations as broken links)
- Note line ranges where possible; at minimum record function-level location
- Identify scars fixed in multiple locations (compound fixes) and document all locations

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% completeness | Every scar entry includes file path, function name, and line range (or current best approximation). Broken links (deleted/moved files) flagged explicitly. Compound fixes fully mapped. |
| B | 80-89% completeness | Most scars mapped to file and function. Line ranges present for majority. Minor gaps in compound fix documentation or broken link flagging. |
| C | 70-79% completeness | Scars mapped to files but not consistently to functions. Line ranges largely absent. Broken links not systematically checked. |
| D | 60-69% completeness | Fix locations mentioned vaguely ("somewhere in internal/hook") without specific file or function references. |
| F | < 60% completeness | Fix locations not documented or cannot be verified against current codebase. |

---

### Criterion 4: Defensive Pattern Documentation (weight: 15%)

**What to observe**: Documentation of the defensive code each scar spawned. The knowledge reference must connect each historical failure to the guard or validation that now prevents recurrence.

**Evidence to collect**:
- For each scar, identify the defensive pattern added as a result: sorted iterations, nil checks, validation guards, idempotency enforcement, etc.
- Record where the defensive pattern lives (file, function) and what comment marks it as scar-born
- Identify the regression test that guards against recurrence (test name, file, what assertion it makes)
- Note scars with no defensive pattern or no regression test (coverage gaps)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% completeness | Every scar links to: (1) defensive pattern with location and marker, (2) regression test name and assertion. Coverage gaps (no defensive pattern, no regression test) explicitly flagged. |
| B | 80-89% completeness | Most scars linked to defensive patterns. Regression test coverage documented for majority. Minor gaps in marker documentation or coverage gap flagging. |
| C | 70-79% completeness | Defensive patterns documented but not consistently linked to specific scars. Regression test mapping incomplete. |
| D | 60-69% completeness | Defensive patterns mentioned without tracing to originating scars or verifying test coverage. |
| F | < 60% completeness | Defensive pattern documentation absent or not connected to the scar catalog. |

---

### Criterion 5: Agent-Relevance Tagging (weight: 10%)

**What to observe**: Mapping of each scar to the agent role(s) that need to know about it. The knowledge reference must answer "which agent working in which area needs this scar in their context?"

**Evidence to collect**:
- Assign each scar to one or more agent responsibility areas (e.g., session management, hook pipeline, materialization, CLI commands, test infrastructure)
- For each assignment, document WHY the agent needs this knowledge (not just "integration-engineer" but "must sort dict iterations in query paths when building materialization logic")
- Identify scars relevant to multiple agents and document all responsibility areas
- Flag any scars with no clear agent relevance as "platform-wide" or "historical only"

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% completeness | Every scar maps to at least one agent responsibility area with an explicit "why" statement. Multi-agent scars fully tagged. Platform-wide and historical-only designations used appropriately. |
| B | 80-89% completeness | Most scars tagged to responsibility areas. Why-statements present for majority. Minor gaps in multi-agent coverage or historical-only designation. |
| C | 70-79% completeness | Responsibility area tags present but why-statements largely absent. Some scars untagged. |
| D | 60-69% completeness | Agent tagging attempted but without consistent criteria. Mostly name-only without rationale. |
| F | < 60% completeness | Agent-relevance tagging absent or applied to fewer than half of catalog entries. |

---

## Grading Calculation

Final grade is weighted average of all criteria midpoint scores (see `schemas/grading.lego.md`). Example:
- Failure Catalog Completeness: A (midpoint 95%) x 30% = 28.5
- Category Coverage: B (midpoint 85%) x 25% = 21.25
- Fix-Location Mapping: B (midpoint 85%) x 20% = 17.0
- Defensive Pattern Documentation: B (midpoint 85%) x 15% = 12.75
- Agent-Relevance Tagging: A (midpoint 95%) x 10% = 9.5
- **Total: 89.0 -> B**

## Related

- [Pinakes INDEX](../INDEX.lego.md) -- Full audit system documentation
- [architecture-criteria](architecture.lego.md) -- Codebase architecture knowledge capture
- [design-constraints-criteria](design-constraints.lego.md) -- Design constraints, load-bearing code, risk zone mapping
