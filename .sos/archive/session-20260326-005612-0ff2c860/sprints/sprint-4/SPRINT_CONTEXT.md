---
schema_version: "2.3"
session_id: session-20260326-005612-0ff2c860
sprint_id: sprint-4
status: ACTIVE
created_at: "2026-03-26T00:53:43Z"
rite: sre
mission: "Instrument both data gaps in operational telemetry with OTel span attributes and structured log events that make office null rate and phone format compliance visible in dashboards"
agents: [observability-engineer, platform-engineer]
---

# Sprint 4: Observability Enhancement (WS-4)

## Mission

Instrument both data gaps in operational telemetry with OTel span attributes and structured log events that make office null rate and phone format compliance visible in dashboards.

## Entry Criteria

- [x] sprint-2 COMPLETE: cascade contract repair delivered and PT-02 PASSED
- [x] sprint-3 COMPLETE: phone normalization on read path delivered and PT-03 PASSED
- [x] Technical spec available at .ledge/specs/offer-data-gaps-technical-spec.md

## Exit Criteria (Required for PT-04 gate)

- [ ] OTel span attribute emitted during progressive build for offer `office` column null rate
- [ ] OTel span attribute emitted for offer phone E.164 compliance rate
- [ ] Structured log event for display-column null audit captures `office` column
- [ ] Dashboard query documented

## Context Loading Order

1. .ledge/specs/offer-data-gaps-technical-spec.md -- technical specification with per-gap observability requirements
2. .know/architecture.md -- package structure, layers, data flow; essential for instrumentation placement
3. .know/scar-tissue.md -- SCAR-005 (cascade null rate), SCAR-006 (hierarchy warming gaps), SCAR-020 (phone trailing newline)

## Discovery Notes

(To be populated by agents during sprint execution)

## Blockers
None yet.

## Verdict

(Pending PT-04 soft gate)

## Next Steps
1. observability-engineer: design OTel span attribute schema for office null rate and phone E.164 compliance
2. platform-engineer: instrument progressive build path with span attributes
3. Document dashboard queries for both metrics
