---
name: commit-ref
description: "AI-assisted git commits with message generation and session tracking. CRITICAL: User-only attribution - no AI markers in commits. Triggers: /commit, commit changes, git commit, stage and commit."
---

# /commit - AI-Assisted Git Commits

> **Category**: Development Workflows | **Phase**: Implementation | **Complexity**: Low

## Purpose

Create git commits with AI-generated messages following conventional commit format. This command analyzes staged changes, generates appropriate commit messages, and executes the commit with user-only attribution.

Use this when:
- Ready to commit staged changes
- Want consistent conventional commit format
- Need smart staging suggestions
- Working within a session that tracks commits

**CRITICAL Attribution Policy**: Unlike `/pr` which adds AI attribution to PR descriptions, `/commit` produces commits with USER-ONLY attribution. No `Co-Authored-By`, `Generated with`, or any AI markers appear in git history.

---

## Usage

```bash
/commit [--all] [--message="override"]
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--all` | No | false | Stage all changes before commit (`git add -A`) |
| `--message` | No | - | Override AI-generated message |

---

## Behavior

### 1. Validate Git State

Check current git state:

```bash
# Verify in git repository
git rev-parse --git-dir

# Check for staged changes
git diff --staged --name-only

# If nothing staged, check for changes
git status --porcelain
```

**If not in git repo**: Error with guidance.
**If nothing staged**: Enter smart staging flow (unless `--all`).
**If merge conflict**: Error - resolve conflicts first.

### 2. Smart Staging (if needed)

When nothing is staged and `--all` not provided:

```
No files staged. Stage these files?

Modified:
  [x] src/auth/login.ts
  [x] src/auth/utils.ts

Untracked:
  [ ] src/auth/config.ts  (appears related)
  [ ] notes.txt           (skip - likely scratch)

[A]ll / [S]elected / [M]anual select / [C]ancel
```

User selects option, files are staged:

```bash
git add src/auth/login.ts src/auth/utils.ts
```

### 3. Analyze Staged Changes

Gather comprehensive change information:

```bash
# Statistics
git diff --staged --stat

# Full diff for analysis
git diff --staged

# File types changed
git diff --staged --name-only | xargs -I{} file {}
```

### 4. Generate Commit Message

Analyze changes and generate message following conventional commits:

**Format**: `type(scope): subject`

**Types** (in priority order for detection):
| Type | Description | Trigger Patterns |
|------|-------------|------------------|
| `feat` | New feature | New files, new exports, new API endpoints |
| `fix` | Bug fix | Error handling, edge case fixes, patches |
| `docs` | Documentation | README, comments, docstrings |
| `style` | Formatting | Whitespace, semicolons, formatting |
| `refactor` | Code restructure | Rename, extract, reorganize (no behavior change) |
| `test` | Tests | Test files, test utilities |
| `chore` | Maintenance | Dependencies, build config, CI |
| `perf` | Performance | Optimization, caching, lazy loading |
| `ci` | CI/CD | GitHub Actions, pipeline config |
| `build` | Build system | Webpack, bundler, compiler config |

**Scope**: Detected from changed file paths (e.g., `src/auth/` -> `auth`)

**Subject Line Rules**:
- Imperative mood: "add" not "added" or "adds"
- No period at end
- Max 50 characters
- Lowercase after type

**Body Rules** (for complex commits):
- Wrap at 72 characters
- Explain "why" not "what" (code shows what)
- Use bullet points for multiple changes

**Example Generation**:

Input (staged diff):
```diff
+++ b/src/auth/refresh.ts
@@ -0,0 +1,45 @@
+export async function refreshToken(token: string): Promise<string> {
+  // Implementation...
+}
```

Output:
```
feat(auth): add JWT refresh token support

- Implement automatic token refresh on expiry
- Add configurable expiration window (default 5min)
- Update auth middleware to handle refresh flow
```

### 5. Present for Confirmation

Display proposed commit:

```
Proposed commit:
────────────────────────────────────
feat(auth): add JWT refresh token support

- Implement automatic token refresh on expiry
- Add configurable expiration window (default 5min)
- Update auth middleware to handle refresh flow
────────────────────────────────────

3 files changed, 127 insertions(+), 12 deletions(-)

Proceed? [Y/n/edit]
```

**User options**:
- `Y` (default): Execute commit
- `n`: Abort
- `edit`: User provides replacement message

### 6. Execute Commit

**CRITICAL SECTION - Attribution Policy**

Execute commit with user as sole author:

```bash
git commit -m "feat(auth): add JWT refresh token support

- Implement automatic token refresh on expiry
- Add configurable expiration window (default 5min)
- Update auth middleware to handle refresh flow"
```

**DO NOT INCLUDE**:
- `--trailer "Co-Authored-By: Claude <noreply@anthropic.com>"`
- `--trailer "Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"`
- Footer: `Generated with [Claude Code](https://claude.com/claude-code)`
- Any variation of AI attribution

**Rationale**: The user:
1. Wrote or reviewed the code being committed
2. Staged the specific changes
3. Confirmed the commit message
4. Is the intellectual owner of the work
5. Is the sole author in every meaningful sense

The AI assistance in message generation is analogous to IDE autocomplete - helpful but not authorship.

### 7. Report Success

```
Committed: abc1234

feat(auth): add JWT refresh token support

3 files changed, 127 insertions(+), 12 deletions(-)

Session: commit tracked to add-auth-feature
```

---

## Workflow

```mermaid
graph TD
    A[/commit invoked] --> B{In git repo?}
    B -->|No| C[Error: Not a git repository]
    B -->|Yes| D{Merge conflict?}
    D -->|Yes| E[Error: Resolve conflicts first]
    D -->|No| F{Changes staged?}
    F -->|No| G{--all flag?}
    G -->|Yes| H[git add -A]
    G -->|No| I[Smart staging flow]
    I --> J{User confirms?}
    J -->|No| K[Abort]
    J -->|Yes| L[Stage selected]
    H --> M[Analyze changes]
    L --> M
    F -->|Yes| M
    M --> N[Generate message]
    N --> O{User confirms?}
    O -->|Edit| P[User edits message]
    P --> Q[Execute commit]
    O -->|Yes| Q
    O -->|No| K
    Q --> R{Session active?}
    R -->|Yes| S[Track to session]
    R -->|No| T[Report success]
    S --> T
```

---

## Deliverables

1. **Git Commit**: Created with conventional format message
2. **Session Tracking**: Commit logged to `commits.log` (if session active)
3. **SESSION_CONTEXT Update**: Commits table updated (if session active)
4. **Success Report**: Hash and summary displayed

---

## Examples

### Example 1: Simple Feature Commit

```bash
/commit
```

```
Staged files:
  src/components/Button.tsx (modified)
  src/components/Button.test.tsx (modified)

Proposed commit:
────────────────────────────────────
feat(components): add loading state to Button

- Add isLoading prop with spinner indicator
- Disable button interactions while loading
- Add tests for loading state behavior
────────────────────────────────────

2 files changed, 45 insertions(+), 3 deletions(-)

Proceed? [Y/n/edit] Y

Committed: def456

feat(components): add loading state to Button

Session: commit tracked to button-improvements
```

### Example 2: Stage All and Commit

```bash
/commit --all
```

```
Staging all changes...

Proposed commit:
────────────────────────────────────
chore: update dependencies and fix lint errors

- Bump react to 18.2.0
- Fix eslint warnings in utils/
- Update tsconfig strict settings
────────────────────────────────────

8 files changed, 234 insertions(+), 198 deletions(-)

Proceed? [Y/n/edit] Y

Committed: ghi789
```

### Example 3: Override Message

```bash
/commit --message="fix: resolve race condition in auth worker"
```

```
Using provided message.

Committed: jkl012

fix: resolve race condition in auth worker

1 file changed, 5 insertions(+), 2 deletions(-)
```

### Example 4: Smart Staging Interaction

```bash
/commit
```

```
No files staged. Stage these files?

Modified:
  [x] src/api/users.ts
  [x] src/api/users.test.ts

Untracked:
  [x] src/api/types.ts  (new file, appears related)
  [ ] scratch.md        (skip - scratch file)

[A]ll / [S]elected / [M]anual / [C]ancel: S

Staged 3 files.

Proposed commit:
────────────────────────────────────
feat(api): add user CRUD endpoints

- Implement GET/POST/PUT/DELETE for /users
- Add TypeScript types for User entity
- Add comprehensive test coverage
────────────────────────────────────

3 files changed, 189 insertions(+)

Proceed? [Y/n/edit] Y

Committed: mno345
```

---

## Error Cases

| Error | Condition | Resolution |
|-------|-----------|------------|
| Not a git repository | No `.git` directory | Run `git init` or navigate to repo |
| Nothing to commit | No staged or unstaged changes | Make changes first |
| Merge conflict | Unresolved merge in progress | Run `git status`, resolve conflicts |
| Detached HEAD | Not on a branch | Create branch: `git checkout -b branch-name` |
| Pre-commit hook failed | Hook rejected commit | Fix issues, re-run `/commit` |
| Protected branch | Commit blocked by config | Switch to feature branch |

---

## Integration with Sessions

### With Active Session

When a session is active (started via `/start`):

1. **Commit Logged**: Entry added to `$SESSION_DIR/commits.log`
2. **Context Updated**: `## Commits` table in SESSION_CONTEXT.md updated
3. **Audit Trail**: Commit linked to session initiative

```
# $SESSION_DIR/commits.log
2025-12-26T14:30:00Z | COMMIT | abc1234 | feat(auth): add JWT refresh
2025-12-26T15:45:00Z | COMMIT | def5678 | fix(auth): handle expired tokens
```

```markdown
# SESSION_CONTEXT.md
## Commits
| Time | Hash | Message |
|------|------|---------|
| 14:30 | abc1234 | feat(auth): add JWT refresh |
| 15:45 | def5678 | fix(auth): handle expired tokens |
```

### Without Session

Commit works normally:
- No logging to session files
- No SESSION_CONTEXT update
- User still gets commit message generation and execution

---

## Attribution Policy

### What Makes This Different from /pr

| Command | Attribution | Location | Rationale |
|---------|-------------|----------|-----------|
| `/pr` | AI attribution included | PR description | PR metadata, visible to reviewers, editable |
| `/commit` | User-only | Git history | Permanent record, authorship matters |

### Why User-Only Attribution

1. **Intellectual Ownership**: User wrote/reviewed code, chose what to stage, confirmed message
2. **Legal Clarity**: Git history used for copyright/licensing attribution
3. **Blame/Credit**: `git blame` should show actual code owner
4. **Professional Standards**: Industry expectation for commit authorship
5. **Tool Analogy**: AI assistance is like IDE autocomplete, not co-authorship

### Verification

After using `/commit`, verify user-only attribution:

```bash
# Check last commit author
git log -1 --format='Author: %an <%ae>'
# Should show: Author: Your Name <your@email.com>

# Check for AI markers in message
git log -1 --format=%B | grep -i "claude\|generated\|co-authored"
# Should return empty (no matches)

# Full commit inspection
git log -1 --format=full
# Should show ONLY user as Author and Committer
```

---

## Related Commands

- `/pr` - Create pull request (after commits ready)
- `/start` - Begin session (enables commit tracking)
- `/wrap` - End session (includes commit summary)

---

## Related Skills

- [pr-ref](../pr-ref/skill.md) - Pull request workflow
- [10x-workflow](../10x-workflow/SKILL.md) - Development lifecycle
- [standards](../standards/SKILL.md) - Code conventions

---

## Notes

### Message Generation Quality

The AI analyzes:
- File paths for scope detection
- Diff content for change categorization
- Commit history for style consistency
- Project conventions (if `.commitlintrc` exists)

Quality depends on:
- Clear, focused changes (don't mix refactors with features)
- Meaningful file organization (scopes detected from paths)
- Staged changes representing atomic unit of work

### Conventional Commits Benefits

Following conventional commits enables:
- Automated changelog generation
- Semantic versioning automation
- Clear commit history
- CI/CD integration (commit type triggers)

Reference: https://www.conventionalcommits.org/

### Interactive Mode

Claude Code supports interactive prompts. The `/commit` command uses:
- Staging suggestions with checkboxes
- Message confirmation with Y/n/edit options
- User can always override or abort

### Pre-commit Hooks

If project has pre-commit hooks:
1. `/commit` executes `git commit`
2. Hooks run automatically
3. If hooks fail, commit is rejected
4. User fixes issues and re-runs `/commit`

Do NOT retry automatically or bypass hooks.

---

## Edge Cases

### Edge Case 1: No Session Active

**Scenario**: User runs `/commit` without starting a session.

**Behavior**:
- Commit works normally (message generation, execution)
- No logging to `commits.log`
- No SESSION_CONTEXT update
- Success message omits session tracking note

### Edge Case 2: Nothing Staged, --all Not Provided

**Scenario**: User runs `/commit` with no staged changes.

**Behavior**:
- Enter smart staging flow
- Display modified and untracked files with suggestions
- User selects files or cancels
- If cancel, abort without commit

### Edge Case 3: Merge Conflict State

**Scenario**: User runs `/commit` during merge conflict.

**Behavior**:
- Detect via `git status | grep "Unmerged paths"`
- Error: "Cannot commit during merge conflict. Resolve conflicts first."
- List conflicted files
- Exit without commit

### Edge Case 4: Detached HEAD State

**Scenario**: User runs `/commit` in detached HEAD.

**Behavior**:
- Warning: "You are in detached HEAD state"
- Suggest: "Create a branch first: `git checkout -b <branch-name>`"
- If user confirms proceed, commit works (git allows this)

### Edge Case 5: Pre-commit Hook Failure

**Scenario**: `git commit` fails due to pre-commit hook (e.g., linting).

**Behavior**:
- Hook runs during `git commit` execution
- Hook fails, commit rejected
- Display hook error output
- Do NOT retry automatically
- User fixes issues and re-runs `/commit`

### Edge Case 6: Empty Commit Message

**Scenario**: AI generates empty message (defensive case).

**Behavior**:
- Detect empty message after generation
- Fallback to generic: "chore: update files"
- Still show for confirmation (user likely wants to edit)

### Edge Case 7: Very Large Diff

**Scenario**: User staged 50+ files with thousands of lines.

**Behavior**:
- Truncate diff analysis to first 5000 lines
- Generate message from available context
- Note in output: "Large commit - message based on partial analysis"
- User can always edit message

### Edge Case 8: Commit Message Override

**Scenario**: User provides `--message="..."` flag.

**Behavior**:
- Skip message generation entirely
- Use provided message verbatim
- Still verify no AI markers in user input
- Execute commit directly

---

## Troubleshooting

### "Not a git repository" Error

```bash
# Check if .git exists
ls -la .git

# If not, initialize
git init
```

### Session Not Tracking Commits

```bash
# Check if session is active
ls .claude/sessions/

# Check if session-utils.sh can find session
cat .claude/sessions/.tty-map/$(tty | md5)
```

### Pre-commit Hook Issues

```bash
# Check hook status
ls -la .git/hooks/pre-commit

# Temporarily bypass (NOT RECOMMENDED)
git commit --no-verify -m "message"

# Better: fix the hook issue
npm run lint:fix  # or equivalent
```

### Commit Message Formatting Problems

If messages are poorly formatted:
1. Ensure changes are atomic (one logical change per commit)
2. Use meaningful file paths (helps scope detection)
3. Consider using `--message` for complex commits
4. Edit when prompted rather than accepting poor suggestions

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-26 | Initial implementation |

---

## Implementation Details

### Hook Registration

The `commit-tracker.sh` hook is registered in `.claude/settings.local.json`:

```json
{
  "PostToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": ".claude/hooks/commit-tracker.sh",
          "timeout": 5
        }
      ]
    }
  ]
}
```

### Hook Trigger Logic

The hook fires on ALL Bash tool uses but filters internally:

```bash
# Only process git commit commands
if [[ ! "$TOOL_COMMAND" =~ git[[:space:]]+commit ]]; then
  exit 0
fi

# Only track successful commits
if [[ ! "$TOOL_OUTPUT" =~ \[[^]]+[[:space:]][a-f0-9]+\] ]]; then
  exit 0
fi
```

### Session Integration

The hook uses `session-utils.sh` for session discovery:

```bash
source .claude/hooks/lib/session-utils.sh
SESSION_DIR=$(get_session_dir)
```

If no session exists, the hook exits silently without error.

---

## Security Considerations

### No Credential Exposure

The `/commit` command:
- Does not read or expose git credentials
- Does not modify git config
- Uses standard `git commit` command
- Respects existing authentication

### Attribution Integrity

The user-only attribution policy ensures:
- Git history accurately reflects human authorship
- Legal compliance for IP attribution
- Professional standards maintained
- No misleading commit metadata

### Hook Safety

The `commit-tracker.sh` hook:
- Runs with 5-second timeout
- Fails silently on errors (does not block commits)
- Does not modify git history
- Only appends to log files
