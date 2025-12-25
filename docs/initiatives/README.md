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

## Relationship to PRDs and TDDs

Each PROMPT-0 initiative typically references one or more PRD/TDD pairs:
- **PROMPT-0** provides orchestrator context and agent coordination
- **PRD** defines what to build and why (product requirements)
- **TDD** defines how to build it (technical design)

The orchestrator uses PROMPT-0 files to coordinate multi-agent work, while PRDs and TDDs provide the actual specifications.

## Initiative Lifecycle

```
Created → Active → Validation → Archived
```

1. **Created**: Initiative kicked off, PROMPT file created
2. **Active**: Work in progress, referenced by agents
3. **Validation**: Work complete, undergoing validation (VP report)
4. **Archived**: Validated PASS/APPROVED, moved to `.archive/initiatives/YYYY-QN/`

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

## Creating a New Initiative

To create a new PROMPT-0 or PROMPT-MINUS-1 file, see:
- [.claude/skills/initiative-scoping/session-0-protocol.md](../../.claude/skills/initiative-scoping/session-0-protocol.md) - Session 0 template
- [.claude/skills/initiative-scoping/session-minus-1-protocol.md](../../.claude/skills/initiative-scoping/session-minus-1-protocol.md) - Meta-initiative template

These provide structured templates for initiative kickoff.

## Finding Archived Initiatives

Check [`.archive/initiatives/`](../.archive/initiatives/) for historical initiative files.

## See Also

- [PRD README](../requirements/README.md) - Formal requirements documents
- [INDEX.md](../INDEX.md) - Active initiatives registry
