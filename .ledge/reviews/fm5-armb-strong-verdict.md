---
type: review
status: accepted
artifact_id: fm5-armb-strong-verdict
title: "FM-5 ARM-B — Build Seal Verdict (MODERATE -> STRONG)"
initiative: receiver-contract-realization
pr: "autom8y/autom8y-asana#161"
branch: feat/fm5-column-fidelity
commit: ad8817757cc0122ae9c449e2291ca09a840f6f14
review_mode: FULL
date: 2026-06-26
reviewer_rite: review (rite-disjoint from 10x-dev builder)
worktree: /tmp/wt-review-fm5-canary
build_seal:
  from: MODERATE
  to: STRONG
  basis: independently-re-run evidence (rite-disjoint from builder)
rung:
  build_seal: STRONG
  verified_realized: "[UNATTESTED — DEFER-POST-HANDOFF]"
  merge_authority: operator-held (PR #161)
  gfr_telos: distinct altitude ([UNATTESTED — DEFER], .know/telos/gfr.md:79-89)
cross_stream_concurrence: true
overall_health_grade: A
f1_correction: "Stale anchors cited '105 GFR spine'; measured/correct count is 207."
---

# Code Review: autom8y-asana — FM-5 ARM-B Build Seal Verdict

## Executive Summary

This is the rite-disjoint build-seal review for FM-5 ARM-B (PR autom8y/autom8y-asana#161, `feat/fm5-column-fidelity` @ `ad8817757`), which introduces a typed consumer-column contract layer that turns a requested-but-absent REQUIRED column on `/v1/query` into a `contract_complete=False` signal — never a silent drop, a daily KeyError, or a $0/7-row fossil. The review ran from an independent worktree (`/tmp/wt-review-fm5-canary`, detached HEAD at `ad8817757`, fresh from `origin/feat/fm5-column-fidelity`, rite-disjoint from the builder's `autom8y-asana-wt-fm5`) and independently re-fired the authored two-sided discriminating canary, the TEETH mutation-kill, and the ADR-D2 orthogonality construction. All six STRONG criteria are satisfied by independently-re-run evidence: the build seal elevates from MODERATE to STRONG. Two watch items are noted (F2: manifest projection coverage, Medium; F3: empty-string member, Low) and neither blocks STRONG. The merge of PR #161, the S9/S10 eunomia work, and the prod cutover remain operator-held; `verified_realized` is `[UNATTESTED — DEFER-POST-HANDOFF]` at the eunomia/live-HTTP altitude — a distinct altitude from this build seal, and NOT the gfr telos proof (`.know/telos/gfr.md:79-89`).

## Health Report Card

| Dimension | Grade | Key Finding |
|-----------|-------|-------------|
| Canary discriminating power | A | 6/6 passed; RED bites on broken input, GREEN passes on served column, DOOR two-way |
| Mutation gate integrity | A | TEETH bites: gate inversion flips RED; sha256 restored byte-identical |
| Design orthogonality (ADR-D2) | A | `honest_contract_complete` and `contract_complete` independently derived; zero 503 wiring confirmed |
| GFR spine non-regression | A | 207 passed; frozen sentinels untouched; ARM-B strictly-additive |
| Propagation integrity | A | `field_contract_maps.py` sole propagation point; no orphan consumer contract |
| **Overall** | **A** | All five dimensions A; weakest-link: A; 0 critical, 0 high, 1 medium (F2), 1 low (F3) |

Weakest-link model applied. No floor-drag conditions triggered. Overall: **A**.

## Metrics Dashboard

| Metric | Value |
|--------|-------|
| PR | autom8y/autom8y-asana#161 |
| Commit | ad8817757cc0122ae9c449e2291ca09a840f6f14 |
| Worktree | /tmp/wt-review-fm5-canary (rite-disjoint from builder's autom8y-asana-wt-fm5) |
| Files changed | 8 files, 963+/3- |
| Canary tests | 6/6 passed (0.57s) |
| GFR spine tests | 207 passed (0.74s) |
| PR CI checks | 24 passing, 2 skipping (Convention Check, Integration Tests — non-blocking by design) |
| Total findings | 2 (0 critical, 0 high, 1 medium, 1 low) |
| Review mode | FULL |
| Build seal | MODERATE -> STRONG |

## GREEN / RED / TEETH / ORTHOGONALITY MATRIX

### [1] Canary Run — 6/6 Passed, 0.57s

Independently re-run from `/tmp/wt-review-fm5-canary`. PYTHONPATH pointed to fresh worktree src. Detached HEAD at `ad8817757cc0122ae9c449e2291ca09a840f6f14`.

| Arm | Test | Input | Result | Status |
|-----|------|-------|--------|--------|
| RED | `test_red_arm_declared_unservable_column_fires_typed_signal` | `required_columns=["offer_id"]` | `contract_complete=False`, `unservable=["offer_id"]` | BITES |
| GREEN | `test_green_arm_declared_served_column_passes` | `required_columns=["office_phone"]` | `contract_complete=True`, `unservable=[]` | PASSES |
| DOOR | `test_two_way_door_no_declaration_preserves_today_behavior` | no declaration | `contract_complete=True`, `unservable=[]`, `column_manifest=None` | TWO-WAY |
| NO-SELECT | `test_no_select_path_carries_typed_signal_not_silent_drop` | — | typed signal on no-select path | PASSES |
| UNIT | `TestDeriveColumnContractUnit::test_completeness_uses_schema_not_df_columns` | — | schema-membership gate confirmed | PASSES |
| UNIT | `TestDeriveColumnContractUnit::test_non_declaring_request_is_two_way_door_identity` | — | two-way door identity | PASSES |

The RED arm is a deliberately-broken INPUT (offer_id absent from PROJECT_SCHEMA) correctly refused. This is NOT a regression and NOT an injected prod defect. [STRONG | TACTICAL]

### [2] TEETH Mutation-Kill

Load-bearing gate: `engine.py:649` — `unservable = [c for c in required if c not in served]`

| Step | Detail |
|------|--------|
| BEFORE sha256 | `563979f0fe1cbe4f924781c7204b2f4eecd426cd96cb20ec63951b0684391748` |
| Mutation applied | `c not in served` -> `c in served` (gate inverted; offer_id no longer unservable) |
| RED arm post-mutation | `AssertionError: assert True is False` — RED flipped to `contract_complete=True` |
| TEETH receipt | `assert result.meta.contract_complete is False` fails; gate is load-bearing |
| Restore method | copy-aside: golden copy restored from /tmp/ |
| AFTER sha256 | `563979f0fe1cbe4f924781c7204b2f4eecd426cd96cb20ec63951b0684391748` — BEFORE==AFTER |
| git status after restore | clean |

Disable the schema-membership gate and the RED arm vanishes. Restore is byte-identical. [STRONG | TACTICAL]

### [3] ADR-D2 Orthogonality Construction

Claim: `honest_contract_complete` and `contract_complete` are independently derived; `contract_complete=False` is wired to ZERO 503 sites.

| Element | Evidence |
|---------|----------|
| `honest_contract_complete` derivation | `engine.py:254` via `_derive_honest_contract_complete()` (SectionPersistence manifest) |
| `contract_complete` derivation | `engine.py:263` via `_derive_column_contract()` (schema.column_names() membership) |
| Independent assignment | Set independently at `engine.py:292,294` |
| Mutation corroboration | Mutated state showed `honest_contract_complete=False AND contract_complete=True` — selective flip confirms orthogonal derivation paths |
| Constructed case | `honest_contract_complete=True AND contract_complete=False` simultaneously — CONFIRMED |
| 503 wiring on `contract_complete` | ZERO — grep across src: `contract_complete` appears only at `query/models.py:489` (field definition) and `query/engine.py:263,294,630,642,650,658` (derivation and return) |
| 503 path | `models.py:465` comment keys on `honest_contract_complete=False -> 503` exclusively |
| D2 collision avoided | A structural column gap (offer_id absent from PROJECT_SCHEMA) does NOT route to 503-retry-forever. GLINT L1-2 reconciliation holds: one-gate graft, SSOT-fed, distinct field is the only shape that avoids the conflation (TDD §4.2). |

Corroboration: direct read of `models.py:446` on origin/main confirms the 503 comment keys on `honest_contract_complete=False -> 503` exclusively; `contract_complete` is additive in the PR and absent on main, confirming the field is additive and orthogonal. [STRONG | STRUCTURAL]

### [4] GFR Spine Non-Regression — 207 Passed, 0.74s

| Sentinel | Location | Status |
|----------|----------|--------|
| `_resolve_identity_plan_async` | `resolution/gfr/engine.py:98` | UNTOUCHED |
| `assert_rows_tenant_identity` | `resolution/gfr/guard.py:183` | UNTOUCHED |
| Spine count | 207 passed (0.74s) | NOT BELOW 207 |

F1 corrected: stale anchors cited "105 GFR spine." The measured/correct count is **207**. Build is strictly-additive to the certified GFR spine. [STRONG | TACTICAL]

### [5] PR CI — 24 Checks Passing

24 checks passing. 2 skipping (Convention Check, Integration Tests — non-blocking by design per PR configuration). Zero failures. [STRONG | TACTICAL]

### [6] G-PROPAGATE — Sole Propagation Point Confirmed

`load_consumer_requirements`, `derive_required_columns`, `requirements_drift_check` appear only in `field_contract_maps.py` and its `contracts/__init__.py` re-export and test files. `gid_lookup.py:270` use is a local `set(key_columns) | {"gid"}` variable unrelated to the manifest mechanism. `engine.py`'s `_derive_column_contract` implements the schema-membership gate inline, consuming `RowsRequest.required_columns` (the wire field) — not a separate propagation path. No per-consumer orphan contract found. [STRONG | STRUCTURAL]

## G-HALT Status

| Condition | Result | Evidence |
|-----------|--------|----------|
| Re-run RED is intended typed-incomplete arm (not a regression) | CLEAR | offer_id correctly refused (ABSENT from PROJECT_SCHEMA); broken input, not a prod defect |
| TEETH bites (gate inverted -> RED flips) | CLEAR | AssertionError on mutation; sha256 BEFORE==AFTER; git status clean |
| GFR spine not below 207 | CLEAR | 207 passed |
| Orthogonality: `contract_complete` wired to ZERO 503 sites | CLEAR | Zero 503/retry sites confirmed by grep + direct file read |

**G-HALT: NO HALT. All four conditions clear.**

## Binding Verdict

**BUILD SEAL: STRONG**

Issued on independently-re-run evidence from a rite-disjoint worktree (`/tmp/wt-review-fm5-canary`, detached HEAD at `ad8817757`, fresh from `origin/feat/fm5-column-fidelity`, independent of the builder's `autom8y-asana-wt-fm5`). This station is the rite-disjoint external critic. The self-ref STRONG ceiling is NOT in effect: the verdict issues on independently re-run evidence, not the builder's or qa-adversary's green run.

| STRONG Criterion | Status |
|------------------|--------|
| RED arm bit: `contract_complete=False`, `unservable=['offer_id']` | CONFIRMED |
| GREEN passed: `contract_complete=True`, `unservable=[]` | CONFIRMED |
| DOOR two-way: `contract_complete=True`, `unservable=[]`, `column_manifest=None` | CONFIRMED |
| TEETH flipped on mutation; sha-restored byte-identical | CONFIRMED |
| Orthogonality: `honest_contract_complete=True AND contract_complete=False` simultaneously; zero 503 sites on `contract_complete` | CONFIRMED |
| Spine at 207 (not below) | CONFIRMED |

All six criteria satisfied by independently-re-run receipt. BUILD SEAL: **MODERATE -> STRONG**.

## F2 / F3 Disposition

### F2 — column_manifest Projection Coverage (Medium, watch-register)

`column_manifest` population is best-effort over the projected frame. A required column in-schema but `select`-projected-out gets no population entry in `column_manifest`. The load-bearing gate — `contract_complete` (schema-membership: `required ∈ schema.column_names()`) — is unaffected. A column present in schema but absent from the current select-projection is still schema-complete and `contract_complete=True`. F2 is a manifest-coverage nuance routed to S9 (live HTTP canary, verified_realized altitude). Does NOT block STRONG. Severity: Medium. [MODERATE | TACTICAL]

### F3 — Empty-String Member Cosmetic (Low, watch-register)

`required_columns=[""]` is pydantic-accepted, yielding `unservable=['']`, `contract_complete=False`. A harmless typed signal — no crash, no silent drop, no data loss. S4 watch item. Does NOT block STRONG. Severity: Low. [PLATFORM-HEURISTIC | TACTICAL]

Neither F2 nor F3 touches the schema-membership gate. Neither introduces a critical or high finding against the build seal.

## Rung Discipline

| Rung | Status |
|------|--------|
| Build seal | **STRONG** — independently-re-run, rite-disjoint from 10x-dev builder |
| Merged status | UNMERGED — operator/releaser holds the merge of PR #161 |
| `verified_realized` | **[UNATTESTED — DEFER-POST-HANDOFF]** — S9 live-HTTP two-sided canary + S10 denylist-retirement; eunomia's, distinct altitude |
| GFR telos proof | DISTINCT ALTITUDE — `.know/telos/gfr.md:79-89`; send-origination round-trip; `verified_realized` = UNATTESTED; NOT discharged by this build |

`built != verified_realized`. This STRONG verdict attests the BUILD SEAL only. It does NOT constitute a merged status, a `verified_realized` attestation, or a GFR telos proof.

## Evidence Summary

| Claim | Evidence | Grade |
|-------|----------|-------|
| RED arm bites (`offer_id` -> `contract_complete=False`) | Re-run receipt: `test_red_arm_declared_unservable_column_fires_typed_signal` PASSED | [STRONG \| TACTICAL] |
| GREEN arm passes (`office_phone` -> `contract_complete=True`) | Re-run receipt: `test_green_arm_declared_served_column_passes` PASSED | [STRONG \| TACTICAL] |
| DOOR two-way (no-decl -> `contract_complete=True`) | Re-run receipt: `test_two_way_door_no_declaration_preserves_today_behavior` PASSED | [STRONG \| TACTICAL] |
| TEETH gate is load-bearing | Mutation `c not in served` -> `c in served`; RED flips; sha256 BEFORE==AFTER | [STRONG \| TACTICAL] |
| D2 orthogonality: zero 503 wiring on `contract_complete` | Grep + direct file read; `contract_complete` at derivation/return sites only; 503 keyed exclusively on `honest_contract_complete=False` | [STRONG \| STRUCTURAL] |
| GFR spine non-regression: 207 passed | Re-run receipt: 207 passed 0.74s; frozen sentinels untouched | [STRONG \| TACTICAL] |
| G-PROPAGATE: `field_contract_maps.py` sole propagation point | Grep across src; no orphan consumer contract; `gid_lookup.py:270` unrelated | [STRONG \| STRUCTURAL] |
| F1 correction: 207 not 105 | Direct measurement from re-run | [STRONG \| TACTICAL] |
| F2 medium finding | Schema-membership gate unaffected by projection; manifest-coverage nuance | [MODERATE \| TACTICAL] |
| F3 low finding | Empty-string pydantic-accepted; harmless typed signal | [PLATFORM-HEURISTIC \| TACTICAL] |

## Cross-Rite Recommendations

| Concern | Recommended Rite | Action |
|---------|-----------------|--------|
| S9 live-HTTP two-sided canary | eunomia (releaser altitude) | Run after operator merge of PR #161; this is the `verified_realized` gate |
| S10 operator denylist retirement | eunomia (releaser altitude) | Post-merge, operator-walked |
| F2 manifest projection coverage | 10x-dev (if addressed) | Tracked at S9 altitude; not a build-seal blocker |
| GFR telos `verified_realized` | review-rite critic (rite-disjoint attester per `.know/telos/gfr.md`) | Distinct initiative, distinct altitude — do not conflate with FM-5 ARM-B |

## Recommended Next Steps

1. **Operator walks the merge of PR #161** — build seal is STRONG; CI all-green (24/24 passing); no stowaways; 0-behind main. Merge is operator-held.
2. **Eunomia routes S9/S10** — post-merge, the live-HTTP two-sided canary (S9) and denylist-retirement (S10) drive `verified_realized`; eunomia's, distinct altitude.
3. **Watch F2 at S9** — manifest projection coverage is a manifest-coverage nuance for the live-HTTP canary to exercise; no code change required pre-merge.
4. **GFR telos (distinct initiative)** — send-origination round-trip (`.know/telos/gfr.md:79-89`) is a separate altitude and separate initiative; do not conflate with this FM-5 ARM-B build seal.

---
*Review mode: FULL | Build seal: MODERATE -> STRONG | Generated by review rite (rite-disjoint from 10x-dev builder)*
*Worktree: /tmp/wt-review-fm5-canary @ ad8817757 | cross_stream_concurrence: true*
