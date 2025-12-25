---
description: Get ecosystem guidance, team recommendations, and command-flows
argument-hint: [query] [--playbook=NAME] [--team] [--commands]
allowed-tools: Bash, Read, Grep, Glob, Task
model: claude-opus-4-5
---

## Context

Auto-injected by SessionStart hook (project, team, session, git).

**Active team**: !`cat .claude/ACTIVE_TEAM 2>/dev/null || echo "none"`
**Available teams**: !`ls ~/Code/roster/teams/ 2>/dev/null | tr '\n' ' '`

## Your Task

Provide ecosystem guidance and recommendations. $ARGUMENTS

## Behavior

### No arguments (general help)
1. Summarize current ecosystem state (active team, session status)
2. Display the 9 teams with brief descriptions
3. List common starting points based on user goals
4. Point to playbook library for detailed workflows

### Query provided (e.g., `/consult "improve code quality"`)
1. Parse user intent using knowledge base
2. Consult `.claude/knowledge/consultant/routing/intent-patterns.md`
3. Match to appropriate team and workflow
4. Provide command-flow with phases and decision points
5. Offer alternatives if multiple valid approaches exist

### `--playbook=NAME` flag
1. Load playbook from `.claude/knowledge/consultant/playbooks/curated/{NAME}.md`
2. Present complete workflow with current context
3. If not found, list available playbooks

### `--team` flag
Display all 9 teams:
```
| Team              | Command       | Best For                           |
|-------------------|---------------|------------------------------------|
| 10x-dev-pack      | /10x          | Full feature development lifecycle |
| doc-team-pack     | /docs         | Documentation, technical writing   |
| hygiene-pack      | /hygiene      | Code quality, refactoring          |
| debt-triage-pack  | /debt         | Technical debt prioritization      |
| sre-pack          | /sre          | Operations, reliability            |
| security-pack     | /security     | Security assessment, compliance    |
| intelligence-pack | /intelligence | Analytics, A/B testing, research   |
| rnd-pack          | /rnd          | Exploration, prototyping           |
| strategy-pack     | /strategy     | Market research, business analysis |
```

### `--commands` flag
Display all commands by category:
```
Session (5): /start, /park, /continue, /handoff, /wrap
Team (10): /team, /10x, /docs, /hygiene, /debt, /sre, /security, /intelligence, /rnd, /strategy
Workflow (4): /task, /sprint, /hotfix, /spike
Operations (5): /architect, /build, /qa, /pr, /code-review
```

## Response Format

Always structure responses as:

1. **Assessment**: What you understand the user needs
2. **Recommendation**: Which team/workflow fits best
3. **Command-Flow**: Step-by-step commands to execute
4. **Alternatives**: Other valid approaches (if any)

## Example Interactions

```bash
# General guidance
/consult

# Specific goal
/consult "I need to add user authentication"

# Load specific playbook
/consult --playbook=new-feature

# List all teams
/consult --team

# List all commands
/consult --commands
```

## Knowledge Sources

- `.claude/knowledge/consultant/ecosystem-map.md` - System overview
- `.claude/knowledge/consultant/routing/` - Intent matching
- `.claude/knowledge/consultant/team-profiles/` - Deep team knowledge
- `.claude/knowledge/consultant/playbooks/curated/` - Pre-built workflows

## Reference

Full documentation: `.claude/skills/consult-ref/skill.md`
