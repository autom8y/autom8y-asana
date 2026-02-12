---
paths:
  - "rites/**"
---

When modifying files in rites/:
- rite.yaml is the manifest: name, description, agents, dependencies, mena entries
- orchestrator.yaml defines specialist routing, handoff criteria, and workflow position
- workflow.yaml defines phases, entry point, complexity levels, and back-routes
- agents/ contains specialist prompts (frontmatter + behavioral instructions)
- mena/ contains rite-specific dromena (.dro.md) and legomena (.lego.md)
- Every agent in manifest must appear in workflow phases or be documented as out-of-workflow
- shared/ directory provides cross-rite overlay resources inherited by all rites
- Never edit .claude/ directly from rite definitions — run `ari sync` to project
