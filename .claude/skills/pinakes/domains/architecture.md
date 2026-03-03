---
name: architecture-criteria
description: "Observation criteria for codebase architecture knowledge capture. Use when: theoros is producing architecture knowledge for .know/, documenting package structure and layer relationships. Triggers: architecture knowledge criteria, codebase structure observation, package documentation."
---

# Architecture Observation Criteria

> The theoros observes and documents codebase architecture -- producing a knowledge reference that enables any CC agent to navigate the source code with zero prior context.

## Language Detection

Before beginning observation, identify the primary language(s) in the project:
- Check for: `go.mod` (Go), `package.json` (JS/TS), `pyproject.toml`/`setup.py` (Python),
  `Cargo.toml` (Rust), `pom.xml`/`build.gradle` (Java/Kotlin)
- Adapt scope targets, evidence collection, and tooling references accordingly

### Scope Adaptation

| Criteria Element | Go | TypeScript | Python |
|---|---|---|---|
| Source directories | `cmd/`, `internal/` | `src/`, `lib/` | `src/`, `app/` |
| Package/module unit | package (directory) | module (file or directory) | module (file) or package (directory) |
| Dependency manifest | `go.mod` | `package.json` | `pyproject.toml` |
| Entry point | `cmd/*/main.go` | `src/index.ts` | `__main__.py`, `app.py` |
| Layer model | `cmd/` → `internal/cmd/` → `internal/*` | `app/` → `lib/` → `utils/` | `app/` → `core/` → `utils/` |

## Scope

**Target files**: Primary source directories (see Scope Adaptation table), root-level config files

**Observation focus**: Source code structure, package/module organization, layer boundaries, and data flow paths that a new CC agent needs to understand before making changes.

**NOTE**: This domain uses knowledge-capture grading. Instead of grading compliance ratios ("90% of packages have X"), grade the COMPLETENESS of the knowledge reference produced. A = comprehensive documentation of the codebase with evidence. F = incomplete or inaccurate documentation.

## Criteria

### Criterion 1: Package Structure (weight: 30%)

**What to observe**: Directory layout, module organization, package count, and what each package does. The knowledge reference must give a reader a mental map of the codebase.

**Evidence to collect**:
- List all directories under `cmd/` and `internal/`
- Read each package's primary file (usually the file matching the package name, or the largest .go file)
- Record: package name, one-line purpose, exported types count, file count
- Note any packages that import many siblings (hub packages) vs. packages imported by many (leaf packages)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% completeness | Every package under `cmd/` and `internal/` documented with purpose, key types, and relationship notes. Hub/leaf classification included. No packages omitted. |
| B | 80-89% completeness | All packages listed with purpose. Most have key types documented. Minor gaps in relationship notes. |
| C | 70-79% completeness | Key packages documented but some omitted or described only by name. Relationships partially mapped. |
| D | 60-69% completeness | Major packages listed but descriptions are superficial ("does stuff"). Relationships not mapped. |
| F | < 60% completeness | Fewer than half the packages documented, or descriptions are inaccurate. |

---

### Criterion 2: Layer Boundaries (weight: 25%)

**What to observe**: What calls what, separation of concerns, import direction. The knowledge reference must document which packages form the "core" vs "infrastructure" vs "CLI surface" and how they relate.

**Evidence to collect**:
- For each package, scan import statements to identify internal dependencies
- Identify the import graph shape: which packages are leaf (no internal imports), which are hub (import many siblings)
- Note any circular dependency avoidance patterns (interface packages, shared types)
- Document the layer model: cmd/ (CLI) -> internal/cmd/ (command wiring) -> internal/* (domain logic)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% completeness | Import graph direction documented. Layer model (CLI -> wiring -> domain) explicitly stated with evidence. Hub and leaf packages identified. Boundary-enforcement patterns noted (if any). |
| B | 80-89% completeness | Layer model documented with most import relationships. Hub/leaf classification present. Minor gaps in boundary pattern documentation. |
| C | 70-79% completeness | General layer structure described but specific import relationships not traced. Hub/leaf not classified. |
| D | 60-69% completeness | Layers mentioned vaguely ("cmd calls internal") without specific evidence or relationship detail. |
| F | < 60% completeness | No meaningful layer documentation. Import relationships not analyzed. |

---

### Criterion 3: Entry Points and API Surface (weight: 20%)

**What to observe**: CLI commands (cobra commands), exported interfaces that other packages depend on, initialization paths (main -> root command -> subcommands). The knowledge reference must tell an agent "here is how a user interacts with this codebase."

**Evidence to collect**:
- Read `cmd/ari/main.go` for entry point
- Trace the cobra command tree: root command -> subcommands -> their handlers
- List all user-facing subcommands with one-line descriptions
- Identify key exported interfaces that define contracts between packages

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% completeness | All CLI subcommands listed with descriptions. Entry point traced from main() through command wiring. Key exported interfaces documented with consuming packages. Initialization path clear. |
| B | 80-89% completeness | CLI subcommands listed. Entry point documented. Most exported interfaces noted. Minor gaps in consumer documentation. |
| C | 70-79% completeness | Main subcommands listed but not exhaustive. Entry point mentioned but not traced. Interfaces partially documented. |
| D | 60-69% completeness | Some CLI commands listed. Entry point not traced. Interfaces not documented. |
| F | < 60% completeness | CLI surface not documented or inaccurate. |

---

### Criterion 4: Key Abstractions (weight: 15%)

**What to observe**: Core types, interfaces, and design patterns that define the mental model for working in this codebase. The knowledge reference must tell an agent "these are the concepts you need to understand."

**Evidence to collect**:
- Identify the 5-10 most important types (by usage frequency or centrality): structs, interfaces, type aliases
- For each, record: name, package, purpose, and how other packages use it
- Note design patterns in use: polymorphic YAML fields, envelope patterns, registry patterns, cascade/merge patterns
- Document any custom conventions: naming, error handling, file organization

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% completeness | Core types identified with package, purpose, and usage context. Design patterns named and evidenced. Conventions documented. A new agent could start working with this reference alone. |
| B | 80-89% completeness | Most core types documented. Major design patterns noted. Minor gaps in convention documentation. |
| C | 70-79% completeness | Some core types listed but without usage context. Patterns mentioned but not evidenced. |
| D | 60-69% completeness | Types listed by name only. No pattern documentation. |
| F | < 60% completeness | Core types not identified or mischaracterized. |

---

### Criterion 5: Data Flow (weight: 10%)

**What to observe**: How configuration and data move through the system. Input (config files, CLI flags, environment variables) -> processing (parsing, merging, transforming) -> output (file writes, CLI output, side effects). The knowledge reference must document the primary data paths.

**Evidence to collect**:
- Trace the sync pipeline: knossos source files -> materialization -> .claude/ output
- Trace the session pipeline: session events -> event file -> event readers
- Trace the hook pipeline: CC lifecycle event -> stdin JSON -> ari hook handler -> side effects
- Note configuration merge points (manifest + rite + agent frontmatter cascades)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% completeness | Primary data pipelines (sync, session, hook) documented with source -> transform -> destination. Merge points identified. An agent could trace any config value from source to effect. |
| B | 80-89% completeness | Major pipelines documented. Most merge points noted. Minor gaps in trace completeness. |
| C | 70-79% completeness | Pipelines mentioned but not fully traced. Some merge points missing. |
| D | 60-69% completeness | Data flow described vaguely ("config goes through sync"). No specific trace. |
| F | < 60% completeness | Data flow not documented or inaccurate. |

---

## Grading Calculation

Final grade is weighted average of all criteria midpoint scores (see `schemas/grading.lego.md`). Example:
- Package Structure: A (midpoint 95%) x 30% = 28.5
- Layer Boundaries: B (midpoint 85%) x 25% = 21.25
- Entry Points: A (midpoint 95%) x 20% = 19.0
- Key Abstractions: B (midpoint 85%) x 15% = 12.75
- Data Flow: B (midpoint 85%) x 10% = 8.5
- **Total: 90.0 -> A**

## Related

- [Pinakes INDEX](../INDEX.lego.md) -- Full audit system documentation
- [agents-criteria](agents.lego.md) -- Evaluation criteria for agent prompts
- [dromena-criteria](dromena.lego.md) -- Evaluation criteria for slash commands
