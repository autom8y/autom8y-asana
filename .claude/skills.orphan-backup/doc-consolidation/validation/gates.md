# Quality Gates Between Phases

> **Purpose**: Mandatory checkpoints between consolidation phases with specific pass/fail criteria. No phase proceeds until its gate passes.

## Design Principles

1. **No Phase Skipping**: Gates enforce sequential progression
2. **Explicit Criteria**: Every gate has measurable pass/fail conditions
3. **Blocking vs. Warning**: Distinguish what blocks progress vs. what needs attention
4. **Traceability**: Gate passage is logged with timestamp and approver

---

## Gate Overview

```
Phase 0        Phase 1        Phase 2        Phase 3        Phase 4
Discovery  --> Extraction --> Synthesis  --> Review     --> Archive
           |              |              |              |              |
    [Manifest Gate] [Extraction Gate] [Synthesis Gate] [Review Gate] [Archive Gate]
                                                                            |
                                                                     [Validation Gate]
                                                                            |
                                                                        COMPLETE
```

---

## Manifest Gate (Phase 0 --> Phase 1)

**Purpose**: Ensure discovery is complete and extraction can proceed with confidence.

### Required Checks

| ID | Check | Severity | Automated |
|----|-------|----------|-----------|
| MG-1 | All source files categorized into topics | Blocking | Yes |
| MG-2 | No file appears in multiple topics as primary | Blocking | Yes |
| MG-3 | No orphan files (files without topic assignment) | Blocking | Yes |
| MG-4 | Token estimates provided for all files | Blocking | Yes |
| MG-5 | Primary source identified for each topic | Blocking | Yes |
| MG-6 | Ambiguous mappings flagged for resolution | Warning | Yes |
| MG-7 | File hashes computed and recorded | Blocking | Yes |
| MG-8 | Topic dependencies form acyclic graph | Blocking | Yes |

### Validation Logic

```yaml
manifest_gate:
  precondition: MANIFEST.yaml exists

  blocking_checks:
    all_files_categorized:
      rule: "every file in scope has topics[] with at least one entry"
      failure: "Files without topic assignment: {list}"

    no_duplicate_primary:
      rule: "no file has authority: primary for more than one topic"
      failure: "File {path} is primary for multiple topics: {list}"

    no_orphan_files:
      rule: "files not in exclusions[] must have topic assignment"
      failure: "Orphan files found: {list}"

    token_estimates_present:
      rule: "every file has token_estimate > 0"
      failure: "Missing token estimates for: {list}"

    primary_source_per_topic:
      rule: "every topic has exactly one primary_source"
      failure: "Topics without primary source: {list}"

    hashes_computed:
      rule: "every file has 64-character hex hash"
      failure: "Invalid or missing hashes for: {list}"

    no_dependency_cycles:
      rule: "topic dependencies form directed acyclic graph"
      failure: "Dependency cycle detected: {cycle}"

  warning_checks:
    ambiguous_flagged:
      rule: "files with unclear topic mapping are in ambiguous[]"
      action: "Review ambiguous mappings before extraction"

  on_pass:
    - log: "Manifest Gate passed at {timestamp}"
    - update checkpoint status to "extraction_ready"

  on_fail:
    - log: "Manifest Gate failed: {failure_reasons}"
    - block progression to Phase 1
```

### Gate Checklist

```markdown
## Manifest Gate Checklist

- [ ] MG-1: All source files categorized
- [ ] MG-2: No file appears in multiple topics as primary
- [ ] MG-3: No orphan files
- [ ] MG-4: Token estimates provided
- [ ] MG-5: Primary source identified per topic
- [ ] MG-6: Ambiguous mappings reviewed (warning)
- [ ] MG-7: File hashes computed
- [ ] MG-8: No dependency cycles

**Gate Status**: PASS / FAIL
**Passed at**: {timestamp}
**Approved by**: {agent}
```

---

## Extraction Gate (Phase 1 --> Phase 2)

**Purpose**: Ensure extraction is complete and synthesis has sufficient structured input.

### Required Checks

| ID | Check | Severity | Automated |
|----|-------|----------|-----------|
| EG-1 | All source content accounted for in extraction | Blocking | Partial |
| EG-2 | Conflicts explicitly identified and categorized | Blocking | Yes |
| EG-3 | Authoritative sources marked per section | Blocking | Yes |
| EG-4 | Key concepts extracted with definitions | Blocking | Yes |
| EG-5 | Blocking conflicts resolved or escalated | Blocking | Yes |
| EG-6 | Source hashes match (no stale sources) | Blocking | Yes |
| EG-7 | Extraction token count < 2000 (target) | Warning | Yes |
| EG-8 | Synthesis notes provided | Warning | Yes |

### Validation Logic

```yaml
extraction_gate:
  precondition: extraction-{topic}.yaml exists for each topic

  blocking_checks:
    content_accounted:
      rule: "each source file section appears in canonical_sections or gaps"
      failure: "Unaccounted sections in {source}: {list}"
      note: "Every key_concept from extraction must be traceable to source"

    conflicts_identified:
      rule: "conflicts[] array exists (may be empty)"
      failure: "Missing conflicts array in extraction-{topic}.yaml"

    authority_marked:
      rule: "every canonical_section has authority_source"
      failure: "Sections without authority: {list}"

    key_concepts_extracted:
      rule: "shared_concepts[] has entries OR synthesis_notes explains why none"
      failure: "No shared concepts and no explanation"

    blocking_conflicts_resolved:
      rule: "no conflicts with severity: blocking and status: unresolved"
      failure: "Unresolved blocking conflicts: {list}"

    sources_fresh:
      rule: "all sources[].hash match current file content"
      failure: "Stale sources detected: {list}"

  warning_checks:
    token_efficiency:
      rule: "extraction_token_count < 2000"
      action: "Consider further summarization if > 3000"

    synthesis_guidance:
      rule: "synthesis_notes object is populated"
      action: "Add synthesis notes to guide synthesis agent"

  on_pass:
    - log: "Extraction Gate passed at {timestamp}"
    - update checkpoint status to "synthesis_ready"

  on_fail:
    - log: "Extraction Gate failed: {failure_reasons}"
    - block progression to Phase 2
```

### Gate Checklist

```markdown
## Extraction Gate Checklist

- [ ] EG-1: All source content accounted for
- [ ] EG-2: Conflicts explicitly identified
- [ ] EG-3: Authoritative sources marked
- [ ] EG-4: Key concepts extracted
- [ ] EG-5: Blocking conflicts resolved
- [ ] EG-6: Source hashes current
- [ ] EG-7: Token count efficient (warning)
- [ ] EG-8: Synthesis notes provided (warning)

**Gate Status**: PASS / FAIL
**Passed at**: {timestamp}
**Approved by**: {agent}
```

---

## Synthesis Gate (Phase 2 --> Phase 3)

**Purpose**: Ensure consolidated document is complete, accurate, and ready for review.

### Required Checks

| ID | Check | Severity | Automated |
|----|-------|----------|-----------|
| SG-1 | Every key concept from extraction preserved | Blocking | Partial |
| SG-2 | Conflicts resolved in content (not dropped) | Blocking | Partial |
| SG-3 | Consolidated doc smaller than sources | Blocking | Yes |
| SG-4 | Cross-references use consolidated paths | Blocking | Yes |
| SG-5 | Document structure follows extraction outline | Warning | No |
| SG-6 | Code examples included and attributed | Warning | Partial |
| SG-7 | Revision history initialized | Warning | Yes |
| SG-8 | Self-review completed by synthesis agent | Warning | No |

### Validation Logic

```yaml
synthesis_gate:
  precondition: consolidated document draft exists

  blocking_checks:
    key_concepts_preserved:
      rule: "every shared_concepts[].concept from extraction appears in doc"
      failure: "Missing concepts: {list}"
      note: "This is the critical information preservation check"

    conflicts_resolved_in_content:
      rule: "each extraction conflict resolution is reflected in document"
      verification: "manual spot-check of 3 resolved conflicts"
      failure: "Conflict resolution not applied: {conflict_id}"

    token_reduction:
      rule: "consolidated_tokens < sum(source_tokens)"
      failure: "Consolidation increased token count from {before} to {after}"

    paths_updated:
      rule: "no links reference pre-consolidation file paths"
      failure: "Stale path references: {list}"

  warning_checks:
    structure_follows_extraction:
      rule: "section headings align with canonical_sections"
      action: "Review structure divergence"

    code_examples_present:
      rule: "extraction code_examples appear in document"
      action: "Ensure examples included or note why excluded"

    revision_history:
      rule: "document has revision history section"
      action: "Initialize revision history"

    self_review:
      rule: "synthesis agent performed self-review pass"
      action: "Document self-review findings"

  on_pass:
    - log: "Synthesis Gate passed at {timestamp}"
    - update checkpoint status to "review_ready"

  on_fail:
    - log: "Synthesis Gate failed: {failure_reasons}"
    - block progression to Phase 3
```

### Key Concept Verification Script

```bash
#!/bin/bash
# Verify key concepts from extraction appear in consolidated doc

EXTRACTION=$1
CONSOLIDATED=$2

# Extract concepts from extraction file
concepts=$(yq '.shared_concepts[].concept' "$EXTRACTION" 2>/dev/null)

missing=0
for concept in $concepts; do
  if ! grep -qi "$concept" "$CONSOLIDATED"; then
    echo "MISSING: $concept"
    ((missing++))
  fi
done

if [ $missing -eq 0 ]; then
  echo "PASS: All concepts found"
  exit 0
else
  echo "FAIL: $missing concepts missing"
  exit 1
fi
```

### Gate Checklist

```markdown
## Synthesis Gate Checklist

- [ ] SG-1: Every key concept preserved
- [ ] SG-2: Conflicts resolved in content
- [ ] SG-3: Consolidated doc smaller than sources
- [ ] SG-4: Cross-references use new paths
- [ ] SG-5: Structure follows extraction (warning)
- [ ] SG-6: Code examples included (warning)
- [ ] SG-7: Revision history initialized (warning)
- [ ] SG-8: Self-review completed (warning)

**Gate Status**: PASS / FAIL
**Passed at**: {timestamp}
**Approved by**: {agent}
```

---

## Review Gate (Phase 3 --> Phase 4)

**Purpose**: Ensure document has been reviewed and approved for publication.

### Required Checks

| ID | Check | Severity | Automated |
|----|-------|----------|-----------|
| RG-1 | Review requested from appropriate stakeholder | Blocking | No |
| RG-2 | Feedback addressed or documented | Blocking | No |
| RG-3 | Technical accuracy verified | Blocking | No |
| RG-4 | Approval recorded in checkpoint | Blocking | Yes |
| RG-5 | Final version marked in document | Warning | Yes |

### Validation Logic

```yaml
review_gate:
  precondition: document submitted for review

  blocking_checks:
    review_requested:
      rule: "review assigned to appropriate stakeholder"
      failure: "No reviewer assigned"

    feedback_addressed:
      rule: "all feedback items have response"
      failure: "Unaddressed feedback: {list}"

    accuracy_verified:
      rule: "technical accuracy confirmed by reviewer"
      failure: "Technical review not completed"

    approval_recorded:
      rule: "checkpoint shows review_approved with approver and timestamp"
      failure: "Approval not recorded in checkpoint"

  warning_checks:
    final_marker:
      rule: "document header shows 'Status: Final'"
      action: "Update document status"

  on_pass:
    - log: "Review Gate passed at {timestamp}"
    - update checkpoint status to "archive_ready"

  on_fail:
    - log: "Review Gate failed: {failure_reasons}"
    - block progression to Phase 4
```

### Gate Checklist

```markdown
## Review Gate Checklist

- [ ] RG-1: Review requested from stakeholder
- [ ] RG-2: All feedback addressed
- [ ] RG-3: Technical accuracy verified
- [ ] RG-4: Approval recorded in checkpoint
- [ ] RG-5: Final version marked (warning)

**Reviewer**: {name}
**Review Date**: {date}
**Approval**: APPROVED / CHANGES REQUESTED

**Gate Status**: PASS / FAIL
**Passed at**: {timestamp}
**Approved by**: {agent}
```

---

## Archive Gate (Phase 4 --> Validation)

**Purpose**: Ensure archiving can proceed safely without breaking references.

### Required Checks

| ID | Check | Severity | Automated |
|----|-------|----------|-----------|
| AG-1 | INDEX.md complete with all mappings | Blocking | Yes |
| AG-2 | All originals staged for archive | Blocking | Yes |
| AG-3 | Navigation updated to new paths | Blocking | Partial |
| AG-4 | No broken links in repository | Blocking | Yes |
| AG-5 | Archive directory structure prepared | Blocking | Yes |
| AG-6 | Rollback plan documented | Warning | No |

### Validation Logic

```yaml
archive_gate:
  precondition: archiving actions prepared but not executed

  blocking_checks:
    index_complete:
      rule: "INDEX.md has mapping for every original file"
      failure: "Unmapped files: {list}"

    originals_staged:
      rule: "all source files identified for move to .archive/"
      failure: "Unstaged files: {list}"

    navigation_updated:
      rule: "CLAUDE.md and skill indexes reference consolidated paths"
      failure: "Navigation references old paths: {list}"

    no_broken_links:
      rule: "link check finds 0 broken internal links"
      failure: "Broken links: {list}"

    archive_prepared:
      rule: ".archive/ directory exists with dated subdirectory"
      failure: "Archive directory not prepared"

  warning_checks:
    rollback_documented:
      rule: "rollback procedure documented in consolidation manifest"
      action: "Document how to restore if issues found"

  on_pass:
    - log: "Archive Gate passed at {timestamp}"
    - execute archive operations
    - proceed to Validation Gate

  on_fail:
    - log: "Archive Gate failed: {failure_reasons}"
    - do not execute archive operations
```

### Gate Checklist

```markdown
## Archive Gate Checklist

- [ ] AG-1: INDEX.md complete
- [ ] AG-2: All originals in .archive/
- [ ] AG-3: Navigation updated
- [ ] AG-4: No broken links
- [ ] AG-5: Archive directory prepared
- [ ] AG-6: Rollback plan documented (warning)

**Gate Status**: PASS / FAIL
**Passed at**: {timestamp}
**Approved by**: {agent}
```

---

## Validation Gate (Phase 4 Complete)

**Purpose**: Final verification that consolidation achieved its goals without information loss.

### Required Checks

| ID | Check | Severity | Automated |
|----|-------|----------|-----------|
| VG-1 | Spot-check 3 random sections for info loss | Blocking | No |
| VG-2 | All skill references updated | Blocking | Partial |
| VG-3 | CLAUDE.md navigation correct | Blocking | Yes |
| VG-4 | Token reduction achieved | Blocking | Yes |
| VG-5 | Staleness detection functional | Warning | Yes |
| VG-6 | Consolidation metrics logged | Warning | Yes |

### Validation Logic

```yaml
validation_gate:
  precondition: archive operations completed

  blocking_checks:
    spot_check_info_loss:
      rule: "3 randomly selected sections verified for completeness"
      method: |
        1. Select 3 random canonical_sections from extraction
        2. Locate corresponding content in consolidated doc
        3. Verify key_points are present and accurate
        4. Document verification results
      failure: "Information loss detected in section: {section_id}"

    skill_references_updated:
      rule: "all .claude/skills/ references point to current locations"
      failure: "Stale skill references: {list}"

    claude_md_correct:
      rule: "CLAUDE.md skill table and links resolve correctly"
      failure: "CLAUDE.md navigation errors: {list}"

    token_reduction:
      rule: "post-consolidation tokens < pre-consolidation tokens"
      failure: "No token reduction achieved"

  warning_checks:
    staleness_detection:
      rule: "modifying archived file updates hash mismatch"
      action: "Verify staleness detection works"

    metrics_logged:
      rule: "consolidation manifest metrics section populated"
      action: "Record before/after metrics"

  on_pass:
    - log: "Validation Gate passed at {timestamp}"
    - mark consolidation COMPLETE
    - update consolidation manifest status

  on_fail:
    - log: "Validation Gate failed: {failure_reasons}"
    - escalate for remediation
```

### Spot-Check Verification Template

```markdown
## Spot-Check Verification

**Topic**: {topic_id}
**Date**: {YYYY-MM-DD}
**Verifier**: {agent_or_person}

### Section 1: {section_id}

**From Extraction**:
- Key point 1: {point}
- Key point 2: {point}
- Key point 3: {point}

**In Consolidated Doc**:
- [ ] Key point 1 present at: {location}
- [ ] Key point 2 present at: {location}
- [ ] Key point 3 present at: {location}

**Verdict**: PASS / FAIL

### Section 2: {section_id}
{same structure}

### Section 3: {section_id}
{same structure}

### Overall Spot-Check Result
- Sections Checked: 3
- Sections Passed: {count}
- Information Loss Detected: YES / NO

**Approved for Completion**: _______________
```

### Gate Checklist

```markdown
## Validation Gate Checklist

- [ ] VG-1: Spot-check 3 sections (no info loss)
- [ ] VG-2: All skill references updated
- [ ] VG-3: CLAUDE.md navigation correct
- [ ] VG-4: Token reduction achieved
- [ ] VG-5: Staleness detection works (warning)
- [ ] VG-6: Metrics logged (warning)

**Gate Status**: PASS / FAIL
**Passed at**: {timestamp}
**Approved by**: {agent}

## Consolidation Complete

**Final Status**: COMPLETE / FAILED
**Total Duration**: {start_date} to {end_date}
**Token Reduction**: {before} -> {after} ({percentage}% reduction)
```

---

## Gate Failure Recovery

| Gate | Common Failures | Recovery Action |
|------|-----------------|-----------------|
| Manifest | Orphan files | Add to topic or exclusions |
| Manifest | Dependency cycle | Restructure topic dependencies |
| Extraction | Stale sources | Recompute hashes, re-extract |
| Extraction | Blocking conflict | Escalate to human decision |
| Synthesis | Missing concepts | Update synthesis from extraction |
| Synthesis | Token increase | Further summarization needed |
| Review | Changes requested | Address feedback, re-submit |
| Archive | Broken links | Update references before archive |
| Validation | Info loss detected | Revert archive, fix synthesis |

---

## Gate Logging Format

All gate passages should be logged in the consolidation manifest:

```yaml
gate_log:
  - gate: manifest
    status: passed
    timestamp: "2024-12-25T10:00:00Z"
    agent: "discovery-agent-v1"
    notes: "All 12 files categorized into 4 topics"

  - gate: extraction
    status: passed
    timestamp: "2024-12-25T11:30:00Z"
    agent: "extractor-agent-v1"
    notes: "2 conflicts resolved; 1 deferred (minor)"

  - gate: synthesis
    status: failed
    timestamp: "2024-12-25T14:00:00Z"
    agent: "synthesis-agent-v1"
    failure_reason: "Missing 2 key concepts"
    remediation: "Updated synthesis to include tier-precedence and array-strategies"

  - gate: synthesis
    status: passed
    timestamp: "2024-12-25T15:00:00Z"
    agent: "synthesis-agent-v1"
    notes: "All concepts verified present"
```

---

*Part of the [Documentation Consolidation Workflow](../SKILL.md)*
