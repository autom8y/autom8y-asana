---
name: socratic-design-constraints-criteria
description: "Socratic challenge criteria for .know/design-constraints.md assumption exposure. Use when: theoros is surfacing constraints that exist in the codebase but are not documented in design-constraints.md. Triggers: socratic design constraints challenge, undocumented constraints, hidden constraints, assumption exposure audit, design constraints gaps."
scope: socratic
---

# socratic-design-constraints Challenge Criteria

> **ASSUMPTION-EXPOSURE GRADING — READ BEFORE PROCEEDING**
>
> This is a socratic challenge domain. Grading measures how thoroughly the theoros SURFACES CONSTRAINTS that exist in the codebase but are not documented in `.know/design-constraints.md`.
>
> - **A (Excellent)** = MANY undocumented constraints surfaced — thorough analysis
> - **F (Failing)** = FEW undocumented constraints surfaced — shallow analysis, likely missed constraints
>
> The theoros role here is to ask: "What does this codebase enforce that the design-constraints document does not say?" A high grade means the challenge found many real constraints present in code that are invisible in the documentation. A low grade means the analysis was superficial.

## Scope

**Input file (the thing being analyzed)**: `.know/design-constraints.md`

**Codebase scan** for undocumented constraint evidence:
- Hard-coded values, magic numbers, length limits, path prefixes
- Build tags, `//go:build` constraints, OS-specific code paths
- `init()` functions, package-level `var` blocks with sentinel values
- Validation functions: `if len(x) < N`, `if x == ""`, `if !strings.HasPrefix(x, prefix)`
- Comment blocks beginning with "must", "cannot", "always", "never", "only"
- `panic()` calls indicating invariants enforced at runtime
- Interface implementation assertions: `var _ SomeInterface = (*SomeType)(nil)`
- Lock types, `sync.Once`, channel directions indicating concurrency constraints

**What to do**: Read `.know/design-constraints.md` completely. Then scan the codebase for constraints enforced in code that are not documented in the file. Surface the gap: "this constraint exists in code, but is invisible in the documentation."

**What NOT to do**: Do not evaluate whether the constraints are correct or well-designed. Do not look for constraint violations (that is the radar-constraint-violations domain). Surface what is enforced but undocumented.

**Challenge question**: "What constraints exist in the code that are not documented in `.know/design-constraints.md`?"

## Constraint Categories to Probe

| Category | Signal in code |
|----------|---------------|
| **Size and length limits** | `len(x) > N`, buffer sizes, string length checks |
| **Format and shape invariants** | Regex validation, prefix/suffix requirements, structural checks |
| **Ordering and initialization** | `sync.Once`, `init()`, must-call-before patterns |
| **Concurrency constraints** | Mutex usage, single-goroutine assumptions, channel directionality |
| **Path and environment constraints** | Hard-coded path prefixes, env variable requirements, home directory assumptions |
| **Interface invariants** | Compile-time interface checks, nil guards, method call ordering |
| **Build and platform constraints** | `//go:build` tags, `runtime.GOOS` switches, `CGO_ENABLED` assumptions |
| **External dependency constraints** | Minimum version assumptions, API surface assumptions about dependencies |

## Challenge Output Format

Each undocumented constraint must follow this structure:

| Field | Content |
|-------|---------|
| **Undocumented constraint** | Description of the constraint as it should read if documented |
| **Evidence in code** | File path, approximate line, specific code that enforces the constraint |
| **Category** | One of the categories above |
| **Present in design-constraints.md?** | Confirm it is absent or only weakly implied |
| **Why it matters** | Who needs to know this constraint; what breaks if it is violated unknowingly |
| **Recommendation** | Add to `.know/design-constraints.md`, add to ADR, or document inline with comment |

## Criteria

### Criterion 1: Documented Constraint Inventory (weight: 15%)

**What to evaluate**: Does the theoros correctly inventory what IS documented in `.know/design-constraints.md`? This creates the baseline — everything NOT in this inventory that is found in code is an undocumented constraint.

**Evidence to collect**:
- Read `.know/design-constraints.md` completely
- Extract every stated constraint: category, constraint text, whether it references code locations
- Note constraints stated vaguely (hard to match against code) vs. precisely (easy to cross-reference)
- Count total documented constraints as the baseline

**Grading** — complete inventory is a prerequisite for finding gaps:

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 100% of documented constraints extracted with category and precision classification | Complete inventory table; vague vs. precise classification; count of documented constraints |
| B | 90-99% of constraints extracted | All but 1-2 constraints inventoried; missed entries noted |
| C | 80-89% of constraints extracted | Most constraints captured; some paraphrased rather than precisely extracted |
| D | 70-79% of constraints extracted | Notable gaps in baseline; gap analysis will be incomplete |
| F | < 70% of constraints extracted | Incomplete baseline; undocumented constraint analysis unreliable |

---

### Criterion 2: Size, Format, and Invariant Constraints (weight: 30%)

**What to evaluate**: Does the codebase enforce size limits, format requirements, or structural invariants that are not in `.know/design-constraints.md`? These are among the most common undocumented constraints.

**Evidence to collect**:
- Scan validation functions across `internal/` packages for length limits, format checks, required prefixes/suffixes
- Look for `panic()` calls with constraint-violation messages
- Look for compile-time interface assertions (`var _ Interface = (*Type)(nil)`)
- For each undocumented constraint found: file path, code excerpt, constraint as it should be stated, cross-check that it is absent from `.know/design-constraints.md`

**Grading** — MORE undocumented constraints surfaced = HIGHER grade:

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 4+ undocumented size/format/invariant constraints surfaced | Each constraint: code evidence, category, documentation gap confirmed, recommendation |
| B | 3 undocumented constraints surfaced | Three constraints with full documentation |
| C | 2 undocumented constraints surfaced | Two constraints with adequate documentation |
| D | 1 undocumented constraint surfaced | One constraint found; analysis likely incomplete |
| F | 0 undocumented constraints surfaced | No size/format/invariant constraints found; implausible for a non-trivial codebase |

---

### Criterion 3: Environment and Build Constraints (weight: 25%)

**What to evaluate**: Does the codebase enforce environment requirements, build constraints, or platform assumptions that are not documented in `.know/design-constraints.md`?

**Evidence to collect**:
- Scan for `//go:build` tags and what they imply about supported platforms
- Look for `runtime.GOOS` switches that restrict behavior on specific OSes
- Look for environment variable reads without defaults (implicitly required)
- Look for hard-coded paths that assume specific filesystem layouts (e.g., `~/.claude/`, `KNOSSOS_HOME`)
- Look for `CGO_ENABLED` or other build-time assumptions in code or comments
- For each undocumented constraint: what the code requires, file evidence, whether design-constraints.md mentions it

**Grading** — MORE undocumented constraints surfaced = HIGHER grade:

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 4+ undocumented environment/build constraints surfaced | Each constraint: code evidence, what environment it requires, documentation gap confirmed |
| B | 3 undocumented constraints surfaced | Three constraints with full documentation |
| C | 2 undocumented constraints surfaced | Two constraints with adequate documentation |
| D | 1 undocumented constraint surfaced | One constraint found; environment analysis likely shallow |
| F | 0 undocumented constraints surfaced | No environment/build constraints found; implausible for a Go CLI tool |

---

### Criterion 4: Concurrency and Ordering Constraints (weight: 30%)

**What to evaluate**: Does the codebase enforce concurrency safety requirements, initialization ordering, or single-caller invariants that are not documented in `.know/design-constraints.md`?

**Evidence to collect**:
- Scan for `sync.Once` usage: what initialization is guaranteed to happen exactly once? Is this documented?
- Scan for mutex locks: what data requires synchronized access? Are concurrent callers warned?
- Look for `init()` functions: what must be initialized before the package is usable?
- Look for channel directions that imply caller/callee roles
- Look for struct fields that are "must set before use" without documentation
- For each undocumented constraint: what the code enforces, the enforcement mechanism, absence from design-constraints.md

**Grading** — MORE undocumented constraints surfaced = HIGHER grade:

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 4+ undocumented concurrency/ordering constraints surfaced | Each constraint: code mechanism (mutex, sync.Once, etc.), what it enforces, documentation gap confirmed, recommendation |
| B | 3 undocumented constraints surfaced | Three constraints with full documentation |
| C | 2 undocumented constraints surfaced | Two constraints with adequate documentation |
| D | 1 undocumented constraint surfaced | One constraint found; concurrency analysis likely incomplete |
| F | 0 undocumented constraints surfaced | No concurrency/ordering constraints found; implausible for a system with file operations and state |

---

## Grading Calculation

Final grade is weighted average of all criteria midpoint scores (see `schemas/grading.lego.md`). Reminder: for this domain, HIGHER grades indicate MORE undocumented constraints surfaced (more thorough analysis).

Example (thorough analysis surfacing many undocumented constraints):

- Documented Constraint Inventory: A (midpoint 95%) x 15% = 14.25
- Size / Format / Invariant Constraints: A (midpoint 95%) x 30% = 28.5
- Environment / Build Constraints: B (midpoint 85%) x 25% = 21.25
- Concurrency / Ordering Constraints: A (midpoint 95%) x 30% = 28.5
- **Total: 92.5 -> A** (thorough analysis; many undocumented constraints surfaced)

Example (shallow analysis missing most constraints):

- Documented Constraint Inventory: B (midpoint 85%) x 15% = 12.75
- Size / Format / Invariant Constraints: D (midpoint 65%) x 30% = 19.5
- Environment / Build Constraints: C (midpoint 75%) x 25% = 18.75
- Concurrency / Ordering Constraints: D (midpoint 65%) x 30% = 19.5
- **Total: 70.5 -> C** (surface-level analysis; significant undocumented constraints likely uncovered)

## Related

- [Pinakes INDEX](../INDEX.lego.md) -- Full audit system documentation
- [design-constraints-criteria](design-constraints.lego.md) -- Direct design constraints audit
- [radar-constraint-violations-criteria](radar-constraint-violations.lego.md) -- Radar signal: constraint violations in code
- [socratic-architecture-criteria](socratic-architecture.lego.md) -- Companion: assumption exposure for architecture document
- [grading schema](../schemas/grading.lego.md) -- Grade calculation rules
