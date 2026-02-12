---
paths:
  - "internal/agent/**"
---

When modifying files in internal/agent/:
- 3 archetypes: orchestrator (Read only, opus), specialist (8 tools, opus/sonnet), reviewer (10 tools + must_not)
- 2-tier validation: WARN (all agents), STRICT (orchestrators, reviewers)
- Agents cannot spawn other agents — CC silently strips Task tool from subagents
- additionalProperties: true in JSON schema for forward compatibility
- Orchestrators are stateless advisors: they return structured YAML directives, not execute work
- BehavioralContract.MaxTurns is NOT surfaced as CC top-level maxTurns (known gap)
