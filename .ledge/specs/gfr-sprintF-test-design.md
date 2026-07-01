---
type: spec
status: draft
slug: gfr-sprintF-test-design
title: "GFR Sprint-F Round-Trip Test Design — TEST HOME fork resolution + positive/negative/defense spec"
authored_by: architect (10x-dev) — design only; implementation is principal-engineer's, attestation is the rite-disjoint review rite's
authored_at: 2026-06-25
initiative_slug: gfr
rite: 10x-dev
code_truth_anchor: |
  asana engine worktree /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr @ feat/gfr-engine HEAD b15c5259;
  EBI inbound target /Users/tomtenuta/Code/a8/repos/autom8y/services/email-booking-intake @ on-disk 2026-06-23.
self_ref_cap: MODERATE
exit_artifact: tests/integration/test_gfr_tenant_roundtrip.py  # in autom8y-asana
---

# GFR Sprint-F Round-Trip Test Design

> **Grandeur anchor (verbatim):** GFR lets any fleet caller resolve a gid to schema-declared
> fields BY NAME with entity-tree topology fully hidden. The rung this procession drives is
> PROVEN-candidate: sprint-F proves the realization predicate — an Offer gid resolves
> `company_id` (== `chiropractors.guid`), the minted `{guid}@appointments.contenteapp.com`
> round-trips through inbound `resolve_office_stage` to the CORRECT tenant — proven ONLY by a
> live positive on a positively-selected REAL tenant with an a-priori-known guid AND a
> deliberately-broken cross-tenant fixture (tenant B positively seeded as the keep='first'
> dedup-winner) firing RED, never by a green suite alone.

This spec resolves the **TEST HOME fork** (the cross-repo, no-shared-import-path problem),
fixes the **BOUNDARY** (what is mocked in-session vs. what the user-gated live run adds), and
specifies the **POSITIVE / NEGATIVE / DEFENSE** designs the build must encode. It is a design
artifact only; the build is principal-engineer's, PROVEN-attestation is the rite-disjoint
review rite's, and the live-against-prod run is the user's.

---

## 0. Ground truth (SVR — verified at HEAD, this pass)

Every load-bearing claim below was directly inspected this pass (not carried from frame/swarm).

- **Inbound target signature** — `resolve_office_stage(data_read_client, guid_phone_mapping=None, guid_overrides=None)`
  at `email-booking-intake/src/email_booking_intake/pipeline/stages/resolve_office.py:53`. Flow verified:
  overrides applied to FULL `ctx.to` address (`:80`) BEFORE zero-width strip + `@`-split (`:83-84`);
  `guid = parts[0].strip()` (`:88`); **`ctx.chiropractor_guid = guid` (`:92`)**;
  `business = await data_read_client.get_business_by_guid_async(guid)` (`:105`); on `None` →
  `elif guid in mapping` fallback (`:121`) → else `OfficeResolutionError` (`:131`). Phone lookup
  (`:141`) writes ONLY `ctx.office_phone` / `ctx.office_name` display fields (`:149-170`).
- **`data_read_client` is structurally an AsyncMock-able port** — EBI's own `test_resolve_office.py`
  passes `AsyncMock()` for the client and an `AsyncMock` with `.office_phone`/`.business_name` for the
  `BusinessRecord` (`test_resolve_office.py:39-42, 49-52`). The round-trip LOGIC is testable in-process
  with no live creds — this is the established EBI pattern, not a novel mock.
- **Override trap** — `_DEFAULT_OVERRIDES` (`resolve_office.py:46-50`) has exactly one
  U+200B-prefixed key `"​33e3a930-2ade-4551-9e5b-409e31a2a8ef@appointments.contenteapp.com"`.
  `overrides = {**_DEFAULT_OVERRIDES, **(guid_overrides or {})}` (`:73`).
- **Canary real-tenant guid (a-priori-known, override-safe)** — `prod-canary-real-2026-04-13.eml`
  `To:` = `b167331c-536f-4996-9b2d-2f696f35f556@appointments.contenteapp.com`. This guid is **NOT**
  `33e3a930-...` (override-safe) and is a clean UUID (the non-real `prod-canary-2026-04-13.eml` uses a
  `booking+val02-canary-...` plus-addressed form that is NOT a guid — so the REAL canary is the correct
  positive source).
- **GFR engine surface** — `resolve_async(gid, fields, *, client, query_engine, truth_tier=CACHE, scalar=False, verifier=None) -> ResolvedFields`
  at `resolution/gfr/engine.py:166`; public via `resolution/gfr/__init__.py` (`resolve_async`, `ResolvedFields`,
  `UnresolvedError`, `FieldWithProvenance`). Result access shape `result.rows[0]["company_id"].value`
  (verified against `models.py:84-99` `ResolvedFields.rows: list[dict[str, FieldWithProvenance]]`,
  `FieldWithProvenance.value`) — exactly what `test_collision_closure.py:158` already asserts.
- **Engine-owned tenant guard** — `assert_rows_tenant_identity(rows, business_gid)` LIVE in
  `resolution/gfr/guard.py:183` (GAP-1 landed); fails closed on any row whose `gid != business_gid`.
- **Mint is a CONVENTION, not a constant** — `{guid}@appointments.contenteapp.com` lives in
  autom8y-core `.know`, the producer is UNBUILT (telos NOTE-4 / R-6). Sprint-F stubs the mint at the
  boundary by formatting the string directly: `f"{guid}@appointments.contenteapp.com"`.
- **Cross-repo import viability** — `email_booking_intake` is NOT a dependency of asana (separate repo,
  GFR not in autom8y-core; sprint-E deferred). BUT the `resolve_office_stage` transitive import chain
  (`email_booking_intake.errors`, `.pipeline.result`, `.pipeline.context`, `.utils.redact`) is fully
  self-contained: stdlib + `pydantic` + `autom8y_log` + `autom8y_core.errors`, ALL of which resolve in
  the asana venv (`autom8y_log` and `autom8y_core.errors` import OK; `autom8y-core>=4.2.0` is an asana
  dep at `pyproject.toml:25`). A **test-only `sys.path` insert** of the co-located EBI `src/` is
  mechanically viable. asana `tests/integration/` has NO top-level conftest (subdir-only), so the insert
  is clean and local to the new test module. asana `asyncio_mode = "auto"` (`pyproject.toml:111`) — the
  async round-trip executes without a decorator.

---

## 1. TEST HOME fork — option enumeration THEN recommendation

The realization predicate's round-trip spans two repos with no shared import path. There is a genuine
search space here; per option-enumeration-discipline the full slate is enumerated BEFORE recommending.

### Option (a) — asana `tests/integration/` reaches `resolve_office_stage` via a test-only `sys.path` insert to co-located EBI `src/`

A new `tests/integration/test_gfr_tenant_roundtrip.py` in **autom8y-asana** that, at module top, inserts
`/Users/tomtenuta/Code/a8/repos/autom8y/services/email-booking-intake/src` onto `sys.path` (guarded by
an existence check + `pytest.skip` if absent), then imports the REAL `resolve_office_stage`. GFR runs
in-process (its home repo); the EBI stage runs in-process against the REAL inbound code.

- **+** Exercises the REAL inbound code (`resolve_office.py` byte-for-byte) — the round-trip is genuine,
  not a mirror. Override trap, `@`-split, `:92` assignment, by-guid HIT path are all the production code.
- **+** Lives at the honored exit-artifact path; GFR is in its own repo (no GFR re-import gymnastics).
- **+** Transitive imports verified self-contained in the asana venv (§0) — mechanically works today.
- **+** Defeats the "two mirrors agreeing" failure mode: a contract-mirror (option b) can drift from the
  real stage and still pass green; option (a) cannot.
- **−** Path coupling to a sibling repo's on-disk location. Mitigated: existence-guarded `sys.path`
  insert + `pytest.skip(reason=...)` when the EBI checkout is absent (CI-in-asana-alone stays green-skip,
  never red-import-error). The coupling is **named, bounded, surfaced** (harness-sovereignty discipline),
  not silent.
- **−** Not a packaged dependency edge — the insert is test-scaffolding, not a real import contract. This
  is acceptable BECAUSE sprint-E (GFR → autom8y-core) is deferred; when E lands, this insert is replaced
  by a real import and the test is unchanged in substance.

### Option (b) — vendored contract-mirror of the `@`-split + guid-extraction boundary inside the asana test

Re-implement the override-apply → zero-width-strip → `@`-split → `parts[0].strip()` → `chiropractor_guid`
logic as a small fixture INSIDE the asana test, asserting GFR → mirror → guid.

- **+** Zero cross-repo coupling; runs anywhere asana runs.
- **−** **FATAL for a PROVEN rung**: a mirror is a *second copy* of the boundary. If the real
  `resolve_office.py` drifts (e.g., override semantics change, strip order changes), the mirror passes
  green while production breaks — this is exactly the coverage-theater the telos predicate forbids
  ("never by a green suite alone"). A mirror proves the asana author's *belief* about EBI, not EBI.
- **−** The override trap (`_DEFAULT_OVERRIDES`) and the `:80`-before-`:84` ordering are subtle, real
  defects-in-waiting; mirroring them defeats the purpose of testing them.

### Option (c) — EBI-side test importing GFR

Put the round-trip test in `email-booking-intake/tests/`, importing GFR.

- **+** Exercises real `resolve_office_stage` natively (no `sys.path` trick on that half).
- **−** Symmetric-but-worse coupling: GFR is NOT in autom8y-core (sprint-E deferred), so EBI would need a
  `sys.path` insert to the asana **worktree** `src/` (`autom8y-asana-wt-gfr`), which is even more fragile
  (worktree path, not a stable repo path).
- **−** Violates the honored exit-artifact path (`tests/integration/test_gfr_tenant_roundtrip.py` in
  **autom8y-asana**). The dispatch says honor it unless strong reason; there is none here.
- **−** Splits the GFR test corpus across two repos; the engine's own anti-vacuity gate
  (`test_collision_closure.py`) lives in asana — keeping the integration lift beside it is coherent.

### Option (d) — split: asana proves the GFR half + boundary contract; live cross-repo is user-gated

asana proves GFR → minted-string and asserts a *boundary contract* (the minted string's `parts[0]`
equals `G_correct`); the full cross-repo round-trip through the real stage is deferred entirely to the
user-gated live run.

- **+** Cleanest separation of "what the rite proves" vs "what the user proves live".
- **−** **Under-proves the PROVEN-candidate rung**: the predicate explicitly requires the minted address
  to "round-trip THROUGH inbound `resolve_office_stage`". Asserting only `parts[0] == G_correct` re-tests
  string-splitting, not the stage's override/fallback/`:92` behavior. The cross-tenant negative
  (B as dedup-winner) needs the real stage to be meaningful at integration altitude. Option (d) collapses
  the integration proof back to the unit altitude that `test_collision_closure.py` already covers — it
  adds nothing the unit test does not.
- **−** Leaves the realization predicate UNREACHED at this rung; it would defer the actual round-trip to a
  step that is harder to attest and easier to skip.

### RECOMMENDATION — **Option (a)**, with the option-(d) live-gate bolted on as the explicit USER step

Build the round-trip in **autom8y-asana `tests/integration/test_gfr_tenant_roundtrip.py`** (honors the
exit-artifact path). Reach the REAL `resolve_office_stage` via an existence-guarded test-only `sys.path`
insert to the co-located EBI `src/`. This is the ONLY option that exercises the real inbound code at
integration altitude (defeating the mirror-drift theater of (b)) while keeping the test beside the GFR
engine and its anti-vacuity gate (rejecting (c)'s corpus-split) and actually reaching the realization
predicate (rejecting (d)'s under-proof). The option-(d) *insight* is preserved correctly: the
in-session proof is mocked-data-service (a PROVEN-**candidate**); the live-data-service round-trip on a
real tenant is the separately-gated USER step (§5). We do not round (a)+mock up to PROVEN-attested.

**Import strategy (the resolved fork mechanism):** test-only existence-guarded `sys.path.insert(0, EBI_SRC)`
at module top, where `EBI_SRC` is resolved relative to the asana repo root (`../autom8y/services/email-booking-intake/src`)
with a fallback to an env var (`GFR_EBI_SRC`) for non-default checkouts. If the path does not exist, the
module raises `pytest.skip(reason="EBI src not co-located; cross-repo round-trip skipped (see sprint-E)")`
at collection — never an import error, never a false red. When sprint-E lands GFR into autom8y-core and
EBI takes a real dep, the insert is deleted and the import becomes a plain `from email_booking_intake...`
import; the test body is otherwise unchanged.

---

## 2. BOUNDARY — what is mocked in-session vs. what the user-gated live run adds

### In-session integration proof (PROVEN-candidate; the rite's deliverable)

- **MOCK `data_read_client`** as an `AsyncMock` exactly per EBI's own `test_resolve_office.py:39-42`
  pattern, BUT bind it to the **real canary `BusinessRecord` values** for the known guid:
  `client.get_business_by_guid_async.return_value` is an `AsyncMock` carrying `.office_phone` /
  `.business_name` for `G_correct`; `client.get_business_by_phone_async.return_value` carries the same.
  The mock returns a real-shaped record so the `:105` by-guid HIT path is taken (NOT `None` → fallback).
- **GFR runs against mocked substrate** identically to `test_collision_closure.py`: `hydrate_from_gid_async`
  patched to anchor the Offer to the correct Business gid; `query_engine.execute_rows` patched to serve the
  gid-exact Business row from the multi-tenant collision frame. GFR's own engine code (planner, guard,
  `assert_rows_tenant_identity`) runs unmocked — it is the system under test on the asana half.
- **Mint is stubbed at the boundary**: `f"{G_correct}@appointments.contenteapp.com"` — the convention
  formatted directly (producer unbuilt, NOTE-4). GFR supplies `gid → company_id → guid` only.
- The boundary between the two halves is: GFR emits `company_id`; the test mints `{company_id}@...`; the
  real `resolve_office_stage` consumes that minted address and sets `ctx.chiropractor_guid`.

### What the user-gated live-against-prod run adds (NEVER faked, NEVER self-attested by the rite)

The live attestation is the user's. It replaces, on a positively-selected REAL tenant:

1. **Real `DataServiceClient`** (not `AsyncMock`) — a live `data_read_client` hitting the real
   data-service `get_business_by_guid_async`, proving the real chiropractors-table row exists for the
   real guid and the by-guid HIT path resolves against production data.
2. **Real tenant credentials** — the asana side reads `company_id` from the live multi-tenant Business
   frame (real S3 parquet / live cache), not the in-memory collision fixture.
3. **The real (eventually built) mint producer**, once NOTE-4's send-origination producer lands — until
   then the live run still stubs the mint string but proves both ends against live data-service truth.

The in-session test asserts the round-trip LOGIC is correct on canary/mocked-data-service data
(PROVEN-candidate). The live run asserts it holds against production truth on a real tenant
(input to PROVEN-attested, which is the rite-disjoint review rite's call, not the author's, not the
green suite's). G-rung discipline: authored < emitting < alerting < **proven-candidate (this phase)** <
... ; we never round up.

---

## 3. POSITIVE design — real tenant, a-priori-known G_correct, by-guid HIT path

```
G_correct  = "b167331c-536f-4996-9b2d-2f696f35f556"   # from prod-canary-real-2026-04-13.eml To:
                                                       # NOT 33e3a930-... (override-safe); a clean UUID
GID_OFFER  = a positively-selected Offer gid in the canary tenant's tree
GID_BIZ    = the canary tenant's Business gid (the parent-chain anchor)
```

1. **GFR half** — patch `hydrate_from_gid_async` to anchor `GID_OFFER` → `GID_BIZ` (offer path_len=3,
   per `make_hydration_result`); patch `query_engine.execute_rows` to serve the gid-exact Business row
   `{gid: GID_BIZ, company_id: G_correct, office_phone: <canary phone>}`. Call
   `resolve_async(GID_OFFER, ["company_id"], client=mock_client, query_engine=...)`. Assert
   `result.rows[0]["company_id"].value == G_correct` (the GFR engine + its guard run unmocked).
2. **Mint half** — `minted = f"{G_correct}@appointments.contenteapp.com"`.
3. **Inbound half** — build `client = AsyncMock()`; `client.get_business_by_guid_async.return_value` =
   real-canary `BusinessRecord`-shaped `AsyncMock(office_phone=..., business_name=...)`;
   `client.get_business_by_phone_async.return_value` = same. Build the stage with **empty mapping** and
   **no extra overrides**: `stage = resolve_office_stage(client, guid_phone_mapping={}, guid_overrides={})`.
   Build `ctx = PipelineContext(...)`, `ctx.to = minted`. `await stage(ctx)`.
4. **Round-trip assertion (G-DENOM)** — `assert ctx.chiropractor_guid == G_correct`. Assert on
   `ctx.chiropractor_guid` ONLY — NEVER `ctx.office_name` / `ctx.office_phone` (those are display fields
   written by the phone lookup, not the tenant-identity proof; the dispatch is explicit: assert
   `chiropractor_guid`, never display fields).
5. **HIT-path proof** — `client.get_business_by_guid_async.assert_awaited_once_with(G_correct)` proves
   the `:105` by-guid HIT path was taken, NOT the `:121` `guid_phone_mapping` fallback.

This is a positively-selected REAL tenant with an a-priori-known guid (canary fixture), never a synthetic
blanket pass.

## 4. NEGATIVE design — cross-tenant RED-firing fixture (the PHI-leak guard)

Reuse the `test_collision_closure.py` pattern at integration altitude. Tenant B is positively seeded as
the `keep='first'` dedup-WINNER for A's gid; the broken v1 phone-join path returns `G_B`, the v2 gid-exact
path returns `G_A`, and the round-trip must mint A's address and resolve to A — NEVER B.

```
G_A = G_correct (the canary tenant)        G_B = a DIFFERENT tenant's company_id
SHARED_PHONE shared by A and B's Business rows
collision frame: [ {gid: GID_B, office_phone: SHARED_PHONE, company_id: G_B},   # FIRST → keep='first' winner
                   {gid: GID_A, office_phone: SHARED_PHONE, company_id: G_A} ]  # second
```

1. **DELTA proof (broken vs v2)** — run the REAL frozen `execute_join` (read-only client, NEVER edited)
   on A's offer primary keyed on `office_phone` against the collision frame: assert
   `broken["business_company_id"] == G_B` (RED — the wrong tenant survives `keep='first'`). Run
   `resolve_async(GID_OFFER_A, ["company_id"], ...)` with the gid-exact engine: assert
   `result.rows[0]["company_id"].value == G_A`. Assert `G_A != G_B` and `broken != v2`. This is the
   non-vacuity hinge: same fixture, broken=G_B, v2=G_A.
2. **Round-trip continuation** — mint `f"{G_A}@..."`, run it through the real `resolve_office_stage` with
   the canary `data_read_client` mock, assert `ctx.chiropractor_guid == G_A` and
   `ctx.chiropractor_guid != G_B`. (The minted address carries G_A because GFR resolved A correctly; the
   negative proves that even when a phone-collision tenant B exists and would win the v1 dedup, GFR's
   gid-exact path mints A's address, so the round-trip lands A.)
3. **Engine-guard RED corroboration** — additionally assert that feeding the engine an UNFILTERED
   multi-tenant frame (B's row leaking past the gid-exact filter) raises `GuardViolationError` via the
   LIVE `assert_rows_tenant_identity` (`guard.py:183`) — the Vector-A defense-in-depth, proving the leak
   fails closed rather than silently reading B's `company_id`.

A green suite WITHOUT the RED-firing broken half is REJECTED by design (coverage theater); the DELTA is
the proof the gid-exact identity path actually defeats the cross-tenant collision.

## 5. DEFENSES the build MUST encode

| # | Defense | Mechanism (assert in the test) | Why |
|---|---------|--------------------------------|-----|
| D1 | **Override-key avoidance (`_DEFAULT_OVERRIDES`)** | `G_correct == b167331c-...` ≠ `33e3a930-...`; assert `ctx.chiropractor_guid == G_correct` (proves the default U+200B remap did NOT fire) | If G_correct were `33e3a930-...`, `:80` would remap it to `abb01032-...` and the round-trip would prove the WRONG guid |
| D2 | **Override-key avoidance (injected `guid_overrides`)** | Build stage with `guid_overrides={}` explicitly; add a sub-case asserting that an injected override for a DIFFERENT key does NOT touch G_correct's address | `overrides = {**_DEFAULT_OVERRIDES, **guid_overrides}` (`:73`) — an injected override is also a remap surface |
| D3 | **`guid_phone_mapping` neutralization (by-guid HIT, not fallback)** | `guid_phone_mapping={}` AND `client.get_business_by_guid_async.assert_awaited_once_with(G_correct)` (the `:105` HIT). Negative-control: assert the `:121` fallback branch is NOT taken (the mapping is empty / G_correct-absent) | The `:105` by-guid HIT is the path the predicate proves; the `:121` fallback would resolve via a stale override map, not the data-service identity |
| D4 | **Assert on `ctx.chiropractor_guid` — NEVER display fields** | Every round-trip assertion targets `ctx.chiropractor_guid`; explicitly assert NOTHING about `ctx.office_name` / `ctx.office_phone` for the identity proof | Display fields are written by the phone lookup (`:149-170`) and are NOT the tenant-identity surface; G-DENOM requires asserting on tenant identity, never display |
| D5 | **Real inbound code, not a mirror** | The test imports the REAL `resolve_office_stage` (option a); CI skips (never reds) if EBI src absent | A mirror (option b) would pass green on drift — defeats the PROVEN rung |
| D6 | **Frozen-range read-only** | `execute_join` and the engine are imported and CALLED, never edited; the 42 scar tests untouched; build ON TOP | STANDING GRANT: never edit frozen ranges (`query/{engine,join,compiler}.py`) or the 42 scar tests |

## 6. Live-prod gate (the USER's attestation — exact step)

> **User runs**, on a positively-selected REAL tenant with an a-priori-known guid:
> the round-trip with a **real `DataServiceClient`** (not `AsyncMock`) bound to the live data-service, and
> **real tenant credentials** so the asana side reads `company_id` from the live multi-tenant Business
> frame — asserting the minted `{guid}@appointments.contenteapp.com` resolves through the real
> `resolve_office_stage` to `ctx.chiropractor_guid == <the real tenant's guid>`, and that a
> different-tenant gid never mints this tenant's address. The mint producer is stubbed until NOTE-4's
> send-origination producer lands. This live run is the input to PROVEN-attested; the attestation itself
> is the **rite-disjoint review rite's** (CERT-3 close), never the author's, never a green suite alone.
> Production-mutating levers stay the user's.

This phase's deliverable is PROVEN-**candidate**: integration GREEN on canary/mocked-data-service + the
RED-firing cross-tenant negative. It is never rounded up to PROVEN-attested in-session.

## 7. Reversibility

Two-way door. The `sys.path` insert is test-only scaffolding deleted when sprint-E lands GFR in
autom8y-core and EBI takes a real dependency edge; the test body (positive/negative/defense asserts) is
unchanged by that migration. No production code, no schema, no public API is touched by this test.

## Evidence Grade

`[STRUCTURAL | MODERATE]` — self-ref cap MODERATE per `self-ref-evidence-grade-rule`. All §0 platform
claims directly inspected at HEAD this pass (engine signature, guard, EBI stage flow, canary guid,
import-chain viability, pytest config). PROVEN attestation is deferred to the rite-disjoint review rite;
the live-against-prod run is user-gated.
