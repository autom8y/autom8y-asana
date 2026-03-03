---
name: cross-rite
description: "Cross-rite handoff protocols. Use when: completing 10x work that needs specialist handoff, wrapping sessions for deployment or review, transitioning between rites. Triggers: handoff, wrap, /wrap, rite transition, deployment ready."
---

# Cross-Rite Handoff Protocols

> Artifact checklists for formal work transfer between rites.

## When to Use

Use these routes when work in one rite is complete and requires handoff to a specialist rite:

| Situation | Route |
|-----------|-------|
| Feature ready for production deployment | [10x-to-sre](routes/10x-to-sre.md) |
| Security-sensitive code requires review | [10x-to-security](routes/10x-to-security.md) |
| Feature documentation needed | [10x-to-doc](routes/10x-to-doc.md) |
| Clinic diagnosis: fixable code bug identified | [clinic-to-10x](routes/clinic-to-10x.md) |
| Clinic diagnosis: monitoring gaps revealed | [clinic-to-sre](routes/clinic-to-sre.md) |
| Clinic diagnosis: systemic pattern identified | [clinic-to-debt-triage](routes/clinic-to-debt-triage.md) |

## Decision Tree

### From 10x-dev (feature complete)

```
Feature implementation complete?
+-- No -> Continue development, use /park if pausing
+-- Yes -> Continue below

Does it need production deployment?
+-- Yes -> 10x-to-sre route (always required for SERVICE+ complexity)
+-- No -> Continue below

Does it have security implications?
+-- Auth/authz, crypto, secrets, user data, external input?
+-- Yes -> 10x-to-security route
+-- No -> Continue below

Does it need user-facing documentation?
+-- New feature, API changes, config changes?
+-- Yes -> 10x-to-doc route
+-- No -> Proceed to /wrap
```

### From clinic (investigation complete)

```
Root cause identified?
+-- No -> Back-route (evidence gap or escalate to user)
+-- Yes -> Continue below

Is the root cause a fixable bug or misconfiguration?
+-- Yes -> clinic-to-10x route
+-- No -> Continue below

Were monitoring or observability gaps revealed?
+-- Yes -> clinic-to-sre route (may combine with clinic-to-10x)

Is the root cause a systemic pattern across the codebase?
+-- Yes -> clinic-to-debt-triage route (may combine with clinic-to-10x)
```

Note: A single clinic investigation may produce multiple outbound handoffs. Fix the instance (10x), improve visibility (sre), and address the pattern (debt-triage) are independent workstreams.

## Route Summary

| Route | Source Rite | Target Rite | Trigger |
|-------|-------------|-------------|---------|
| [10x-to-sre](routes/10x-to-sre.md) | 10x-dev | sre | SERVICE+ complexity, production deploy |
| [10x-to-security](routes/10x-to-security.md) | 10x-dev | security | Auth, crypto, secrets, external input |
| [10x-to-doc](routes/10x-to-doc.md) | 10x-dev | docs | User-facing features, API changes |
| [clinic-to-10x](routes/clinic-to-10x.md) | clinic | 10x-dev | Fixable code bug or misconfiguration |
| [clinic-to-sre](routes/clinic-to-sre.md) | clinic | sre | Monitoring or observability gaps |
| [clinic-to-debt-triage](routes/clinic-to-debt-triage.md) | clinic | debt-triage | Systemic pattern across codebase |

## Integration with /wrap

The `/wrap` command integrates with these routes:

1. During wrap, quality gates check if cross-rite handoff is required
2. If complexity >= SERVICE with production deployment, SRE handoff is flagged
3. Use `--skip-handoff` to bypass (logged, not recommended for production work)

See [validation.md](validation.md) for hook integration details.

## Cross-Rite Protocol

**Never invoke other rites directly.** Cross-rite coordination flows through the user.

When you identify a cross-rite concern:
1. Complete your rite's work to a stable stopping point
2. Document the cross-rite concern with specific context
3. Surface to the user: *"This may benefit from involving the [Rite Name] for [specific reason]. Suggest next step: [concrete action]."*

### Example Handoff

```
"The feature implementation is complete and tests pass. However, I've identified
300+ lines of duplicated error handling logic across services that should be
consolidated. This may benefit from involving the Hygiene Rite for refactoring
assessment. Suggest next step: Create hygiene ticket for DRY violation review."
```

## Progressive Disclosure

### 10x-dev outbound routes
- [routes/10x-to-sre.md](routes/10x-to-sre.md) - SRE deployment handoff checklist
- [routes/10x-to-security.md](routes/10x-to-security.md) - Security review handoff checklist
- [routes/10x-to-doc.md](routes/10x-to-doc.md) - Documentation handoff checklist

### clinic outbound routes
- [routes/clinic-to-10x.md](routes/clinic-to-10x.md) - Fix implementation handoff
- [routes/clinic-to-sre.md](routes/clinic-to-sre.md) - Monitoring gap handoff
- [routes/clinic-to-debt-triage.md](routes/clinic-to-debt-triage.md) - Systemic issue handoff

- [validation.md](validation.md) - Hook integration specification

## Related Skills

| Skill | When to Use |
|-------|-------------|
| `cross-rite-handoff` skill | HANDOFF artifact schema for formal transfers |
| `/wrap` command | Session completion with quality gates |
| `/handoff` command | Within-rite agent transitions |
