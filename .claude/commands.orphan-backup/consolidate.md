---
description: Consolidate documentation in a category into numbered artifacts
argument-hint: <category_dir> [--dry-run]
allowed-tools: Bash, Read, Write, Task, Glob, Grep, TodoWrite
model: claude-opus-4-5
---

## Context
Auto-injected by SessionStart hook (project, team, session, git, workflow).

## Your Task

Consolidate documentation from a category directory into numbered, well-organized artifacts. $ARGUMENTS

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `category_dir` | Yes | Directory containing docs to consolidate (e.g., `.claude/skills/documentation`) |
| `--dry-run` | No | Generate MANIFEST.yaml only, do not execute consolidation |

## Workflow Phases

This command orchestrates the ecosystem-pack workflow for documentation consolidation:

| Phase | Agent | Produces | Description |
|-------|-------|----------|-------------|
| 0 | Ecosystem Analyst | MANIFEST.yaml | Analyze directory, identify files, plan consolidation structure |
| 1 | Context Architect | Extractions | Extract content chunks with metadata (parallel per file) |
| 2 | Documentation Engineer | Consolidated docs | Synthesize extractions into numbered artifacts |
| 3 | Integration Engineer | Archive | Move originals to `.archive/` with timestamp |
| 4 | Compatibility Tester | Validation | Verify consolidated docs are complete and cross-refs work |

## Behavior

1. **Validate input**:
   - Confirm `category_dir` exists and contains `.md` files
   - Check for existing MANIFEST.yaml (resume vs. fresh start)

2. **Phase 0 - Analysis** (Ecosystem Analyst):
   - Scan directory for all documentation files
   - Identify content categories and relationships
   - Generate MANIFEST.yaml with consolidation plan:
     ```yaml
     source_dir: .claude/skills/documentation
     files_to_consolidate:
       - path: templates.md
         category: templates
         estimated_chunks: 3
       - path: formats.md
         category: formats
         estimated_chunks: 2
     target_structure:
       - "01-templates.md"
       - "02-formats.md"
       - "03-examples.md"
     ```
   - If `--dry-run`: Stop here, output manifest for review

3. **Phase 1 - Extraction** (Context Architect):
   - For each file in MANIFEST.yaml (parallel):
     - Extract logical content chunks
     - Add metadata (source file, line numbers, cross-refs)
     - Produce extraction file per source

4. **Phase 2 - Synthesis** (Documentation Engineer):
   - Read all extractions
   - Merge related content into target structure
   - Produce numbered consolidated docs (01-*.md, 02-*.md, etc.)
   - Update internal cross-references

5. **Phase 3 - Archive** (Integration Engineer):
   - Create `.archive/{timestamp}/` directory
   - Move original files preserving structure
   - Update any external references

6. **Phase 4 - Validation** (Compatibility Tester):
   - Verify all original content is represented
   - Check cross-references resolve
   - Test any code examples compile/parse
   - Produce Compatibility Report

## Examples

```bash
# Consolidate documentation skill (full execution)
/consolidate .claude/skills/documentation

# Preview consolidation plan only
/consolidate docs/design --dry-run

# Consolidate knowledge base
/consolidate .claude/knowledge/consultant
```

## Phase Transitions

Each phase produces artifacts that gate the next:

```
Phase 0 ──[MANIFEST.yaml]──> Phase 1
Phase 1 ──[extractions/]───> Phase 2
Phase 2 ──[consolidated/]──> Phase 3
Phase 3 ──[.archive/]──────> Phase 4
Phase 4 ──[REPORT.md]─────> DONE
```

## Resumption

If consolidation is interrupted:
- Check for existing MANIFEST.yaml to determine last phase
- Resume from the appropriate phase
- Use existing extractions if Phase 1 completed

## Error Handling

| Error | Action |
|-------|--------|
| Directory not found | Exit with clear error message |
| No .md files | Exit, suggest alternate directory |
| Manifest conflict | Prompt: resume or restart? |
| Extraction failure | Mark file as failed, continue, report at end |
| Validation failure | List missing content, do not archive originals |

## Reference

Full workflow documentation: `.claude/skills/10x-workflow-ref/skill.md`
Agent details: `.claude/agents/orchestrator.md`
