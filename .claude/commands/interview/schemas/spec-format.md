---
user-invocable: false
---

# Spec Artifact Format

> Output schema for interview-produced specifications.

## Template

```markdown
# {Topic}

## Intent
{One paragraph: what we're building and why. Written in active voice.
States the problem being solved, not just the solution being built.}

## Decisions
| Decision | Choice | Rationale |
|----------|--------|-----------|
| {key decision} | {what was chosen} | {why — include what was rejected and why} |

## Scope
**In scope:**
- {concrete deliverable 1}
- {concrete deliverable 2}

**Out of scope:**
- {explicit exclusion 1 — and why it's excluded}
- {explicit exclusion 2}

## Design
{Technical approach. Architecture, data model, integration points.
Reference specific files and paths from the codebase.
Diagrams in ASCII if helpful. Keep it scannable — bullets over prose.}

## Implementation Plan
{Ordered steps. Each step references files to create or modify.}

1. **{Step name}**: {What to do}
   - Files: `{path/to/file}`
   - Depends on: {previous step or "none"}

2. **{Step name}**: {What to do}
   - Files: `{path/to/file}`
   - Depends on: {previous step}

## Open Questions
{Anything explicitly deferred during the interview. Empty if fully resolved.
Each question should note WHY it was deferred (not enough info, out of scope, etc.)}

- {Question}: {reason deferred}
```

## Quality Criteria

The spec is ready when:

1. **A developer who wasn't in the interview can execute from it.** No tribal knowledge required.
2. **Every decision has a rationale.** "Because the user said so" is valid; silence is not.
3. **Scope boundaries are explicit.** What's out is as important as what's in.
4. **File paths are real.** If the spec says "modify `internal/auth/handler.go`", that file exists.
5. **Implementation steps are ordered and sized.** Each step is a logical commit-sized unit.
6. **Open questions are captured, not silently dropped.** Deferred is fine. Forgotten is not.

## Size Guidelines

| Depth | Target Length | Reading Time |
|-------|-------------|-------------|
| shallow | 50-100 lines | 1 minute |
| standard | 100-200 lines | 2-3 minutes |
| deep | 200-400 lines | 5 minutes max |

A spec that takes longer than 5 minutes to read is too long. Split it or compress it.
