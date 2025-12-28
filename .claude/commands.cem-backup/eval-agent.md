---
description: Test a single agent in isolation
argument-hint: <agent-name> [--team=<team-name>] [--adversarial]
allowed-tools: Bash, Glob, Grep, Read, Task, TodoWrite
model: claude-opus-4-5
---

## Context

Auto-injected by SessionStart hook (project, team, session context).

## Your Task

Test the agent: $ARGUMENTS

## Behavior

### 1. Parse Arguments

- `agent-name`: Required. Name of agent to test (e.g., `principal-engineer`)
- `--team`: Optional. Team containing the agent. Defaults to active team.
- `--adversarial`: Optional. Include adversarial prompts in testing.

### 2. Locate Agent

Find agent file at:
- `.claude/agents/{agent-name}.md` (if in active team)
- `~/Code/roster/teams/{team-name}/agents/{agent-name}.md` (if team specified)
- `.claude/global-agents/{agent-name}.md` (if global agent)

If not found, report error with available agents.

### 3. Invoke Eval Specialist

Use the Task tool to invoke the eval-specialist agent:

```
"Test the agent {agent-name} in isolation.

Agent file: {path-to-agent}

Run the following checks:
1. Completeness - All 11 sections present
2. Frontmatter - Required fields valid
3. Examples - Realistic and helpful
4. Anti-patterns - Specific and actionable
5. Token count - Within budget

{If --adversarial}
Also run adversarial prompts:
- Ambiguous requests
- Out-of-scope requests
- Conflicting requirements
- Edge cases for this agent's domain

Report pass/fail for each check with specific findings."
```

### 4. Report Results

Display test results:

```
AGENT EVAL: {agent-name}
========================
Location: {path}
Model: {model from frontmatter}

Completeness:  {✓|✗}
Frontmatter:   {✓|✗}
Examples:      {✓|✗}
Anti-patterns: {✓|✗}
Token count:   {N} tokens {✓|✗}

{If adversarial}
Adversarial:   {✓|✗}
  - Ambiguous:    {result}
  - Out-of-scope: {result}
  - Conflicting:  {result}
  - Edge cases:   {result}

Overall: {PASS | FAIL}
{Any specific issues found}
```

## Example Usage

```bash
# Test agent in active team
/eval-agent principal-engineer

# Test agent in specific team
/eval-agent threat-modeler --team=security-pack

# Test with adversarial prompts
/eval-agent architect --adversarial

# Test global agent
/eval-agent consultant
```

## Reference

Full documentation: `.claude/skills/forge-ref/skill.md`
Agent completeness checklist: `.claude/knowledge/forge/evals/agent-completeness.md`
