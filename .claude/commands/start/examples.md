---
user-invocable: false
---

# /start Examples

> Usage scenarios for initializing work sessions.

## Example 1: Simple Patch

```bash
/start "Add retry logic to API client"
```

Interactive prompts:
```
Initiative: Add retry logic to API client
Complexity? [PATCH/MODULE/SYSTEM/INITIATIVE/MIGRATION]: PATCH
Rite? [current: 10x-dev]: <Enter>

✓ Session started
✓ Requirements Analyst creating PRD...
✓ PRD saved: /docs/requirements/PRD-api-retry.md

Review PRD and use /handoff engineer when ready to implement.
```

---

## Example 2: Module with Rite Switch

```bash
/start "Multi-tenant authentication" --complexity=MODULE --rite=10x-dev
```

Output:
```
Switching to rite: 10x-dev (5 agents loaded)

✓ Session started: Multi-tenant authentication
✓ Complexity: MODULE
✓ Requirements Analyst creating PRD...
✓ PRD approved: /docs/requirements/PRD-multi-tenant-auth.md
✓ Architect creating TDD...
✓ TDD draft: /docs/design/TDD-multi-tenant-auth.md
✓ ADR created: /docs/decisions/ADR-0042-jwt-token-strategy.md

Next: Review design documents and approve before implementation.
```

---

## Example 3: Initiative

```bash
/start "Migrate to microservices architecture" --complexity=INITIATIVE
```

Output:
```
⚠ INITIATIVE complexity detected - this is a multi-session initiative.

✓ Session started: Migrate to microservices architecture
✓ Requirements Analyst scoping initiative...
✓ PRD saved: /docs/requirements/PRD-microservices-migration.md
✓ Architect creating TDD and ADRs...
✓ TDD saved: /docs/design/TDD-microservices-migration.md
✓ ADRs created:
  - ADR-0043-service-decomposition-strategy.md
  - ADR-0044-api-gateway-selection.md
  - ADR-0045-data-consistency-approach.md

Next: This initiative will require multiple sessions. Consider breaking into phases.
Use /park to save state between work periods.
```
