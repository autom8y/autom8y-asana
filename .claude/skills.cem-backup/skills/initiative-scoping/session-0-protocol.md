# Session 0 Protocol: Execution Readiness

> **Purpose**: Initialize the Orchestrator with full context so it can coordinate the 4-agent workflow starting in Session 1.

---

## What This Session Does

Session 0 is **Orchestrator initialization**. The main agent:
1. Receives initiative context (ideally including Session -1 output)
2. Invokes the Orchestrator to internalize context and create an execution plan
3. Returns the Orchestrator's plan to the user
4. Takes no other significant action

**No implementation, no agent work** - just Orchestrator planning.

---

## Main Agent Protocol

You are a **prompter**, not a decision-maker. Your only skill is `prompting`. When the user provides context for Session 0:

### Step 1: Acknowledge Receipt

```
I've received the initiative context. Let me invoke the Orchestrator to create an execution plan for the 4-agent workflow.
```

### Step 2: Invoke Orchestrator

Use the Task tool to invoke `@orchestrator` with this prompt:

```markdown
## Session 0: Orchestrator Initialization

**Your Task**: Internalize this initiative and prepare to coordinate the 4-agent workflow.

### Initiative Context

{PASTE SESSION -1 OUTPUT AND/OR USER'S INITIATIVE CONTEXT HERE}

### Skills Available to You

Reference these skills as needed - do not repeat their content:
- **`10x-workflow`** - Agent routing, session protocol, quality gates
- **`documentation`** - PRD/TDD/ADR/Test Plan templates
- **`prompting`** - Agent invocation patterns

### Your Initialization Output

1. **North Star**: 1-3 sentences describing the session objective and what "done" means.

2. **10x Plan**: A stepwise plan aligned to the `10x-workflow`, with:
   - Which agents to invoke, in what order
   - What each agent will produce
   - Quality gates between phases
   - Checkpoints for user confirmation

3. **Delegation Map**: For each agent invocation, specify:
   - Agent to invoke
   - Task brief (what they're doing)
   - Skills they should use (from: `documentation`, `standards`)
   - Expected artifact

4. **Blocking Questions**: Only what must be answered before Session 1 begins.

5. **Risks/Assumptions**: Key assumptions and failure modes to watch.

**Output Format**: Structured plan that enables Session 1 to begin immediately.
```

### Step 3: Return Plan

Present the Orchestrator's plan to the user verbatim. Ask for confirmation:
- "Shall I proceed to Session 1?"
- Surface any blocking questions the Orchestrator identified

---

## Delegation Map Reference

When the Orchestrator creates the delegation map, it should specify skill usage:

| Agent | Primary Skill | For |
|-------|---------------|-----|
| Requirements Analyst | `documentation` | PRD template, quality gates |
| Architect | `documentation` | TDD/ADR templates, quality gates |
| Principal Engineer | `standards` | Code conventions, tech stack |
| QA/Adversary | `documentation` | Test Plan template, quality gates |

The main agent will include these skill instructions when invoking each subagent in Session 1+.

---

## What Session 0 Produces

The Orchestrator returns a plan that includes:

| Output | Purpose |
|--------|---------|
| **North Star** | Clear success criteria |
| **10x Plan** | Phased approach with checkpoints |
| **Delegation Map** | Which agents, with what skills, producing what |
| **Blocking Questions** | What user must answer first |
| **Risks/Assumptions** | Watch points during execution |

This output **enables Session 1 to begin**.

---

## Session -1 vs Session 0

| Aspect | Session -1 | Session 0 |
|--------|------------|-----------|
| **Question answered** | "Should we do this?" | "How will we do this?" |
| **Orchestrator task** | Assess readiness | Plan execution |
| **Output** | Go/No-Go + conditions | Execution plan + delegation map |
| **When to skip** | Simple/validated scope | Never (always initialize) |

---

## Flow

```
User provides initiative context (+ Session -1 output if available)
         |
         v
Main Agent acknowledges, invokes Orchestrator
         |
         v
Orchestrator plans using 10x-workflow skill
         |
         v
Main Agent returns plan to user
         |
         v
User confirms: "Proceed to Session 1"
         |
         v
Session 1 begins (real work starts)
```

---

## Key Principles

1. **Main agent does NOT create the plan** - Orchestrator creates it
2. **Main agent does NOT decide workflow** - references `10x-workflow` skill
3. **This session produces a plan, not artifacts** - execution begins in Session 1
4. **Delegation map includes skill instructions** - main agent uses this when invoking agents
5. **User confirmation required** - never start Session 1 without explicit approval
