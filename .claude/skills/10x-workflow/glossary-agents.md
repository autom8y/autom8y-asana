# Glossary: Agents & Artifacts

> Agent roles, documentation artifacts, communication patterns

**Other Domains**: [Process & Workflow](glossary-process.md) | [Quality & Principles](glossary-quality.md) | [Index](glossary-index.md)

---

## Agents & Roles

### Pythia
**Definition**: The coordinating agent that plans, delegates, coordinates, and verifies. Does not implement directly. Acts as a dispatcher routing work to specialist agents.

**Core Responsibilities**:
1. **Assess**: Determine complexity and required agents
2. **Plan**: Create phased approach with clear deliverables
3. **Delegate**: Invoke specialist agents with full context
4. **Verify**: Confirm quality gates before phase transitions
5. **Adapt**: Adjust plans based on discoveries

**Key Principle**: Pythia's judgment determines agent routing, session ordering, and workflow adaptation. It should not be over-prescribed by Prompt 0.

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

**Location**: `.ledge/specs/PRD-{NNNN}-{slug}.md`

**Key Sections**: Problem Statement, Scope (In/Out), Functional Requirements, Acceptance Criteria

---

### TDD (Technical Design Document)
**Definition**: Defines HOW we're building it from a technical perspective. Contains architecture, components, interfaces, and data flow.

**Owner**: Architect

**Location**: `.ledge/specs/TDD-{NNNN}-{slug}.md`

**Key Sections**: Overview, Component Architecture, Data Model, API Contracts, Implementation Plan

---

### ADR (Architecture Decision Record)
**Definition**: Captures WHY a specific architectural decision was made. Provides context for future maintainers and enables informed evolution.

**Owner**: Architect (primary), Principal Engineer (implementation-level)

**Location**: `.ledge/decisions/ADR-{NNNN}-{slug}.md`

**Key Sections**: Context, Decision, Rationale, Alternatives Considered, Consequences

**When to Write**: Choosing between viable approaches, adopting new patterns, deviating from established conventions, making trade-offs with long-term implications.

---

### Test Plan
**Definition**: Defines HOW we validate the implementation meets requirements. Maps requirements to test cases with coverage tracking.

**Owner**: QA/Adversary

**Location**: `.ledge/specs/TP-{NNNN}-{slug}.md`

**Key Sections**: Test Scope, Requirements Traceability, Test Cases, Edge Cases, Exit Criteria

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

## Note on Technical Glossary

This glossary defines **workflow process terms** (agents, phases, artifacts, decision concepts).

For **project-specific domain terminology**, create a project glossary file only when you have terms Claude wouldn't know (e.g., business domain entities, product-specific concepts, or non-standard terminology).
