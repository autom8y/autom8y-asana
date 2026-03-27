---
name: land
description: "Full land-to-know pipeline: synthesize cross-session knowledge via Dionysus, then refresh .know/ with land injection. Replaces /dion as the single entry point for session knowledge integration."
argument-hint: "[--domain=DOMAIN] [--force] [--skip-know] [--know-only]"
allowed-tools: Bash, Read, Glob, Grep, Task, AskUserQuestion
model: opus
---

# /land -- Session Knowledge Landing Pipeline

Orchestrates the full land-to-know pipeline: inventory archived sessions via `ari land synthesize`, dispatch Dionysus to produce domain-scoped land files in `.sos/land/`, then refresh `.know/` with the new land content.

This command replaces `/dion` as the single entry point for landing session knowledge into the codebase context system. Use `/dion` for the old behavior (Stage 2 only, no .know/ refresh).

## Context

This command runs in the main thread (requires Task tool for Dionysus dispatch). The Argus Pattern requires main-thread execution because agents cannot spawn agents -- only the main thread has Task tool access.

Dionysus is a leaf agent. It reads `.sos/archive/` and writes `.sos/land/{domain}.md`. This dromenon is the orchestrator that prepares context and invokes the agent.

## Pre-flight: Dionysus Availability

Check if dionysus is currently available:
1. Run `ls ~/.claude/agents/dionysus.md 2>/dev/null` via Bash
2. If file exists: proceed to Stage 1
3. If file missing:
   a. Run `ari agent summon dionysus` via Bash
   b. Tell user: "Dionysus summoned. Restart CC to activate, then re-run /land."
   c. STOP — do not attempt Agent("dionysus") until restart

## Stage 1: Prerequisite Check

### 1. Parse Arguments

- `--domain=DOMAIN`: Optional. One of `initiative-history`, `scar-tissue`, `workflow-patterns`, `all`. Default: `all`.
- `--force`: Skip confirmation when existing land files would be overwritten, and skip expiry checks for /know.
- `--skip-know`: Run Dionysus synthesis only (Stage 2), skip .know/ refresh (Stage 3). Equivalent to the old /dion behavior.
- `--know-only`: Skip Dionysus synthesis (Stage 2), only refresh .know/ with existing land files (Stage 3).

If `--domain` is present, validate it against the allowed list. If invalid: ERROR "Invalid domain '{value}'. Must be one of: initiative-history, scar-tissue, workflow-patterns, all." STOP.

If both `--know-only` and `--skip-know` are set: ERROR "Cannot use --know-only and --skip-know together." STOP.

### 2. Verify Archives Exist

If `--know-only` is NOT set:

```
Bash("test -d .sos/archive && ls .sos/archive/ | head -1")
```

If `.sos/archive/` does not exist or is empty: print "No archived sessions found. Run `ari session wrap` to archive completed sessions first." STOP.

If `--know-only` is set, skip directly to Stage 3.

## Stage 2: Dionysus Synthesis

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

### 4. Handle Empty States

- If `status` is `"no-archive"`: print "No archive directory found. Run `ari session wrap` to archive a completed session first." STOP.
- If `status` is `"empty"`: print "No archived sessions found. Run `ari session wrap` to archive a completed session first." STOP.
- If `sessions` array is empty (defensive check): same message as "empty". STOP.

### 5. Check Existing Land Files

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

### 6. Resolve Source Hash

```
Bash("git rev-parse --short HEAD")
```

Capture the output as `source_hash` (e.g., `ab9fcc6`).

## Execution: Dispatch Dionysus

Extract from the inventory:
- `session_count`: length of the `sessions` array
- `session_ids`: comma-separated list of all `session_id` values
- `domain`: the effective domain (`all` if no `--domain` flag)

Dispatch Dionysus via Task tool:

```
Agent("dionysus", "Synthesize {domain} domains from archives in .sos/archive/. Source hash: {source_hash}. Session count: {session_count}. Sessions: {session_ids}.")
```

If `--domain` specifies a single domain (not `all`), include it:

```
Agent("dionysus", "Synthesize {domain} domain from archives in .sos/archive/. Source hash: {source_hash}. Session count: {session_count}. Sessions: {session_ids}.")
```

Wait for Dionysus to return. Dionysus will provide a structured summary table with domains, file paths, session counts, confidence scores, and status.

## Post-Synthesis (Stage 2 Completion)

### 1. Verify Output

After Dionysus returns, verify land files were written:

```
Bash("ls -la .sos/land/*.md 2>/dev/null || echo 'NO_LAND_FILES'")
```

If no land files exist after synthesis, report the error from Dionysus and STOP. Do not proceed to Stage 3 with no land files.

### 2. Display Synthesis Summary

Print the summary returned by Dionysus (it follows a structured table format). This ends Stage 2.

## Stage 3: .know/ Refresh

If `--skip-know` is set:

Print:

```
Stage 3 skipped (--skip-know).

To integrate land files into .know/:
  /know --all --force
```

STOP.

Otherwise, proceed with .know/ refresh guidance:

The land-to-know mapping (LAND_MAP) routes land files to the following .know/ domains:

```
LAND_MAP = {
  "architecture": [".sos/land/initiative-history.md"],
  "conventions": [".sos/land/workflow-patterns.md"],
  "design-constraints": [".sos/land/initiative-history.md"],
  "scar-tissue": [".sos/land/scar-tissue.md"],
  "test-coverage": [".sos/land/workflow-patterns.md"],
}
```

Print:

```
Land files are ready. Run /know to integrate them into .know/:

  /know --all --force

The updated /know step 2.5 uses the LAND_MAP to route:
  .sos/land/initiative-history.md  ->  architecture, design-constraints
  .sos/land/workflow-patterns.md   ->  conventions, test-coverage
  .sos/land/scar-tissue.md         ->  scar-tissue
```

## Pipeline Summary Report

After all stages complete (or after Stage 3 guidance is printed), output:

```
## Pipeline Complete

Stage 1: Archive inventory -- {N} sessions found in .sos/archive/
Stage 2: Dionysus synthesis -- {list of domains written, e.g. "initiative-history, scar-tissue, workflow-patterns"}
Stage 3: .know/ refresh -- {one of: "guidance printed (run /know --all --force)" | "skipped (--skip-know)" | "skipped (--know-only was the entry point)"}
```

If entry was `--know-only`, Stage 2 is listed as "skipped (--know-only)".

## Error Handling

| Scenario | Action |
|----------|--------|
| No archives (checked in Stage 1) | Print message. STOP. |
| `ari land synthesize` not found or fails | ERROR: "ari land synthesize failed. Ensure ari is built and on PATH. Run: CGO_ENABLED=0 go build ./cmd/ari" STOP. |
| `ari land synthesize` returns "stub" status | The installed ari binary is stale. Run: `CGO_ENABLED=0 go build -o ./ari ./cmd/ari && cp ./ari $(which ari)` |
| JSON parse failure | ERROR: "Could not parse inventory JSON. Run `ari land synthesize` manually to diagnose." STOP. |
| Dionysus Task fails | Report the error message. Do not proceed to Stage 3. Suggest running with a single domain to isolate the issue. |
| `--know-only` but no land files in .sos/land/ | Print warning: "No land files found in .sos/land/. Run /land without --know-only first." Continue to Stage 3 anyway (land injection will be skipped gracefully by /know). |
| `--force` + `--skip-know` | Valid combination: force-overwrite Dionysus output, skip .know/ refresh. |
| `--know-only` + `--skip-know` | ERROR: "Cannot use --know-only and --skip-know together." STOP (handled in Stage 1 argument parsing). |

## Anti-Patterns

- **Running Dionysus without inventory**: Always run `ari land synthesize -o json` first. The inventory provides session count, IDs, and existing land file state that Dionysus needs for context.
- **Passing raw JSON to Dionysus**: Dionysus expects a natural-language prompt with extracted parameters (domain, source_hash, session_count, session_ids). Do NOT paste the full JSON inventory into the Task prompt.
- **Skipping post-synthesis verification**: Always verify land files exist after Dionysus returns. Synthesis can fail silently if archives have unexpected formats.
- **Dispatching multiple Dionysus instances**: Unlike the /radar Argus Pattern, Dionysus handles multi-domain synthesis internally. Dispatch ONE Task, even for `all` domains.
- **Proceeding to Stage 3 after Dionysus failure**: If synthesis fails, the land files are stale or missing. Always STOP after a Dionysus failure rather than proceeding to /know with outdated content.

## Closure: Dionysus Dismissal

After the full /land pipeline completes (all stages finished or stopped on error):

1. Run `ari agent dismiss dionysus` via Bash
2. Note: dismissal takes effect on next CC restart (or session end via autopark safety net)
