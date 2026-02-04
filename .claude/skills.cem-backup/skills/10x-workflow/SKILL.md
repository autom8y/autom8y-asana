---
name: 10x-workflow
description: "10x agentic workflow coordination. Use when: routing work between agents, understanding PRD-TDD-Code pipeline, coordinating handoffs, applying workflow rules, managing quality gates. Triggers: workflow, agent coordination, handoff, pipeline, phase transition, orchestration, sequential workflow, feedback loops."
---

# 10x Agentic Workflow

> **Status**: Complete (Session 3)

## Protocol Overview

The 10x Agentic Workflow achieves 10x productivity through specialized AI agents coordinated by an orchestrator:

- **Early clarity** - Requirements and scope validated before implementation
- **Right-sized effort** - Complexity calibrated to actual need
- **Quality gates** - Issues caught before they propagate
- **Specialist sovereignty** - Decisions made by the appropriate expert
- **Adaptive planning** - Plans adjusted based on discoveries

---

## Agent Routing

### Quick Reference

| Agent | Domain Authority | Primary Artifact |
|-------|------------------|------------------|
| **Requirements Analyst** | Scope definition, acceptance criteria | PRD |
| **Architect** | System design, technology selection | TDD, ADRs |
| **Principal Engineer** | Implementation approach, code structure | Code, tests |
| **QA/Adversary** | Test strategy, validation, release readiness | Test Plan |
| **Orchestrator** | Session planning, quality gates, adaptive routing | (Coordinates) |

### When to Route

**By Signal**:

| Request | Likely Agent |
|---------|--------------|
| "What should we build?" | Requirements Analyst |
| "How should we build it?" | Architect |
| "Build it" | Principal Engineer |
| "Does it work?" | QA/Adversary |

**By Complexity**:

| Complexity | Typical Pattern |
|------------|-----------------|
| Script (single file) | Engineer -> QA |
| Module (multiple files) | Analyst -> Engineer -> QA |
| Service (multiple modules) | Full 4-agent workflow |
| Platform (multiple services) | Extended workflow with iterations |

---

## Session Protocol

Every session follows **PLAN -> CLARIFY -> EXECUTE -> VERIFY -> HANDOFF**:

1. **PLAN** (Orchestrator): Define goal, prerequisites, deliverables, quality gate
2. **CLARIFY** (Orchestrator + User): Surface ambiguities, get confirmation
3. **EXECUTE** (Specialist): Plan approach, execute work, document decisions
4. **VERIFY** (Orchestrator): Check quality gate, confirm handoff readiness
5. **HANDOFF** (Orchestrator): Summarize outcomes, identify next inputs

**Critical Rule**: Never execute without explicit user confirmation ("Proceed with the plan").

See [lifecycle.md](lifecycle.md) for detailed session protocol with checklists.

---

## Quality Gates Summary

Quality gates are mandatory checkpoints between phases:

- **PRD**: Problem clear, scope defined, requirements testable, acceptance criteria present
- **TDD**: Traces to PRD, decisions have ADRs, interfaces defined, complexity justified
- **Implementation**: Satisfies TDD, tests pass, type-safe, readable, documented
- **Validation**: Acceptance criteria met, edge cases covered, failures handled, production ready

See [quality-gates.md](quality-gates.md) for complete criteria and workflow integration.

---

## Progressive Disclosure

**For complete operational reference**:

- [lifecycle.md](lifecycle.md) - Full workflow lifecycle, role definitions, communication patterns, problem resolution
- [quality-gates.md](quality-gates.md) - Detailed gate criteria, cross-references to artifact templates

**Glossary (Domain-Specific)**:
- [glossary-index.md](glossary-index.md) - Quick navigation to all workflow terms
- [glossary-agents.md](glossary-agents.md) - Agent roles, artifacts, communication
- [glossary-process.md](glossary-process.md) - Workflow phases, concepts, decisions
- [glossary-quality.md](glossary-quality.md) - Quality concepts, anti-patterns, principles

**Related skills**:

- [documentation](../documentation/SKILL.md) - PRD/TDD/ADR/Test Plan templates and formats
- [initiative-scoping](../initiative-scoping/SKILL.md) - Prompt -1 and Prompt 0 creation
- [prompting](../prompting/SKILL.md) - Copy-paste prompt patterns for agent invocation
- [consult-ref](../consult-ref/skill.md) - Ecosystem navigation and guidance
- [team-development](../team-development/SKILL.md) - Creating new team packs

> **Note**: When modifying workflows or agents, update the Consultant knowledge base at `.claude/knowledge/consultant/` to keep `/consult` guidance accurate. See [consultant-sync.md](../team-development/patterns/consultant-sync.md).

**Agent configurations**: See `.claude/agents/` for full agent prompts:
- [orchestrator.md](../../agents/orchestrator.md)
- [requirements-analyst.md](../../agents/requirements-analyst.md)
- [architect.md](../../agents/architect.md)
- [principal-engineer.md](../../agents/principal-engineer.md)
- [qa-adversary.md](../../agents/qa-adversary.md)

---

## Project Glossary

This skill defines **workflow process terms** (agents, phases, artifacts). For **project-specific domain terminology**, create a project glossary file only when you have terms Claude wouldn't know (e.g., business domain entities, product-specific concepts, or non-standard terminology).
