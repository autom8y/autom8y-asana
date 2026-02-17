# Context Architecture Plan: Multi-Sprint Agentic Execution

**Initiative**: SSoT Convergence & Reliability Hardening
**Date**: 2026-02-17
**Author**: Context Engineer (meta-consultation)
**Workstreams**: WS1 (EntityDescriptor SSoT, 5 sprints), WS2 (Cache Hardening, 3 sprints), WS3 (Query CLI + Traversal, 2 sprints)

---

## 1. Token Budget Analysis

Before designing anything, understand the cost structure of each agent invocation.

### Fixed Costs Per Agent Invocation (unavoidable)

| Component | Estimated Tokens | Notes |
|-----------|-----------------|-------|
| System prompt (CLAUDE.md chain) | ~1,200 | Global + project + memory CLAUDE.md |
| Agent prompt (frontmatter + body) | 1,500-2,500 | Pythia=2,200; PE=1,200; Architect=1,200; QA=1,300 |
| Skills auto-loaded by agent | 500-2,000 | Depends on task triggers; standards alone is ~800 |
| **Subtotal: fixed overhead** | **3,200-5,700** | Every invocation pays this |

### Variable Costs (what we control)

| Component | Tokens | When |
|-----------|--------|------|
| Sprint Execution Guide (full) | ~5,000 | NEVER load the whole thing |
| ARCH-descriptor-driven-auto-wiring.md | ~7,500 | Only for Architect + PE on WS1 |
| Source file (entity_registry.py) | ~6,000 | Only when PE is modifying it |
| Checkpoint document | 300-600 | Every invocation after sprint 1 |
| Sprint-specific section of Execution Guide | 800-1,500 | PE invocations only |
| Handoff report from prior agent | 200-400 | Continuation invocations |

### Target Prompt Sizes (variable portion only)

| Agent Type | Target Variable Tokens | Max Total (fixed + variable) |
|------------|----------------------|------------------------------|
| Pythia (consultation) | 400-800 | ~4,500 |
| Architect (TDD production) | 2,000-4,000 | ~8,000 |
| Principal Engineer (implementation) | 1,500-3,000 | ~7,000 |
| QA Adversary (validation) | 1,000-2,000 | ~6,000 |

**Principle**: Leave 80%+ of the context window for the agent's own work (file reading, thinking, tool use). Front-loading context past ~8K tokens actively harms performance by competing with the agent's working memory.

---

## 2. Progressive Disclosure Strategy

### Decision: Checkpoint Documents (not living state doc, not agent resumption)

**Rejected alternatives**:

- **Living initiative state document**: Grows monotonically. By sprint 5, it would be 3K+ tokens of accumulated state, most of which is irrelevant to the current sprint. Violates "right information at right time."
- **Agent ID resumption**: Pythia (a77434e) could be resumed, but resumption loads the entire prior conversation into context. After 3 consultations, Pythia's context is 50%+ stale conversation history. Fresh invocations with compressed checkpoints are more token-efficient.

**Chosen approach**: Write a checkpoint document after each sprint completes. Each checkpoint is a FIXED-SIZE summary (max 40 lines / ~600 tokens) that replaces the previous one. The main thread maintains ONE current checkpoint, not an accumulating history.

### Checkpoint Document Format

Location: `.claude/wip/INITIATIVE-CHECKPOINT.md`

```markdown
# Initiative Checkpoint: SSoT Convergence & Reliability Hardening

**Updated**: {date}
**Current Sprint**: WS{n}-S{m} ({title})
**Branch**: {branch_name}

## Completed Sprints
| Sprint | Status | Key Outcome |
|--------|--------|-------------|
| WS1-S1 | DONE | EntityDescriptor +4 fields, validation checks 6a-7 |
| WS1-S2 | DONE | OfferExtractor + OfferRow, B1 fix verified |

## Active Sprint Summary
- **Goal**: {one sentence}
- **PE invocations remaining**: {count}
- **Blocking issues**: {none or brief description}

## Cumulative Decisions
- {decision 1}: {choice} (ADR-{NNNN})
- {decision 2}: {choice} (sprint {n} handoff)

## Files Modified This Sprint
- `src/autom8_asana/core/entity_registry.py` (lines {range})
- `src/autom8_asana/dataframes/models/registry.py` (method: `_ensure_initialized`)

## Test Baseline
- Last full suite: {count} passed, {count} failed (pre-existing: {list})
- Sprint-specific: {test commands and results}
```

**Why fixed-size**: The checkpoint is loaded into EVERY agent invocation. At 600 tokens, it costs 600 tokens * N invocations. If it grew to 2K tokens, that is 2K * N -- an unacceptable tax on later sprints.

**What gets dropped**: Detailed implementation notes from prior sprints. If a later sprint needs to reference a specific prior decision, the main thread reads the relevant file directly and includes a one-line summary in the agent prompt.

---

## 3. Prompt Templates

### 3.1 Pythia Consultation (Between Sprints)

Use this when transitioning between sprints or when a PE invocation fails and you need routing guidance.

```yaml
consultation:
  type: "{{type}}"  # startup | continuation | failure

  initiative:
    title: "SSoT Convergence & Reliability Hardening"
    goal: "EntityDescriptor absorbs DataFrameSchema (WS1), cache hardening (WS2), query CLI + traversal (WS3)"

  state:
    current_phase: "{{phase}}"  # e.g., "WS1-S3 implementation"
    completed_phases:
      {{#each completed}}
      - "{{this}}"
      {{/each}}
    blocked_on: "{{blocker_or_none}}"

  results:
    last_specialist: "{{agent_name}}"
    last_outcome: "{{success|failure|partial}}"
    artifacts_ready:
      {{#each artifacts}}
      - "{{this.name}}: {{this.path}}"
      {{/each}}

  context_summary: |
    {{summary}}
    Current checkpoint: .claude/wip/INITIATIVE-CHECKPOINT.md
    Sprint execution guide: .claude/wip/SPRINT-EXECUTION-GUIDE.md (section {{n}})
    Architecture doc: docs/design/ARCH-descriptor-driven-auto-wiring.md
```

**Token cost**: ~300-500 tokens. Pythia reads the checkpoint file itself if needed.

**When NOT to consult Pythia**: For straightforward sprint progression where the next PE invocation is unambiguous (the Sprint Execution Guide already specifies the exact sequence). Consult Pythia only for: (a) sprint transitions, (b) failures, (c) scope questions, (d) workstream switches.

### 3.2 Architect: TDD Production for a Sprint

Use when a workstream needs architectural design that does not yet exist (primarily WS2 and WS3, since WS1 already has `ARCH-descriptor-driven-auto-wiring.md`).

```
Act as the Architect.

## Initiative Context
SSoT Convergence & Reliability Hardening, workstream {{ws_id}}: {{ws_title}}.

## Checkpoint
{{paste checkpoint summary -- 3-5 lines from INITIATIVE-CHECKPOINT.md}}

## Scope for This TDD
{{ws_id}}-S{{sprint_num}}: {{sprint_title}}

Specific goals:
{{#each goals}}
- {{this}}
{{/each}}

## Existing Architecture to Integrate With
{{#each key_files}}
- `{{this.path}}` -- {{this.description}}
{{/each}}

## Constraints
- Must integrate with existing EntityDescriptor pattern (21 fields, frozen dataclass)
- Test command: `.venv/bin/pytest tests/ -x -q --timeout=60`
- Pre-existing test failures: test_adversarial_pacing, test_paced_fetch, test_cache_errors_logged_as_warnings
{{#each additional_constraints}}
- {{this}}
{{/each}}

## Deliverables
1. TDD at `docs/design/TDD-{{slug}}.md`
2. ADRs for significant decisions at `docs/decisions/ADR-{{nnnn}}-{{slug}}.md`
3. Sprint execution guide section (PE-ready, same format as `.claude/wip/SPRINT-EXECUTION-GUIDE.md`)

Use the doc-artifacts skill for templates.
```

**Pre-read files before invoking**: Read ONLY the files listed in `key_files` and paste relevant excerpts (not whole files) into `Existing Architecture to Integrate With`. Target: 50-100 lines of excerpted context, not full file contents.

**Token cost**: ~800-1,200 tokens (variable portion).

### 3.3 Principal Engineer: Implementation from Sprint Execution Guide

This is the most frequent invocation. Optimize ruthlessly.

```
Act as the Principal Engineer.

## Sprint Context
Initiative: SSoT Convergence & Reliability Hardening
Sprint: {{ws_id}}-S{{sprint_num}} ({{sprint_title}})
Invocation: PE-{{invocation_id}} ({{title}})

## Checkpoint (current state)
{{paste 5-8 lines from INITIATIVE-CHECKPOINT.md}}

## Your Assignment
{{paste the EXACT section from SPRINT-EXECUTION-GUIDE.md for this PE invocation}}

## Key Files You Will Modify
{{#each target_files}}
- `{{this.path}}` ({{this.what_to_change}})
{{/each}}

## Test Commands
- Module tests: `{{module_test_command}}`
- Full suite (only if uncertain): `.venv/bin/pytest tests/ -x -q --timeout=60`

## Commit Convention
Follow existing style: `{{commit_prefix}}({{scope}}): {{description}} ({{finding_id}})`

## Constraints
- Do NOT modify files outside the listed targets without documenting why
- If design flaw discovered, complete what is feasible, document the gap, escalate
- Pre-existing test failures to ignore: test_adversarial_pacing, test_paced_fetch, test_cache_errors_logged_as_warnings
```

**Critical optimization**: The Sprint Execution Guide (`SPRINT-EXECUTION-GUIDE.md`) is ~5,000 tokens. NEVER pass the whole thing. Extract only the section relevant to this specific PE invocation (typically 400-800 tokens). The main thread does this extraction before invoking PE.

**Pre-read files before invoking**: The main thread reads each file in `target_files` to verify it exists and note current line numbers. DO NOT paste file contents into the prompt -- PE will read them itself. Only include the path and a one-line description of what to change.

**Token cost**: ~1,000-1,500 tokens (variable portion).

### 3.4 QA Adversary: Sprint Gate Validation

```
Act as the QA Adversary.

## Sprint Context
Initiative: SSoT Convergence & Reliability Hardening
QA Gate: {{gate_id}} (after {{sprints_covered}})

## Checkpoint
{{paste full INITIATIVE-CHECKPOINT.md -- QA needs broader context}}

## Scope of Changes Since Last Gate
{{paste git diff --stat output between gate boundaries}}

## Files Changed
{{#each changed_files}}
- `{{this.path}}` ({{this.change_type}}: {{this.description}})
{{/each}}

## Implementation Notes from PE
{{#each pe_notes}}
- PE-{{this.id}}: {{this.summary}}
  {{#if this.deviations}}Deviations: {{this.deviations}}{{/if}}
  {{#if this.risks}}Risk areas: {{this.risks}}{{/if}}
{{/each}}

## QA Gate Specification
{{paste the QA Gate section from SPRINT-EXECUTION-GUIDE.md}}

## Test Baseline
- Pre-existing failures: test_adversarial_pacing, test_paced_fetch, test_cache_errors_logged_as_warnings
- Expected passing: {{count}}+ tests
- Full test command: `.venv/bin/pytest tests/ -x -q --timeout=60`

## Deliverables
1. Test plan with adversarial scenarios
2. Defect report (if any)
3. GO/CONDITIONAL-GO/NO-GO recommendation
4. Save report to `.claude/wip/QA-GATE-{{gate_id}}-report.md`
```

**Pre-read files before invoking**: Run `git diff --stat` and `git log --oneline` for the gate range. Read PE handoff notes. DO NOT read source files -- QA reads them itself.

**Token cost**: ~1,200-1,800 tokens (variable portion).

---

## 4. Context Handoff Pattern

### The Minimal Viable Handoff

The handoff between agents is NOT passing artifacts directly. Each agent reads files from disk. The handoff is passing **pointers and summaries**.

```
Architect -> Principal Engineer:
  PASS: TDD path, ADR paths, sprint execution guide section path
  PASS: 2-3 sentence summary of key design decisions
  DO NOT PASS: TDD content, ADR content, source file contents

Principal Engineer -> QA Adversary:
  PASS: git diff --stat, list of modified files, commit messages
  PASS: PE handoff notes (deviations, risk areas) -- max 200 tokens
  DO NOT PASS: source code, test output, full file contents

QA Adversary -> Main Thread (for next sprint):
  PASS: GO/NO-GO verdict, defect list (if any)
  PASS: Updated checkpoint document
  DO NOT PASS: full test plan, detailed defect analysis
```

### Handoff Data Flow Diagram

```
                    CHECKPOINT.md (600 tok, updated after each sprint)
                         |
                         v
  +-----------+    +-----------+    +-----------+    +-----------+
  |  Pythia   |    | Architect |    | Principal |    |    QA     |
  | (consult) |--->| (if new   |--->| Engineer  |--->| Adversary |
  |           |    |  WS/TDD)  |    | (per PE)  |    | (at gate) |
  +-----------+    +-----------+    +-----------+    +-----------+
       |                |                |                |
       | reads:         | reads:         | reads:         | reads:
       | checkpoint     | checkpoint     | checkpoint     | checkpoint
       |                | key src files  | sprint guide   | git diff
       |                | prior TDDs     | target files   | PE notes
       |                |                |                |
       | writes:        | writes:        | writes:        | writes:
       | (nothing)      | TDD, ADRs      | code, tests    | QA report
       |                | exec guide     | commits        | verdict
       |                |                | PE notes       |
       v                v                v                v
  Main thread updates CHECKPOINT.md after each agent completes
```

### What the Main Thread Does Between Invocations

The main thread (you, the human, driving Claude Code) is the context broker. Between agent invocations:

1. **Read** the previous agent's output (file paths, not full content)
2. **Update** `INITIATIVE-CHECKPOINT.md` (replace, not append)
3. **Extract** the relevant section from the Sprint Execution Guide
4. **Compose** the next agent's prompt using the template above
5. **Invoke** the next agent via Task tool

This keeps the main thread's context clean -- it never accumulates large artifacts, only pointers and summaries.

---

## 5. Pythia Integration Strategy

### Decision: Fresh Invocations with Checkpoint, Not Resumption

**Do NOT resume Pythia by agent ID (a77434e)**. Here is why:

1. Each Pythia consultation is ~400-500 tokens of input and ~400-500 tokens of output.
2. After 3 resumptions, the context contains ~2,700 tokens of stale consultation history.
3. By sprint 5, the accumulated history would be ~9,000 tokens -- most of it irrelevant decisions from sprints 1-3.
4. Fresh invocation with the current checkpoint costs ~500 tokens every time, regardless of how many sprints have passed.

### When to Consult Pythia

| Situation | Consult Pythia? | Rationale |
|-----------|----------------|-----------|
| Starting a new workstream | YES | Phase decomposition, specialist routing |
| Transitioning between sprints within a WS | MAYBE | Only if execution guide is ambiguous |
| Starting the next PE invocation in sequence | NO | Execution guide specifies the exact work |
| PE invocation fails | YES | Diagnosis, recovery prompt generation |
| QA gate returns NO-GO | YES | Determine fix scope, re-route |
| Switching from WS1 to WS2 | YES | Branch management, context shift |
| Design flaw discovered during PE | YES | Decide: patch vs. architect revision |

### Pythia Consultation Quick Path

For the common case (sprint transition, everything going well):

```yaml
consultation:
  type: "continuation"
  initiative:
    title: "SSoT Convergence"
    goal: "WS1: EntityDescriptor SSoT"
  state:
    current_phase: "WS1-S2 complete"
    completed_phases: ["WS1-S1", "WS1-S2"]
    blocked_on: "none"
  results:
    last_specialist: "qa-adversary"
    last_outcome: "success"
    artifacts_ready:
      - "QA Gate 1: .claude/wip/QA-GATE-1-report.md"
  context_summary: |
    QA Gate 1 passed (GO). WS1-S3 next: auto-wire SchemaRegistry.
    Checkpoint: .claude/wip/INITIATIVE-CHECKPOINT.md
```

**Expected response**: Pythia returns a specialist prompt for the Architect (if TDD revision needed) or confirms direct PE invocation per the execution guide. ~400 tokens round trip.

---

## 6. Workstream-Specific Strategies

### WS1: EntityDescriptor SSoT (Feature Branch, 5 Sprints)

**Branch**: `feature/ws1-entity-descriptor-ssot`

**Context accumulation pattern**: WS1 sprints are sequential and build on each other. The checkpoint document tracks cumulative state. Each PE invocation gets ONLY its section from the execution guide.

**Key files always needed by reference** (PE reads them, not passed in prompt):
- `src/autom8_asana/core/entity_registry.py`
- `docs/design/ARCH-descriptor-driven-auto-wiring.md`

**Sprint-to-PE mapping** (from the architecture doc section 5):

| Sprint | PE Invocations | Key Context for PE |
|--------|---------------|-------------------|
| S1: Foundation | 1 (add fields + validation) | ARCH doc sections 2, 4 |
| S2: Fix B1 | 1 (OfferExtractor + OfferRow) | ARCH doc section 5.1 Phase 2 |
| S3: Auto-wire SchemaRegistry | 1 | ARCH doc section 3.2 |
| S4: Auto-wire _create_extractor | 1 | ARCH doc section 3.3 |
| S5: Auto-wire relationships + cascading | 2 (parallel-safe) | ARCH doc sections 3.4, 3.5 |

**QA Gates**: After S2 (foundation + B1 fix) and after S5 (all auto-wiring complete).

### WS2: Cache Hardening (Main Branch, 3 Sprints)

**Branch**: `main` (direct commits)

**Key difference from WS1**: No pre-existing architecture doc. The Architect must produce a TDD before PE begins. This means the Architect invocation needs to read cache module structure.

**Pre-Architect file reading** (main thread reads these, passes excerpts):
- `src/autom8_asana/cache/backends/redis.py` (class structure, ~30 lines)
- `src/autom8_asana/cache/policies/` (directory listing)
- `src/autom8_asana/core/exceptions.py` (error tuples, ~20 lines)

**Context isolation**: WS2 has zero overlap with WS1 files. The checkpoint document should note this explicitly so PE does not accidentally modify entity_registry.py.

### WS3: Query CLI + Traversal (Main Branch, 2 Sprints)

**Branch**: `main` (direct commits)

**Dependencies**: Depends on WS1 completing (traversal unification uses EntityDescriptor fields). The checkpoint document tracks this dependency.

**Pre-Architect file reading**:
- `.claude/wip/TODO.md` (traversal unification section, ~20 lines)
- `docs/spikes/SPIKE-deferred-todo-triage.md` (section 2, ~40 lines)
- `src/autom8_asana/dataframes/extractors/base.py` (traversal methods, ~30 lines)

---

## 7. Anti-Patterns to Avoid

### 1. "Load Everything" Anti-Pattern

**Wrong**: "Let me paste the entire ARCH doc and the Sprint Execution Guide and the current entity_registry.py into the PE prompt."

**Why it fails**: That is ~18,000 tokens of prompt context. PE then reads the same files again during execution, doubling the cost. Worse, the pre-loaded context competes with PE's working memory when it is making implementation decisions.

**Correct**: Pass file paths and 1-line descriptions. PE reads what it needs.

### 2. "Resume for Continuity" Anti-Pattern

**Wrong**: "Resume Pythia (a77434e) so it remembers all prior consultations."

**Why it fails**: Resumed agents carry their ENTIRE conversation history. After 5 consultations, Pythia has ~5,000 tokens of stale context that it must process every time, slowing responses and increasing the chance of attention dilution.

**Correct**: Fresh invocation with the 600-token checkpoint.

### 3. "Append to Checkpoint" Anti-Pattern

**Wrong**: "Add this sprint's results to the checkpoint, keeping all prior results too."

**Why it fails**: Checkpoints that grow linearly become the living state document you rejected. By sprint 8, the checkpoint is 2,000+ tokens and most of it is irrelevant.

**Correct**: REPLACE the checkpoint. Keep only: completed sprint table (fixed-width summary), active sprint state, cumulative decisions list (max 10 entries), files modified THIS sprint.

### 4. "Pass QA the Full Test Plan" Anti-Pattern

**Wrong**: "Here is the test plan from the execution guide, plus all PE notes, plus the full git diff."

**Why it fails**: QA reads files itself. Passing large diffs in the prompt wastes tokens and may exceed the variable budget.

**Correct**: Pass `git diff --stat` (file list, not content), PE notes (max 200 tokens per PE), and the QA Gate specification section (max 500 tokens).

### 5. "Stale Checkpoint" Anti-Pattern

**Wrong**: Forgetting to update the checkpoint between PE invocations within a sprint.

**Why it fails**: The next PE invocation gets outdated "files modified" and "blocking issues" context, leading to confusion about what has already been done.

**Correct**: Update the checkpoint after EVERY PE invocation completes, not just after sprints complete.

### 6. "Architect for Every Sprint" Anti-Pattern

**Wrong**: Invoking the Architect before every sprint, even when the execution guide already specifies the work.

**Why it fails**: The Architect invocation costs 30-90 minutes and 8,000+ tokens. For WS1, the ARCH doc already contains all 6 phases in detail. Re-designing is pure waste.

**Correct**: Only invoke Architect when: (a) a new workstream starts without a TDD, (b) PE discovers a design flaw, (c) QA rejects an implementation for architectural reasons.

### 7. "Orphan Context" Anti-Pattern

**Wrong**: Referring to "the decision we made in sprint 2" without specifying what it was.

**Why it fails**: Agents have no memory of prior invocations. A reference to "the decision" requires the agent to guess or search.

**Correct**: Include the decision in the checkpoint's "Cumulative Decisions" section with a one-line summary.

---

## 8. Execution Sequence (First 3 Sprints as Example)

### Pre-Flight (Before Any Sprint)

1. Create `INITIATIVE-CHECKPOINT.md` with empty template
2. Verify Sprint Execution Guide exists (WS1 already has `SPRINT-EXECUTION-GUIDE.md` equivalent in ARCH doc)
3. Create feature branch for WS1: `git checkout -b feature/ws1-entity-descriptor-ssot`

### WS1-S1: Foundation

**Step 1**: Update checkpoint (sprint = WS1-S1, goal = "Add 4 fields to EntityDescriptor + validation")

**Step 2**: Extract ARCH doc section 5.1 Phase 1 (~400 tokens)

**Step 3**: Invoke PE with template 3.3:
```
Sprint: WS1-S1 (Foundation)
Invocation: PE-S1 (EntityDescriptor field additions + validation)

Assignment: [paste ARCH doc section 5.1 Phase 1]

Key files:
- src/autom8_asana/core/entity_registry.py (add 4 fields to EntityDescriptor dataclass)

Test: .venv/bin/pytest tests/unit/core/ -x -q --timeout=60
Commit: feat(core): add DataFrame layer fields to EntityDescriptor (WS1-S1)
```

**Step 4**: PE completes. Update checkpoint with files modified and test results.

### WS1-S2: Fix B1

**Step 1**: Update checkpoint (sprint = WS1-S2)

**Step 2**: Extract ARCH doc section 5.1 Phase 2 (~500 tokens)

**Step 3**: Invoke PE. Assignment = Phase 2 content.

**Step 4**: PE completes. Update checkpoint.

**Step 5**: QA Gate 1. Invoke QA with template 3.4.

**Step 6**: QA returns GO/NO-GO. Update checkpoint with verdict.

### WS1-S3: Auto-wire SchemaRegistry

**Step 1**: Update checkpoint.
**Step 2**: Check if Pythia consultation needed (probably not -- ARCH doc is clear).
**Step 3**: Extract ARCH doc section 3.2 + section 5.1 Phase 3.
**Step 4**: Invoke PE. Continue the pattern.

---

## 9. File Reference Quick Index

Files the main thread should bookmark (absolute paths for clipboard):

| File | Purpose | When to Read |
|------|---------|-------------|
| `/Users/tomtenuta/Code/autom8_asana/.claude/wip/INITIATIVE-CHECKPOINT.md` | Current state | Before every agent invocation |
| `/Users/tomtenuta/Code/autom8_asana/docs/design/ARCH-descriptor-driven-auto-wiring.md` | WS1 design | Before WS1 PE/Architect invocations |
| `/Users/tomtenuta/Code/autom8_asana/.claude/wip/SPRINT-EXECUTION-GUIDE.md` | WS-other execution | Before non-WS1 PE invocations |
| `/Users/tomtenuta/Code/autom8_asana/.claude/wip/TODO.md` | Deferred items | Before WS3 planning |
| `/Users/tomtenuta/Code/autom8_asana/docs/spikes/SPIKE-deferred-todo-triage.md` | Traversal analysis | Before WS3 Architect invocation |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/entity_registry.py` | EntityDescriptor source | WS1 PE invocations (PE reads it, not you) |
| `/Users/tomtenuta/Code/autom8_asana/.claude/skills/orchestrator-templates/schemas/consultation-request.md` | Pythia input format | When composing Pythia consultations |
| `/Users/tomtenuta/Code/autom8_asana/.claude/agents/pythia.md` | Pythia behavior spec | Reference only; do not paste into prompts |

---

## 10. Session Boundary Design

### When to Start a Fresh Claude Code Session

| Trigger | Action | Rationale |
|---------|--------|-----------|
| Sprint complete | Fresh session | Accumulated tool output from PE/QA pollutes context |
| Workstream switch (WS1 -> WS2) | Fresh session | Completely different file set; old context is 100% waste |
| QA gate complete | Fresh session | QA output is large; next sprint needs clean context |
| 3+ PE invocations in one session | Consider fresh session | Task tool results accumulate in main thread context |
| PE failure + Pythia consultation + PE retry | Continue session | Failure context is relevant for the retry |

### Session Handoff Document

When starting a fresh session, paste this into the first message:

```
Resuming initiative: SSoT Convergence & Reliability Hardening.
Current checkpoint: .claude/wip/INITIATIVE-CHECKPOINT.md
Next action: [describe what to do next]
```

The checkpoint file contains everything the new session needs. No other context loading required for the first message.
