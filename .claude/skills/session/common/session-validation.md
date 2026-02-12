# Session Validation Patterns

> Pre-flight validation patterns used by session-lifecycle commands.

## Overview

Before executing any session-lifecycle command, validation checks ensure the environment is in the correct state. This document defines common validation patterns used across all commands.

## Validation Categories

1. **Session Existence** - Does a session exist?
2. **Session State** - Is session active or parked?
3. **Rite Context** - Is rite configuration valid?
4. **Agent Availability** - Does target agent exist?
5. **Git State** - Is working directory clean?

## Session Existence Validation

### Check: Session Exists

**Used By**: park, resume, wrap, handoff

**Implementation**:
```bash
session_dir=$(ari session status | jq -r '.session_dir')
if [[ -z "$session_dir" || ! -d "$session_dir" ]]; then
  ERROR: No active session
fi
```

**Success**: Session directory exists and is readable

**Failure**: Error with suggestion to /start

**Error Message**:
```
No active session to {verb}.

Use /start to begin a new session.
```

### Check: Session Does NOT Exist

**Used By**: start

**Implementation**:
```bash
session_dir=$(ari session status | jq -r '.session_dir')
if [[ -n "$session_dir" && -d "$session_dir" ]]; then
  ERROR: Session already exists
fi
```

**Success**: No session directory exists

**Failure**: Error with suggestion to /wrap or /resume

**Error Message**:
```
Session already active: {initiative}

Use /wrap to complete it, or /resume to continue working.
```

## Session State Validation

### Check: Session Active (Not Parked)

**Used By**: park, wrap, handoff

**Implementation**:
```bash
parked_at=$(yq e '.parked_at' SESSION_CONTEXT.md)
if [[ "$parked_at" != "null" ]]; then
  ERROR: Session is parked
fi
```

**Success**: `parked_at` field not set in SESSION_CONTEXT

**Failure**: Error with suggestion to /resume

**Error Message**:
```
Session parked at {timestamp}.

Use /resume to continue before {verb}.
```

### Check: Session Parked

**Used By**: resume

**Implementation**:
```bash
parked_at=$(yq e '.parked_at' SESSION_CONTEXT.md)
if [[ "$parked_at" == "null" ]]; then
  ERROR: Session not parked
fi
```

**Success**: `parked_at` field set in SESSION_CONTEXT

**Failure**: Error indicating session is active

**Error Message**:
```
Session is not parked. It's already active.

Continue working or use /park to pause.
```

## Rite Context Validation

### Check: Rite Exists

**Used By**: start, resume, handoff

**Implementation**:
```bash
if [[ -z "$KNOSSOS_HOME" ]]; then
  ERROR: Knossos system not configured
fi

rite_dir="$KNOSSOS_HOME/rites/$target_rite"
if [[ ! -d "$rite_dir" ]]; then
  ERROR: Rite not found
fi
```

**Success**: Rite directory exists in knossos

**Failure**: Error listing available rites

**Error Message**:
```
Rite '{rite}' not found.

Available rites:
{list from knossos}

Use /rite to switch or check KNOSSOS_HOME.
```

### Check: Rite Consistency

**Used By**: resume

**Implementation**:
```bash
active_rite=$(cat .claude/ACTIVE_RITE)
session_rite=$(yq e '.active_rite' SESSION_CONTEXT.md)

if [[ "$active_rite" != "$session_rite" ]]; then
  WARNING: Rite mismatch
fi
```

**Success**: ACTIVE_RITE matches session.active_rite

**Failure**: Warning with option to switch or override

**Warning Message**:
```
⚠ Rite mismatch:
  Session rite: {session_rite}
  Active rite:  {active_rite}

Options:
1. Switch to session rite: /rite {session_rite}
2. Continue with current rite (may have different agents)
3. Cancel and investigate

Continue? [1/2/cancel]:
```

## Agent Availability Validation

### Check: Agent Exists

**Used By**: handoff, resume (if --agent specified)

**Implementation**:
```bash
agent_file=".claude/agents/$target_agent.md"
if [[ ! -f "$agent_file" ]]; then
  ERROR: Agent not found
fi
```

**Success**: Agent file exists in current rite

**Failure**: Error listing available agents

**Error Message**:
```
Agent '{agent}' not found in rite '{rite}'.

Available agents:
{list from .claude/agents/}

Use /rite to see agent descriptions.
```

### Check: Agent Different from Current

**Used By**: handoff

**Implementation**:
```bash
last_agent=$(yq e '.last_agent' SESSION_CONTEXT.md)
if [[ "$target_agent" == "$last_agent" ]]; then
  ERROR: Same agent
fi
```

**Success**: Target agent differs from last_agent

**Failure**: Error suggesting to continue with current agent

**Error Message**:
```
Already working with {agent}.

Continue with current agent or specify a different one.
```

## Git State Validation

### Check: Git Status

**Used By**: resume (informational), wrap (blocking)

**Implementation**:
```bash
git_status=$(git status --porcelain)
if [[ -n "$git_status" ]]; then
  if [[ "$command" == "wrap" ]]; then
    ERROR: Uncommitted changes
  else
    WARNING: Uncommitted changes
  fi
fi
```

**Success (wrap)**: `git status --porcelain` returns empty

**Failure (wrap)**: Error requiring clean state

**Warning (resume)**: Informational, allow to continue

**Error Message (wrap)**:
```
⚠ Uncommitted changes detected:

{git status output}

Commit changes before wrapping or use --skip-checks.
```

**Warning Message (resume)**:
```
⚠ Uncommitted changes detected since park:

{git status output}

Review changes before continuing? [y/n]:
```

## Validation Helpers

### ari session Functions

```bash
# Get session directory
ari session status | jq -r '.session_dir'

# Get session state
ari session status | jq -r '.session_state'  # active | parked | none

# Get session metadata
ari session status | jq -r '.{field}'
```

### YAML Extraction

```bash
# Read frontmatter fields
yq e '.{field}' SESSION_CONTEXT.md

# Check field existence
yq e 'has("{field}")' SESSION_CONTEXT.md
```

## Validation Timing

| Command | Validation Stage | Abort on Failure? |
|---------|------------------|-------------------|
| /start | Before any action | Yes |
| /park | Before state capture | Yes |
| /resume | Before agent invocation | Yes (errors), No (warnings) |
| /wrap | Before quality gates | Yes (unless --skip-checks) |
| /handoff | Before moirai call | Yes |

## Error Handling Philosophy

1. **Fail fast**: Validate before side effects
2. **Clear messages**: Explain what's wrong and how to fix
3. **Actionable**: Suggest specific next steps
4. **Informative warnings**: Surface issues but allow override when safe

## Example: Multi-Check Validation

```bash
# Full pre-flight for /park command

# 1. Session exists
session_dir=$(ari session status | jq -r '.session_dir')
[[ -z "$session_dir" ]] && error "No active session to park. Use /start."

# 2. Session not already parked
parked_at=$(yq e '.parked_at' "$session_dir/SESSION_CONTEXT.md")
[[ "$parked_at" != "null" ]] && error "Session already parked at $parked_at."

# 3. Git status (warning only)
git_status=$(git status --porcelain | wc -l)
if [[ "$git_status" -gt 0 ]]; then
  warn "⚠ $git_status uncommitted files. Consider committing before park."
fi

# All checks passed, proceed with park
```

## Validation Matrix

| Command | Session Exists | Session State | Rite Valid | Agent Valid | Git Clean |
|---------|----------------|---------------|------------|-------------|-----------|
| /start | ❌ Must NOT | N/A | ✓ Check | N/A | - |
| /park | ✓ Must | Active | - | - | ⚠ Warn |
| /resume | ✓ Must | Parked | ⚠ Warn | ✓ (if --agent) | ⚠ Warn |
| /wrap | ✓ Must | Active | - | - | ✓ Block* |
| /handoff | ✓ Must | Active | - | ✓ Check | - |

*Unless --skip-checks

## Cross-References

- [Session Resolution Pattern](../shared/session-resolution.md) - Behavioral implementation
- [Workflow Resolution Pattern](../shared/workflow-resolution.md) - Rite/agent validation
- [Session Context Schema](session-context-schema.md) - Field definitions
- [Error Messages](error-messages.md) - Standard error templates
