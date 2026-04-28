---
domain: "workflow-patterns"
generated_at: "2026-04-28T20:00:00Z"
expires_after: "14d"
source_scope: [".sos/archive/**", ".sos/sessions/**"]
generator: "dionysus"
source_hash: "8c58f930"
confidence: 0.75
format_version: "1.1"
sessions_synthesized: 18
last_session: "session-20260428-004041-4c69f12c"
provenance_distribution:
  wrapped: 18
  stale_parked: 0
  recent_parked: 0
sails_color: "WHITE"
sails_reason: "18/18 WRAPPED, newest <24h old; -0.10 because tool-usage and events.jsonl tallies were not re-grepped in this dispatch (carry forward + augment from SESSION_CONTEXT only)"
---

## Tool Usage Patterns

(Tool-call tallies for the 8 originally-grepped sessions are preserved verbatim from the prior synthesis. Tallies for the 10 sessions added in this dispatch were not re-grepped — they are inferred from SESSION_CONTEXT artifact density and sprint-commit counts.)

| Tool | Total Calls (8 grepped) | Sessions Using (8 grepped) | Avg Calls/Session (8 grepped) |
|------|------------|---------------|------------------|
| Bash | 417 | 8 | 52 |
| Edit | 185 | 7 | 26 |
| Write | 42 | 6 | 7 |

## Tool Calls Per Session (grepped subset)

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

## Inferred Activity Density (sessions added 2026-03-29 to 2026-04-28)

| Session | Density Signal | Inferred Tier |
|---------|---------------|--------------|
| session-20260329-153238-9bcc549e | sprint-1 complete + 1 commit (9d279a2); 3 future sprints pending | MEDIUM |
| session-20260409-170809-a07b979e | 20+ routes hardened, fuzz pass rate 5%->66%, PRD + TDD produced | HIGH |
| session-20260412-165046-26eaea0e | parked at requirements; minimal activity | LOW |
| session-20260415-010441-e0231c37 | 8 signal classes inventoried, 7 agents defined; sprint-1 not started at park | MEDIUM |
| session-20260415-032649-5912eaec | 6 sprints, 36+ commits (CRU-S2..S5 series), 8h25m wall clock | VERY HIGH |
| session-20260427-154543-c703e121 | 5 verified findings + 4 open questions; concrete file references | MEDIUM |
| session-20260427-232025-634f0913 | Frame 419 lines, Shape 809 lines, Workflow 1407 lines; telos block | HIGH |
| session-20260428-004041-4c69f12c | parked at requirements 88m later; PRD/TDD pending | LOW-MEDIUM |

## File Change Hotspots (grepped subset preserved)

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

## File Change Hotspots (newly inferred from SESSION_CONTEXT)

| Path Pattern | Sessions Touching | Domain |
|-------------|-------------------|--------|
| docs/guides/remittance-openapi-schemathesis-remediation.md | 1 (session-20260409) | documentation |
| tests/test_openapi_fuzz.py | 2 (session-20260409, session-20260415-010441) | tests |
| .sos/wip/frames/project-crucible-17-second-frontier*.md | 1 (session-20260415-032649) | frames |
| .sos/wip/frames/project-asana-pipeline-extraction*.md | 1 (session-20260427-232025) | frames |
| .ledge/spikes/crucible-*-handoff.md | 1 (session-20260415-032649) | review-artifacts |
| 33 scar-tissue regression tests | 1 (session-20260415-032649, preserved-not-modified) | tests |

## Phase Progression Patterns

| Terminal Phase | Sessions | Avg Session Duration |
|---------------|---------|---------------------|
| requirements | 9 | 47m |
| design | 1 | 25m |
| research | 1 | 40m |
| sprint-3+4-parallel | 1 | 41m |
| complete | 1 | 20m |
| observation | 1 | 67m |
| implementation | 1 | 58m |
| remediation | 1 | 79m |
| sprint-6 | 1 | 8h25m |

Total: 18/18 (100%; 1 session "complete" + 8 multi-sprint terminal states + 9 requirements parks).

## Agent Delegation Patterns

events.jsonl was not re-grepped in this dispatch. The 8-session delegation tally from the prior dionysus run is preserved as the only authoritative source. Newly-added sessions are not yet measured for subagent volume.

- 0/8 grepped sessions contain agent.delegated events
- agent.task_start events found in 7/8 grepped sessions
- All agent.task_start events have agent_name="unknown"
- Delegation volume by grepped session:
  - session-20260315-131104-fd8bf8d4: 10 subagent starts
  - session-20260324-134959-b83800f2: 9 subagent starts
  - session-20260324-122624-3932c629: 8 subagent starts
  - session-20260326-005612-0ff2c860: 7 subagent starts
  - session-20260318-141031-485cc768: 6 subagent starts
  - session-20260324-131439-602b6637: 4 subagent starts
  - session-20260325-003123-fb6967fa: 1 subagent start
- Newly-added (un-grepped) sessions explicitly enumerate agents in SESSION_CONTEXT for 2 cases:
  - session-20260415-010441 (asana-test-rationalization): 7 named eunomia agents (potnia, test-cartographer, pipeline-cartographer, entropy-assessor, consolidation-planner, rationalization-executor, verification-auditor)
  - session-20260415-032649 (project-crucible) sprint-6: 5 named hygiene agents (potnia, code-smeller, architect-enforcer, janitor, audit-lead)
- Agent-name data limitation persists: events.jsonl agent_name still "unknown" in grepped sessions; SESSION_CONTEXT enumeration is the only path to typed delegation analysis

## Common Command Patterns

- Session lifecycle commands (ari session create/lock/sync): present in all 18 sessions
- File exploration (find, ls, grep): dominant Bash usage pattern across all grepped sessions
- Test execution: present in session-20260315, session-20260324-3932c629, session-20260326, session-20260329, session-20260409, session-20260415-032649
- Cross-rite transitions via `ari sync --rite=...`: documented in session-20260415-032649 (hygiene<->10x-dev), session-20260427-232025 (rnd->10x-dev planned)

## Phase Transition Events

| Session | Transitions | Path |
|---------|------------|------|
| session-20260302-165404-dfdf5ad1 | 0 | research (parked) |
| session-20260303-134822-abd31a5b | 0 | design (parked) |
| session-20260303-173218-9ba34f7f | 0 | requirements (parked) |
| session-20260315-131104-fd8bf8d4 | 2 | sprint-1 -> sprint-2 -> sprint-3+4-parallel |
| session-20260318-141031-485cc768 | 0 | requirements (parked) |
| session-20260324-122624-3932c629 | 0 | complete (from SESSION_CONTEXT) |
| session-20260324-131439-602b6637 | 0 | requirements (parked) |
| session-20260324-134959-b83800f2 | 0 | requirements (parked) |
| session-20260325-003123-fb6967fa | 0 | requirements |
| session-20260326-005612-0ff2c860 | 5 | observation -> sprint-1 -> sprint-2 -> sprint-3 -> sprint-4 -> sprint-5 |
| session-20260329-153238-9bcc549e | 1 | debt-triage-requirements -> 10x-dev-implementation (rite + phase) |
| session-20260409-170809-a07b979e | 1 | requirements -> remediation |
| session-20260412-165046-26eaea0e | 0 | requirements (parked) |
| session-20260415-010441-e0231c37 | 0 | requirements (sprint-1 not started at park) |
| session-20260415-032649-5912eaec | 5 | sprint-1 -> sprint-2 -> sprint-3 -> sprint-4 -> sprint-5 -> sprint-6 (cross-rite handoffs at sprint-2/sprint-5 boundaries) |
| session-20260427-154543-c703e121 | 0 | requirements (parked) |
| session-20260427-232025-634f0913 | 0 | requirements (parked at Phase 0 spike) |
| session-20260428-004041-4c69f12c | 0 | requirements (parked) |

Total transitions across corpus: 14. Top contributors: session-20260326-005612 (5), session-20260415-032649 (5), session-20260315-131104 (2), session-20260329-153238 (1), session-20260409-170809 (1).

## Session Duration Distribution

| Bucket | Count | Sessions |
|--------|-------|---------|
| 0-15m | 2 | session-20260303-173218, session-20260324-131439 |
| 16-30m | 4 | session-20260303-134822, session-20260324-122624, session-20260325-003123, session-20260415-010441 |
| 31-60m | 5 | session-20260302-165404, session-20260315-131104, session-20260324-134959, session-20260329-153238, session-20260427-232025 |
| 61-90m | 5 | session-20260318-141031, session-20260326-005612, session-20260409-170809, session-20260412-165046 (close to bucket boundary; counted here), session-20260428-004041 |
| 91m-3h | 1 | session-20260427-154543 (2h31m) |
| > 3h | 1 | session-20260415-032649 (8h25m) |

Total: 18/18 (100%).

## Observations

- Bash dominates tool calls (417/644 in grepped subset, 65%); pattern likely holds for newer sessions
- Edit usage correlates with session productivity in the grepped subset; 3 highest-output sessions hold 158/185 Edit calls (85%)
- Multi-sprint sessions (5+ phase transitions) cluster in offer-data-gaps (sprint-5 PT-PASS) and project-crucible (sprint-6 cross-rite) — these are the two longest sustained efforts in the corpus
- 50% of sessions (9/18) park at "requirements" without progressing; suggests systematic early-exit pattern (lifecycle / discovery sessions)
- project-crucible (session-20260415-032649) is the longest single session in the corpus (8h25m); reflects 6-sprint cross-rite execution with 36+ commits
- Cross-rite handoff is operationally exercised (offer-data-gaps: review->10x-dev->sre; crucible: hygiene<->10x-dev<->hygiene)
- SCAR test cluster (33 inviolable tests) is documented as a sacred constraint in project-crucible
- 1/18 sessions (project-asana-pipeline-extraction Phase 0) carries telos discipline (telos_deadline 2026-05-11)
- 17/18 sessions GRAY sails, 1/18 BLACK; no WHITE proofs ever captured -> WHITE_SAILS proof pipeline is not wired

## Confidence Notes

- Confidence 0.75 (HIGH tier 0.85, -0.10 because tool-usage and file-change tallies for 10 of 18 sessions are inferred from SESSION_CONTEXT density rather than re-grepped from events.jsonl in this dispatch)
- Tool-call data for sessions added in this dispatch (2026-03-29 onward) is qualitative (artifact-density tier) not quantitative (exact call counts)
- 18/18 sessions verified resident in `.sos/archive/` (all status: ARCHIVED)
- Recommend follow-up dionysus run with explicit Grep over events.jsonl across all 18 sessions to refresh exact tool-call tallies and file-change hotspots
- Phase transition tally is authoritative (extracted from SESSION_CONTEXT Timeline / Sprints sections)
