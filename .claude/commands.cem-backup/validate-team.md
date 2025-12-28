---
description: Run validation suite on an existing team pack
argument-hint: <team-name> [--verbose]
allowed-tools: Bash, Glob, Grep, Read, Task, TodoWrite
model: claude-opus-4-5
---

## Context

Auto-injected by SessionStart hook (project, team, session context).

## Your Task

Validate the team pack: $ARGUMENTS

## Behavior

### 1. Parse Arguments

- `team-name`: Required. Name of team to validate (with or without `-pack` suffix)
- `--verbose`: Optional. Show detailed check results

### 2. Locate Team

Check team exists at:
- `~/Code/roster/teams/{team-name}/` or
- `~/Code/roster/teams/{team-name}-pack/`

If not found, report error and suggest checking team name.

### 3. Invoke Eval Specialist

Use the Task tool to invoke the eval-specialist agent:

```
"Validate the team pack at ~/Code/roster/teams/{team-name}/.

Run the full validation suite:
1. Structure Validation - Check all files exist
2. Schema Validation - Verify frontmatter and workflow.yaml
3. Logic Validation - Check phase chain and complexity levels
4. Adversarial Testing - Run edge case prompts

Produce an eval-report.md with pass/fail status for each check.

Verbose mode: {verbose}"
```

### 4. Report Results

Display validation results:

```
VALIDATION REPORT: {team-name}
==============================
Status: {PASS | FAIL | WARNINGS}

Structure:  {✓|✗} All files exist
Schema:     {✓|✗} Frontmatter valid
Logic:      {✓|✗} Workflow coherent
Adversarial: {✓|✗} Edge cases handled

{If verbose, show detailed check results}

{If issues found, list them with severity}
```

## Example Usage

```bash
# Validate security-pack
/validate-team security-pack

# Validate with detailed output
/validate-team 10x-dev-pack --verbose

# Validate team (auto-adds -pack suffix)
/validate-team hygiene
```

## Reference

Full documentation: `.claude/skills/forge-ref/skill.md`
Validation checklist: `.claude/knowledge/forge/evals/`
