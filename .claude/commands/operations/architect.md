---
name: architect
description: Design-only session producing design artifacts (no implementation)
argument-hint: "<feature-description> [--complexity=LEVEL]"
allowed-tools: Bash, Read, Write, Task, Glob, Grep
model: opus
disable-model-invocation: true
---

## Context
Auto-injected by SessionStart hook (project, rite, session, git, workflow).

## Pre-flight

1. **Session context** (recommended):
   - Check Session Status in context above
   - If no session: WARN "No active session. Consider /start for tracked workflow."

2. **Prerequisites check**:
   - Verify task description is provided in $ARGUMENTS
   - If empty: ERROR "Feature description required. Usage: /architect 'feature description'"

## Your Task

Design a feature/system without implementation. Produce design documents only. $ARGUMENTS

**NO CODE/IMPLEMENTATION. Design documents only.**

## Workflow Resolution

Read the design agent from workflow:

```bash
# Find the design/architecture phase agent
# This varies by rite - 10x uses "design", doc-rite uses "architecture", etc.
DESIGN_AGENT=$(grep -B1 "produces: tdd\|produces: doc-structure\|produces: refactor-plan\|produces: risk-report" .claude/ACTIVE_WORKFLOW.yaml | grep "agent:" | head -1 | awk '{print $2}')
```

## Behavior

1. **Validate prerequisites**:
   - Requirements/entry artifact exists or scope is clear
   - Scope is defined

2. **Resolve design agent** from workflow:
   - 10x-dev → architect
   - docs → information-architect
   - hygiene → architect-enforcer
   - debt-triage → risk-assessor

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

Full documentation: `rites/10x-dev/mena/architect-ref/INDEX.lego.md`
