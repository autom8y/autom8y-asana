# Validation Phase Patterns

> Copy-paste prompts for testing, validation, maintenance, and quality checks

---

## Agent Invocation (Quick Reference)

### QA/Adversary

```
Act as the QA/Adversary.

Available skills:
- `documentation` — Test Plan templates
- `10x-workflow` — quality gates, validation criteria

{task}
```

### Principal Engineer (for maintenance)

```
Act as the Principal Engineer.

Available skills:
- `standards` — code conventions, repository structure
- `documentation` — ADR templates (for decisions during fixes)

{task}
```

---

## Validation Phase

### Create Test Plan

```
Act as the QA/Adversary.

Create a Test Plan for:
- PRD: /docs/requirements/PRD-{NNNN}-{slug}.md
- TDD: /docs/design/TDD-{NNNN}-{slug}.md

(The `documentation` skill provides the Test Plan template.)

Ensure every acceptance criterion has test coverage.
Include edge cases, error cases, and security considerations.
```

### Validate Implementation

```
Act as the QA/Adversary.

Validate this implementation:
- Code: /src/{path}
- PRD: /docs/requirements/PRD-{NNNN}-{slug}.md
- TDD: /docs/design/TDD-{NNNN}-{slug}.md

Check:
1. Does it satisfy every acceptance criterion in the PRD?
2. Does it match the design in the TDD?
3. Are error paths handled and tested?
4. Are there edge cases not covered?
5. Any security concerns?
6. Would you approve this for production tonight?
```

### Adversarial Review

```
Act as the QA/Adversary.

Try to break this: /src/{path}

Think like an attacker:
- What inputs could cause failures?
- What sequences weren't anticipated?
- What happens under resource exhaustion?
- What happens with malicious input?
- What race conditions exist?

Think like a confused user:
- What unexpected but valid inputs might occur?
- What's the experience when things fail?
```

### Pre-Ship Checklist

```
Act as the QA/Adversary.

Final review before shipping:
- PRD: /docs/requirements/PRD-{NNNN}-{slug}.md
- TDD: /docs/design/TDD-{NNNN}-{slug}.md
- Code: /src/{path}
- Tests: /tests/{path}

Verify:
- [ ] All PRD acceptance criteria have passing tests
- [ ] All TDD components implemented
- [ ] Error handling complete and tested
- [ ] No high-severity issues open
- [ ] Observability in place (logs, metrics)
- [ ] Documentation updated

Approve or list blocking issues.
```

---

## Maintenance Patterns

### Bug Investigation

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

### Add Feature to Existing System

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

(Skills available: `documentation`, `standards`, `10x-workflow`, `prompting`)
```

### Update Documentation

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

## Meta-Prompts

### Check Workflow Compliance

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

### Suggest Next Steps

```
Current state:
- PRD-{NNNN}: {status}
- TDD-{NNNN}: {status}
- Implementation: {status}
- Tests: {status}

What should I work on next? What's blocking progress?
```

### Retrospective

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
| Need test strategy | Create Test Plan |
| Code complete, verify it works | Validate Implementation |
| Security/edge case review | Adversarial Review |
| Ready to deploy | Pre-Ship Checklist |
| Bug reported | Bug Investigation |
| Extending existing feature | Add Feature to Existing System |
| Docs out of date | Update Documentation |
| Audit recent work | Check Workflow Compliance |
| Unsure what's next | Suggest Next Steps |
| After shipping | Retrospective |

---

## Related Patterns

- **Requirements/Discovery**: [discovery.md](discovery.md) - Session init, PRD creation
- **Design/Implementation**: [implementation.md](implementation.md) - TDD, architecture, coding

---

## Cross-Skill Navigation

- [SKILL.md](../SKILL.md) - Complete prompting skill overview
- [10x-workflow](../../10x-workflow/SKILL.md) - Pipeline flow and quality gates
- [documentation](../../documentation/SKILL.md) - Test Plan templates
