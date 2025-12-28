# Team Pack Schema

> Complete schema documentation for workflow.yaml files used in team pack definitions.

## Overview

A **team pack** is a self-contained configuration that defines a specialized AI team with:
- Named agents with specific roles
- A structured workflow defining how agents collaborate
- Complexity-based phase selection for right-sized execution
- Command mappings for slash-command integration

Team packs live in the roster repository under `teams/<team-name>/` and are synced to satellites via the CEM (Claude Ecosystem Manager).

## File Structure

```
teams/<team-name>/
├── workflow.yaml      # Required: Team configuration and workflow definition
├── workflow.md        # Required: Human-readable workflow documentation
├── README.md          # Required: Team overview and when-to-use guidance
├── agents/            # Required: Agent definition files
│   ├── agent1.md
│   ├── agent2.md
│   └── ...
└── commands/          # Optional: Team-specific slash commands
    ├── command1.md
    └── ...
```

### Directory Naming Convention

The directory name must:
- Be lowercase with hyphens (kebab-case)
- End with `-pack` suffix
- Match the `name` field in `workflow.yaml`

**Valid**: `10x-dev-pack`, `ecosystem-pack`, `security-pack`
**Invalid**: `10xDevPack`, `ecosystem_pack`, `myteam`

---

## workflow.yaml Schema

### Top-Level Fields

#### name (required)

The unique identifier for this team pack.

| Property | Value |
|----------|-------|
| **Type** | `string` |
| **Constraints** | Lowercase, hyphenated (kebab-case), must end with `-pack` |
| **Must Match** | Parent directory name |

```yaml
# Good
name: 10x-dev-pack

# Bad
name: 10xDevPack     # No camelCase
name: my_team        # No underscores, missing -pack suffix
```

---

#### version (optional)

Semantic version for the team pack schema.

| Property | Value |
|----------|-------|
| **Type** | `string` |
| **Format** | Semantic versioning (`MAJOR.MINOR.PATCH`) |
| **Default** | None (implicit v1.0.0) |

```yaml
version: "1.0.0"
version: "2.1.0"
```

**When to increment**:
- MAJOR: Breaking changes to phase structure or agent roles
- MINOR: New optional fields, additional phases
- PATCH: Documentation updates, bug fixes

---

#### workflow_type (required)

Defines how phases execute relative to each other.

| Property | Value |
|----------|-------|
| **Type** | `enum` |
| **Values** | `sequential`, `parallel`, `hybrid` |
| **Default** | None (must specify) |

```yaml
workflow_type: sequential  # Most common
workflow_type: parallel    # For independent phases
workflow_type: hybrid      # Mix of sequential and parallel
```

**Type descriptions**:

| Type | Behavior | Use When |
|------|----------|----------|
| `sequential` | Phases execute in order; each depends on previous | Standard workflows with artifact dependencies |
| `parallel` | Multiple phases can execute simultaneously | Independent analysis tasks |
| `hybrid` | Mix specified per-phase | Complex workflows with parallel sub-trees |

---

#### description (required)

Human-readable description of what this team does.

| Property | Value |
|----------|-------|
| **Type** | `string` |
| **Format** | Brief phrase describing the lifecycle |
| **Max Length** | ~100 characters recommended |

```yaml
description: Full development lifecycle (PRD -> TDD -> Code -> QA)
description: Ecosystem infrastructure lifecycle (Gap Analysis -> Design -> Implementation -> Documentation -> Validation)
```

**Pattern**: Describe as `<Domain> lifecycle (<Phase1> -> <Phase2> -> ...)`

---

### entry_point (required)

Defines where the workflow begins and what initial artifact is produced.

| Property | Value |
|----------|-------|
| **Type** | `object` |
| **Required Fields** | `agent`, `artifact` |

```yaml
entry_point:
  agent: requirements-analyst
  artifact:
    type: prd
    path_template: docs/requirements/PRD-{slug}.md
```

#### entry_point.agent (required)

| Property | Value |
|----------|-------|
| **Type** | `string` |
| **Constraints** | Must match a file in `agents/` directory (without `.md` extension) |
| **Must Equal** | `phases[0].agent` |

```yaml
entry_point:
  agent: ecosystem-analyst  # Must have agents/ecosystem-analyst.md
```

#### entry_point.artifact (required)

| Property | Value |
|----------|-------|
| **Type** | `object` |
| **Required Fields** | `type`, `path_template` |

#### entry_point.artifact.type (required)

| Property | Value |
|----------|-------|
| **Type** | `string` |
| **Constraints** | Lowercase, hyphenated identifier |
| **Must Equal** | `phases[0].produces` |

```yaml
artifact:
  type: prd
  type: gap-analysis
  type: threat-model
```

#### entry_point.artifact.path_template (required)

| Property | Value |
|----------|-------|
| **Type** | `string` |
| **Format** | Path with `{slug}` placeholder |
| **Constraints** | Must include `{slug}` placeholder |

```yaml
artifact:
  path_template: docs/requirements/PRD-{slug}.md
  path_template: docs/ecosystem/GAP-{slug}.md
  path_template: docs/security/THREAT-{slug}.md
```

**Template variables**:
- `{slug}`: Kebab-case identifier for the work item (e.g., `user-auth-flow`)

---

### phases (required)

Ordered list of workflow phases defining the execution pipeline.

| Property | Value |
|----------|-------|
| **Type** | `array[object]` |
| **Min Items** | 1 |
| **Constraint** | Last phase must have `next: null` |

```yaml
phases:
  - name: requirements
    agent: requirements-analyst
    produces: prd
    next: design

  - name: design
    agent: architect
    produces: tdd
    next: implementation
    condition: "complexity >= MODULE"

  - name: implementation
    agent: principal-engineer
    produces: code
    next: validation

  - name: validation
    agent: qa-adversary
    produces: test-plan
    next: null  # Terminal phase
```

#### phases[].name (required)

| Property | Value |
|----------|-------|
| **Type** | `string` |
| **Constraints** | Lowercase, hyphenated, unique within phases |

```yaml
- name: requirements
- name: design
- name: implementation
- name: validation
```

**Common phase names by team type**:

| Team Type | Typical Phases |
|-----------|----------------|
| Development | requirements, design, implementation, validation |
| Documentation | audit, architecture, writing, review |
| Security | threat-modeling, compliance-design, penetration-testing, security-review |
| Infrastructure | analysis, design, implementation, documentation, validation |

---

#### phases[].agent (required)

| Property | Value |
|----------|-------|
| **Type** | `string` |
| **Constraints** | Must match file in `agents/` directory (without `.md`) |

```yaml
- name: design
  agent: architect  # Requires agents/architect.md
```

---

#### phases[].produces (required)

| Property | Value |
|----------|-------|
| **Type** | `string` |
| **Constraints** | Lowercase, hyphenated artifact type identifier |

```yaml
- name: design
  produces: tdd

- name: validation
  produces: test-plan
```

**Common artifact types**:

| Artifact Type | Description |
|---------------|-------------|
| `prd` | Product Requirements Document |
| `tdd` | Technical Design Document |
| `code` | Implementation code |
| `test-plan` | Test specifications |
| `gap-analysis` | Problem diagnosis |
| `context-design` | Architecture blueprint |

---

#### phases[].next (required)

| Property | Value |
|----------|-------|
| **Type** | `string` or `null` |
| **Constraints** | Must reference valid phase name, or `null` for terminal phase |

```yaml
phases:
  - name: design
    next: implementation  # Must match a phase name

  - name: validation
    next: null  # Terminal phase
```

**Validation Rules**:
- Every `next` value except `null` must match a `phases[].name`
- Exactly one phase must have `next: null`
- No circular references allowed

---

#### phases[].condition (optional)

| Property | Value |
|----------|-------|
| **Type** | `string` |
| **Format** | Condition expression |
| **Default** | Always include phase |

```yaml
- name: design
  condition: "complexity >= MODULE"

- name: documentation
  condition: "complexity >= MODULE"

- name: coordination
  condition: "complexity >= SERVICE"
```

**Condition syntax**:
- `complexity >= <LEVEL>`: Phase included when complexity is at or above specified level
- `complexity == <LEVEL>`: Phase included only at exact complexity level

**Note**: Complexity levels are defined in `complexity_levels` section.

---

### complexity_levels (required)

Defines team-specific complexity tiers that control which phases execute.

| Property | Value |
|----------|-------|
| **Type** | `array[object]` |
| **Min Items** | 1 |
| **Order** | Ascending by scope (smallest to largest) |

```yaml
complexity_levels:
  - name: SCRIPT
    scope: "Single file, <200 LOC"
    phases: [requirements, implementation, validation]

  - name: MODULE
    scope: "Multiple files, <2000 LOC"
    phases: [requirements, design, implementation, validation]

  - name: SERVICE
    scope: "APIs, persistence"
    phases: [requirements, design, implementation, validation]

  - name: PLATFORM
    scope: "Multi-service"
    phases: [requirements, design, implementation, validation]
```

#### complexity_levels[].name (required)

| Property | Value |
|----------|-------|
| **Type** | `string` |
| **Constraints** | UPPERCASE, unique within levels |

**Common complexity level names by domain**:

| Domain | Levels (small to large) |
|--------|-------------------------|
| Development | SCRIPT, MODULE, SERVICE, PLATFORM |
| Documentation | PAGE, SECTION, SITE |
| Security | PATCH, FEATURE, SYSTEM |
| Infrastructure | PATCH, MODULE, SYSTEM, MIGRATION |
| Strategy | TACTICAL, STRATEGIC, TRANSFORMATION |

---

#### complexity_levels[].scope (required)

| Property | Value |
|----------|-------|
| **Type** | `string` |
| **Format** | Human-readable description of what this level covers |

```yaml
- name: SCRIPT
  scope: "Single file, <200 LOC"

- name: SYSTEM
  scope: "Multi-system change affecting CEM + skeleton + roster"
```

---

#### complexity_levels[].phases (required)

| Property | Value |
|----------|-------|
| **Type** | `array[string]` |
| **Constraints** | All items must reference valid phase names |

```yaml
- name: SCRIPT
  phases: [requirements, implementation, validation]  # Skips design

- name: MODULE
  phases: [requirements, design, implementation, validation]  # Full pipeline
```

**Rules**:
- Higher complexity levels typically include all lower-level phases plus additional ones
- The `phases` array defines which phases execute at this complexity level
- Must not reference phases that don't exist in `phases[]`

---

### commands (optional)

Team-specific slash commands synced to satellite.

| Property | Value |
|----------|-------|
| **Type** | `array[object]` |
| **Default** | Empty (no team-specific commands) |

```yaml
commands:
  - name: consolidate
    file: consolidate.md
    description: "Consolidate documentation into numbered artifacts"
    primary_agent: ecosystem-analyst
    workflow_phase: all
```

#### commands[].name (required)

| Property | Value |
|----------|-------|
| **Type** | `string` |
| **Constraints** | Lowercase, no spaces (becomes `/name`) |

```yaml
- name: consolidate  # Invoked as /consolidate
- name: security-scan  # Invoked as /security-scan
```

---

#### commands[].file (required)

| Property | Value |
|----------|-------|
| **Type** | `string` |
| **Constraints** | Must exist in `commands/` directory |

```yaml
- name: consolidate
  file: consolidate.md  # Must exist: commands/consolidate.md
```

---

#### commands[].description (required)

| Property | Value |
|----------|-------|
| **Type** | `string` |
| **Format** | Brief description for help output |

```yaml
- name: consolidate
  description: "Consolidate documentation into numbered artifacts"
```

---

#### commands[].primary_agent (optional)

| Property | Value |
|----------|-------|
| **Type** | `string` |
| **Constraints** | Must match agent in team's `agents/` directory |
| **Default** | Entry point agent |

```yaml
- name: consolidate
  primary_agent: ecosystem-analyst
```

---

#### commands[].workflow_phase (optional)

| Property | Value |
|----------|-------|
| **Type** | `string` |
| **Values** | Phase name or `all` |
| **Default** | `all` |

```yaml
- name: consolidate
  workflow_phase: all  # Orchestrates full pipeline

- name: quick-scan
  workflow_phase: analysis  # Only runs analysis phase
```

---

### Agent Role Comments (optional but recommended)

Comment block mapping standard commands to team agents.

```yaml
# Agent roles for command mapping:
# /architect  -> architect
# /build      -> principal-engineer
# /qa         -> qa-adversary
# /hotfix     -> principal-engineer (fast path)
# /code-review -> qa-adversary (review mode)
```

**Purpose**: Documents which team agent handles each standard slash command, enabling consistent behavior across different team packs.

---

## Validation Rules

### Required File Validation

- [ ] `workflow.yaml` exists in team directory
- [ ] `workflow.md` exists in team directory
- [ ] `README.md` exists in team directory
- [ ] `agents/` directory exists with at least one `.md` file

### Field Validation

- [ ] `name` matches directory name
- [ ] `workflow_type` is one of: `sequential`, `parallel`, `hybrid`
- [ ] `entry_point.agent` matches `phases[0].agent`
- [ ] `entry_point.artifact.type` matches `phases[0].produces`
- [ ] `entry_point.artifact.path_template` contains `{slug}`

### Phase Validation

- [ ] All `phases[].agent` values have corresponding files in `agents/`
- [ ] All `phases[].next` values reference valid phase names or are `null`
- [ ] Exactly one phase has `next: null` (terminal phase)
- [ ] No circular phase references

### Complexity Level Validation

- [ ] All `complexity_levels[].phases` reference valid phase names
- [ ] Complexity level names are unique
- [ ] At least one complexity level defined

### Command Validation (if commands section exists)

- [ ] All `commands[].file` values exist in `commands/` directory
- [ ] All `commands[].primary_agent` values exist in `agents/` directory
- [ ] Command names are unique

---

## Common Patterns

### Pattern: Skip-Phase for Simple Work

Lower complexity levels skip intermediate phases.

```yaml
complexity_levels:
  - name: SCRIPT
    scope: "Single file, <200 LOC"
    phases: [requirements, implementation, validation]  # Skips design

  - name: MODULE
    scope: "Multiple files"
    phases: [requirements, design, implementation, validation]  # Full pipeline
```

**Use when**: Some phases add overhead without value for small changes.

---

### Pattern: Conditional Phase Inclusion

Use `condition` to dynamically include phases based on complexity.

```yaml
phases:
  - name: design
    agent: architect
    produces: tdd
    next: implementation
    condition: "complexity >= MODULE"
```

**Use when**: Phase should be included at certain complexity levels but not others.

---

### Pattern: Domain-Specific Complexity Naming

Name complexity levels to match domain vocabulary.

```yaml
# Security team
complexity_levels:
  - name: PATCH        # Minimal security impact
  - name: FEATURE      # New attack surface
  - name: SYSTEM       # Critical security systems

# Documentation team
complexity_levels:
  - name: PAGE         # Single document
  - name: SECTION      # Multiple related docs
  - name: SITE         # Full documentation site
```

---

### Pattern: Team-Specific Commands

Add commands that make sense only for this team.

```yaml
commands:
  - name: consolidate
    file: consolidate.md
    description: "Consolidate documentation into numbered artifacts"
    primary_agent: ecosystem-analyst
    workflow_phase: all
```

**Use when**: Team has unique workflows that don't fit standard commands.

---

## Anti-Patterns to Avoid

### Anti-Pattern: Name Mismatch

```yaml
# Directory: teams/ecosystem-pack/
name: ecosystemPack  # WRONG: Must match directory name exactly
```

**Fix**: Use `name: ecosystem-pack` to match directory.

---

### Anti-Pattern: Orphan Phases

```yaml
phases:
  - name: analysis
    next: design
  - name: implementation  # ORPHAN: No phase points to this
    next: null
```

**Fix**: Ensure every phase except the first is referenced by another phase's `next` field.

---

### Anti-Pattern: Missing Terminal Phase

```yaml
phases:
  - name: analysis
    next: implementation
  - name: implementation
    next: validation  # ERROR: validation phase doesn't exist
```

**Fix**: Define all referenced phases and ensure exactly one has `next: null`.

---

### Anti-Pattern: Agent File Mismatch

```yaml
phases:
  - name: design
    agent: architect  # Expects agents/architect.md
# But team has: agents/software-architect.md
```

**Fix**: Ensure agent names in workflow.yaml match actual filenames in `agents/`.

---

### Anti-Pattern: Inconsistent Complexity Scope

```yaml
complexity_levels:
  - name: SMALL
    phases: [a, b, c, d]  # Full pipeline
  - name: LARGE
    phases: [a, c]  # Fewer phases than SMALL?
```

**Fix**: Higher complexity should include same or more phases than lower complexity.

---

### Anti-Pattern: Unused Phases

```yaml
phases:
  - name: analysis
  - name: design
  - name: implementation
  - name: review  # Defined but never in any complexity_levels[].phases
```

**Fix**: Either include phase in at least one complexity level or remove it.

---

## Migration from Legacy Formats

### From Markdown-Only Teams

If your team only has `workflow.md` without `workflow.yaml`:

1. Create `workflow.yaml` following this schema
2. Extract phase information from `workflow.md`
3. Define complexity levels based on documented scope
4. Ensure agent files exist for all phases
5. Add entry_point with first phase agent and artifact

### From Unstructured Agent Collections

If you have agents without workflow definition:

1. Identify the logical order of agent handoffs
2. Define phases based on what each agent produces
3. Create complexity levels for different use case sizes
4. Document in `workflow.yaml`

---

## Quick Reference

```yaml
# Minimal valid workflow.yaml
name: my-team-pack
workflow_type: sequential
description: Brief description of team purpose

entry_point:
  agent: first-agent
  artifact:
    type: first-artifact
    path_template: docs/{slug}.md

phases:
  - name: first-phase
    agent: first-agent
    produces: first-artifact
    next: null

complexity_levels:
  - name: DEFAULT
    scope: "All work"
    phases: [first-phase]
```

```yaml
# Complete workflow.yaml with all optional fields
name: full-team-pack
version: "1.0.0"
workflow_type: sequential
description: Complete example with all fields

entry_point:
  agent: analyst
  artifact:
    type: analysis-report
    path_template: docs/analysis/REPORT-{slug}.md

phases:
  - name: analysis
    agent: analyst
    produces: analysis-report
    next: design

  - name: design
    agent: architect
    produces: design-doc
    next: implementation
    condition: "complexity >= MODULE"

  - name: implementation
    agent: engineer
    produces: code
    next: validation

  - name: validation
    agent: tester
    produces: test-report
    next: null

complexity_levels:
  - name: PATCH
    scope: "Single file change"
    phases: [analysis, implementation, validation]

  - name: MODULE
    scope: "Multiple files"
    phases: [analysis, design, implementation, validation]

  - name: SYSTEM
    scope: "Cross-system change"
    phases: [analysis, design, implementation, validation]

commands:
  - name: quick-scan
    file: quick-scan.md
    description: "Run quick analysis only"
    primary_agent: analyst
    workflow_phase: analysis

# Agent roles for command mapping:
# /architect  -> architect
# /build      -> engineer
# /qa         -> tester
```
