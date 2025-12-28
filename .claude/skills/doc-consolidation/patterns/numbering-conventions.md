# Numbering Conventions

> **Purpose**: Standardized numbering scheme for consolidated documents to ensure consistent organization, clear hierarchy, and predictable file discovery.

## Design Principles

1. **Semantic Ranges**: Number ranges convey document category
2. **Room for Growth**: Gaps allow future insertions without renumbering
3. **Sort Stability**: Numeric prefix ensures consistent alphabetical ordering
4. **Self-Documenting**: Number itself signals document importance and type

---

## Numbering Scheme Overview

```
000-099: Reserved / System
100-199: Core / Foundational
200-299: Features
300-399: Operations
400-499: Integration
500-599: Security
600-699: Performance
700-799: (Reserved for expansion)
800-899: Guides / How-To
900-999: Reference / Appendix
```

---

## Range Definitions

### 000-099: Reserved / System

**Purpose**: System-level configuration and meta-documentation.

| Range | Category | Examples |
|-------|----------|----------|
| 000-009 | Entry points | `000-index.md`, `001-quick-start.md` |
| 010-019 | Configuration | `010-settings-overview.md` |
| 020-049 | (Reserved) | Future system needs |
| 050-099 | Meta | `050-consolidation-log.md`, `099-changelog.md` |

**Naming Pattern**: `0XX-{descriptor}.md`

### 100-199: Core / Foundational

**Purpose**: Essential concepts that other documents depend on. Read these first.

| Range | Category | Examples |
|-------|----------|----------|
| 100-119 | Architecture | `100-system-architecture.md`, `110-data-model.md` |
| 120-139 | Core concepts | `120-tier-precedence.md`, `125-merge-algorithm.md` |
| 140-159 | Workflows | `140-agent-workflow.md`, `145-session-lifecycle.md` |
| 160-179 | Interfaces | `160-cli-interface.md`, `165-api-contracts.md` |
| 180-199 | (Buffer) | Room for foundational additions |

**Naming Pattern**: `1XX-{core-concept}.md`

**Assignment Criteria**:
- Other documents reference this content
- Understanding this is prerequisite for other topics
- Changes here have widespread impact

### 200-299: Features

**Purpose**: Specific capabilities and feature documentation.

| Range | Category | Examples |
|-------|----------|----------|
| 200-219 | Settings/Config | `200-settings-merge.md`, `210-config-tiers.md` |
| 220-239 | Hooks | `220-hook-lifecycle.md`, `225-custom-hooks.md` |
| 240-259 | Agents | `240-agent-routing.md`, `245-agent-creation.md` |
| 260-279 | Skills | `260-skill-architecture.md`, `265-skill-discovery.md` |
| 280-299 | (Buffer) | Room for feature additions |

**Naming Pattern**: `2XX-{feature-name}.md`

**Assignment Criteria**:
- Describes a distinct capability
- Can be understood independently (after core)
- Has clear boundaries and use cases

### 300-399: Operations

**Purpose**: Day-to-day operational procedures and runbooks.

| Range | Category | Examples |
|-------|----------|----------|
| 300-319 | Sync operations | `300-cem-sync.md`, `310-conflict-resolution.md` |
| 320-339 | Migration | `320-migration-runbook.md`, `325-version-upgrade.md` |
| 340-359 | Maintenance | `340-health-checks.md`, `345-cleanup-procedures.md` |
| 360-379 | Recovery | `360-disaster-recovery.md`, `365-rollback-procedures.md` |
| 380-399 | (Buffer) | Room for operational additions |

**Naming Pattern**: `3XX-{operation-name}.md`

**Assignment Criteria**:
- Describes "how to do X" operationally
- Involves running commands or procedures
- Has prerequisites and verification steps

### 400-499: Integration

**Purpose**: Connecting with external systems and satellites.

| Range | Category | Examples |
|-------|----------|----------|
| 400-419 | Satellite integration | `400-satellite-onboarding.md`, `410-satellite-config.md` |
| 420-439 | CI/CD | `420-github-actions.md`, `425-pre-commit-hooks.md` |
| 440-459 | IDE integration | `440-vscode-setup.md`, `445-cursor-integration.md` |
| 460-479 | External tools | `460-external-apis.md` |
| 480-499 | (Buffer) | Room for integration additions |

**Naming Pattern**: `4XX-{integration-target}.md`

**Assignment Criteria**:
- Involves external systems or tools
- Describes connection/configuration with other software
- May have external dependencies

### 500-599: Security

**Purpose**: Security considerations, permissions, and access control.

| Range | Category | Examples |
|-------|----------|----------|
| 500-519 | Access control | `500-permissions-model.md`, `510-role-based-access.md` |
| 520-539 | Secrets | `520-secret-management.md`, `525-credential-rotation.md` |
| 540-559 | Auditing | `540-audit-logging.md`, `545-compliance.md` |
| 560-599 | (Buffer) | Room for security additions |

**Naming Pattern**: `5XX-{security-topic}.md`

**Assignment Criteria**:
- Involves authentication, authorization, or access
- Discusses sensitive data handling
- Has compliance or security implications

### 600-699: Performance

**Purpose**: Performance optimization, tuning, and monitoring.

| Range | Category | Examples |
|-------|----------|----------|
| 600-619 | Token efficiency | `600-token-optimization.md`, `610-context-budgeting.md` |
| 620-639 | Caching | `620-cache-strategies.md` |
| 640-659 | Monitoring | `640-metrics-collection.md`, `645-alerting.md` |
| 660-699 | (Buffer) | Room for performance additions |

**Naming Pattern**: `6XX-{performance-topic}.md`

**Assignment Criteria**:
- Focuses on speed, efficiency, or resource usage
- Includes benchmarks or metrics
- Discusses optimization techniques

### 700-799: Reserved

**Purpose**: Reserved for future category expansion.

**Do not assign numbers in this range without team discussion.**

### 800-899: Guides / How-To

**Purpose**: Task-oriented guides for specific scenarios.

| Range | Category | Examples |
|-------|----------|----------|
| 800-819 | Getting started | `800-first-time-setup.md`, `810-your-first-agent.md` |
| 820-839 | Common tasks | `820-adding-a-hook.md`, `825-creating-a-skill.md` |
| 840-859 | Advanced usage | `840-custom-workflows.md`, `845-extending-cem.md` |
| 860-879 | Troubleshooting | `860-common-errors.md`, `865-debugging-sync.md` |
| 880-899 | (Buffer) | Room for guide additions |

**Naming Pattern**: `8XX-{task-or-goal}.md`

**Assignment Criteria**:
- Written from user perspective ("How do I...")
- Task-focused with clear outcome
- May reference multiple other documents

### 900-999: Reference / Appendix

**Purpose**: Reference material, schemas, glossaries, and appendices.

| Range | Category | Examples |
|-------|----------|----------|
| 900-919 | Schemas | `900-settings-schema.md`, `910-manifest-schema.md` |
| 920-939 | API reference | `920-cli-reference.md`, `925-hook-api.md` |
| 940-959 | Glossary | `940-glossary.md`, `945-acronyms.md` |
| 960-979 | Examples | `960-example-configs.md`, `965-sample-workflows.md` |
| 980-999 | Appendices | `980-version-history.md`, `999-contributors.md` |

**Naming Pattern**: `9XX-{reference-type}.md`

**Assignment Criteria**:
- Lookup/reference material (not narrative)
- Technical specifications or schemas
- Supporting material for other documents

---

## Number Assignment Process

### Step 1: Determine Category

```
Document: "How settings from multiple tiers combine"
  |
  v
Is it a core concept others depend on?
  |-- Yes --> 100-199 range
  |
Is it a feature description?
  |-- Yes --> 200-299 range (Settings = 200-219)
  |
Is it an operational procedure?
  |-- Yes --> 300-399 range
  |
Is it a how-to guide?
  |-- Yes --> 800-899 range
  |
Is it reference material?
  |-- Yes --> 900-999 range
```

### Step 2: Select Specific Number

Within the category:

1. Check existing numbers in that range
2. Leave gaps of 5-10 between related documents
3. Use lower numbers for more fundamental topics
4. Reserve round numbers (X00, X10, X20) for major topics

**Example Assignment:**

```yaml
topic: "settings-merge"
category: "Features - Settings/Config"
range: 200-219

existing_in_range:
  - 200-settings-overview.md
  - 205-tier-precedence.md

decision: 210-merge-algorithm.md
rationale: "Builds on 205, leaves room for 206-209 additions"
```

### Step 3: Document the Assignment

```yaml
# In MANIFEST.yaml or consolidation log
assignments:
  - number: 210
    file: "210-merge-algorithm.md"
    topic: "settings-merge"
    assigned_by: "synthesis-agent"
    assigned_at: "2024-12-25T14:00:00Z"
    rationale: "Core algorithm documentation for settings feature"
```

---

## Renumbering Policy

### When to Renumber

- **Never** for live/published documentation
- **Acceptable** during consolidation (before publication)
- **Required** if semantic category changes

### Renumbering Procedure

1. Update all internal cross-references
2. Create redirect from old number (if published)
3. Update MANIFEST and indexes
4. Note in changelog

---

## Examples

### Complete Consolidated Documentation Set

```
docs/consolidated/
├── 000-index.md                    # Entry point
├── 001-quick-start.md              # 5-minute getting started
│
├── 100-system-architecture.md      # Core: How it all fits together
├── 120-tier-precedence.md          # Core: The precedence model
│
├── 200-settings-overview.md        # Feature: Settings introduction
├── 205-tier-precedence.md          # Feature: Detailed tier docs
├── 210-merge-algorithm.md          # Feature: How merging works
├── 220-hook-lifecycle.md           # Feature: Hook system
├── 240-agent-routing.md            # Feature: Agent system
│
├── 300-cem-sync.md                 # Operations: Running sync
├── 320-migration-runbook.md        # Operations: Version migration
│
├── 400-satellite-onboarding.md     # Integration: Adding satellites
│
├── 800-first-time-setup.md         # Guide: Initial setup
├── 820-adding-a-hook.md            # Guide: Hook creation
├── 860-common-errors.md            # Guide: Troubleshooting
│
├── 900-settings-schema.md          # Reference: JSON schema
├── 920-cli-reference.md            # Reference: CLI commands
└── 940-glossary.md                 # Reference: Term definitions
```

### Number Selection for New Document

**Scenario**: Creating consolidated doc for "hook event types"

```yaml
analysis:
  topic: "hook-event-types"
  content: "Documents all hook events (SessionStart, PreToolUse, etc.)"

  is_core: false  # Not a prerequisite for other docs
  is_feature: true  # Describes hook capability
  is_operations: false  # Not a procedure
  is_guide: false  # Not task-oriented
  is_reference: partially  # Has reference elements

decision:
  primary: 225-hook-events.md  # In feature range (220-239 = Hooks)
  alternative: 925-hook-event-reference.md  # If purely reference

rationale: |
  Hooks range is 220-239. Existing: 220-hook-lifecycle.md.
  Hook events build on lifecycle, so 225 is appropriate.
  Leave 221-224 for potential hook-lifecycle subsections.
```

---

## Validation Rules

- [ ] Numbers are unique within the documentation set
- [ ] Numbers fall within appropriate semantic range
- [ ] Gaps exist for future expansion (minimum 5 between documents)
- [ ] Round numbers (X00, X10) reserved for major topics
- [ ] Cross-references use numbers, not filenames (for stability)
- [ ] MANIFEST tracks all number assignments
