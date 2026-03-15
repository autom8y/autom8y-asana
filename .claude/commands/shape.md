---
name: shape
description: "Produce execution shape for an initiative — orchestration plan for Potnia. Produces .sos/wip/frames/{slug}.shape.md."
argument-hint: "<initiative-slug-or-brief>"
allowed-tools: Read, Glob, Grep, Write, Task, Skill, Bash
model: opus
---

# /shape -- Initiative Execution Shape

Dispatches Pythia to analyze the initiative context and produce a structured execution shape -- the orchestration plan that tells Potnia how to execute across sprints, rites, and agent rosters. Shape files are the execution companion to a frame's problem decomposition.

## Context

This command runs in the main thread. Main-thread execution is required because Pythia needs full visibility into the conversation history -- a forked context would lose the initiative discussion that makes shape production meaningful. Single Task dispatch, no Argus pattern.

## Pre-flight

1. **Parse `$ARGUMENTS`**:
   - Treat the full argument string as the initiative slug or brief verbatim.
   - If empty: ERROR "Usage: /shape <initiative-slug-or-brief> -- Provide the initiative slug or a short description to shape."

2. **Normalize to slug**:
   - Convert to kebab-case: lowercase, spaces to hyphens, strip non-alphanumeric except hyphens.
   - Truncate to 60 characters if longer.
   - Output path: `.sos/wip/frames/{slug}.shape.md`

3. **Ensure output directory exists**:
   - `mkdir -p .sos/wip/frames`
   - Execute before Task dispatch.

4. **Check for frame**:
   - Attempt to Read `.sos/wip/frames/{slug}.md`.
   - If it exists: include full content as context to Pythia. The frame provides decomposition, spikes, and artifact locations that the shape should reference rather than re-derive.
   - If it does not exist: note "no frame -- Pythia will decompose from brief and conversation history."

5. **Read session context** (if available):
   - Check `.sos/sessions/` for the most recent active session's `SESSION_CONTEXT.md`.
   - If it exists: extract active rite, sprint, phase, recent decisions.
   - If it does not exist: note "no active session."
   - Do NOT call `ari` commands or run shell introspection to discover session state.

## Pythia Dispatch

Construct the Task prompt and dispatch Pythia. The prompt encodes the hard-won patterns for shape production so the user does not need to specify them.

```
Task(subagent_type="pythia", prompt="
## Shape Production Request

### Initiative Brief
{brief verbatim from $ARGUMENTS}

### Frame Context
{If frame exists: full content of .sos/wip/frames/{slug}.md}
{If no frame: 'No frame exists. Decompose the initiative from this brief and the conversation history above.'}

### Session Context
{If SESSION_CONTEXT.md was found:}
- Active rite: {rite}
- Sprint: {sprint}
- Phase: {phase}
- Recent decisions: {summary}

{If no session context:}
- No active session. Shape as a standalone initiative.

### Your Directive

Produce an execution shape file -- the orchestration plan that tells Potnia how to execute this initiative across sprints, rites, and agent rosters.

**First**: Load the shape-schema skill for canonical structure and section reference:
Skill('shape-schema')

**Second**: Discover which rites this initiative touches:
- Load Skill('rite-discovery') for the current rite inventory
- Run `ari ask -o json '<initiative keywords>'` for rite routing recommendations
- For each recommended rite: Read `rites/{name}/orchestrator.yaml` for agent roster and workflow phases

**Third**: Produce the shape file following these principles:

1. POTNIA THROUGHLINE: The Initiative Thread section is the shape's consciousness. The throughline is a one-sentence invariant that every PT-NN checkpoint evaluates against. Not 'is everything OK?' but 'does X satisfy Y?' Every checkpoint question must reference a specific aspect of the throughline with a measurable answer.

2. NON-PRESCRIPTIVE SPRINT INTERNALS: Define the mission and constraints for each sprint, NOT the agent task list. Potnia coordinates; agents discover. The agent roster comes from orchestrator.yaml -- list which agents participate, not what they do step-by-step. Entry criteria gate sprint start. Exit criteria define 'done'. Exit artifacts are the durable outputs.

3. CROSS-RITE HANDOFF ARTIFACTS: When the initiative transitions between rites, the outgoing rite produces a handoff artifact at .ledge/spikes/{slug}-{rite}-handoff.md or .ledge/decisions/{slug}-{decision}.md. The incoming rite's Potnia loads this as entry context. Define what each handoff produces, what the next rite consumes, and how to verify completeness.

4. EMERGENT BEHAVIOR BOUNDARIES: Be explicit about three categories -- Prescribed (must follow, non-negotiable constraints), Emergent (agent discretion, local optimization), and Out of Scope (must not touch). Agents need freedom to make local decisions within guard rails.

5. CONTEXT LOADING: For each sprint, specify the files to Read() at session start -- spike references, prior sprint artifacts, configuration files. Reference specific paths, not generic instructions. If a frame exists, reference spike and artifact locations from the frame rather than re-deriving them.

6. EXECUTION SEQUENCE: Provide the full command flow including rite transitions (ari sync --rite=X), session lifecycle (/sos start, /sprint, /sos wrap), and checkpoint evaluations. Every sprint, transition, and checkpoint must appear as a phase.

7. PARALLEL OPPORTUNITIES: Identify which sprints can execute in parallel (independent inputs and outputs) and which are strictly sequential (one depends on another's artifacts). Record this in the Critical Path section when applicable.

### Output

Write the shape file to: .sos/wip/frames/{slug}.shape.md

Include YAML frontmatter per the shape-schema specification:
- type: shape
- initiative: {slug}
- frame: {path to frame or null}
- created: {today's date}
- rite: {primary rite slug or 'cross-rite'}
- complexity: {MODULE or INITIATIVE}
- scope: rites list and sprint count
- cross_rite_consultations: from/to/artifact (if multi-rite)

All structured data in YAML code blocks. Machine-parseable sprint definitions. Numbered PT-NN checkpoints. The shape is a Potnia-first document.
")
```

## Report

After Pythia returns:

1. Confirm the artifact was written:
   ```
   Read(".sos/wip/frames/{slug}.shape.md", limit=20)
   ```

2. Display to the user:
   ```
   ## Shape: .sos/wip/frames/{slug}.shape.md

   {Summary: rite count, sprint count, checkpoint count extracted from the shape}

   Suggested next commands:
   - `/sos start --initiative={slug}` -- begin execution
   - `/sprint 1` -- start first sprint
   - `ari sync --rite={first-rite}` -- switch to the starting rite (if cross-rite)

   Read the full shape: .sos/wip/frames/{slug}.shape.md
   ```

If the file was not written (Pythia did not produce output at the expected path), WARN: "Pythia did not write the expected shape file. Check the Pythia output above for the shape content."

## Error Handling

| Scenario | Action |
|----------|--------|
| No `$ARGUMENTS` provided | ERROR with usage message |
| SESSION_CONTEXT.md unreadable | Proceed without session context, note omission |
| Frame file not found | Proceed without frame, note "no frame" in dispatch |
| Pythia Task dispatch fails | ERROR "Shape production failed: {reason}" |
| Output file not found after Pythia returns | WARN with path; display Pythia output directly |
| `ari ask` unavailable in Pythia context | Pythia falls back to `rite-discovery` skill and manual rite inspection |

## Anti-Patterns

- **Reading rite configs yourself**: You are the dispatcher. Let Pythia discover rites via `ari ask` and `rite-discovery`. Do not pre-load orchestrator files or run codebase scans.
- **Prescribing sprint task lists**: Sprint internals are non-prescriptive. Define missions and constraints, not step-by-step agent instructions. This is Potnia's domain.
- **Creating shapes without throughline**: Every shape must have an Initiative Thread with a throughline statement. A shape without a throughline produces checkpoints that ask "is everything OK?" instead of evaluating specific success criteria.
- **Running in forked context**: This dromenon intentionally runs in the main thread. Do not add `context: fork`. Pythia needs the conversation history.
- **Pre-loading shape-schema yourself**: Pythia loads it on-demand via `Skill("shape-schema")`. The dromenon should not read or summarize the schema.
- **Re-deriving frame decisions**: If a frame exists, the shape references its spikes and artifacts. Do not re-analyze what the frame already decomposed.
