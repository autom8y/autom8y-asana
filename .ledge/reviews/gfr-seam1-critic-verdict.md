---
type: review
status: accepted
cert: CERT-1 (PT-01)
subject: Option E re-assertion contract coverage — SEAM1 legacy-fallback read-gates
rite: review (pattern-profiler, rite-disjoint critic)
authored_at: 2026-06-25
verdict: STRONG
rung: proven-candidate
red_on_bypass_receipt: gfr-seam1-scan.md § CERT-1-STRONG-EVIDENCE Task 2 (HEAD 70c3e8c6, 2026-06-25)
---

# GFR SEAM-1 Critic Verdict — CERT-1 (PT-01)

**Charge (from ADR frontmatter `external_critic.mandate`):** Is there ANY path that
serves a legacy-fallback row WITHOUT the gid-identity re-assertion firing? Enumerate the
read-gates (`storage.py:1010,1195,1291,1372`) and confirm each one that can serve a
fallback row routes through the re-assertion.

---

## Verdict: STRONG

GAP-1 is CLOSED. The implicit-filter gap is now ENGINE-OWNED and TEST-GUARANTEED.

10x-dev placed an explicit `assert_rows_tenant_identity` guard at
`engine.py:138` — called after `execute_rows` returns and BEFORE `response.data[0]`
is read. The guard is self-contained in the engine's own module (`guard.py:183-237`);
it iterates every returned row (`for index, row in enumerate(rows)`) and raises
`GuardViolationError` if any row's gid is absent or mismatches `anchor.business_gid`
(fail-closed: `None != business_gid` is a violation). The engine-owned guard is the
re-assertion that was previously carried only implicitly by the query substrate's
Polars filter.

The RED-on-bypass mutation probe (SIGNAL-SIFTER, appended to gfr-seam1-scan.md
2026-06-25, HEAD 70c3e8c6) is the definitive proof instrument: commenting out
`guard_mod.assert_rows_tenant_identity(response.data, anchor.business_gid)` at
`engine.py:138` caused 4 tests to go RED — including the integration-altitude test
`TestNegativeCrossTenant::test_engine_guard_fails_closed_on_unfiltered_cross_tenant_frame`
and all three `TestEngineOwnedTenantGuard` unit tests. Restoring the guard via
`git checkout --` returned all 44 targeted tests to GREEN and produced a clean tree
(`git status --porcelain` empty). The unfiltered multi-tenant frame with `data[0] = {gid: B_WRONG, company_id: G_WRONG}` leaked through silently with the guard disabled;
it raised `GuardViolationError` with the guard present. The contract is proven by
the test failure, not by prose or a green dashboard alone.

**Rung: proven-candidate** (CERT-1 advances the rung from proven-PENDING per G-THEATER
and the GRANDEUR ANCHOR; this rite cannot reach PROVEN-attested — that requires the
user-gated live-against-prod run.)

---

## Read-Gate Evidence (enumerated, gate by gate)

### Gate G-1 — `_load_dataframe_impl` at `storage.py:1010`

**How it is reached by GFR:**
```
resolve_async (engine.py:206)
  → _resolve_identity_plan_async (engine.py:113)
  → query_engine.execute_rows("business", project_gid, client, request)
  → provider.get_dataframe("business", project_gid, client)
  → DataFrameCache.get_async(project_gid, "business")
  → progressive_tier.get_async("business:{project_gid}")
  → storage.load_dataframe_with_metadata(project_gid, "business")
  → _load_dataframe_impl(project_gid, entity_type="business")
  → [v2 miss] → legacy fallback at :1010
  → returns (multi-tenant Business DataFrame, watermark, wm_dict)
```

**Does re-assertion fire?** YES — explicitly (GAP-1 closed).

Prior verdict found the re-assertion present only as an implicit Polars `gid ==
business_gid` filter in the query substrate (`query/engine.py:169`). GAP-1 asked
10x-dev to add an explicit engine-owned guard post-`execute_rows`. That guard now
exists at `engine.py:138`: `guard_mod.assert_rows_tenant_identity(response.data,
anchor.business_gid)`. It fires on the returned `response.data` before any field is
consumed. The Polars filter remains (defense in depth at the substrate); the engine
guard is the explicit, auditable re-assertion living in `resolution/gfr/engine.py`.

**Direct file read confirms** (pattern-profiler, 2026-06-25):
- `engine.py:129-138` — guard call with inline comment naming GAP-1 / INVARIANT I1,
  citing the substrate filter's location and explaining why the engine-owned guard
  is not redundant
- `guard.py:183-237` — `assert_rows_tenant_identity`: iterates all rows via
  `enumerate(rows)`, raises `GuardViolationError` on `row_gid != business_gid`,
  fail-closed on absent gid key (`row.get(key)` returns `None`, which is `!= business_gid`)

**Disposition:** CLOSED. Re-assertion is engine-owned, explicit, every-row,
fail-closed, and test-guaranteed.

---

### Gate G-2 — `get_watermark` at `storage.py:1195`

**Is it on the GFR call path?** NO.

`get_watermark` is a standalone watermark-only utility; not on the GFR identity
resolution call trace. Serves metadata, not rows.

**Disposition:** NOT APPLICABLE to GFR CERT-1. Confirmed in prior verdict; unchanged.

---

### Gate G-3 — `load_index` at `storage.py:1291`

**Is it on the GFR call path?** NO.

GFR engine does not call `load_index`. Used by intake/matching path only. `grep
load_index resolution/gfr/` returns no matches.

**Disposition:** OUT OF SCOPE for GFR CERT-1. A real gap for the intake/matching path
under `legacy_fallback_enabled=True` — routed to 10x-dev as a separate concern.

---

### Gate G-4 — `load_section` at `storage.py:1372`

**Is it on the GFR call path?** NO.

GFR engine does not call `load_section`. `grep load_section resolution/gfr/` returns
no matches.

**Disposition:** OUT OF SCOPE for GFR CERT-1. Same route as G-3 if this path is
ever on fallback.

---

## Coverage Summary

| Gate | On GFR identity path? | Fallback can serve wrong-tenant row? | Re-assertion present? |
|------|-----------------------|--------------------------------------|----------------------|
| G-1 `_load_dataframe_impl:1010` | YES | YES (multi-tenant Business frame) | ENGINE-OWNED EXPLICIT (`engine.py:138`, `guard.py:183-237`) |
| G-2 `get_watermark:1195` | NO | N/A (metadata only) | N/A |
| G-3 `load_index:1291` | NO | Not on GFR path | N/A for GFR |
| G-4 `load_section:1372` | NO | Not on GFR path | N/A for GFR |

One gate (G-1) is on the GFR identity call path. The engine-owned guard at
`engine.py:138` closes the re-assertion contract on that gate with every-row
coverage and fail-closed semantics. No legacy-fallback row can reach the GFR
engine's output without `assert_rows_tenant_identity` firing.

---

## GAP-1 Disposition

### GAP-1 — CLOSED

**Was:** Re-assertion at G-1 was implicit — carried by the Polars `gid ==
business_gid` filter in the query substrate (`query/engine.py:169`). Auditing
the re-assertion required reading the query substrate, not `resolution/gfr/engine.py`.
A test with a mock provider that returned an unfiltered multi-tenant frame would
have bypassed the re-assertion silently.

**Now:** `engine.py:138` calls `guard_mod.assert_rows_tenant_identity(response.data,
anchor.business_gid)` — an explicit, named, engine-owned assertion on the returned
data, independent of the substrate's filter. The guard's location (post-execute,
pre-data-read), scope (every row), and failure mode (fail-closed on absent gid) are
all confirmed by direct file read and by the RED-on-bypass mutation probe.

**CONDITIONAL condition satisfied.** The re-assertion contract is now auditable by
reading `resolution/gfr/engine.py` alone.

---

## Cross-Rite Routing

| Finding | Target Rite | Trigger Signal |
|---------|-------------|----------------|
| G-3 / G-4 gaps on intake/matching path | 10x-dev | `load_index` / `load_section` on legacy fallback lack re-assertion — out of GFR scope but real risk for intake path if `legacy_fallback_enabled=True` |

GAP-1 is closed; no 10x-dev routing for the GFR identity path remains open.

---

## Verdict Summary

- **VERDICT:** STRONG
- **RUNG:** proven-candidate
- **Decisive evidence:** RED-on-bypass mutation probe at worktree HEAD 70c3e8c6. Disabling `guard_mod.assert_rows_tenant_identity(response.data, anchor.business_gid)` at `engine.py:138` caused 4 tests RED — `TestEngineOwnedTenantGuard` (3 unit) + `TestNegativeCrossTenant::test_engine_guard_fails_closed_on_unfiltered_cross_tenant_frame` (integration). The explicit failure: `DID NOT RAISE GuardViolationError` with `data[0] = {gid: B_WRONG, company_id: G_WRONG}` — the wrong tenant's row consumed silently. Restoring via `git checkout --` → 44 GREEN, clean tree.
- **Engine-owned:** `engine.py:138` (guard call) + `guard.py:183-237` (implementation). Every-row via `enumerate(rows)`. Fail-closed: `row.get(_ROW_GID_KEY)` returns `None` when key absent; `None != business_gid` is a violation.
- **G-rung note:** This rite ratifies CERT-1 to STRONG at proven-candidate altitude. PROVEN-attested requires the user-gated live-against-prod run. merged/live is MINE.

---

## Evidence Receipt Chain

| Item | Receipt |
|------|---------|
| RED-on-bypass proof | `gfr-seam1-scan.md` § CERT-1-STRONG-EVIDENCE Task 2; HEAD 70c3e8c6 |
| Every-row confirmation | `guard.py:220-222` (`for index, row in enumerate(rows)`) — direct file read 2026-06-25 |
| Fail-closed confirmation | `guard.py:221-222` (`row.get(_ROW_GID_KEY)` → `None != business_gid`) — direct file read 2026-06-25 |
| Pre-read-of-data[0] ordering | `engine.py:138` precedes `engine.py:146` (`response.data[0].get("company_id")`) — direct file read 2026-06-25 |
| Guard call site inline comment | `engine.py:129-138` names GAP-1, INVARIANT I1, and the substrate/engine distinction — direct file read 2026-06-25 |
| Unit baseline | 96 passed pre-probe (`gfr-seam1-scan.md` § Task 1) |
| Post-restore GREEN | 44 passed, clean tree (`gfr-seam1-scan.md` § Task 2 Restore) |

---

*Verdict advanced to STRONG by PATTERN-PROFILER (rite-disjoint critic), CERT-1 (PT-01), 2026-06-25.
Evidence: live Read against worktree `/Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr`
(engine.py, guard.py) + scan artifact `gfr-seam1-scan.md` § CERT-1-STRONG-EVIDENCE.
Write-only to `.ledge/reviews/`; no engine files touched.*
