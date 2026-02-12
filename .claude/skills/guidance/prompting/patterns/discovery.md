# Discovery Phase Patterns

> Copy-paste prompts for session initialization and requirements definition

---

## Session Initialization

### Start of Session

```
Check /docs/INDEX.md for existing artifacts.

You have access to these skills for on-demand context:
- `orchestration` — workflow coordination
- `documentation` — artifact templates
- `standards` — code conventions
- `prompting` — invocation patterns (you're using one now)

Skills activate automatically. You don't need to load them manually.

Confirm when ready.
```

### Resume Previous Work

```
Review existing artifacts:
- PRD: /docs/requirements/PRD-{NNNN}-{slug}.md
- TDD: /docs/design/TDD-{NNNN}-{slug}.md (if exists)

We were working on {feature}. Last session we completed {what}.
Let's continue with {next step}.

(Skills available: `orchestration`, `documentation`, `standards`, `prompting`)
```

> For agent invocation patterns, see [INDEX.lego.md](../INDEX.lego.md#quick-reference-agent-invocation)

---

## Requirements Phase

### New Feature PRD

```
Act as the Requirements Analyst.

Create a PRD for: {feature description}

(The `documentation` skill provides the PRD template.)
Check /docs/INDEX.md first—reference existing PRDs if this
relates to prior work.

Key questions to address:
- What problem does this solve?
- Who experiences this problem?
- What does success look like?
```

### Clarify Vague Requirements

```
Act as the Requirements Analyst.

The stakeholder said: "{vague request}"

Before creating a PRD, I need to understand:
1. What's the actual problem?
2. Who is affected?
3. What's the impact of not solving it?
4. What's explicitly out of scope?

Ask me clarifying questions.
```

### Migration PRD (Capture Existing Behavior)

```
Act as the Requirements Analyst.

I'm migrating this legacy code:
{paste code or reference path}

Create a PRD that:
1. Documents current behavior as requirements (what must be preserved)
2. Identifies any implicit behavior that should become explicit
3. Notes potential improvements to make during migration
4. Defines acceptance criteria for parity validation
```

### Review PRD

```
Act as the Architect.

Review this PRD: /docs/requirements/PRD-{NNNN}-{slug}.md

Before I can design a solution, verify:
- [ ] Problem statement is clear?
- [ ] Success criteria are measurable?
- [ ] Scope boundaries are explicit?
- [ ] Requirements are testable?
- [ ] Anything ambiguous I should clarify with stakeholders?
```

---

## When to Use These Patterns

| Situation | Pattern |
|-----------|---------|
| Starting fresh session | Start of Session |
| Continuing previous work | Resume Previous Work |
| New feature request | New Feature PRD |
| Unclear requirements | Clarify Vague Requirements |
| Moving legacy code | Migration PRD |
| Before design phase | Review PRD |

---

## Related Patterns

- **Design/Implementation**: [implementation.md](implementation.md) - TDD creation, architecture, coding
- **Validation/Maintenance**: [validation.md](validation.md) - Testing, pre-ship, maintenance

