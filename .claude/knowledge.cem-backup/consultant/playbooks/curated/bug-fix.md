# Playbook: Bug Fix

> Quick resolution for bugs and broken behavior

## When to Use

- Something is broken and needs fixing
- User-reported bug
- Test failure
- Regression

## Prerequisites

- Bug description or reproduction steps
- Access to affected code

## Command Sequence

### Phase 1: Hotfix Mode

```bash
/hotfix
```
**Expected output**: Hotfix workflow initiated
**Decision point**: If bug is complex (security, data corruption), consider full `/10x` workflow instead.

### Phase 2: Diagnose

The hotfix workflow guides you through:
1. Reproduce the issue
2. Identify root cause
3. Determine fix scope

**Decision point**:
- Simple fix → Continue with hotfix
- Complex fix → `/10x` → `/task "Fix: description"`

### Phase 3: Fix

Implement the fix with tests.

**Expected output**: Code changes with test coverage

### Phase 4: Verify

Verify fix resolves the issue.

**Expected output**: Tests pass, bug no longer reproducible

### Phase 5: Ship

```bash
/pr
```
**Expected output**: Pull request with bug fix

## Variations

- **Critical production bug**: Coordinate with `/sre` for incident response
- **Security bug**: Use `/security` for review before shipping
- **Complex root cause**: Escalate to full `/10x` workflow

## Success Criteria

- [ ] Bug reproduced before fix
- [ ] Root cause identified
- [ ] Fix implemented with tests
- [ ] Bug verified resolved
- [ ] PR created

## Quick Path

For truly simple bugs:
```bash
/hotfix
# Fix is obvious and small
# Make change directly
/pr --draft
```
