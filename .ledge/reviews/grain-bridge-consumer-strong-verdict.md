---
type: review
status: accepted
initiative: grain-bridge-resolver
node: thin asana leads consumer (WS-CONSUMER + WS-SKIP + WS-CANARY)
review_mode: FULL
review_date: 2026-06-26
reviewer_rite: review (rite-disjoint from 10x-dev builder and security pantheon)
pr: autom8y/autom8y-asana#160
pr_head: 10ff40f2e69c9be2400650880cd03f1410925247
pr_base: main
pr_state: OPEN / MERGEABLE
seal_elevation: MODERATE -> STRONG
cross_stream_concurrence: true
rung: "consumer = BUILT (PR #160 OPEN @ 10ff40f2, not merged); in-rite verification = MODERATE (qa 14/14, self-grade cap honored); seal STRONG-elevation = ISSUED (this verdict, rite-disjoint review critic, independently re-run); verified_realized = [UNATTESTED -- DEFER-POST-HANDOFF]"
---

# Code Review: grain-bridge-leads-consumer (Rite-Disjoint STRONG Attestation)

## Executive Summary

PR autom8y/autom8y-asana#160 (feat/grain-bridge-leads-consumer, `10ff40f2`, OPEN/MERGEABLE, 16 files/2032+/157-) implements the thin asana consumer that mints per-business single-tenant tokens for the nightly leads read, eliminating the shared fleet token without re-opening DATA-VAL-003. This review re-ran the two-sided discriminating canary independently in a fresh isolated worktree, rite-disjoint from both the 10x-dev builder and the security pantheon — all five canary arms passed, the TEETH mutation-kill confirmed the gate is the sole load-bearing control (3 failed on gate-disable, sha256 BEFORE==AFTER, tree clean), and the FINDING-2 anti-IDOR JWT-dominance guard is confirmed live at `data_service.py:1009` (dd4566e5). The consumed auth seal surface is byte-stable at f2a95959. The seal is elevated MODERATE to STRONG on independently re-derived first-party evidence. One LOW finding (FINDING-1: `collision_conflict` consumer-altitude test gap) is routed to principal-engineer and does not block the seal or merge readiness.

## Health Report Card

| Category | Grade | Key Finding |
|----------|-------|-------------|
| Canary Coverage | A | 5/5 arms pass; GREEN + RED + minter-RED + TEETH + SCOPE; 0 critical, 0 high; FINDING-1 is LOW (test gap, not a control defect) |
| Data-Tenant Isolation | A | FINDING-2 anti-IDOR JWT-dominance confirmed at `data_service.py:1009` (dd4566e5); JWT binding chain traced; 0 cross-tenant defects |
| Consumer Architecture | A | No orphan resolver; `leads_ebid.py` is caller-side normalize only; G-PROPAGATE clean |
| Evidence Provenance | A | Fresh worktree @ `10ff40f2`; sha256 BEFORE==AFTER; tree clean post-restore; auth surface `git diff 1ad88e87..f2a95959` empty |
| Canary Discriminating Power | A | TEETH mutation-kill: 3 failed on gate-disable; gate at `_FakeSealExchange.post:81` is the sole load-bearing control |
| **Overall** | **A** | **0 critical, 0 high, 0 medium, 1 low (FINDING-1). Weakest-link = A.** |

## Metrics Dashboard

| Metric | Value |
|--------|-------|
| PR head | `10ff40f2` (OPEN, MERGEABLE) |
| Files changed | 16 (2032+/157-) |
| Total findings | 2 (0 critical, 0 high, 0 medium, 1 low, 1 info) |
| Canary arms re-run | 5/5 passed |
| TEETH mutation-kill | 3 failed on gate-disable; sha256 BEFORE==AFTER |
| Auth seal surface drift | NONE (`git diff 1ad88e87..f2a95959` empty) |
| Orphan resolvers | 0 (G-PROPAGATE clean) |
| Review complexity | FULL (scan + rite-disjoint canary re-run + cross-repo trace) |
| Seal elevation | MODERATE -> STRONG |
| cross_stream_concurrence | true |

## Verification Gates (GREEN/RED Matrix)

| Gate | Result | Evidence | Evidence Grade |
|------|--------|----------|----------------|
| G-PROVE GREEN (owned -> mint + leads) | PASS | `test_tc_green_owned_resolves_and_reads` PASSED; `succeeded==1`; `get_leads_async` called on `+17705550001`; `tokens_seen==[f"per-business-jwt:{compute_ebid(OWNED_COMPANY_ID)}"]`; `requested_scopes==["data:read"]` | [STRONG -- first-party re-run, rite-disjoint] |
| G-PROVE RED (cross-tenant -> 404 + no-mint = DATA-VAL-003 non-regression) | PASS | `test_tc_red_cross_tenant_refused_no_mint_no_read` PASSED; `succeeded==0`; `skipped_by_class[RESOLUTION_MISS]==1`; `get_leads_async.calls==[]`; `factory_calls==[]` | [STRONG -- first-party re-run, rite-disjoint] |
| G-PROVE minter-RED (isolated 404->MintResolutionMiss) | PASS | `test_tc_red_minter_raises_resolution_miss_directly` PASSED; `pytest.raises(MintResolutionMiss)` confirmed | [STRONG -- first-party re-run, rite-disjoint] |
| G-PROVE SCOPE (data:read only, never read:pii) | PASS | `test_tc_scope_no_arm_ever_requests_read_pii` PASSED; all requests across GREEN and TEETH-mint arms verified `requested_scopes==["data:read"]`, `"read:pii" not in scopes` | [STRONG -- first-party re-run, rite-disjoint] |
| G-THEATER / TEETH (gate-disable flips RED->mint) | PASS | `test_tc_teeth_gate_disabled_flips_red_to_mint_then_restores` PASSED; gate OFF -> `succeeded==1`, `get_leads_async` called on cross-tenant `+17705559999` | [STRONG -- first-party re-run, rite-disjoint] |
| G-HALT (re-run RED is intended DATA-VAL-003 arm, not a real leak) | CLEAR | RED arm passes with gate enabled; cross-tenant input is a broken input correctly refused; no halt condition | [STRONG -- first-party re-run, rite-disjoint] |
| FINDING-2 (anti-IDOR JWT-dominance at data_service.py:1009, dd4566e5) | CONFIRMED | `detail_office_phone = None if is_fleet_read(request) else tenant_office_phone` at line 1009; JWT binding chain: `OfficePhoneDep` -> `_resolve_tenant_office_phone` -> `resolve_office_phone(request, session)` (JWT `business_id` -> canonical `office_phone` from DB) | [STRONG -- first-party cross-repo read, rite-disjoint] |
| Auth seal surface UNCHANGED (1ad88e87..f2a95959) | CONFIRMED | `git diff 1ad88e87..f2a95959 -- identity_resolver.py tokens.py service-accounts.yaml` = empty; f2a95959 = `feat(autom8y-core): add business-binding verify transport method (#785)`; consumed surface byte-stable | [STRONG -- first-party git diff] |
| G-PROPAGATE (no orphan resolver) | CONFIRMED | `leads_ebid.py` uses `normalize_chiropractor_guid(company_id)` (caller-side, no data fetch); no `GET /businesses/{office_phone}` call; no `ServiceTokenAuthProvider` in leads path | [STRONG -- first-party read, rite-disjoint] |

### Full Pytest Receipt (5 passed)

```
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.0.2, pluggy-1.6.0
rootdir: /private/tmp/wt-review-grain-bridge-canary
configfile: pyproject.toml
asyncio: mode=Mode.AUTO
collecting ... collected 5 items

tests/unit/canary/test_grain_bridge_canary.py::test_tc_green_owned_resolves_and_reads PASSED [ 20%]
tests/unit/canary/test_grain_bridge_canary.py::test_tc_red_cross_tenant_refused_no_mint_no_read PASSED [ 40%]
tests/unit/canary/test_grain_bridge_canary.py::test_tc_red_minter_raises_resolution_miss_directly PASSED [ 60%]
tests/unit/canary/test_grain_bridge_canary.py::test_tc_teeth_gate_disabled_flips_red_to_mint_then_restores PASSED [ 80%]
tests/unit/canary/test_grain_bridge_canary.py::test_tc_scope_no_arm_ever_requests_read_pii PASSED [100%]

============================== 5 passed in 0.70s ===============================
```

Worktree: `/tmp/wt-review-grain-bridge-canary` (detached HEAD `10ff40f2`, fresh, independent of the builder's `autom8y-asana-wt-grain-bridge`). Python: `/Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-grain-bridge/.venv/bin/python` (autom8y-log 0.8.0, autom8y-core 4.8.0). PYTHONPATH: `/tmp/wt-review-grain-bridge-canary/src`.

### TEETH Mutation-Kill Receipt (COPY-ASIDE)

File: `tests/unit/canary/test_grain_bridge_canary.py`

SHA256 BEFORE: `3164b34eace5a32763412ceecd144950673137b3846bbb10f2d100e7d8f3e39c`

Mutation applied at line 83 (gate-disabled path):
- Before: `return _FakeResponse(404, {"error": "AUTH-TEB-005"})`
- After: `return _FakeResponse(200, {"access_token": "MUTANT-LEAKED-TOKEN"})`

Mutated run output:
```
tests/unit/canary/test_grain_bridge_canary.py::test_tc_green_owned_resolves_and_reads PASSED
tests/unit/canary/test_grain_bridge_canary.py::test_tc_red_cross_tenant_refused_no_mint_no_read FAILED
tests/unit/canary/test_grain_bridge_canary.py::test_tc_red_minter_raises_resolution_miss_directly FAILED
tests/unit/canary/test_grain_bridge_canary.py::test_tc_teeth_gate_disabled_flips_red_to_mint_then_restores FAILED
tests/unit/canary/test_grain_bridge_canary.py::test_tc_scope_no_arm_ever_requests_read_pii PASSED

assert result.succeeded == 0
E   assert 1 == 0  (cross-tenant succeeded=1 on gate-disable)
Failed: DID NOT RAISE MintResolutionMiss
assert red_before.succeeded == 0
E   assert 1 == 0

3 failed, 2 passed
```

Restore: `cp /tmp/golden_canary.py` back; SHA256 AFTER: `3164b34eace5a32763412ceecd144950673137b3846bbb10f2d100e7d8f3e39c` (BEFORE==AFTER). `git status` -> `nothing to commit, working tree clean`. Post-restore clean run: 5 passed in 0.41s.

The gate at `_FakeSealExchange.post:81` (`if self.gate_enabled and ebid not in self.authorized`) is the sole load-bearing mechanism. Without it, cross-tenant mints through (`succeeded=1`, `MintResolutionMiss` not raised, `get_leads_async` called on `+17705559999`).

### FINDING-2 Cross-Repo Receipt (data_service.py:1009 @ dd4566e5)

File: `/Users/tomtenuta/Code/a8/repos/autom8y-data/src/autom8_data/analytics/routes/data_service.py`
Anchor: line 1009

```python
detail_office_phone = None if is_fleet_read(request) else tenant_office_phone
```

Load-bearing comment at lines 1004-1008:
```
# Own-tenant path: BYTE-IDENTICAL to pre-adoption (anti-IDOR design spec §4):
# the JWT-resolved tenant key OVERRIDES the client-supplied ``office_phone``
# query param. The client value is validated for shape (above) but NEVER
# trusted as the tenant selector -- ``tenant_office_phone`` is the SOLE source
# of the ``Lead.office_phone ==`` predicate.
```

JWT binding chain (confirmed): `OfficePhoneDep` (line 94) -> `_resolve_tenant_office_phone` (line 66) -> `resolve_office_phone(request, session)` (JWT `business_id` -> canonical `office_phone` from DB). The client-supplied `office_phone` request parameter is shape-validated but structurally excluded from the tenant selection predicate.

G-PROPAGATE: the asana consumer receives this guard by construction -- when it mints a per-business token (JWT containing the minted `business_id`), the data service resolves `tenant_office_phone` from THAT JWT's `business_id`. Even if the consumer sent a cross-tenant `office_phone` query param, the data service ignores it in favor of the JWT binding. The consumer authors no competing resolver.

### PR State Receipt

```
headRefOid: 10ff40f2e69c9be2400650880cd03f1410925247
baseRefName: main
mergeable: MERGEABLE
state: OPEN
```

## Findings by Priority

### Critical
None.

### High
None.

### Medium
None.

### Low

**FINDING-1 -- collision_conflict consumer-altitude test gap**

- **Severity**: LOW [STRONG -- 10x-dev handoff characterization; pattern-profiler concurs; independently confirmed]
- **Location**: `src/autom8_asana/automation/workflows/leads_consumer.py:223-225` (production catch present); `tests/unit/canary/test_grain_bridge_canary.py` (consumer-loop 409 path absent)
- **Description**: `collision_conflict` is the only WS-SKIP class not driven to a counted emit at consumer altitude. The production code at `leads_consumer.py:223-225` correctly catches `MintCollision` -> `SkipClass.COLLISION_CONFLICT`. A minter-altitude test (`test_mint_409_raises_collision`) confirms 409 -> `MintCollision` raises. What is absent: a consumer-loop test driving a 409 through the consumer to a counted `skipped_by_class[COLLISION_CONFLICT]` assertion, closing the 4/4 EMIT matrix.
- **Why it does NOT block STRONG**: This is a test coverage gap, not a defect in the seal control. The production path is present and correct. The reconciliation invariant at `leads_consumer.py:165` (`assert result.attempted == result.succeeded + result.total_skipped`) would surface any accounting failure. The gate the STRONG seal validates is the oracle-seal 404 cross-tenant refusal (DATA-VAL-003). FINDING-1 concerns the 409 server-side collision (DATA-CONFLICT-002), a different skip class that carries no cross-tenant access risk. A 409 collision is a correctly-refused-and-counted skip, not a leak vector.
- **Recommendation**: Author a consumer-altitude test driving 409 -> `MintCollision` -> counted `skipped_by_class[COLLISION_CONFLICT]` to close the 4/4 EMIT matrix.
- **Effort**: Low (bounded single test)
- **Blocks merge**: No. **Blocks STRONG**: No.

### Info

**FINDING-2 -- Anti-IDOR JWT-dominance (cross-repo, informational)**

- **Severity**: INFO (not a defect in this PR)
- **Location**: `/Users/tomtenuta/Code/a8/repos/autom8y-data/src/autom8_data/analytics/routes/data_service.py:1009` @ dd4566e5
- **Description**: The anti-IDOR guard is present and live. `tenant_office_phone` (JWT-resolved) is the SOLE `Lead.office_phone ==` predicate. The asana consumer CONSUMES this guard; it does not enforce it and does not need to. G-PROPAGATE confirmed.
- **Status**: CONFIRMED LIVE -- no action required.

## Cross-Rite Recommendations

| Concern | Recommended Rite | Action |
|---------|-----------------|--------|
| FINDING-1: collision_conflict consumer test gap (4/4 EMIT matrix) | principal-engineer | Author consumer-loop test: 409 -> `MintCollision` -> counted `skipped_by_class[COLLISION_CONFLICT]` |
| Lever C1 (GR-6 deletion + F-001 frozenset) | operator-sovereign | Apply post-deploy; gates fleet-token retirement |
| Dedicated leads-resolver SA provisioning (Option B) | operator-sovereign | Lead-time NOTIFY; precedes fleet-retire |
| UV-P-DBCLEAN (DATA-VAL-003 live re-probe) | operator (eunomia/live) | Deploy-time re-probe post-C1 |
| gfr verified_realized (send-origination round-trip) | eunomia (rite-disjoint, live) | Post-C1 + post-fleet-retire; DISTINCT altitude from this consumer seal -- do NOT conflate |
| Merge, fleet-token retirement, prod deploy | operator-sovereign | User holds these levers; not agent-executable |

## Binding Verdict

**SEAL: MODERATE -> STRONG**

**Grounds**: All five verification gates cleared on independently re-run first-party evidence, rite-disjoint from the 10x-dev builder and the security pantheon (SEC-grain-bridge-resolver-2026-06-26.md). The two-sided canary was re-fired first-party -- not read from qa's run. The RED arm is the intended broken input correctly refused (DATA-VAL-003 non-regression, G-HALT clear). The TEETH mutation-kill demonstrates the gate at `_FakeSealExchange.post:81` is the sole load-bearing mechanism (3 failed on gate-disable, sha256 BEFORE==AFTER, tree clean). FINDING-2 anti-IDOR is live at dd4566e5:1009. No orphan resolver (G-PROPAGATE). Auth seal surface byte-stable at f2a95959.

**STRONG issued as the rite-disjoint external critic on first-party re-derived evidence.**
**cross_stream_concurrence: true** -- evidence is first-party re-run by this review station, rite-disjoint, and corroborates the 10x-dev builder's authored canary without inheriting the builder's priors.

## Rung (G-RUNG -- not rounded)

| Rung | Status |
|------|--------|
| consumer | BUILT (PR #160 OPEN @ `10ff40f2`, not merged) |
| in-rite verification | MODERATE (qa 14/14; self-grade cap honored) |
| seal STRONG-elevation | ISSUED (this verdict, rite-disjoint review critic, independently re-run) |
| verified_realized | [UNATTESTED -- DEFER-POST-HANDOFF] -- eunomia, LIVE, post-C1 + post-fleet-retire |

This canary re-run does NOT discharge `verified_realized`. The gfr `verified_realized` predicate (`.know/telos/gfr.md:79-89`) is the send-origination `{guid}@appointments.contenteapp.com` round-trip to the correct tenant -- a distinct altitude. This verdict closes the consumer seal at STRONG; it does not close the gfr telos proof.

## DEFER Watch (unchanged; none scope-crept at this station)

- **Lever C1** (SC-C1-1 GR-6 deletion + SC-C1-2 F-001) -- operator-held
- **Dedicated leads-resolver SA provisioning** (Option B) -- operator-held
- **UV-P-DBCLEAN** -- deploy-time re-probe, post-C1, eunomia/live
- **FINDING-1** collision_conflict consumer test gap -- principal-engineer
- **Merge, fleet-token retirement, prod deploy** -- operator-sovereign
- **gfr `verified_realized`** -- eunomia, live, [UNATTESTED-DEFER]

## Recommended Next Steps

1. **Merge PR #160** (operator-sovereign): consumer is merge-ready -- STRONG seal issued, 0 critical, 0 high, MERGEABLE at `10ff40f2`. FINDING-1 does not block.
2. **Apply Lever C1** (operator-sovereign, post-deploy): SC-C1-1 (GR-6 bypass-tuple deletion) + SC-C1-2 (F-001 frozenset fast-follow); gates fleet-token retirement and discharges the telos's "fleet token GONE" predicate.
3. **Provision dedicated SA** (Option B, operator): leads-resolver SA provisioning before fleet-retire.
4. **UV-P-DBCLEAN** (operator, deploy-time): DATA-VAL-003 live re-probe; zero-collision assertion on live chiropractors before C1.
5. **FINDING-1 consumer test** (principal-engineer): author 409 -> `MintCollision` -> counted `skipped_by_class[COLLISION_CONFLICT]` at consumer altitude to close 4/4 EMIT matrix.
6. **gfr verified_realized** (eunomia, post-C1 + post-fleet-retire): live `insights_export_completed succeeded>0` + fresh `Autom8y/AsanaInsights LastSuccessTimestamp` + zero DATA-VAL-003 in LEADS path + fleet token retired -- eunomia attests, rite-disjointly, at a distinct altitude from this consumer seal.

---
*Review mode: FULL | Seal: MODERATE -> STRONG | cross_stream_concurrence: true | Generated by review rite (rite-disjoint from 10x-dev builder and security pantheon) | 2026-06-26*
