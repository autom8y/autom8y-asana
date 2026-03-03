---
name: fray
description: Fork current session into a parallel strand with optional worktree isolation
argument-hint: "[--no-worktree] [--from=SESSION_ID]"
allowed-tools: Bash, Read
disallowed-tools: Write, Edit, NotebookEdit
disable-model-invocation: true
---

## Context
Auto-injected by SessionStart hook (project, rite, session, git).

## Your Task

Fork the current session into a parallel strand. $ARGUMENTS

## Pre-flight

1. **Active session required**:
   - Read session state from hook-injected context above
   - If no active session: ERROR "No active session to fray. Use `/start` to begin."
   - If session is PARKED: ERROR "Cannot fray a parked session. Use `/continue` first."

2. **Git repository required** (if worktree mode):
   - Verify in git repository: `git rev-parse --git-dir`
   - If not in git repo and no `--no-worktree`: WARN and add `--no-worktree`

## Behavior

### 1. Extract Session ID

**CRITICAL**: The CLI cannot discover the session automatically from a Bash subprocess.
You MUST extract the session ID from the hook-injected Session Context table above.

Look for the row: `| Session | session-YYYYMMDD-HHMMSS-XXXXXXXX |`

Store this value — you will pass it via `--from` to the CLI.

### 2. Build CLI Command

```bash
ari session fray --from <session-id> [--no-worktree]
```

| User Says | Maps To |
|-----------|---------|
| `/fray` | `ari session fray --from <session-id>` |
| `/fray --no-worktree` | `ari session fray --from <session-id> --no-worktree` |

Always pass `--from` with the session ID extracted from the context table.

### 3. Execute

Run the command via Bash. The CLI handles all state mutation:
- Parks parent session (reason: "Frayed to {child-id}")
- Creates child session inheriting initiative, complexity, rite, phase
- Creates git worktree at `/tmp/knossos-fray-*` (unless `--no-worktree`)
- Emits `session.frayed` and `session.created` events

### 3. Interpret Output

The CLI returns JSON with these fields:

| Field | Description |
|-------|-------------|
| `parent_id` | Session that was parked |
| `child_id` | New parallel session |
| `child_dir` | Session directory path |
| `fray_point` | Phase at which fork occurred |
| `worktree_path` | Worktree location (empty if `--no-worktree`) |
| `status` | Child session status (ACTIVE) |
| `created_at` | Timestamp |

### 4. Present Results

**With worktree** (default):
```
Frayed: {parent_id} -> {child_id}
Phase: {fray_point}
Worktree: {worktree_path}

Next steps:
  cd {worktree_path} && claude
  # Start working in the parallel strand

To return to parent:
  /continue   (from original directory)
```

**Without worktree** (`--no-worktree`):
```
Frayed: {parent_id} -> {child_id}
Phase: {fray_point}

The child session shares this working tree.
Parent is parked. You are now on the child strand.

To return to parent:
  /park       (park child)
  /continue   (resume parent)
```

### 5. Known Limitation

The worktree created by fray is a raw `git worktree add --detach HEAD`. It is NOT
managed by `ari worktree` and will NOT appear in `/worktree list`. To clean up:

```bash
git worktree remove {worktree_path}
```

## When to Use Fray vs Worktree

| Scenario | Use |
|----------|-----|
| Explore alternative approach mid-session | `/fray` |
| Start independent parallel work | `/worktree create` |
| Quick spike that might be discarded | `/fray --no-worktree` |
| Long-running parallel sprint | `/worktree create` + `/start` |

Fray preserves session lineage (parent/child). Worktrees are independent.

## Sigil

### On Success

If a worktree was created (default), end your response with:

🧵 frayed · next: cd {worktree_path} && claude

Use the `worktree_path` from the CLI output.

If `--no-worktree` was used, end with:

🧵 frayed · next: /go

### On Failure

❌ fray failed: {brief reason} · fix: {recovery}

Infer recovery: no active session → `/start`; session is PARKED → `/continue` first; not in git repo → initialize git; uncertain → `/consult`.
