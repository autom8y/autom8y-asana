---
name: socratic-architecture-criteria
description: "Socratic challenge criteria for .know/architecture.md assumption exposure. Use when: theoros is surfacing unstated assumptions in the architecture document. Triggers: socratic architecture challenge, architecture assumptions, hidden architecture constraints, assumption exposure audit."
scope: socratic
---

# socratic-architecture Challenge Criteria

> **ASSUMPTION-EXPOSURE GRADING — READ BEFORE PROCEEDING**
>
> This is a socratic challenge domain. Grading measures how thoroughly the theoros SURFACES HIDDEN ASSUMPTIONS in `.know/architecture.md`.
>
> - **A (Excellent)** = MANY well-categorized assumptions surfaced — thorough analysis
> - **F (Failing)** = FEW assumptions surfaced — shallow analysis, likely missed assumptions
>
> The theoros role here is to ask: "What does this document take for granted without saying so?" A high grade means the challenge found many implicit assumptions that the document treats as obvious. A low grade means the analysis was superficial and likely left assumptions buried.

## Scope

**Input file (the thing being analyzed)**: `.know/architecture.md`

**Supporting evidence** (to verify whether assumptions hold):
- Package structure inspection (do actual packages match the model?)
- `cmd/` entry points (does the single-binary assumption hold?)
- Go module files (`go.mod`) for dependency and versioning assumptions
- Build tags and environment variables referenced in code

**What to do**: Read `.know/architecture.md` completely. For every architectural claim, ask: "What must be true for this claim to hold that the document does not explicitly state?" Surface those implicit truths as assumptions.

**What NOT to do**: Do not evaluate whether the architecture is correct. Do not look for contradictions (that is the advocatus domain). Surface what is assumed but unsaid.

**Challenge question**: "What assumptions does `.know/architecture.md` make without stating them?"

## Assumption Categories to Probe

The following categories guide the analysis. Apply each as a lens to the document:

| Category | Example assumption type |
|----------|------------------------|
| **Single-instance** | "One binary is deployed" — never stated, assumed everywhere |
| **Execution environment** | OS, filesystem layout, working directory, permissions |
| **Concurrency model** | Whether operations are safe for concurrent callers |
| **Ordering guarantees** | Sequential phase execution, single-writer constraints |
| **Failure modes** | What happens when a layer fails; recovery assumptions |
| **Performance expectations** | Implicit latency/throughput requirements |
| **Deployment topology** | Where the binary runs, who invokes it, with what permissions |
| **Dependency stability** | External libraries assumed stable/pinned/available |
| **State persistence** | What state survives restarts; durability assumptions |
| **Interface contracts** | What callers must provide; what the system guarantees back |

## Challenge Output Format

Each assumption finding must follow this structure:

| Field | Content |
|-------|---------|
| **Assumed claim** | The unstated thing the document takes for granted |
| **Where it appears** | Section or architectural element that relies on this assumption |
| **Category** | One of the categories above (single-instance, execution environment, etc.) |
| **Evidence from document** | Quote or paraphrase showing the assumption is load-bearing but unstated |
| **Why it matters** | What breaks if the assumption is false |
| **Recommendation** | State the assumption explicitly, document its rationale, or add a constraint to design-constraints.md |

## Criteria

### Criterion 1: Single-Instance and Topology Assumptions (weight: 25%)

**What to evaluate**: Does the architecture document assume a single instance, single user, single invocation path, or specific deployment topology without stating these constraints?

**Evidence to collect**:
- Look for implied single-writer patterns (e.g., file operations without locking described)
- Look for global state assumptions (e.g., process-level singletons implied)
- Look for topology assumptions (e.g., "runs on developer's machine" vs "runs in CI")
- For each assumption found: quote the document section, state the assumption, explain what breaks if violated

**Grading** — MORE assumptions surfaced = HIGHER grade (more thorough analysis):

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 4+ distinct single-instance or topology assumptions surfaced | Each assumption: document quote, category, why-it-matters, recommendation |
| B | 3 assumptions surfaced | Three distinct assumptions with full documentation |
| C | 2 assumptions surfaced | Two assumptions with adequate documentation |
| D | 1 assumption surfaced | One assumption found; analysis likely shallow |
| F | 0 assumptions surfaced | No single-instance or topology assumptions identified; implausible for non-trivial architecture |

---

### Criterion 2: Execution Environment and OS Assumptions (weight: 20%)

**What to evaluate**: Does the architecture document assume a specific OS, filesystem layout, environment variables, working directory, shell environment, or permission model without making these explicit?

**Evidence to collect**:
- Look for implicit filesystem path assumptions (e.g., `~/.claude/` assumed to exist)
- Look for shell or environment variable dependencies assumed available
- Look for OS-specific behavior assumed (e.g., symlinks, file permissions, temp directories)
- Check whether Go version, build toolchain, or CGO_ENABLED constraints are documented vs. assumed
- For each assumption: document source section, specific assumption, platform sensitivity

**Grading** — MORE assumptions surfaced = HIGHER grade:

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 4+ distinct environment assumptions surfaced | Each assumption: document section, specific constraint assumed, what fails on a different platform/environment |
| B | 3 assumptions surfaced | Three assumptions with category and documentation |
| C | 2 assumptions surfaced | Two assumptions adequately documented |
| D | 1 assumption surfaced | One assumption; environment analysis likely incomplete |
| F | 0 assumptions surfaced | No environment assumptions found; implausible for a CLI tool with filesystem operations |

---

### Criterion 3: Ordering and Concurrency Assumptions (weight: 25%)

**What to evaluate**: Does the architecture document assume sequential execution, single-threaded operation, or specific ordering guarantees that are not explicitly stated?

**Evidence to collect**:
- Look for pipeline stage descriptions that assume sequential execution without saying so
- Look for read-then-write patterns assumed to be atomic
- Look for initialization sequences assumed to complete before use
- Look for phase orchestration described without documenting reentrancy safety or concurrent-call behavior
- For each assumption: document the pipeline or flow section, the ordering constraint assumed, what breaks if violated

**Grading** — MORE assumptions surfaced = HIGHER grade:

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 4+ distinct ordering or concurrency assumptions surfaced | Each assumption: pipeline context, specific ordering claim assumed, consequence of violation |
| B | 3 assumptions surfaced | Three ordering/concurrency assumptions with full documentation |
| C | 2 assumptions surfaced | Two assumptions with adequate documentation |
| D | 1 assumption surfaced | One assumption found; concurrency analysis likely shallow |
| F | 0 assumptions surfaced | No ordering or concurrency assumptions identified; implausible for a system with pipeline stages |

---

### Criterion 4: Failure Mode and Interface Contract Assumptions (weight: 30%)

**What to evaluate**: Does the architecture document assume specific failure behavior, error propagation paths, or interface contracts that callers must honor — without stating these assumptions?

**Evidence to collect**:
- Look for error handling described at one layer without documenting what the caller is expected to do with errors
- Look for resource management (file handles, locks, connections) assumed to be cleaned up by callers
- Look for interface invariants assumed: "this function always returns a non-nil result" assumed but not stated
- Look for what is NOT documented: missing failure mode documentation (what if the config file is missing? what if the target directory is unwritable?)
- Look for callee contracts assumed: "caller must call Init before Use" patterns implied but not stated
- For each assumption: which interface, what the caller must guarantee or can assume, document section relying on it

**Grading** — MORE assumptions surfaced = HIGHER grade:

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 5+ distinct failure mode or interface contract assumptions surfaced | Each assumption: interface/function context, specific contract assumed, what breaks if violated, recommendation |
| B | 3-4 assumptions surfaced | Multiple failure/contract assumptions with full documentation |
| C | 2 assumptions surfaced | Two assumptions with adequate documentation |
| D | 1 assumption surfaced | One assumption found; failure mode analysis likely shallow |
| F | 0 assumptions surfaced | No failure mode or contract assumptions found; implausible for a multi-layer architecture |

---

## Grading Calculation

Final grade is weighted average of all criteria midpoint scores (see `schemas/grading.lego.md`). Reminder: for this domain, HIGHER grades indicate MORE assumptions surfaced (more thorough analysis).

Example (thorough analysis surfacing many assumptions):

- Single-Instance / Topology: A (midpoint 95%) x 25% = 23.75
- Execution Environment: A (midpoint 95%) x 20% = 19.0
- Ordering / Concurrency: B (midpoint 85%) x 25% = 21.25
- Failure Modes / Contracts: A (midpoint 95%) x 30% = 28.5
- **Total: 92.5 -> A** (thorough assumption exposure; many hidden assumptions surfaced)

Example (shallow analysis missing most assumptions):

- Single-Instance / Topology: C (midpoint 75%) x 25% = 18.75
- Execution Environment: D (midpoint 65%) x 20% = 13.0
- Ordering / Concurrency: C (midpoint 75%) x 25% = 18.75
- Failure Modes / Contracts: D (midpoint 65%) x 30% = 19.5
- **Total: 70.0 -> C** (surface-level analysis; significant assumptions likely uncovered)

## Related

- [Pinakes INDEX](../INDEX.lego.md) -- Full audit system documentation
- [architecture-criteria](architecture.lego.md) -- Direct architecture compliance audit
- [advocatus-architecture-criteria](advocatus-architecture.lego.md) -- Companion: contradiction finding for architecture document
- [socratic-design-constraints-criteria](socratic-design-constraints.lego.md) -- Companion: assumption exposure for design-constraints document
- [grading schema](../schemas/grading.lego.md) -- Grade calculation rules
