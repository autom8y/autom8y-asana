# Pre-Archive Validation Checklist

> **Purpose**: Comprehensive validation checks to run before archiving original files. Ensures information preservation, link integrity, and schema compliance.

## Design Principles

1. **No Silent Loss**: Every piece of source information must be accounted for
2. **Verify Before Archive**: Archive is irreversible in practice; validate first
3. **Automated Where Possible**: Scripted checks catch what humans miss
4. **Traceable Decisions**: Every exclusion or transformation must be documented

---

## Information Preservation Checks

### IP-1: Key Concept Coverage

Verify every key concept from extraction files appears in consolidated output.

```yaml
validation:
  name: "Key Concept Coverage"
  id: IP-1
  severity: blocking
  automated: partial

check:
  for_each: extraction-{topic}.yaml
  verify:
    - all items in shared_concepts[].concept exist in consolidated doc
    - all items in canonical_sections[].key_points exist in consolidated doc
    - all conflict resolutions are reflected in consolidated content

pass_criteria: 100% of key concepts accounted for
fail_action: Block archive; list missing concepts
```

**Manual Steps:**

1. Open extraction file for topic
2. For each `shared_concepts[].concept`:
   - Search consolidated doc for concept term
   - Verify definition is preserved (may be reworded)
   - Check "FOUND" or note location of gap
3. For each `canonical_sections[].key_points`:
   - Search consolidated doc for key point content
   - Verify technical accuracy preserved
   - Check "FOUND" or note location of gap

### IP-2: Conflict Resolution Preservation

Verify all conflict resolutions from extraction are applied in synthesis.

```yaml
validation:
  name: "Conflict Resolution Preservation"
  id: IP-2
  severity: blocking
  automated: partial

check:
  for_each: extraction-{topic}.yaml
  verify:
    - all conflicts[].resolution.decision are reflected in consolidated doc
    - no "unresolved" blocking conflicts remain
    - resolution rationale is traceable

pass_criteria: 0 blocking conflicts unresolved; all decisions applied
fail_action: Block archive; list unresolved conflicts
```

**Verification Table:**

| Conflict ID | Resolution Decision | Applied in Consolidated? | Location |
|-------------|---------------------|--------------------------|----------|
| conflict-001 | {decision} | YES / NO | Section/line |

### IP-3: Source Section Accounting

Every section from every source file must be:
- Preserved in consolidated doc, OR
- Explicitly excluded with documented rationale

```yaml
validation:
  name: "Source Section Accounting"
  id: IP-3
  severity: blocking
  automated: no

check:
  for_each: source file in MANIFEST.yaml
  verify:
    - each H1/H2 heading is mapped to consolidated location
    - exclusions are documented in preservation audit
    - no sections silently dropped

pass_criteria: 100% of source sections accounted for
fail_action: Block archive; create preservation audit for gaps
```

**Audit Template:**

| Source File | Section Heading | Status | Destination | Rationale |
|-------------|-----------------|--------|-------------|-----------|
| {path} | {heading} | preserved / moved / removed | {location} | {reason if removed} |

### IP-4: Code Example Preservation

All code examples from sources should be preserved unless redundant.

```yaml
validation:
  name: "Code Example Preservation"
  id: IP-4
  severity: significant
  automated: partial

check:
  for_each: source file
  verify:
    - code blocks are preserved or superseded by better example
    - language tags preserved correctly
    - source attribution maintained

pass_criteria: All unique code examples preserved
fail_action: Document missing examples; require justification
```

---

## Link Integrity Validation

### LI-1: Internal Cross-References

All internal links in consolidated docs must resolve.

```yaml
validation:
  name: "Internal Cross-References"
  id: LI-1
  severity: blocking
  automated: yes

check:
  for_each: consolidated document
  verify:
    - all [text](path) links resolve to existing files
    - all [text](#anchor) links resolve to existing headings
    - all cross_references from extraction resolve

pass_criteria: 0 broken internal links
fail_action: Block archive; list broken links with line numbers
```

**Automated Check Script:**

```bash
# Extract markdown links and verify targets
grep -oE '\[.+?\]\(.+?\)' consolidated-doc.md | \
while read link; do
  target=$(echo "$link" | sed 's/.*(\(.*\))/\1/')
  if [[ "$target" == \#* ]]; then
    # Anchor link - check heading exists
    anchor="${target#\#}"
    grep -qi "^#.*$anchor" consolidated-doc.md || echo "BROKEN: $link"
  elif [[ -f "$target" ]]; then
    echo "OK: $link"
  else
    echo "BROKEN: $link"
  fi
done
```

### LI-2: External Reference Validity

External URLs should be verified (where practical).

```yaml
validation:
  name: "External Reference Validity"
  id: LI-2
  severity: minor
  automated: partial

check:
  for_each: external URL in consolidated doc
  verify:
    - URL format is valid
    - Domain is accessible (optional HTTP check)
    - Link text describes destination accurately

pass_criteria: All URLs syntactically valid; external checks advisory
fail_action: Log warnings; do not block archive
```

### LI-3: Archive Path References

After archiving, links pointing to original locations must be updated.

```yaml
validation:
  name: "Archive Path References"
  id: LI-3
  severity: blocking
  automated: yes

check:
  scope: entire repository
  verify:
    - no links point to to-be-archived files
    - all references updated to point to consolidated doc
    - INDEX.md mappings are complete

pass_criteria: 0 references to soon-to-be-archived paths
fail_action: Block archive; list files with stale references
```

**Search Command:**

```bash
# Find references to files being archived
for file in $(cat archive-list.txt); do
  grep -rn "$file" --include="*.md" . | grep -v "^\.archive/"
done
```

---

## Schema Compliance Verification

### SC-1: MANIFEST.yaml Validity

Manifest must conform to schema and reflect current state.

```yaml
validation:
  name: "MANIFEST.yaml Validity"
  id: SC-1
  severity: blocking
  automated: yes

check:
  verify:
    - schema_version is "1.0"
    - all required fields present
    - all file paths exist
    - all file hashes match current content
    - no orphan topics (topics without files)
    - no orphan files (files without topics)

pass_criteria: MANIFEST passes schema validation
fail_action: Block archive; list schema violations
```

### SC-2: Extraction File Validity

All extraction files must conform to schema.

```yaml
validation:
  name: "Extraction File Validity"
  id: SC-2
  severity: blocking
  automated: yes

check:
  for_each: extraction-{topic}.yaml
  verify:
    - schema_version is "1.0"
    - topic.id matches filename
    - all source paths exist
    - all source hashes match (not stale)
    - canonical_sections has at least one entry
    - conflicts array exists (may be empty)

pass_criteria: All extraction files pass schema validation
fail_action: Block archive; list invalid files
```

### SC-3: Checkpoint Consistency

Checkpoints must reflect completed state.

```yaml
validation:
  name: "Checkpoint Consistency"
  id: SC-3
  severity: significant
  automated: yes

check:
  for_each: checkpoint-{topic}.yaml
  verify:
    - status.phase is "archive" or "complete"
    - status.state is not "blocked"
    - all synthesis.sections[].status are "final"
    - activity_log has archive entry

pass_criteria: All checkpoints show complete state
fail_action: Warn; investigate incomplete checkpoints
```

---

## Cross-Reference Resolution

### CR-1: Topic Dependency Satisfaction

Topics with dependencies must have those dependencies consolidated first.

```yaml
validation:
  name: "Topic Dependency Satisfaction"
  id: CR-1
  severity: blocking
  automated: yes

check:
  for_each: topic in MANIFEST.yaml
  verify:
    - all topics[].dependencies are already consolidated
    - cross-references to dependent topics use new paths
    - no circular dependencies

pass_criteria: Dependency order respected
fail_action: Block archive; show dependency violations
```

### CR-2: Skill Reference Updates

References to consolidated skills in CLAUDE.md and other skills are updated.

```yaml
validation:
  name: "Skill Reference Updates"
  id: CR-2
  severity: blocking
  automated: partial

check:
  scope: .claude/skills/, .claude/CLAUDE.md
  verify:
    - skill references point to consolidated docs
    - "When to Activate" triggers are updated
    - Related Skills sections updated

pass_criteria: All skill references current
fail_action: Block archive; list stale references
```

### CR-3: Navigation Integrity

CLAUDE.md and skill indexes provide valid navigation paths.

```yaml
validation:
  name: "Navigation Integrity"
  id: CR-3
  severity: blocking
  automated: partial

check:
  scope: .claude/CLAUDE.md, .claude/skills/*/index.md
  verify:
    - all linked paths exist
    - navigation reflects consolidated structure
    - no orphan documents (unreachable from navigation)

pass_criteria: All navigation paths valid
fail_action: Block archive; update navigation
```

---

## Validation Execution Order

Run validations in this order to catch foundational issues first:

```
Phase 1: Schema Compliance (SC-1, SC-2, SC-3)
    |
    v  All pass? Continue : Fix and re-run
    |
Phase 2: Information Preservation (IP-1, IP-2, IP-3, IP-4)
    |
    v  All pass? Continue : Fix and re-run
    |
Phase 3: Cross-Reference Resolution (CR-1, CR-2, CR-3)
    |
    v  All pass? Continue : Fix and re-run
    |
Phase 4: Link Integrity (LI-1, LI-2, LI-3)
    |
    v  All pass? ARCHIVE APPROVED : Fix and re-run
```

---

## Quick Reference Checklist

Copy this checklist for each consolidation:

```markdown
## Pre-Archive Validation - {Topic Name}

**Date**: {YYYY-MM-DD}
**Validator**: {agent_or_person}

### Schema Compliance
- [ ] SC-1: MANIFEST.yaml valid
- [ ] SC-2: Extraction files valid
- [ ] SC-3: Checkpoints consistent

### Information Preservation
- [ ] IP-1: Key concepts covered (100%)
- [ ] IP-2: Conflict resolutions applied
- [ ] IP-3: Source sections accounted
- [ ] IP-4: Code examples preserved

### Cross-Reference Resolution
- [ ] CR-1: Topic dependencies satisfied
- [ ] CR-2: Skill references updated
- [ ] CR-3: Navigation integrity verified

### Link Integrity
- [ ] LI-1: Internal links resolve
- [ ] LI-2: External URLs valid (advisory)
- [ ] LI-3: Archive path references cleared

### Approval

- [ ] All blocking checks pass
- [ ] Significant issues documented
- [ ] Ready for archive

**Approved by**: _______________
**Date**: _______________
```

---

## Failure Modes and Recovery

| Failure | Impact | Recovery |
|---------|--------|----------|
| Missing key concept | Information loss | Re-extract from source; update synthesis |
| Broken internal link | Navigation failure | Update link or add missing anchor |
| Stale source hash | Extraction outdated | Re-run extraction for affected source |
| Unresolved conflict | Ambiguous content | Escalate to human; resolve before archive |
| Orphan file | Lost documentation | Add to topic or explicit exclusion |

---

*Part of the [Documentation Consolidation Workflow](../SKILL.md)*
