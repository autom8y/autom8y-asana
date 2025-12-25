# Session -1 Protocol: Initiative Scoping

> **Purpose**: Ingest a new initiative and have the Orchestrator assess readiness for the 4-agent workflow.

---

## What This Session Does

Session -1 is **context ingestion only**. The main agent:
1. Receives an initiative description from the user
2. Immediately invokes the Orchestrator to assess it
3. Returns the Orchestrator's guidance to the user
4. Takes no other significant action

**No implementation, no planning, no artifacts** - just Orchestrator assessment.

---

## Main Agent Protocol

You are a **prompter**, not a decision-maker. Your only skill is `prompting`. When the user provides an initiative for Session -1:

### Step 1: Acknowledge Receipt

```
I've received your initiative description. Let me invoke the Orchestrator to assess readiness for the 4-agent workflow.
```

### Step 2: Invoke Orchestrator

Use the Task tool to invoke `@orchestrator` with this prompt:

```markdown
## Session -1: Initiative Assessment

**Your Task**: Assess whether this initiative is ready for the 4-agent workflow.

### Initiative to Assess

{PASTE USER'S INITIATIVE DESCRIPTION HERE}

### Your Assessment Should Include

Using the `10x-workflow` skill for workflow reference:

1. **North Star**: 1-3 sentences describing what this initiative achieves and what success looks like.

2. **Go/No-Go Assessment**:
   - Is the problem validated?
   - Is scope bounded?
   - Are there blocking dependencies?
   - What's the complexity level? (Script / Module / Service / Platform)
   - Recommendation: GO / CONDITIONAL GO / NO-GO

3. **If GO or CONDITIONAL GO**:
   - Which agents are needed and in what order?
   - What's the right-sized workflow for this complexity?
   - What context should be gathered before Session 0?

4. **Blocking Questions**: Only what must be answered before proceeding.

5. **Risks/Assumptions**: Key assumptions that could invalidate the plan.

**Output Format**: Structured assessment that can seed Session 0.
```

### Step 3: Return Guidance

Present the Orchestrator's assessment to the user verbatim. Ask if they want to:
- Proceed to Session 0 (if GO)
- Address conditions (if CONDITIONAL GO)
- Resolve blockers (if NO-GO)

---

## What Session -1 Produces

The Orchestrator returns guidance that includes:

| Output | Purpose |
|--------|---------|
| **North Star** | Session objective and success criteria |
| **Go/No-Go** | Whether to proceed to Session 0 |
| **Workflow Sizing** | Which agents, in what order |
| **Blocking Questions** | What must be answered first |
| **Risks/Assumptions** | Failure modes to watch |

This output becomes **input context for Session 0**.

---

## When to Use Session -1

| Scenario | Use Session -1? |
|----------|-----------------|
| New feature (complex) | Yes |
| Major refactoring | Yes |
| Cross-cutting changes | Yes |
| Simple bug fix | No - go direct to implementation |
| Exploration/spike | No - go direct to implementation |
| Already validated scope | No - go direct to Session 0 |

---

## Flow

```
User provides initiative description
         |
         v
Main Agent acknowledges, invokes Orchestrator
         |
         v
Orchestrator assesses using 10x-workflow skill
         |
         v
Main Agent returns assessment to user
         |
         v
User decides: Proceed to Session 0 / Address conditions / Resolve blockers
```

---

## Key Principles

1. **Main agent does NOT make decisions** - Orchestrator makes all assessments
2. **Main agent does NOT fill out templates** - just passes context to Orchestrator
3. **This session is lightweight** - ingestion and assessment only
4. **The `10x-workflow` skill defines the workflow** - don't repeat it here
5. **Output seeds Session 0** - this is preparation, not execution
