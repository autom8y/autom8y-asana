# Test Matrix for Consolidation Validation

> **Purpose**: Define test scenarios across complexity levels to validate the consolidation workflow handles simple, medium, complex, and edge cases correctly.

## Design Principles

1. **Progressive Complexity**: Start simple, add complexity systematically
2. **Representative Coverage**: Each tier tests different failure modes
3. **Repeatable Execution**: Scenarios can be re-run for regression testing
4. **Edge Case Emphasis**: Unusual inputs often reveal bugs

---

## Complexity Tiers

| Tier | Documents | Overlaps | Conflicts | Edge Cases | Purpose |
|------|-----------|----------|-----------|------------|---------|
| Simple | 3-5 | None | None | None | Baseline functionality |
| Medium | 10-15 | Some | Some | Few | Typical real-world scenario |
| Complex | 20+ | Many | Multiple | Many | Stress test and robustness |
| Edge | Variable | N/A | N/A | All | Boundary conditions |

---

## Simple Tier (3-5 Documents, No Conflicts)

### Scenario S1: Clean Three-File Consolidation

**Setup:**
```
test-data/simple/s1/
  doc-a.md (500 tokens) - Primary source for "widget-config"
  doc-b.md (300 tokens) - Secondary source, extends doc-a
  doc-c.md (200 tokens) - Supplementary examples
```

**Characteristics:**
- Clear authority hierarchy
- No contradictions between sources
- Single topic
- No cross-references

**Expected Outcomes:**

| Phase | Expected Result |
|-------|-----------------|
| Manifest | 3 files, 1 topic, doc-a as primary |
| Extraction | ~400 tokens extraction, 0 conflicts |
| Synthesis | ~600 tokens consolidated doc |
| Archive | 3 files archived, 1 consolidated |

**Gate Validations:**
- MG-1 through MG-8: All pass
- EG-1 through EG-8: All pass (no conflicts)
- SG-1: 100% concept preservation
- SG-3: Token reduction (1000 -> 600)

### Scenario S2: Five-File Linear Dependency

**Setup:**
```
test-data/simple/s2/
  intro.md (200 tokens) - Overview, no dependencies
  concepts.md (400 tokens) - Core concepts
  api.md (300 tokens) - API docs, depends on concepts
  examples.md (250 tokens) - Examples, depends on api
  faq.md (150 tokens) - FAQ, depends on all
```

**Characteristics:**
- Linear dependency chain
- Clear extraction order required
- No conflicts
- Some cross-references

**Expected Outcomes:**

| Check | Expected |
|-------|----------|
| Dependency order | intro -> concepts -> api -> examples -> faq |
| Cross-references | All updated to consolidated paths |
| Token reduction | 1300 -> ~800 |

### Scenario S3: Disjoint Topics

**Setup:**
```
test-data/simple/s3/
  auth-overview.md (300 tokens) - Auth topic
  auth-config.md (200 tokens) - Auth topic
  logging-setup.md (400 tokens) - Logging topic (separate)
```

**Characteristics:**
- Two distinct topics
- No overlap between topics
- Tests topic separation

**Expected Outcomes:**
- MANIFEST shows 2 topics
- Separate extraction files per topic
- Separate consolidated outputs
- No cross-topic contamination

---

## Medium Tier (10-15 Documents, Some Overlap)

### Scenario M1: Overlapping Content, Clear Authority

**Setup:**
```
test-data/medium/m1/
  primary/
    main-guide.md (800 tokens) - Primary authority
    api-reference.md (600 tokens) - Primary for API
  secondary/
    getting-started.md (400 tokens) - Duplicates some main-guide
    tutorial-1.md (350 tokens) - Examples from main-guide
    tutorial-2.md (300 tokens) - More examples
    troubleshooting.md (450 tokens) - References API
  supporting/
    changelog.md (200 tokens)
    contributing.md (250 tokens)
    glossary.md (300 tokens)
    license.md (50 tokens) - Should be excluded
```

**Characteristics:**
- 10 files across 3 directories
- ~40% content overlap between main-guide and getting-started
- Clear authority hierarchy
- Mix of file types

**Expected Outcomes:**

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Total files | 10 | 3 consolidated + 1 excluded | 70% |
| Total tokens | 3700 | ~2200 | 40% |
| Topics | 3 | 3 | - |

**Conflict Testing:**
- Overlap detection between main-guide and getting-started
- Authority resolution: main-guide wins
- Duplicate examples consolidated

### Scenario M2: Multiple Conflicts Requiring Resolution

**Setup:**
```
test-data/medium/m2/
  design/
    TDD-architecture.md - States "timeout default: 30s"
    TDD-config.md - States "timeout default: 60s"
  implementation/
    config-module.md - Shows timeout = 45
  docs/
    user-guide.md - States "timeout default: 30s"
    api-docs.md - States "timeouts are configurable"
```

**Conflict Matrix:**

| Conflict | Sources | Positions | Severity |
|----------|---------|-----------|----------|
| C1: Timeout default | TDD-arch, TDD-config, config-module | 30s, 60s, 45 | Blocking |
| C2: Feature availability | user-guide, api-docs | Partial vs full | Significant |
| C3: Terminology | Multiple | Various terms for same concept | Minor |

**Expected Outcomes:**
- EG-5: Blocking conflict C1 must be resolved before synthesis gate
- EG-2: All 3 conflicts documented in extraction
- Conflict resolution recorded with authority and rationale

### Scenario M3: Cross-Reference Web

**Setup:**
```
test-data/medium/m3/
  15 documents with circular-ish references:
  - doc-a references doc-b, doc-c
  - doc-b references doc-c, doc-d
  - doc-c references doc-a, doc-e
  ... (web of cross-references)
```

**Characteristics:**
- Tests cross-reference resolution
- No true circular dependencies (topics are independent)
- References must all update to consolidated paths

**Expected Outcomes:**
- LI-1: All internal links resolve post-consolidation
- LI-3: No references to archived files
- CR-1: Topic dependencies satisfied

---

## Complex Tier (20+ Documents, Multiple Conflicts)

### Scenario C1: Large-Scale Documentation Set

**Setup:**
```
test-data/complex/c1/
  25 documents, 15,000 total tokens
  5 topics with interdependencies
  8 identified conflicts
  3 different file types (md, yaml configs, code comments)
```

**Stress Test Points:**

| Aspect | Test |
|--------|------|
| Scale | 25 files processed without timeout |
| Token efficiency | < 2K tokens per extraction |
| Conflict handling | 8 conflicts categorized and tracked |
| Cross-references | 50+ internal links all resolve |

### Scenario C2: Deep Dependency Chain

**Setup:**
```
Topic dependency graph:
  A (no deps)
  B depends on A
  C depends on A, B
  D depends on B, C
  E depends on C, D
  F depends on all
```

**Expected Outcomes:**
- MG-8: Detects no cycles
- CR-1: Enforces extraction order A -> B -> C -> D -> E -> F
- EG-1: Each topic extraction available before dependents start

### Scenario C3: Multi-Author Conflict Resolution

**Setup:**
- Documents from 4 different "authors" (representing different eras/styles)
- Conflicting information with no clear recency
- Requires authority hierarchy resolution

**Conflict Patterns:**
- Terminology drift over time
- Contradictory best practices
- Overlapping but differently-scoped content

---

## Edge Cases

### E1: Empty Files

**Setup:**
```
test-data/edge/e1/
  non-empty.md (100 tokens)
  empty.md (0 tokens)
  whitespace-only.md (0 tokens after trim)
```

**Expected Behavior:**
- Empty files flagged in MANIFEST exclusions
- Reason: "empty" or "whitespace_only"
- MG-3: Not counted as orphans (explicitly excluded)

### E2: Circular References (True Cycles)

**Setup:**
```
doc-a.md references doc-b
doc-b.md references doc-c
doc-c.md references doc-a
```

**Expected Behavior:**
- MG-8: Fails if modeled as topic dependencies
- If modeled as cross-references only: LI-1 validates links resolve

### E3: Binary Files in Scope

**Setup:**
```
test-data/edge/e3/
  readme.md
  diagram.png
  logo.svg
  data.json (valid JSON, not markdown)
```

**Expected Behavior:**
- Binary files excluded with reason: "binary"
- JSON files handled as config type or excluded
- MG-3: Binaries not counted as orphans

### E4: Very Large Single File

**Setup:**
```
test-data/edge/e4/
  massive.md (50,000 tokens)
```

**Expected Behavior:**
- MANIFEST warns about size
- Topic split recommended (> 10K tokens)
- Extraction may require subsection approach

### E5: Unicode and Special Characters

**Setup:**
```
test-data/edge/e5/
  unicode-title-日本語.md
  special-chars-@#$.md
  emoji-doc-🚀.md
```

**Expected Behavior:**
- File paths handled correctly
- Content with unicode preserved
- Hash computation works on unicode content

### E6: Duplicate File Names in Different Directories

**Setup:**
```
test-data/edge/e6/
  api/README.md
  cli/README.md
  web/README.md
```

**Expected Behavior:**
- Each treated as separate file
- Topics assigned correctly (may be same or different)
- INDEX.md disambiguates by full path

### E7: File Modified During Consolidation

**Setup:**
- Start consolidation
- Modify source file mid-process
- Continue consolidation

**Expected Behavior:**
- SC-1 or EG-6: Stale hash detected
- Extraction invalidated for modified source
- Workflow prompts re-extraction

### E8: Missing Primary Source

**Setup:**
```
test-data/edge/e8/
  supplementary-1.md (supplementary for topic-x)
  supplementary-2.md (supplementary for topic-x)
  # No primary source exists
```

**Expected Behavior:**
- MG-5: Fails - no primary source for topic-x
- MANIFEST must designate one as primary or human input required

### E9: Conflicting Exclusions

**Setup:**
- File marked excluded in one topic
- Same file marked included in another topic

**Expected Behavior:**
- MANIFEST validation detects inconsistency
- Flags in ambiguous[] for resolution

### E10: Self-Referencing Document

**Setup:**
```
doc.md contains link to doc.md itself (anchor link)
```

**Expected Behavior:**
- LI-1: Self-reference anchor links resolve
- Not flagged as circular dependency

---

## Test Execution Protocol

### Setup Phase

```bash
# Create test data directory
mkdir -p test-data/{simple,medium,complex,edge}

# Generate test scenarios
./scripts/generate-test-scenarios.sh

# Verify test data
./scripts/validate-test-data.sh
```

### Execution Phase

For each scenario:

```bash
# 1. Run discovery (Phase 0)
./consolidate.sh discover test-data/{tier}/{scenario}/

# 2. Verify Manifest Gate
./validate.sh manifest-gate

# 3. Run extraction (Phase 1)
./consolidate.sh extract test-data/{tier}/{scenario}/

# 4. Verify Extraction Gate
./validate.sh extraction-gate

# 5. Run synthesis (Phase 2)
./consolidate.sh synthesize test-data/{tier}/{scenario}/

# 6. Verify Synthesis Gate
./validate.sh synthesis-gate

# 7. Complete review (Phase 3) - may be automated for tests
./consolidate.sh review test-data/{tier}/{scenario}/

# 8. Verify Review Gate
./validate.sh review-gate

# 9. Run archive (Phase 4)
./consolidate.sh archive test-data/{tier}/{scenario}/

# 10. Verify Archive and Validation Gates
./validate.sh archive-gate
./validate.sh validation-gate
```

### Validation Phase

```yaml
test_result:
  scenario: "{tier}/{scenario}"
  phases_completed: [0, 1, 2, 3, 4]
  gates_passed: [manifest, extraction, synthesis, review, archive, validation]
  gates_failed: []
  token_reduction:
    before: {count}
    after: {count}
    percentage: {percent}
  conflicts:
    total: {count}
    resolved: {count}
    deferred: {count}
  issues: []
```

---

## Regression Test Suite

### Minimum Regression Set

Run these scenarios for every workflow change:

| Scenario | Tests | Priority |
|----------|-------|----------|
| S1 | Basic functionality | P0 |
| S3 | Multi-topic handling | P0 |
| M2 | Conflict resolution | P0 |
| E1 | Empty file handling | P1 |
| E3 | Binary exclusion | P1 |
| E7 | Staleness detection | P1 |

### Full Regression Set

Run all scenarios before major releases:
- All Simple (S1-S3)
- All Medium (M1-M3)
- All Complex (C1-C3)
- All Edge (E1-E10)

### Performance Benchmarks

| Scenario | Max Duration | Target Duration |
|----------|--------------|-----------------|
| Simple | 30s | 10s |
| Medium | 2min | 45s |
| Complex | 10min | 3min |

---

## Test Data Templates

### Simple Scenario Template

```markdown
# {Topic Name} - {Role}

> Summary line for discovery phase.

## Section 1: {Heading}

{Content that should be consolidated}

## Section 2: {Heading}

{More content with clear structure}

---
*Test file for consolidation validation*
```

### Conflict Scenario Template

```markdown
# {Topic Name} - Source A

## Configuration

The default timeout is **30 seconds**.

---

# {Topic Name} - Source B

## Configuration

The default timeout is **60 seconds**.
```

---

## Success Criteria Summary

| Tier | Pass Criteria |
|------|---------------|
| Simple | All gates pass, > 30% token reduction, 0 info loss |
| Medium | All gates pass, conflicts documented, > 25% token reduction |
| Complex | All gates pass, no timeouts, scalable performance |
| Edge | Graceful handling, appropriate errors, no crashes |

---

*Part of the [Documentation Consolidation Workflow](../SKILL.md)*
