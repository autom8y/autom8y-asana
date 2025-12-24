# Initiative Coordination Files

## What Are PROMPT Files?

PROMPT files are orchestrator initialization instructions that coordinate multi-agent work on complex initiatives. They are NOT product requirements.

### PROMPT-0 Files
Format: `PROMPT-0-INITIATIVE-NAME.md`

Kickoff prompts for specific initiatives. Contain:
- Initiative context
- Specialist agent assignments
- Phase breakdown
- Success criteria

Example: `PROMPT-0-CACHE-INTEGRATION.md`

### PROMPT-MINUS-1 Files
Format: `PROMPT-MINUS-1-META-NAME.md`

Meta-initiative planning prompts that span multiple related initiatives.

Example: `PROMPT-MINUS-1-CACHE-PERFORMANCE-META.md`

## How PROMPT Files Differ from PRDs

| PROMPT-0 | PRD |
|----------|-----|
| Work coordination | Requirements specification |
| For orchestrator agent | For humans and engineers |
| Temporary (archived when complete) | Permanent (preserved for history) |
| Contains agent instructions | Contains feature specifications |

**If you need feature requirements**, look in [`/docs/requirements/`](../requirements/). Each initiative has a corresponding PRD.

## Initiative Lifecycle

```
Created → Active → Complete → Archived
```

1. **Created**: Initiative kicked off, PROMPT file created
2. **Active**: Work in progress, referenced by agents
3. **Complete**: Initiative finished, validated
4. **Archived**: Moved to `.archive/initiatives/YYYY-QN/`

## Archival Policy

When an initiative status reaches "Complete" (validated with VP-* report), archive the PROMPT file:

```bash
git mv initiatives/PROMPT-0-INITIATIVE-NAME.md .archive/initiatives/2025-Q4/
```

Update [INDEX.md](../INDEX.md) to reflect archive location or remove from active section.

**Completed Initiatives** (archived 2025-Q4):
- PROMPT-0-CACHE-OPTIMIZATION-PHASE2 (VP PASS)
- PROMPT-0-CACHE-PERF-FETCH-PATH (VP PASS)
- PROMPT-0-WATERMARK-CACHE (VALIDATION PASS)
- PROMPT-0-WORKSPACE-PROJECT-REGISTRY (VP APPROVED)

## Finding Archived Initiatives

Check [`.archive/initiatives/`](../.archive/initiatives/) for historical initiative files.

## See Also

- [PRD README](../requirements/README.md) - Formal requirements documents
- [INDEX.md](../INDEX.md) - Active initiatives registry
