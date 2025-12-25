# Playbook: Code Quality Audit

> Systematic assessment and improvement of code quality

## When to Use

- Periodic codebase health check
- Before major refactoring
- New team member onboarding
- Pre-release quality gate
- Technical debt assessment

## Prerequisites

- Clear scope (module, directory, or full codebase)
- Time allocated for remediation

## Command Sequence

### Phase 1: Switch to Hygiene Team

```bash
/hygiene
```
**Expected output**: Team switched to hygiene-pack

### Phase 2: Start Audit Session

```bash
/start "Code audit - [area]" --complexity=MODULE
```
**Expected output**: Session created, audit-lead invoked
**Decision point**: Complexity levels:
- SPOT: Single file
- MODULE: Directory/component
- CODEBASE: Entire repository

### Phase 3: Assessment

Audit Lead creates initial assessment.

**Expected output**: Audit report with findings overview

### Phase 4: Detection

Code Smeller identifies specific issues.

**Expected output**: Smell inventory with locations and severity

### Phase 5: Remediation Planning

Review findings and prioritize.

**Decision point**:
- Fix all now → Continue to remediation
- Fix later → Document and `/park`
- Too much debt → Consider `/debt` for strategic triage

### Phase 6: Remediation

```bash
# Janitor executes fixes
```
**Expected output**: Clean code, issues resolved

### Phase 7: Validation

Architect Enforcer validates compliance.

**Expected output**: Compliance report

### Phase 8: Wrap Up

```bash
/wrap
```
**Expected output**: Audit summary with improvements made

## Variations

- **Audit only (no fix)**: Stop after Phase 4, document for later
- **Focused audit**: Target specific patterns or anti-patterns
- **Pre-merge audit**: Review specific changes before merge

## Success Criteria

- [ ] Scope defined and assessed
- [ ] Issues inventoried with severity
- [ ] Priority issues remediated
- [ ] Compliance validated
- [ ] Session documented
