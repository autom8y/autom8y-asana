# clinic-to-sre Handoff

> The investigation revealed what was invisible. Now make it visible.

## When This Route Fires

The attending produces `handoff-sre.md` when the investigation reveals that monitoring or observability gaps caused or prolonged the incident. This route fires independently of whether a code fix is needed — a bug fix and an observability improvement often come out of the same investigation.

**Trigger conditions**:
- The failure was not detected promptly because alerts were missing or misconfigured
- Diagnosis required manual log archaeology that automated dashboards should have caught
- Evidence collection was difficult because key metrics were not instrumented
- The incident response was prolonged because responders lacked visibility

**Not this route** if SRE work is infrastructure deployment for a code fix — that goes through the standard 10x-to-sre route after 10x-dev implements the fix.

## Inbound Artifact

The clinic produces `handoff-sre.md` in `.sos/wip/ERRORS/{investigation-slug}/`. This file contains:

| Field | Required | Description |
|-------|----------|-------------|
| Signals Missing | Yes | What monitoring or observability was absent during this incident |
| Recommended Alerts | Yes | Specific alerts that would have caught this failure earlier |
| Recommended Dashboards | Yes | Dashboards that would have aided debugging |
| SLO Impact | Optional | How this incident affected service level objectives |
| Runbook Recommendation | Optional | Incident response procedure for this failure class |

## Inbound Context: SRE Escalation

The clinic also accepts inbound escalations from SRE incident-commander. When SRE escalates to clinic:

- SRE provides: incident ID, timeline, affected services, symptoms observed, initial findings, severity assessment, responders, optional evidence URLs
- Clinic triage-nurse treats this as a head start, not gospel
- After investigation, clinic may produce a sre handoff that loops back to SRE with better-specified improvements

This creates a bidirectional relationship: SRE can escalate to clinic for root cause, and clinic can recommend observability improvements back to SRE.

## Handoff Protocol

**Standard handoff message from attending when monitoring gaps found**:
```
Investigation complete. Monitoring gaps identified that delayed detection.

Investigation: {investigation-slug}
Time to detect: {duration from symptom to alert}
Signals absent: {list of missing signals}

Observability improvements specified. Suggest next step:
  /sre && /task "Improve monitoring for {failure-class}" --complexity={TASK|PROJECT}

Handoff artifact: .sos/wip/ERRORS/{slug}/handoff-sre.md
```

## SRE Intake

When the user switches to sre and starts a task referencing the clinic handoff:

1. Load `handoff-sre.md` — specific signal gaps and alert recommendations are pre-specified
2. Implement recommended alerts first (highest ROI)
3. Build recommended dashboards second
4. Validate each alert would have fired during the incident window (backtest if possible)
5. Document new runbook procedure if recommended

## Alert Specification Quality Gate

The clinic's recommended alerts should include:
- Alert name
- Specific trigger condition (not vague — "error rate above threshold" is insufficient; "checkout service HTTP 5xx rate exceeds 1% over 5m rolling window" is correct)
- Rationale: when during this specific incident would this alert have fired

The attending is responsible for this specificity. If the handoff contains vague alert specifications, the attending has not met its exit criteria.

## Common Patterns

### Pattern 1: Missing Error Rate Alert

```
clinic finding: 500 errors spiked for 23 minutes before anyone noticed
clinic recommendation: alert on checkout service 5xx rate > 0.5% for 2m
sre work: configure alert in monitoring platform, add to on-call runbook
```

### Pattern 2: Invisible Dependency Health

```
clinic finding: DuckDB connection failures logged but no circuit breaker metrics exposed
clinic recommendation: dashboard showing circuit breaker state per service
sre work: instrument circuit breaker state, build dependency health dashboard
```

### Pattern 3: Missing SLO Tracking

```
clinic finding: incident violated payment SLO but was not flagged by any SLO burn rate alert
clinic recommendation: add SLO burn rate alert at 5x rate for 1h window
sre work: define SLO budget, configure burn rate alerts
```

## Related Routes

- [clinic-to-10x.md](clinic-to-10x.md) - When investigation reveals a fixable bug
- [clinic-to-debt-triage.md](clinic-to-debt-triage.md) - When root cause is systemic
