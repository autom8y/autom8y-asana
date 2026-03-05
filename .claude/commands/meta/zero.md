---
name: zero
description: Initialize Orchestrator with 4-agent workflow plan
argument-hint: <initiative>
model: opus
disable-model-invocation: true
allowed-tools: Task, Read
context: fork
---

# Session 0: Orchestrator Initialization

You are a **prompter**. Your only skill is `prompting`. Do not make decisions—invoke the Orchestrator.

**Your action**: Immediately invoke the `orchestrator` subagent with this task:

---

Initialize for the 4-agent workflow. Use these skills by reference (do not repeat content):
- `10x-workflow` for workflow and quality gates
- `documentation` for artifact templates

**Initiative**: `$ARGUMENTS`

**Return**:
1. **North Star**: What "done" means (1-3 sentences)
2. **10x Plan**: Phased approach with checkpoints aligned to `10x-workflow`
3. **Delegation Map**:
    | Phase | Agent | Skill to Use | Artifact |
    |-------|-------|--------------|----------|
    | 1 | requirements-analyst | `documentation` | PRD |
    | 2 | architect | `documentation` | TDD |
    | ... | ... | ... | ... |
4. **Blocking Questions**: Only what must be answered before Session 1
5. **Risks/Assumptions**: Failure modes to watch

---

Return the Orchestrator's plan verbatim. Ask: "Shall I proceed to Session 1?"
