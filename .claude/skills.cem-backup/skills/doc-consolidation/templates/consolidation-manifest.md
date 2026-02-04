# Consolidation Manifest

> **Target**: {category_dir}
> **Started**: {YYYY-MM-DD}
> **Status**: {Phase N: Phase Name}
> **Owner**: {agent_or_person}

## Scope

**What's being consolidated**:
{description_of_consolidation_scope}

**Boundaries**:
- Include: {what_is_in_scope}
- Exclude: {what_is_out_of_scope}

**Success Criteria**:
- [ ] {criterion_1}
- [ ] {criterion_2}
- [ ] {criterion_3}

---

## Phase Progress

| Phase | Name | Status | Started | Completed | Agent |
|-------|------|--------|---------|-----------|-------|
| 0 | Discovery | {not_started/in_progress/complete/blocked} | {date} | {date} | {agent} |
| 1 | Extraction | {status} | {date} | {date} | {agent} |
| 2 | Synthesis | {status} | {date} | {date} | {agent} |
| 3 | Review | {status} | {date} | {date} | {agent} |
| 4 | Archive | {status} | {date} | {date} | {agent} |
| 5 | Validation | {status} | {date} | {date} | {agent} |

### Phase Checklist

**Phase 0: Discovery**
- [ ] Scan scope directory
- [ ] Generate MANIFEST.yaml
- [ ] Identify topics from file signals
- [ ] Flag ambiguous mappings
- [ ] Validate file hashes

**Phase 1: Extraction**
- [ ] Create extraction-{topic}.yaml for each topic
- [ ] Identify conflicts between sources
- [ ] Resolve blocking conflicts
- [ ] Document shared concepts
- [ ] Add synthesis notes

**Phase 2: Synthesis**
- [ ] Create consolidated doc from extraction
- [ ] Write all canonical sections
- [ ] Add cross-references
- [ ] Complete revision history
- [ ] Self-review draft

**Phase 3: Review**
- [ ] Submit for review
- [ ] Address feedback
- [ ] Obtain approval
- [ ] Mark as final

**Phase 4: Archive**
- [ ] Move original files to archive
- [ ] Update internal links
- [ ] Generate INDEX.md
- [ ] Verify no broken links

**Phase 5: Validation**
- [ ] Validate INDEX.md completeness
- [ ] Test all cross-references
- [ ] Verify archive integrity
- [ ] Confirm staleness detection works

---

## Artifacts Produced

| Phase | Artifact | Location | Status |
|-------|----------|----------|--------|
| 0 | MANIFEST.yaml | `.consolidation/MANIFEST.yaml` | {status} |
| 1 | extraction-{topic}.yaml | `.consolidation/extraction-{topic}.yaml` | {status} |
| 1 | checkpoint-{topic}.yaml | `.consolidation/checkpoint-{topic}.yaml` | {status} |
| 2 | {NNN}-{Title}.md | `{output_path}` | {status} |
| 4 | INDEX.md | `{index_path}` | {status} |

---

## Topics

| Topic ID | Name | Priority | Sources | Status | Checkpoint |
|----------|------|----------|---------|--------|------------|
| {topic_id} | {topic_name} | {critical/high/normal/low} | {count} | {phase:state} | [checkpoint]({path}) |

### Topic Dependencies

```
{topic_1}
  └── {dependent_topic} (depends on {topic_1})
{topic_2} (no dependencies)
```

---

## Blockers

| ID | Description | Blocking | Owner | ETA |
|----|-------------|----------|-------|-----|
| {blocker_id} | {description} | {what_is_blocked} | {owner} | {date} |

---

## Decisions Made

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| {date} | {decision} | {why} | {what_it_affects} |

---

## Metrics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total Files | {count} | {count} | {delta} |
| Total Tokens | {count} | {count} | {delta} |
| Topics | {count} | N/A | N/A |
| Conflicts Resolved | N/A | {count} | N/A |
| Gaps Filled | N/A | {count} | N/A |

---

## Activity Log

| Date | Agent | Action | Details |
|------|-------|--------|---------|
| {date} | {agent} | manifest_created | Initialized consolidation manifest |
| {date} | {agent} | {action} | {details} |

---

## Notes

<!-- Free-form notes, observations, or context for future agents -->

{notes}

---

*Managed by the [Documentation Consolidation Workflow](/.claude/skills/doc-consolidation/SKILL.md)*
