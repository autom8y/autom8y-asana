# clinic-to-10x Handoff

> Root cause identified. Time to implement the fix.

## When This Route Fires

The attending produces `handoff-10x-dev.md` when the investigation concludes that the root cause is fixable via code or configuration changes. This is the most common clinic outbound route.

**Trigger conditions**:
- Root cause is a bug in application code
- Root cause is a misconfiguration
- Fix requires new code, test coverage, or dependency updates

**Not this route** if the root cause is systemic (use clinic-to-debt-triage) or the failure was caused by missing monitoring (use clinic-to-sre). A single investigation may produce multiple handoff artifacts.

## Inbound Artifact

The clinic produces `handoff-10x-dev.md` in `.sos/wip/ERRORS/{investigation-slug}/`. This file contains:

| Field | Required | Description |
|-------|----------|-------------|
| Root Cause Summary | Yes | From diagnosis.md — not re-derived in the handoff |
| Affected Files | Yes | Specific file paths with what to change |
| Fix Approach | Yes | Recommended implementation strategy with rationale |
| Acceptance Criteria | Yes | Specific, testable conditions for verifying the fix |
| Fix Ordering | Optional | For compound failures: which bug to fix first and why |
| Risk Assessment | Optional | What could go wrong with the fix |
| Related Tests | Optional | Existing tests to update or new tests to write |

## Handoff Protocol

The clinic never auto-invokes 10x-dev. The attending surfaces the recommendation; the user decides whether to act.

**Standard handoff message from attending**:
```
Root cause identified and treatment plan produced.

Investigation: {investigation-slug}
Root cause: {brief description}
Confidence: {high|medium}

Fix specification is ready for implementation. Suggest next step:
  /10x && /task "Fix {investigation-slug}" --complexity={SCRIPT|MODULE|SERVICE}

Handoff artifact: .sos/wip/ERRORS/{slug}/handoff-10x-dev.md
```

## 10x-dev Intake

When the user switches to 10x-dev and starts a task referencing the clinic investigation:

1. Load `handoff-10x-dev.md` — do not re-read the full investigation
2. Trust the root cause summary — the diagnostician did the analysis
3. Use the acceptance criteria as the task's definition of done
4. Reference the affected files list as the starting point
5. Do not expand scope without escalating to the user

## Complexity Calibration

| Investigation Result | Suggested 10x-dev Complexity |
|---------------------|-------------------------------|
| Single file, obvious fix | SCRIPT |
| Multi-file change, clear approach | MODULE |
| Cross-service change, coordination required | SERVICE |
| Architectural refactor implied | Escalate — use debt-triage route first |

## Common Patterns

### Pattern 1: Simple Bug Fix

```
clinic diagnosis: NullPointerException in checkout service
clinic handoff: single file, add null check before line 47
10x-dev complexity: SCRIPT
```

### Pattern 2: Compound Failure

```
clinic diagnosis: two root causes (race condition + missing retry)
clinic handoff: fix_ordering specified (fix race condition first)
10x-dev complexity: MODULE
attending note: implement fixes sequentially per handoff ordering
```

### Pattern 3: Configuration Fix

```
clinic diagnosis: circuit breaker threshold too aggressive
clinic handoff: config change in services/checkout/config.yaml
10x-dev complexity: SCRIPT
note: acceptance criteria requires load test validation
```

## Related Routes

- [clinic-to-sre.md](clinic-to-sre.md) - When investigation reveals monitoring gaps
- [clinic-to-debt-triage.md](clinic-to-debt-triage.md) - When root cause is systemic
