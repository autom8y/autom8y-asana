---
name: design-constraints-criteria
description: "Observation criteria for codebase design constraint knowledge capture. Use when: theoros is producing design constraint knowledge for .know/, documenting structural tensions, load-bearing decisions, and abstraction boundaries. Triggers: design constraint knowledge criteria, tension catalog observation, trade-off documentation, load-bearing code identification, abstraction boundary mapping."
---

# Design Constraints Observation Criteria

> The theoros observes and documents codebase design constraints -- producing a knowledge reference that catalogs structural tensions, load-bearing jank, and abstraction boundaries, enabling any CC agent to work WITH constraints rather than reflexively removing them.

## Language Detection

Before beginning observation, identify the primary language(s) in the project:
- Check for: `go.mod` (Go), `package.json` (JS/TS), `pyproject.toml`/`setup.py` (Python),
  `Cargo.toml` (Rust), `pom.xml`/`build.gradle` (Java/Kotlin)
- Adapt scope targets, evidence collection, and tooling references accordingly

### Scope Adaptation

| Criteria Element | Go | TypeScript | Python |
|---|---|---|---|
| Source directories | `cmd/`, `internal/` | `src/`, `lib/` | `src/`, `app/` |
| Dependency manifest | `go.mod` | `package.json` | `pyproject.toml` |
| Import graph tool | `go list -json ./...` | `ts-prune`, `dependency-cruiser` | `pydeps`, `importlab` |
| Deprecated markers | `// Deprecated:` godoc convention | `@deprecated` JSDoc | `warnings.warn(DeprecationWarning)` |
| Layering violations | import direction in `go.mod` graph | circular imports in bundler | circular imports via `importlab` |

## Scope

**Target files**: Primary source directories, import graph, backward-compatibility markers (see Scope Adaptation table)

**Observation focus**: Structural conflicts, naming mismatches, layering violations, under/over-engineering, missing/premature abstractions, and load-bearing jank that agents must navigate rather than "fix." Evidence from type hierarchies, import graphs, naming audits, deprecated markers, and dual-system patterns.

**NOTE**: This domain uses knowledge-capture grading. Instead of grading compliance ratios, grade the COMPLETENESS of the knowledge reference produced. A = comprehensive documentation of constraints with evidence. F = incomplete or inaccurate documentation.

## Criteria

### Criterion 1: Tension Catalog Completeness (weight: 27%)

**What to observe**: Exhaustive identification of structural tensions in the codebase -- naming mismatches, layering violations, under/over-engineering, and missing/premature abstractions. The knowledge reference must catalog every tension a CC agent might stumble into.

**Evidence to collect**:
- Scan for naming mismatches between packages, types, and their actual responsibilities
- Identify layering violations (import direction reversals, cross-layer dependencies that shouldn't exist)
- Note under-engineering (duplicated logic that should be extracted) and over-engineering (abstractions serving only one use case)
- Look for dual-system patterns (two subsystems doing overlapping work with neither fully replacing the other)
- Assign sequential TENSION-NNN identifiers with type classification, location, historical reason, ideal resolution, and resolution cost

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% completeness | Every structural tension documented with TENSION-NNN entry: type, location (file:line), historical reason, ideal resolution, resolution cost. Minimum 8 tensions for mature codebase. No tensions omitted; gaps explicitly noted as "not observed." |
| B | 80-89% completeness | Most tensions cataloged with TENSION-NNN entries. Historical reasons and resolution costs present for major entries. Minor gaps in low-impact tension documentation. |
| C | 70-79% completeness | Key tensions listed but some without TENSION-NNN format. Historical reasons partially documented. Resolution costs missing for several entries. |
| D | 60-69% completeness | Some tensions identified but described superficially. No structured entries. Resolution costs not assessed. |
| F | < 60% completeness | Fewer than half the structural tensions documented, or descriptions are vague and unactionable. |

---

### Criterion 2: Trade-off Documentation (weight: 22%)

**What to observe**: Explicit documentation of design trade-offs -- what was chosen, what was rejected, and why each tension persists. The knowledge reference must explain why the current state is what it is, not just that a tension exists.

**Evidence to collect**:
- For each tension, document the trade-off: current state, ideal state, why current state persists
- Link to ADRs where they exist (check `.ledge/decisions/` for relevant decision records)
- Identify tensions that have been attempted before and failed (survived prior refactoring attempts)
- Note external constraints (API compatibility, performance requirements, deployment constraints) that force trade-offs

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% completeness | Every tension has explicit trade-off documentation: current state, ideal state, why current persists. ADR links included where ADRs exist. Prior refactoring attempts noted. External constraints identified. |
| B | 80-89% completeness | Most tensions have trade-off documentation. ADR links present for major decisions. Minor gaps in prior-attempt or external-constraint documentation. |
| C | 70-79% completeness | Trade-offs documented for major tensions. Minor tensions lack rationale. ADR links missing for some relevant decisions. |
| D | 60-69% completeness | Trade-offs mentioned superficially ("it's complicated") without specific current/ideal/why documentation. |
| F | < 60% completeness | Trade-off rationale absent or inaccurate. Current state described without explaining why it persists. |

---

### Criterion 3: Abstraction Gap Mapping (weight: 18%)

**What to observe**: Missing abstractions (duplicated logic that should be unified) and premature abstractions (generalizations that serve only one use case). The knowledge reference must map where abstraction failures create maintenance burden or hidden coupling.

**Evidence to collect**:
- Find duplicated logic across N locations that should be extracted into a shared abstraction -- document each cluster with file references and recommended abstraction name
- Identify abstractions serving only one use case (over-generalized for current needs)
- Note abstractions that were designed for a use case that no longer exists (zombie abstractions)
- Document the maintenance burden: what breaks when the duplication diverges, or what dead code the premature abstraction carries

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% completeness | Missing abstractions: each cluster documented with file references, duplication count, and recommended abstraction. Premature abstractions: each documented with use-case count and zombie evidence. Maintenance burden quantified for significant gaps. |
| B | 80-89% completeness | Major abstraction gaps documented with file references. Most premature abstractions identified. Minor gaps in maintenance burden assessment. |
| C | 70-79% completeness | Key abstraction gaps mentioned but not exhaustively cataloged. File references partially provided. Premature abstractions partially identified. |
| D | 60-69% completeness | Abstraction gaps described vaguely ("some duplication exists") without specific locations or counts. |
| F | < 60% completeness | Abstraction gaps not documented or misidentified. |

---

### Criterion 4: Load-Bearing Code Identification (weight: 13%)

**What to observe**: Code that MUST NOT be refactored without coordinated multi-file effort -- load-bearing jank with multiple dependents, partial fixes that would be worse than the status quo, and code that has survived prior refactoring attempts because the cost is too high.

**Evidence to collect**:
- Identify code meeting load-bearing criteria: multiple callers, fixing requires cross-file changes, partial fix is worse than status quo, survived prior refactoring attempts
- For each load-bearing item: document what it does, what depends on it, what a naive "fix" would break, and what a safe refactor would require
- Flag any load-bearing code that is also in a hot path (performance-sensitive) or security boundary
- Note whether load-bearing status is documented in comments or only implicit

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% completeness | Every load-bearing code location documented: what it does, dependents listed, naive-fix failure mode described, safe-refactor requirements specified. Hot path and security boundary flags included. |
| B | 80-89% completeness | Major load-bearing locations documented with dependents. Naive-fix failure modes present. Minor gaps in safe-refactor requirement documentation. |
| C | 70-79% completeness | Load-bearing code identified but dependents not fully cataloged. Failure modes described for some but not all entries. |
| D | 60-69% completeness | Load-bearing code mentioned without specific dependent documentation. "Don't touch this" without explaining why. |
| F | < 60% completeness | Load-bearing code not identified, or identified load-bearing code turns out to be safely refactorable. |

---

### Criterion 5: Evolution Constraint Documentation (weight: 10%)

**What to observe**: Constraints on future evolution -- what areas of the codebase can be changed safely, what requires coordinated migration, and what is effectively frozen. The knowledge reference must give agents a per-area changeability rating before they start editing.

**Evidence to collect**:
- Assign changeability ratings per codebase area: safe (local change only), coordinated (multi-file, no external break), migration (breaking change to callers or format), frozen (do not touch without explicit decision)
- Document the evidence for each rating (why is this area frozen? what contract does it expose? what would a caller-breaking change require?)
- Note any deprecated markers, compatibility shims, or migration helpers that signal evolution in progress
- Identify evolution constraints from external dependencies (API consumers, serialization formats, database schemas)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% completeness | Changeability ratings assigned to all significant codebase areas with evidence. Deprecated markers and in-progress migrations documented. External dependency constraints identified. An agent could determine safe change scope before editing any area. |
| B | 80-89% completeness | Most areas rated. Major frozen areas documented with evidence. Minor gaps in deprecated marker or external constraint documentation. |
| C | 70-79% completeness | Key areas rated but coverage incomplete. Some frozen areas identified without full evidence. External constraints partially documented. |
| D | 60-69% completeness | Changeability mentioned for a few areas only. Ratings without supporting evidence. External constraints not assessed. |
| F | < 60% completeness | Evolution constraints not documented or ratings are inaccurate. |

---

### Criterion 6: Risk Zone Mapping (weight: 10%)

**What to observe**: Identification of unguarded areas where defenses are missing but should exist. The knowledge reference must document where the safety net has holes so agents do not introduce new failures in these areas.

**Evidence to collect**:
- Identify code paths where validation is absent but caller-responsibility is assumed (look for comments like "caller must ensure", "assumes valid", "precondition:")
- Scan for silent fallbacks that swallow errors or use zero-values without logging
- Note input paths from external sources (CLI flags, config files, stdin, environment variables) that lack validation
- Record RISK-NNN entries: location, type of missing guard, evidence of missing protection, and recommended guard
- Cross-reference each RISK-NNN entry to any TENSION-NNN entries it relates to (a risk zone often corresponds to a known tension)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% completeness | All significant risk zones documented with RISK-NNN entries. Each entry includes location, missing guard type, evidence, and recommended guard. Cross-references to related TENSION-NNN entries provided. Silent fallbacks cataloged. |
| B | 80-89% completeness | Major risk zones identified. Most entries have location and missing guard type. Cross-references present for major risk zones. Minor gaps in silent fallback cataloging. |
| C | 70-79% completeness | Some risk zones noted but coverage is incomplete. Entries lack recommended guards. Cross-references to tensions not documented. |
| D | 60-69% completeness | Risk zones mentioned vaguely without specific locations or evidence. No RISK-NNN entries. |
| F | < 60% completeness | Risk zones not documented or only trivially identified. |

---

## Grading Calculation

Final grade is weighted average of all criteria midpoint scores (see `schemas/grading.lego.md`). Example:
- Tension Catalog: A (midpoint 95%) x 27% = 25.65
- Trade-off Docs: B (midpoint 85%) x 22% = 18.7
- Abstraction Gaps: A (midpoint 95%) x 18% = 17.1
- Load-Bearing Code: B (midpoint 85%) x 13% = 11.05
- Evolution Constraints: B (midpoint 85%) x 10% = 8.5
- Risk Zone Mapping: B (midpoint 85%) x 10% = 8.5
- **Total: 89.5 -> B**

## Related

- [Pinakes INDEX](../INDEX.lego.md) -- Full audit system documentation
- [architecture-criteria](architecture.lego.md) -- Codebase architecture knowledge capture
- [scar-tissue-criteria](scar-tissue.lego.md) -- Scar tissue knowledge capture (failure history, regressions)
