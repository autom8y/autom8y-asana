---
name: discover
description: "Run Myron feature discovery scan across the codebase or a targeted scope. Produces a glint report in .sos/wip/glints/."
argument-hint: "[codebase|directory:{path}|package:{name}|recent|--rite {target}]"
allowed-tools: Bash, Read, Write, Glob, Agent
model: opus
---

# /discover

> Feature discovery via Myron -- the wide-scan signal detection agent.

## Arguments

Parse the user's input to determine scope:
- No args or `codebase` -> full codebase scan
- `directory:{path}` -> scan a specific directory tree
- `package:{name}` -> scan a specific Go package
- `recent` -> scan files changed in last 20 commits
- `--rite {target}` or `rite:{target}` -> rite scan mode (scan a single rite's artifact tree)

Store the parsed scope as `{scope}`. Derive `{scope-slug}` for file naming:
- `codebase` -> `full`
- `directory:internal/session` -> `internal-session`
- `package:internal/materialize` -> `internal-materialize`
- `recent` -> `recent`
- `--rite forge` or `rite:forge` -> `rite-forge` (scope_type: `rite`)

## Pre-flight: Agent Availability

Check if Myron is currently available:

1. Run `ls ~/.claude/agents/myron.md 2>/dev/null` via Bash <!-- HA-CHAN: checks harness-specific agent installation path -->
2. If file exists: proceed to Dispatch
3. If file missing:
   a. Run `ari agent summon myron` via Bash
   b. Tell user: "Myron summoned. Restart CC to activate, then re-run /discover."
   c. STOP -- do not attempt Agent("myron") until restart

## Validation (rite scope only)

If scope_type is `rite`, validate the target before dispatch:

1. Check `rites/{target}/manifest.yaml` exists:
   ```
   Bash("ls rites/{target}/manifest.yaml 2>/dev/null")
   ```
2. If the file does NOT exist:
   a. List available rites: `Bash("ls rites/")`
   b. Print error: "Rite '{target}' not found. Available rites: [{comma-separated list from ls}]"
   c. STOP -- do not dispatch Myron

## Dispatch

### Standard dispatch (codebase, directory, package, recent)

Invoke Myron with the parsed scope:

```
Agent("myron", "Scan scope: {scope}. Produce a glint report following your scan protocol. Output the full glint report (YAML frontmatter + markdown body) as your final response.")
```

### Rite-scan dispatch (--rite {target})

Invoke Myron with the rite scope:

```
Agent("myron", "Scan scope: rite:{target}. Target rite directory: rites/{target}/. Produce a Rite Glint Report following your rite-scan protocol. Output the full glint report (YAML frontmatter + markdown body) as your final response.")
```

Wait for Myron to return the glint report as its response.

## Capture

After Myron returns the glint report:

1. Ensure the glints directory exists:
   ```
   Bash("mkdir -p .sos/wip/glints")
   ```

2. Compute the output filename:
   - Date: `Bash("date -u +%Y-%m-%d")`
   - Filename: `glint-{scope-slug}-{YYYY-MM-DD}.md`
   - Full path: `.sos/wip/glints/glint-{scope-slug}-{YYYY-MM-DD}.md`

3. Write the report. Check if the file already exists first:
   - If it exists: `Read(".sos/wip/glints/glint-{scope-slug}-{YYYY-MM-DD}.md")`
   - Then: `Write(".sos/wip/glints/glint-{scope-slug}-{YYYY-MM-DD}.md", {myron-output})`

4. Verify the write:
   - `Read(".sos/wip/glints/glint-{scope-slug}-{YYYY-MM-DD}.md", limit=10)`

5. Print: "Glint report written to .sos/wip/glints/glint-{scope-slug}-{YYYY-MM-DD}.md"

6. Parse and summarize the frontmatter: display glint_count and the summary breakdown (audit, document, investigate, dismiss counts).

## Closure

After capture:

1. Run `ari agent dismiss myron` via Bash
2. Print: "Myron dismissed. Takes effect on next CC restart."

## Notes

- The `--audit` flag (auto-dispatch theoros on AUDIT glints) is deferred. Ship /discover standalone first.
- Myron is read-only (disallowedTools: Write, Edit). This dromenon writes the report.
- Glint reports are ephemeral (`.sos/` is gitignored). They persist for the session lifecycle.
- If Myron's output does not contain YAML frontmatter, write it as-is and note: "Warning: report missing structured frontmatter."
