---
name: meta-prompts
description: "Process audit patterns for workflow compliance, retrospectives, and next-step suggestions."
---

# Meta-Prompts

> Process audits and workflow introspection

---

## Check Workflow Compliance

```
Review my recent work for workflow compliance:

- /docs/requirements/PRD-{NNNN}.md
- /docs/design/TDD-{NNNN}.md
- /docs/decisions/ADR-{NNNN}.md
- /src/{path}

Check:
- Does PRD follow template?
- Does TDD trace to PRD?
- Are ADRs complete for significant decisions?
- Does code follow conventions? (see `standards` skill)
- Is /docs/INDEX.md updated?
```

## Suggest Next Steps

```
Current state:
- PRD-{NNNN}: {status}
- TDD-{NNNN}: {status}
- Implementation: {status}
- Tests: {status}

What should I work on next? What's blocking progress?
```

## Retrospective

```
We just completed {feature}.

Review the process:
- What documentation is missing or incomplete?
- What decisions weren't captured in ADRs?
- What would make the next feature faster?
- What should we update in our conventions?
```

---

## When to Use These Patterns

| Situation | Pattern |
|-----------|---------|
| Audit recent work | Check Workflow Compliance |
| Unsure what's next | Suggest Next Steps |
| After shipping | Retrospective |

---

## Related

- [INDEX.lego.md](../INDEX.lego.md) - Pattern index
