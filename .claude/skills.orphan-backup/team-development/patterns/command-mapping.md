# Command Mapping Patterns

How slash commands integrate with team workflows.

---

## Standard Command Mappings

Every team should map these 5 commands to agents:

| Command | Purpose | Maps To |
|---------|---------|---------|
| `/architect` | Design only | Design phase agent |
| `/build` | Implement only | Implementation phase agent |
| `/qa` | Validate only | Validation phase agent |
| `/hotfix` | Fast fix | Implementation or coordination agent |
| `/code-review` | Review changes | Validation agent (review mode) |

---

## How Commands Find Agents

Commands read from `ACTIVE_WORKFLOW.yaml` to find the right agent.

### /architect → Design Agent
```bash
# Finds agent that produces design artifacts
grep -B1 "produces: tdd\|produces: doc-structure\|produces: refactor-plan\|produces: reliability-plan" \
  .claude/ACTIVE_WORKFLOW.yaml | grep "agent:" | head -1
```

### /build → Implementation Agent
```bash
# Finds agent that produces implementation artifacts
grep -B1 "produces: code\|produces: commits\|produces: documentation\|produces: infrastructure-changes" \
  .claude/ACTIVE_WORKFLOW.yaml | grep "agent:"
```

### /qa → Validation Agent
```bash
# Finds terminal phase agent (next: null)
grep -B1 "next: null" .claude/ACTIVE_WORKFLOW.yaml | grep "agent:"
```

---

## Mapping by Team

### 10x-dev-pack
```yaml
# /architect  → architect
# /build      → principal-engineer
# /qa         → qa-adversary
# /hotfix     → principal-engineer (fast path)
# /code-review → qa-adversary (review mode)
```

### doc-team-pack
```yaml
# /architect  → information-architect
# /build      → tech-writer
# /qa         → doc-reviewer
# /hotfix     → tech-writer (fast path)
# /code-review → doc-reviewer (review mode)
```

### hygiene-pack
```yaml
# /architect  → architect-enforcer
# /build      → janitor
# /qa         → audit-lead
# /hotfix     → janitor (fast path)
# /code-review → audit-lead (review mode)
```

### debt-triage-pack
```yaml
# /architect  → risk-assessor
# /build      → sprint-planner
# /qa         → risk-assessor (3 agents, doubles as validator)
# /hotfix     → (N/A - planning only team)
# /code-review → (N/A - planning only team)
```

### sre-pack
```yaml
# /architect  → platform-engineer
# /build      → platform-engineer
# /qa         → chaos-engineer
# /hotfix     → incident-commander (fast path)
# /code-review → chaos-engineer (review mode)
```

---

## Quick-Switch Commands

Each team has a quick-switch command:

| Command | Team | Action |
|---------|------|--------|
| `/10x` | 10x-dev-pack | Switch and show roster |
| `/docs` | doc-team-pack | Switch and show roster |
| `/hygiene` | hygiene-pack | Switch and show roster |
| `/debt` | debt-triage-pack | Switch and show roster |
| `/sre` | sre-pack | Switch and show roster |

### Implementation Pattern
```yaml
---
description: Quick switch to {team-name} ({workflow description})
allowed-tools: Bash, Read
model: claude-haiku-4-5
---

## Behavior
1. Execute: `~/Code/roster/swap-team.sh {team-name}`
2. Display team roster
3. Update SESSION_CONTEXT if active
```

---

## Workflow Entry Commands

These commands use the workflow's entry point:

| Command | Behavior |
|---------|----------|
| `/start` | Invoke entry point agent, create session |
| `/task` | Run full workflow through all phases |
| `/sprint` | Run multiple `/task` invocations |

### Entry Point Resolution
```bash
# Get entry agent from workflow
ENTRY_AGENT=$(grep -A2 "^entry_point:" .claude/ACTIVE_WORKFLOW.yaml | grep "agent:" | awk '{print $2}')
```

---

## Comment Convention

Document mappings in workflow.yaml:

```yaml
name: my-team-pack
workflow_type: sequential

# ... phases ...

# Agent roles for command mapping:
# /architect  → {design-agent}
# /build      → {implementation-agent}
# /qa         → {validation-agent}
# /hotfix     → {fast-path-agent}
# /code-review → {review-agent}
```

---

## Phase-Skipping Commands

Some commands skip to specific phases:

| Command | Skips | Starts At |
|---------|-------|-----------|
| `/architect` | Entry phase | Design phase |
| `/build` | Entry + Design | Implementation phase |
| `/qa` | Entry + Design + Implementation | Validation phase |
| `/hotfix` | Entry + Design | Implementation (minimal design) |

---

## Special Cases

### Teams Without All Commands
Some teams don't support all commands:

**debt-triage-pack (3 agents):**
```yaml
# /hotfix → (N/A - planning only team)
# /code-review → (N/A - planning only team)
```

Document this in the workflow comments.

### Dual-Purpose Agents
Some agents serve multiple command mappings:

**sre-pack:**
```yaml
# /architect  → platform-engineer
# /build      → platform-engineer  # Same agent for both
```

This is acceptable when one agent handles both design and implementation.

---

## Command Registration

### COMMAND_REGISTRY.md
Add quick-switch command to Team Management section:

```markdown
### Team Management (N commands)

| Command | File | Status | Description |
|---------|------|--------|-------------|
| `/sre` | [commands/sre.md](commands/sre.md) | Active | Quick switch to sre-pack |
```

### Update Count
Update the total command count at the top of COMMAND_REGISTRY.md.

---

## Validation

### Pre-Flight Checks
```bash
# Verify command mappings work
~/Code/roster/swap-team.sh {team-name}

# Test /architect routing
grep -B1 "produces: tdd" .claude/ACTIVE_WORKFLOW.yaml

# Test /qa routing
grep -B1 "next: null" .claude/ACTIVE_WORKFLOW.yaml
```

### Common Issues
- Missing `produces:` field → commands can't find agent
- Wrong artifact type → command routes to wrong agent
- Missing command comment → documentation incomplete
