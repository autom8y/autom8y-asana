---
name: 10x-workflow
description: "10x workflow coordination and agent routing. Use when: understanding phase transitions, routing work to specialist agents, coordinating multi-agent pipelines. Triggers: workflow, agent coordination, handoff, pipeline, phase transition, orchestration."
---

# 10x Agentic Workflow

## Protocol Overview

Specialist agents coordinated by Pythia through four phases:
- **Early clarity** — Requirements and scope validated before implementation
- **Right-sized effort** — Complexity calibrated to actual need
- **Quality gates** — Issues caught before they propagate
- **Specialist sovereignty** — Decisions made by the appropriate expert

## Agent Pantheon

| Agent | Domain Authority | Primary Artifact |
|-------|------------------|------------------|
| **Requirements Analyst** | Scope definition, acceptance criteria | PRD |
| **Architect** | System design, technology selection | TDD, ADRs |
| **Principal Engineer** | Implementation approach, code structure | Code, tests |
| **QA/Adversary** | Test strategy, validation, release readiness | Test Plan |
| **Pythia** | Session planning, quality gates, adaptive routing | (Coordinates) |

## Routing Quick Reference

| Request | Likely Agent |
|---------|--------------|
| "What should we build?" | Requirements Analyst |
| "How should we build it?" | Architect |
| "Build it" | Principal Engineer |
| "Does it work?" | QA/Adversary |

## Session Protocol

Every session follows **PLAN -> CLARIFY -> EXECUTE -> VERIFY -> HANDOFF**.

**Critical Rule**: Never execute without explicit user confirmation ("Proceed with the plan").

## Quality Gates Summary

- **PRD**: Problem clear, scope defined, requirements testable, acceptance criteria present
- **TDD**: Traces to PRD, decisions have ADRs, interfaces defined, complexity justified
- **Implementation**: Satisfies TDD, tests pass, type-safe, readable, documented
- **Validation**: Acceptance criteria met, edge cases covered, failures handled, production ready

## Companion Reference

| Topic | File | When to Load |
|-------|------|-------------|
| Entry point selection by work type | `entry-points.lego.md` | Deciding where to start |
| Full session protocol with checklists | `lifecycle.md` | Running a session |
| Detailed quality gate criteria | `quality-gates.md` | Validating phase transitions |
| Glossary navigation | `glossary-index.md` | Looking up workflow terms |

## Related Skills

- `doc-artifacts` skill — PRD/TDD/ADR/Test Plan templates
- `/consult` command — Ecosystem navigation and guidance
