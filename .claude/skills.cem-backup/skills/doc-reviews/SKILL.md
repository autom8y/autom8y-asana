---
name: doc-reviews
description: "Documentation audit, review, and architecture templates for doc-team workflows. Use when: conducting documentation audits, planning information architecture, reviewing documentation accuracy, planning migrations, creating documentation briefs. Triggers: doc audit, documentation review, information architecture, migration plan, content brief, documentation quality, staleness analysis."
---

# Documentation Reviews & Audits

> **Status**: Extracted from documentation skill (Session N)

## Core Principles

### Documentation Health
Documentation must be accurate, up-to-date, and discoverable. Audit regularly to identify staleness, redundancy, and gaps. Architecture decisions should support findability and maintainability.

### Single Source of Truth
Each piece of knowledge has exactly one canonical location. Audits should identify and resolve redundancy. Information architecture should prevent duplication through clear taxonomy.

### Living Documentation
Documentation is never "done." Reviews validate accuracy against current code. Audits detect drift. Architecture evolves as the product grows.

---

## Templates

## Documentation Audit Report {#documentation-audit-report}

```markdown
# Documentation Audit Report
Generated: [timestamp]
Scope: [directories audited]

## Executive Summary
- Total documentation artifacts: [N]
- Current/healthy: [N] ([%])
- Stale (needs update): [N] ([%])
- Orphaned (references dead code): [N] ([%])
- Redundant (consolidation candidates): [N] pairs
- Missing (identified gaps): [N]

## Critical Issues (Immediate Attention)
[Docs that actively mislead or describe non-existent behavior]

## Staleness Report
| File | Last Updated | Related Code Changed | Staleness Score |
|------|--------------|---------------------|-----------------|
| ...  | ...          | ...                 | ...             |

## Redundancy Clusters
[Groups of docs covering the same topic]

## Gap Analysis
| Area | Expected Documentation | Status |
|------|----------------------|--------|
| ...  | ...                  | ...    |

## Recommendations
[Prioritized list of actions for Information Architect]
```

---

## Information Architecture Specification {#information-architecture-spec}

```markdown
# Documentation Information Architecture
Version: [N]
Date: [timestamp]

## Taxonomy Overview
[Visual representation of category hierarchy]

## Directory Structure
```
[Target directory tree with annotations]
```

## Category Definitions
### [Category Name]
- **Purpose:** [What this category contains]
- **Audience:** [Who reads this]
- **Entry point:** [Index page or primary navigation]
- **Examples:** [Representative documents]

## Naming Conventions
[File naming, title conventions, metadata requirements]

## Navigation Design
[Entry points, cross-reference strategy, search optimization]
```

---

## Migration Plan {#migration-plan}

```markdown
# Documentation Migration Plan

## Phase 1: Structure Creation
[Create new directories and index pages]

## Phase 2: Content Migration
| Current Location | Action | Target Location | Notes |
|-----------------|--------|-----------------|-------|
| ...             | Move   | ...             | ...   |
| ...             | Merge  | ...             | Source for consolidation |
| ...             | Retire | N/A             | Archive with redirect |

## Phase 3: Consolidation Work
[Specific consolidation tasks for Tech Writer]

## Phase 4: Cross-Reference Updates
[Links that need updating after moves]

## Phase 5: Retirement
[Old locations to remove after migration complete]
```

---

## Content Brief {#content-brief}

```markdown
# Content Brief: [Document Title]

## Location
Path: docs/[category]/[filename].md

## Purpose
[Why this document needs to exist]

## Audience
[Primary readers and their context]

## Scope
- Include: [topics to cover]
- Exclude: [topics covered elsewhere]

## Related Documentation
- [Links to related docs that should cross-reference]

## Source Material
- [Existing content to draw from, if any]

## Priority
[Critical/High/Medium/Low with rationale]
```

---

## Documentation Review Report {#documentation-review-report}

```markdown
# Documentation Review Report
Document: [path/to/document.md]
Reviewer: Doc Reviewer Agent
Date: [timestamp]

## Summary
- **Status:** [Approved / Needs Revision / Needs Rewrite]
- **Critical Issues:** [N]
- **Major Issues:** [N]
- **Minor Issues:** [N]

## Critical Issues
### [Issue Title]
**Location:** Line [N], Section "[Section Name]"
**Documentation states:**
> [Quoted text from doc]

**Actual behavior:**
[Description of actual behavior with code reference]
```
// Code from [file:line]
[Relevant code snippet]
```

**Suggested correction:**
> [Corrected text]

## Major Issues
[Same format as critical]

## Minor Issues
[Same format, may be briefer]

## Cross-Reference Validation
| Reference | Target | Status |
|-----------|--------|--------|
| [link text] | [target path] | Valid / Broken / Outdated |

## Code Example Validation
| Example Location | Status | Notes |
|-----------------|--------|-------|
| Line [N] | Valid / Invalid | [Details] |

## Approval Status
[ ] Approved for publication
[ ] Approved with minor corrections (can be fixed post-publish)
[ ] Requires revision before publication
[ ] Requires significant rewrite
```

---

## Usage Patterns

### Conducting a Documentation Audit
1. Use Documentation Audit Report template
2. Scan docs directory structure
3. Compare doc timestamps with code changes
4. Identify redundancy through content similarity
5. Flag orphaned references (links to deleted code)
6. Produce prioritized recommendation list

### Planning Information Architecture
1. Use Information Architecture Specification template
2. Define taxonomy based on audience and purpose
3. Design directory structure for discoverability
4. Establish naming conventions
5. Plan navigation and entry points

### Reviewing Documentation Accuracy
1. Use Documentation Review Report template
2. Compare doc claims against actual code behavior
3. Validate cross-references and links
4. Test code examples
5. Categorize issues by severity (Critical/Major/Minor)
6. Provide approval status and suggested corrections

### Planning Documentation Migration
1. Use Migration Plan template
2. Phase 1: Create target structure
3. Phase 2: Map source to target (move/merge/retire)
4. Phase 3: Consolidation work items
5. Phase 4: Update cross-references
6. Phase 5: Clean up old locations

### Creating Documentation Briefs
1. Use Content Brief template
2. Define document location and purpose
3. Identify target audience
4. Scope inclusion/exclusion boundaries
5. Link related documentation
6. Assign priority with rationale

---

## Related Resources

- **documentation** skill: PRD, TDD, ADR, Test Plan templates
- **standards** skill: Project structure and conventions
- **10x-workflow** skill: Agent coordination for doc teams
