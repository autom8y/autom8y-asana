---
user-invocable: false
---

# /commit Examples

> Usage scenarios with sample outputs.

## Example 1: Simple Feature Commit

**Command**:
```bash
/commit
```

**Output**:
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

---

## Example 2: Stage All and Commit

**Command**:
```bash
/commit --all
```

**Output**:
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

---

## Example 3: Override Message

**Command**:
```bash
/commit --message="fix: resolve race condition in auth worker"
```

**Output**:
```
Using provided message.

Committed: jkl012

fix: resolve race condition in auth worker

1 file changed, 5 insertions(+), 2 deletions(-)
```

---

## Example 4: Smart Staging Interaction

**Command**:
```bash
/commit
```

**Output**:
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

## Edge Case Examples

### Edge Case: No Session Active

**Scenario**: User runs `/commit` without starting a session.

**Command**:
```bash
/commit
```

**Output**:
```
Staged files:
  src/utils/format.ts (modified)

Proposed commit:
────────────────────────────────────
refactor(utils): extract date formatting logic

- Extract formatDate helper function
- Remove duplication across components
────────────────────────────────────

1 file changed, 15 insertions(+), 8 deletions(-)

Proceed? [Y/n/edit] Y

Committed: pqr678

refactor(utils): extract date formatting logic
```

**Notes**: Commit works normally. No session tracking note appears (no session active).

---

### Edge Case: Nothing Staged, --all Not Provided

**Scenario**: User runs `/commit` with no staged changes and doesn't use `--all`.

**Command**:
```bash
/commit
```

**Output**:
```
No files staged. Stage these files?

Modified:
  [x] src/auth/login.ts
  [x] src/auth/utils.ts

Untracked:
  [ ] src/auth/config.ts  (appears related)
  [ ] notes.txt           (skip - likely scratch)

[A]ll / [S]elected / [M]anual select / [C]ancel: C

Aborted.
```

**Notes**: User canceled staging. No commit created.

---

### Edge Case: Merge Conflict State

**Scenario**: User runs `/commit` during merge conflict.

**Command**:
```bash
/commit
```

**Output**:
```
Error: Cannot commit during merge conflict

Unmerged paths:
  both modified:   src/auth/login.ts
  both modified:   src/auth/utils.ts

Resolve conflicts first:
1. Edit conflicted files
2. Mark as resolved: git add <file>
3. Complete merge: git commit (or re-run /commit)

Run: git status
```

**Notes**: Detects merge conflict via `git status | grep "Unmerged paths"`. Exits without commit.

---

### Edge Case: Detached HEAD State

**Scenario**: User runs `/commit` in detached HEAD.

**Command**:
```bash
/commit
```

**Output**:
```
Warning: You are in detached HEAD state

Current commit: abc1234
Not on any branch.

Recommendation: Create a branch first
  git checkout -b <branch-name>

Proceed with commit anyway? [y/N]: n

Aborted.
```

**Notes**: Warns about detached HEAD. If user confirms, commit works (git allows this).

---

### Edge Case: Pre-commit Hook Failure

**Scenario**: `git commit` fails due to pre-commit hook (e.g., linting).

**Command**:
```bash
/commit
```

**Output**:
```
Staged files:
  src/utils/format.ts (modified)

Proposed commit:
────────────────────────────────────
refactor(utils): extract date formatting

- Extract formatDate helper function
────────────────────────────────────

1 file changed, 15 insertions(+), 8 deletions(-)

Proceed? [Y/n/edit] Y

Error: Pre-commit hook failed

Hook output:
  src/utils/format.ts:12:5 - error TS2322: Type 'string' is not assignable to type 'Date'.

Fix the issues and re-run /commit.
```

**Notes**: Hook runs during `git commit` execution. Hook fails, commit rejected. User fixes and re-runs.

---

### Edge Case: Empty Commit Message

**Scenario**: AI generates empty message (defensive case).

**Command**:
```bash
/commit
```

**Output**:
```
Staged files:
  scratch.txt (modified)

Warning: Unable to generate meaningful commit message

Proposed commit:
────────────────────────────────────
chore: update files
────────────────────────────────────

1 file changed, 1 insertion(+)

Proceed? [Y/n/edit] e

Enter commit message: docs: add notes on API design

Committed: stu901

docs: add notes on API design
```

**Notes**: Fallback to generic message. User edits to provide meaningful message.

---

### Edge Case: Very Large Diff

**Scenario**: User staged 50+ files with thousands of lines.

**Command**:
```bash
/commit --all
```

**Output**:
```
Staging all changes...

Warning: Large commit detected
  52 files changed, 3847 insertions(+), 1205 deletions(-)
  Message generated from partial analysis

Proposed commit:
────────────────────────────────────
chore: major refactoring and dependency updates

- Restructure project directory layout
- Update all dependencies to latest versions
- Apply consistent code formatting
- Add missing type definitions
────────────────────────────────────

Note: Large commit - consider breaking into smaller commits

Proceed? [Y/n/edit] Y

Committed: vwx234
```

**Notes**: Truncates diff analysis to first 5000 lines. Generates message from available context. Recommends smaller commits.

---

### Edge Case: Commit Message Override

**Scenario**: User provides `--message="..."` flag.

**Command**:
```bash
/commit --message="fix: resolve null pointer in validator"
```

**Output**:
```
Using provided message.

Committed: yza567

fix: resolve null pointer in validator

1 file changed, 3 insertions(+), 1 deletion(-)
```

**Notes**: Skips message generation entirely. Uses provided message verbatim. Still verifies no AI markers.

---

## Troubleshooting

### "Not a git repository" Error

**Command**:
```bash
/commit
```

**Output**:
```
Error: Not a git repository

No .git directory found.

Initialize repository:
  git init

Or navigate to an existing repository:
  cd /path/to/repo
```

**Resolution**:
```bash
# Check if .git exists
ls -la .git

# If not, initialize
git init
```

---

### Session Not Tracking Commits

**Scenario**: User expects commit to be tracked but it's not appearing in session.

**Diagnosis**:
```bash
# Check if session is active
ls .sos/sessions/

# Check if session-utils.sh can find session
cat .sos/sessions/.tty-map/$(tty | md5)
```

**Output**:
```
No active session found for this TTY.

Start a session to enable commit tracking:
  /start "feature development"
```

---

### Pre-commit Hook Issues

**Scenario**: Pre-commit hook is blocking commit.

**Command**:
```bash
/commit
```

**Output**:
```
Error: Pre-commit hook failed

Hook output:
  npm run lint failed
  src/utils/format.ts: Line 12:5 - Unexpected semicolon

Fix the issue:
  npm run lint:fix

Then re-run: /commit

(To bypass hook - NOT RECOMMENDED):
  git commit --no-verify -m "message"
```

**Resolution**:
```bash
# Better: fix the hook issue
npm run lint:fix

# Then re-run
/commit
```
