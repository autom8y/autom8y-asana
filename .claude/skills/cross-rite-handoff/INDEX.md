---
name: cross-rite-handoff
description: "Cross-rite HANDOFF artifact schema. Use when: transferring work between rites, creating formal handoff documents, defining handoff acceptance criteria. Triggers: cross-rite, handoff artifact, rite transfer, work handoff, HANDOFF template."
---

# Cross-Rite Handoff Skill

> Defines the HANDOFF artifact schema for transferring work between rites.

## Quick Reference

**When to Use**: Work crosses rite boundaries and requires formal handoff
**Artifact Pattern**: `HANDOFF-{source}-to-{target}-{date}.md`
**Handoff Types**: execution, validation, assessment, implementation, strategic_input, strategic_evaluation

## Decision Tree

```
Is work crossing rite boundaries?
+-- No -> Use /handoff (within-rite) or continue directly
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
