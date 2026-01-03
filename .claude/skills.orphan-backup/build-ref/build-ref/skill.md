---
name: build-ref
description: "Implementation-only session from approved TDD. Use when: TDD has been approved and ready to code, following up after /architect session, implementing from existing design. Triggers: /build, implement design, code from TDD, build approved design."
---

# /build - Implementation-Only Session

> **Category**: Development Workflows | **Phase**: Implementation | **Complexity**: Low

## Purpose

Implement code from an approved TDD without re-doing the design phase. This command assumes design documentation (TDD) already exists and has been reviewed.

Use this when:
- TDD has been approved and you're ready to code
- Following up after `/architect` session
- Design is complete, implementation needed
- Skipping integrated workflow in favor of phased approach

---

## Usage

```bash
/build "feature-or-system-description"
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `feature-or-system-description` | Yes | - | What to implement (must match existing TDD) |

---

## Behavior

### 1. Validate Prerequisites

Check that design artifacts exist:

```bash
# Look for TDD
find /docs/design -name "TDD-{feature-slug}.md"

# Look for PRD
find /docs/requirements -name "PRD-{feature-slug}.md"
```

**If TDD not found**: Error and suggest using `/architect` first or `/task` for integrated workflow.

**If PRD not found**: Warn but proceed (TDD might be sufficient for implementation).

### 2. Invoke Principal Engineer

Once TDD confirmed, delegate to Principal Engineer:

```markdown
Act as **Principal Engineer**.

Feature: {feature-description}
PRD: /docs/requirements/PRD-{feature-slug}.md (if exists)
TDD: /docs/design/TDD-{feature-slug}.md

Implement the solution following the approved TDD:

1. Read TDD thoroughly - this is your specification
2. Read PRD for acceptance criteria context
3. Follow project standards (see `.claude/skills/standards/`)
4. Write tests first (TDD approach) or alongside implementation
5. Implement with production quality:
   - Type safety
   - Error handling
   - Logging/observability
   - Documentation
6. Verify all tests pass
7. Update implementation notes if you deviate from TDD

Guidelines:
- Build exactly what TDD specifies
- If TDD is ambiguous, document assumption in impl ADR
- If TDD has design flaw, stop and escalate to Architect
- If acceptance criteria untestable, escalate to Analyst

Deliverables:
- Implementation code
- Unit/integration tests (all passing)
- Implementation ADRs (if needed for choices within TDD)
- Updated documentation
```

**Quality Gate**: Tests pass, code follows standards, TDD fully implemented.

### 3. Implementation Complete

Display summary:

```
Implementation Complete: {feature-description}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Design Artifacts (Used):
✓ PRD: /docs/requirements/PRD-{slug}.md
✓ TDD: /docs/design/TDD-{slug}.md

Implementation Artifacts (Created):
✓ Code: {list-of-files}
✓ Tests: {list-of-test-files}
✓ Coverage: {percentage}%
✓ Implementation ADRs: {count} (if any)

Quality Checks:
✓ All tests passing
✓ TDD specification fully implemented
✓ Code follows project standards
✓ Error paths covered

Next Steps:
- Use `/qa` to validate implementation
- Or commit changes with `/commit` (if desired)
- Or use `/pr` to create pull request
```

---

## Workflow

```mermaid
graph LR
    A[/build invoked] --> B{TDD exists?}
    B -->|No| C[Error: Run /architect first]
    B -->|Yes| D[Principal Engineer]
    D --> E{TDD clear?}
    E -->|No| F[Escalate to Architect]
    E -->|Yes| G[Implement]
    G --> H[Tests Pass?]
    H -->|No| I[Fix & Retest]
    H -->|Yes| J[Implementation Complete]
    I --> H
```

---

## Deliverables

1. **Implementation code**: Production-quality source files
2. **Tests**: Unit and integration tests (all passing)
3. **Implementation ADRs**: If choices made within TDD boundaries
4. **Updated docs**: If implementation reveals documentation needs

**Does NOT produce**: PRD, TDD (those must pre-exist)

---

## Examples

### Example 1: Implement from Approved Design

```bash
/build "user authentication API service"
```

Output:
```
Feature: user authentication API service

[Prerequisites Check]
✓ TDD found: /docs/design/TDD-user-auth-api.md
✓ PRD found: /docs/requirements/PRD-user-auth-api.md

[Implementation]
✓ Principal Engineer implementing from TDD...

  Created:
  - /src/auth/authentication_handler.py
  - /src/auth/token_manager.py
  - /src/auth/user_store.py (interface)
  - /src/auth/rate_limiter.py
  - /tests/auth/test_authentication_handler.py
  - /tests/auth/test_token_manager.py
  - /tests/auth/test_rate_limiter.py

✓ All tests passing (coverage: 92%)

✓ Implementation ADR created:
  - ADR-0046: JWT Library Selection (chose PyJWT over python-jose)

Implementation complete. Ready for QA validation.

Next: Run `/qa "user authentication API"` to validate.
```

### Example 2: Build Without PRD (TDD-Only)

```bash
/build "cache invalidation module"
```

Output:
```
Feature: cache invalidation module

[Prerequisites Check]
✓ TDD found: /docs/design/TDD-cache-invalidation.md
⚠ PRD not found (proceeding with TDD only)

[Implementation]
✓ Principal Engineer implementing...

  Created:
  - /src/cache/invalidator.py
  - /src/cache/strategies.py
  - /src/cache/observer.py
  - /tests/cache/test_invalidator.py
  - /tests/cache/test_strategies.py

✓ All tests passing (coverage: 88%)

Implementation complete.

Next: Use `/qa` to validate or `/pr` to create pull request.
```

### Example 3: TDD Not Found Error

```bash
/build "new feature without design"
```

Output:
```
Error: Cannot build without TDD

Feature: new feature without design

[Prerequisites Check]
✗ TDD not found: /docs/design/TDD-new-feature-without-design.md
✗ Cannot implement without design specification

Suggestions:
1. Run `/architect "new feature without design"` to create TDD first
2. Run `/task "new feature without design"` for integrated workflow
3. Verify feature name matches existing TDD file name

Current TDD files:
- /docs/design/TDD-user-auth-api.md
- /docs/design/TDD-cache-invalidation.md
- /docs/design/TDD-data-platform.md
```

### Example 4: Implementation Finds Design Flaw

```bash
/build "payment processor"
```

Output:
```
Feature: payment processor

[Prerequisites Check]
✓ TDD found: /docs/design/TDD-payment-processor.md
✓ PRD found: /docs/requirements/PRD-payment-processor.md

[Implementation]
⚠ Principal Engineer found design issue:

Issue: TDD specifies synchronous payment processing, but PRD requires
       idempotency and retry logic. These are incompatible - sync calls
       cannot safely retry without double-charging risk.

Escalating to Architect for design revision.

Suggested fix:
- Switch to async processing with idempotency keys
- Update TDD to include job queue and status polling

Build halted pending TDD update.

Next:
1. Architect updates TDD with async design
2. Re-run `/build "payment processor"` after TDD revision
```

---

## When to Use vs Alternatives

| Use /build when... | Use alternative when... |
|-------------------|-------------------------|
| TDD approved and exists | No TDD yet → Use `/architect` first |
| Phased workflow (design then code) | Want integrated workflow → Use `/task` |
| Design has been reviewed | Design + implementation together → Use `/task` |
| Multiple people (designer ≠ implementer) | Single person doing both → Use `/task` |

### /architect + /build vs /task

**Two-phase** (`/architect` then `/build`):
- Design approval gate
- Separate designer from implementer
- Formal architecture review
- Better for complex/uncertain systems

**Single-phase** (`/task`):
- Faster for obvious designs
- One person owns full lifecycle
- Less overhead
- Better for well-understood patterns

### /build vs /task

- `/build`: Implement from **existing TDD**
- `/task`: **Create** PRD + TDD + Code + QA

---

## Complexity Level

**LOW** - This command:
- Invokes 1 agent (Principal Engineer)
- Assumes design pre-exists
- Produces implementation only
- No QA validation in this command

**Recommended for**:
- Implementing approved designs
- Following up after design review
- Phased development workflow
- When designer and implementer are different people

**Not recommended for**:
- Ad-hoc features without design (use `/task`)
- Simple scripts (use `/task --skip-tdd`)
- When you want integrated workflow (use `/task`)
- Urgent fixes (use `/hotfix`)

---

## Prerequisites

- **TDD must exist** at `/docs/design/TDD-{feature-slug}.md`
- PRD recommended but optional
- 10x-dev-pack or team with Principal Engineer
- TDD has been reviewed and approved

---

## Success Criteria

- Implementation matches TDD specification
- All tests passing
- Code follows project standards
- Error handling complete
- Ready for QA validation

---

## State Changes

### Files Created

| File Type | Location | Always? |
|-----------|----------|---------|
| Source code | Project-specific | Yes |
| Test files | Project-specific | Yes |
| Implementation ADRs | `/docs/decisions/ADR-{N}-{slug}.md` | As needed |

### Files Read (Not Created)

| File Type | Location | Required? |
|-----------|----------|-----------|
| TDD | `/docs/design/TDD-{slug}.md` | Yes (errors if missing) |
| PRD | `/docs/requirements/PRD-{slug}.md` | No (warns if missing) |

---

## Related Commands

- `/architect` - Create TDD before using /build (prerequisite)
- `/qa` - Validate implementation after /build
- `/task` - Integrated workflow (alternative to architect + build)
- `/pr` - Create pull request after implementation
- `/commit` - Commit changes after implementation

---

## Related Skills

- [10x-workflow](../10x-workflow/SKILL.md) - Agent coordination patterns
- [documentation](../documentation/SKILL.md) - TDD/ADR templates
- [standards](../standards/SKILL.md) - Code quality conventions

---

## Notes

### Implementation-Only Philosophy

`/build` is opinionated: **implementation follows design**.

If TDD has issues, stop and fix the design. Don't work around bad design in implementation. This discipline maintains design/implementation separation.

### When Principal Engineer Escalates

Engineer may escalate during implementation:

**To Architect** (design issues):
- TDD ambiguous on critical points
- Design won't work as specified
- Interface contracts unclear

**To Analyst** (requirements issues):
- Acceptance criteria untestable
- Requirements conflict discovered

When escalation happens:
1. Implementation pauses
2. Issue documented
3. Appropriate agent updates documentation
4. Re-run `/build` after fixes

### Implementation ADRs

Engineer may create ADRs during implementation for:
- Choices within TDD boundaries (which library, data structure, algorithm)
- Clarifications when TDD ambiguous
- Deviations from TDD (with justification)

These are "implementation ADRs" separate from "architectural ADRs" created during design.

### Pairing with /qa

After `/build` completes, use `/qa` to validate:

```bash
/build "feature"
# Implementation complete

/qa "feature"
# Validation catches edge cases

# If issues found:
/build "feature"  # Re-implement fixes
/qa "feature"     # Re-validate
```

This build → validate → fix cycle continues until QA approves.

---

## Error Cases

| Error | Condition | Resolution |
|-------|-----------|------------|
| TDD not found | No design exists | Run `/architect` first or use `/task` |
| TDD ambiguous | Can't implement unclear spec | Escalate to Architect for TDD update |
| Tests failing | Implementation bugs | Engineer fixes, reruns tests |
| Design flaw discovered | TDD won't work | Escalate to Architect, halt build |
| Missing Engineer agent | Team doesn't have engineer | Switch to 10x-dev-pack with `/10x` |

---

## Integration with Sessions

Works with or without sessions:

**Phased workflow with sessions**:
```bash
/start "Auth system"
/architect "authentication service"
/park
# After design review and approval...
/resume
/build "authentication service"
/qa "authentication service"
/wrap
```

**Ad-hoc implementation**:
```bash
/build "authentication service"
# Standalone implementation from existing TDD
```

---

## Metrics to Track

- Time from TDD approval to implementation complete
- Test coverage achieved
- Number of TDD clarifications needed
- Defects found in QA (indicates implementation quality)
- Implementation ADRs created (indicates TDD clarity)
