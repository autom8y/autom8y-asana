# Schema: Guard Entry [GUARD-NNN]

## Guard Template

```markdown
### [GUARD-NNN] Title
- **Location**: {file:line or file:line-range}
- **Guards Against**: {what failure mode this prevents}
- **Trigger Condition**: {when/how this guard activates}
- **Failure Without Guard**: {what would happen if this guard were removed}
- **Agent Mapping**: {agent-name} (what awareness is needed)
```

## Risk Zone Template

```markdown
### [RISK-NNN] Title
- **Risk**: {description of the unguarded failure mode}
- **Evidence**: {code location showing absence of guard, or comment admitting gap}
- **Impact**: {consequence if this risk materializes}
- **Recommended Guard**: {what should be added}
- **Agent Mapping**: {which agents should be aware}
```

## Field Descriptions

### Guard Fields

| Field | Required | Description |
|-------|----------|-------------|
| NNN | Yes | Sequential number. Guards and risks use separate sequences. |
| Title | Yes | Short phrase. Use active verb: "prevents X", "validates Y", "enforces Z". |
| Location | Yes | File:line reference. For multi-site guards, list all locations. |
| Guards Against | Yes | The specific failure mode. Reference a SCAR-NNN if this guard was added in response to one. |
| Trigger Condition | Yes | When does this guard fire? Include the boolean expression or function name. |
| Failure Without Guard | Yes | Concrete consequence. Quantify if possible (e.g., "1M inflated rows"). |
| Agent Mapping | Yes | Which agents need awareness and why. |

### Risk Zone Fields

| Field | Required | Description |
|-------|----------|-------------|
| Risk | Yes | What failure mode is unguarded. |
| Evidence | Yes | Code location showing the gap. Comments admitting the gap are strong evidence. |
| Impact | Yes | How severe is the consequence? |
| Recommended Guard | Yes | What should be built. Be specific enough for an engineer to implement. |
| Agent Mapping | Yes | Which agents should be extra careful in this area. |

## Example Guard

```markdown
### [GUARD-010] Stale read hard limit (120 minutes)
- **Location**: `src/core/infra/connection_router.py:699-767`
- **Guards Against**: Serving data older than 120 minutes when fallback is unavailable
- **Trigger Condition**: Staleness >= STALE_READ_HARD_LIMIT_MINUTES (120) AND
  fallback backend is down
- **Failure Without Guard**: Silently serving hours-old data leading to incorrect
  business decisions
- **Agent Mapping**: quality-sentinel (must understand freshness SLA hierarchy)
```

## Example Risk Zone

```markdown
### [RISK-001] No guard against policy bypass in raw query paths
- **Risk**: Raw query code paths may not apply the date floor filter. The policy
  module generates filter strings but enforcement is caller-responsibility.
- **Evidence**: Comment at `engine.py:1416`: "This method does NOT apply date filtering"
- **Impact**: Historical test data leaking into specific query paths
- **Recommended Guard**: Centralized enforcement layer or query builder hook
- **Agent Mapping**: quality-sentinel, query-specialist
```

## Notes

- Group guards by the failure category they prevent (data integrity, schema validation, security, etc.)
- After cataloging all guards, draw the guard dependency graph showing which guards depend on others.
- Risk zones are as valuable as guards -- they tell agents where the safety net has holes.
