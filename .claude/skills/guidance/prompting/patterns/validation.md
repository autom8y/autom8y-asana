# Validation Phase Patterns

> Copy-paste prompts for testing, validation, and quality checks. For agent invocation patterns, see [INDEX.lego.md](../INDEX.lego.md#quick-reference-agent-invocation).

---

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

## When to Use These Patterns

| Situation | Pattern |
|-----------|---------|
| Need test strategy | Create Test Plan |
| Code complete, verify it works | Validate Implementation |
| Security/edge case review | Adversarial Review |
| Ready to deploy | Pre-Ship Checklist |

## Related Patterns

- [discovery.md](discovery.md) - Session init, PRD creation
- [implementation.md](implementation.md) - TDD, architecture, coding
- [maintenance.md](maintenance.md) - Bug investigation, feature additions
- [meta-prompts.md](meta-prompts.md) - Process audits, retrospectives
