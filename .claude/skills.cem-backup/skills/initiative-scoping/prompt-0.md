# Prompt 0 Template

> **Purpose**: Initialize the Orchestrator with full context to coordinate the 4-agent workflow. This template provides the structure for a comprehensive kickoff prompt.

---

# Orchestrator Initialization: {PROJECT_NAME} {INITIATIVE_TYPE}

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`documentation`** — PRD/TDD/ADR templates, workflow pipeline, quality gates
  - Activates when: Creating/reviewing PRD, TDD, ADR, or Test Plan

- **`standards`** — Tech stack decisions, code conventions, repository structure
  - Activates when: Writing code, choosing libraries, organizing files

- **`10x-workflow`** — Agent coordination, session protocol, quality gates
  - Activates when: Planning phases, coordinating handoffs, checking quality criteria

- **`prompting`** — Agent invocation patterns, workflow examples
  - Activates when: Invoking agents, structuring prompts

**How Skills Work**: Skills load automatically based on your current task. You do not need to read or load them manually. When you need template formats, the `documentation` skill activates. When you need coding conventions, the `standards` skill activates. This enables focused context for each task instead of loading everything upfront.

## Your Role: Orchestrator

You coordinate a 4-agent development workflow. You plan, delegate, coordinate, and verify—you do not implement directly.

## Your Specialist Agents

| Agent | Invocation | Responsibility |
|-------|------------|----------------|
| **Requirements Analyst** | `@requirements-analyst` | Requirements definition, acceptance criteria, scope boundaries |
| **Architect** | `@architect` | TDDs, ADRs, system design, trade-off analysis |
| **Principal Engineer** | `@principal-engineer` | Implementation, code quality, technical execution |
| **QA/Adversary** | `@qa-adversary` | Validation, failure mode testing, security/quality review |

## The Mission: {ONE_SENTENCE_OBJECTIVE}

{2-3 sentences: What are we building/fixing/improving? Why does it matter? What's the expected outcome?}

### Why This Initiative?

- **{Benefit 1}**: {Brief explanation}
- **{Benefit 2}**: {Brief explanation}
- **{Benefit 3}**: {Brief explanation}
- **{Benefit 4}**: {Brief explanation}

### Current State

**{Component/System} (Status)**:
- {Current capability or state item 1}
- {Current capability or state item 2}
- {Current capability or state item 3}
- {Current capability or state item 4}

**{Baseline/Foundation}**:
- {Existing foundation element 1}
- {Existing foundation element 2}
- {Existing foundation element 3}
- {Existing foundation element 4}

**What's Missing**:


```

# This is what we need to enable:

{command/action 1} {command/action 2} {command/action 3}

# Result: {Desired end state with:

# - Key outcome 1

# - Key outcome 2

# - Key outcome 3

# - Key outcome 4

```

### {Component/System} Profile

| Attribute | Value |
|-----------|-------|
| {Attribute 1} | {Value} |
| {Attribute 2} | {Value} |
| {Attribute 3} | {Value} |
| {Attribute 4} | {Value} |
| {Attribute 5} | {Value} |
| {Attribute 6} | {Value} |

### Target Architecture


```

{ASCII diagram or description of target state} {Component A} → {Component B} → {Component C} → {Component D} → {Component E}

```

### Key Constraints

- {Constraint 1 with brief rationale}
- {Constraint 2 with brief rationale}
- {Constraint 3 with brief rationale}
- {Constraint 4 with brief rationale}
- {Constraint 5 with brief rationale}
- {Constraint 6 with brief rationale}

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| {Requirement 1} | Must |
| {Requirement 2} | Must |
| {Requirement 3} | Must |
| {Requirement 4} | Must |
| {Requirement 5} | Must |
| {Requirement 6} | Must |
| {Requirement 7} | Should |
| {Requirement 8} | Should |
| {Requirement 9} | Should |

### Success Criteria

1. {Measurable outcome 1}
2. {Measurable outcome 2}
3. {Measurable outcome 3}
4. {Measurable outcome 4}
5. {Measurable outcome 5}
6. {Measurable outcome 6}
7. {Measurable outcome 7}
8. {Measurable outcome 8}

### Performance Targets

| Metric | {Environment 1} | {Environment 2} |
|--------|-----------------|-----------------|
| {Metric 1} | {Value} | {Value} |
| {Metric 2} | {Value} | {Value} |
| {Metric 3} | {Value} | {Value} |
| {Metric 4} | {Value} | {Value} |
| {Metric 5} | {Value} | {Value} |

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | {Analysis artifact with scope understanding} |
| **2: Requirements** | Requirements Analyst | PRD-{IDENTIFIER} with acceptance criteria |
| **3: Architecture** | Architect | TDD-{IDENTIFIER} + ADRs for key decisions |
| **4: Implementation P1** | Principal Engineer | {Core components/modules} |
| **5: Implementation P2** | Principal Engineer | {Supporting components/integration} |
| **6: Implementation P3** | Principal Engineer | {Final components/automation} |
| **7: Validation** | QA/Adversary | Validation report, failure mode testing, quality review |

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rule**: Never execute without explicit confirmation.

## Discovery Phase: What Must Be Explored

Before requirements can be finalized, the **Requirements Analyst** must explore:

### {Component/Codebase} Analysis

| File/Area | Questions to Answer |
|-----------|---------------------|
| `{path/to/file1}` | {What do we need to understand about this?} |
| `{path/to/file2}` | {What patterns/dependencies exist?} |
| `{path/to/file3}` | {What configuration/behavior is relevant?} |
| {Concept/Feature} | {What implementation details matter?} |

### {External System/Dependency} Audit

| Resource/System | Questions to Answer |
|-----------------|---------------------|
| {System 1} | {What exists? How is it configured?} |
| {System 2} | {What's the current state? What needs to change?} |
| {System 3} | {What dependencies exist? What's the integration pattern?} |
| {System 4} | {What credentials/access is needed?} |
| {System 5} | {What conventions/standards apply?} |
| {System 6} | {What existing patterns should be followed?} |

### {Domain Area} Gap Analysis

| Area | Questions |
|------|-----------|
| {Domain 1} | {What's missing? What needs creation vs modification?} |
| {Domain 2} | {What dependencies exist? What's blocked?} |
| {Domain 3} | {What constraints apply? What's the current state?} |
| {Domain 4} | {What conventions exist? What's the standard?} |

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins, the following questions need answers:

### {Category 1} Questions

1. **{Question about decision/pattern}**: {Specific choice that needs to be made}
2. **{Question about behavior}**: {Clarification needed on expected behavior}
3. **{Question about timing/scope}**: {Boundary or timing question}
4. **{Question about metrics}**: {Measurement or sizing question}

### {Category 2} Questions

5. **{Question about strategy}**: {Approach or pattern decision}
6. **{Question about dependencies}**: {Integration or dependency question}
7. **{Question about existing systems}**: {Reuse vs rebuild decision}
8. **{Question about scope}**: {Boundary or naming question}

### {Category 3} Questions

9. **{Question about operations}**: {Runtime or operational question}
10. **{Question about quality}**: {Standard or threshold question}
11. **{Question about process}**: {Workflow or approval question}

## Your First Task

Confirm understanding by:

1. Summarizing the {initiative type} goal in 2-3 sentences
2. Listing the 7 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step before requirements
4. Confirming which {files/systems/areas} must be analyzed before PRD-{IDENTIFIER}
5. Listing which open questions you need answered before Session 2

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

# Session Trigger Prompts

## Session 1: Discovery

```markdown
Begin Session 1: {System/Codebase/Context} Discovery

Work with the @requirements-analyst agent to analyze {the system/codebase/context} and audit existing {dependencies/integrations/state}.

**Goals:**
1. {Discovery goal 1}
2. {Discovery goal 2}
3. {Discovery goal 3}
4. {Discovery goal 4}
5. {Discovery goal 5}
6. {Discovery goal 6}
7. {Discovery goal 7}

**{Artifacts} to Analyze:**
- `{path/to/artifact1}` — {What to look for}
- `{path/to/artifact2}` — {What to understand}
- `{path/to/artifact3}` — {What to document}
- {Other sources of information}

**{External Systems/Dependencies} to Audit:**
- {System/dependency 1}
- {System/dependency 2}
- {System/dependency 3}
- {System/dependency 4}
- {System/dependency 5}
- {System/dependency 6}

**Deliverable:**
A discovery document with:
- {Discovery output 1}
- {Discovery output 2}
- {Discovery output 3}
- {Discovery output 4}
- {Discovery output 5}
- {Discovery output 6}

Create the analysis plan first. I'll review before you execute.

```

## Session 2: Requirements

```markdown
Begin Session 2: {Domain} Requirements Definition

Work with the @requirements-analyst agent to create PRD-{IDENTIFIER}.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Define {requirement category 1}
2. Define {requirement category 2}
3. Define {requirement category 3}
4. Define {requirement category 4}
5. Define {requirement category 5}
6. Define {requirement category 6}
7. Define acceptance criteria for each {component/feature}

**Key Questions to Address:**
- {Strategic question 1}
- {Strategic question 2}
- {Strategic question 3}
- {Strategic question 4}

**PRD Organization:**
- FR-{CATEGORY1}-*: {Description of requirement type}
- FR-{CATEGORY2}-*: {Description of requirement type}
- FR-{CATEGORY3}-*: {Description of requirement type}
- FR-{CATEGORY4}-*: {Description of requirement type}
- FR-{CATEGORY5}-*: {Description of requirement type}
- FR-{CATEGORY6}-*: {Description of requirement type}
- NFR-*: Performance, {quality attribute}, {quality attribute} requirements

Create the plan first. I'll review before you execute.

```

## Session 3: Architecture

```markdown
Begin Session 3: {System} Architecture Design

Work with the @architect agent to create TDD-{IDENTIFIER} and foundational ADRs.

**Prerequisites:**
- PRD-{IDENTIFIER} approved

**Goals:**
1. Design {architecture component 1}
2. Design {architecture component 2}
3. Design {architecture component 3}
4. Design {architecture component 4}
5. Design {architecture component 5}
6. Design {module/package structure}
7. Design {automation/integration strategy}

**Required ADRs:**
- ADR-{NNN1}: {Decision area 1}
- ADR-{NNN2}: {Decision area 2}
- ADR-{NNN3}: {Decision area 3}
- ADR-{NNN4}: {Decision area 4}
- ADR-{NNN5}: {Decision area 5}
- ADR-{NNN6}: {Decision area 6}

**{Structure Type} to Consider:**


```

{root}/ ├── {artifact1} ├── {structure1}/ │ ├── {file1} │ ├── {file2} │ ├── {file3} │ ├── {substructure}/ │ │ ├── {module1}/ │ │ ├── {module2}/ │ │ ├── {module3}/ │ │ └── {module4}/ │ └── {substructure2}/ │ ├── {config1} │ └── {config2} └── {structure2}/ └── {artifact2}

```

Create the plan first. I'll review before you execute.

```

## Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - {Core Components}

Work with the @principal-engineer agent to implement foundational components.

**Prerequisites:**
- PRD-{IDENTIFIER} approved
- TDD-{IDENTIFIER} approved
- ADRs documented

**Phase 1 Scope:**
1. {Implementation item 1}
2. {Implementation item 2}
3. {Implementation item 3}
4. {Implementation item 4}
5. {Implementation item 5}
6. {Implementation item 6}

**Hard Constraints:**
- {Constraint 1}
- {Constraint 2}
- {Constraint 3}
- {Constraint 4}

**Explicitly OUT of Phase 1:**
- {Deferred item 1} (Phase 2)
- {Deferred item 2} (Phase 2)
- {Deferred item 3} (Phase 2)
- {Deferred item 4} (Phase 3)

Create the plan first. I'll review before you execute.

```

## Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - {Supporting Components}

Work with the @principal-engineer agent to complete {system/feature}.

**Prerequisites:**
- Phase 1 complete and tested

**Phase 2 Scope:**
1. {Implementation item 1}
2. {Implementation item 2}
3. {Implementation item 3}
4. {Implementation item 4}
5. {Implementation item 5}
6. {Implementation item 6}

**Integration Points:**
- {Integration requirement 1}
- {Integration requirement 2}
- {Integration requirement 3}

Create the plan first. I'll review before you execute.

```

## Session 6: Implementation Phase 3

```markdown
Begin Session 6: Implementation Phase 3 - {Final Components/Automation}

Work with the @principal-engineer agent to implement {final scope area}.

**Prerequisites:**
- Phase 2 complete and tested

**Phase 3 Scope:**
1. {Implementation item 1}
2. {Implementation item 2}
3. {Implementation item 3}
4. {Implementation item 4}
5. {Implementation item 5}
6. {Implementation item 6}
7. {Implementation item 7}

**{Structure/Workflow} Structure:**


```

{structure description}

{stages}: {stage1}: # {Description} {stage2}: # {Description} {stage3}: # {Description} {stage4}: # {Description} {stage5}: # {Description}

```

Create the plan first. I'll review before you execute.

```

## Session 7: Validation

```markdown
Begin Session 7: {System/Feature} Validation

Work with the @qa-adversary agent to validate the {implementation/system}.

**Prerequisites:**
- All implementation phases complete
- {System} deployed to {environment}

**Goals:**

**Part 1: Functional Validation**
- {Validation item 1}
- {Validation item 2}
- {Validation item 3}
- {Validation item 4}
- {Validation item 5}

**Part 2: Failure Mode Testing**
- {Failure scenario 1} → {Expected behavior}
- {Failure scenario 2} → {Expected behavior}
- {Failure scenario 3} → {Expected behavior}
- {Failure scenario 4} → {Expected behavior}
- {Failure scenario 5} → {Expected behavior}

**Part 3: {Quality Attribute} Validation**
- {Quality check 1}
- {Quality check 2}
- {Quality check 3}
- {Quality check 4}

**Part 4: Operational Readiness**
- {Operational check 1}
- {Operational check 2}
- {Operational check 3}
- {Operational check 4}

Create the plan first. I'll review before you execute.

```

----------

# Context Gathering Checklist

Before starting, gather:

**{Context Category 1}:**

-   [ ] `{artifact/file 1}` — {What we need from it}
-   [ ] `{artifact/file 2}` — {What we need from it}
-   [ ] `{artifact/file 3}` — {What we need from it}
-   [ ] {Other information needed}

**{Context Category 2}:**

-   [ ] {Information item 1}
-   [ ] {Information item 2}
-   [ ] {Information item 3}
-   [ ] {Information item 4}
-   [ ] {Information item 5}
-   [ ] {Information item 6}
-   [ ] {Information item 7}
-   [ ] {Information item 8}

**{Context Category 3}:**

-   [ ] {Information item 1}
-   [ ] {Information item 2}
-   [ ] {Information item 3}
-   [ ] {Information item 4}

**{Context Category 4}:**

-   [ ] {Information item 1}
-   [ ] {Information item 2}
-   [ ] {Information item 3}
-   [ ] {Information item 4}
