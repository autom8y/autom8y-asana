---
name: consult
description: Get ecosystem guidance, rite recommendations, and command-flows
argument-hint: "[query] [--playbook=NAME] [--rite] [--commands]"
allowed-tools: Bash, Read, Grep, Glob, WebSearch
model: opus
---

## Cognitive Load Absorber Role

`/consult` is the designated entry point for users who are confused, overwhelmed, or unsure where to start. When users don't know which rite, workflow, or command to use, `/consult` absorbs that cognitive load by:

1. **Parsing natural language intent** - Understanding what the user wants to accomplish
2. **Matching to ecosystem capabilities** - Identifying the right rite, workflow, and complexity
3. **Providing actionable patterns** - Referencing `prompting` skill for exact invocation commands
4. **Explaining the journey** - Referencing `10x-workflow` for phase transitions and quality gates

**Key principle**: Users describe outcomes; `/consult` handles routing complexity.

## Context

Auto-injected by SessionStart hook (project, rite, session, git).

The active rite is available in your session context (injected at session start via the `rite` field).
Available rites are listed in your session context (`available_rites` field).

## Pre-flight

1. **Knowledge base accessible**:
   - Verify `${KNOSSOS_HOME:-~/Code/knossos}/rites/` exists
   - If missing: WARN "Knossos not found at expected location."

## Your Task

Provide ecosystem guidance and recommendations. $ARGUMENTS

## Behavior

### No arguments (general help)
1. Summarize current ecosystem state (active rite, session status)
2. Display rites dynamically (use `rite-discovery` skill for current count)
3. List common starting points based on user goals
4. Point to playbook library for detailed workflows

### Query provided (e.g., `/consult "improve code quality"`)
1. Parse user intent using knowledge base
2. Use `rite-discovery` skill to match intent to rite routing conditions
3. Match to appropriate rite and workflow
4. **Reference invocation patterns**: Use `prompting` skill to retrieve exact copy-paste patterns
5. **Reference workflow context**: Use `10x-workflow` skill for phase/gate information
6. Provide command-flow with phases and decision points
7. Offer alternatives if multiple valid approaches exist

### `--playbook=NAME` flag
1. Load playbook from `~/.claude/knowledge/consultant/playbooks/curated/{NAME}.md`
2. Present complete workflow with current context
3. If not found, list available playbooks

### `--rite` flag
Display all rites dynamically (use `rite-discovery` skill):
```
| Rite              | Command       | Best For                           |
|-------------------|---------------|------------------------------------|
| 10x-dev      | /10x          | Full feature development lifecycle |
| debt-triage  | /debt         | Technical debt prioritization      |
| docs     | /docs         | Documentation, technical writing   |
| ecosystem    | /ecosystem    | knossos sync infrastructure        |
| forge        | /forge        | Rite creation and validation       |
| hygiene      | /hygiene      | Code quality, refactoring          |
| intelligence | /intelligence | Analytics, A/B testing, research   |
| rnd          | /rnd          | Exploration, prototyping           |
| security     | /security     | Security assessment, compliance    |
| sre          | /sre          | Operations, reliability            |
| strategy     | /strategy     | Market research, business analysis |
```
**Note**: This list reflects current rite catalog. Use `rite-discovery` skill for programmatic access.

### `--commands` flag
Display all commands by category:
```
Session (5): /start, /park, /continue, /handoff, /wrap
Rite (10): /rite, /10x, /docs, /hygiene, /debt, /sre, /security, /intelligence, /rnd, /strategy
Workflow (4): /task, /sprint, /hotfix, /spike
Operations (5): /architect, /build, /qa, /pr, /code-review
```

## Response Format

Always structure responses as:

1. **Assessment**: What you understand the user needs
2. **Recommendation**: Which rite/workflow fits best
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

# List all rites
/consult --rite

# List all commands
/consult --commands
```

## Skill Reference Patterns

`/consult` references other skills to provide accurate, current information:

### Referencing prompting Skill

When providing invocation patterns, retrieve patterns from:
- `prompting/INDEX.lego.md` - Agent invocation quick reference
- `prompting/patterns/discovery.md` - PRD creation, session initialization
- `prompting/patterns/implementation.md` - TDD, coding, testing

**Pattern**: Instead of generating ad-hoc commands, extract from `prompting` skill.

### Referencing 10x-workflow Skill

When explaining workflow journeys, retrieve context from:
- `10x-workflow/INDEX.lego.md` - Agent routing, complexity calibration
- `10x-workflow/lifecycle.md` - Phase protocol (PLAN -> CLARIFY -> EXECUTE -> VERIFY -> HANDOFF)
- `10x-workflow/quality-gates.md` - Gate criteria per phase

**Pattern**: Include quality gate expectations when describing phase transitions.

### Referencing rite-discovery Skill

When recommending rites, retrieve current rite inventory from:
- `rite-discovery` skill for dynamic rite list
- `rite-discovery/schemas/rite-profile.yaml` for profile structure

**Pattern**: Never hardcode rite counts or capabilities; always read from `rite-discovery`.

## Knowledge Sources

- `$KNOSSOS_HOME/rites/*/orchestrator.yaml` - Rite profiles (via rite-discovery)
- `prompting` skill - Invocation patterns
- `10x-workflow` skill - Phase transitions and quality gates

## Reference

Full documentation: `.claude/commands/navigation/consult/INDEX.md`
