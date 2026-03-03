---
name: conventions-criteria
description: "Observation criteria for codebase conventions knowledge capture. Use when: theoros is producing conventions knowledge for .know/, documenting error handling style, file organization, domain idioms, and naming patterns. Triggers: conventions knowledge criteria, codebase conventions observation, naming patterns documentation, error handling conventions, file organization patterns."
---

# Conventions Observation Criteria

> The theoros observes and documents codebase conventions -- producing a knowledge reference that enables any CC agent to write code that looks native to the project.

## Language Detection

Before beginning observation, identify the primary language(s) in the project:
- Check for: `go.mod` (Go), `package.json` (JS/TS), `pyproject.toml`/`setup.py` (Python),
  `Cargo.toml` (Rust), `pom.xml`/`build.gradle` (Java/Kotlin)
- Adapt scope targets, evidence collection, and tooling references accordingly

### Scope Adaptation

| Criteria Element | Go | TypeScript | Python |
|---|---|---|---|
| Source directories | `cmd/`, `internal/` | `src/`, `lib/` | `src/`, `app/` |
| Error patterns | `errors.New`, `fmt.Errorf %w`, custom error types | `Error` subclasses, `Result<T, E>` | `raise`, `Exception` subclasses, `Result` patterns |
| File organization | one package per directory; file per concern | modules, barrel `index.ts` exports | modules, `__init__.py` exports |
| Entry point | `cmd/*/main.go` | `src/index.ts` | `__main__.py`, `app.py` |

## Scope

**Target files**: Primary source directories (see Scope Adaptation table), root-level config files

**Observation focus**: Error handling conventions, file organization rules, domain-specific idioms, and naming patterns that a new CC agent needs to internalize before contributing code.

**NOTE**: This domain uses knowledge-capture grading. Instead of grading compliance ratios ("90% of functions follow X convention"), grade the COMPLETENESS of the conventions reference produced. A = comprehensive documentation of conventions with evidence. F = incomplete or inaccurate documentation.

## Criteria

### Criterion 1: Error Handling Style (weight: 40%)

**What to observe**: How errors are created, wrapped, propagated, and handled throughout the codebase. The knowledge reference must tell an agent the project's error handling philosophy and patterns.

**Evidence to collect**:
- Identify the error creation pattern (custom error types, sentinel errors, `errors.New`, `fmt.Errorf`)
- Check for error wrapping conventions (`%w`, custom wrap functions, error context enrichment)
- Document error propagation style (immediate return, defer cleanup, error aggregation)
- Note error handling at boundaries (CLI output, logging, user-facing messages)
- Identify any error code systems or categorization patterns
- Check for error checking conventions (inline `if err != nil`, helper functions, must-style panics)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% completeness | Error creation, wrapping, propagation, and boundary handling all documented with specific patterns and file references. Custom error infrastructure described. An agent could handle errors consistently. |
| B | 80-89% completeness | Major error patterns documented. Wrapping and propagation covered. Minor gaps in boundary handling. |
| C | 70-79% completeness | Basic error patterns noted but wrapping or propagation conventions incomplete. |
| D | 60-69% completeness | Error handling mentioned superficially without tracing patterns through the codebase. |
| F | < 60% completeness | Error handling conventions not documented or inaccurate. |

---

> **Test conventions**: See test-coverage domain (`.know/test-coverage.md`). Test patterns are documented there to avoid duplication across `.know/` files.

### Criterion 2: File Organization (weight: 30%)

**What to observe**: How code is organized within packages: file boundaries, what goes where, separation patterns. The knowledge reference must tell an agent where to put new code.

**Evidence to collect**:
- Identify per-package file organization patterns (one type per file, grouped by concern, sorted alphabetically)
- Document the relationship between file names and their contents (e.g., `types.go` for types, `helpers.go` for utilities)
- Note where constants, variables, and init functions live
- Check for internal package usage patterns (`internal/` boundaries, what gets exported)
- Document the cmd/ vs internal/ separation philosophy (or equivalent for the detected language)
- Identify any generated code patterns or file conventions

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% completeness | File organization patterns documented across multiple packages with evidence. File naming conventions, content grouping rules, and internal/ boundaries all covered. An agent could place new files correctly. |
| B | 80-89% completeness | Major organization patterns documented. Good coverage of file naming and content grouping. Minor gaps in internal/ boundary documentation. |
| C | 70-79% completeness | General organization described but specific patterns not evidenced across packages. |
| D | 60-69% completeness | File organization mentioned vaguely without specific patterns or examples. |
| F | < 60% completeness | Organization conventions not documented or inaccurate. |

---

### Criterion 3: Domain-Specific Idioms (weight: 15%)

**What to observe**: Project-specific patterns that are NOT standard language patterns -- idioms unique to this codebase that an agent cannot infer from general language knowledge. The knowledge reference must capture project DNA that is not obvious from reading a few files.

**Evidence to collect**:
- Identify recurring project-specific patterns: envelope types, registry patterns, cascade/merge patterns, polymorphic YAML fields, or other non-standard conventions
- Document builder/option patterns (functional options, builder structs, option types)
- Note constant/enum patterns (iota usage, string constants, typed vs untyped) unique to this project
- Identify any project-specific abstractions layers not present in the language standard library
- Record domain language: terms used in the codebase with project-specific meanings (not standard language terms)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% completeness | All non-obvious project idioms documented with examples and rationale. Domain language terms cataloged. Builder/option and enum patterns documented. An agent could avoid "looks standard but isn't" mistakes. |
| B | 80-89% completeness | Major project idioms documented. Domain language partially captured. Minor gaps in pattern documentation. |
| C | 70-79% completeness | Some idioms noted but not exhaustively identified. Domain language not fully captured. |
| D | 60-69% completeness | A few idioms mentioned without systematic identification. |
| F | < 60% completeness | Domain-specific idioms not documented, or only standard language patterns described. |

---

### Criterion 4: Naming Patterns (weight: 15%)

**What to observe**: Variable naming, function naming, type naming, package naming, file naming conventions. The knowledge reference must tell an agent the naming rules that are NOT obvious from standard language conventions -- project-specific deviations and patterns.

**Evidence to collect**:
- Scan exported type names across packages for project-specific patterns (e.g., `New*` constructors, `*Options` config structs, `*Result` return types)
- Note variable naming conventions that deviate from language defaults (e.g., short receiver names, non-standard abbreviations)
- Check for acronym conventions that are project-specific (e.g., `ID` vs `Id`, `URL` vs `Url`)
- Document package naming patterns (singular vs plural, verb vs noun) where non-standard
- Flag naming anti-patterns or inconsistencies that already exist and should not be spread

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% completeness | Project-specific naming deviations and patterns documented with examples. Acronym conventions noted. Anti-patterns flagged. An agent could name new entities consistently with the codebase. |
| B | 80-89% completeness | Most naming patterns documented. Good examples for major conventions. Minor gaps. |
| C | 70-79% completeness | Key patterns documented but coverage incomplete. Limited examples. |
| D | 60-69% completeness | Some patterns listed without examples or with only 1 example each. |
| F | < 60% completeness | Naming conventions not systematically documented or descriptions are vague. |

---

## Grading Calculation

Final grade is weighted average of all criteria midpoint scores (see `schemas/grading.lego.md`). Example:
- Error Handling Style: A (midpoint 95%) x 40% = 38.0
- File Organization: B (midpoint 85%) x 30% = 25.5
- Domain-Specific Idioms: B (midpoint 85%) x 15% = 12.75
- Naming Patterns: B (midpoint 85%) x 15% = 12.75
- **Total: 89.0 -> B**

## Related

- [Pinakes INDEX](../INDEX.lego.md) -- Full audit system documentation
- [architecture-criteria](architecture.lego.md) -- Codebase architecture knowledge capture
- [test-coverage-criteria](test-coverage.lego.md) -- Test patterns and coverage conventions (owns the test domain)
