# Checkpoint Format

> **Purpose**: Define the structure for `.consolidation/checkpoint-{topic}.yaml` files that capture workflow state, enabling any agent to resume consolidation work without re-reading sources or re-analyzing content.

## Design Principles

1. **Semantic State**: Capture understanding, not just completion status
2. **Resumability**: Any agent can pick up where another left off
3. **Dependency Tracking**: Know what inputs affect what outputs
4. **Audit Trail**: Record who did what and when

---

## Schema Definition

```yaml
# .consolidation/checkpoint-{topic}.yaml
# Purpose: Track consolidation progress and enable resumption

# Required: Schema version for forward compatibility
schema_version: "1.0"

# Required: What this checkpoint tracks
topic:
  id: string           # Must match extraction topic.id
  name: string         # Human-readable name

# Required: Current workflow state
status:
  phase: enum          # Current phase in consolidation workflow
  state: enum          # State within the phase
  blocked_by: string   # Reason if blocked (null if not blocked)
  last_activity: string  # ISO 8601 timestamp of last update

# Required: Source file tracking for staleness detection
sources:
  - path: string       # Relative path from repo root
    hash: string       # SHA-256 of file content
    last_read: string  # ISO 8601 timestamp when last processed
    status: enum       # "current" | "stale" | "new" | "deleted"

# Required: Extraction artifact reference
extraction:
  path: string         # Path to extraction-{topic}.yaml
  hash: string         # SHA-256 of extraction file
  created_at: string   # When extraction was generated
  conflicts_resolved: integer  # Count of resolved conflicts
  conflicts_pending: integer   # Count of unresolved conflicts

# Required: Key concepts understood (semantic state)
concepts:
  - name: string       # Concept name
    understanding: string  # 1-2 sentence summary of what agent understands
    confidence: enum   # "high" | "medium" | "low"
    source_refs:       # Where this understanding comes from
      - string         # Section ID from extraction

# Required: Synthesis progress
synthesis:
  status: enum         # "not_started" | "in_progress" | "draft_complete" | "final"
  output_path: string  # Where consolidated doc will be/is written
  sections_complete:   # Track section-by-section progress
    - section_id: string     # From extraction.canonical_sections
      status: enum           # "pending" | "drafted" | "reviewed" | "final"
      draft_location: string # Line range in output or temp location

  # For in-progress work
  current_section: string    # Section ID being worked on (null if between sections)
  notes: string             # Free-form notes for next agent

# Optional: Review tracking
review:
  reviewer: string     # Who reviewed (null if not reviewed)
  reviewed_at: string  # ISO 8601 timestamp
  status: enum         # "pending" | "approved" | "changes_requested"
  feedback:            # Specific feedback items
    - section: string  # Section ID
      issue: string    # What needs attention
      severity: enum   # "blocking" | "suggestion"

# Required: Activity log (append-only)
activity_log:
  - timestamp: string  # ISO 8601
    agent: string      # Who performed the action
    action: string     # What was done
    details: string    # Additional context

# Optional: Dependencies on other topics
dependencies:
  - topic_id: string   # Other topic this depends on
    reason: string     # Why the dependency exists
    status: enum       # "satisfied" | "pending" | "blocking"
```

---

## Validation Rules

### Required Fields

| Field | Rule |
|-------|------|
| `schema_version` | Must be semantic version string |
| `topic.id` | Must be kebab-case, match extraction topic.id |
| `status.phase` | Must be valid phase enum value |
| `status.state` | Must be valid state for the phase |
| `sources` | Must have at least one entry |
| `extraction.path` | Must point to existing extraction file |
| `concepts` | Must have at least one entry after Phase 1 |
| `synthesis.status` | Must be valid synthesis status enum |
| `activity_log` | Must have at least one entry (creation) |

### Enum Constraints

```yaml
phase:
  - discovery      # Phase 0: Finding and cataloging sources
  - extraction     # Phase 1: Creating extraction artifact
  - synthesis      # Phase 2: Writing consolidated document
  - review         # Phase 3: Validation and approval
  - complete       # Phase 4: Done, monitoring for staleness

state:
  # Discovery phase states
  - scanning       # Looking for relevant files
  - cataloging     # Building manifest entry
  - mapped         # Manifest complete, ready for extraction

  # Extraction phase states
  - reading        # Ingesting source files
  - analyzing      # Identifying sections and conflicts
  - resolving      # Working through conflicts
  - extracted      # Extraction artifact complete

  # Synthesis phase states
  - planning       # Determining document structure
  - drafting       # Writing sections
  - integrating    # Connecting sections, adding transitions
  - polishing      # Final edits and formatting
  - drafted        # Draft complete, ready for review

  # Review phase states
  - pending_review # Waiting for reviewer
  - in_review      # Actively being reviewed
  - revising       # Addressing feedback
  - approved       # Review passed

  # Complete phase states
  - published      # Document in final location
  - monitoring     # Watching for source changes

source_status:
  - current        # Hash matches, no re-reading needed
  - stale          # Hash changed, re-extraction may be needed
  - new            # File added since last checkpoint
  - deleted        # File removed since last checkpoint

synthesis_status:
  - not_started    # Haven't begun writing
  - in_progress    # Actively drafting
  - draft_complete # All sections drafted
  - final          # Approved and published

section_status:
  - pending        # Not started
  - drafted        # Initial draft written
  - reviewed       # Reviewer has seen it
  - final          # Approved, no more changes

confidence:
  - high           # Clear, unambiguous understanding
  - medium         # Mostly clear, some uncertainty
  - low            # Significant gaps or confusion

review_status:
  - pending        # Awaiting review
  - approved       # Passed review
  - changes_requested  # Needs revision

dependency_status:
  - satisfied      # Dependent topic is complete
  - pending        # Dependent topic not yet complete
  - blocking       # Cannot proceed until dependency resolved
```

### Business Rules

1. **Phase Progression**: Phases must progress in order: discovery -> extraction -> synthesis -> review -> complete
2. **State Consistency**: State must be valid for current phase
3. **Source Tracking**: All sources in extraction must appear in checkpoint sources
4. **Hash Verification**: If any source hash differs from extraction, status should be "stale"
5. **Conflict Gate**: Cannot enter synthesis phase if `extraction.conflicts_pending > 0` with blocking severity
6. **Activity Logging**: Every state change must add an activity_log entry
7. **Concept Population**: `concepts` array must be populated before leaving extraction phase

---

## Example

```yaml
schema_version: "1.0"

topic:
  id: "settings-merge"
  name: "Settings Merge Algorithm"

status:
  phase: synthesis
  state: drafting
  blocked_by: null
  last_activity: "2024-12-25T14:30:00Z"

sources:
  - path: ".claude/skills/doc-ecosystem/SKILL.md"
    hash: "a1b2c3d4e5f6..."
    last_read: "2024-12-25T10:30:00Z"
    status: current
  - path: "docs/design/TDD-0042-settings.md"
    hash: "b2c3d4e5f6g7..."
    last_read: "2024-12-25T10:30:00Z"
    status: current

extraction:
  path: ".consolidation/extraction-settings-merge.yaml"
  hash: "c3d4e5f6g7h8..."
  created_at: "2024-12-25T10:30:00Z"
  conflicts_resolved: 1
  conflicts_pending: 0

concepts:
  - name: "tier precedence"
    understanding: "Settings merge in strict order: skeleton < project < team < user. Higher tiers override lower for scalars."
    confidence: high
    source_refs:
      - "tier-precedence"
  - name: "array merge strategies"
    understanding: "Arrays can merge via replace (default), append, or union. Strategy is configurable per-key."
    confidence: high
    source_refs:
      - "array-strategies"
  - name: "recursive object merge"
    understanding: "Nested objects merge recursively, applying tier precedence at each level."
    confidence: medium
    source_refs:
      - "tier-precedence"

synthesis:
  status: in_progress
  output_path: "docs/consolidated/settings-merge.md"
  sections_complete:
    - section_id: "tier-precedence"
      status: drafted
      draft_location: "lines 15-45"
    - section_id: "array-strategies"
      status: pending
      draft_location: null
  current_section: "array-strategies"
  notes: "Tier precedence section complete. Starting array strategies. Consider adding a decision tree diagram."

review:
  reviewer: null
  reviewed_at: null
  status: pending
  feedback: []

activity_log:
  - timestamp: "2024-12-25T10:00:00Z"
    agent: "discovery-agent"
    action: "checkpoint_created"
    details: "Initialized checkpoint for settings-merge topic"
  - timestamp: "2024-12-25T10:30:00Z"
    agent: "extractor-agent"
    action: "extraction_complete"
    details: "Created extraction with 2 sections, 1 conflict resolved"
  - timestamp: "2024-12-25T11:00:00Z"
    agent: "synthesis-agent"
    action: "phase_started"
    details: "Beginning synthesis, planning document structure"
  - timestamp: "2024-12-25T14:00:00Z"
    agent: "synthesis-agent"
    action: "section_drafted"
    details: "Completed draft of tier-precedence section"
  - timestamp: "2024-12-25T14:30:00Z"
    agent: "synthesis-agent"
    action: "section_started"
    details: "Beginning array-strategies section"

dependencies: []
```

---

## Usage Notes

### For Any Agent Resuming Work

1. **Read checkpoint first** - understand current state before proceeding
2. **Verify source freshness** - check hashes against actual files
3. **Load concepts** - use recorded understanding as starting point
4. **Check for blockers** - respect `blocked_by` and dependency status
5. **Continue from current state** - don't restart completed work

### Staleness Handling

When source hashes don't match:

```yaml
# Stale source detected
sources:
  - path: "docs/design/TDD-0042-settings.md"
    hash: "old_hash..."      # From checkpoint
    status: stale            # Computed by comparing to actual file

# Decision tree:
# 1. If in discovery/extraction phase: re-extract that source
# 2. If in synthesis phase: check if stale section affects current work
# 3. If in review/complete: flag for re-consolidation
```

### Activity Log Best Practices

- Log every phase/state transition
- Log significant decisions (not minor edits)
- Include agent identifier for traceability
- Keep details concise but specific
- Never delete log entries (append-only)

### Checkpoint Location

```
.consolidation/
  checkpoint-settings-merge.yaml     # This file
  checkpoint-hook-lifecycle.yaml     # Another topic
  extraction-settings-merge.yaml     # Related extraction
  extraction-hook-lifecycle.yaml     # Related extraction
```

### Recovery Scenarios

| Scenario | Action |
|----------|--------|
| Agent crash mid-section | Resume from `current_section`, check `notes` |
| Source file changed | Mark stale, re-extract affected sections |
| Conflict discovered late | Return to extraction phase, update conflicts |
| Review rejected | Set state to "revising", address feedback |
| Dependency blocked | Wait or escalate, do not proceed |
