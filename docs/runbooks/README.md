# Operational Runbooks

## What Are Runbooks?

Runbooks are **step-by-step troubleshooting guides** for diagnosing and resolving production issues. They are written for on-call engineers responding to incidents.

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

## Current Runbooks

| Runbook | System | Use When |
|---------|--------|----------|
| [RUNBOOK-cache-troubleshooting.md](RUNBOOK-cache-troubleshooting.md) | Cache | Cache misses, staleness issues, TTL problems, degraded performance |
| [RUNBOOK-savesession-debugging.md](RUNBOOK-savesession-debugging.md) | SaveSession | Save failures, dependency graph errors, partial failures, healing system issues |
| [RUNBOOK-detection-troubleshooting.md](RUNBOOK-detection-troubleshooting.md) | Detection | Entity type detection failures, tier fallback issues |

## Creating a New Runbook

1. Identify recurring production issue
2. Document symptoms and investigation steps
3. Write resolution procedures
4. Test runbook during next incident
5. Add entry to this README and incident response playbook

## See Also

- [TDDs](../design/) - For architectural deep dives
- [ADRs](../decisions/) - For understanding why system works this way
