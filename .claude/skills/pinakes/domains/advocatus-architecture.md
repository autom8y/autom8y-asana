---
name: advocatus-architecture-criteria
description: "Adversarial challenge criteria for .know/architecture.md accuracy. Use when: theoros is running advocatus diaboli challenge mode to find structural evidence that contradicts the documented architecture. Triggers: advocatus architecture challenge, challenge architecture, architecture accuracy, adversarial architecture audit."
scope: adversarial
---

# advocatus-architecture Challenge Criteria

> **INVERTED GRADING — READ BEFORE PROCEEDING**
>
> This is an adversarial (advocatus diaboli) domain. Grading is the OPPOSITE of a standard audit.
>
> - **A (Excellent)** = FEW contradictions found — the architecture document is ACCURATE
> - **F (Failing)** = MANY contradictions found — the architecture document is INACCURATE
>
> The theoros role here is devil's advocate: actively seek structural evidence that CONTRADICTS `.know/architecture.md`. A high grade means the challenge found little structural drift. A low grade means the documented architecture no longer reflects codebase reality.

## Scope

**Input file (the thing being challenged)**: `.know/architecture.md`

**Codebase scan**:
- Package structure: `internal/`, `cmd/`, top-level directories
- Import graphs: check actual import relationships in Go source files
- Layer boundaries: verify the documented layer model against real imports
- Entry points: `cmd/` binaries vs. documented CLI surface
- Key data flows: trace actual call paths through documented pipeline stages

**What to do**: Read `.know/architecture.md` completely. Extract every structural claim as a falsifiable assertion. Then inspect the codebase for evidence that contradicts each assertion.

**What NOT to do**: Do not confirm the architecture. Do not read only the files that seem to support the documentation. Seek contradictions.

**Challenge question**: "Find structural evidence that contradicts the documented architecture in `.know/architecture.md`."

## Challenge Output Format

Each finding must follow this structure:

| Field | Content |
|-------|---------|
| **Claim** | Exact quote or close paraphrase from `.know/architecture.md` |
| **Counter-evidence** | File path(s), import statement, or structural observation that contradicts the claim |
| **Contradiction strength** | `strong` (clear violation), `moderate` (plausible exception), `weak` (ambiguous) |
| **Recommendation** | Update the knowledge document, refactor the code to match documented intent, or accept as documented exception |

## Criteria

### Criterion 1: Claim Extraction Completeness (weight: 15%)

**What to evaluate**: Does the theoros extract every structural claim from `.know/architecture.md` as a falsifiable assertion? Missed claims cannot be challenged.

**Evidence to collect**:
- Read `.know/architecture.md` completely
- Extract structural claims: package descriptions, layer responsibilities, dependency directions, data flow stages, entry points, key invariants
- Convert each claim to a testable assertion: "Package X should only import Y" or "Layer A should not depend on Layer B"
- Count total falsifiable claims extracted

**INVERTED GRADING** — A = comprehensive extraction (more challenge surface):

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% of structural claims extracted as falsifiable assertions | Complete assertion inventory: claim text, what falsification looks like, verification approach |
| B | 80-89% of claims extracted | Most structural claims captured; 1-3 claims not broken into testable form |
| C | 70-79% of claims extracted | Majority extracted; some architectural claims remain too vague to falsify |
| D | 60-69% of claims extracted | Less than 70% of structural claims extracted; challenge surface incomplete |
| F | < 60% of claims extracted | Adversarial analysis cannot proceed reliably; too many unchallenged claims |

---

### Criterion 2: Package and Layer Boundary Contradictions (weight: 35%)

**What to evaluate**: `.know/architecture.md` documents a package structure and layer model. Find import violations: packages that import across stated boundaries, hub packages that import leaf packages, or undocumented cross-cutting dependencies.

**Evidence to collect**:
- Extract the documented layer model and package responsibilities from `.know/architecture.md`
- Inspect actual Go import statements in 15-20 key files across the package tree
- Map actual imports against the documented dependency graph
- Document each boundary violation: importer, importee, why this contradicts the documented layer model
- Check specifically for: circular dependencies, upward-layer imports, undocumented cross-package couplings

**INVERTED GRADING** — A = few boundary violations (architecture accurate); F = many violations:

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 0-1 import boundary violations found | Files inspected listed; import trace for each alleged violation; reason the boundary was not violated (or the one that was) |
| B | 2-3 boundary violations found | Violations documented with importer, importee, and why it contradicts documentation |
| C | 4-6 boundary violations found | Several violations; pattern may indicate evolving codebase or stale layer model |
| D | 7-10 boundary violations found | Layer model in documentation does not match actual dependency graph; significant drift |
| F | > 10 boundary violations found | Documented architecture is substantially inaccurate; import graph contradicts stated layers throughout |

---

### Criterion 3: Data Flow and Pipeline Contradictions (weight: 30%)

**What to evaluate**: `.know/architecture.md` describes key data flows or pipeline stages (e.g., sync pipeline, materialization sequence, hook execution order). Find code paths that contradict the documented flow: missing stages, stages in wrong order, undocumented branches, or stages that no longer exist.

**Evidence to collect**:
- Extract documented data flow descriptions and pipeline stages from `.know/architecture.md`
- Trace actual code paths through the described pipeline using source files
- Document contradictions: a stage described that has no corresponding code, a stage in the wrong order, an undocumented branch that changes behavior
- Note code paths that exist but are absent from the documented flow

**INVERTED GRADING** — A = few flow contradictions (data flow accurate); F = many contradictions:

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | < 2 flow contradictions found | Pipeline trace for each documented flow; specific files and functions identified; any contradictions with exact file paths |
| B | 2-3 flow contradictions found | Most documented flows match code; contradictions described with specific code references |
| C | 4-5 flow contradictions found | Some documented flows are partially inaccurate; may reflect new code paths not yet documented |
| D | 6-8 flow contradictions found | Multiple pipeline descriptions do not match code reality; documentation lags significantly |
| F | > 8 flow contradictions found | Data flow documentation is substantially inaccurate; major undocumented paths or absent stages |

---

### Criterion 4: Entry Point and CLI Surface Contradictions (weight: 20%)

**What to evaluate**: `.know/architecture.md` describes the CLI surface, entry points, and binary structure. Find contradictions: undocumented commands, commands that no longer exist, binary structure that differs from the description, or entry points that contradict the stated model.

**Evidence to collect**:
- Extract CLI surface and entry point claims from `.know/architecture.md`
- Inspect `cmd/` directory structure and Cobra command registration
- Compare documented commands vs. actual registered commands
- Note any entry points not in documentation and any documented entry points not in code

**INVERTED GRADING** — A = few CLI contradictions (entry point documentation accurate); F = many contradictions:

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 0-1 CLI surface contradictions found | `cmd/` directory structure documented; command registration checked; any single discrepancy explained |
| B | 2-3 CLI contradictions found | Most entry points documented accurately; minor gaps in command surface documentation |
| C | 4-5 CLI contradictions found | Several undocumented or mis-described commands; documentation is partially stale |
| D | 6-8 CLI contradictions found | CLI surface significantly different from documentation; major commands missing or wrongly described |
| F | > 8 CLI contradictions found | CLI documentation substantially inaccurate; does not reflect actual binary structure |

---

## Grading Calculation

Final grade is weighted average of all criteria midpoint scores (see `schemas/grading.lego.md`). Reminder: for this domain, LOWER grades indicate MORE contradictions found (less accurate documentation).

Example (architecture document closely matching code):

- Claim Extraction: A (midpoint 95%) x 15% = 14.25
- Layer Boundary Contradictions: A (midpoint 95%) x 35% = 33.25
- Data Flow Contradictions: B (midpoint 85%) x 30% = 25.5
- CLI Surface Contradictions: A (midpoint 95%) x 20% = 19.0
- **Total: 92.0 -> A** (few contradictions found; architecture document is accurate)

Example (architecture document with notable drift):

- Claim Extraction: B (midpoint 85%) x 15% = 12.75
- Layer Boundary Contradictions: C (midpoint 75%) x 35% = 26.25
- Data Flow Contradictions: D (midpoint 65%) x 30% = 19.5
- CLI Surface Contradictions: B (midpoint 85%) x 20% = 17.0
- **Total: 75.5 -> C** (moderate contradictions; architecture document has accuracy gaps requiring refresh)

## Related

- [Pinakes INDEX](../INDEX.lego.md) -- Full audit system documentation
- [architecture-criteria](architecture.lego.md) -- Direct architecture compliance audit (confirmatory, not adversarial)
- [radar-architecture-decay-criteria](radar-architecture-decay.lego.md) -- Radar signal for architectural decay
- [socratic-architecture-criteria](socratic-architecture.lego.md) -- Companion: assumption exposure for architecture document
- [grading schema](../schemas/grading.lego.md) -- Grade calculation rules
