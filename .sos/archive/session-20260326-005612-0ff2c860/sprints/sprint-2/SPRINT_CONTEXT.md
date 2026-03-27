---
schema_version: "2.3"
session_id: session-20260326-005612-0ff2c860
sprint_id: sprint-2
status: ACTIVE
created_at: "2026-03-26T00:33:41Z"
rite: 10x-dev
mission: "Bring the Offer schema office column under cascade governance by changing its source to cascade:Business Name, fixing the cascade validator source_field bug, and bumping the schema version to 1.4.0"
agents: [architect, principal-engineer, qa-adversary]
---

# Sprint 2: Cascade Contract Remediation (GAP-A)

## Mission

Bring the Offer schema office column under cascade governance by changing its source to cascade:Business Name, fixing the cascade validator source_field bug, and bumping the schema version to 1.4.0.

## Entry Criteria

- [x] Sprint-1 technical spec confirms cascade source change is safe
- [x] Sprint-1 handoff artifact available with implementation recommendations
- [x] Cascade validator behavior for source_field='name' documented and confirmed

## Exit Criteria (Required for PT-02 gate)

- [ ] Offer schema office column source changed from None to cascade:Business Name
- [ ] OFFER_SCHEMA version bumped from 1.3.0 to 1.4.0
- [ ] Cascade validator corrects office on offers where Business ancestor has a name
- [ ] Cascade validator Office Phone correction still works (regression test)
- [ ] ADR documenting the cascade contract change

## Exit Artifacts

- path: .ledge/decisions/ADR-offer-office-cascade-contract.md
  description: "ADR documenting the cascade contract change: why office was previously source=None, what risk the change introduces, why cascade:Business Name is the correct source, and schema version bump rationale."

## Context Loading Order

1. .ledge/spikes/offer-data-gaps-review-handoff.md -- cross-rite handoff artifact with implementation recommendations, file paths, test strategy
2. .ledge/specs/offer-data-gaps-technical-spec.md -- technical specification with per-gap remediation design, affected file inventory, risk assessment
3. .know/architecture.md -- package structure, layer boundaries, data flow
4. .know/scar-tissue.md -- SCAR-005 (cascade null rate), SCAR-006 (hierarchy warming gaps), past defensive patterns
5. .know/conventions.md -- error handling, file organization, domain idioms

## Implementation Notes

(To be populated by agents during sprint execution)

## Blockers

None yet.
