---
name: task-ref
description: "Single focused development task through full lifecycle (PRD → TDD → Code → QA). Most common development workflow. Triggers: /task, implement feature, build task, development task, full cycle."
---

# /task - Single Task Full Lifecycle

> **Category**: Development | **Phase**: Task Execution | **Complexity**: Medium

## Purpose

Execute a single focused development task through the complete workflow lifecycle: Requirements → Design → Implementation → Validation.

This is the **most common development command**, providing the right balance of structure and speed for individual features, bug fixes, or enhancements.

---

## Usage

```bash
/task "task-description" [--complexity=LEVEL] [--skip-prd] [--skip-tdd]
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `task-description` | Yes | - | Clear description of what to build |
| `--complexity` | No | Auto-detect | SCRIPT \| MODULE \| SERVICE \| PLATFORM |
| `--skip-prd` | No | false | Skip PRD creation (use for small tasks) |
| `--skip-tdd` | No | false | Skip TDD creation (SCRIPT only) |

---

## Behavior

### 1. Task Initialization

Gather task details if not fully specified:

- **Task name**: What needs to be built/fixed
- **Complexity**: Auto-detect or prompt if unclear
  - SCRIPT: Single file, < 200 LOC
  - MODULE: Multiple files, clear interfaces
  - SERVICE: Multiple modules, APIs, persistence
  - PLATFORM: Multiple services, infrastructure

### 2. Phase 1: Requirements (PRD)

**Invoke Requirements Analyst** unless `--skip-prd` specified:

```markdown
Act as **Requirements Analyst**.

Task: {task-description}
Complexity: {complexity}

Create a PRD following template at `.claude/skills/documentation/templates/prd.md`.

For SCRIPT complexity:
- Keep PRD lightweight (1-2 pages)
- Focus on acceptance criteria

For MODULE+ complexity:
- Full PRD with use cases
- Detailed acceptance criteria
- Edge case analysis

Save to: /docs/requirements/PRD-{task-slug}.md
```

**Quality Gate**: PRD must have clear acceptance criteria.

### 3. Phase 2: Design (TDD)

**Invoke Architect** if complexity is MODULE or higher (unless `--skip-tdd`):

```markdown
Act as **Architect**.

Task: {task-description}
PRD: /docs/requirements/PRD-{task-slug}.md
Complexity: {complexity}

Create TDD following template at `.claude/skills/documentation/templates/tdd.md`.

For MODULE:
- Component interfaces
- Key algorithms
- Testing strategy

For SERVICE:
- System architecture
- API contracts
- Data models
- Integration points

For PLATFORM:
- Multi-service design
- Infrastructure requirements
- Deployment strategy

Create ADRs for any significant decisions using template at `.claude/skills/documentation/templates/adr.md`.

Save:
- TDD to: /docs/design/TDD-{task-slug}.md
- ADRs to: /docs/decisions/ADR-{NNNN}-{decision-slug}.md
```

**Quality Gate**: TDD traces to PRD, all design decisions documented.

**Skip for SCRIPT**: Scripts typically don't need formal TDD.

### 4. Phase 3: Implementation

**Invoke Principal Engineer**:

```markdown
Act as **Principal Engineer**.

Task: {task-description}
PRD: /docs/requirements/PRD-{task-slug}.md
TDD: /docs/design/TDD-{task-slug}.md (if MODULE+)
Complexity: {complexity}

Implement the solution following these guidelines:

1. Read PRD and TDD thoroughly
2. Follow project standards (see `.claude/skills/standards/`)
3. Write tests first (TDD approach) or alongside implementation
4. Implement with production quality:
   - Type safety
   - Error handling
   - Logging/observability
   - Documentation
5. Verify all tests pass
6. Update any relevant documentation

Deliverables:
- Implementation code
- Unit/integration tests
- Updated documentation (if needed)
```

**Quality Gate**: Tests pass, code follows standards, PRD acceptance criteria met.

### 5. Phase 4: Validation (QA)

**Invoke QA Adversary**:

```markdown
Act as **QA/Adversary**.

Task: {task-description}
PRD: /docs/requirements/PRD-{task-slug}.md
Implementation: {code-locations}

Validate the implementation:

1. Verify all PRD acceptance criteria met
2. Test edge cases and error conditions
3. Check for security vulnerabilities
4. Validate error messages and user experience
5. Confirm performance meets requirements
6. Review test coverage

Create Test Plan at: /docs/testing/TEST-{task-slug}.md

If issues found:
- Document in test plan
- Create defect report
- Hand back to Principal Engineer for fixes

Final deliverable: Production readiness report
```

**Quality Gate**: All acceptance criteria met, no critical defects, production ready.

### 6. Task Completion

When all phases complete:

**Display summary**:

```
Task Complete: {task-description}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Artifacts Created:
✓ PRD: /docs/requirements/PRD-{slug}.md
✓ TDD: /docs/design/TDD-{slug}.md (if MODULE+)
✓ Code: {implementation-files}
✓ Tests: {test-files}
✓ Test Plan: /docs/testing/TEST-{slug}.md

Quality Gates:
✓ All acceptance criteria met
✓ Tests passing (coverage: {percentage}%)
✓ No critical defects
✓ Production ready

Next steps:
- Review artifacts for approval
- Run `/commit` to commit changes (if desired)
- Use `/wrap` to finalize session (if in session)
```

---

## Workflow

```mermaid
graph LR
    A[/task invoked] --> B{Skip PRD?}
    B -->|No| C[Requirements Analyst]
    B -->|Yes| D{Complexity}
    C --> D
    D -->|SCRIPT| E[Principal Engineer]
    D -->|MODULE+| F[Architect]
    F --> E
    E --> G[QA Adversary]
    G --> H{Issues?}
    H -->|Yes| I[Fix & Retest]
    I --> G
    H -->|No| J[Task Complete]
```

---

## Deliverables

Every task produces:

1. **PRD** (unless --skip-prd): Requirements document
2. **TDD** (MODULE+ only): Technical design
3. **ADRs** (as needed): Architecture decisions
4. **Implementation**: Production-quality code
5. **Tests**: Passing unit/integration tests
6. **Test Plan**: QA validation results

---

## Examples

### Example 1: Simple Script Task

```bash
/task "Add retry logic to API client" --complexity=SCRIPT
```

Output:
```
Task: Add retry logic to API client
Complexity: SCRIPT

[Phase 1] Requirements
✓ PRD created (lightweight): /docs/requirements/PRD-api-retry.md
  Acceptance criteria:
  - Retry on network failures (3 attempts)
  - Exponential backoff
  - Configurable retry count

[Phase 2] Design
⊘ Skipped (SCRIPT complexity - no TDD needed)

[Phase 3] Implementation
✓ Principal Engineer implementing...
✓ Code: /src/api/client.ts (added retryWithBackoff function)
✓ Tests: /src/api/client.test.ts (5 test cases)
✓ All tests passing

[Phase 4] Validation
✓ QA Adversary validating...
✓ All acceptance criteria met
✓ Edge cases tested: timeout, max retries, success after retry
✓ No defects found

Task complete: Ready for commit
```

### Example 2: Module Task

```bash
/task "Implement user authentication module"
```

Interactive prompts:
```
Task: Implement user authentication module
Complexity? [SCRIPT/MODULE/SERVICE/PLATFORM]: MODULE

[Phase 1] Requirements
✓ Requirements Analyst creating PRD...
✓ PRD: /docs/requirements/PRD-user-auth.md

[Phase 2] Design
✓ Architect creating TDD...
✓ TDD: /docs/design/TDD-user-auth.md
✓ ADR created: /docs/decisions/ADR-0050-jwt-vs-sessions.md

[Phase 3] Implementation
✓ Principal Engineer implementing...
  Files created:
  - /src/auth/authenticator.ts
  - /src/auth/jwt-manager.ts
  - /src/auth/middleware.ts
  - /tests/auth/authenticator.test.ts
✓ All tests passing (coverage: 94%)

[Phase 4] Validation
✓ QA Adversary validating...
✓ Test Plan: /docs/testing/TEST-user-auth.md
✓ Security review: PASSED
✓ Performance: Login < 100ms (requirement: < 200ms)
✓ Production ready

Task complete.
```

### Example 3: Quick Task (Skip PRD)

```bash
/task "Fix typo in error message" --skip-prd --complexity=SCRIPT
```

Output:
```
Task: Fix typo in error message
Complexity: SCRIPT

[Phase 1] Requirements
⊘ Skipped (--skip-prd specified)

[Phase 2] Design
⊘ Skipped (SCRIPT complexity)

[Phase 3] Implementation
✓ Principal Engineer implementing...
✓ Fixed: /src/errors/messages.ts
✓ Tests updated

[Phase 4] Validation
✓ QA Adversary: Quick validation passed

Task complete: Trivial change, ready for commit
```

---

## When to Use vs Alternatives

| Use /task when... | Use alternative when... |
|-------------------|-------------------------|
| Single focused feature/fix | Multiple related tasks → Use `/sprint` |
| Need full PRD → Code → QA cycle | Urgent production fix → Use `/hotfix` |
| Want quality gates at each phase | Just researching → Use `/spike` |
| Building production code | Exploring feasibility → Use `/spike` |

### /task vs /sprint

- `/task`: ONE task, full lifecycle
- `/sprint`: MULTIPLE tasks, coordinated execution

### /task vs /hotfix

- `/task`: Full workflow with PRD/TDD/QA
- `/hotfix`: Skip PRD/TDD, minimal QA, rapid fix

### /task vs /spike

- `/task`: Production code expected
- `/spike`: NO production code, research only

---

## Complexity Level

**MEDIUM** - This command:
- Coordinates 4 agents sequentially
- Enforces quality gates
- Produces comprehensive documentation
- Suitable for most development tasks

**Recommended for**:
- Feature development (small to medium)
- Bug fixes requiring design review
- Enhancements with clear requirements
- Refactoring with test coverage

**Not recommended for**:
- Urgent hotfixes (use `/hotfix`)
- Research/exploration (use `/spike`)
- Multi-feature sprints (use `/sprint`)
- Trivial changes (just make the edit)

---

## State Changes

### Files Created

| File Type | Location | Condition |
|-----------|----------|-----------|
| PRD | `/docs/requirements/PRD-{slug}.md` | Unless --skip-prd |
| TDD | `/docs/design/TDD-{slug}.md` | If MODULE+ |
| ADRs | `/docs/decisions/ADR-{N}-{slug}.md` | As needed |
| Code | Project-specific | Always |
| Tests | Project-specific | Always |
| Test Plan | `/docs/testing/TEST-{slug}.md` | Always |

### No Session Context Required

`/task` can run independently of `/start`:
- Works without active SESSION_CONTEXT
- Can be used ad-hoc for single tasks
- If session active, artifacts are linked to session

---

## Prerequisites

- 10x-dev-pack active (or team with 4 agents: Analyst, Architect, Engineer, QA)
- Project structure exists (for artifact storage)
- Clear task description

---

## Success Criteria

- All 4 workflow phases complete (unless skipped)
- Artifacts produced meet quality gates
- Tests passing
- Code follows project standards
- Production ready

---

## Error Cases

| Error | Condition | Resolution |
|-------|-----------|------------|
| Unclear requirements | Task description too vague | Requirements Analyst asks clarifying questions |
| Design complexity mismatch | Complexity underestimated | Architect escalates, recommends higher complexity |
| Implementation fails tests | Code doesn't meet acceptance criteria | Engineer fixes, QA re-validates |
| QA finds critical defects | Quality gate failure | Hand back to Engineer, fix and retest |
| Missing team agents | Required agent not available | Switch to 10x-dev-pack with `/10x` |

---

## Related Commands

- `/sprint` - Multi-task coordination (uses /task internally)
- `/hotfix` - Rapid fix without full workflow
- `/spike` - Research without production code
- `/start` - Initialize session (optional before /task)
- `/handoff` - Manual agent switching (alternative to automatic)

---

## Related Skills

- [10x-workflow](../10x-workflow/SKILL.md) - Agent coordination patterns
- [documentation](../documentation/SKILL.md) - PRD/TDD/ADR/Test Plan templates
- [standards](../standards/SKILL.md) - Code quality and conventions

---

## Notes

### Skip Flags Best Practices

**--skip-prd**: Use when:
- Task is trivial (typo fix, simple refactor)
- Requirements are crystal clear
- You've already written requirements elsewhere

**Don't use** for:
- New features (always need PRD)
- Complex bugs (need root cause analysis)
- Ambiguous tasks (clarification required)

**--skip-tdd**: Use when:
- Complexity is SCRIPT (auto-skipped anyway)
- Design is obvious and no decisions needed
- Quick implementation task

**Don't use** for:
- MODULE+ complexity
- Architectural changes
- New integrations

### Agent Coordination

`/task` automatically coordinates agents:
1. **Analyst** → Creates PRD, exits
2. **Architect** → Reads PRD, creates TDD, exits
3. **Engineer** → Reads PRD+TDD, implements, exits
4. **QA** → Reads all artifacts, validates, exits

No manual handoffs needed. Each agent reads previous outputs.

### Parallel Tasks

To run multiple independent tasks:

```bash
# Don't do this - use /sprint instead
/task "Task 1"
/task "Task 2"  # Will conflict with Task 1

# Instead:
/sprint "Multi-task" --tasks="Task 1,Task 2"
```

`/task` is designed for single-task execution.

---

## Quality Gate Details

### PRD Quality Gate
- Problem statement clear
- Acceptance criteria testable
- Edge cases identified
- Success metrics defined

### TDD Quality Gate (MODULE+)
- Traces to PRD requirements
- Interfaces well-defined
- Technology choices justified (ADRs)
- Testing strategy specified

### Implementation Quality Gate
- All tests passing
- Code follows standards
- PRD acceptance criteria met
- Documentation updated

### QA Quality Gate
- All acceptance criteria validated
- Edge cases tested
- No critical defects
- Performance acceptable
- Production ready

---

## Integration with Git

After task completes, you can:

```bash
# Commit changes
/commit "Implement user authentication module"

# Create PR (if desired)
/pr "Add user authentication"
```

These are separate commands, not part of `/task`.

---

## Metrics Tracked

For each task, track:
- Time to complete (each phase)
- Complexity (actual vs estimated)
- Defect count (found in QA)
- Test coverage
- Lines of code

Use for velocity estimation in future tasks.
