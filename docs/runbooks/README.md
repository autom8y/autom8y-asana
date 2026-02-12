# Operational Runbooks

## What Are Runbooks?

Runbooks are **step-by-step troubleshooting guides** for diagnosing and resolving production issues. They are written for on-call engineers responding to incidents.

## When to Create a Runbook

Create a runbook when a feature has:
- **Complex failure modes** - Multiple symptoms or root causes
- **Ops escalation history** - Repeated incidents requiring investigation
- **Non-obvious debugging steps** - Diagnosis requires specialized knowledge or tools
- **Production impact** - Failures affect user experience or system availability

**When NOT to create a runbook:**
- Simple errors with obvious fixes (document in code comments instead)
- Rare edge cases that haven't recurred
- Issues better addressed by fixing the underlying system

## When to Use a Runbook

Use a runbook when:
- Production system is failing or degraded
- Alert fired and you need to investigate
- User reported issue and you need to diagnose
- You need quick operational guidance (not deep architecture understanding)

**For architectural understanding**, see TDDs in [`/docs/design/`](../design/).
**For feature context**, see PRDs in [`/docs/requirements/`](../requirements/).

## Runbook Structure

All runbooks follow this format:

1. **Problem Statement** - What is failing?
2. **Symptoms** - How do you know it's this problem?
3. **Investigation Steps** - How to diagnose the root cause
4. **Resolution** - How to fix it
5. **Prevention** - How to prevent recurrence

## Severity Classification

Runbooks should indicate severity level for incident triage:

- **P0 (Outage)** - Complete system failure, no workaround available
- **P1 (Degraded)** - Partial functionality loss, performance degradation affecting users
- **P2 (Advisory)** - Non-critical issues, edge cases, operational warnings

Include severity in the Problem Statement to help responders prioritize.

## Current Runbooks

| Runbook | System | Use When |
|---------|--------|----------|
| [RUNBOOK-cache-troubleshooting.md](RUNBOOK-cache-troubleshooting.md) | Cache | Cache misses, staleness issues, TTL problems, degraded performance |
| [RUNBOOK-rate-limiting.md](RUNBOOK-rate-limiting.md) | Rate Limiting | HTTP 429 errors, rate limit exceeded, slow requests, token bucket depletion, hierarchy warming backpressure |
| [RUNBOOK-savesession-debugging.md](RUNBOOK-savesession-debugging.md) | SaveSession | Save failures, dependency graph errors, partial failures, healing system issues |
| [RUNBOOK-detection-troubleshooting.md](RUNBOOK-detection-troubleshooting.md) | Detection | Entity type detection failures, tier fallback issues |

## Creating a New Runbook

1. Identify recurring production issue
2. Document symptoms and investigation steps
3. Write resolution procedures
4. Test runbook during next incident
5. Add entry to this README

**Naming Convention**: `RUNBOOK-feature-name.md` (e.g., RUNBOOK-cache-troubleshooting.md)

## Known Gaps

Additional runbooks needed for:
- **Batch operations** - Chunking failures, parallelization issues, timeout handling
- **Business model navigation** - Hierarchy traversal errors, missing parent/child relationships

These represent areas with operational complexity that would benefit from documented troubleshooting procedures.

## See Also

- [TDDs](../design/) - For architectural deep dives
- [ADRs](../decisions/) - For understanding why system works this way
