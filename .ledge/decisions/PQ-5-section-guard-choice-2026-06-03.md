---
type: decision
status: accepted
decision_state: resolved
id: PQ-5-section-guard-choice
date: 2026-06-03
author: platform-engineer (sre)
initiative: cr3-fleet-data-plane-foundation-cutover
consumer_visible: true
review_required_before_impl: false
supersedes: none
decision_class: default-recommendation
oq_3_resolution: accept-guard
gates:
  - S7-GATE-FIDELITY (Section half of the composite)
related:
  - HANDOFF-autom8-to-asana-sre-cr3-producer-work-queue-ingest-2026-06-03
  - HANDOFF-autom8-to-asana-sre-cr3-consumer-return-2026-06-03 (OQ-3 = accept-guard)
  - SPIKE-cr3-getdf-callsites-gid-reconciliation (autom8 §4 read-first spike)
source_artifacts:
  - .ledge/handoffs/HANDOFF-autom8-to-asana-sre-cr3-producer-work-queue-ingest-2026-06-03.md
  - /Users/tomtenuta/Code/autom8/.sos/wip/handoffs/HANDOFF-autom8-to-asana-sre-cr3-consumer-return-2026-06-03.md
  - .sos/wip/cr3-verified-findings-2026-06-03.md
provenance:
  - { source: "src/autom8_asana/api/routes/query.py:517-526", type: code, grade: strong }
  - { source: "src/autom8_asana/api/routes/query.py:492-499", type: code, grade: strong }
  - { source: "src/autom8_asana/query/engine.py:163-165", type: code, grade: strong }
  - { source: "src/autom8_asana/query/engine.py:126,487-488", type: code, grade: strong }
  - { source: "src/autom8_asana/query/models.py:269-272,318-326", type: code, grade: strong }
  - { source: "HANDOFF-autom8-to-asana-sre-cr3-consumer-return-2026-06-03.md (OQ-3)", type: artifact, grade: strong }
evidence_grade: moderate
---

# PQ-5 — Canary section-arm guard-vs-seed choice (RESOLVED: fail-closed guard IMPLEMENTED)

## Status

**RESOLVED — OQ-3 = ACCEPT-GUARD.** The consumer (monolith) answered OQ-3: it
**accepts a receiver-side fail-closed guard** and does **NOT** seed a canary
`section_gid` (`HANDOFF-autom8-to-asana-sre-cr3-consumer-return-2026-06-03.md`
OQ-3: *"ACCEPT the receiver's fail-closed guard. Do NOT seed a canary
`section_gid`. Keep `ENABLE_SECTION_PROBE = False`."*). The guard is now
**implemented** at `src/autom8_asana/api/routes/query.py:517-526` and locked by
`tests/unit/api/test_routes_query_section_missing_selector_guard.py`.

Self-referential MODERATE ceiling applies to the receiver-authored vulnerability
finding; the consumer's independent corroboration of the silent-unfiltered
mechanism (OQ-3, rite-disjoint) lifts the *mechanism* claim above the self-ref
ceiling. The S7-GATE-FIDELITY re-gate remains the in-anger corroboration event.

## RECONCILIATION — corrected framing vs the pending-oq-3 draft

The pending-oq-3 draft framed the vulnerability as *"`section_gid` absent → filter
skipped"*. **That framing is corrected here against current source** (verified by
file-read this session). The substance of the vulnerability stands; the *selector*
it names was wrong.

### What is actually true at source

1. **The live section selector is `request.section` (the section NAME), not
   `section_gid`.** `RowsRequest.section: str | None` (`query/models.py:269-272`,
   *"Section name to scope the query to"*) is the field the engine consumes.
   `_resolve_section(request.section, …)` returns `None` when `request.section is
   None` (`engine.py:487-488`) and otherwise returns the **name**
   (`engine.py:493-496`) — name-based resolution, consistent with the consumer's
   S3-MAP fix (name-based where-IN).

2. **`request.section_gid` is INERT on the `/rows` path.** It is declared and
   format-validated (`query/models.py:318-326,334-344`) but is **never read** by
   the query engine or by `resolve_section_index` — the route passes
   `request_body.section` (the name) to `resolve_section_index`
   (`query.py:502-504`), and the engine filters on `request.section` only
   (`engine.py:126`). A caller supplying only `section_gid` therefore does **not**
   scope the query — it still degenerates. (Confirmed: the only consumers of
   `section_gid` in the tree are the task-move endpoint, reconciliation, and
   sla_profile — none on the `/rows` query path.) This matches the consumer's OQ-3
   contract-reconciliation note (`section_gid` INERT post-S3-MAP-fix).

3. **The degenerate-unfiltered 200 still exists** (`engine.py:163-165`): the
   section predicate is ANDed in **only** `if section_name_filter is not None`.
   With `request.section` absent, no section narrowing is applied and the
   **unfiltered project-wide frame is returned as 200** — the liveness-masquerade.

4. **A `project_gid`-required 400 already exists** (`query.py:492-499`) — but it
   does **NOT** cover this vulnerability. It rejects a body-parameterized request
   that omits `project_gid`; a section-entity request can carry `project_gid`
   (passing that guard) and still omit `request.section`, degenerating silently.
   So the consumer's relied-upon layer (2) (*"receiver fail-fasts 400 'project_gid
   is required …'"*, OQ-3) is real and present, but it is the **project_gid**
   guard — it is **not** the missing-section-selector guard. The PQ-5 guard is a
   distinct, additional fail-closed branch.

### Net: the guard was genuinely needed (NOT already present)

The `section_gid`-inert + project_gid-400-present facts do **not** make the guard
dead code. The reachable failure mode — section entity, `project_gid` present,
`request.section` absent → unfiltered 200 — survives the existing project_gid
guard. Default-to-REFUTED on *"the guard already exists"*: REFUTED at source.

## Decision — fail-closed guard (IMPLEMENTED)

Reject a **section-entity** request whose live `section` selector is absent with an
explicit **400 `MISSING_SECTION_SELECTOR`-class** error, rather than silently
degenerating to an unfiltered project-wide query.

Implemented at `src/autom8_asana/api/routes/query.py:517-526`, immediately after
the existing risk-1 `project_gid` guard:

```
if entity_type == EntityType.SECTION.value and request_body.section is None:
    raise_service_error(
        request_id,
        InvalidParameterError(
            "section is required in the request body for a section-entity query: "
            "a section query without a section selector would silently return the "
            "unfiltered project-wide frame. Supply the 'section' name selector "
            "(note: 'section_gid' is not consumed on this path). "
            "[MISSING_SECTION_SELECTOR]"
        ),
    )
```

`InvalidParameterError` maps to HTTP 400 (`services/errors.py:370`). The guard is
**section-only** (`entity_type == EntityType.SECTION.value`,
`core/types.py:59`) — a project-entity request with no section is a legitimate
project-wide read and is unaffected.

Rationale:
- **Correctness-first / meet-the-real-need.** A section query with no section
  selector is malformed, not an "all sections" request. Fail-closed makes the
  contract violation observable instead of masquerading as a valid 200.
- **Defeats the liveness-masquerade at the source.** The guard converts the
  silent wrong-frame 200 into an explicit 400, so the S7 canary cannot read green
  on a degenerate section-arm regardless of how the canary asserts.
- **Receiver-owned and reversible.** The guard lives entirely in receiver code;
  it does not depend on the monolith correctly seeding every canary fixture.
- **Names the inert selector explicitly.** The error message tells the caller
  `section_gid` is not consumed on this path — preventing the silent-degenerate
  retry a caller would otherwise attempt by supplying only `section_gid`.

**Rejected alternative — monolith seeds a valid `section_gid`:** declined by the
consumer (OQ-3). The monolith does not own a stable, verified canary section gid;
every candidate is a sequential SCAR-REG-001 placeholder on both sides
(`reconciliation/section_registry.py:94-106` self-incriminates
`section_registry_gids_appear_fabricated`). Seeding a fabricated gid would NOT even
scope the query (`section_gid` is inert), so a seed would produce the same
degenerate 200 — the seed alternative was already moot on the current contract.

## Section-arm is column-contract-EXEMPT (scope note for S7)

The Section arm is **column-contract-EXEMPT**: per the autom8 §4 read-first spike
`SPIKE-cr3-getdf-callsites-gid-reconciliation.md:35` — *"PROJECT frames only:
`office_phone` + `vertical` … SECTION frames are EXEMPT
(`assert_column_contract=False`, SIG-3 `getdf_signals.py:233-241`)."* Because the
Section arm carries no `office_phone`/`vertical` column contract, the Section half
of the S7 composite **cannot** clear on column-content presence. It MUST instead
clear on: (1) the disaggregated honest-EMF / cause signal (503-cadence /
502-capacity / honest-refusal split, NOT a collapsed `GetDfFallback` counter), AND
(2) **this PQ-5 decision resolved** (guard implemented — now satisfied).

The guard is the load-bearing mechanism by which a Section `2xx` becomes
trustworthy at S7: with the guard, a Section `2xx` cannot be a silently-unfiltered
project-wide frame.

Per the consumer's OQ-3: `ENABLE_SECTION_PROBE` stays **False** on the consumer
side and the **project-arm alone is the deploy gate**. The guard does not require
the consumer to enable a section canary; it closes the receiver-side latent path
so that IF/WHEN a section probe is later enabled (on the SCAR-REG-001 discharge
path), it cannot read a false-green.

## Blocking relationship

- This decision is a **GATE on S7-GATE-FIDELITY** (`dependencies: [PQ-1, PQ-5]`).
  The Section half can now clear on this axis: the guard is implemented and tested
  (the other axis — disaggregated cause signal — is tracked separately).

## Validation

- `tests/unit/api/test_routes_query_section_missing_selector_guard.py` — 4 cases:
  1. section + project_gid + **no** selector → 400 (vulnerability blocked).
  2. section + **only** `section_gid` (inert) → 400 (proves section_gid does not
     satisfy the selector requirement).
  3. section + `section` name → 200, frame narrowed to the named section (guard
     does NOT over-block legitimate section queries).
  4. project + no section → 200 (guard is section-only; project-wide read intact).
- Non-regression: existing query-route suites
  (`test_routes_query_project_section_rows_sprint2.py`,
  `test_routes_query_body_parameterized_unregistered.py`,
  `test_routes_query_rows.py`) — 36 tests pass with the guard in place.

## Evidence ceilings & disciplines

- **SVR receipts** (file-read this session): guard `query.py:517-526`; project_gid
  guard `query.py:492-499`; engine filter-gate `engine.py:163-165`;
  `_resolve_section` None-on-absent `engine.py:487-488`; selector fields
  `query/models.py:269-272` (`section` name, live) + `:318-326` (`section_gid`,
  inert); error→400 `errors.py:370`; `EntityType.SECTION="section"`
  `core/types.py:59`.
- **Consumer corroboration (STRONG on the mechanism):** OQ-3 in
  `HANDOFF-autom8-to-asana-sre-cr3-consumer-return-2026-06-03.md` independently
  describes the silent-unfiltered mechanism and accepts the guard — rite-disjoint.
- **Self-referential MODERATE ceiling:** receiver-authored finding; the in-anger
  S7 re-gate is the STRONG-lift event for the *gate-fidelity* claim.
- **Default-to-REFUTED:** *"the guard already exists"* and *"`section_gid` is the
  selector"* were both tested at source and REFUTED. The corrected selector is
  `request.section`.
- **Reversible:** doc + guard + tests authored on a branch cut from origin/main;
  nothing merged, deployed, or applied.

*Resolved under the CR-3 PRODUCER-prong sprint (rite=sre, Potnia-coordinated),
2026-06-03. Grounding: consumer return OQ-3 (accept-guard) +
`.sos/wip/cr3-verified-findings-2026-06-03.md` (V4c) +
`HANDOFF-autom8-to-asana-sre-cr3-producer-work-queue-ingest-2026-06-03.md` (PQ-5),
reconciled against current source.*
