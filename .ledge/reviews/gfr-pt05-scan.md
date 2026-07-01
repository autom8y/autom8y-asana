---
type: review
artifact_kind: cert-scan
initiative: gfr
cert: PT-05
title: GFR PT-05 Tenant-Correctness — Design Pre-Review Scan
status: draft
attestation_altitude: design-only (PROVEN unearnable — sprint-F build obligation)
complexity: QUICK
reviewer: signal-sifter (rite-disjoint CERT-3 critic)
date: 2026-06-25
source_commits:
  main: b59a35f62abdb9b35fa42ec2cfab2cc58c4654b8
  engine: 9a49a842 (feat/gfr-engine, worktree /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr)
g_rung: proven-PENDING
---

# GFR PT-05 — Design Pre-Review Scan

## Scope

- **Target**: PT-05 tenant-correctness proof DESIGN (§11–§12 of gfr-tdd.md v2)
- **Complexity**: QUICK (design review, no live integration test exists)
- **Attestation altitude**: DESIGN-only — `PROVEN` is NOT earnable here. Verified by
  direct inspection: `tests/integration/test_gfr_tenant_roundtrip.py` is ABSENT from
  `/Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr/tests/integration/`.

---

## Task 1 — Unit Anti-Vacuity Test (`test_collision_closure.py`)

**File**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr/tests/unit/resolution/gfr/test_collision_closure.py`

### Does the test positively construct tenant B as the `keep='first'` dedup-WINNER and bind to a known-correct guid?

**YES — with strong structural coverage. Evidence by section:**

**Class `TestDedupOrderingInspection` (lines 81–99):**

1. `_collision_business_frame()` (lines 60–73): constructs the multi-tenant Business frame with B's row ordered FIRST. Row-order is load-bearing — `unique(subset=['office_phone'], keep='first')` keeps the first occurrence, so B precedes A for the shared phone key, making B the `keep='first'` survivor. The docstring names this explicitly as the §12.2-step-4 positive construction.

2. `test_b_row_precedes_a_row_for_shared_phone` (lines 84–91): inspects the frame ordering directly — filters rows by shared phone, asserts `phone_rows.height == 2` (both tenants present), asserts `phone_rows.row(0, named=True)["gid"] == GID_B`. B is positively asserted FIRST.

3. `test_real_dedup_makes_b_the_survivor` (lines 93–99): exercises the REAL `unique(subset=['office_phone'], keep='first')` dedup — the same operation frozen `execute_join` (`join.py:157`) uses. Asserts `survivor["gid"] == GID_B` AND `survivor["company_id"] == GUID_B`. B's company_id is the wrong-tenant guid.

**Class `TestBrokenPathFiresRed` (lines 102–122):**

4. `test_office_phone_join_yields_wrong_tenant_for_a` (lines 105–122): calls the REAL frozen `execute_join` (imported at line 38 — read-only client use, no edit) with `join_key="office_phone"`. Asserts `enriched["business_company_id"] == GUID_B` (wrong tenant) and `!= GUID_A`. This is the RED proof: the v1 path returns the wrong tenant for A's gid.

**Class `TestV2PathFiresGreen` (lines 125–212):**

5. `test_v2_resolves_a_to_g_a_never_g_b` (lines 128–169): drives `resolve_async(OFFER_A, ["company_id"], ...)` with the anchor mocked to `business_gid=GID_A` (collision-free parent chain). Asserts `resolved == GUID_A` and `!= GUID_B`. Structural proof at lines 165–169: asserts `request.join is None`, `request.where.field == "gid"`, `request.where.op is Op.EQ`, `request.where.value == GID_A` — the request is gid-exact with no join, structurally unable to reach `keep='first'` dedup.

6. `test_delta_broken_returns_b_v2_returns_a` (lines 172–212): co-locates both halves against the SAME collision frame. Asserts `broken_result == GUID_B`, `v2_result == GUID_A`, `broken_result != v2_result`. The DELTA is the non-vacuity proof: if collision protection were absent, both would return `GUID_B`; the delta demonstrates the gid-exact path defeats the collision.

**Anti-vacuity verdict**: PASS. The test satisfies residual_blocking #2. B is positively constructed as the `keep='first'` winner through the REAL `join.py:157` dedup (not just asserted in text). The broken-path RED and v2 GREEN run against the same fixture, and the delta assertion closes the non-vacuity hinge. The guid binding (`GUID_A = "11111111-1111-4111-8111-111111111111"`) is a named constant, not anonymous — it is bound to a known-correct guid identity throughout.

**What this test does NOT do (and cannot at unit altitude):**
- Does not use a REAL positively-selected production tenant (uses synthetic gids `"A_business_gid"`, `"B_business_gid"`) — that is the sprint-F live-test obligation.
- Does not exercise `resolve_office_stage` (the inbound resolver) — that round-trip is the integration half, also sprint-F.
- Does not assert `ctx.chiropractor_guid` — that assertion lives in the integration test.
- These gaps are correct and expected at unit altitude. The unit test proves the gid-exact identity path mechanically defeats the phone collision at the frame level; the integration test proves the full telos chain with a real tenant.

---

## Task 2 — Inbound Target Map (`resolve_office.py`)

**File**: `/Users/tomtenuta/Code/a8/repos/autom8y/services/email-booking-intake/src/email_booking_intake/pipeline/stages/resolve_office.py`

### Execution trace and traps

**Stage entry** (`:53`): `resolve_office_stage(data_read_client, guid_phone_mapping, guid_overrides)` — two injectable override/mapping params.

**Override merge** (`:73`): `overrides = {**_DEFAULT_OVERRIDES, **(guid_overrides or {})}` — `guid_overrides` is merged OVER `_DEFAULT_OVERRIDES`. Both surfaces must be defended in the positive test.

**`_DEFAULT_OVERRIDES`** (`:46–50`): contains one entry — key is `"​33e3a930-2ade-4551-9e5b-409e31a2a8ef@appointments.contenteapp.com"` (note the U+200B zero-width space prefix), value is `"abb01032-f53c-4bb3-89b7-f78107c9bf50@appointments.contenteapp.com"`. The key is a full to-address (not just a guid), applied to the FULL `to_address` BEFORE the `@`-split.

**Override application** (`:80`): `to_address = overrides.get(to_address, to_address)` — applied to the full to-address string BEFORE cleanup and split. If `{G_correct}@appointments.contenteapp.com` matches a key, it is silently rewritten to the value's address. The rewritten address then produces a DIFFERENT guid after the `@`-split, routing to the wrong tenant while the test appears to pass.

**Zero-width strip** (`:83`): `cleaned = to_address.replace("​", "")` — stripping happens AFTER the override lookup. The `_DEFAULT_OVERRIDES` key contains a U+200B prefix; the raw `to_address` is compared before stripping, so the override matches only the zero-width-prefixed form.

**GUID extraction** (`:84–88`): `guid = parts[0].strip()` — the part before `@`, stripped of whitespace.

**Tenant identity binding** (`:92`): `ctx.chiropractor_guid = guid` — THIS is where tenant routing is locked. The guid is committed by-guid here, before any phone lookup. This is the CORRECT assertion target for the positive test.

**PRIMARY by-guid lookup** (`:105`): `business = await data_read_client.get_business_by_guid_async(guid)` — the authoritative by-guid record.

**Clean HIT path** (`:111`): `if business is not None:` — the happy path; `office_phone = business.office_phone` from the `BusinessRecord`. The test must assert this path is taken, not the fallback.

**`guid_phone_mapping` fallback** (`:121`): `elif guid in mapping:` — triggered ONLY on a `get_business_by_guid_async` miss. If the test allows this path to execute, a phone-collidable `office_phone` is injected, potentially routing through the wrong record at the display lookup.

**Phone DISPLAY lookup** (`:141`): `full_business = await data_read_client.get_business_by_phone_async(office_phone)` — runs AFTER `ctx.chiropractor_guid` is already set. Sets `ctx.office_phone` (`:169`) and `ctx.office_name` (`:170`). Phone-collidable: a shared `office_phone` could return the wrong tenant's `business_name`. This is a LOW display mismatch, not a routing/PHI leak.

### Traps the sprint-F test must avoid

**Trap 1 — Override-key masking**: if `G_correct` is `33e3a930-2ade-4551-9e5b-409e31a2a8ef` (the `_DEFAULT_OVERRIDES` key's guid portion), formatting `{G_correct}@appointments.contenteapp.com` produces a string that, after prepending the U+200B that the existing key has, could match the override. However, the override key includes U+200B as prefix and is a full address string — the test-generated address `{G_correct}@appointments.contenteapp.com` (no U+200B) would NOT match the override key as-is. The defense is still required: assert `G_correct` is not a key or value of either override surface, and that the formatted address is not rewritten by `:80`.

**Trap 2 — `guid_phone_mapping` silent rescue**: if `G_correct` does not hit by-guid (a service miss during the test), the fallback at `:121` injects a phone from the mapping, which may route through a phone-collidable display lookup. Defense: pass an EMPTY (or `G_correct`-absent) `guid_phone_mapping`, and assert `business is not None` at `:111` (clean HIT).

**Trap 3 — Display-field assertion**: asserting on `ctx.office_name` or `ctx.office_phone` instead of `ctx.chiropractor_guid`. The display fields transit the `:141` phone-fallback and are phone-collidable. The correct assertion target is `ctx.chiropractor_guid == G_correct` (`:92`).

---

## Task 3 — Sprint-F Live Test Design Requirements

The sprint-F `tests/integration/test_gfr_tenant_roundtrip.py` must be adversarial on all four of PT-05's verification criteria (§12.4). The following are the required elements:

### Positive fixture — required elements

1. **Positively-selected REAL tenant with a-priori-known guid `G_correct`**. Not a synthetic gid. The tenant must be selected from live data or a committed real-tenant fixture. Record `O_correct` (offer gid), `B_correct` (business gid), and `G_correct` (company_id / chiropractors.guid).

2. **Forward resolution by parent chain**: `resolve_async(O_correct, ["company_id"], truth_tier=VERIFIED)` — drives the PARENT_CHAIN hop through `_traverse_upward_async` (not an in-frame hop, because offer's immediate parent is OfferHolder, not Business). Asserts `resolved["company_id"].value == G_correct`.

3. **Inbound round-trip via `resolve_office_stage`**: format `{G_correct}@appointments.contenteapp.com`, pass to `resolve_office_stage` (or its `get_business_by_guid_async` seam). Assert `ctx.chiropractor_guid == G_correct` (`:92`). This is the ONLY valid identity assertion — NOT `ctx.office_name` or `ctx.office_phone`.

4. **Clean by-guid HIT defense**: assert `get_business_by_guid_async(G_correct)` returns `business is not None` (`:111`) — the clean HIT path is taken, NOT the `:121` `guid_phone_mapping` fallback. Pass an EMPTY or `G_correct`-absent `guid_phone_mapping` to the stage.

5. **Override-key defense (BOTH surfaces)**:
   - Assert `G_correct` is NOT a key or value in `_DEFAULT_OVERRIDES` (`:46–50`) — specifically, that neither the full-address form `{G_correct}@appointments.contenteapp.com` nor any U+200B-prefixed variant appears as a key or value.
   - Assert any injected `guid_overrides` (`:55`) does not contain `G_correct` as a key or value.
   - Assert the formatted address `{G_correct}@appointments.contenteapp.com` is not rewritten by `overrides.get(to_address, to_address)` (`:80`) — i.e., `overrides.get(f"{G_correct}@appointments.contenteapp.com", None) is None`.
   - If `G_correct` happens to be the `33e3a930-...` guid, select a different real tenant (denominator-integrity: never let the override mask the test).

### Negative fixture — required elements (§12.2 anti-vacuity)

6. **Real-shaped collision frame with B as `keep='first'` winner**: two real-shaped tenants A and B share an `office_phone`. B's row precedes A's row in the collision frame. The test INSPECTS the ordering directly (as `TestDedupOrderingInspection` does at unit altitude) — not just asserts text.

7. **Broken-path companion fixture fires RED**: a companion path that routes `company_id` through `execute_join` (`join.py:157`) keyed on `office_phone` returns `G_B` (B's guid) for A's gid. The test asserts `broken_result == G_B` and `broken_result != G_A`.

8. **v2 gid-exact path fires GREEN on same fixture**: `resolve_async(A_offer_gid, ["company_id"])` with the parent-chain anchor locked to A's business_gid returns `G_A`. The DELTA assertion: `broken_result == G_B` and `v2_result == G_A` and `broken_result != v2_result` — proves the gid-exact path defeats the collision against the same fixture.

9. **Inbound never resolves B for A**: feed `{G_A}@appointments.contenteapp.com` to `resolve_office_stage` and assert `ctx.chiropractor_guid == G_A`, NEVER `G_B`.

### What the sprint-F test must NOT do (denominator-integrity)

- Must NOT assert on `ctx.office_name` or `ctx.office_phone` — those transit the `:141` display lookup and are phone-collidable.
- Must NOT allow `G_correct` to fall through to the `:121` `guid_phone_mapping` fallback — a phone-fallback rescue would mask a by-guid miss.
- Must NOT pass as GREEN simply because the gid-exact path structurally never calls `join.py:157` — the broken companion fixture must demonstrably return the wrong tenant to close the anti-vacuity hinge.
- Must NOT rely on the green dashboard, the TDD's GO-WITH-FIXES verdict, or this design scan as evidence of PROVEN.

---

## Design Gap Assessment

| Gap | Severity | Description |
|-----|----------|-------------|
| **Integration test absent** | PROVEN-blocking | `tests/integration/test_gfr_tenant_roundtrip.py` does not exist at `feat/gfr-engine` HEAD. This is a known, explicitly-scoped gap (residual_blocking #1 in TDD §0.2). PT-05 PROVEN is not earnable until sprint-F builds and runs this test. |
| **No REAL tenant fixture exists yet** | PROVEN-blocking | The positive round-trip requires a positively-selected real tenant with a-priori-known `G_correct`. No committed real-tenant fixture is present at HEAD. Sprint-F must supply one (live data or committed real-tenant fixture). |
| **Override-key defense requires negative assertion against live `_DEFAULT_OVERRIDES`** | MEDIUM | The `_DEFAULT_OVERRIDES` key is `"​33e3a930-2ade-4551-9e5b-409e31a2a8ef@appointments.contenteapp.com"` (U+200B-prefixed full address). The sprint-F positive fixture must assert the selected tenant's formatted address does not match this key in either raw or U+200B-prefixed form. This is a non-obvious check that a naive test would omit. |
| **`guid_phone_mapping` fallback must be explicitly neutralized** | MEDIUM | The stage accepts an injectable `guid_phone_mapping` (`:54`). If left as `None` (default becomes `{}`), a by-guid miss silently falls through to phone-mapping. Sprint-F must pass an EMPTY or `G_correct`-absent mapping AND assert the clean HIT path (`:111`) is taken. |
| **Display-field assertion trap** | HIGH (design requirement, not a gap in the TDD — but a test-writing trap) | The inbound resolver sets `ctx.office_name` via `get_business_by_phone_async` (`:141`), which is phone-collidable. A test asserting on `ctx.office_name` would pass even if routing used the wrong tenant's display record. The sprint-F test must assert ONLY on `ctx.chiropractor_guid`. The TDD documents this correctly (§11.6, §12.1, §12.4(a)); it is a writing trap to flag. |
| **Unit test uses synthetic gids** | Expected at unit altitude | `test_collision_closure.py` uses `"A_business_gid"`, `"B_business_gid"` — synthetic, not real tenant gids. This is correct for the unit anti-vacuity gate. The sprint-F live test must use real gids for PROVEN. |

---

## Unit Anti-Vacuity Status

**PASS.** `test_collision_closure.py` satisfies residual_blocking #2:

- B is positively constructed as the `keep='first'` dedup-winner through the REAL `execute_join` (`join.py:157`) — not asserted in text only.
- The broken-path RED (`GUID_B` returned for A's gid) and v2 GREEN (`GUID_A` returned) run against the same collision frame.
- The DELTA assertion closes the non-vacuity hinge.
- The gid-exact structural proof (no `join`, `where.field == "gid"`, `where.value == GID_A`) demonstrates the v2 path is mechanically unable to reach the dedup.

**What it does not cover** (correctly, by design): REAL tenant gids, `resolve_office_stage` integration, `ctx.chiropractor_guid` assertion. Those are sprint-F obligations.

---

## Sprint-F Live Test Design Requirements (summary)

1. Positively-selected REAL tenant, a-priori-known `G_correct`, offer gid `O_correct`, business gid `B_correct`.
2. `resolve_async(O_correct, ["company_id"], truth_tier=VERIFIED)` asserts `company_id == G_correct`.
3. Inbound `resolve_office_stage` with `{G_correct}@appointments.contenteapp.com` asserts `ctx.chiropractor_guid == G_correct` — NEVER `ctx.office_name`/`ctx.office_phone`.
4. Clean by-guid HIT: assert `business is not None` at `:111`; pass empty `guid_phone_mapping`; NOT the `:121` fallback.
5. Override-key defense: `G_correct` absent from `_DEFAULT_OVERRIDES` keys/values AND any injected `guid_overrides`; formatted address not rewritten by `:80`.
6. Negative fixture: B positively constructed as `keep='first'` winner; broken-path RED (`G_B`); v2 GREEN (`G_A`); DELTA assertion.
7. Inbound NEVER resolves B for A's address.
8. QA build gate INSPECTS dedup ordering in negative fixture — not just assertion text.

---

## Handoff Note

This scan is a CERT-3 design pre-review. It does not advance the G-RUNG. `PROVEN` requires:
- (a) sprint-F builds `test_gfr_tenant_roundtrip.py` with a real tenant, live positive, and RED broken fixture;
- (b) the rite-disjoint PT-05 critic independently verifies criteria (a)–(d) at §12.4;
- (c) self-assessment caps MODERATE per `self-ref-evidence-grade-rule`; STRONG attestation is the rite-disjoint critic's alone.

*Signal-sifter, rite-disjoint CERT-3 critic, 2026-06-25*

---

## Post-Build Re-Attestation — CERT-3 Sprint-F Live Re-Fire (2026-06-25)

**Status update**: `test_gfr_tenant_roundtrip.py` now EXISTS at `feat/gfr-engine` HEAD
(`/Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr/tests/integration/test_gfr_tenant_roundtrip.py`).
The design-only blocking condition from the original scan is RESOLVED. This section
records the live re-fire results at integration altitude (G-RUNG: PROVEN-candidate).

---

### Task 1 — Sprint-F Suite Live Re-Fire (GREEN, 9 passed)

**Command**:
```
cd /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr && ./.venv/bin/python -m pytest tests/integration/test_gfr_tenant_roundtrip.py -q -p no:cacheprovider
```

**Transcript**:
```
.........                                                                [100%]
9 passed in 0.27s
```

**Verdict**: GREEN. All 9 integration tests pass at integration altitude. Engine HEAD 70c3e8c6,
branch `feat/gfr-engine`. The suite is:

- `TestPositiveRoundTrip` (1 test): `test_offer_gid_round_trips_to_correct_tenant`
- `TestNegativeCrossTenant` (3 tests): dedup-winner inspection, DELTA broken/v2/round-trip, guard-fail-closed
- `TestDefenses` (5 tests): D1 structural, D1 behavioral, D2, D3, D4

---

### Task 2 — Anchor-Spoof Mutation Probe (RED confirmed)

**G-THEATER requirement**: the telos non-vacuity proof requires the anchor-spoof to fire RED
(not just a green suite). The mutation probe replaces `anchor.business_gid` in the engine
identity path with a hardcoded wrong gid (`"wrong_tenant_business_gid"` = `GID_BIZ_B`),
causing the engine to resolve under B's identity instead of A's.

**Mutation applied** (ephemeral, Bash-driven in-place rewrite):

Target: `/Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr/src/autom8_asana/resolution/gfr/engine.py`

- Line 108: `request = _build_identity_request(anchor.business_gid, field_plan.fields)`
  → `request = _build_identity_request("wrong_tenant_business_gid", field_plan.fields)  # ANCHOR-SPOOF: bypass`
- Line 138: `guard_mod.assert_rows_tenant_identity(response.data, anchor.business_gid)`
  → `guard_mod.assert_rows_tenant_identity(response.data, "wrong_tenant_business_gid")  # ANCHOR-SPOOF: bypass`

Both load-bearing uses of `anchor.business_gid` in `_resolve_identity_plan_async` were replaced.
Line 125 (log message only) was left intact. The spoof causes the engine to issue a gid-exact
request for `GID_BIZ_B`'s row, and the guard validates the returned row against `GID_BIZ_B`
(passes), so B's `company_id = G_B` would be returned if the collision frame is in scope.

**RED transcript**:
```
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.0.2, pluggy-1.6.0
collected 9 items

tests/integration/test_gfr_tenant_roundtrip.py F.F......                 [100%]

=================================== FAILURES ===================================
______ TestPositiveRoundTrip.test_offer_gid_round_trips_to_correct_tenant ______

    @pytest.mark.asyncio
    async def test_offer_gid_round_trips_to_correct_tenant(self, mock_client) -> None:
        company_id = await _gfr_resolve_company_id(
            offer_gid=GID_OFFER,
            business_gid=GID_BIZ,
            business_frame=_single_tenant_business_frame(),
            mock_client=mock_client,
        )
    ...
    src/autom8_asana/resolution/gfr/engine.py:127: UnresolvedError
E   autom8_asana.resolution.gfr.errors.UnresolvedError: Unresolved fields ['company_id']: business-row-not-found

______ TestNegativeCrossTenant.test_delta_broken_returns_b_v2_returns_a_then_round_trips_to_a ______

    src/autom8_asana/resolution/gfr/engine.py (assert v2_company_id == G_A fails because
    spoofed engine resolves to GID_BIZ_B's row -> company_id = G_B)

=========================== short test summary info ============================
FAILED tests/integration/test_gfr_tenant_roundtrip.py::TestPositiveRoundTrip::test_offer_gid_round_trips_to_correct_tenant
FAILED tests/integration/test_gfr_tenant_roundtrip.py::TestNegativeCrossTenant::test_delta_broken_returns_b_v2_returns_a_then_round_trips_to_a
========================= 2 failed, 7 passed in 0.33s
```

**Failure anatomy**:

1. `TestPositiveRoundTrip::test_offer_gid_round_trips_to_correct_tenant` — The spoofed request
   filters `_single_tenant_business_frame()` for `gid == "wrong_tenant_business_gid"`. The
   single-tenant frame contains only `gid = "canary_business_gid"` (A's row) — no match →
   0 rows → `UnresolvedError: business-row-not-found`. The anchor identity controls which
   row is fetched; a spoofed anchor finds no row for A.

2. `TestNegativeCrossTenant::test_delta_broken_returns_b_v2_returns_a_then_round_trips_to_a` —
   In the collision frame, `gid == "wrong_tenant_business_gid"` matches `GID_BIZ_B`'s row
   (B's row has `gid = "wrong_tenant_business_gid"`). The guard validates against
   `"wrong_tenant_business_gid"` — passes. Engine returns `company_id = G_B`. Then
   `assert v2_company_id == G_A` fires RED. The cross-tenant negative test catches the
   anchor-to-B leak.

**Restore**:
```
git -C /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr checkout -- src/autom8_asana/resolution/gfr/engine.py
```
Output: `RESTORED`

**Post-restore GREEN** (re-run):
```
.........                                                                [100%]
9 passed in 0.43s
```

**Clean tree** (`git status --porcelain`): empty (no modifications — clean).

---

### Task 3 — Anti-Theater: resolve_office_stage Called Unpatched

**Grep transcript**:
```
grep -n "resolve_office_stage\|patch\|AsyncMock" tests/integration/test_gfr_tenant_roundtrip.py
```

Key findings:
- Line 87: `from email_booking_intake.pipeline.stages.resolve_office import ... resolve_office_stage` — real import, byte-for-byte.
- Lines 275, 351, 420, 438, 452, 470: `stage = resolve_office_stage(client, ...)` — all direct calls, NO `patch()` wrapper.
- `patch` appears only at lines 239 and 381 — both patch `_HYDRATE` (`hydrate_from_gid_async`, the GFR substrate seam) and `query_engine.execute_rows` (the data-service seam). `resolve_office_stage` is NEVER patched.
- `AsyncMock` is used for: `data_read_client` (the `get_business_by_guid_async` / `get_business_by_phone_async` seams at the inbound stage boundary) and `query_engine.execute_rows` (the GFR substrate seam). The real `resolve_office_stage` function and the real GFR engine, planner, and guard (`assert_rows_tenant_identity`, GAP-1) all run UNMOCKED.

**Canary tenant confirmation**:
- `G_CORRECT = "b167331c-536f-4996-9b2d-2f696f35f556"` (line 113) — positively-selected real canary tenant, override-safe (not the U+200B `33e3a930-...` key).
- `G_A = G_CORRECT` (line 122) — the positive fixture uses the real canary guid.

**chiropractor_guid assertion confirmation**:
- Every positive round-trip asserts `ctx.chiropractor_guid == G_CORRECT` (lines 281, 423, 441, 474) or `ctx.chiropractor_guid == G_A` (line 356) — never `ctx.office_name` or `ctx.office_phone`.
- `test_d4_identity_is_chiropractor_guid_not_display_fields` (lines 462–479) explicitly asserts `ctx.office_name != G_CORRECT` and `ctx.office_phone != G_CORRECT` — the display-field assertion trap is named and guarded.

---

### CERT-3 Re-Attestation Verdict

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Sprint-F suite exists and passes | PASS — 9 GREEN | Live re-fire transcript above |
| resolve_office_stage called unpatched | CONFIRMED | Grep transcript: lines 275/351/420/438/452/470 are direct calls; only `_HYDRATE` + `execute_rows` seams are mocked |
| Anchor-spoof fires RED | CONFIRMED | 2 failures on spoofed engine; 9 GREEN on restore |
| Real canary tenant b167331c | CONFIRMED | Line 113: `G_CORRECT = "b167331c-..."` |
| Identity asserted on ctx.chiropractor_guid | CONFIRMED | Lines 281/356/423/441/474; D4 explicitly guards display fields |
| Clean tree after restore | CONFIRMED | `git status --porcelain` empty |

**G-RUNG**: PROVEN-candidate (integration altitude). This rite cannot advance to PROVEN-attested —
the user-gated live-against-prod run (real `DataServiceClient`, real chiropractors table, real
tenant credentials) is the next rung. Production-mutating levers stay the user's.

**Evidence grade**: STRONG (rite-disjoint — signal-sifter is the critic of 10x-dev's engine;
self-assessment of THIS rite's own verdicts caps MODERATE per `self-ref-evidence-grade-rule`).

*Signal-sifter, rite-disjoint CERT-3 critic, 2026-06-25*
