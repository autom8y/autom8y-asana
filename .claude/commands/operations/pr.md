---
name: pr
description: Create pull request with comprehensive description
argument-hint: "[title] [--base=BRANCH]"
allowed-tools: Bash, Read, Glob, Grep
model: sonnet
disable-model-invocation: true
context: fork
---

## Context
Auto-injected by SessionStart hook (project, rite, session).

Base branch for PR targeting: detect via `git symbolic-ref refs/remotes/origin/HEAD` or default to `main`.

## Your Task

Create a GitHub pull request with auto-generated description. $ARGUMENTS

## Behavior

1. **Analyze changes** (gather fresh volatile context):
   - Count divergent commits with `git rev-list --count HEAD ^origin/<base_branch>`
   - List changed files with `git diff --name-only origin/<base_branch>`
   - Review all commits since branch divergence
   - Identify related PRD/TDD/ADR artifacts

2. **Generate PR description**:
   ```markdown
   ## Summary
   [Auto-generated from commits and artifacts]

   ## Changes
   - [List of key changes]

   ## Test Plan
   - [Derived from test plan if exists]

   ## Artifacts
   - PRD: [link if exists]
   - TDD: [link if exists]

   ## Checklist
   - [ ] Tests pass
   - [ ] Code reviewed
   - [ ] Documentation updated
   ```

3. **Create PR** via `gh pr create`:
   ```bash
   gh pr create --title "..." --body "..."
   ```

4. **Return PR URL**

## Example

```
/pr "Add user authentication"
/pr --base=develop
```

## Reference

Full documentation: `.claude/commands/operations/pr/INDEX.md`

## Sigil

### On Success

End your response with:

📬 opened · next: {hint}

**Fork-context note**: This command may run without conversation history. To resolve the hint, read session state from disk:
- Find active session: look for `status: "ACTIVE"` in `.sos/sessions/*/SESSION_CONTEXT.md`
- Read `current_phase` from its frontmatter and check `.knossos/ACTIVE_WORKFLOW.yaml` for phase ordering
- No active session found → output `📬 opened` without hint.

Natural follow-on: `next: /code-review {pr_number}` or `next: merge when green`.

### On Failure

❌ pr failed: {brief reason} · fix: {recovery}

Infer recovery: no divergent commits → `/commit` first; not on a branch → create a branch; gh CLI error → check `gh auth status`; uncertain → `/consult`.
