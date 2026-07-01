---
type: review
artifact_kind: cert-verdict
initiative: gfr
cert: PT-05
title: GFR PT-05 Tenant-Correctness — Critic Verdict (PROVEN-candidate re-attested)
status: accepted
reviewer: pattern-profiler (rite-disjoint CERT-3 critic)
date: 2026-06-25
g_rung: PROVEN-candidate
attestation_altitude: INTEGRATION (sprint-F live suite + anchor-spoof RED confirmed)
grandeur_anchor: "GFR lets any fleet caller resolve a gid to schema-declared fields BY NAME with entity-tree topology fully hidden."
verdict: PROVEN-candidate
proven_attested_remainder: USER-GATED (real DataServiceClient + real chiropractors table + real tenant creds + real mint producer)
anchor_spoof_red_receipt: "2 FAILED, 7 passed — TestPositiveRoundTrip::test_offer_gid_round_trips_to_correct_tenant (UnresolvedError: business-row-not-found) + TestNegativeCrossTenant::test_delta_broken_returns_b_v2_returns_a_then_round_trips_to_a (v2_company_id == G_A fails, resolves to G_B instead)"
post_restore_green: "9 passed in 0.43s; git status --porcelain empty"
---

# GFR PT-05 — Tenant-Correctness Proof: Critic Verdict

**PROVEN-candidate re-attested. Rung: PROVEN-candidate (integration altitude).**
**PROVEN-attested is explicitly deferred to the USER-GATED live-against-prod run.**

This verdict is produced by the rite-disjoint pattern-profiler critic (CERT-3).
It supersedes the design-altitude PRE-REVIEW verdict dated 2026-06-25. Sprint-F
has been built and independently verified at integration altitude. The G-RUNG
advances from proven-PENDING to PROVEN-candidate. PROVEN-attested cannot be
reached by this rite — it requires the user-gated live-against-prod run.

---

## CERT-3 Re-Attestation: PROVEN-candidate

### Independent Verification Performed (this critic)

The following were verified by direct file reads, not by prose acceptance:

1. `test_gfr_tenant_roundtrip.py` EXISTS at
   `/Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr/tests/integration/test_gfr_tenant_roundtrip.py`.
   The file is 480 lines; the test module is self-documenting with explicit
   boundary statements naming the PROVEN-attested remainder.

2. `resolve_office_stage` is called UNPATCHED. Grep of `test_gfr_tenant_roundtrip.py`
   confirms `resolve_office_stage` is imported at line 87 as a real import
   (`from email_booking_intake.pipeline.stages.resolve_office import ... resolve_office_stage`)
   and called directly at lines 275, 351, 420, 438, 452, 470 — ZERO `patch()` wrappers
   on the stage function itself. The only `patch()` calls cover `_HYDRATE`
   (`hydrate_from_gid_async`) and `query_engine.execute_rows` — the substrate seams,
   not the stage or engine.

3. `ctx.chiropractor_guid` is the sole identity assertion surface. Grep confirms
   `ctx.chiropractor_guid == G_CORRECT` or `== G_A` at lines 281, 356, 423, 441, 474.
   `test_d4_identity_is_chiropractor_guid_not_display_fields` (lines 462-479)
   explicitly guards `ctx.office_name != G_CORRECT` and `ctx.office_phone != G_CORRECT` —
   the display-field assertion trap is named, tested, and closed.

4. Real canary tenant `b167331c-536f-4996-9b2d-2f696f35f556` bound at line 113
   (`G_CORRECT = "b167331c-536f-4996-9b2d-2f696f35f556"`). This is NOT the U+200B
   override key (`33e3a930-...`); the defense test `test_d1_g_correct_is_not_the_default_override_key`
   asserts `override_key_guid != G_CORRECT` and iterates every `_DEFAULT_OVERRIDES`
   key to assert `G_CORRECT not in key`.

5. Engine `engine.py` independently read. `anchor.business_gid` appears at:
   - Line 108: `request = _build_identity_request(anchor.business_gid, field_plan.fields)`
   - Line 138: `guard_mod.assert_rows_tenant_identity(response.data, anchor.business_gid)`
   Both load-bearing uses are present and unmodified (clean engine). The engine is
   at the state the mutation probe reverted to.

---

## Anchor-Spoof RED Receipt

**G-THEATER proof**: the suite non-vacuity was established by the mutation probe
described in `gfr-pt05-scan.md` §Post-Build Re-Attestation Task 2.

**Mutation**: lines 108 and 138 of `engine.py` — both uses of `anchor.business_gid`
in `_resolve_identity_plan_async` — were replaced with the hardcoded wrong gid
`"wrong_tenant_business_gid"` (= `GID_BIZ_B`), causing the engine to request B's
row and validate against B's gid.

**RED result** (2 failed, 7 passed):

- `TestPositiveRoundTrip::test_offer_gid_round_trips_to_correct_tenant`:
  The spoofed request filtered `_single_tenant_business_frame()` for
  `gid == "wrong_tenant_business_gid"` — no row matched (frame contains only
  `"canary_business_gid"`) — 0 rows — `UnresolvedError: business-row-not-found`.
  Failure mechanism: the anchor identity controls which row is fetched; a spoofed
  anchor finds no row for A's business gid. The test DOES NOT pass vacuously.

- `TestNegativeCrossTenant::test_delta_broken_returns_b_v2_returns_a_then_round_trips_to_a`:
  In the collision frame, `gid == "wrong_tenant_business_gid"` matched `GID_BIZ_B`'s
  row; the guard validated against `"wrong_tenant_business_gid"` — passed; engine
  returned `company_id = G_B`. Then `assert v2_company_id == G_A` fired RED. The
  cross-tenant negative test caught the anchor-to-B leak.

**Restore**: `git checkout -- src/autom8_asana/resolution/gfr/engine.py`
**Post-restore GREEN**: 9 passed in 0.43s; `git status --porcelain` empty (clean tree).

The probe is non-vacuous: anchor identity is the load-bearing variable. Spoofing it
causes EXACTLY the tests that prove tenant-correctness to fail RED, and only those.
The 7 tests that did not fail are the defense tests (D1-D4) and the dedup-inspection
test — which are structurally independent of anchor identity spoofing (they test the
stage in isolation or the frame construction). This is the correct failure topology.

---

## Original G-THEATER Criteria (re-confirmed at integration altitude)

### Criterion 1 — Positively-selected REAL tenant: CONFIRMED

`G_CORRECT = "b167331c-536f-4996-9b2d-2f696f35f556"` (line 113) — a real canary
tenant guid, a-priori-known, not synthetic. Denominator-integrity defense verified:
`test_d1_g_correct_is_not_the_default_override_key` asserts the canary guid is not
the U+200B `_DEFAULT_OVERRIDES` key.

### Criterion 2 — Negative fixture positively constructed, DELTA fires RED: CONFIRMED

`_collision_business_frame()` places `GID_BIZ_B`'s row FIRST (line 200), making B
the `keep='first'` dedup-winner. `test_b_is_positively_seeded_as_dedup_winner`
inspects the frame ordering directly (line 305: `assert phone_rows.row(0, named=True)["gid"] == GID_BIZ_B`)
and exercises the SAME dedup (`frame.unique(subset=["office_phone"], keep="first")`).
`test_delta_broken_returns_b_v2_returns_a_then_round_trips_to_a` calls the REAL
frozen `execute_join` (`join.py:157`) and asserts `broken_company_id == G_B` (RED
broken) and `v2_company_id == G_A` (GREEN v2) with explicit `assert broken_company_id != v2_company_id`.

### Criterion 3 — ctx.chiropractor_guid, not display fields: CONFIRMED

Five assertion sites in the integration suite assert on `ctx.chiropractor_guid`.
`test_d4` explicitly guards the display-field trap: `ctx.office_name != G_CORRECT`,
`ctx.office_phone != G_CORRECT`.

### Criterion 4 — Override-key defense: CONFIRMED

`test_d1_g_correct_is_not_the_default_override_key` asserts the canary is not in
`_DEFAULT_OVERRIDES`. `test_d1_default_override_remap_does_not_fire_for_g_correct`
runs with default overrides ACTIVE (`guid_overrides` omitted) and asserts
`ctx.chiropractor_guid == G_CORRECT` — behavioral proof the U+200B remap did not fire.
`test_d2_injected_override_for_other_key_does_not_touch_g_correct` covers the
injected-override surface.

---

## False Positives Dismissed

None. All scan signals remain validated. The scan's post-build re-attestation
(§Post-Build Re-Attestation, 2026-06-25) is internally consistent with the engine
source and test source as independently read by this critic.

---

## Rung Statement

**Rung: PROVEN-candidate (integration altitude).**

This rite advances the G-RUNG from proven-PENDING to PROVEN-candidate.

The rung PROVEN-candidate is earned because:
- Sprint-F integration test exists, has run GREEN (9 passed) at engine HEAD 70c3e8c6.
- `resolve_office_stage` is exercised unpatched — real inbound code byte-for-byte.
- Real canary tenant `b167331c` is the positive fixture; `ctx.chiropractor_guid` is
  the sole identity assertion surface.
- Anchor-spoof mutation probe fired RED (2 failures) — non-vacuous proof.
- Post-restore GREEN (9 passed); clean tree.

The rung PROVEN-attested is NOT reached. It requires all of:
- A real `DataServiceClient` (not `AsyncMock`) hitting the live `get_business_by_guid_async`
  against the real chiropractors table.
- Real tenant credentials (not canary-shaped mock records).
- Real mint producer (currently unbuilt — telos NOTE-4 / R-6).
- The rite-disjoint CERT-3 critic independently reviews the live run output.

Production-mutating levers stay the user's (MINE per G-THEATER). This rite
CANNOT round up to PROVEN-attested.

The rungs merged / live / protecting-prod are user-gated (MINE).

---

## Evidence Grade

This verdict is `[STRUCTURAL | STRONG]` on the tenant-correctness attestation.
The pattern-profiler critic is rite-disjoint from 10x-dev (the engine author) and
from signal-sifter (the scan author). The STRONG ceiling is reachable at integration
altitude for engine verdicts by a rite-disjoint critic per the STANDING GRANT.
Self-assessment of THIS rite's own verdicts caps MODERATE per `self-ref-evidence-grade-rule`.

---

## Design-Altitude Verdict (archived, superseded)

The design-altitude PRE-REVIEW verdict (DESIGN-SOUND, proven-PENDING, 2026-06-25)
is superseded by this re-attestation. Its findings (all four G-THEATER criteria
DESIGN-SOUND; sprint-F routing items; PROVEN-blocking gaps) were correct and have
been closed by the sprint-F build. The sprint-F routing items are now confirmed
implemented and verified. No design-altitude finding requires re-opening.

---

*pattern-profiler, rite-disjoint CERT-3 critic, 2026-06-25*
*CERT-3 re-attestation — PROVEN-candidate*
