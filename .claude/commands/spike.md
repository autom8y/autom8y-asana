---
description: Time-boxed research and exploration (no production code)
argument-hint: "<question> [--timebox=DURATION]"
allowed-tools: Bash, Read, Write, Task, Glob, Grep, WebFetch, WebSearch
model: opus
---

## Context
Auto-injected by SessionStart hook (project, rite, session, git).

## Pre-flight

1. **Arguments required**:
   - Parse `$ARGUMENTS` for spike topic
   - If empty: ERROR "Spike topic required. Usage: /spike 'exploration topic'"

## Your Task

Conduct time-boxed research to answer a technical question. $ARGUMENTS

**NO PRODUCTION CODE. Research and report only.**

## Behavior

1. **Define the question**:
   - What are we trying to learn?
   - What decision will this inform?
   - What's the timebox?

2. **Research**:
   - Explore existing codebase
   - Search documentation
   - Evaluate alternatives
   - Build throwaway POC if needed

3. **Document findings**:
   - Create spike report
   - Comparison matrix (if evaluating options)
   - Recommendation with rationale

4. **Timebox checkpoints**:
   - 25% mark: Initial findings
   - 50% mark: Deep dive complete
   - 75% mark: Draft recommendation
   - 100% mark: Final report

## Output

Spike report at `/docs/spikes/SPIKE-{slug}.md`:
- Question and context
- Approach taken
- Findings
- Recommendation
- Follow-up actions

## Example

```
/spike "Can we use GraphQL instead of REST?" --timebox=4h
/spike "What's the best approach for real-time updates?"
```

## Reference

Full documentation: `.claude/commands/operations/spike/INDEX.md`
