---
name: initiative-scoping
description: "Session -1 and Session 0 protocols for initiative kickoff. Use when: starting new projects, scoping major initiatives, initializing the Orchestrator. Triggers: session -1, session 0, prompt -1, prompt 0, initiative scoping, project kickoff, new project, major initiative, initialization."
status: complete
---

# Initiative Scoping (Session -1/0)

> Protocols for the two initialization sessions that prepare the Orchestrator for execution.

## The Hierarchy

```
ORCHESTRATOR (subagent)     <-- Decision-maker, "north star" advisor
       |
       | advises/contextualizes
       v
MAIN AGENT (Claude)         <-- Simple invoker, ONLY job is prompting
       |
       | invokes with explicit skill instructions
       v
SPECIALIST SUBAGENTS        <-- Do the actual work
```

**Key principle**: The main agent is subordinate to subagents. Subagents make decisions; the main agent only prompts.

---

## Session Overview

| Session | Purpose | Main Agent Action | Orchestrator Action |
|---------|---------|-------------------|---------------------|
| **Session -1** | Assess readiness | Invoke Orchestrator with initiative | Assess Go/No-Go |
| **Session 0** | Plan execution | Invoke Orchestrator with context | Create delegation map |
| **Session 1+** | Execute work | Invoke specialists per delegation map | Coordinate, verify gates |

**Sessions -1 and 0 are pre-work** - just Orchestrator ingestion and context seeding. Real work begins in Session 1.

---

## Quick Decision Framework

| Scenario | Session -1? | Session 0? | Rationale |
|----------|-------------|------------|-----------|
| New feature (complex) | Yes | Yes | Full scoping validates readiness |
| New feature (simple) | No | Yes | Skip assessment, init orchestrator |
| Major refactoring | Yes | Yes | Risk assessment critical |
| Bug fix (isolated) | No | No | Direct implementation |
| Bug fix (cross-cutting) | Yes | Yes | Dependencies need validation |
| Exploration/spike | No | No | Direct implementation |

---

## Session Protocols

### Session -1: Initiative Assessment

**Main agent receives**: Initiative description from user

**Main agent does**: Invokes Orchestrator to assess readiness

**Orchestrator returns**:
- North Star (objective + success criteria)
- Go/No-Go recommendation
- Workflow sizing (which agents, what order)
- Blocking questions
- Risks/assumptions

**See**: [session-minus-1-protocol.md](session-minus-1-protocol.md)

### Session 0: Orchestrator Initialization

**Main agent receives**: Initiative context + Session -1 output (if available)

**Main agent does**: Invokes Orchestrator to create execution plan

**Orchestrator returns**:
- North Star (what "done" means)
- 10x Plan (phased approach with checkpoints)
- Delegation Map (agents + skills + artifacts)
- Blocking questions
- Risks/assumptions

**See**: [session-0-protocol.md](session-0-protocol.md)

---

## Skill Delegation Map

When invoking specialists in Session 1+, the main agent must specify which skills to use:

| Agent | Invoke With | Primary Skill | What They Produce |
|-------|-------------|---------------|-------------------|
| Requirements Analyst | `@requirements-analyst` | `documentation` | PRD |
| Architect | `@architect` | `documentation` | TDD, ADRs |
| Principal Engineer | `@principal-engineer` | `standards` | Code, tests |
| QA/Adversary | `@qa-adversary` | `documentation` | Test Plan, validation |

**Example invocation** (main agent to specialist):
```
Act as Requirements Analyst. Use the `documentation` skill for PRD template and quality gates.
Create PRD for: {feature description}
```

---

## Flow Diagram

```
User provides initiative
         |
         v
+------------------+
| Session -1       |  Main Agent invokes Orchestrator
| (Assessment)     |  Orchestrator: "Should we do this?"
+------------------+  Output: Go/No-Go + conditions
         |
         v
+------------------+
| Session 0        |  Main Agent invokes Orchestrator
| (Initialization) |  Orchestrator: "How will we do this?"
+------------------+  Output: Delegation Map + plan
         |
         v
+------------------+
| Session 1+       |  Main Agent invokes specialists
| (Execution)      |  per delegation map with skill instructions
+------------------+
```

---

## What the Main Agent Does NOT Do

- Make decisions about workflow (Orchestrator decides)
- Fill out templates (specialists do)
- Choose which agents to invoke (Orchestrator's delegation map)
- Repeat workflow definitions (reference `10x-workflow` skill)
- Do implementation work (specialists do)

The main agent's **only skill is `prompting`** - it invokes subagents with clear context.

---

## Related Skills

- [10x-workflow](../10x-workflow/SKILL.md) - Defines the workflow (do not repeat)
- [documentation](../documentation/SKILL.md) - Templates for specialists
- [prompting](../prompting/SKILL.md) - Agent invocation patterns
- [standards](../standards/SKILL.md) - Code conventions for Principal Engineer

---

## Legacy Templates

For heavyweight Prompt -1/0 documents (user-authored initiative context):
- [prompt-minus-1.md](prompt-minus-1.md) - Detailed scoping template
- [prompt-0.md](prompt-0.md) - Detailed initialization template

These are **optional input formats** the user may provide. The protocols above define what the main agent does with that input.
