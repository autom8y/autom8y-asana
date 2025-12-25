---
name: consult-ref
description: |
  Reference documentation for the Consultant and ecosystem navigation.
  Use when: learning about teams, commands, or workflows; understanding how to navigate
  the ecosystem; invoking the consultant. Triggers: /consult, which team, which command,
  how do I, what should I use, ecosystem guidance, command-flow, playbook.
---

# Consultant Reference

> Meta-level guidance for the Claude Code ecosystem

## Quick Reference

### By Goal

| I want to... | Use This |
|--------------|----------|
| Build a feature | `/10x` → `/task` |
| Fix a bug | `/hotfix` |
| Improve code quality | `/hygiene` → `/task` |
| Document something | `/docs` → `/task` |
| Address tech debt | `/debt` → `/task` |
| Security review | `/security` → `/task` |
| Research/explore | `/spike` or `/rnd` → `/task` |
| A/B test | `/intelligence` → `/task` |
| Strategic planning | `/strategy` → `/task` |
| Get help | `/consult` |

### By Team

| Team | Switch | Best For |
|------|--------|----------|
| 10x-dev-pack | `/10x` | Full feature development |
| doc-team-pack | `/docs` | Documentation |
| hygiene-pack | `/hygiene` | Code quality |
| debt-triage-pack | `/debt` | Tech debt management |
| sre-pack | `/sre` | Operations, reliability |
| security-pack | `/security` | Security assessment |
| intelligence-pack | `/intelligence` | Analytics, research |
| rnd-pack | `/rnd` | Exploration, prototyping |
| strategy-pack | `/strategy` | Business analysis |

### By Command Category

**Session (5)**: `/start`, `/park`, `/continue`, `/handoff`, `/wrap`

**Team (10)**: `/team`, `/10x`, `/docs`, `/hygiene`, `/debt`, `/sre`, `/security`, `/intelligence`, `/rnd`, `/strategy`

**Workflow (4)**: `/task`, `/sprint`, `/hotfix`, `/spike`

**Operations (5)**: `/architect`, `/build`, `/qa`, `/pr`, `/code-review`

**Meta (1)**: `/consult`

---

## How the Consultant Works

### Intent Recognition

When you describe what you want to do, the Consultant:
1. Parses keywords and patterns from your request
2. Matches against known intent patterns
3. Routes to appropriate team/command
4. Provides command-flow or playbook

### Routing Logic

```
User Intent → Intent Patterns → Decision Tree → Team/Command
```

See:
- `knowledge/consultant/routing/intent-patterns.md`
- `knowledge/consultant/routing/decision-trees.md`
- `knowledge/consultant/routing/complexity-matrix.md`

### Playbook System

**Curated Playbooks**: Pre-authored sequences for common scenarios
- `new-feature.md`
- `bug-fix.md`
- `code-audit.md`
- `documentation-refresh.md`
- `security-review.md`
- `performance-optimization.md`
- `tech-debt-sprint.md`
- `incident-response.md`

**Dynamic Generation**: For novel scenarios, Consultant generates custom playbooks.

---

## Using /consult

### General Help

```bash
/consult
```

Returns ecosystem overview and common starting points.

### Specific Guidance

```bash
/consult "I want to improve code quality"
```

Returns:
1. Assessment of your need
2. Team recommendation
3. Command sequence
4. Alternatives

### Load Playbook

```bash
/consult --playbook=new-feature
```

Returns curated playbook with full workflow.

### List Teams

```bash
/consult --team
```

Returns all 9 teams with descriptions.

### List Commands

```bash
/consult --commands
```

Returns all 24+ commands by category.

---

## Ecosystem Architecture

### Teams (9)

Each team has:
- **Agents**: Specialized roles (3-5 per team)
- **Workflow**: Sequential phases
- **Artifacts**: Documents produced
- **Complexity levels**: Scope-based gating

### Global Agents

Some agents persist across team swaps:
- **Consultant**: Always available for guidance

### Sessions

TTY-based isolation:
- Each terminal gets its own session
- Sessions can be parked and resumed
- State preserved in SESSION_CONTEXT.md

### Hooks

Automatic context injection:
- SessionStart: Loads project/team/git context
- Stop: Auto-parks session
- PostToolUse: Tracks artifacts
- PreToolUse: Validates commands

---

## Decision Trees

### Primary Router

```
BUILD → /10x → /task
FIX → /hotfix or /10x
DOCUMENT → /docs → /task
QUALITY → /hygiene → /task
DEBT → /debt → /task
SECURITY → /security → /task
RESEARCH → /spike or /rnd
ANALYTICS → /intelligence → /task
STRATEGY → /strategy → /task
OPERATIONS → /sre → /task
```

### Complexity Selection

```
1-2 files → Lowest level (SCRIPT, SPOT, PAGE, etc.)
Module/component → Middle level (MODULE)
Service/subsystem → High level (SERVICE)
Entire system → Highest level (PLATFORM, CODEBASE)
```

---

## Creating Custom Playbooks

### When to Create

- Repeated workflow not covered by curated playbooks
- Team-specific patterns
- Project-specific needs

### Playbook Format

```markdown
# Playbook: [Name]

> [One-line description]

## When to Use
- [Trigger condition]

## Prerequisites
- [Requirement]

## Command Sequence

### Phase 1: [Name]
```bash
/[command] [args]
```
**Expected output**: [What happens]
**Decision point**: [If X, do Y]

## Variations
- **[Variant]**: [Adjustment]

## Success Criteria
- [ ] [Criterion]
```

### Where to Save

Place in: `.claude/knowledge/consultant/playbooks/curated/`

---

## Troubleshooting

### "Which team should I use?"

1. Run `/consult --team`
2. Match your goal to team description
3. Or run `/consult "your goal"` for recommendation

### "What commands are available?"

1. Run `/consult --commands`
2. Commands organized by category
3. Or check COMMAND_REGISTRY.md

### "I'm stuck in a workflow"

1. Use `/park` to save state
2. Run `/consult` for guidance
3. Use `/continue` to resume

### "I need to switch teams mid-work"

1. Use `/handoff` to transfer context
2. Or `/park`, switch team, then start new session

---

## Related Resources

- [Ecosystem Map](../../knowledge/consultant/ecosystem-map.md)
- [Command Reference](../../knowledge/consultant/command-reference.md)
- [Agent Reference](../../knowledge/consultant/agent-reference.md)
- [Intent Patterns](../../knowledge/consultant/routing/intent-patterns.md)
- [Decision Trees](../../knowledge/consultant/routing/decision-trees.md)
- [Curated Playbooks](../../knowledge/consultant/playbooks/curated/)

---

## Cross-References

- **Workflow Skill**: @10x-workflow for detailed workflow info
- **Standards Skill**: @standards for code conventions
- **Prompting Skill**: @prompting for invocation patterns
- **Team Development**: @team-development for creating new teams

---

## Keeping Consultant Canonical

The Consultant's knowledge base MUST stay synchronized with ecosystem changes.

### When to Update

| Change Type | Action Required |
|-------------|-----------------|
| New team added | Update ecosystem-map, agent-reference, create team-profile |
| New command | Update command-reference, ecosystem-map |
| Workflow changed | Update team-profile, agent-reference |
| New playbook | Add to playbooks/curated/ |

### Synchronization Guide

See `.claude/skills/team-development/patterns/consultant-sync.md` for:
- Step-by-step update instructions
- File-by-file update matrix
- Validation commands

### Validation

```bash
# Quick check all teams have profiles
ls .claude/knowledge/consultant/team-profiles/

# Verify command count
grep -c "^| \`/" .claude/knowledge/consultant/command-reference.md
```

> **Rule**: Any PR that adds teams, commands, or agents MUST include Consultant knowledge updates.
