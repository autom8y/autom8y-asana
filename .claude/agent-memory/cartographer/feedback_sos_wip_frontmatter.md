---
name: .sos/wip/ files require YAML frontmatter
description: All files written to .sos/wip/ must include YAML frontmatter with a type field
type: feedback
---

All files written to `.sos/wip/` (including subdirectories like `.sos/wip/release/`) must begin with YAML frontmatter:

```
---
type: <spike|spec|audit|design|triage|qa|scratch>
---
```

Use `type: scratch` for cartographer output artifacts (platform-state-map.yaml, platform-state-map.md).

**Why:** A PreToolUse:Write hook enforces this requirement and will flag missing frontmatter. The hook fired when platform-state-map.yaml was written without it (2026-03-15).

**How to apply:** Always prepend frontmatter block before the file content when writing any file under `.sos/wip/`. Apply to both the `.yaml` and `.md` artifacts.
