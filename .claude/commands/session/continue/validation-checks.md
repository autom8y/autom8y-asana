---
user-invocable: false
---

# Resume Validation Checks

> Context validation for resuming parked sessions.

## Rite Consistency Check

### Purpose

Rites contain different pantheons. If session started with `10x-dev` but current rite is `docs`, expected agents may not be available.

### Check Logic

```
Read current .knossos/ACTIVE_RITE
Compare to SESSION_CONTEXT.active_rite
If different → Surface mismatch warning
```

### Mismatch Handling

```
⚠ Rite Mismatch Detected

Session started with: {session.active_rite}
Current active rite: {current ACTIVE_RITE}

This session's agents may not be available in the current rite.

Options:
1. Switch back to {session.active_rite} (recommended)
2. Continue with {current ACTIVE_RITE} (may cause issues)
3. Cancel resume

Choice [1/2/3]:
```

**Option 1**: Invoke `ari sync --rite {session.active_rite}`
**Option 2**: Continue with potential agent mismatch
**Option 3**: Abort resume

---

## Git Status Check

### Purpose

Git changes since park indicate:
1. **Concurrent work**: Files modified outside the session
2. **Merge issues**: Branch diverged, conflicts possible
3. **Stale session**: Session may no longer be relevant

### Check Logic

```
Run git status
Compare to parked_git_status from SESSION_CONTEXT
If mismatch (was clean, now dirty) → Surface warning
If new uncommitted files → List changes
```

### Change Handling

```
⚠ Git Changes Detected

Git status at park time: {parked_git_status}
Current git status: {current status}

New/modified files since park:
- {file1}
- {file2}

This may indicate:
1. Work done outside this session
2. Merge conflicts from branch updates
3. Unrelated changes

Review changes before continuing? [y/n]:
```

**If yes**: Display `git diff --stat` output
**Either way**: User decides whether to continue

---

## Agent Availability Check

### Purpose

Validate selected agent exists in current rite.

### Check Logic

```
Determine target agent:
  - --agent parameter if provided
  - Otherwise: SESSION_CONTEXT.last_agent

Check .claude/agents/{agent}.md exists
If not found → Error with agent list
```

### Error Message

```
Agent '{agent}' not found in rite '{active_rite}'.

Available agents:
- requirements-analyst
- architect
- principal-engineer
- qa-adversary

Use --agent=NAME to specify a valid agent.
```

---

## Validation Flow Summary

```
1. Pre-flight (session exists, is parked)
      ↓
2. Rite consistency check
   ├─ Match → Continue
   └─ Mismatch → User chooses action
      ↓
3. Git status check
   ├─ Clean/unchanged → Continue
   └─ Dirty/new files → User reviews
      ↓
4. Agent availability check
   ├─ Found → Continue to invoke
   └─ Not found → Error with guidance
```
