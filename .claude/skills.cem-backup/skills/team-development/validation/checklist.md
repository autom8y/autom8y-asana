# Team Validation Checklist

Pre-flight checks before deploying a new team pack.

---

## Directory Structure

### Team Directory
- [ ] Directory exists: `~/Code/roster/teams/{team-name}/`
- [ ] Name follows pattern: `{domain}-pack` (e.g., `sre-pack`)
- [ ] Agents directory exists: `~/Code/roster/teams/{team-name}/agents/`

### Files Present
- [ ] `workflow.yaml` exists in team root
- [ ] 3-5 agent markdown files in `agents/` directory
- [ ] Agent file count matches workflow phases (±1 for orchestrator)

---

## Workflow Configuration

### Required Fields
- [ ] `name` matches directory name
- [ ] `workflow_type` is `sequential`
- [ ] `description` is a single line

### Entry Point
- [ ] `entry_point.agent` matches an agent filename (without .md)
- [ ] `entry_point.artifact.type` is defined
- [ ] `entry_point.artifact.path_template` follows `docs/{category}/{PREFIX}-{slug}.md`

### Phases
- [ ] Each phase has: `name`, `agent`, `produces`, `next`
- [ ] Phase names are lowercase, single word or hyphenated
- [ ] All `agent` values match agent filenames
- [ ] All `produces` values are lowercase, hyphenated
- [ ] Exactly one phase has `next: null` (terminal)
- [ ] No orphan phases (all reachable from entry)
- [ ] Phase order is logical (entry → design → execute → validate)

### Complexity Levels
- [ ] 2-4 complexity levels defined
- [ ] Level names are UPPERCASE
- [ ] Each level has `name`, `scope`, `phases`
- [ ] `scope` descriptions are concrete (not vague like "simple work")
- [ ] Phase lists follow workflow order
- [ ] All levels include terminal phase

### Command Mapping Comments
- [ ] `/architect` mapping documented
- [ ] `/build` mapping documented
- [ ] `/qa` mapping documented
- [ ] `/hotfix` mapping documented (or N/A noted)
- [ ] `/code-review` mapping documented (or N/A noted)

---

## Agent Files

### Frontmatter
- [ ] Each agent has YAML frontmatter between `---` markers
- [ ] `name` matches filename (without .md)
- [ ] `description` includes role summary, triggers, and example
- [ ] `tools` list is appropriate for role
- [ ] `model` is one of: `claude-opus-4-5`, `claude-sonnet-4-5`, `claude-haiku-4-5`
- [ ] `color` is unique within team

### 11 Sections Present
- [ ] Title and Overview (2-3 sentences)
- [ ] Core Responsibilities (4-6 bullets)
- [ ] Position in Workflow (ASCII diagram)
- [ ] Domain Authority (decide/escalate/route)
- [ ] How You Work (3-4 phases with steps)
- [ ] What You Produce (artifact table + template)
- [ ] Handoff Criteria (checklist)
- [ ] The Acid Test (single question)
- [ ] Skills Reference (cross-references)
- [ ] Cross-Team Notes (when to flag for other teams)
- [ ] Anti-Patterns to Avoid (3-5 items)

### Model Assignment
- [ ] Orchestration/Senior roles use `opus`
- [ ] Mid-level specialists use `sonnet`
- [ ] Assessment/Analysis roles use `haiku` or `sonnet`

### Color Assignment
- [ ] Coordination agents: purple
- [ ] Entry/Requirements agents: pink or orange
- [ ] Design/Architecture agents: cyan
- [ ] Execution/Implementation agents: green or cyan
- [ ] Validation/Testing agents: red

---

## Integration

### Quick-Switch Command
- [ ] Command file exists: `.claude/commands/{team-name}.md`
- [ ] `description` matches team purpose
- [ ] `allowed-tools` is `Bash, Read`
- [ ] `model` is `claude-haiku-4-5`
- [ ] Bash command is `~/Code/roster/swap-team.sh {team-name}`
- [ ] Roster table lists all agents

### Reference Skill
- [ ] Skill directory exists: `.claude/skills/{team-name}-ref/`
- [ ] `skill.md` exists in skill directory
- [ ] Frontmatter has `name` and `description`
- [ ] Documents all agents, workflow, and commands

### Registry Updates
- [ ] COMMAND_REGISTRY.md updated
- [ ] Command count incremented
- [ ] New command in correct section (Team Management)

---

## Verification Commands

```bash
# 1. Test team swap
~/Code/roster/swap-team.sh {team-name}
# Expected: "Switched to {team-name} (N agents, M phases, entry: {agent})"

# 2. List all teams
~/Code/roster/swap-team.sh --list
# Expected: {team-name} appears in list

# 3. Verify workflow copied
cat .claude/ACTIVE_WORKFLOW.yaml
# Expected: Contains team's workflow configuration

# 4. Verify agents copied
ls .claude/agents/
# Expected: Agent files match roster agents/

# 5. Count agents vs phases
ls ~/Code/roster/teams/{team-name}/agents/ | wc -l
grep -c "^  - name:" ~/Code/roster/teams/{team-name}/workflow.yaml
# Expected: Agent count = phase count (±1 for orchestrator)

# 6. Verify terminal phase
grep -B1 "next: null" ~/Code/roster/teams/{team-name}/workflow.yaml
# Expected: Shows terminal phase name and agent

# 7. Test command routing
grep -B1 "produces: tdd" .claude/ACTIVE_WORKFLOW.yaml  # /architect
grep -B1 "produces: code" .claude/ACTIVE_WORKFLOW.yaml # /build
grep -B1 "next: null" .claude/ACTIVE_WORKFLOW.yaml     # /qa
```

---

## Consultant Knowledge Base (REQUIRED)

> **CRITICAL**: The Consultant agent is the ecosystem's navigation system. Stale data = wrong user guidance.

### Ecosystem Map
- [ ] `ecosystem-map.md` updated with new team in Teams table
- [ ] Team count updated (currently 9 teams)
- [ ] Agent count updated (currently 36 agents)

### Agent Reference
- [ ] `agent-reference.md` updated with new team section
- [ ] All agents listed with model and phase
- [ ] Workflow summary included

### Team Profile
- [ ] New file created: `team-profiles/{team-name}.md`
- [ ] Profile includes: Overview, Switch Command, Agents, Workflow
- [ ] Complexity levels documented
- [ ] Best For / Not For sections completed
- [ ] Quick Start example provided

### Routing Updates
- [ ] `routing/intent-patterns.md` updated with team keywords
- [ ] `routing/decision-trees.md` updated with routing logic
- [ ] `routing/complexity-matrix.md` updated with team's levels

### Command Reference
- [ ] `command-reference.md` updated with new quick-switch command
- [ ] Command appears in correct section (Team Management)

### Verification
```bash
# Check team appears in ecosystem map
grep "{team-name}" .claude/knowledge/consultant/ecosystem-map.md

# Check agents are listed
grep "{entry-agent}" .claude/knowledge/consultant/agent-reference.md

# Check profile exists
cat .claude/knowledge/consultant/team-profiles/{team-name}.md

# Check routing
grep "{team-name}" .claude/knowledge/consultant/routing/intent-patterns.md
```

---

## Final Sign-Off

- [ ] All checklist items verified
- [ ] Verification commands pass
- [ ] Team tested with sample task
- [ ] Documentation reviewed for accuracy
- [ ] **Consultant knowledge base synchronized**
