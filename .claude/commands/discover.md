---
name: discover
description: "Run Myron feature discovery scan across the codebase or a targeted scope. Produces a glint report in .sos/wip/glints/."
argument-hint: "[codebase|directory:{path}|package:{name}|recent]"
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

Store the parsed scope as `{scope}`. Derive `{scope-slug}` for file naming:
- `codebase` -> `full`
- `directory:internal/session` -> `internal-session`
- `package:internal/materialize` -> `internal-materialize`
- `recent` -> `recent`

## Pre-flight: Agent Availability

Check if Myron is currently available:

1. Run `ls ~/.claude/agents/myron.md 2>/dev/null` via Bash
2. If file exists: proceed to Dispatch
3. If file missing:
   a. Run `ari agent summon myron` via Bash
   b. Tell user: "Myron summoned. Restart CC to activate, then re-run /discover."
   c. STOP -- do not attempt Agent("myron") until restart

## Dispatch

Invoke Myron with the parsed scope:

```
Agent("myron", "Scan scope: {scope}. Produce a glint report following your scan protocol. Output the full glint report (YAML frontmatter + markdown body) as your final response.")
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
