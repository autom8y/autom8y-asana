---
name: reflect
description: "Triage accumulated complaints from .sos/wip/complaints/. Deduplicates, scores using triage-scoring model, cross-references scar-tissue, produces prioritized backlog."
argument-hint: "[--dry-run]"
allowed-tools: Bash, Read, Write, Glob, Grep, Skill
model: opus
---

# /reflect -- Complaint Triage Pipeline

Reads accumulated complaints filed by agents via the complaint-filing skill, deduplicates by tag/title similarity, scores using the 6-dimension triage-scoring model, cross-references against `.know/scar-tissue.md`, and produces a prioritized triage backlog at `.sos/wip/TRIAGE-complaints.md`.

## Context

This command runs in the main thread (single-agent judgment pipeline). The model itself applies the scoring rubric -- scores are assessed by judgment using the dimensional weights, not computed algorithmically. No subagent dispatch is needed; the inputs (complaint YAML files + scar-tissue) fit comfortably in a single context window.

## Platform Constraint: Read Before Write

**The Claude Code Write tool WILL FAIL if you attempt to write to an existing file without first reading it via the Read tool in the current conversation.** Before writing `.sos/wip/TRIAGE-complaints.md`, check whether it already exists and `Read()` it first if so.

## Pre-flight

### Parse Arguments

- `--dry-run`: If present, display triage results to the user but do NOT write the output file. Useful for previewing triage without persisting.
- No arguments: standard mode (score and write output).

### Verify Complaints Exist

1. Check that the complaints directory exists and contains files:
   ```
   Glob(".sos/wip/complaints/COMPLAINT-*.yaml")
   ```

2. If no files found (directory missing or empty):
   - Output: "No complaints to triage. The complaints directory `.sos/wip/complaints/` is empty or does not exist."
   - STOP. Do not proceed to scoring.

3. Record the count of complaint files found. This is the raw input count before dedup.

## Step 1: Load Scoring Model

Load the triage-scoring skill to get the full rubric into context:

```
Skill("triage-scoring")
```

This provides:
- 6 scoring dimensions with weights (Severity 25%, Recurrence 20%, Zone Impact 20%, Scar-Tissue Match 15%, Effort-to-Impact 10%, Source Diversity 10%)
- Dimension scoring rules (severity enum to score mapping, recurrence bands, zone mappings)
- Threshold bands (0-39 auto-reject, 40-69 auto-accept, 70-84 human-review, 85-100 adr-required)
- Zone override rules (behavior forces human-review, structure forces adr-required)
- Cross-reference protocol (match types and score adjustments)
- Output format (per-complaint YAML entry)

Do NOT proceed until the skill content is loaded. The scoring rules are the authoritative reference for all subsequent steps.

## Step 2: Read All Complaints

Read every complaint file found in pre-flight:

```
Read(".sos/wip/complaints/COMPLAINT-{each-file}.yaml")
```

For each file, parse the YAML and extract:
- `id`: complaint identifier
- `filed_by`: agent name
- `filed_at`: timestamp
- `title`: short description
- `severity`: low | medium | high | critical
- `description`: full friction description
- `tags`: string array
- `status`: filed | triaged | resolved
- `zone`: parameter | behavior | structure (optional, from deep-file format)
- `effort_estimate`: trivial | small | medium | large | epic (optional)
- `related_scars`: string array (optional)
- `evidence`: object with session_id, event_refs, context (optional)

**Skip already-triaged complaints**: If a complaint has `status: triaged` or `status: resolved`, skip it. Only process `status: filed` complaints.

Record all parsed complaints for the next step.

## Step 3: Deduplicate

Group complaints that describe the same or closely related friction:

**Dedup signals** (apply in order):
1. **Tag overlap**: Two complaints sharing 2+ identical tags are candidates for grouping.
2. **Title similarity**: Two complaints whose titles describe the same friction pattern (semantic judgment -- e.g., "missing skill for X" and "no skill available for X" are the same).
3. **Filed-by convergence**: Multiple complaints from different agents about the same friction (this also feeds source diversity scoring).

**Grouping rules**:
- Each group gets a **representative title** (the most descriptive title from the group).
- Each group records all member complaint IDs.
- Each group inherits the **highest severity** among its members.
- Each group records **recurrence count** = number of member complaints.
- Each group records **distinct filers** = number of unique `filed_by` values.
- If any member has a `zone` field, the group inherits the **most restrictive zone** (structure > behavior > parameter).
- If any member has an `effort_estimate`, the group inherits it. If multiple members have different estimates, use the most common one.

After dedup, record the group count. This is the effective complaint count for scoring.

## Step 4: Cross-Reference Scar Tissue

Read the scar-tissue knowledge file:

```
Read(".know/scar-tissue.md")
```

**If the file does not exist**: Set scar-tissue dimension to 20 (baseline) for all groups. Log a warning: "`.know/scar-tissue.md` not found -- scar-tissue cross-reference skipped. Run `/know scar-tissue` to generate." Proceed to Step 5.

**If the file exists**: For each complaint group, search the Failure Catalog for matching SCAR entries.

**Match detection**: Search SCAR entries for overlap with the complaint group's description, tags, or friction pattern. Match on:
- Fix location overlap (complaint describes friction in a file/package that a SCAR's fix location covers)
- Category overlap (complaint tags match a SCAR's category)
- Behavioral pattern similarity (complaint describes the same class of failure a SCAR documents)

**Classify each match** per the triage-scoring cross-reference protocol:

| Match Type | Condition | Scar-Tissue Dimension Score |
|------------|-----------|----------------------------|
| **Regression** | SCAR was fixed but complaint describes the same failure recurring | 95 |
| **Known-and-fixed** | Complaint describes a pattern already addressed by a SCAR | 40 |
| **Related** | Complaint is adjacent to but distinct from a SCAR | 60 |
| **No match** | No SCAR relates to this complaint | 20 |

Record `scar_ref: "SCAR-NNN (TYPE)"` for each matched group. This notation appears in the triage output.

## Step 5: Score Each Group

Apply the 6-dimension scoring model to each deduplicated complaint group. For each group:

### Dimension Scoring

| Dimension | Weight | Input | Scoring Rule |
|-----------|--------|-------|--------------|
| Severity | 25% | Group's severity field | low=20, medium=45, high=70, critical=95 |
| Recurrence | 20% | Group's recurrence count | 1=15, 2=40, 3-4=65, 5+=90 |
| Zone Impact | 20% | Group's zone field | parameter=30, behavior=60, structure=90, missing=45 |
| Scar-Tissue Match | 15% | From Step 4 | no-match=20, fixed=40, related=60, regression=95 |
| Effort-to-Impact | 10% | Group's effort_estimate + severity | See triage-scoring skill rules; default 50 if absent |
| Source Diversity | 10% | Group's distinct filer count | 1=20, 2=50, 3+=80 |

### Compute Composite Score

```
score = (severity * 0.25) + (recurrence * 0.20) + (zone_impact * 0.20) + (scar_tissue * 0.15) + (effort_to_impact * 0.10) + (source_diversity * 0.10)
```

### Apply Zone Overrides

After computing the raw score, apply zone-based routing overrides per the triage-scoring model:

- If zone is `behavior`: action is AT LEAST `human-review` regardless of score
- If zone is `structure`: action is AT LEAST `adr-required` regardless of score
- If zone is `parameter`: standard threshold routing applies

The zone override only **elevates** review level, never reduces it. A parameter-zone complaint scoring 85+ still requires an ADR per the threshold band.

### Classify into Threshold Band

| Score Range | Base Action |
|-------------|-------------|
| 0-39 | auto-reject |
| 40-69 | auto-accept |
| 70-84 | human-review |
| 85-100 | adr-required |

Apply zone override after threshold classification. Record the final action for each group.

### Sort by Priority

1. Score descending (highest first)
2. Within same score: severity descending (critical > high > medium > low)
3. Within same score and severity: alphabetical by representative title

## Step 6: Assemble Output

Build the triage output document:

```markdown
# Complaint Triage -- {YYYY-MM-DD}

## Summary
{2-3 sentences: raw complaint count, group count after dedup, score distribution across bands, identify the highest-priority finding}

## Triage Results

### Priority 1: ADR Required (85-100)

{For each group in this band, highest score first:}

- id: {representative-complaint-id}
  score: {0-100}
  action: adr-required
  zone: {parameter|behavior|structure}
  scar_ref: "{SCAR-NNN (TYPE)}" # if matched, omit line if no match
  members: [{list of all complaint IDs in this group}]
  title: "{representative title}"
  dimension_scores:
    severity: {0-100}
    recurrence: {0-100}
    zone_impact: {0-100}
    scar_tissue_match: {0-100}
    effort_to_impact: {0-100}
    source_diversity: {0-100}
  rationale: "{one-line explanation of why this action was assigned}"

### Priority 2: Human Review (70-84)

{Same format per group}

### Priority 3: Auto-Accept (40-69)

{Same format per group}

### Priority 4: Auto-Reject (0-39)

{Same format per group}

## Cross-Reference Log

{List every scar_ref match found during Step 4, with the complaint group title and the matched SCAR ID and type. If no matches: "No scar-tissue matches found."}

## Methodology
- Complaints read: {N} files
- Skipped (already triaged): {N}
- After dedup: {N} groups
- Scoring model: triage-scoring (6 weighted dimensions, 0-100 composite)
- Scar-tissue cross-reference: .know/scar-tissue.md ({N} SCARs checked)
- Zone overrides applied: {N} groups had zone-based action elevation
- Run date: {YYYY-MM-DD}
```

## Step 7: Write and Display

### If `--dry-run`

Display the full triage output to the user in the conversation. Do NOT write any file. End with:

```
(dry run -- no file written)
```

STOP.

### If standard mode

1. **Check for existing output**:
   ```
   Glob(".sos/wip/TRIAGE-complaints.md")
   ```
   If it exists, `Read(".sos/wip/TRIAGE-complaints.md")` first (platform read-before-write constraint).

2. **Write output**:
   ```
   Write(".sos/wip/TRIAGE-complaints.md", triage_content)
   ```

3. **Verify**:
   ```
   Read(".sos/wip/TRIAGE-complaints.md", limit=30)
   ```
   Confirm the Summary section and first triage entry are present.

4. **Display summary to user**:

```
## Complaint Triage Complete -- {YYYY-MM-DD}

| Band | Count | Action |
|------|-------|--------|
| 85-100 | {N} | ADR required |
| 70-84 | {N} | Human review |
| 40-69 | {N} | Auto-accept |
| 0-39 | {N} | Auto-reject |

**{total_groups} complaint groups** from {total_raw} raw complaints.

{If any adr-required or human-review groups exist:}
Top finding: [{id}] {title} (score: {score}, action: {action})

Full report: `.sos/wip/TRIAGE-complaints.md`
```

---

## Error Handling

| Scenario | Action |
|----------|--------|
| No `.sos/wip/complaints/` directory | "No complaints to triage." STOP. |
| Directory exists but no COMPLAINT-*.yaml files | "No complaints to triage." STOP. |
| All complaints already triaged (status != filed) | "No new complaints to triage. All {N} complaints have status: triaged or resolved." STOP. |
| `.know/scar-tissue.md` missing | Warning in output. Scar-tissue dimension defaults to 20. Continue. |
| Complaint YAML malformed (unparseable) | Skip that file. Log warning: "Skipped {filename}: malformed YAML." Continue with remaining. |
| `triage-scoring` skill not available | ERROR: "triage-scoring skill not loaded. Run `ari sync --scope=user --resource=mena` to sync shared skills." STOP. |
| Write fails | ERROR with path and reason. Display triage results in conversation as fallback. |

---

## Anti-Patterns

- **Scoring without loading the skill first**: The triage-scoring skill is the authoritative rubric. Do NOT invent scoring rules or weights from memory. Always `Skill("triage-scoring")` before scoring.
- **Dispatching subagents for scoring**: This is a single-agent pipeline. Do NOT use Task tool. You are the scoring engine.
- **Modifying complaint files**: This command is READ-ONLY on complaint files. Never update `status`, add fields, or delete complaints. A separate command handles complaint lifecycle.
- **Exact-match dedup only**: Dedup is heuristic. Two complaints about the same friction with different wording should still be grouped. Use tag overlap AND semantic title similarity.
- **Ignoring zone overrides**: A behavior-zone complaint scoring 45 is NOT auto-accept. Zone overrides are mandatory per the triage-scoring model. Always apply zone overrides after threshold classification.
- **Writing output during --dry-run**: Dry run means display only. No file writes.

---

## Sigil

### On Success

End your response with:

```
reflected {N} complaints into {M} groups -- next: review TRIAGE-complaints.md
```

### On Empty

```
reflected -- inbox empty
```

### On Failure

```
reflect failed: {brief reason} -- fix: {recovery hint}
```
