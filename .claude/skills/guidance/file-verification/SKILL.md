---
name: file-verification
description: "File write verification protocol with path anchoring. Use when: verifying file writes succeeded, preventing hallucinated file operations, validating artifact existence after creation. Triggers: file verification, write verification, artifact check, post-write check."
---

# File Verification Protocol

> Shared protocol for all agents with Write access. Referenced by agent prompts.

## Purpose

Prevent hallucinated file operations by mandating post-write verification. This protocol addresses the root cause of agents claiming file creation without actual file existence—a failure mode that breaks handoff chains and corrupts artifact tracking.

## The Rule

**NEVER claim you wrote a file without verification.**

Before any statement like "I have produced X" or "Artifact written to Y", you must:
1. Have called Write/Edit with the path
2. Have called Read on that same path
3. Have confirmed the file contains expected content

## Verification Sequence (Detailed)

### Step 1: Path Construction

Construct absolute paths before writing:

```
# For session artifacts
/full/path/to/.sos/sessions/session-YYYYMMDD-HHMMSS-hash/artifacts/ARTIFACT-name.md

# For code files
/full/path/to/repository/src/module/file.ext

# For configuration
/full/path/to/repository/.claude/config/file.json
```

**NEVER use**:
- Relative paths (`./file.md`, `../config.json`)
- Unexpanded variables (`$HOME/file.md` without verification)
- Assumed paths ("the usual location")

### Step 2: Immediate Verification

Call Read tool on the EXACT path used in Write:
- If Read succeeds: Verify content is non-empty and matches intent
- If Read fails: Enter failure protocol

### Step 3: Completion Report

Include in completion message:
```
**Artifact Produced**: ARTIFACT-name.md
**Path**: /absolute/path/to/file.md
**Verified**: YES (Read confirmed existence and content)
```

## Failure Protocol (Detailed)

### Verification Failure Scenarios

| Scenario | Detection | Action |
|----------|-----------|--------|
| Read returns "file not found" | Tool error message | Retry once with explicit path |
| Read returns empty content | Zero-length response | Retry write, verify again |
| Read returns wrong content | Content mismatch | Investigate path, retry |
| Retry also fails | Second failure | Report failure, halt |

### Failure Report Format

```markdown
## VERIFICATION FAILED

**Operation**: Write to /path/to/file.md
**Verification**: Read returned "file not found"
**Retry**: Attempted once, same result
**Status**: HALTED - Cannot confirm artifact exists

**Next Steps Required**:
1. Verify working directory with `pwd`
2. Verify path construction logic
3. Manual intervention may be required
```

### DO NOT

- Claim success if verification failed
- Proceed to handoff with unverified artifacts
- Assume file exists because write "felt successful"
- Skip verification "to save time"

## Handoff Attestation

Before signaling handoff readiness, produce attestation table:

```markdown
## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| Gap Analysis | /path/to/GAP-analysis.md | YES |
| Context Design | /path/to/CONTEXT-design.md | YES |

All artifacts verified. Ready for handoff.
```

**Unverified artifacts block handoff.** If any artifact shows "NO" in Verified column, handoff cannot proceed.

## Session Checkpoint Protocol

For sessions exceeding 5 minutes, emit checkpoints at natural breakpoints:

```markdown
## Checkpoint: {phase-name}

**Time Elapsed**: ~{N} minutes
**Artifacts Created**:
| Artifact | Path | Verified |
|----------|------|----------|
| ... | ... | YES/NO |

**Current Working Directory**: {pwd output}
**Next Phase**: {description}
```

Emit checkpoints:
- After completing major artifact sections
- Before switching between distinct work phases
- When 5+ minutes have elapsed since last checkpoint
- Before final completion message

## Integration with Handoff Criteria

Every agent's "Handoff Criteria" section should include:

```markdown
Ready for [next phase] when:
- [ ] [existing criteria...]
- [ ] All artifacts verified via Read tool
- [ ] Attestation table included with absolute paths
```

## Anti-Patterns

| Anti-Pattern | Why It Fails | Correct Approach |
|--------------|--------------|------------------|
| "I wrote the file" (no verification) | File may not exist | Verify with Read, report path |
| Using relative paths | Path may resolve differently | Use absolute paths always |
| Skipping verification for speed | Creates hallucinated artifacts | Always verify, no exceptions |
| Claiming partial success | Downstream depends on full artifacts | Either fully verified or failed |
| Verifying different file than written | Proves nothing | Verify EXACT path from Write |

## Progressive Disclosure

This skill is intentionally self-contained as a quick reference protocol. All verification patterns are documented inline for immediate agent access without additional file loads.

**Related Skills**:
- [cross-rite](../cross-rite/INDEX.lego.md) - Cross-rite routing protocol
- [prompting](../prompting/INDEX.lego.md) - Agent invocation patterns
