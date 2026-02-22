---
name: hooks-criteria
description: "Evaluation criteria for CC hook wiring audits. Use when: theoros is auditing hooks domain, evaluating hook lifecycle coverage and configuration quality. Triggers: hooks audit criteria, hook wiring evaluation, settings.json assessment."
---

# Hooks Audit Criteria

> The theoros evaluates CC hook wiring against these standards to ensure comprehensive lifecycle coverage, correct tool targeting, and safe timeout configuration.

## Scope

**Target files**: `.claude/settings.local.json` (projected hook configuration)

**Supporting context**: `internal/hook/` (Go hook implementations), `knossos/templates/rules/internal-hook.md` (hook development rules)

**Evaluation focus**: The hooks section of settings.local.json — lifecycle event coverage, command structure, matcher patterns, timeout values, and async classification.

## Criteria

### Criterion 1: Lifecycle Event Coverage (weight: 30%)

**What to evaluate**: Which CC lifecycle events have hooks registered. CC supports: PreToolUse, PostToolUse, PreCompact, SessionStart, SessionEnd, Stop, SubagentStart, SubagentStop, Notification. Each event should have a hook if there is platform behavior to enforce or observe.

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | 8+ of 9 lifecycle events have hooks. All critical events (SessionStart, SessionEnd, Stop, PreToolUse, PostToolUse) covered. Coverage gaps are intentional and justified. |
| B | 80-89% | 7 lifecycle events have hooks. All critical events covered. 1-2 non-critical gaps. |
| C | 70-79% | 5-6 lifecycle events have hooks. Critical events covered but gaps exist in observability (SubagentStart/Stop) or safety (PreCompact). |
| D | 60-69% | 4 lifecycle events have hooks. Some critical events missing. |
| F | < 60% | Fewer than 4 lifecycle events have hooks. Critical safety gaps. |

**Evidence collection**: Read `.claude/settings.local.json`. Extract all keys under `hooks`. Count distinct lifecycle events. List which events have hooks and which don't. Compare against the 9 known CC lifecycle events.

---

### Criterion 2: Command Structure (weight: 25%)

**What to evaluate**: Hook commands should use the `ari hook <subcommand>` pattern with `--output json`. Each hook should map to a specific ari subcommand. Commands should be well-formed and consistent.

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | All hooks use `ari hook <name> --output json` pattern. Each hook has a unique, descriptive subcommand name. No raw shell commands or scripts. |
| B | 80-89% | 95%+ use ari hook pattern. 1-2 hooks may have minor inconsistencies (missing --output json). |
| C | 70-79% | 85-94% use ari hook pattern. Some hooks use raw shell commands instead of ari subcommands. |
| D | 60-69% | 75-84% use ari hook pattern. Mix of ari subcommands and ad-hoc scripts. |
| F | < 60% | Fewer than 75% use ari hook pattern. Hook commands are ad-hoc or inconsistent. |

**Evidence collection**: Read each hook entry's `command` field. Verify it starts with `ari hook`. Check for `--output json` suffix. List any non-conforming commands.

---

### Criterion 3: Matcher Precision (weight: 20%)

**What to evaluate**: PreToolUse and PostToolUse hooks should use `matcher` fields to target specific tools. Matchers should use pipe-delimited tool names. Over-broad matchers (no matcher = matches all) should be intentional.

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | All tool-specific hooks have precise matchers. Write guards target Edit\|Write. Bash validation targets Bash. Global hooks (no matcher) are justified (e.g., budget tracking). |
| B | 80-89% | Most hooks have appropriate matchers. 1 hook missing a matcher that should have one. |
| C | 70-79% | Some hooks have matchers. 2-3 hooks are overly broad or missing matchers. |
| D | 60-69% | Few hooks have matchers. Most fire on all tool uses regardless of relevance. |
| F | < 60% | No matchers used. All hooks fire on all events. |

**Evidence collection**: For each PreToolUse and PostToolUse entry, check for `matcher` field. Parse matcher patterns (pipe-delimited). Evaluate whether each hook needs to see all tools or specific ones. Flag hooks that should be scoped but aren't.

---

### Criterion 4: Timeout and Async Configuration (weight: 25%)

**What to evaluate**: Timeouts should be proportional to hook complexity. Async hooks should not block the user. Sync hooks on critical paths (PreToolUse) should have short timeouts (3-5s). Observability hooks (PostToolUse, SubagentStart/Stop) can be async.

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | All hooks have explicit timeouts. PreToolUse hooks: 3-5s. SessionStart: 10s max. Observability hooks marked async. No blocking hooks exceed 10s. |
| B | 80-89% | 95%+ have explicit timeouts. Most timeouts are appropriate. 1-2 hooks could benefit from async. |
| C | 70-79% | 85-94% have explicit timeouts. Some timeouts too generous (>10s on critical path). Missing async on observability hooks. |
| D | 60-69% | 75-84% have explicit timeouts. Several timeouts inappropriate for their position in the lifecycle. |
| F | < 60% | Many hooks missing explicit timeouts. Blocking hooks with no time bounds. |

**Evidence collection**: For each hook, extract `timeout` and `async` fields. Classify by lifecycle position: critical path (PreToolUse, PreCompact) vs. observability (PostToolUse, SubagentStart/Stop) vs. lifecycle (SessionStart/End, Stop). Evaluate timeout appropriateness per position.

---

## Grading Calculation

Final grade is weighted average of all criteria midpoint scores (see `schemas/grading.lego.md`). Example:
- Lifecycle Coverage: A (midpoint 95%) x 30% = 28.5
- Command Structure: A (midpoint 95%) x 25% = 23.75
- Matcher Precision: B (midpoint 85%) x 20% = 17.0
- Timeout/Async: B (midpoint 85%) x 25% = 21.25
- **Total: 90.5 -> A**

## Related

- [Pinakes INDEX](../INDEX.lego.md) - Full audit system documentation
- [dromena-criteria](dromena.lego.md) - Evaluation criteria for slash commands
- [agents-criteria](agents.lego.md) - Evaluation criteria for agent prompts
