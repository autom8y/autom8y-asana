---
name: code-review
description: Structured review with categorized feedback
argument-hint: "<pr-number-or-branch> [--focus=AREA]"
allowed-tools: Bash, Read, Glob, Grep
model: opus
disable-model-invocation: true
context: fork
---

## Context
Auto-injected by SessionStart hook (project, rite, session, git, workflow).

## Pre-flight

1. **Discover review targets**:
   - List recent PRs with `gh pr list --limit 5` (requires gh CLI)
   - Check git status for uncommitted changes OR PR reference provided in $ARGUMENTS
   - If neither: ERROR "No changes to review. Provide PR number or ensure uncommitted changes exist."

## Your Task

Review changes with structured, categorized feedback. $ARGUMENTS

## Workflow Resolution

Use the validation agent in review mode:

```bash
# Get validation agent from workflow (last phase)
REVIEW_AGENT=$(grep -B1 "next: null" .knossos/ACTIVE_WORKFLOW.yaml | grep "agent:" | awk '{print $2}')
```

## Behavior

1. **Get changes to review**:
   - If PR number: `gh pr diff <number>`
   - If branch: `git diff main...<branch>`

2. **Invoke validation agent** (review mode) via Task tool:
   - Review all changed files/content
   - Apply multiple lenses
   - Agent varies by rite:
     - 10x-dev → qa-adversary
     - docs → doc-reviewer
     - hygiene → audit-lead

3. **Categorize feedback**:

   **Blocking Issues** (must fix):
   - Critical errors
   - Security vulnerabilities
   - Breaking changes

   **Suggestions** (should consider):
   - Improvements
   - Better patterns
   - Maintainability

   **Nits** (optional polish):
   - Style preferences
   - Naming tweaks
   - Minor documentation

4. **Provide recommendation**:
   - APPROVE: No blockers, good to merge
   - REQUEST CHANGES: Blockers found
   - COMMENT: Suggestions only, author decides

## Review Lenses

| Lens | Focus |
|------|-------|
| Functional | Does it work correctly? |
| Quality | Is it maintainable? |
| Security | Any vulnerabilities? |
| Accuracy | Is it correct? |

## Example

```
/code-review 123
/code-review feature/auth --focus=security
```

## Reference

Full documentation: `.claude/commands/operations/code-review/INDEX.md`

## Sigil

### On Success

End your response with:

🔍 reviewed · next: {hint}

**Fork-context note**: This command may run without conversation history. To resolve the hint, read session state from disk:
- Find active session: look for `status: "ACTIVE"` in `.sos/sessions/*/SESSION_CONTEXT.md`
- Read `current_phase` from its frontmatter and check `.knossos/ACTIVE_WORKFLOW.yaml` for phase ordering
- No active session found → output `🔍 reviewed` without hint.

Resolve hint from your review recommendation:
- APPROVE → `next: merge`
- REQUEST CHANGES → `next: fix issues, /commit`
- COMMENT → `next: author decides`

### On Failure

❌ review failed: {brief reason} · fix: {recovery}

Infer recovery: no changes to review → provide a PR number or branch; gh CLI error → check `gh auth status`; uncertain → `/consult`.
