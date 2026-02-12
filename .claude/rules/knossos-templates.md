---
paths:
  - "knossos/templates/**"
---

When modifying files in knossos/templates/:
- sections/*.md.tpl: Go templates rendering CLAUDE.md regions via materialization
- rules/*.md: Path-scoped instructions projected to .claude/rules/ on sync
- 3 section owner types: knossos (SYNC), satellite (PRESERVE), regenerate (from source)
- Region markers: <!-- KNOSSOS:START name --> ... <!-- KNOSSOS:END name -->
- Templates must be idempotent: rendering twice produces identical output
- Rules use paths: frontmatter for CC path-scoped activation
- Changes here require `ari sync` to project into .claude/
