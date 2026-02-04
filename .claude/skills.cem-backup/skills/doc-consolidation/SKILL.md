---
name: doc-consolidation
description: "Documentation consolidation workflow schemas. Use when: consolidating fragmented docs, building extraction artifacts, managing checkpoints, or creating file manifests. Triggers: consolidation, extraction, checkpoint, manifest, synthesis, topic mapping, staleness detection."
---

# Documentation Consolidation Workflow

> **Status**: Complete (Sprint 1, 2, & 5)

## Purpose

This skill defines the artifact schemas for the Documentation Consolidation Workflow - a phased approach to consolidating fragmented documentation into authoritative consolidated documents.

The workflow solves the "scattered knowledge" problem: information about a topic exists in multiple files, leading to inconsistencies, duplication, and high token costs for agents reading all sources.

## Core Problem

```
Before Consolidation:
  Source A (3K tokens) ──┐
  Source B (4K tokens) ──┼── Agent reads all (~10K tokens)
  Source C (3K tokens) ──┘

After Consolidation:
  Extraction (2K tokens) ── Synthesis Agent ── Consolidated Doc
```

## Workflow Phases

| Phase | Agent | Input | Output |
|-------|-------|-------|--------|
| 0. Discovery | Discovery Agent | File listing, first 50 lines | `MANIFEST.yaml` |
| 1. Extraction | Extractor Agent | Source files, manifest | `extraction-{topic}.yaml` |
| 2. Synthesis | Synthesis Agent | Extraction artifact | Consolidated document |
| 3. Review | Review Agent | Draft document | Approved/feedback |

## Schema Artifacts

### MANIFEST.yaml
**Location**: `.consolidation/MANIFEST.yaml`
**Schema**: [manifest-schema.md](schemas/manifest-schema.md)

Maps files to topics with minimal context (file path + first 50 lines). Enables targeted extraction without full file reads.

Key fields:
- `files[]` - File catalog with hashes, line counts, topic assignments
- `topics[]` - Topic definitions with priority, dependencies, primary source
- `exclusions[]` - Files intentionally not mapped
- `ambiguous[]` - Mappings requiring human input

### extraction-{topic}.yaml
**Location**: `.consolidation/extraction-{topic}.yaml`
**Schema**: [extraction-schema.md](schemas/extraction-schema.md)

Captures analyzed content so synthesis agents work from structured data (~2K tokens) instead of raw sources (~10K tokens).

Key fields:
- `canonical_sections[]` - Extracted sections with authority source
- `conflicts[]` - Disagreements between sources with resolution status
- `shared_concepts[]` - Concepts appearing across multiple sources
- `synthesis_notes` - Guidance for synthesis agent

### checkpoint-{topic}.yaml
**Location**: `.consolidation/checkpoint-{topic}.yaml`
**Schema**: [checkpoint-format.md](schemas/checkpoint-format.md)

Enables any agent to resume consolidation without re-reading sources or re-analyzing content.

Key fields:
- `status` - Current phase, state, blockers
- `sources[]` - File hashes for staleness detection
- `concepts[]` - Semantic understanding captured
- `synthesis` - Section-by-section progress
- `activity_log[]` - Audit trail

## Directory Structure

```
.consolidation/
  MANIFEST.yaml                      # Phase 0 output
  checkpoint-settings-merge.yaml     # Per-topic checkpoint
  checkpoint-agent-routing.yaml
  extraction-settings-merge.yaml     # Per-topic extraction
  extraction-agent-routing.yaml
```

## Staleness Detection

All schemas use SHA-256 hashes for staleness detection:

```yaml
# In checkpoint
sources:
  - path: "docs/design/TDD-0042.md"
    hash: "a1b2c3..."  # Compare to actual file
    status: stale      # Triggers re-extraction
```

When a source hash doesn't match:
1. Mark source as `stale` in checkpoint
2. Re-run extraction for affected sections
3. Update synthesis if content changed

## Token Efficiency

| Artifact | Target Size | Purpose |
|----------|-------------|---------|
| Manifest | < 1K tokens | Quick topic discovery |
| Extraction | < 2K tokens | Semantic capture of ~10K source |
| Checkpoint | < 500 tokens | State tracking overhead |

## Templates

Copy-paste ready templates for consolidation artifacts:

| Template | Purpose | When to Use |
|----------|---------|-------------|
| [topic-summary.md](templates/topic-summary.md) | Phase 1 topic analysis | After extraction, before synthesis |
| [numbered-doc.md](templates/numbered-doc.md) | Consolidated document structure | Phase 2 synthesis output |
| [index.md](templates/index.md) | INDEX.md mapping file | Phase 4 archive tracking |
| [consolidation-manifest.md](templates/consolidation-manifest.md) | Overall progress tracking | All phases |

### Template Usage

**topic-summary.md**: Use during Phase 1 to document extraction findings. Captures sources analyzed, conflicts identified, gaps found, and consolidation recommendations. Aligns with extraction-schema.md fields.

**numbered-doc.md**: Structure for consolidated documents in Phase 2. Sections derived from extraction canonical_sections. Includes cross-references and revision history.

**index.md**: Generate during Phase 4 to track original-to-consolidated mappings. Documents archive location, navigation updates, and exclusions.

**consolidation-manifest.md**: Master tracking document for the entire consolidation effort. Track phase progress, blockers, decisions, and metrics across all topics.

## Patterns

Decision frameworks and heuristics for consolidation work:

| Pattern | Purpose | When to Use |
|---------|---------|-------------|
| [grouping-heuristics.md](patterns/grouping-heuristics.md) | Topic clustering rules | Phase 0: Categorizing files into topics |
| [merge-strategies.md](patterns/merge-strategies.md) | Merge/split decision framework | Phase 1-2: Resolving overlapping content |
| [numbering-conventions.md](patterns/numbering-conventions.md) | Numbering scheme semantics | Phase 2: Naming consolidated documents |

### Pattern Usage

**grouping-heuristics.md**: Apply during Phase 0 (Discovery) to classify files into topic clusters. Covers naming patterns, content similarity detection, cross-reference clustering, and directory inheritance. Includes decision tree for ambiguous files.

**merge-strategies.md**: Apply during Phase 1-2 when sources overlap. Defines overlap thresholds (>50% = merge), conflict resolution priority, and information preservation guarantees. Includes authority hierarchy and merge direction rules.

**numbering-conventions.md**: Apply during Phase 2 (Synthesis) to assign document numbers. Semantic ranges: 001-099 (core), 100-199 (features), 200-299 (operations), 900-999 (reference). Ensures consistent organization and predictable discovery.

## Examples

Concrete YAML examples showing complete artifacts:

| Example | Demonstrates | Based On |
|---------|--------------|----------|
| [manifest-example.yaml](examples/manifest-example.yaml) | Complete MANIFEST.yaml | manifest-schema.md |
| [extraction-example.yaml](examples/extraction-example.yaml) | Complete extraction artifact | extraction-schema.md |
| [checkpoint-example.yaml](examples/checkpoint-example.yaml) | Mid-workflow checkpoint | checkpoint-format.md |

### Example Usage

**manifest-example.yaml**: Reference for Discovery Agent output. Shows realistic file catalog with 8 files across 3 topics, including exclusions and ambiguous mappings requiring resolution.

**extraction-example.yaml**: Reference for Extractor Agent output. Demonstrates semantic capture of ~8300 source tokens into ~1850 extraction tokens (78% reduction). Includes resolved conflicts and synthesis notes.

**checkpoint-example.yaml**: Reference for workflow state tracking. Shows mid-synthesis checkpoint with 2 of 4 sections drafted, activity log, and notes for resuming agent.

## Validation

Quality gates and validation checklists to ensure consolidation correctness:

| Validation | Purpose | When to Use |
|------------|---------|-------------|
| [checklist.md](validation/checklist.md) | Pre-archive validation checks | Before Phase 4: Comprehensive info preservation |
| [gates.md](validation/gates.md) | Quality gates between phases | All phases: Mandatory phase transition checks |
| [test-matrix.md](validation/test-matrix.md) | Test scenarios by complexity | Testing: Validate workflow handles all cases |

### Validation Usage

**checklist.md**: Run before archiving original files. Covers information preservation (IP-1 through IP-4), link integrity (LI-1 through LI-3), schema compliance (SC-1 through SC-3), and cross-reference resolution (CR-1 through CR-3). Includes automated check scripts and manual verification templates.

**gates.md**: Mandatory checkpoints between phases. Each gate has blocking checks (must pass) and warning checks (should address). Gates: Manifest (Phase 0->1), Extraction (1->2), Synthesis (2->3), Review (3->4), Archive (4->Validation), Validation (Complete). Includes gate logging format and failure recovery procedures.

**test-matrix.md**: Test scenarios across four complexity tiers: Simple (3-5 docs, no conflicts), Medium (10-15 docs, some overlap), Complex (20+ docs, multiple conflicts), Edge (empty files, circular refs, binary files, unicode, etc.). Includes test execution protocol, regression test suite, and performance benchmarks.

## Related Skills

- [doc-ecosystem](../doc-ecosystem/SKILL.md) - Ecosystem templates (Gap Analysis, Context Design)
- [documentation](../documentation/SKILL.md) - Core artifact templates (PRD, TDD, ADR)
- [10x-workflow](../10x-workflow/SKILL.md) - Agent coordination patterns
