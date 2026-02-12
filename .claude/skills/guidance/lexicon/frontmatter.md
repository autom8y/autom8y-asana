# Frontmatter Field Reference

How each YAML frontmatter field maps to CC runtime behavior.

## Agent Frontmatter

| Field | CC Behavior | Required |
|---|---|---|
| `name` | Target for `Task(subagent_type="name")`. Must be unique across all agents. | Yes |
| `description` | CC reads this to decide routing. Include trigger phrases, use cases, examples. | Yes |
| `tools` | Constrains which tools the agent can use. CC enforces this at runtime. | Yes |
| `model` | Routes to specific model (opus/sonnet/haiku). Affects capability and cost. | No (inherits parent) |
| `color` | UI display only. No CC runtime effect. | No |
| `type` | Knossos metadata for validation (`meta`, `designer`, `engineer`, `reviewer`). CC ignores. | No |
| `role` | Short role label for agent tables. CC ignores. | No |
| `contract` | Knossos validation constraints (`must_not` rules). CC ignores at runtime. | No |
| `aliases` | Alternative names for `ari` CLI routing. CC ignores. | No |

### Description Best Practices

The `description` field is the single most important field for CC routing. CC reads agent descriptions to decide which subagent to invoke via Task tool.

**Effective pattern:**
```yaml
description: |
  What this agent does (one line). Use when: condition1, condition2, condition3.
  Triggers: keyword1, keyword2, keyword3.

  <example>
  Context: situation
  user: "request"
  assistant: "response showing routing decision"
  </example>
```

**Why examples matter:** CC uses `<example>` tags in descriptions to learn routing patterns. More examples = more accurate routing.

## Dromena Frontmatter (Slash Commands)

| Field | CC Behavior | Required |
|---|---|---|
| `name` | Becomes the `/name` slash command. CC discovers via `.claude/commands/` listing. | Yes |
| `allowed-tools` | Tools the command can use during execution. | No |
| `disable-model-invocation` | **Critical**: When `true`, prevents CC from invoking this command autonomously. Use for commands with side effects (commits, pushes, deployments). | No |
| `argument-hint` | Displayed to user as argument placeholder text. | No |

### `disable-model-invocation` Decision Guide

| Has Side Effects? | User Must Control? | Set `disable-model-invocation`? |
|---|---|---|
| Yes (writes, sends, deploys) | Yes | `true` |
| No (reads, analyzes, formats) | No | `false` or omit |

## Legomena Frontmatter (Skills)

| Field | CC Behavior | Required |
|---|---|---|
| `name` | Key for `Skill("name")` invocation. CC discovers via `<available_skills>` system-reminder. | Yes |
| `description` | **Activation trigger.** CC reads this to decide whether to load the skill autonomously. Precision here directly controls false-positive and false-negative loading rates. | Yes |

### Legomena Description = Discovery Mechanism

CC sees a list of available skills with their descriptions. When a user request matches a description, CC loads that skill. This means:

- **Too vague** ("helps with documentation") = skill never loads when needed
- **Too broad** ("use for any writing task") = skill loads when not needed, wasting tokens
- **Just right** ("PRD, TDD, ADR, and Test Plan templates. Activated by template requests, artifact formats, documentation workflows") = loads precisely when relevant
