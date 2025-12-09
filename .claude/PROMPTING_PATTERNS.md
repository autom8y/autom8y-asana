# Prompting Patterns Cheatsheet

> Quick-reference for effective prompts. Copy, customize, use.

---

## Session Initialization

### Start of Session (Always Do This)
```
Read .claude/CLAUDE.md to understand this project's workflow and
documentation structure. Then read .claude/PROJECT_CONTEXT.md for
project context. Check /docs/INDEX.md for existing documentation.

Confirm when ready.
```

### Resume Previous Work
```
Read .claude/CLAUDE.md and then review:
- PRD: /docs/requirements/PRD-{NNNN}-{slug}.md
- TDD: /docs/design/TDD-{NNNN}-{slug}.md (if exists)

We were working on {feature}. Last session we completed {what}.
Let's continue with {next step}.
```

---

## Agent Invocation

### Requirements Analyst
```
Act as the Requirements Analyst (per .claude/agents/requirements-analyst.md).

{task}
```

### Architect
```
Act as the Architect (per .claude/agents/architect.md).

{task}
```

### Principal Engineer
```
Act as the Principal Engineer (per .claude/agents/principal_engineer.md).

{task}
```

### QA/Adversary
```
Act as the QA/Adversary (per .claude/agents/qa_adversary.md).

{task}
```

---

## Requirements Phase

### New Feature PRD
```
Act as the Requirements Analyst.

Create a PRD for: {feature description}

Follow TEAM_DOCUMENTATION_PROTOCOL.md for the template.
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

## Design Phase

### Create TDD from PRD
```
Act as the Architect.

The PRD is approved: /docs/requirements/PRD-{NNNN}-{slug}.md

Create a TDD following TEAM_DOCUMENTATION_PROTOCOL.md.

First:
1. Check /docs/decisions/ for existing ADRs that apply
2. Check /docs/design/ for related TDDs to reference

Then design the simplest architecture that satisfies the requirements.
Create ADRs for any new significant decisions.
```

### Complexity Calibration
```
Act as the Architect.

For this requirement set (PRD-{NNNN}), what's the right complexity level?

Options:
- Script: Single file, functions, no structure
- Module: Clean API, types, tests
- Service: Layered architecture, config, observability
- Platform: Full architectural rigor

Justify your recommendation based on the actual requirements,
not hypothetical future needs.
```

### Create ADR
```
Act as the Architect.

I need to decide: {decision to make}

Options I'm considering:
1. {option 1}
2. {option 2}
3. {option 3}

Create an ADR following TEAM_DOCUMENTATION_PROTOCOL.md.
Analyze trade-offs honestly—what do we give up with each choice?
```

### Review TDD
```
Act as the Principal Engineer.

Review this TDD before I implement: /docs/design/TDD-{NNNN}-{slug}.md

Check:
- [ ] Is the design implementable as specified?
- [ ] Are interfaces clear enough to code against?
- [ ] Are there ambiguities I'll have to guess at?
- [ ] Is complexity justified by the PRD requirements?
- [ ] Anything missing that I'll need to decide during implementation?
```

---

## Implementation Phase

### Implement from TDD
```
Act as the Principal Engineer.

Implement this design:
- TDD: /docs/design/TDD-{NNNN}-{slug}.md
- PRD: /docs/requirements/PRD-{NNNN}-{slug}.md (for acceptance criteria)
- Related ADRs: {list}

Follow:
- CODE_CONVENTIONS.md for patterns
- REPOSITORY_MAP.md for file placement

Create implementation ADRs for any decisions the TDD didn't specify.
```

### Implement Single Component
```
Act as the Principal Engineer.

Implement {component name} per TDD-{NNNN}:

From the TDD, this component:
- Responsibility: {what it does}
- Interface: {its contract}
- Dependencies: {what it needs}

Follow CODE_CONVENTIONS.md. Place files per REPOSITORY_MAP.md.
```

### Add Tests for Implementation
```
Act as the Principal Engineer.

Add tests for: /src/{path}

Requirements (from PRD-{NNNN}):
- FR-001: {requirement}
- FR-002: {requirement}

Test coverage needed:
- Unit tests for business logic
- Edge cases for each requirement
- Error handling paths

Follow testing conventions in CODE_CONVENTIONS.md.
```

### Refactor Existing Code
```
Act as the Principal Engineer.

Refactor: /src/{path}

Goal: {what improvement}
Constraint: No behavior changes (unless specified)

Approach:
1. Ensure tests exist for current behavior
2. Make incremental changes
3. Keep tests passing after each change
4. Create ADR if making non-obvious decisions
```

---

## Validation Phase

### Create Test Plan
```
Act as the QA/Adversary.

Create a Test Plan for:
- PRD: /docs/requirements/PRD-{NNNN}-{slug}.md
- TDD: /docs/design/TDD-{NNNN}-{slug}.md

Follow TEAM_DOCUMENTATION_PROTOCOL.md template.

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
Read .claude/CLAUDE.md and /docs/INDEX.md first.

I want to add: {feature description}

To existing system documented in:
- PRD-{NNNN}
- TDD-{NNNN}

Should this be:
A) Amendment to existing PRD/TDD
B) New PRD/TDD that references existing

Help me decide, then proceed with the appropriate approach.
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

## Workflow Shortcuts

### Full Feature Flow (Compact)
```
Let's build: {feature}

Phase 1: Act as Analyst, create PRD
Phase 2: Act as Architect, create TDD + ADRs
Phase 3: Act as Engineer, implement
Phase 4: Act as QA, validate

Start with Phase 1. I'll review and approve each phase
before we proceed to the next.
```

### Quick Fix (Skip Full Workflow)
```
This is a simple bug fix that doesn't need full workflow.

Bug: {description}
File: /src/{path}

Act as Engineer: fix the bug.
Then act as QA: verify the fix and add a regression test.
```

### Spike/Exploration (Minimal Process)
```
This is exploratory work, not production code.

I want to explore: {concept}

Act as Engineer. Build a quick prototype to test the idea.
Skip PRD/TDD—this is throwaway code to learn.
Focus on answering: {key question to answer}
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
- Does code follow CODE_CONVENTIONS.md?
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
