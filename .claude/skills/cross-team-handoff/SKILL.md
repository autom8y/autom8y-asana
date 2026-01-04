---
name: cross-team-handoff
description: "HANDOFF artifact schema for cross-team work transfer. Use when: work crosses team boundaries, specialist review required, formal handoff needed. Triggers: cross-team, handoff artifact, team transfer, work handoff."
---

# Cross-Team Handoff Skill

> Defines the HANDOFF artifact schema for transferring work between team packs.

## Quick Reference

**When to Use**: Work crosses team boundaries and requires formal handoff
**Artifact Pattern**: `HANDOFF-{source}-to-{target}-{date}.md`
**Handoff Types**: execution, validation, assessment, implementation, strategic_input, strategic_evaluation

## Decision Tree

```
Is work crossing team boundaries?
+-- No -> Use /handoff (within-team) or continue directly
+-- Yes -> Continue below

Is formal work transfer needed?
+-- No -> Use /consult or surface to user informally
+-- Yes -> Create HANDOFF artifact

What type of work?
+-- Ready for execution -> type: execution
+-- Needs validation (dev -> ops) -> type: validation
+-- Needs specialist review -> type: assessment
+-- Research -> production build -> type: implementation
+-- Data -> strategy -> type: strategic_input
+-- R&D -> go/no-go -> type: strategic_evaluation
```

## Handoff Types

| Type | Flow | Required Per Item |
|------|------|-------------------|
| `execution` | Planning -> Execution | `acceptance_criteria` |
| `validation` | Dev -> Ops | `validation_scope` |
| `assessment` | Dev -> Specialist | `assessment_questions` |
| `implementation` | Research -> Dev | `design_references` |
| `strategic_input` | Research -> Strategy | `data_sources`, `confidence` |
| `strategic_evaluation` | R&D -> Strategy | `evaluation_criteria` |

## Progressive Disclosure

- [schema.md](schema.md) - Full schema specification
- [validation.sh](validation.sh) - Validation functions
- [examples/](examples/) - Example handoffs by type
