# Common Issues and Troubleshooting

Solutions for frequent problems when creating team packs.

---

## Team Swap Issues

### "Team not found: {team-name}"

**Cause**: Team directory doesn't exist or is misnamed.

**Fix**:
```bash
# Check directory exists
ls ~/Code/roster/teams/

# Ensure name follows pattern: {domain}-pack
# Good: sre-pack, doc-team-pack
# Bad: sre, documentation-team
```

### "Switched to {team-name} (0 agents, 4 phases)"

**Cause**: Agent files not found in `agents/` directory.

**Fix**:
```bash
# Check agents directory exists
ls ~/Code/roster/teams/{team-name}/agents/

# Ensure files have .md extension
# Good: platform-engineer.md
# Bad: platform-engineer, platform-engineer.txt
```

### "workflow.yaml not found"

**Cause**: Missing workflow configuration file.

**Fix**:
```bash
# Create workflow.yaml in team root
touch ~/Code/roster/teams/{team-name}/workflow.yaml

# Use template from:
# .claude/skills/team-development/templates/workflow.yaml.template
```

---

## Workflow Configuration Issues

### Phase Count Mismatch

**Symptom**: "4 agents, 5 phases" (or similar mismatch)

**Cause**: `complexity_levels` entries being counted as phases.

**Fix**: The swap script counts `- name:` entries. This is expected when complexity levels use the same YAML pattern. Verify actual phase count:
```bash
grep -A1 "^phases:" workflow.yaml | grep -c "name:"
```

### Agent Not Found in Phase

**Symptom**: Phase references non-existent agent.

**Fix**:
```bash
# List actual agent names
ls ~/Code/roster/teams/{team-name}/agents/ | sed 's/.md$//'

# Compare with workflow references
grep "agent:" ~/Code/roster/teams/{team-name}/workflow.yaml
```

### Orphan Phase

**Symptom**: Phase never executes.

**Cause**: No phase's `next` points to this phase, and it's not the entry point.

**Fix**: Ensure phase is reachable:
```bash
# Check entry point
grep -A2 "entry_point:" workflow.yaml

# Check all next references
grep "next:" workflow.yaml
```

---

## Agent File Issues

### Frontmatter Parse Error

**Symptom**: Agent not loading correctly, model/color not applied.

**Cause**: Malformed YAML frontmatter.

**Fix**:
```yaml
# Ensure proper formatting:
---
name: agent-name
description: |
  Multi-line description
  goes here.
tools: Bash, Glob, Grep, Read
model: claude-sonnet-4-5
color: cyan
---
```

Common frontmatter mistakes:
- Missing opening or closing `---`
- Unquoted special characters in description
- Wrong indentation in multi-line description
- Invalid model name (use `claude-{opus|sonnet|haiku}-4-5`)

### Duplicate Colors

**Symptom**: Multiple agents with same color, hard to distinguish.

**Fix**: Assign unique colors per role type:
```
Coordination: purple
Entry/Requirements: pink, orange
Design/Architecture: cyan
Implementation: green
Validation: red
```

### Wrong Model Assignment

**Symptom**: Slow responses for simple tasks, or shallow analysis for complex ones.

**Fix**: Match model to role:
| Role Type | Model | Reasoning |
|-----------|-------|-----------|
| Orchestration | opus | Complex coordination |
| Senior/Architect | opus | Deep analysis needed |
| Mid-level | sonnet | Balanced capability |
| Assessment | haiku | Fast, focused |

---

## Command Mapping Issues

### /architect Routes to Wrong Agent

**Cause**: Agent's `produces` field doesn't match expected artifact type.

**Fix**: Design phase agents should produce design artifacts:
```yaml
- name: design
  agent: architect
  produces: tdd          # or doc-structure, refactor-plan, reliability-plan
```

Command routing uses:
```bash
grep -B1 "produces: tdd\|produces: doc-structure\|produces: refactor-plan\|produces: reliability-plan"
```

### /build Routes to Wrong Agent

**Cause**: Implementation agent's `produces` doesn't match.

**Fix**: Implementation agents should produce:
```yaml
produces: code          # or commits, documentation, infrastructure-changes
```

### /qa Routes to Wrong Agent

**Cause**: Terminal phase not marked correctly.

**Fix**: Ensure validation phase has `next: null`:
```yaml
- name: validation
  agent: qa-adversary
  produces: test-plan
  next: null            # This makes it the /qa target
```

---

## Integration Issues

### Command Not Recognized

**Symptom**: `/{team-name}` doesn't work.

**Fix**:
1. Check file exists: `.claude/commands/{team-name}.md`
2. Verify frontmatter:
```yaml
---
description: Quick switch to {team-name}
allowed-tools: Bash, Read
model: claude-haiku-4-5
---
```
3. Restart Claude Code session

### Skill Not Discoverable

**Symptom**: `@{team-name}-ref` not found.

**Fix**:
1. Check directory: `.claude/skills/{team-name}-ref/`
2. Check file: `.claude/skills/{team-name}-ref/skill.md`
3. Verify frontmatter has `name` and `description`

### SESSION_CONTEXT Not Updating

**Symptom**: `active_team` stays as previous team.

**Fix**: The quick-switch command should update SESSION_CONTEXT:
```bash
# In command, after swap:
if [ -n "$(get_session_dir 2>/dev/null)" ]; then
  # Update active_team field
fi
```

---

## Validation Failures

### Complexity Level Phase Mismatch

**Symptom**: Phases listed in complexity level don't exist.

**Fix**: Phase names in complexity levels must match phase definitions:
```yaml
phases:
  - name: requirements    # Must match
  - name: design
  - name: implementation
  - name: validation

complexity_levels:
  - name: SCRIPT
    phases: [implementation, validation]  # Must use exact names
```

### Conditional Phase Not Skipping

**Symptom**: Design phase runs even for SCRIPT complexity.

**Fix**: Verify condition syntax:
```yaml
- name: design
  condition: "complexity >= MODULE"  # Exact format
```

And ensure complexity is set when invoking:
```
/task "Fix typo" --complexity=SCRIPT
```

---

## Quick Diagnostic Commands

```bash
# Full team validation
~/Code/roster/swap-team.sh {team-name} && \
ls .claude/agents/ && \
cat .claude/ACTIVE_WORKFLOW.yaml

# Check for common YAML issues
python3 -c "import yaml; yaml.safe_load(open('workflow.yaml'))"

# Verify agent frontmatter
head -20 agents/*.md | grep -A10 "^---"

# Check command file
cat .claude/commands/{team-name}.md | head -10
```
