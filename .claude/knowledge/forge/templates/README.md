# Forge Templates Index

> Pointers to templates used by The Forge

## Agent Templates

The Forge uses templates from the team-development skill:

| Template | Location | Purpose |
|----------|----------|---------|
| Agent Prompt | `.claude/skills/team-development/templates/agent.md.template` | 11-section agent file |
| Workflow YAML | `.claude/skills/team-development/templates/workflow.yaml.template` | Team workflow config |
| Quick-Switch Command | `.claude/skills/team-development/templates/quick-switch.md.template` | Team switching command |
| Skill Reference | `.claude/skills/team-development/templates/skill-ref.md.template` | Team documentation |

## When to Use Each Template

### agent.md.template

Used by **Prompt Architect** when creating agent files.

Key sections:
- YAML frontmatter with name, description, tools, model, color
- 11 standard body sections

### workflow.yaml.template

Used by **Workflow Engineer** when defining team orchestration.

Key elements:
- entry_point definition
- phases array
- complexity_levels
- command mapping comments

### quick-switch.md.template

Used by **Workflow Engineer** when creating team commands.

Creates commands like `/10x`, `/security`, etc.

### skill-ref.md.template

Used by **Agent Curator** when documenting teams.

Creates reference documentation at `.claude/skills/{team}-ref/skill.md`

## Forge-Specific Patterns

In addition to templates, The Forge uses patterns from:

```
.claude/knowledge/forge/patterns/
├── role-definition.md      # How to define agent roles
├── domain-authority.md     # decide/escalate/route structure
└── handoff-criteria.md     # Verification checklists
```

## Template Usage by Forge Agent

| Agent | Uses Templates |
|-------|----------------|
| Agent Designer | role-definition pattern |
| Prompt Architect | agent.md.template |
| Workflow Engineer | workflow.yaml.template, quick-switch.md.template |
| Platform Engineer | (creates directories, copies files) |
| Eval Specialist | eval harnesses |
| Agent Curator | skill-ref.md.template |

## Creating New Templates

If a new template type is needed:

1. Create in `.claude/knowledge/forge/templates/`
2. Document in this README
3. Update relevant Forge agent to reference it
