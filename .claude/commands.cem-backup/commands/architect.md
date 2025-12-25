---
description: Design-only session producing design artifacts (no implementation)
argument-hint: <feature-description> [--complexity=LEVEL]
allowed-tools: Bash, Read, Write, Task, Glob, Grep
model: claude-opus-4-5
---

## Context
Auto-injected by SessionStart hook (project, team, session, git, workflow).

## Your Task

Design a feature/system without implementation. Produce design documents only. $ARGUMENTS

**NO CODE/IMPLEMENTATION. Design documents only.**

## Workflow Resolution

Read the design agent from workflow:

```bash
# Find the design/architecture phase agent
# This varies by team - 10x uses "design", doc-team uses "architecture", etc.
DESIGN_AGENT=$(grep -B1 "produces: tdd\|produces: doc-structure\|produces: refactor-plan\|produces: risk-report" .claude/ACTIVE_WORKFLOW.yaml | grep "agent:" | head -1 | awk '{print $2}')
```

## Behavior

1. **Validate prerequisites**:
   - Requirements/entry artifact exists or scope is clear
   - Scope is defined

2. **Resolve design agent** from workflow:
   - 10x-dev-pack → architect
   - doc-team-pack → information-architect
   - hygiene-pack → architect-enforcer
   - debt-triage-pack → risk-assessor

3. **Invoke design agent** via Task tool:
   - Analyze requirements/inputs
   - Evaluate alternatives
   - Make structural decisions

4. **Produce artifacts**:
   - Design document (TDD, doc-structure, refactor-plan, etc.)
   - Decision records (ADRs if applicable)

5. **Quality gate**:
   - All requirements traced to design
   - Significant decisions documented
   - Interfaces/structure defined
   - Risks identified

## When to Use

- Before committing to implementation
- Design review gates
- Evaluating approaches
- Two-phase workflow with `/build`

## Example

```
/architect "User authentication system"
/architect "Documentation restructure" --complexity=SECTION
```

Pairs with: `/build` (implementation from approved design)

## Reference

Full documentation: `.claude/skills/architect-ref/skill.md`
