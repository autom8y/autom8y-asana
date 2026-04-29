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

## Repo-Identity Detection (ADR-pythia-shape-contract Appendix B — Option D baseline)

Before dispatching, detect the cwd-repo and check against the active session's repo:

1. Execute `git rev-parse --show-toplevel` via Bash to get the current cwd's repo root (`artifact_repo`).
2. If SESSION_CONTEXT.md was found in step 4: check whether it contains a `session_repo` field; use that value as `session_repo`. If the field is absent, treat `artifact_repo` as `session_repo`.
3. If cwd-repo ≠ session-repo: emit WARN "Repo-identity mismatch: session bound to {session_repo}, artifact authoring in {artifact_repo}. Artifact will be stamped with both; verify intentional."
4. Pass both `session_repo` and `artifact_repo` (both as absolute paths) into the Myron dispatch prompt below.

Both values are required in the artifact's YAML frontmatter regardless of whether they match. When paths are identical this is informational (routine case); when different the stamp surfaces the mismatch for downstream consumers (Dionysus, etc.).

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

<!-- BREAKING: ADR-AMEND-1 cross-reference — dispatch contract changed from literal "Write" imperative to progressive-write-heredoc pattern per ADR-pythia-shape-contract DR-2 AMENDED. Myron authors via existing Bash grant; no tools: widening. -->

Load `Skill('telos-integrity-ref')` before authoring. The §2 telos schema is MANDATORY for every frame artifact — if the framing document does not declare a valid `telos:` block (name, statement, success_criteria, constraints), Gate A REFUSAL CLAUSE fires and you must halt authoring and surface the missing telos to the user. Do not proceed past Phase 1 scaffold without a confirmed telos block.

Author the framing document at `.sos/wip/frames/{slug}.md` via the progressive-write-heredoc pattern. Load `Skill('progressive-write-heredoc')` for the canonical protocol (Section 4 scaffold-first; Section 5 interpolation mode selection; Section 11.2 canonical frame.md example). Phase 1: scaffold the file with YAML frontmatter + framing section skeletons. The YAML frontmatter must include `session_repo` and `artifact_repo` fields (both absolute paths supplied by the dromenon at dispatch time — see ### Repo-Identity fields below). Phase 2: interpolate content section-by-section. Phase 3: verify `grep -c '<!-- pending:' {slug}.md` returns zero before reporting completion.

### Repo-Identity fields (ADR-pythia-shape-contract Appendix B)

- session_repo: {session_repo absolute path detected at dispatch time}
- artifact_repo: {artifact_repo absolute path detected at dispatch time}

Include both in Phase 1 YAML frontmatter. If paths are identical, this is informational. If different, the stamp surfaces the mismatch for downstream consumers.

The document must end with a '## Next Commands' section listing the exact commands the user should run next (with arguments), in priority order.
")
```

## SVR Pre-Authoring Probe

After myron writes the frame artifact and before surfacing results to the user, execute the following refusal-generating gate:

```
REFUSAL CLAUSE frame-svr-probe:

  IF /frame produces a frame artifact at .sos/wip/frames/{slug}.md AND
     the artifact body contains one or more sentences matching the
     platform-behavior claim shape (legomenon §1 trigger table rows 1-4:
     platform-behavior assertion / library-version-semantic /
     infrastructure-topology fact / historical-codebase fact)
  THEN
    REQUIRE: each such sentence is co-emitted with EITHER
      (a) a structural-verification-receipt YAML block per schema-freeze §1
          three-field tuple satisfying §7 mechanical predicates
          (length 6-15 words, literal substring, orthogonality < 50%), OR
      (b) a UV-P label matching regex
            \[UV-P:\s*[^|]+\|\s*METHOD:\s*[^|]+\|\s*REASON:\s*[^\]]+\]
          (verbatim from schema-freeze §3)

    FOR EACH platform-behavior sentence WITHOUT receipt-or-UV-P co-emission:
      EMIT: "FRAME-SVR-REFUSED: platform-behavior claim at line {N}
      ('{matched_sentence}') lacks structural-verification-receipt OR
      UV-P label. Per project-receipts-svr-framework-elevation throughline,
      direct-inspection-at-claim-assertion-time is a structural invariant,
      not a heroic practice. Re-author claim with co-emitted SVR tuple
      (schema-freeze §1) OR UV-P label (schema-freeze §3) before re-invoking
      /frame."
      HALT framing.
      SURFACE refusal to /go dashboard SVR-gap signal.

  The refusal clause is consumed by the dromenon body at /frame exit and by
  eunomia ADVISORY at close (Sprint-4 gate spec). The dispatching rite's
  Potnia MUST NOT author the missing receipt on the user's behalf --
  user-sovereign claim-and-receipt co-emission is the load-bearing semantic
  (mirrors telos-integrity-ref Gate A user-sovereign declaration binding).
```

## Report

After myron returns:

1. Confirm the artifact was authored by myron via Bash heredoc:
   ```
   Read(".sos/wip/frames/{slug}.md", limit=20)
   ```

2. Assert no pending markers remain (myron's verification protocol):
   ```
   Bash: grep -c '<!-- pending:' .sos/wip/frames/{slug}.md
   ```
   Expected result: `0`. If non-zero, WARN: "myron left {N} pending placeholders in the framing document. Check the file for incomplete sections."

3. Display to the user:
   ```
   ## Frame: .sos/wip/frames/{slug}.md

   {myron's suggested next commands, extracted from the ## Next Commands section}

   Read the full framing document: .sos/wip/frames/{slug}.md
   ```

If the file is not present at the expected path, WARN: "myron did not author the expected file at .sos/wip/frames/{slug}.md. Check myron's output above — the framing content may have been returned inline rather than persisted via heredoc."

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
