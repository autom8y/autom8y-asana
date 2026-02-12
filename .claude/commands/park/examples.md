---
user-invocable: false
---

# /park Examples

> Usage scenarios for pausing work sessions.

## Example 1: Simple Park

```bash
/park
```

Output:
```
Session parked: Add dark mode toggle
Parked at: 2025-12-24 15:30:00
Reason: Manual park

Current state preserved:
✓ Phase: design
✓ Last agent: architect
✓ Artifacts: 2 files (PRD, TDD)
✓ Git status: Clean

To resume: /resume
```

---

## Example 2: Park with Reason

```bash
/park "Waiting for design review from stakeholders"
```

Output:
```
Session parked: Multi-tenant authentication
Parked at: 2025-12-24 10:15:00
Reason: Waiting for design review from stakeholders

Current state preserved:
✓ Phase: design
✓ Last agent: architect
✓ Artifacts: 4 files (PRD, TDD, 2 ADRs)
✓ Git status: Clean
✓ Blockers: 1 (design review pending)

To resume: /resume
```

---

## Example 3: Park with Uncommitted Work

```bash
/park "End of day - implementation in progress"
```

Output:
```
Session parked: API retry logic
Parked at: 2025-12-24 17:45:00
Reason: End of day - implementation in progress

Current state preserved:
✓ Phase: implementation
✓ Last agent: engineer
✓ Artifacts: 3 files (PRD, code files)
⚠ Git status: Dirty (5 uncommitted files)
  - src/api/client.py (modified)
  - src/api/retry.py (new)
  - tests/test_retry.py (new)
  - src/config.py (modified)
  - README.md (modified)

⚠ Reminder: Commit or stash changes before resuming to avoid conflicts.

To resume: /resume
```
