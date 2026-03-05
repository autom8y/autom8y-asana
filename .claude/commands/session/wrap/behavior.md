---
user-invocable: false
---

# /wrap Behavior Specification

> Full step-by-step sequence for completing a work session.

## Behavior Sequence

### 1. Pre-flight Validation

Apply [Session Resolution Pattern](../shared/session-resolution.md):
- Requires: Active session (not parked)
- Verb: "wrap"
- Auto-resume offer: Yes (offer to resume if parked)

See [session-validation](../common/session-validation.md) for patterns.

### 2. Run Quality Gates (unless --skip-checks)

Validate artifacts based on session complexity. See [quality-gates.md](quality-gates.md).

Quality gates run in order:
1. PRD Quality Gate (all complexity levels)
2. TDD Quality Gate (MODULE+)
3. Code Quality Gate (if engineer was last_agent)
4. Validation Quality Gate (if qa was last_agent)

If any gate fails: Surface issues, offer resolution options.

### 3. Optional: Invoke QA for Final Review

If `last_agent` is not `qa-adversary`:
- Offer final QA review before wrapping
- If yes: Invoke QA Adversary via Task tool
- Wait for response; abort if issues found

### 4. Invoke Moirai (Atropos) for Wrap Ceremony

Session wrap is managed via the Moirai (Atropos - the Cutter):

```
Task(moirai, "wrap_session

Session Context:
- Session ID: {current session}
- Session Path: .sos/sessions/{session-id}/SESSION_CONTEXT.md")
```

**The Moirai (Atropos) will**:
1. Invoke `ari session wrap` to generate WHITE_SAILS confidence signal
2. Validate quality gate: **BLOCKS if sails are BLACK** (unless --force)
3. Transition session state to ARCHIVED
4. Record wrap in audit trail
5. Return structured response with sails metadata

**Prerequisites Enforced by Atropos**:
- Session must be ACTIVE (not PARKED)
- If PARKED, Atropos returns LIFECYCLE_VIOLATION with hint to resume first
- `--override=reason` can bypass prerequisites if explicitly requested

**WHITE_SAILS Quality Gate**:
- **WHITE sails**: All proofs pass, no open questions → Wrap succeeds
- **GREY sails**: Some proofs missing or open questions → Wrap succeeds with warning
- **BLACK sails**: Critical failures, major blockers → **Wrap blocked**
  - Use `--force` to override (logged and flagged)
  - Example: `Task(moirai, "wrap_session --force")`

**Additional Error Handling**:
- If quality gates fail (checked by skill BEFORE invoking Moirai), offer options
- If PARKED, offer to auto-invoke `/resume` then retry wrap
- If BLACK sails, display blockers and offer fix/override options

See [Moirai agent](~/.claude/agents/moirai.md) and [Atropos skill](~/.claude/skills/moirai/atropos.md) -- not yet implemented, see .ledge/specs/TDD-fate-skills.md for full WHITE_SAILS algorithm.

### 5. Generate Session Summary

Create comprehensive summary. See [session-summary.md](session-summary.md).

Summary includes:
- Session metadata (ID, duration, complexity)
- Accomplishments and artifacts
- Key decisions and ADRs
- Quality metrics and test results
- Workflow history (handoffs, parks)
- Next session starting point

### 6. Archive Session Directory

Archival is performed by Ariadne (`ari session wrap`) as part of the wrap ceremony.

The session directory is moved from:
```
.sos/sessions/{session_id}/ → .sos/archive/{session_id}/
```

Note: Archival is handled by `ari` binary, not by the skill directly.

### 7. Save Session Summary

Write to `/docs/sessions/SUMMARY-{session_id}.md`

### 8. Update Session Index

Append entry to `/docs/sessions/INDEX.md`:
```markdown
| Date | Session ID | Initiative | Complexity | Duration | Artifacts |
```

Create index if it doesn't exist.

### 9. Confirmation

Display:
- Session name and duration
- Quality gate status
- Artifacts delivered
- Summary location
- Next session starting point

---

## State Changes

### Files Created

- `/docs/sessions/SUMMARY-{session_id}.md` - Summary report
- `/docs/sessions/INDEX.md` - Session index (if first wrap)
- `.sos/archive/{session_id}/` - Archived directory

### Files Modified

- `/docs/sessions/INDEX.md` - New entry appended

### Files Deleted/Moved

- `.sos/sessions/{session_id}/` - Removed or moved to archive

---

## Error Cases

| Error | Condition | Resolution |
|-------|-----------|------------|
| No active session | Session missing | Already completed or never started |
| Quality gates failing | Artifacts incomplete | Fix issues or use --skip-checks |
| Session parked | `parked_at` set | Use `/resume` first |
| Git dirty | Uncommitted changes | Commit or use --skip-checks |
| Tests failing | Test suite errors | Fix tests or use --skip-checks |

---

## Design Notes

### Why Archive by Default?

Preserves audit trail, debugging context, and compliance requirements. Deletion available but discouraged.

### Why Session Index?

Provides discoverability, metrics tracking, and project history - "git log for work sessions."
