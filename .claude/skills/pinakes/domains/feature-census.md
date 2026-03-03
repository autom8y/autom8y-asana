---
name: feature-census-criteria
description: "Criteria for feature enumeration census. Use when: theoros is scanning project sources to produce a comprehensive feature taxonomy with GENERATE/SKIP recommendations. Triggers: feature census, feature enumeration, feature inventory, feature taxonomy, feature discovery."
---

# Feature Census Criteria

> The theoros scans project sources and enumerates ALL identifiable features, producing a structured feature inventory with classification and triage recommendations. This is a census -- completeness of enumeration is the grading target, not feature quality.

## Language Detection

Before beginning observation, identify the primary language(s) in the project:
- Check for: `go.mod` (Go), `package.json` (JS/TS), `pyproject.toml`/`setup.py` (Python),
  `Cargo.toml` (Rust), `pom.xml`/`build.gradle` (Java/Kotlin)
- Adapt source directories and evidence collection accordingly

### Scope Adaptation for Feature Discovery

| Source Category | Go | TypeScript | Python | Generic |
|---|---|---|---|---|
| Module/package map | `internal/*/`, `cmd/*/` | `src/*/`, `lib/*/`, `app/*/` | `src/*/`, `app/*/` | top-level source directories |
| Entry points | `cmd/*/main.go` | `src/index.ts`, `src/app/` | `__main__.py`, `app.py` | main/index files |
| Decision records | `docs/decisions/`, `docs/adrs/` | `docs/decisions/`, `docs/adrs/` | `docs/decisions/`, `docs/adrs/` | `docs/decisions/`, `docs/adrs/`, `docs/rfcs/` |
| Config manifests | `go.mod` | `package.json`, `tsconfig.json` | `pyproject.toml` | project root configs |
| User-facing interface | CLI subcommands, route handlers | API routes, page components | CLI commands, API endpoints | interface definitions |

## Scope

**Prerequisite**: Fresh `.know/` codebase domain seeds (architecture, scar-tissue, conventions, design-constraints, test-coverage) must exist. The `/know` dromenon enforces this gate before dispatching this census.

**Source discovery** (theoros must scan all applicable):

1. **Structural map** (highest priority): Read `.know/architecture.md` for the package/module inventory, layer model, and entry points. This is your project-specific navigation map -- use it to identify where features are implemented rather than guessing directory structures.
2. **Module/package directories**: Identified via Language Detection (see Scope Adaptation table). Verify against `.know/architecture.md` if available.
3. **Decision records** (ADRs, RFCs, design documents): Check standard locations (`docs/decisions/`, `docs/adrs/`, `docs/rfcs/`). Titles and first paragraphs reveal feature-level decisions.
4. **User-facing interface definitions**: Commands, routes, pages, API endpoints, or CLI subcommands -- whatever the project exposes to users. Discover via language conventions and project documentation.
5. **Project documentation**: `README.md`, `CONTRIBUTING.md`, `docs/` directory. These often describe features at a high level.
6. **Existing codebase knowledge**: `.know/*.md` frontmatter as feature signals. Each knowledge domain implicitly maps to feature areas.
7. **Configuration and workflow definitions**: CI/CD configs, deployment manifests, or any declarative files that reveal feature boundaries.

**Observation focus**: Enumerate every identifiable feature in the project. For each feature, produce a structured entry with slug, name, category, source evidence, complexity rating, GENERATE/SKIP recommendation, and confidence score.

**NOTE**: This domain uses knowledge-capture grading. Grade the COMPLETENESS of the enumeration, not the quality of individual features. A = every identifiable feature cataloged with evidence. F = fewer than half of identifiable features documented.

## Output Format

The census theoros must produce per-feature entries with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `slug` | kebab-case string | Unique identifier (e.g., `authentication`, `billing`, `data-pipeline`) |
| `name` | human-readable string | Feature display name |
| `category` | string | Grouping (e.g., "Core Platform", "User-Facing", "Infrastructure", "Tooling") |
| `source_evidence` | string list | Which scanned files reference this feature |
| `complexity` | enum | HIGH / MEDIUM / LOW based on module count, decision record count, interface surface |
| `recommendation` | enum + rationale | GENERATE / SKIP with brief rationale |
| `confidence` | float | 0.0-1.0 how confident theoros is in this classification |

## Triage Heuristics

The theoros uses these rules to produce GENERATE vs SKIP recommendations:

**GENERATE** if any of:
- 1+ decision records (ADRs, RFCs, design docs) reference the feature
- 10+ implementation files in relevant packages/modules
- User-facing interface surface exists (CLI commands, API endpoints, UI pages)
- Multiple modules/packages depend on the feature

**SKIP** if all of:
- Pure utility (string helpers, file I/O wrappers, logging utilities)
- No decision records reference the feature
- Fewer than 5 implementation files
- Internal implementation detail with no cross-cutting concerns

## Criteria

### Criterion 1: Source Coverage (weight: 30%)

**What to evaluate**: Did the theoros scan all applicable source types? Each source type contributes unique feature signals. Incomplete scanning produces incomplete census.

**Evidence to collect**:
- Confirm which of the 7 source categories were accessed and scanned
- Record per category: files scanned count, features discovered from that source
- Note any categories that do not exist in this project (explicit absence is evidence, not a failure)
- Flag if any existing category was skipped without justification

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | All applicable source categories scanned with evidence | Per-category scan summary: files accessed, features found. Non-existent categories documented as absent. No existing category skipped. |
| B | All but one applicable category scanned | One category missing but justification provided (e.g., no decision records exist). All other categories fully scanned with evidence. |
| C | 70-79% of applicable categories scanned | Two categories missing. Remaining sources scanned but per-category evidence incomplete. |
| D | 60-69% of applicable categories scanned | Three categories missing. Feature enumeration relies on partial evidence base. |
| F | Fewer than 60% of applicable categories scanned | More than half the available sources not scanned. Census built from insufficient evidence. |

---

### Criterion 2: Feature Enumeration (weight: 30%)

**What to evaluate**: Are all identifiable features listed with slugs and names? The census must capture every distinct feature the project implements, not just the obvious ones.

**Evidence to collect**:
- Count total features enumerated
- Verify each feature has a unique slug (kebab-case) and human-readable name
- Cross-check: do module/package clusters, decision record topics, interface definitions, and documentation sections all have corresponding feature entries?
- Identify any source references that do not map to a feature entry (potential gaps)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of identifiable features enumerated | Every module cluster, decision topic, interface group, and documented capability maps to a feature entry. Cross-reference table shows no unaccounted source references. Each entry has unique slug and name. |
| B | 80-89% of identifiable features enumerated | Most features captured. Minor gaps where 1-2 source references lack corresponding feature entries. All entries have slug and name. |
| C | 70-79% of identifiable features enumerated | Core features present but peripheral features (utilities, tooling, workflow features) partially missing. Some entries missing slug or name. |
| D | 60-69% of identifiable features enumerated | Only major features listed. Many module clusters and decision topics unaccounted for. Slugs or names inconsistent. |
| F | Fewer than 60% of identifiable features enumerated | Fewer than half the identifiable features documented. Census is unreliable for planning purposes. |

---

### Criterion 3: Classification Quality (weight: 20%)

**What to evaluate**: Are categories logical, recommendations justified, and complexity ratings evidence-based? Classification must be grounded in scanned evidence, not assumptions.

**Evidence to collect**:
- Verify categories are internally consistent (features in the same category share meaningful properties)
- For each GENERATE recommendation: confirm at least one triage heuristic is met with evidence
- For each SKIP recommendation: confirm all skip conditions are met with evidence
- For complexity ratings: confirm evidence basis (module count, decision record count, interface surface cited)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of entries have evidence-based classification | Every feature entry: category justified, recommendation cites specific heuristic match with file evidence, complexity rating cites counts. Categories are coherent groupings. |
| B | 80-89% of entries have evidence-based classification | Most entries fully classified with evidence. Minor gaps where 1-2 entries lack heuristic citation or complexity evidence. Categories mostly coherent. |
| C | 70-79% of entries have evidence-based classification | Categories present but some are catch-all groupings. Recommendations present but heuristic citations inconsistent. Complexity ratings present but evidence sparse. |
| D | 60-69% of entries have evidence-based classification | Categories applied but not justified. Recommendations present without heuristic evidence. Complexity ratings appear arbitrary. |
| F | Fewer than 60% of entries have evidence-based classification | Classifications absent, unjustified, or internally contradictory. |

---

### Criterion 4: Output Format Compliance (weight: 20%)

**What to evaluate**: Does the output follow the structured per-feature entry format? Downstream consumers (the `/know` dispatch and feature-knowledge theoros) depend on a consistent, parseable census format.

**Evidence to collect**:
- Verify every feature entry contains all 7 required fields (slug, name, category, source_evidence, complexity, recommendation, confidence)
- Confirm slug format (kebab-case, no uppercase, no spaces)
- Confirm complexity values are exactly HIGH / MEDIUM / LOW
- Confirm recommendation values are exactly GENERATE / SKIP with rationale string
- Confirm confidence is a float between 0.0 and 1.0

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 100% of entries conform to format | Every entry has all 7 fields. Slug format valid. Enum values match spec exactly. Confidence values in range. Output is machine-parseable. |
| B | 90-99% of entries conform | 1-2 entries with minor format violations (e.g., missing confidence, slug with underscore). All required fields present in remainder. |
| C | 80-89% of entries conform | Multiple entries with format violations. Some missing fields. Enum values mostly correct but occasional non-standard values. |
| D | 70-79% of entries conform | Format inconsistent across entries. Multiple missing fields. Output requires manual cleanup before downstream use. |
| F | Fewer than 70% of entries conform | Format largely ignored. Entries are free-text rather than structured. Output not usable by downstream consumers. |

---

## Grading Calculation

Final grade is weighted average of all criteria midpoint scores (see `schemas/grading.lego.md`). Example:
- Source Coverage: A (midpoint 95%) x 30% = 28.5
- Feature Enumeration: B (midpoint 85%) x 30% = 25.5
- Classification Quality: B (midpoint 85%) x 20% = 17.0
- Output Format Compliance: A (midpoint 95%) x 20% = 19.0
- **Total: 90.0 -> A**

## Related

- [Pinakes INDEX](../INDEX.lego.md) -- Full audit system documentation
- [feature-knowledge-criteria](feature-knowledge.lego.md) -- Per-feature knowledge capture (downstream consumer of this census)
- [architecture-criteria](architecture.lego.md) -- Codebase architecture knowledge capture (complementary domain, same Language Detection pattern)
