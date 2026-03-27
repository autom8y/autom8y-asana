---
name: dion
description: "Cross-session knowledge synthesis from archived sessions via Dionysus. Reads .sos/archive/ and produces domain-scoped .sos/land/{domain}.md files. Use /land for the full pipeline (archive + synthesis + .know/ refresh); use /dion for synthesis-only postmortem."
argument-hint: "[--domain=DOMAIN] [--force]"
allowed-tools: Bash, Read, Glob, Grep, Task, AskUserQuestion
model: opus
---

# /dion -- Cross-Session Knowledge Synthesis

Standalone postmortem synthesis command. Reads `.sos/archive/` and writes `.sos/land/{domain}.md` via Dionysus. This is Stage 2 of `/land` extracted as a standalone command.

**Relationship to /land**:
- `/land` = full pipeline (Stage 1 inventory + Stage 2 synthesis + Stage 3 .know/ refresh)
- `/dion` = synthesis only (Stage 1 inventory + Stage 2 synthesis, no .know/ refresh)
- `/land --skip-know` is equivalent to `/dion`

This command runs in the main thread (requires Task tool for Dionysus dispatch).

## Pre-flight: Dionysus Availability

Check if dionysus is currently available:
1. Run `ls ~/.claude/agents/dionysus.md 2>/dev/null` via Bash
2. If file exists: proceed to Stage 1
3. If file missing:
   a. Run `ari agent summon dionysus` via Bash
   b. Tell user: "Dionysus summoned. Restart CC to activate, then re-run /dion."
   c. STOP — do not attempt Agent("dionysus") until restart

## Stage 1: Parse Arguments and Verify Archives

### 1. Parse Arguments

- `--domain=DOMAIN`: Optional. One of `initiative-history`, `scar-tissue`, `workflow-patterns`, `all`. Default: `all`.
- `--force`: Skip confirmation when existing land files would be overwritten.

If `--domain` is present, validate it against the allowed list. If invalid: ERROR "Invalid domain '{value}'. Must be one of: initiative-history, scar-tissue, workflow-patterns, all." STOP.

### 2. Verify Archives Exist

```
Bash("test -d .sos/archive && ls .sos/archive/ | head -1")
```

If `.sos/archive/` does not exist or is empty: print "No archived sessions found. Run `ari session wrap` to archive completed sessions first." STOP.

### 3. Inventory Archives

Run the CLI to enumerate available archives:

```
Bash("cd {project_root} && ari land synthesize -o json")
```

Parse the JSON output. The shape is:

```json
{
  "status": "ready|no-archive|empty",
  "domain": "all",
  "sessions": [
    {
      "session_id": "session-YYYYMMDD-HHMMSS-XXXXXXXX",
      "initiative": "...",
      "complexity": "PATCH|MODULE|SYSTEM|INITIATIVE",
      "active_rite": "...",
      "created_at": "2026-03-02T11:22:13Z",
      "archived_at": "2026-03-02T11:57:17Z",
      "has_events": true,
      "events_bytes": 6107,
      "has_sails": true
    }
  ],
  "land_dir": ".sos/land",
  "existing_land_files": [
    {
      "domain": "initiative-history",
      "path": ".sos/land/initiative-history.md",
      "generated_at": "2026-03-05T18:00:00Z",
      "sessions_synthesized": 10
    }
  ],
  "message": "..."
}
```

Handle empty states:
- If `status` is `"no-archive"`: print "No archive directory found. Run `ari session wrap` to archive a completed session first." STOP.
- If `status` is `"empty"`: print "No archived sessions found. Run `ari session wrap` to archive a completed session first." STOP.
- If `sessions` array is empty (defensive check): same message as "empty". STOP.

## Stage 2: Dionysus Synthesis

### 4. Check Existing Land Files

If `existing_land_files` is non-empty AND `--force` is NOT set:

Print a summary of what exists:

```
Existing land files found:
  initiative-history.md (generated: 2026-03-05, sessions: 10)
  scar-tissue.md (generated: 2026-03-05, sessions: 10)

These files will be overwritten by synthesis. Proceed? (Dionysus uses full-rewrite strategy.)
```

Then use `AskUserQuestion` to confirm. If the user declines, STOP.

If `--force` is set, skip confirmation and proceed.

If `existing_land_files` is empty, proceed without confirmation.

### 5. Resolve Source Hash

```
Bash("git rev-parse --short HEAD")
```

Capture the output as `source_hash` (e.g., `ab9fcc6`).

### 6. Dispatch Dionysus

Extract from the inventory:
- `session_count`: length of the `sessions` array
- `session_ids`: comma-separated list of all `session_id` values
- `domain`: the effective domain (`all` if no `--domain` flag)

Dispatch Dionysus via Task tool:

```
Agent("dionysus", "Synthesize {domain} domains from archives in .sos/archive/. Source hash: {source_hash}. Session count: {session_count}. Sessions: {session_ids}.")
```

If `--domain` specifies a single domain (not `all`):

```
Agent("dionysus", "Synthesize {domain} domain from archives in .sos/archive/. Source hash: {source_hash}. Session count: {session_count}. Sessions: {session_ids}.")
```

Wait for Dionysus to return.

### 7. Verify Output

After Dionysus returns, verify land files were written:

```
Bash("ls -la .sos/land/*.md 2>/dev/null || echo 'NO_LAND_FILES'")
```

If no land files exist after synthesis, report the error from Dionysus and STOP.

### 8. Display Summary

Print the summary returned by Dionysus (structured table with domains, file paths, session counts, confidence scores, and status).

Then print:

```
To integrate land files into .know/, run:
  /land --know-only
```

## Error Handling

| Scenario | Action |
|----------|--------|
| No archives | Print message. STOP. |
| `ari land synthesize` fails | ERROR: "ari land synthesize failed. Ensure ari is built and on PATH. Run: CGO_ENABLED=0 go build ./cmd/ari" STOP. |
| `ari land synthesize` returns "stub" status | Stale binary. Run: `CGO_ENABLED=0 go build -o ./ari ./cmd/ari && cp ./ari $(which ari)` |
| JSON parse failure | ERROR: "Could not parse inventory JSON. Run `ari land synthesize` manually to diagnose." STOP. |
| Dionysus Task fails | Report the error. Suggest running with a single domain to isolate the issue. |

## Anti-Patterns

- **Running Dionysus without inventory**: Always run `ari land synthesize -o json` first. The inventory provides session count, IDs, and existing land file state that Dionysus needs for context.
- **Passing raw JSON to Dionysus**: Dionysus expects a natural-language prompt with extracted parameters. Do NOT paste the full JSON inventory into the Task prompt.
- **Skipping post-synthesis verification**: Always verify land files exist after Dionysus returns.
- **Dispatching multiple Dionysus instances**: Dionysus handles multi-domain synthesis internally. Dispatch ONE Task, even for `all` domains.

## Closure: Dionysus Dismissal

After synthesis completes (or stops on error):

1. Run `ari agent dismiss dionysus` via Bash
2. Note: dismissal takes effect on next CC restart (or session end via autopark safety net)
