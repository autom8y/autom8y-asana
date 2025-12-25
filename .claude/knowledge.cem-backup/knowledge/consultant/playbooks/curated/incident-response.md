# Playbook: Incident Response

> Emergency response for production issues

## When to Use

- Production is down or degraded
- Critical user impact
- Security incident
- Data integrity issue

## Prerequisites

- Access to production systems
- Monitoring/alerting available
- Communication channels ready

## Command Sequence

### Phase 1: Incident Mode

```bash
/sre
```
**Expected output**: Team switched to sre-pack

### Phase 2: Declare Incident

```bash
/start "Incident: [brief description]" --complexity=TASK
```
**Expected output**: Incident Commander takes lead

### Phase 3: Triage

**Priority assessment**:
- P0: Complete outage, all users affected
- P1: Major degradation, many users affected
- P2: Partial impact, workaround exists
- P3: Minor issue, limited impact

**Decision point**: Escalate if P0/P1.

### Phase 4: Respond

Incident Commander leads:
1. Identify impact scope
2. Communicate status
3. Assign investigation
4. Coordinate response

**Expected output**: Incident timeline being documented

### Phase 5: Mitigate

Implement immediate fix:
- Rollback if needed
- Scale resources
- Disable problematic feature
- Apply hotfix

```bash
# If code fix needed:
/hotfix
```

### Phase 6: Resolve

Confirm service restored.

**Expected output**: Service stable, incident resolved

### Phase 7: Postmortem

Postmortem Author documents:
```bash
# Continue with sre-pack
```

**Expected output**: Postmortem document with:
- Timeline
- Root cause
- Impact
- Action items

### Phase 8: Follow-up

Reliability Engineer implements:
- Permanent fixes
- Monitoring improvements
- Alert tuning

```bash
/wrap
```

## Variations

- **Security incident**: Coordinate with `/security`
- **Data incident**: Focus on data integrity/recovery
- **Partial outage**: May not need full incident process

## Success Criteria

- [ ] Impact assessed
- [ ] Communication sent
- [ ] Service restored
- [ ] Postmortem completed
- [ ] Action items created

## Communication Template

```
INCIDENT: [Title]
STATUS: [Investigating/Identified/Monitoring/Resolved]
IMPACT: [Description]
NEXT UPDATE: [Time]
```

## Quick Reference

| Phase | Focus |
|-------|-------|
| Triage | Assess severity |
| Respond | Coordinate team |
| Mitigate | Stop the bleeding |
| Resolve | Confirm stable |
| Postmortem | Learn from it |
