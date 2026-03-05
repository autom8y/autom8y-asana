---
user-invocable: false
---

# /start Agent Integration

> Task tool delegation templates for /start.

## Requirements Analyst Delegation

Always invoked for all complexity levels:

```markdown
Act as **Requirements Analyst**.

Initiative: {initiative-name}
Complexity: {complexity}

Create a PRD following the template at `.claude/skills/documentation/templates/prd.md` -- template paths are illustrative; actual templates vary by rite.

Clarify any ambiguities with the user before drafting. When complete, save to:
`.ledge/specs/PRD-{initiative-slug}.md`
```

## Architect Delegation

Invoked when complexity > PATCH (MODULE, SYSTEM, INITIATIVE, MIGRATION):

```markdown
Act as **Architect**.

Initiative: {initiative-name}
PRD Location: .ledge/specs/PRD-{slug}.md

Create TDD following template at `.claude/skills/documentation/templates/tdd.md` -- template paths are illustrative; actual templates vary by rite.

Identify architecture decisions and create ADRs using template at `.claude/skills/documentation/templates/adr.md` -- template paths are illustrative; actual templates vary by rite.

When complete, save:
- TDD to: .ledge/specs/TDD-{slug}.md
- ADRs to: .ledge/decisions/ADR-{NNNN}-{decision-slug}.md
```

## Complexity → Agent Matrix

| Complexity | Agents Invoked | Artifacts Produced |
|------------|----------------|-------------------|
| PATCH | Requirements Analyst | PRD only |
| MODULE | Requirements Analyst → Architect | PRD, TDD, ADRs |
| SYSTEM | Requirements Analyst → Architect | PRD, TDD, ADRs |
| INITIATIVE | Requirements Analyst → Architect | PRD, TDD, multiple ADRs |
| MIGRATION | Requirements Analyst → Architect | PRD, TDD, migration plan |

## Notes

- All agent invocation happens via Claude Code's native Task tool
- No direct shell execution of agent files
- Agents are defined in `.claude/agents/{agent-name}.md`
- Templates are in `.claude/skills/documentation/templates/`
