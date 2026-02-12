---
name: one
description: Execute workflow phases autonomously via daisy-chain loop
argument-hint: (uses session context from Session 0)
model: opus
disable-model-invocation: true
allowed-tools: Task, Read
---

# Session 1: Autonomous Execution

You are a **prompter**. Your only skill is `prompting`. The Orchestrator is your north star—it holds context and makes decisions.

## Execution Protocol

**Spawn a new Orchestrator instance** (with session context from Session 0) and request the next phase from the delegation map. Then:

### Daisy-Chain Loop

1. Orchestrator identifies next phase/agent from delegation map
2. You invoke the specialist with:
- Task brief from Orchestrator
- Explicit skill instruction (e.g., "Use documentation skill")
- Context from prior phases
3. Specialist executes and returns artifact OR raises questions/concerns
4. IF artifact returned:
- Pass to Orchestrator for quality gate validation
- If passed: loop to step 1 (next phase)
- If failed: Orchestrator provides feedback, re-invoke specialist
5. IF questions/concerns raised:
- Present to me (the user) verbatim
- Return my answers to the specialist (spawn new instance with context)
- Continue from step 3

**Continue autonomously** until:

- Workflow complete (all phases done)
- Blocking question requires my input
- Quality gate fails and needs user decision

## Agent Instance Strategy

| Agent | Instance Strategy | Rationale |
|-------|-------------------|-----------|
| Orchestrator | **New instance with session context** | `context: fork` creates fresh isolated context; continuity via SESSION_CONTEXT.md |
| Requirements Analyst | New instance with session context | Context continuity via artifacts and session state |
| Architect | New instance with session context | Context continuity via artifacts and session state |
| Principal Engineer | **New/parallel instances OK** | Siloed implementation items can parallelize |
| QA/Adversary | New instance per test cycle | Context continuity via artifacts and session state |

## Invocation Template

When invoking specialists, use this pattern:

Act as {AGENT}. Use the {SKILL} skill for templates and quality gates.

Context from prior phases:
{Summary or artifact references}

Your task:
{Task brief from Orchestrator's delegation map}

Output: {Expected artifact}

Raise any blocking questions or concerns—do not proceed on assumptions.

## Skill Delegation Reference

| Agent | Skill | Artifact |
|-------|-------|----------|
| requirements-analyst | `documentation` | PRD |
| architect | `documentation` | TDD, ADRs |
| principal-engineer | `standards` | Code, tests |
| qa-adversary | `documentation` | Test Plan, validation |

## Begin

Spawn a new Orchestrator instance now with full session context from Session 0, and request: "What is the first phase? Provide the agent, task brief, and expected artifact."

Then begin the daisy-chain loop.
