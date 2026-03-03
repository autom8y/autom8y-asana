---
user-invocable: false
---

# /handoff Examples

> Usage scenarios for transferring work between agents.

## Example 1: Design to Implementation

```bash
/handoff principal-engineer
```

Output:
```
Handoff: architect → principal-engineer

Generating handoff note...
✓ TDD reviewed: .ledge/specs/TDD-dark-mode.md
✓ ADRs captured: 2 architecture decisions
✓ Design approved by user

Handoff complete: architect → principal-engineer

Session: Add dark mode toggle
New phase: implementation
Handoff count: 1

Handoff summary:
✓ Artifacts: 3 delivered (PRD, TDD, 2 ADRs)
✓ Blockers: 0 active
✓ Context: Preserved in SESSION_CONTEXT

Principal Engineer is reviewing TDD and ready to implement.

Next: Create component structure following TDD specifications
```

---

## Example 2: Implementation to QA

```bash
/handoff qa-adversary "All acceptance criteria implemented, tests passing"
```

Output:
```
Handoff: principal-engineer → qa-adversary

Custom handoff note: All acceptance criteria implemented, tests passing

Generating handoff context...
✓ Code committed: src/theme/toggle.py, src/theme/storage.py
✓ Tests passing: 15/15 unit tests, 5/5 integration tests
✓ Type safety: mypy clean
✓ Linting: flake8 clean

Handoff complete: principal-engineer → qa-adversary

Session: Add dark mode toggle
New phase: validation
Handoff count: 2

Handoff summary:
✓ Artifacts: 6 delivered (PRD, TDD, 2 ADRs, code, tests)
✓ Blockers: 0 active
✓ Context: All acceptance criteria met per engineer

QA Adversary is reviewing implementation against PRD acceptance criteria.

Next: Create test plan and validate all requirements
```

---

## Example 3: QA Back to Engineer (Issues Found)

```bash
/handoff principal-engineer "3 defects found in edge case testing"
```

Output:
```
Handoff: qa-adversary → principal-engineer

Custom handoff note: 3 defects found in edge case testing

Generating handoff context...
✓ Test Plan created: .ledge/specs/TP-dark-mode.md
⚠ Defects found: 3 issues logged
  - Issue 1: Theme not persisted on logout
  - Issue 2: Flash of wrong theme on page load
  - Issue 3: System preference override not working

Handoff complete: qa-adversary → principal-engineer

Session: Add dark mode toggle
New phase: implementation (rework)
Handoff count: 3

Handoff summary:
✓ Artifacts: 7 delivered (includes test plan)
✓ Blockers: 3 defects to address
✓ Context: QA validation identified issues requiring fixes

Principal Engineer is reviewing defects and planning fixes.

Next: Address defect #1 (theme persistence on logout)
```

---

## Example 4: Same Agent Warning

```bash
/handoff architect
```

When `last_agent` is already `architect`:

Output:
```
⚠ Already working with architect

Session: Multi-tenant authentication
Current phase: design
Last agent: architect

No handoff needed - continuing with same agent.

To switch to a different agent, specify a different agent name.
Available agents:
- requirements-analyst
- principal-engineer
- qa-adversary
```
