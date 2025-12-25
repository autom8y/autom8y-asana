# Playbook: Tech Debt Sprint

> Strategic debt paydown across a focused period

## When to Use

- Scheduled debt paydown sprint
- Blocking debt before feature work
- Quarterly cleanup initiative
- Pre-major-release cleanup

## Prerequisites

- Time allocated for debt work
- Rough understanding of debt areas
- Stakeholder buy-in for sprint

## Command Sequence

### Phase 1: Debt Discovery

```bash
/debt
```
**Expected output**: Team switched to debt-triage-pack

### Phase 2: Start Debt Session

```bash
/start "Tech debt sprint Q[X]" --complexity=AUDIT
```
**Expected output**: Session created, debt-detective invoked

### Phase 3: Inventory

Debt Detective catalogs all debt.

**Expected output**: Comprehensive debt inventory

### Phase 4: Prioritization

Prioritizer creates priority matrix.

**Expected output**: Prioritized debt list with:
- Impact scores
- Effort estimates
- Dependencies

### Phase 5: Sprint Planning

Paydown Planner creates roadmap.

**Expected output**: Sprint plan with specific items

**Decision point**: Review plan, adjust scope if needed.

### Phase 6: Execute Remediation

Switch to hygiene for execution:
```bash
/hygiene
/task "Fix [specific debt item]"
```

Repeat for each prioritized item.

### Phase 7: Validate

```bash
/hygiene
```
Architect Enforcer validates improvements.

**Expected output**: Compliance report

### Phase 8: Wrap Up

```bash
/wrap
```
**Expected output**: Sprint summary with debt paid down

## Variations

- **Quick wins sprint**: Focus on low-effort, high-impact items
- **Blocking debt**: Focus on items blocking feature work
- **Full audit**: Comprehensive inventory without immediate fix

## Success Criteria

- [ ] Debt inventoried
- [ ] Priorities established
- [ ] Sprint scope defined
- [ ] Debt items remediated
- [ ] Improvements validated

## Team Coordination

```bash
# Full debt sprint:
/debt                          # Inventory and prioritize
/hygiene                       # Execute fixes
/debt                          # Update inventory
```

## Measurement

Track:
- Debt items before/after
- Code quality metrics
- Developer satisfaction
