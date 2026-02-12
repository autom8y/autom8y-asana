---
name: lexicon
description: "Knossos-to-CC primitive mapping. Use when: understanding dromena vs legomena distinction, mapping knossos concepts to CC runtime, checking frontmatter schema. Triggers: lexicon, CC primitives, invocation mapping, frontmatter reference, knossos terminology."
---

# Framework Lexicon

Knossos concepts mapped to Claude Code (CC) runtime primitives.

## The Three Invocation Primitives

| CC Primitive | Knossos Name | How CC Discovers It | Invocation |
|---|---|---|---|
| **Slash command** | Dromena | Directory listing of `.claude/commands/` | User types `/name` |
| **Skill tool** | Legomena | `<available_skills>` system-reminder | Model calls `Skill("name")` |
| **Task tool** | Agent | `subagent_type` parameter matching agent name | Model calls `Task(subagent_type="name")` |

**Behavioral difference**: Dromena are transient and user-controlled (execute, return result, exit context). Legomena are persistent and model-controlled (loaded into context, stay until session ends).

## Additional CC Primitives

| CC Primitive | Knossos Name | Function |
|---|---|---|
| **Hook** | Hook | Shell command auto-fired on lifecycle events (tool calls, prompt submit) |
| **CLAUDE.md** | Inscription | Always-loaded project instructions, assembled from templates |
| **settings.json** | MCP/permissions | Tool permissions, MCP server config, model routing |

## What CC Does NOT Understand

These conventions have zero CC runtime meaning. Do not use them in prompts:

| Syntax | Problem | Correct Form |
|---|---|---|
| `@skill-name` | CC has no `@` resolution | `Skill("skill-name")` or just name the skill |
| `` `skill-name` `` in reference context | Backticks are formatting, not invocation | Plain text name or `Skill("name")` call |
| `skill-name#fragment` | CC cannot resolve fragments | Name the sub-file directly |
| `~/.claude/skills/path` | Absolute paths are fragile | Use skill name; CC resolves paths |

## Frontmatter Quick Reference

See `lexicon/frontmatter.md` for field-by-field CC behavior mapping.

**Fields CC uses at runtime:**
- Agent: `name`, `description`, `tools`, `model`
- Dromena: `name`, `allowed-tools`, `disable-model-invocation`, `argument-hint`
- Legomena: `name`, `description` (activation trigger)

**Fields CC ignores** (knossos-only metadata): `type`, `role`, `contract`, `color`, `aliases`, `upstream`, `downstream`, `produces`

## Top Anti-Patterns

| Pattern | Problem | Fix |
|---|---|---|
| Dromena described as "invoke via Skill tool" | Dromena are slash commands, not skills | Use correct primitive name |
| Agent prompt explains how Task tool works | CC already knows its own tools | Remove; trust CC intelligence |
| Agent prompt explains REST/git/markdown | CC has this knowledge built in | Remove generic knowledge |
| `tools: Task` on a subagent | Subagents cannot spawn other agents | Remove Task from subagent tools |
| Vague legomena description | CC can't match intent to load skill | Write precise trigger phrases |

See `lexicon/anti-patterns.md` for migration checklist.

## Knossos-Only Terms

See `lexicon/knossos-only.md` for framework terms with no CC equivalent (rite, materialization, mena, inscription, etc.).
