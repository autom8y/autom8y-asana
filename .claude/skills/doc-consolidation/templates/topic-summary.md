# Topic Summary: {topic_name}

> **Topic ID**: {topic_id}
> **Generated**: {date}
> **Phase**: 1 - Extraction

## Sources Analyzed

| File | Lines | Token Est. | Key Concepts | Authority |
|------|-------|------------|--------------|-----------|
| {path} | {line_count} | {token_estimate} | {concepts} | {primary/secondary/supplementary} |

## Content Overview

### Canonical Sections Identified

| Section ID | Heading | Authority Source | Summary |
|------------|---------|------------------|---------|
| {section_id} | {heading} | {authority_source} | {content_summary} |

### Key Points per Section

**{section_heading}**:
- {key_point_1}
- {key_point_2}
- {key_point_3}

## Content Overlap

<!-- Describe what content appears in multiple sources -->

| Concept | Sources | Treatment |
|---------|---------|-----------|
| {concept_name} | {source_paths} | {how_each_treats_it} |

**Shared Concepts**:
- **{concept}**: {canonical_definition}
  - {source_1}: {treatment_1}
  - {source_2}: {treatment_2}

## Conflicts Identified

<!-- List contradictions between sources. Reference extraction-schema conflict types. -->

| ID | Type | Severity | Description | Resolution Status |
|----|------|----------|-------------|-------------------|
| {conflict_id} | {contradiction/ambiguity/overlap/gap} | {blocking/significant/minor} | {description} | {unresolved/resolved/deferred} |

### Conflict Details

**{conflict_id}**: {description}

| Source | Position | Evidence |
|--------|----------|----------|
| {source_path} | {what_source_says} | "{quote_or_reference}" |

**Resolution** (if resolved):
- **Decision**: {decision}
- **Rationale**: {rationale}
- **Authority**: {who_decided}

## Gaps Identified

<!-- What's missing across all sources? -->

| Gap ID | Description | Needed For | Suggested Source |
|--------|-------------|------------|------------------|
| {gap_id} | {what_is_missing} | {why_it_matters} | {where_to_look} |

## Consolidation Recommendation

<!-- Should these merge? Split? Keep separate? -->

**Recommendation**: {MERGE / SPLIT / KEEP_SEPARATE}

**Rationale**:
{explanation_of_recommendation}

**Suggested Structure** (if merging):
1. {section_1}
2. {section_2}
3. {section_3}

**Audience**: {who_the_consolidated_doc_is_for}

**Tone Guidance**: {voice_and_style_notes}

**Special Handling**:
- {special_consideration_1}
- {special_consideration_2}

---

## Extraction Metrics

| Metric | Value |
|--------|-------|
| Source Token Count | {source_token_count} |
| Extraction Token Count | {extraction_token_count} |
| Compression Ratio | {ratio} |
| Conflicts Total | {total_conflicts} |
| Conflicts Blocking | {blocking_count} |
| Gaps Identified | {gap_count} |

## Next Steps

- [ ] Resolve blocking conflicts before synthesis
- [ ] Fill identified gaps (if blocking)
- [ ] Proceed to Phase 2: Synthesis
