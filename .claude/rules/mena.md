---
paths:
  - "mena/**"
---

When modifying files in mena/:
- .dro.md = dromena (commands): TRANSIENT, user-invoked, side effects OK
- .lego.md = legomena (skills): PERSISTENT, model-invoked, reference only
- These are fundamentally different — context lifecycle, not just routing
- Frontmatter schema: name and description required; scope controls pipeline routing
- Source paths here project to .claude/commands/ (dromena) and .claude/skills/ (legomena)
- INDEX files are the entry point; companion files enable progressive disclosure
- Skill descriptions must be precise with "Use when:" and "Triggers:" for CC autonomous loading
