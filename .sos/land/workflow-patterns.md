---
domain: "workflow-patterns"
generated_at: "2026-03-29T00:00:00Z"
expires_after: "14d"
source_scope: [".sos/archive/**"]
generator: "dionysus"
source_hash: "905fe4b"
confidence: 0.85
format_version: "1.0"
sessions_synthesized: 8
last_session: "session-20260326-005612-0ff2c860"
---

## Tool Usage Patterns

| Tool | Total Calls | Sessions Using | Avg Calls/Session |
|------|------------|---------------|------------------|
| Bash | 417 | 8 | 52 |
| Edit | 185 | 7 | 26 |
| Write | 42 | 6 | 7 |

## Tool Calls Per Session

| Session | Bash | Edit | Write | Total Tool Calls | File Changes |
|---------|------|------|-------|-----------------|-------------|
| session-20260302-165404-dfdf5ad1 | 29 | 2 | 0 | 31 | 2 |
| session-20260315-131104-fd8bf8d4 | 79 | 50 | 12 | 141 | 62 |
| session-20260318-141031-485cc768 | 26 | 2 | 3 | 31 | 5 |
| session-20260324-122624-3932c629 | 34 | 6 | 7 | 47 | 13 |
| session-20260324-131439-602b6637 | 15 | 2 | 1 | 18 | 3 |
| session-20260324-134959-b83800f2 | 58 | 67 | 6 | 131 | 73 |
| session-20260325-003123-fb6967fa | 78 | 15 | 1 | 94 | 16 |
| session-20260326-005612-0ff2c860 | 98 | 41 | 12 | 151 | 53 |

## File Change Hotspots

| Path Pattern | Changes | Sessions | Domain |
|-------------|---------|---------|--------|
| .sos/sessions/*/SESSION_CONTEXT.md | 26 | 6 | session-management |
| src/autom8_asana/api/models.py | 20 | 1 | api-models |
| src/autom8_asana/api/routes/tasks.py | 13 | 1 | api-routes |
| docs/guides/entity-resolution.md | 9 | 1 | documentation |
| src/autom8_asana/clients/data/config.py | 4 | 1 | client-config |
| src/autom8_asana/clients/data/client.py | 5 | 1 | client-data |
| src/autom8_asana/services/gid_push.py | 6 | 1 | services |
| src/autom8_asana/dataframes/builders/cascade_validator.py | 3 | 1 | dataframes |
| tests/unit/dataframes/builders/test_cascade_validator.py | 6 | 1 | tests |
| tests/unit/dataframes/views/test_cascade_view.py | 4 | 1 | tests |
| src/autom8_asana/services/resolution_result.py | 3 | 1 | services |
| src/autom8_asana/services/universal_strategy.py | 2 | 1 | services |
| .ledge/spikes/*.md | 6 | 2 | artifacts |
| .ledge/decisions/*.md | 3 | 2 | artifacts |
| .ledge/reviews/*.md | 5 | 3 | artifacts |
| .ledge/specs/*.md | 3 | 2 | artifacts |
| .sos/wip/review/*.md | 4 | 1 | review-artifacts |
| tests/unit/services/test_universal_strategy*.py | 8 | 1 | tests |
| tests/unit/api/routes/test_resolver_status.py | 3 | 1 | tests |
| docs/api-reference/endpoints/resolver.md | 7 | 1 | documentation |

## Phase Progression Patterns

| Terminal Phase | Sessions | Avg Session Duration |
|---------------|---------|---------------------|
| requirements | 4 | 41m |
| research | 1 | 40m |
| sprint-3+4-parallel | 1 | 41m |
| complete | 1 | 20m |
| observation | 1 | 67m |

## Agent Delegation Patterns

- 0/8 sessions contain agent.delegated events
- agent.task_start events found in 7/8 sessions (all except session-20260302-165404-dfdf5ad1)
- All agent.task_start events have agent_name="unknown"
- Delegation volume by session:
  - session-20260315-131104-fd8bf8d4: 10 subagent starts
  - session-20260324-134959-b83800f2: 9 subagent starts
  - session-20260324-122624-3932c629: 8 subagent starts
  - session-20260326-005612-0ff2c860: 7 subagent starts
  - session-20260318-141031-485cc768: 6 subagent starts
  - session-20260324-131439-602b6637: 4 subagent starts
  - session-20260325-003123-fb6967fa: 1 subagent start
- Agent name data limitation: all agent_name fields are "unknown", preventing delegation pattern analysis by agent type

## Common Command Patterns

- Session lifecycle commands (ari session create/lock): present in all 8 sessions
- File exploration (find, ls, grep): dominant Bash usage pattern across all sessions
- Test execution: present in session-20260315, session-20260324-3932c629, session-20260326

## Phase Transition Events

| Session | Transitions | Path |
|---------|------------|------|
| session-20260302-165404-dfdf5ad1 | 0 | research (parked) |
| session-20260315-131104-fd8bf8d4 | 2 | sprint-1 -> sprint-2 -> sprint-3+4-parallel |
| session-20260318-141031-485cc768 | 0 | requirements (parked) |
| session-20260324-122624-3932c629 | 0 | complete (from SESSION_CONTEXT) |
| session-20260324-131439-602b6637 | 0 | requirements (parked) |
| session-20260324-134959-b83800f2 | 0 | requirements (parked) |
| session-20260325-003123-fb6967fa | 0 | requirements |
| session-20260326-005612-0ff2c860 | 5 | observation -> sprint-1 -> sprint-2 -> sprint-3 -> sprint-4 -> sprint-5 |

## Session Duration Distribution

| Bucket | Count | Sessions |
|--------|-------|---------|
| 0-15m | 1 | session-20260324-131439-602b6637 |
| 16-30m | 2 | session-20260324-122624-3932c629, session-20260325-003123-fb6967fa |
| 31-45m | 3 | session-20260302-165404-dfdf5ad1, session-20260315-131104-fd8bf8d4, session-20260324-134959-b83800f2 |
| 46-60m | 0 | (none) |
| 61-90m | 2 | session-20260318-141031-485cc768, session-20260326-005612-0ff2c860 |

## Observations

- Bash is the dominant tool across all sessions (417/644 total calls, 65%)
- Edit usage correlates strongly with session productivity: the 3 highest-output sessions (session-20260315, session-20260324-b83800f2, session-20260326) account for 158/185 Edit calls (85%)
- The 2 sessions with multi-sprint progression (session-20260315, session-20260326) have the highest total tool call counts (141, 151)
- SESSION_CONTEXT.md is the most frequently changed file path pattern across sessions (session management overhead)
- No phase.transitioned events in events.jsonl; phase transitions tracked only in SESSION_CONTEXT narrative
- File changes concentrate in src/autom8_asana/api/ (models, routes) and tests/ directories
- .ledge/ artifact creation spans spikes, decisions, reviews, and specs across 5 sessions
- 7/8 sessions used subagent delegation but agent identity is not tracked (all "unknown")
