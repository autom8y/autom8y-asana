---
user-invocable: false
---

# Quality Gates

> Validation gates for session wrap.
>
> **Note**: In addition to these skill-level quality gates, Atropos enforces a final WHITE_SAILS quality gate that blocks wrap if critical failures are detected (BLACK sails).

## PRD Quality Gate (All Complexity)

**Checks**:
- ✓ PRD file exists at documented path
- ✓ PRD contains all required sections
- ✓ Acceptance criteria are testable and specific
- ✓ No blocking questions remain

**Failure Message**:
```
⚠ Quality Gate Failure: PRD

Issues:
- PRD file not found at .ledge/specs/PRD-{slug}.md
- PRD missing required sections: {list}
- PRD has {count} unanswered blocking questions

Resolution:
1. Complete PRD before wrapping
2. Use --skip-checks to wrap anyway (not recommended)
3. Use /handoff requirements-analyst to fix PRD
```

---

## TDD Quality Gate (MODULE+)

**Checks**:
- ✓ TDD file exists at documented path
- ✓ TDD traces to PRD requirements
- ✓ All architecture decisions have ADRs
- ✓ Interfaces and data flow defined

**ADR Checks**:
- ✓ All major decisions documented
- ✓ ADRs follow template format
- ✓ Context, decision, consequences captured

**Failure Message**:
```
⚠ Quality Gate Failure: TDD/ADRs

Issues:
- TDD references 3 decisions but only 1 ADR found
- TDD missing component interfaces section
- ADR-0042 missing "Consequences" section

Resolution:
1. Complete TDD and ADRs before wrapping
2. Use /handoff architect to address issues
```

---

## Code Quality Gate (Implementation Phase)

**Triggered when**: `last_agent` is `principal-engineer`

**Checks**:
- ✓ All code committed (git status clean)
- ✓ Tests exist and passing
- ✓ Type safety validated (mypy/tsc clean)
- ✓ Linting clean

**Validation Commands**:
```bash
# Git status
git status --porcelain

# Tests (language-specific)
pytest tests/ --cov  # Python
npm test            # TypeScript
go test ./...       # Go

# Type checking
mypy src/           # Python
tsc --noEmit        # TypeScript

# Linting
flake8 src/         # Python
eslint src/         # TypeScript
golangci-lint run   # Go
```

**Failure Message**:
```
⚠ Quality Gate Failure: Implementation

Issues:
- Uncommitted changes: 3 files
- Tests failing: 2/15 failed
- mypy errors: 1 type safety issue

Resolution:
1. Commit all changes
2. Fix failing tests
3. Address type safety issues
4. Re-run /wrap
```

---

## Validation Quality Gate (QA Phase)

**Triggered when**: `last_agent` is `qa-adversary`

**Checks**:
- ✓ Test Plan exists
- ✓ All PRD acceptance criteria validated
- ✓ Edge cases covered
- ✓ All defects resolved or documented

**Failure Message**:
```
⚠ Quality Gate Failure: Validation

Issues:
- Test Plan shows 2 open defects:
  - DEF-001: Theme not persisted (Critical)
  - DEF-002: Flash of wrong theme (Medium)
- 1 acceptance criterion not tested

Resolution:
1. Address critical defects
2. Document medium/low as known issues
3. Complete validation of all criteria
```

---

## Gate Failure Options

When any gate fails, user has options:

1. **Fix and retry**: Address issues, re-run `/wrap`
2. **Skip checks**: Use `--skip-checks` (not recommended)
3. **Get help**: Use `/handoff` to appropriate agent

---

## Skip Checks Warning

```
⚠ Skipping quality gates (--skip-checks flag)

This is not recommended. Quality issues may exist.

Continue wrap without validation? [y/n]:
```

When wrapped with skip:
```
⚠ Warning: Session wrapped without quality validation.
Review artifacts manually before considering production-ready.
```

---

## WHITE_SAILS Quality Gate (Atropos)

**Triggered when**: Always, during Moirai/Atropos wrap ceremony

The final quality gate, enforced by Atropos after skill-level gates pass.

**Checks**:
- ✓ Test output logs exist and show passing tests
- ✓ Build output logs exist and show successful build
- ✓ Lint output logs exist and show clean results
- ✓ No open questions in SESSION_CONTEXT.md
- ✓ No explicit blockers declared

**Sails Color Computation**:

| Color | Criteria | Wrap Behavior |
|-------|----------|---------------|
| **WHITE** | All proofs pass, no open questions | Wrap succeeds |
| **GREY** | Some proofs missing OR open questions exist | Wrap succeeds with warning |
| **BLACK** | Critical test failures OR build failures OR explicit blockers | **Wrap BLOCKED** |

**Failure Message** (BLACK sails):
```
⚠ Quality Gate Failure: WHITE_SAILS

Sails Color: BLACK
Computed Base: BLACK

Reasons:
- explicit blockers present: black sails (do not ship)
  - Tests failing in integration suite
  - Build broken on macOS

Resolution:
1. Fix critical failures listed above
2. Re-run /wrap (Atropos will regenerate sails)
3. Use --force override ONLY for hotfixes:
   Task(moirai, "wrap_session --force")

⚠ WARNING: Force override logs the reason and flags the session.
```

**Success Message** (WHITE sails):
```
✓ WHITE_SAILS Quality Gate: PASSED

Sails Color: WHITE
All proofs collected, no open questions.
Confidence: Session work is production-ready.
```

**Warning Message** (GREY sails):
```
⚠ WHITE_SAILS Quality Gate: PASSED with warnings

Sails Color: GREY
Some proofs missing or open questions exist.
Confidence: Session work may need manual review before production.
```

---

## Quality Gate Sequence

When `/wrap` is invoked, gates run in this order:

1. **Skill-level gates** (this file) - can be skipped with `--skip-checks`
   - PRD Quality Gate
   - TDD Quality Gate (MODULE+)
   - Code Quality Gate (if last_agent = engineer)
   - Validation Quality Gate (if last_agent = qa)

2. **WHITE_SAILS Quality Gate** (Atropos) - **cannot be skipped**, only overridden with `--force`
   - Generates confidence signal
   - Blocks on BLACK sails
   - Proceeds on WHITE/GREY sails

**Key Difference**: Skill gates validate artifacts; WHITE_SAILS gate validates **confidence in the work itself** via proof collection.
