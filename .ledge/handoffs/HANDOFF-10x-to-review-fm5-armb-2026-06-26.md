---
type: handoff
status: accepted
handoff_type: validation
from_rite: 10x-dev
to_rite: review
date: 2026-06-26
initiative: receiver-contract-realization
node: FM-5 ARM-B (honest-refusal consumer-column contract) -> rite-disjoint S4 canary RUN
rung: "FM-5 = built (PR #161, branch pushed, not merged); in-rite verification = MODERATE; seal STRONG-elevation = PENDING review critic; verified_realized = [UNATTESTED — DEFER] (S9/S10, eunomia)"
seam_state: "BUILT + PR opened. The disjoint review critic RUNs the authored two-sided canary for the STRONG build-seal. Merge stays operator/releaser; verified_realized is live (S9/S10), eunomia's."
validation_scope:
  - "RUN the two-sided discriminating canary rite-disjoint (tests/unit/query/test_fm5_armb_canary.py): RED required_columns=[offer_id] -> contract_complete=False, unservable=['offer_id'] (bites); GREEN [office_phone] -> contract_complete=True, unservable=[] (passes, served column, no Door-C dependency); DOOR no-declaration -> two-way. It is AUTHORED + in-rite GREEN; STRONG requires the disjoint RUN."
  - "VERIFY the single S4-routed design decision (ADR D2): contract_complete is a DISTINCT sibling meta field, NOT a mutation of honest_contract_complete (folding it in routes a structural column-gap into 503-retry-forever, models.py:443-446). qa-adversary showed honest_contract_complete=True AND contract_complete=False simultaneously, contract_complete wired to ZERO 503 sites — re-confirm the orthogonality."
authority_anchors:
  - "PR autom8y/autom8y-asana#161 OPEN, base main, head feat/fm5-column-fidelity @ ad8817757cc0122ae9c449e2291ca09a840f6f14, 8 files 963+/3- (verified live; 0-behind main, no stowaways)"
  - "built off CURRENT origin/main f8902aef (G-PREMISE re-bind; e49c30d7 ancestor; FM-5 surface byte-stable across the disjoint grain-bridge #160 merge)"
  - "ADR: .ledge/decisions/ADR-fm5-armb-contract-locus.md ; TDD: .ledge/specs/TDD-fm5-armb-honest-refusal-contract.md"
  - "graft: query/engine.py _derive_column_contract :615-658, one-gate graft :263-269; query/models.py RowsRequest.required_columns :304 + RowsMeta :489-520; field_contract_maps.py SOLE propagation point"
  - "premise receipt: .claude/agent-memory/architect/project_fm5_offer_id_serve_premise.md (offer_id ABSENT-at-serve on project, 100%-null at storage, populated on entity_type=offer)"
---

# HANDOFF — 10x-dev -> review — FM-5 ARM-B (validation)

## Grandeur Anchor
receiver-contract-realization makes the monolith + fleet CONSUME the GFR-realized honest contract so a
requested-but-absent REQUIRED column on `/v1/query` returns a TYPED contract-incomplete signal — never
a silent drop, a daily KeyError, or a $0/7-row fossil. ARM-B is BUILT (PR #161). THIS handoff hands the
authored two-sided canary to the rite-disjoint `review` critic to RUN for the STRONG build-seal.
`built != verified_realized`; the live fossil-death is S9/S10 (eunomia); this is NOT the gfr telos proof.

## §1 — What's built (FM-5 = `built`, PR #161, not merged)
8 files, 963+/3-, scoped, no stowaways, 0-behind current main `f8902aef`:
- **field_contract_maps.py** (SOLE propagation point, G-PROPAGATE): `load_consumer_requirements` (fail-loud) + `derive_required_columns` (RULING-1 SUBSET) + `requirements_drift_check` (WARN-first, schema-only; NO model-codegen → ADR-S4-001 preserved). Activates its own deferred Phase-3 SCOPE NOTE.
- **consumer_column_requirements.vendored.json** (SPEC v1 seed: offer_id/project, project_gid/section; packaged into the wheel).
- **query/models.py** (additive): `RowsRequest.required_columns`; `RowsMeta.{contract_complete,unservable_required_columns,column_manifest}` (two-way door).
- **query/engine.py**: `_derive_column_contract` grafted at the ONE gate; completeness from `schema.column_names()`, NEVER `df.columns` (the 100%-null offer_id parquet trap).

| Gate (in-rite, MODERATE) | Receipt |
|---|---|
| GFR spine (strictly-additive) | **207 passed** (frozen: `_resolve_identity_plan_async` engine.py:98 + `assert_rows_tenant_identity` guard.py:183 untouched; guard RED-on-bypass test among the 207) |
| mypy --strict | Success, 518 files |
| ruff format/lint | formatted / All checks passed |
| arch gate | 20 passed |
| regression | query 966 / dataframes 1401,2skip,2xfail |
| new FM-5 | 21 passed (6 canary + 15 contract/CI-parity/freshness/fail-loud) |
| two-sided canary | RED `[offer_id]`→`(False,['offer_id'])` bites · GREEN `[office_phone]`→`(True,[])` passes · DOOR no-decl→two-way |

## §2 — Validation scope for the review critic (RUN, rite-disjoint)
1. RUN the two-sided canary disjoint from this builder: confirm RED bites (broken INPUT correctly refused = no silent drop), GREEN passes (served column, no Door-C dependency), DOOR two-way. The RED is a deliberately-broken INPUT, NOT an injected prod defect.
2. Re-confirm the **ADR D2 orthogonality** (the single S4-routed decision): `contract_complete` distinct-sibling vs `honest_contract_complete` mutation — verify zero 503-retry conflation (the qa probe constructed both-true-simultaneously; re-derive).
3. NOTE the canary altitude: it exercises the REAL derivation + REAL PROJECT_SCHEMA but mocks the data provider + SchemaRegistry (engine-altitude). The **live-HTTP two-sided canary is S9** (verified_realized), not this S4 build-seal — do not conflate the altitudes.

## §3 — Rungs (G-RUNG — Gate C honored)
- FM-5 = **built** (PR #161 @ ad8817757).
- in-rite verification = **MODERATE** (qa 10/10 GREEN; self-grade cap honored).
- build seal STRONG-elevation = **PENDING** — the rite-disjoint review critic RUNs the canary.
- **`verified_realized` = [UNATTESTED — DEFER-POST-HANDOFF]** — eunomia, LIVE: S9 = live `/v1/query` HTTP two-sided canary; S10 = operator-denylist retirement. NOT discharged by this build. **NOT the gfr telos proof** (`.know/telos/gfr.md:79-89`, distinct altitude).

## §4 — DEFER watch-register + residual flags (none scope-crept; none blocking)
- **DEFER** (watch-register only, untouched): Door-C `project_gid`/section widen application; the monolith manifest hand-back (drift guard runs schema-only until then); SEAM-2 rebind; the operator denylist. `offer_id`/project intentionally stays UNWIDENED → ARM-B emits a permanent loud `contract_complete=False`, the intended SEAM-2 rebind driver.
- **F1 (retrospective)**: a carried grandeur anchor said "105 GFR spine"; the measured/correct count is **207** (the build used 207). Correct the anchor, don't round the build down.
- **F2 (→ S9)**: `column_manifest` population is best-effort over the PROJECTED frame — a required column in-schema but `select`-projected-out gets no population entry. The load-bearing `contract_complete` (schema-membership) signal is unaffected.
- **F3 (S4 watch, cosmetic)**: empty-string member `[""]` is pydantic-accepted → `unservable=['']`, `contract_complete=False` — harmless typed signal, no crash.

## §5 — Next step
Operator walks `ari sync --rite=review` + CC restart for the rite-disjoint STRONG canary RUN.
On STRONG → releaser/framing for the operator-walked merge of PR #161 (merge stays operator-held).
On WITHHELD → back to 10x-dev/framing with the named deficiency. 10x-dev does NOT dispatch review specialists from here.
