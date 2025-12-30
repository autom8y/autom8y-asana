---
name: cross-team
description: "Protocol for surfacing cross-team concerns and routing work to appropriate specialist teams through user coordination."
---

# Cross-Team Protocol

## When to Surface Cross-Team Concerns

When work reveals concerns that fall outside your team's domain expertise, surface them to the user. Common triggers:

- **Hygiene Team**: Codebase cleanup, linting issues, formatting drift, test coverage gaps
- **SRE Team**: Production reliability, observability gaps, incident response, infrastructure resilience
- **Security Team**: Vulnerability remediation, compliance requirements, security incident response
- **Debt Triage Team**: Technical debt prioritization, legacy system remediation, architectural decay
- **Doc Team**: Documentation-focused work beyond technical specs (user guides, runbooks, external docs)

## How to Route

**Never invoke other teams directly.** Cross-team coordination flows through the user.

When you identify a cross-team concern:
1. Complete your team's work to a stable stopping point
2. Document the cross-team concern with specific context
3. Surface to the user: *"This may benefit from involving the [Team Name] for [specific reason]. Suggest next step: [concrete action]."*

## Example Handoff

```
"The feature implementation is complete and tests pass. However, I've identified
300+ lines of duplicated error handling logic across services that should be
consolidated. This may benefit from involving the Hygiene Team for refactoring
assessment. Suggest next step: Create hygiene ticket for DRY violation review."
```

## Cross-Team Collaboration

Teams collaborate through the user, not directly. This ensures:
- Clear accountability for who owns what
- Proper context transfer between domains
- User visibility into cross-cutting concerns
- No conflicts or duplicated work
