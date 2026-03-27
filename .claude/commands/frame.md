---
name: frame
description: "Invoke myron to decompose initiatives into workstreams or frame rite handoffs. Produces .sos/wip/frames/{slug}.md."
argument-hint: "<brief>"
allowed-tools: Read, Glob, Grep, Write, Task, Skill
model: opus
---

# /frame -- Initiative Framing

Dispatches myron to analyze the current conversation and codebase state, producing a structured framing document that can feed directly into `/sos start`, `/sprint`, or `/rite` invocations.

## Context

This command runs in the main thread. Main-thread execution is required because myron needs full visibility into the conversation history -- a forked context would lose the conversation that makes framing meaningful. Single Task dispatch, no Argus pattern.

## Pre-flight

1. **Parse `$ARGUMENTS`**:
   - Treat the full argument string as the user's brief verbatim.
   - If empty: ERROR "Usage: /frame <brief> -- Provide a short description of the initiative or handoff to frame."

2. **Normalize to slug**:
   - Convert the brief to kebab-case: lowercase, spaces to hyphens, strip non-alphanumeric except hyphens.
   - Truncate to 60 characters if longer.
   - The output path will be: `.sos/wip/frames/{slug}.md`

3. **Ensure output directory exists**:
   - Write a placeholder or use Bash: `mkdir -p .sos/wip/frames`
   - This is a side effect -- execute it before the Task dispatch.

4. **Read session context** (if available):
   - Session context is injected via hooks at session start, not stored at a fixed file path.
   - Check for an active session by looking at `.sos/sessions/` for the most recent active session's `SESSION_CONTEXT.md`.
   - If it exists, read it and extract: active rite, sprint name/number, current phase, recent decisions.
   - If it does not exist: note "no active session" -- framing proceeds without session context.
   - Do NOT call `ari` commands or run shell introspection to discover session state.

## Myron Dispatch

Construct the Task prompt and dispatch myron. Include everything myron needs to produce a useful framing document without asking clarifying questions.

```
Task(subagent_type="myron", prompt="
## Framing Request

### User's Brief

{brief verbatim from $ARGUMENTS}

### Session Context

{If SESSION_CONTEXT.md was found:}
- Active rite: {rite}
- Sprint: {sprint}
- Phase: {phase}
- Recent decisions: {summary from SESSION_CONTEXT.md}

{If no session context:}
- No active session. Frame as a standalone initiative.

### Your Directive

Analyze the conversation history above and the user's brief to produce a framing document.

The framing document should decompose the initiative into actionable workstreams, identify the right starting point, and end with concrete suggested next commands (e.g., `/sos start`, `/sprint`, `/rite`, `/go` invocations the user can run immediately).

For INITIATIVE complexity or cross-rite scope (multiple rites involved), include `/shape "{slug}"` as a recommended next step in the ## Next Commands section with a note: "(recommended for cross-rite processions — produces the execution shape for Potnia orchestration)". For TASK or MODULE complexity within a single rite, omit the /shape suggestion.

You have full discretion over the framing document's structure -- there are no prescribed sections. Design the schema that best serves this specific initiative.

### Output

Write the framing document to: .sos/wip/frames/{slug}.md

The document must end with a '## Next Commands' section listing the exact commands the user should run next (with arguments), in priority order.
")
```

## Report

After myron returns:

1. Confirm the artifact was written:
   ```
   Read(".sos/wip/frames/{slug}.md", limit=20)
   ```

2. Display to the user:
   ```
   ## Frame: .sos/wip/frames/{slug}.md

   {myron's suggested next commands, extracted from the ## Next Commands section}

   Read the full framing document: .sos/wip/frames/{slug}.md
   ```

If the file was not written (myron did not produce output at the expected path), WARN: "myron did not write the expected file. Check myron's output above for the framing document."

## Error Handling

| Scenario | Action |
|----------|--------|
| No `$ARGUMENTS` provided | ERROR with usage message |
| SESSION_CONTEXT.md unreadable | Proceed without session context, note omission |
| Myron Task dispatch fails | ERROR "Framing failed: {reason}" |
| Output file not found after myron returns | WARN with path; display myron output directly |

## Anti-Patterns

- **Reading source files yourself**: You are the dispatcher. Let myron observe the codebase and conversation. Do not pre-load architecture files or run codebase scans.
- **Prescribing the document schema**: Myron has full discretion over artifact structure. The only required section is `## Next Commands`.
- **Running ari commands for session state**: Only read SESSION_CONTEXT.md if it exists. Do not shell out to discover session information.
- **Forking context**: This dromenon intentionally runs in the main thread. Do not add `context: fork`.
