# Workflow Validity Evaluation

> Checklist for verifying workflow.yaml files are valid and coherent

## Required Fields

```yaml
name: {team-name}                    # REQUIRED
workflow_type: sequential            # REQUIRED (only "sequential" supported)
description: {one-line description}  # REQUIRED

entry_point:                         # REQUIRED
  agent: {first-agent-name}
  artifact:
    type: {artifact-type}
    path_template: {path with {slug}}

phases:                              # REQUIRED, array
  - name: {phase-name}
    agent: {agent-name}
    produces: {artifact-type}
    next: {next-phase-name} | null

complexity_levels:                   # REQUIRED, array
  - name: {LEVEL-NAME}
    scope: {description}
    phases: [{phase-names}]
```

## Structural Validation

### Basic Structure

| Check | Pass Condition |
|-------|----------------|
| YAML parses | No syntax errors |
| `name` exists | Non-empty string |
| `workflow_type` valid | Equals "sequential" |
| `description` exists | Non-empty string |
| `entry_point` exists | Has agent and artifact |
| `phases` exists | Non-empty array |
| `complexity_levels` exists | Non-empty array |

### Entry Point Validation

| Check | Pass Condition |
|-------|----------------|
| `entry_point.agent` exists | Non-empty string |
| Agent file exists | File at `agents/{agent}.md` |
| `entry_point.artifact.type` exists | Non-empty string |
| `entry_point.artifact.path_template` exists | Contains `{slug}` |

## Phase Validation

### Per-Phase Checks

```yaml
- name: {phase-name}      # REQUIRED: non-empty, unique
  agent: {agent-name}     # REQUIRED: must match agent file
  produces: {artifact}    # REQUIRED: non-empty
  next: {next} | null     # REQUIRED: valid phase or null
  condition: {expr}       # OPTIONAL: complexity condition
```

| Check | Pass Condition |
|-------|----------------|
| `name` unique | No duplicate phase names |
| `agent` exists | File exists in agents/ |
| `produces` exists | Non-empty string |
| `next` valid | Null or existing phase name |

### Phase Chain Validation

| Check | Pass Condition |
|-------|----------------|
| Entry reachable | First phase is entry_point.agent's phase |
| Single terminal | Exactly one phase has `next: null` |
| No orphans | All phases reachable from entry |
| No cycles | Following `next` eventually reaches null |
| No breaks | Every `next` value is valid phase name or null |

### Reachability Algorithm

```python
def check_reachability(phases):
    entry = phases[0]  # Assumes first phase is entry
    visited = set()
    current = entry

    while current and current['name'] not in visited:
        visited.add(current['name'])
        next_name = current.get('next')
        if next_name is None:
            break  # Terminal reached
        current = find_phase(phases, next_name)

    # All phases should be visited
    return len(visited) == len(phases)
```

## Complexity Level Validation

### Per-Level Checks

```yaml
- name: {LEVEL}           # REQUIRED: uppercase, unique
  scope: {description}    # REQUIRED: non-empty
  phases: [{names}]       # REQUIRED: valid phase names
```

| Check | Pass Condition |
|-------|----------------|
| `name` uppercase | All caps (SCRIPT, MODULE, etc.) |
| `name` unique | No duplicate level names |
| `scope` exists | Non-empty description |
| `phases` valid | All names are existing phases |
| Phases ordered | Phases in workflow order |

### Level Logic Checks

| Check | Pass Condition |
|-------|----------------|
| Entry included | All levels include entry phase |
| Terminal included | All levels include terminal phase |
| Ascending scope | Higher levels have more phases |
| Condition match | Gated phases appear in correct levels |

## Command Mapping Validation

If command mapping comments exist:

```yaml
# /architect  → {agent}
# /build      → {agent}
# /qa         → {agent}
```

| Check | Pass Condition |
|-------|----------------|
| Agents valid | Referenced agents exist in phases |
| Produces match | /architect → produces tdd/design |
| Terminal match | /qa → terminal phase agent |

## Validation Commands

```bash
# Parse YAML
yq '.' workflow.yaml || echo "YAML parse error"

# Check required fields
yq '.name, .workflow_type, .description, .entry_point, .phases, .complexity_levels' workflow.yaml

# Count phases
yq '.phases | length' workflow.yaml

# Find terminal phase
yq '.phases[] | select(.next == null) | .name' workflow.yaml

# Verify agents exist
for agent in $(yq '.phases[].agent' workflow.yaml); do
  test -f "agents/${agent}.md" || echo "Missing: ${agent}"
done
```

## Scoring

| Category | Weight | Pass Threshold |
|----------|--------|----------------|
| Structure | 25% | All required fields |
| Phases | 35% | All phase checks pass |
| Complexity | 25% | All level checks pass |
| Logic | 15% | No cycles, orphans, or breaks |

**Overall Pass**: 90% weighted score (workflow logic is critical)
