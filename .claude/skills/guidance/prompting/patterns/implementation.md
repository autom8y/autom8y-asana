# Implementation Phase Patterns

> Copy-paste prompts for design, architecture, and code implementation

> For agent invocation patterns, see [INDEX.lego.md](../INDEX.lego.md#quick-reference-agent-invocation)

---

## Design Phase

### Create TDD from PRD

```
Act as the Architect.

The PRD is approved: /docs/requirements/PRD-{NNNN}-{slug}.md

(The `documentation` skill provides the TDD template.)

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

(The `documentation` skill provides the ADR template.)
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

(The `standards` skill provides code conventions and repository structure.)

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

(The `standards` skill provides code conventions and file placement.)
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

(The `standards` skill provides testing conventions.)
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

## When to Use These Patterns

| Situation | Pattern |
|-----------|---------|
| PRD approved, need design | Create TDD from PRD |
| Unsure how much architecture | Complexity Calibration |
| Significant technical choice | Create ADR |
| Before starting code | Review TDD |
| TDD approved, start coding | Implement from TDD |
| Breaking down large TDD | Implement Single Component |
| Adding test coverage | Add Tests for Implementation |
| Improving existing code | Refactor Existing Code |

---

## Related Patterns

- **Requirements/Discovery**: [discovery.md](discovery.md) - Session init, PRD creation
- **Validation/Maintenance**: [validation.md](validation.md) - Testing, pre-ship, maintenance

