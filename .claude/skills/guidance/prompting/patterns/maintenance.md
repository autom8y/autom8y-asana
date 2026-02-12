---
name: maintenance
description: "Post-ship maintenance patterns for bug investigation, feature additions, and documentation updates."
---

# Maintenance Patterns

> Post-deployment operations and ongoing maintenance

---

## Bug Investigation

```
Act as the Principal Engineer.

Bug report: {describe symptom}

Before proposing fixes:
1. Find the relevant PRD/TDD to understand intended behavior
2. Check ADRs for context on design decisions
3. Identify root cause vs. symptom

Then propose a fix with:
- Root cause analysis
- Proposed solution
- Test to prevent regression
```

## Add Feature to Existing System

```
Check /docs/INDEX.md for existing artifacts.

I want to add: {feature description}

To existing system documented in:
- PRD-{NNNN}
- TDD-{NNNN}

Should this be:
A) Amendment to existing PRD/TDD
B) New PRD/TDD that references existing

Help me decide, then proceed with the appropriate approach.
```

## Update Documentation

```
Act as the {appropriate role}.

This documentation is outdated: /docs/{path}

Current state of the system:
{describe current reality}

Update the document to reflect reality.
If this contradicts ADRs, note whether we need new ADRs
to document the changed decisions.
```

---

## When to Use These Patterns

| Situation | Pattern |
|-----------|---------|
| Bug reported | Bug Investigation |
| Extending existing feature | Add Feature to Existing System |
| Docs out of date | Update Documentation |

---

## Related

- [validation.md](validation.md) - Testing and QA patterns
- [INDEX.lego.md](../INDEX.lego.md) - Pattern index
