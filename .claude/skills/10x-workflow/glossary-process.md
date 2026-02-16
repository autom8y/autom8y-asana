# Glossary: Process & Workflow

> Workflow phases, concepts, decision-making

**Other Domains**: [Agents & Artifacts](glossary-agents.md) | [Quality & Principles](glossary-quality.md) | [Index](glossary-index.md)

---

## Workflow Phases

### Prompt -1 (Scoping Phase)
**Definition**: The pre-initialization phase that validates an initiative's readiness before committing to the full workflow. Answers: "Do we know enough to write Prompt 0?"

**Owner**: User (with AI assistance)

**Outputs**: Go/No-Go recommendation, validated scope, identified blockers, open questions

**Key Principle**: Cheap validation prevents expensive rework. 30 minutes of scoping can save days of misdirected effort.

---

### Prompt 0 (Initialization Phase)
**Definition**: The Pythia initialization document that establishes mission context, defines success criteria, and structures the session-phased approach. Seeds Pythia with everything it needs to coordinate the workflow.

**Owner**: User (creates) -> Pythia (consumes)

**Outputs**: Mission statement, session plan, trigger prompts, quality gates, context checklists

**Key Principle**: Pythia should be able to execute the entire workflow from Prompt 0 without additional context gathering.

---

### Session
**Definition**: A discrete phase of work with a specific agent, clear deliverable, and quality gate. Sessions are the atomic unit of the workflow.

**Owner**: Pythia (defines) -> Specialist Agent (executes)

**Outputs**: Phase-specific deliverable (PRD, TDD, code, validation report)

**Key Principle**: Each session should be completable in a single focused effort. If a session needs to be split, it was scoped too broadly.

---

### Discovery Phase
**Definition**: The first session(s) of a workflow where unknowns are explored, gaps are identified, and requirements are clarified. Reduces uncertainty before design or implementation.

**Owner**: Requirements Analyst (typically)

**Outputs**: Gap analysis, current state audit, scope refinement, technical clarifications

**Key Principle**: Discovery is not optional for complex initiatives. Skipping discovery leads to rework.

---

## Workflow Concepts

### Quality Gate
**Definition**: A checkpoint between phases that must be passed before proceeding. Prevents low-quality work from propagating downstream.

**Types**:
- **PRD Quality Gate**: Problem clear, scope defined, requirements testable
- **TDD Quality Gate**: Traces to PRD, decisions documented, interfaces defined
- **Implementation Quality Gate**: Satisfies TDD, tests pass, type-safe
- **Validation Quality Gate**: Acceptance criteria met, edge cases covered

**Key Principle**: Quality gates are non-negotiable. Failing a gate means routing back, not proceeding with gaps.

---

### Handoff
**Definition**: The transition between agents or phases, including all context, artifacts, and open items needed for the receiving agent to succeed.

**Requirements**:
- Summary of what was produced
- Quality gate status
- Open questions or concerns
- Inputs needed for next phase

**Key Principle**: A good handoff enables the receiving agent to work without asking clarifying questions about prior work.

---

### Scope Creep
**Definition**: Uncontrolled expansion of scope during execution, often disguised as "clarification" or "while we're at it."

**Detection**: New requirements appearing mid-phase that weren't in the approved PRD.

**Response**: Flag explicitly, distinguish "nice to have" from "blocking," propose deferral or re-planning.

**Key Principle**: Scope creep is the primary cause of project failure. Name it when you see it.

---

### Spike
**Definition**: A timeboxed investigation to reduce uncertainty before committing to a larger effort. Produces knowledge, not production code.

**Characteristics**:
- Fixed timebox (hours, not days)
- Specific question to answer
- Output is decision-enabling information

**When to Use**: High-uncertainty items identified in Prompt -1, technical feasibility questions, "build vs. buy" decisions.

---

### Complexity Level
**Definition**: Classification of initiative scope that determines appropriate workflow depth.

| Level | Description | Typical Workflow |
|-------|-------------|------------------|
| **Script** | Single file, utility function | Direct implementation |
| **Module** | Multiple files, single concern | Engineer -> QA |
| **Service** | Multiple modules, external interfaces | Full 4-agent workflow |
| **Platform** | Multiple services, organizational impact | Extended workflow with multiple implementation phases |

**Key Principle**: Right-size the workflow. Not every task needs all four agents.

---

## Decision Concepts

### Go/No-Go
**Definition**: A binary decision point in Prompt -1 that determines whether to proceed with Prompt 0.

**Go**: Proceed to Prompt 0 generation and workflow execution

**No-Go**: Resolve blockers, gather more context, descope, or abandon initiative

**Conditional Go**: Proceed with specific conditions that must be met before certain phases

---

### Must/Should/Could (MoSCoW)
**Definition**: Requirement prioritization framework used in PRDs.

| Priority | Meaning | Implication |
|----------|---------|-------------|
| **Must** | Non-negotiable | Blocks release if missing |
| **Should** | Important | Include if possible, defer if constrained |
| **Could** | Nice to have | Only if time permits |
| **Won't** | Explicitly excluded | Out of scope for this initiative |

---

### Blocking vs. Non-Blocking
**Definition**: Classification of dependencies and issues by their impact on progress.

**Blocking**: Cannot proceed until resolved. Requires immediate attention or scope change.

**Non-Blocking**: Can be worked around or deferred. Document and continue.
