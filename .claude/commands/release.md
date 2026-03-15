---
name: release
description: "Orchestrate a multi-repo release from reconnaissance through deployment verification. Use when: releasing SDKs, bumping consumers, pushing and verifying across repos, running PATCH/RELEASE/PLATFORM workflows. Triggers: /release, ship it, release all, push and verify, platform release."
argument-hint: "<glob-or-repos> [--complexity=PATCH|RELEASE|PLATFORM] [--dry-run]"
allowed-tools: Bash, Read, Write, Glob, Grep, Task, Skill, AskUserQuestion, TodoWrite
model: opus
---

# /release - Orchestrated Release Workflow

One command from code to verified deployment. `/release` captures your intent, consults Potnia for complexity gating and phase routing, dispatches specialists in order, and loops until the verification report renders a chain-aware verdict.

## Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| positional | Glob pattern or comma-separated repo names | `~/code/acme-*`, `acme-data,acme-ads` |
| `--complexity` | Override auto-detection (PATCH, RELEASE, PLATFORM) | `--complexity=RELEASE` |
| `--dry-run` | Run reconnaissance only, produce state map, stop before execution | |

If no positional argument is given, ask the user what they want to release.

## Behavior

### Phase 0 -- Pre-Flight

1. **Verify releaser rite is active**: Check the context file for `releaser` in the agent configurations section. If not active, run `ari sync --rite releaser` first and inform the user.
2. **Verify gh auth**: Run `gh auth status` -- if unauthenticated, ERROR and stop.
3. **Clean slate**: Check `.sos/wip/release/` for artifacts from a prior run. If found, ask the user whether to clear them or resume from where the prior run left off.
4. **Parse arguments**: Extract glob pattern or repo list from `$ARGUMENTS`. Extract `--complexity` and `--dry-run` flags.
5. **Load cached release knowledge** (if available):
   - Check if `.know/release/` directory exists
   - If it exists, read frontmatter of each `.know/release/*.md` file (limit=10 lines per file)
   - For each file, check freshness: parse `generated_at` + `expires_after`, compare to current time
   - Build a knowledge injection map:
     - `platform-profile.md` (fresh): inject into cartographer and dependency-resolver prompts as "Prior Platform Knowledge"
     - `dependency-topology.md` (fresh): inject into dependency-resolver prompt as "Prior Topology Knowledge"
     - `history.md` (always inject — no expiry): inject into pipeline-monitor prompt as "Release History"
   - If ALL release knowledge is stale or missing: note "No cached release knowledge — full reconnaissance required" and proceed normally
   - If SOME release knowledge is fresh: note "Cached knowledge available: {list of fresh domains}" and proceed with injection
   - **IMPORTANT**: Cached knowledge is ADVISORY, not authoritative. Specialists must still VERIFY cached state against live repos. The cache reduces discovery time, not verification. Include this advisory in every injection:
     ```
     NOTE: This is cached knowledge from a prior release session. Use it to ACCELERATE
     your reconnaissance, not to SKIP it. Verify all cached state against live repo
     contents. Flag any discrepancies between cached and observed state.
     ```

### Phase 1 -- Initial Potnia Consultation

Construct a startup CONSULTATION_REQUEST and invoke Potnia:

```
Task(subagent_type="potnia", prompt="
## CONSULTATION_REQUEST

consultation:
  type: startup

  initiative:
    title: 'Release: {user_intent}'
    goal: '{parsed goal from arguments}'

  state:
    current_phase: none
    completed_phases: []
    blocked_on: none

  results:
    last_specialist: none
    last_outcome: none
    artifacts_ready: []

  context_summary: |
    User invoked /release with scope: {glob_or_repos}
    Complexity override: {--complexity value or 'auto-detect'}
    Dry run: {true|false}
    Artifact directory: .sos/wip/release/
    {any additional context from pre-flight}
")
```

Store Potnia's agent ID for throughline resumption.

### Phase 2 -- Orchestration Loop

Loop until Potnia returns `directive.action: complete`:

#### On `invoke_specialist`:

1. Read `specialist.agent` and `specialist.prompt` from Potnia's response
2. **Inject cached release knowledge** (if available from Phase 0 step 5):
   - If the specialist is `cartographer` AND `platform-profile.md` is fresh: append to the specialist prompt:
     ```
     ### Prior Platform Knowledge (cached from prior release session)
     {content of .know/release/platform-profile.md body, excluding frontmatter}

     NOTE: This is cached knowledge. Use it to ACCELERATE reconnaissance, not SKIP it.
     Verify all cached state against live repo contents. Flag discrepancies.
     ```
   - If the specialist is `dependency-resolver` AND `dependency-topology.md` is fresh: append similarly
   - If the specialist is `pipeline-monitor` AND `history.md` exists: append release history
   - Other specialists receive no injection (release-planner and release-executor work from fresh artifacts)
3. Invoke the specialist via Task tool:
   ```
   Task(subagent_type="{specialist.agent}", prompt="{specialist.prompt}")
   ```
3. When the specialist completes, verify its artifacts exist:
   - cartographer: `platform-state-map.yaml` at `.sos/wip/release/`
   - dependency-resolver: `dependency-graph.yaml`
   - release-planner: `release-plan.yaml`
   - release-executor: `execution-ledger.yaml`
   - pipeline-monitor: `verification-report.yaml`
4. Construct a continuation CONSULTATION_REQUEST and re-consult Potnia (with `resume` if agent ID available):
   ```
   Task(subagent_type="potnia", resume="{potnia_agent_id}", prompt="
   ## CONSULTATION_REQUEST

   consultation:
     type: continuation
     initiative:
       title: 'Release: {user_intent}'
       goal: '{goal}'
     state:
       current_phase: '{completed phase name}'
       completed_phases: [{list of completed phases}]
       blocked_on: none
     results:
       last_specialist: '{agent name}'
       last_outcome: success
       artifacts_ready:
         - '{artifact}: .sos/wip/release/{filename}'
     context_summary: |
       {Brief summary of specialist results}
       {Any notable findings -- dirty repos, dependency issues, failures}
   ")
   ```

#### On `await_user`:

1. Read `user_question.prompt` and `user_question.context`
2. Present to the user via AskUserQuestion
3. Feed the user's answer back to Potnia in the next consultation

#### On specialist failure:

1. Construct a failure CONSULTATION_REQUEST:
   ```
   consultation:
     type: failure
     results:
       last_specialist: '{agent}'
       last_outcome: failure
       artifacts_ready: []
     context_summary: |
       {failure reason and any partial output}
   ```
2. Potnia will either retry with adjusted prompt, recommend phase rollback, or escalate to user

### Phase 3 -- Dry-Run Exit (if `--dry-run`)

After the reconnaissance phase (cartographer produces `platform-state-map.yaml`):
1. Read and display the state map summary to the user
2. If complexity was auto-detected, report it
3. If `has_dependents` was discovered, note the auto-escalation that WOULD occur
4. Stop. Do not proceed to execution.

### Phase 4 -- Completion

When Potnia returns `directive.action: complete`:

1. Read `verification-report.yaml` from `.sos/wip/release/`
2. Display the verdict to the user:

   **On PASS**:
   ```
   Release verified. All CI green, all pipeline chains resolved, all deployments healthy.
   {N} repos released, {M} PRs created.
   ```

   **On FAIL**:
   ```
   Release verification FAILED.
   {failure summary from verification report}
   Recommendation: {pipeline-monitor's recommendation}
   ```

   **On PARTIAL**:
   ```
   Release partially verified. CI green but {chain timeouts / dispatch issues / deployment concerns}.
   Review verification-report.md for details.
   ```

3. If a session is active, note the release outcome for session context.

### Phase 5 -- Knowledge Persistence

After verification completes (regardless of PASS/FAIL/PARTIAL verdict), persist stable platform knowledge to `.know/release/` for future sessions.

1. **Ensure directory exists**: `mkdir -p .know/release`

2. **Persist platform profile** (from cartographer's `platform-state-map.yaml`):
   - Read `.sos/wip/release/platform-state-map.yaml`
   - If it exists, construct `.know/release/platform-profile.md`:
     ```yaml
     ---
     domain: release/platform-profile
     generated_at: "{current ISO 8601 UTC timestamp}"
     expires_after: "30d"
     source_scope:
       - "./.know/release/"
     generator: cartographer
     source_hash: "{git short SHA}"
     confidence: 0.85
     format_version: "1.0"
     update_mode: "full"
     incremental_cycle: 0
     max_incremental_cycles: 3
     ---
     ```
   - Body: Extract the structured platform state from the YAML artifact, converting to markdown with sections per criterion (Repository Ecosystem Map, Pipeline Chain Discovery, Configuration Artifacts)
   - Write: `Write(".know/release/platform-profile.md", frontmatter + body)`

3. **Persist dependency topology** (from dependency-resolver's `dependency-graph.yaml`):
   - Read `.sos/wip/release/dependency-graph.yaml`
   - If it exists, construct `.know/release/dependency-topology.md` with same frontmatter pattern
   - Body: DAG structure, publish order, parallel groups, version constraints
   - Write: `Write(".know/release/dependency-topology.md", frontmatter + body)`

4. **Append to release history** (from pipeline-monitor's `verification-report.yaml`):
   - Read `.sos/wip/release/verification-report.yaml` and `execution-ledger.yaml`
   - If `.know/release/history.md` exists:
     - Read existing file, parse frontmatter
     - Append a new entry to the log body with: date, repos released, versions, outcome, duration, complexity, failures (if any)
     - Increment entry count; if count exceeds 20, archive oldest 10 entries into `## Historical Summary`
     - Update `generated_at` to now
   - If `.know/release/history.md` does not exist:
     - Create with frontmatter (no `expires_after` — history never expires) and the first log entry
     ```yaml
     ---
     domain: release/history
     generated_at: "{timestamp}"
     source_scope:
       - "./.know/release/"
     generator: pipeline-monitor
     source_hash: "{git short SHA}"
     confidence: 0.90
     format_version: "1.0"
     update_mode: "full"
     incremental_cycle: 0
     max_incremental_cycles: 0
     ---
     ```
   - Write: `Write(".know/release/history.md", frontmatter + body)`

5. **Report persistence**: After writing, display:
   ```
   ## Release Knowledge Persisted

   | File | Status | Expires |
   |------|--------|---------|
   | .know/release/platform-profile.md | {Written/Skipped} | {date} |
   | .know/release/dependency-topology.md | {Written/Skipped} | {date} |
   | .know/release/history.md | {Appended/Created/Skipped} | never |

   Cached knowledge will accelerate next /release reconnaissance.
   Check freshness: ari knows --delta release/platform-profile
   ```

6. **Graceful degradation**: If ANY persistence step fails (artifact missing, write error), WARN but do NOT fail the release. Persistence is best-effort — the release itself has already succeeded or failed independently.

## Specialist Agent Reference

| Phase | Agent | Produces | Typical Duration |
|-------|-------|----------|-----------------|
| Reconnaissance | cartographer | platform-state-map.yaml | 2-5 min |
| Dependency Analysis | dependency-resolver | dependency-graph.yaml | 1-3 min |
| Release Planning | release-planner | release-plan.yaml | 1-3 min |
| Execution | release-executor | execution-ledger.yaml | 5-15 min |
| Verification | pipeline-monitor | verification-report.yaml | 5-30 min (chain-dependent) |

## Throughline Resumption

Store Potnia's agent ID after the first consultation. On subsequent consultations, pass `resume: {agent_id}` to maintain Potnia's decision history across the full workflow. If resume fails (ID expired, session changed), fall back to a fresh consultation with full context in `context_summary`.

## Error Recovery

| Scenario | Action |
|----------|--------|
| Specialist times out (maxTurns exceeded) | Report to Potnia as failure; Potnia may retry with narrower scope |
| gh auth expires mid-workflow | Stop, inform user, they re-auth, then `/release --resume` |
| Artifact missing after specialist claims completion | Report to Potnia as failure with details |
| User Ctrl+C during long CI monitoring | Artifacts remain in `.sos/wip/release/`; next `/release` detects and offers resume |

## Anti-Patterns

- **Skipping Potnia**: Never invoke specialists directly without consulting Potnia first. Potnia gates complexity, manages auto-escalation, and verifies handoff criteria.
- **Ignoring specialist failures**: Always report failures back to Potnia. Never silently retry or skip.
- **Hardcoding phase order**: Let Potnia determine routing. PATCH skips dependency-analysis and release-planning. Auto-escalation may add phases mid-flight.
- **Treating dry-run as no-op**: Dry-run still runs full reconnaissance. The state map is valuable even without execution.
