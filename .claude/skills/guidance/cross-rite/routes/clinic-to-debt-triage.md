# clinic-to-debt-triage Handoff

> The bug was a symptom. The pattern is the disease.

## When This Route Fires

The attending produces `handoff-debt-triage.md` when the investigation reveals that the root cause is not a point bug but a systemic or architectural problem that manifests across the codebase. The clinic identified the instance; debt-triage addresses the pattern.

**Trigger conditions**:
- The root cause is a design pattern repeated across multiple services or modules
- The failure reveals an architectural flaw that will produce similar failures elsewhere
- The fix for this instance is straightforward, but the class of problem requires a systematic remediation strategy
- The diagnostician finds the same anti-pattern in multiple locations during evidence collection

**Not this route** if the problem is genuinely isolated to one location — not every bug represents systemic debt. The attending makes this judgment based on what the pathologist's evidence reveals about scope.

## Inbound Artifact

The clinic produces `handoff-debt-triage.md` in `.sos/wip/ERRORS/{investigation-slug}/`. This file contains:

| Field | Required | Description |
|-------|----------|-------------|
| Pattern Analysis | Yes | How this issue manifests across the codebase beyond this instance |
| Scope of Problem | Yes | How widespread: N files, N services, estimated prevalence |
| Remediation Approach | Yes | Long-term fix strategy, not just this instance |
| Debt Classification | Optional | Type: architectural, dependency, test, design |
| Affected Components | Optional | Broader list beyond the immediate investigation |
| Effort Estimate | Optional | Rough sizing: S/M/L/XL |

## Relationship to 10x-dev Handoff

The clinic may produce both `handoff-10x-dev.md` and `handoff-debt-triage.md` for the same investigation:

- `handoff-10x-dev.md`: Fix this specific instance
- `handoff-debt-triage.md`: Address the pattern across the codebase

The user typically acts on the 10x-dev handoff first (fix the immediate production problem), then decides whether to address the systemic issue via debt-triage. These are sequential, not concurrent.

## Handoff Protocol

**Standard handoff message from attending when systemic issue identified**:
```
Investigation complete. Root cause reveals systemic pattern.

Investigation: {investigation-slug}
This instance: {specific fix described in handoff-10x-dev.md}
Systemic scope: {N locations, pattern description}

Two handoff artifacts produced:
1. Fix this instance: .sos/wip/ERRORS/{slug}/handoff-10x-dev.md
   Suggest: /10x && /task "Fix {slug}"

2. Address the pattern: .sos/wip/ERRORS/{slug}/handoff-debt-triage.md
   Suggest: /debt && /task "Remediate {pattern-name}" --complexity=AUDIT

Recommend: address instance fix first, then assess debt remediation scope.
```

## debt-triage Intake

When the user switches to debt-triage and starts a task referencing the clinic handoff:

1. Load `handoff-debt-triage.md` for scope and pattern analysis
2. Load `handoff-10x-dev.md` for context on the triggering incident (do not re-investigate)
3. Treat the clinic's pattern analysis as the starting assessment
4. Run the debt-triage collection phase to validate and expand scope
5. Produce a prioritized remediation plan

The clinic does the initial pattern recognition; debt-triage does the full inventory and prioritization.

## Common Patterns

### Pattern 1: Repeated Error Handling Anti-Pattern

```
clinic finding: missing error propagation in payment service
pathologist evidence: same pattern found in 6 other services during evidence collection
clinic handoff: N=7 services affected, classify as design debt, estimate M effort
debt-triage work: full inventory, prioritize by blast radius, plan systematic remediation
```

### Pattern 2: Dependency Version Skew

```
clinic finding: library version conflict caused the failure
clinic handoff: 12 services on different versions of the same dependency, divergence over 18 months
debt-triage work: dependency audit, upgrade plan, lock strategy
```

### Pattern 3: Architectural Missing Layer

```
clinic finding: no retry/circuit-breaker pattern in service communication
clinic handoff: absent across all 8 downstream service calls in the checkout flow
debt-triage work: assess blast radius, design standardized resilience layer, estimate XL effort
```

## Scope Calibration

| Clinic Scope Finding | debt-triage Complexity |
|---------------------|------------------------|
| 2-5 files affected | QUICK |
| 5-15 files or 2-4 services | AUDIT |
| 15+ files or 5+ services | AUDIT (with scope definition phase) |
| Architectural — no clear boundary | Escalate: spike required before triage |

## Related Routes

- [clinic-to-10x.md](clinic-to-10x.md) - Fix the triggering instance
- [clinic-to-sre.md](clinic-to-sre.md) - When investigation reveals monitoring gaps
