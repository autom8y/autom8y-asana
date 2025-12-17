# 10x Agentic Workflow Glossary

> **Purpose**: Canonical definitions for terms used in the 4-agent development workflow. All agents and documentation reference these definitions to ensure consistent understanding.

---

## Workflow Phases

### Prompt -1 (Scoping Phase)
**Definition**: The pre-initialization phase that validates an initiative's readiness before committing to the full workflow. Answers: "Do we know enough to write Prompt 0?"

**Owner**: User (with AI assistance)

**Outputs**: Go/No-Go recommendation, validated scope, identified blockers, open questions

**Key Principle**: Cheap validation prevents expensive rework. 30 minutes of scoping can save days of misdirected effort.

---

### Prompt 0 (Initialization Phase)
**Definition**: The orchestrator initialization document that establishes mission context, defines success criteria, and structures the session-phased approach. Seeds the orchestrator with everything it needs to coordinate the workflow.

**Owner**: User (creates) -> Orchestrator (consumes)

**Outputs**: Mission statement, session plan, trigger prompts, quality gates, context checklists

**Key Principle**: The orchestrator should be able to execute the entire workflow from Prompt 0 without additional context gathering.

---

### Session
**Definition**: A discrete phase of work with a specific agent, clear deliverable, and quality gate. Sessions are the atomic unit of the workflow.

**Owner**: Orchestrator (defines) -> Specialist Agent (executes)

**Outputs**: Phase-specific deliverable (PRD, TDD, code, validation report)

**Key Principle**: Each session should be completable in a single focused effort. If a session needs to be split, it was scoped too broadly.

---

### Discovery Phase
**Definition**: The first session(s) of a workflow where unknowns are explored, gaps are identified, and requirements are clarified. Reduces uncertainty before design or implementation.

**Owner**: Requirements Analyst (typically)

**Outputs**: Gap analysis, current state audit, scope refinement, technical clarifications

**Key Principle**: Discovery is not optional for complex initiatives. Skipping discovery leads to rework.

---

## Agents & Roles

### Orchestrator
**Definition**: The coordinating agent that plans, delegates, coordinates, and verifies. Does not implement directly. Acts as a dispatcher routing work to specialist agents.

**Core Responsibilities**:
1. **Assess**: Determine complexity and required agents
2. **Plan**: Create phased approach with clear deliverables
3. **Delegate**: Invoke specialist agents with full context
4. **Verify**: Confirm quality gates before phase transitions
5. **Adapt**: Adjust plans based on discoveries

**Key Principle**: The orchestrator's judgment determines agent routing, session ordering, and workflow adaptation. It should not be over-prescribed by Prompt 0.

---

### Requirements Analyst
**Definition**: The specialist agent that clarifies intent, defines scope, and creates testable requirements. Transforms vague requests into precise specifications.

**Core Responsibilities**:
- Challenge assumptions and surface ambiguity
- Create PRDs with acceptance criteria
- Define scope boundaries (in AND out)
- Ask "why" before documenting "what"

**Primary Artifacts**: PRD (Product Requirements Document)

**Key Principle**: "Clarity before velocity. An hour of good questions saves a week of building the wrong thing."

---

### Architect
**Definition**: The specialist agent that designs solutions, makes structural decisions, and creates technical specifications. Translates "what" into "how."

**Core Responsibilities**:
- Design system architecture
- Create TDDs with component definitions
- Document decisions in ADRs
- Calibrate complexity to requirements

**Primary Artifacts**: TDD (Technical Design Document), ADR (Architecture Decision Record)

**Key Principle**: "The right design feels inevitable in hindsight. Right-size everything."

---

### Principal Engineer
**Definition**: The specialist agent that implements solutions with craft. Translates designs into working, maintainable code.

**Core Responsibilities**:
- Implement according to TDD specifications
- Maintain code quality and type safety
- Create tests for all paths
- Document implementation decisions

**Primary Artifacts**: Code, unit tests, implementation ADRs

**Key Principle**: "Simplicity is a feature. Build exactly what's specified, nothing more."

---

### QA/Adversary
**Definition**: The specialist agent that validates implementations, finds edge cases, and ensures production readiness. Thinks like an attacker to protect like a defender.

**Core Responsibilities**:
- Validate against acceptance criteria
- Find edge cases and failure modes
- Execute test plans
- Assess production readiness

**Primary Artifacts**: Test Plan, validation reports, defect lists

**Key Principle**: "Your job is to break things. Every bug found in review is a bug users don't find in production."

---

## Documentation Artifacts

### PRD (Product Requirements Document)
**Definition**: Defines WHAT we're building and WHY from a product/user perspective. Contains requirements, acceptance criteria, and scope boundaries.

**Owner**: Requirements Analyst

**Location**: `/docs/requirements/PRD-{NNNN}-{slug}.md`

**Key Sections**: Problem Statement, Scope (In/Out), Functional Requirements, Acceptance Criteria

---

### TDD (Technical Design Document)
**Definition**: Defines HOW we're building it from a technical perspective. Contains architecture, components, interfaces, and data flow.

**Owner**: Architect

**Location**: `/docs/design/TDD-{NNNN}-{slug}.md`

**Key Sections**: Overview, Component Architecture, Data Model, API Contracts, Implementation Plan

---

### ADR (Architecture Decision Record)
**Definition**: Captures WHY a specific architectural decision was made. Provides context for future maintainers and enables informed evolution.

**Owner**: Architect (primary), Principal Engineer (implementation-level)

**Location**: `/docs/decisions/ADR-{NNNN}-{slug}.md`

**Key Sections**: Context, Decision, Rationale, Alternatives Considered, Consequences

**When to Write**: Choosing between viable approaches, adopting new patterns, deviating from established conventions, making trade-offs with long-term implications.

---

### Test Plan
**Definition**: Defines HOW we validate the implementation meets requirements. Maps requirements to test cases with coverage tracking.

**Owner**: QA/Adversary

**Location**: `/docs/testing/TP-{NNNN}-{slug}.md`

**Key Sections**: Test Scope, Requirements Traceability, Test Cases, Edge Cases, Exit Criteria

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

---

## Communication Patterns

### Plan -> Clarify -> Execute
**Definition**: The mandatory communication pattern before any significant work.

1. **Plan**: Agent creates detailed plan for the phase
2. **Clarify**: Surface ambiguities, get user input on decisions
3. **Execute**: Only after explicit confirmation ("Proceed with the plan")

**Key Principle**: "Never execute without confirmation. Plans are cheap; rework is expensive."

---

### Session Trigger Prompt
**Definition**: The specific prompt used to initiate a session, containing prerequisites, goals, scope, and deliverables.

**Purpose**: Provides the specialist agent with everything needed to plan and execute the session.

**Key Sections**: Prerequisites, Goals, Scope (In/Out), Constraints, Deliverable specification

---

### Checkpoint
**Definition**: A summary of progress at phase boundaries, including what was accomplished, what changed, and what's next.

**Contents**: Deliverables produced, decisions made, open items, recommended next phase

---

## Quality Concepts

### Fresh-Machine Test
**Definition**: Validation that code/documentation works on a clean environment without implicit dependencies on the author's setup.

**Application**: Examples must run, procedures must execute, from a fresh starting point.

---

### Acid Test
**Definition**: A specific, measurable validation that proves an initiative achieved its goals. Often used for documentation initiatives.

**Characteristics**:
- Concrete scenario (not abstract)
- Measurable outcome (time, success rate)
- Tests the real goal, not proxies

**Example**: "New developer completes first successful API call in under 5 minutes using only the documentation."

---

### Backward Compatibility
**Definition**: Constraint that existing interfaces, behaviors, or contracts must continue to work after changes.

**Application**: New parameters must be optional with sensible defaults. Existing method signatures must not change.

---

## Anti-Patterns

### Rubber-Stamp Approval
**Definition**: Approving artifacts without genuine validation. Passing quality gates without checking criteria.

**Impact**: Low-quality work propagates downstream, causing expensive rework.

---

### Analysis Paralysis
**Definition**: Endless scoping and planning without reaching a Go/No-Go decision.

**Mitigation**: Timebox Prompt -1, accept uncertainty, use spikes for high-risk unknowns.

---

### Premature Implementation
**Definition**: Writing code before requirements and design are understood.

**Impact**: Building the wrong thing, rework, scope creep.

---

### Documentation Theater
**Definition**: Creating documents to satisfy process rather than to enable success.

**Detection**: Documents that no one reads or references.

**Mitigation**: Every document should have a clear consumer and purpose.

---

### Footgun Framing
**Definition**: Documentation that emphasizes what NOT to do rather than what TO do.

**Impact**: Makes users feel stupid, doesn't teach the right patterns.

**Better Approach**: Lead with the correct pattern, explain why it's correct.

---

## Workflow Principles

### The 10x Principle
**Definition**: Well-structured agentic workflows can achieve 10x productivity by:
- Preventing rework through clear requirements
- Right-sizing effort to complexity
- Parallelizing where possible
- Catching issues early through quality gates

---

### Specialist Sovereignty
**Definition**: Each specialist agent has authority over their domain. The orchestrator delegates decisions within scope, not just tasks.

**Application**: Architect decides architecture, Engineer decides implementation details, QA decides test strategy.

---

### Explicit Over Implicit
**Definition**: State assumptions, boundaries, and decisions explicitly rather than relying on shared understanding.

**Application**: Define scope IN and OUT, document decisions in ADRs, surface open questions.

---

### Reference, Don't Duplicate
**Definition**: Information should exist in exactly one canonical location. Other documents should link to it.

**Application**: PRD defines requirements (reference from TDD). TDD defines design (reference from implementation). ADR explains decision (reference from everywhere).

---

## Note on Technical Glossary

This glossary defines **workflow process terms** (agents, phases, artifacts, decision concepts).

For **project-specific technical terms** (API clients, caching, event systems, data models), see `GLOSSARY.md` in the repository root.
