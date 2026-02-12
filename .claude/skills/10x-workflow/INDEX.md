---
name: 10x-workflow
description: "10x workflow coordination and agent routing. Use when: understanding phase transitions, routing work to specialist agents, coordinating multi-agent pipelines. Triggers: workflow, agent coordination, handoff, pipeline, phase transition, orchestration."
---

# 10x Agentic Workflow

> **Status**: Complete (Session 3)

## Protocol Overview

The 10x Agentic Workflow achieves 10x productivity through specialized AI agents coordinated by Pythia:

- **Early clarity** - Requirements and scope validated before implementation
- **Right-sized effort** - Complexity calibrated to actual need
- **Quality gates** - Issues caught before they propagate
- **Specialist sovereignty** - Decisions made by the appropriate expert
- **Adaptive planning** - Plans adjusted based on discoveries

---

## Flexible Entry Points

The default workflow starts with Requirements Analyst, but work type determines the optimal entry point:

### Entry Point Selection

| Work Type | Entry Agent | Phases Run |
|-----------|-------------|------------|
| New feature | requirements-analyst | PRD -> TDD -> Code -> QA |
| Enhancement | requirements-analyst | PRD -> TDD -> Code -> QA |
| Technical refactoring | architect | TDD -> Code -> QA |
| Performance optimization | architect | TDD -> Code -> QA |
| Bug fix | principal-engineer | Code -> QA |
| Security fix | principal-engineer | Code -> QA |
| Hotfix | principal-engineer | Code -> QA |

### Usage Examples

**New feature (default entry)**:
```
/task "Add user profile photo upload"
```
Starts with Requirements Analyst -> full workflow.

**Bug fix (principal-engineer entry)**:
```
/task --entry=principal-engineer "Fix login timeout after 5 minutes"
/task --work-type=bug_fix "Fix null pointer in user service"
```
Skips PRD and TDD; goes directly to implementation and QA.

**Refactoring (architect entry)**:
```
/task --entry=architect "Migrate from REST to GraphQL"
/task --work-type=technical_refactoring "Extract payment module"
```
Skips PRD; starts with TDD to document design decisions.

**Performance optimization (architect entry)**:
```
/task --entry=architect "Optimize database query performance"
```
Architect analyzes bottlenecks, designs solution, then implementation.

### Decision Criteria

1. **Adding user-facing capability?** -> requirements-analyst
2. **Changing system structure without new features?** -> architect
3. **Fixing known broken behavior?** -> principal-engineer
4. **Time-critical remediation?** -> principal-engineer

When uncertain, default to requirements-analyst. Skipping phases is cheaper than backtracking.

---

## Agent Routing

### Quick Reference

| Agent | Domain Authority | Primary Artifact |
|-------|------------------|------------------|
| **Requirements Analyst** | Scope definition, acceptance criteria | PRD |
| **Architect** | System design, technology selection | TDD, ADRs |
| **Principal Engineer** | Implementation approach, code structure | Code, tests |
| **QA/Adversary** | Test strategy, validation, release readiness | Test Plan |
| **Pythia** | Session planning, quality gates, adaptive routing | (Coordinates) |

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

1. **PLAN** (Pythia): Define goal, prerequisites, deliverables, quality gate
2. **CLARIFY** (Pythia + User): Surface ambiguities, get confirmation
3. **EXECUTE** (Specialist): Plan approach, execute work, document decisions
4. **VERIFY** (Pythia): Check quality gate, confirm handoff readiness
5. **HANDOFF** (Pythia): Summarize outcomes, identify next inputs

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

- [documentation](../../../../mena/templates/documentation/INDEX.lego.md) - PRD/TDD/ADR/Test Plan templates and formats
- [prompting](../../../../mena/guidance/prompting/INDEX.lego.md) - Copy-paste prompt patterns for agent invocation
- [consult](../../../../mena/navigation/consult/INDEX.dro.md) - Ecosystem navigation and guidance
- [rite-development](../../../forge/mena/rite-development/INDEX.lego.md) - Creating new rites

> **Note**: When modifying workflows or agents, update the Consultant knowledge base at `.claude/knowledge/consultant/` to keep `/consult` guidance accurate. See [consultant-sync.md](../rite-development/patterns/consultant-sync.md).

**Agent configurations**: See `.claude/agents/` for full agent prompts:
- [pythia.md](../../agents/pythia.md)
- [requirements-analyst.md](../../agents/requirements-analyst.md)
- [architect.md](../../agents/architect.md)
- [principal-engineer.md](../../agents/principal-engineer.md)
- [qa-adversary.md](../../agents/qa-adversary.md)

---

## Project Glossary

This skill defines **workflow process terms** (agents, phases, artifacts). For **project-specific domain terminology**, create a project glossary file only when you have terms Claude wouldn't know (e.g., business domain entities, product-specific concepts, or non-standard terminology).
