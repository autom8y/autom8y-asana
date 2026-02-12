---
name: cross-rite
description: "Cross-rite handoff protocols. Use when: completing 10x work that needs specialist handoff, wrapping sessions for deployment or review, transitioning between rites. Triggers: handoff, wrap, /wrap, rite transition, deployment ready."
---

# Cross-Rite Handoff Protocols

> Artifact checklists for formal work transfer between rites.

## When to Use

Use these routes when 10x development work is complete and requires handoff to specialist rites:

| Situation | Route |
|-----------|-------|
| Feature ready for production deployment | [10x-to-sre](routes/10x-to-sre.md) |
| Security-sensitive code requires review | [10x-to-security](routes/10x-to-security.md) |
| Feature documentation needed | [10x-to-doc](routes/10x-to-doc.md) |

## Decision Tree

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

## Route Summary

| Route | Target Rite | Required For | Validation |
|-------|-------------|--------------|------------|
| [10x-to-sre](routes/10x-to-sre.md) | sre | SERVICE+ complexity, any production deploy | `ari hook handoff-validate --route=sre` |
| [10x-to-security](routes/10x-to-security.md) | security | Auth, crypto, secrets, external input handling | `ari hook handoff-validate --route=security` |
| [10x-to-doc](routes/10x-to-doc.md) | docs | User-facing features, API changes, config changes | `ari hook handoff-validate --route=doc` |

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

- [routes/10x-to-sre.md](routes/10x-to-sre.md) - SRE deployment handoff checklist
- [routes/10x-to-security.md](routes/10x-to-security.md) - Security review handoff checklist
- [routes/10x-to-doc.md](routes/10x-to-doc.md) - Documentation handoff checklist
- [validation.md](validation.md) - Hook integration specification

## Related Skills

| Skill | When to Use |
|-------|-------------|
| [cross-rite-handoff](../../../rites/shared/mena/cross-rite-handoff/INDEX.lego.md) | HANDOFF artifact schema for formal transfers |
| [wrap](../../session/wrap/INDEX.dro.md) | Session completion with quality gates |
| [handoff](../../session/handoff/INDEX.dro.md) | Within-rite agent transitions |
