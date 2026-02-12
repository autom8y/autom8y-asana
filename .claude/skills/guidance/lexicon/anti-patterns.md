# Anti-Patterns & Migration Checklist

Common mistakes in agent prompts and how to fix them.

## Stale Syntax

| Find | Replace With | Why |
|---|---|---|
| `@skill-name` | `skill-name` (plain text) or `Skill("skill-name")` | CC has no `@` resolution mechanism |
| `` `skill-name` `` as invocation | Plain skill name or `Skill("name")` | Backticks are formatting, not invocation |
| `doc-artifacts#tdd-template` | `doc-artifacts` skill, TDD section | CC cannot resolve `#fragment` references |
| `~/.claude/skills/...` or `.claude/knowledge/...` | Skill name only | CC resolves paths from skill name |
| `Read(~/.claude/skills/moirai/INDEX.md)` | `Skill("moirai")` or load by name | Hardcoded paths break on restructure |

## Invocation Confusion

| Mistake | Correction |
|---|---|
| "Invoke dromena via Skill tool" | Dromena are slash commands (`/name`), not skills |
| Agent prompt says "use Task tool to spawn sub-agent X" | Subagents cannot spawn other agents (no Task tool access) |
| Agent executes silently without returning output | All operations must return structured responses |
| Legomena described as "slash command" | Legomena are `Skill("name")`, not `/name` |

## Frontmatter Mistakes

| Mistake | Correction |
|---|---|
| `tools: Task` on a subagent | Only main thread has Task tool; remove from subagent |
| Vague `description: "Helps with things"` | Write precise trigger phrases with use cases |
| Missing `disable-model-invocation` on side-effect dromena | Add `disable-model-invocation: true` for commits, pushes, etc. |
| Using `aliases` expecting CC routing | Aliases are `ari` CLI only; CC uses `name` field |

## Redundant Explanations

Content to remove from agent prompts because CC already knows it:

- How the Task tool works (invocation syntax, parameters)
- How the Skill tool works (loading mechanism)
- REST API conventions (HTTP methods, status codes)
- Git basics (branching, merging, commit messages)
- Markdown formatting rules
- JSON/YAML syntax
- Standard error handling patterns (try/catch, error propagation)
- Input validation basics (validate early, fail fast)
- Dependency injection as a concept
- "Prefer boring technology" and similar general engineering wisdom

## Agent Compression Checklist

When compressing an agent prompt:

1. Read the full agent + all linked skills + archetype template
2. For each section, ask: "Does CC need this to function as this agent?"
3. Remove content CC already knows (see Redundant Explanations above)
4. Remove content that exists in linked skills (reference the skill instead)
5. Remove duplicated templates/examples that exist in other files
6. Replace `@skill`, backtick, `#fragment` syntax with plain names
7. Replace stale paths (`.claude/knowledge/`, `~/.claude/skills/`) with skill names
8. Verify remaining content is unique to this agent's specific role
9. Check that `description` field has precise trigger phrases
