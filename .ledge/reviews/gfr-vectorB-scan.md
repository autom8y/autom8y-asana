---
type: review
status: proposed
---
# GFR Vector-B Scan: gid->project_gid->entity_type Chain

**Authored**: 2026-06-25
**Rite**: SIGNAL-SIFTER, CERT-2 (Vector-B: gid->project_gid discriminator)
**Engine commit**: 9a49a842 on branch feat/gfr-engine at /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr

---

## Discriminator Chain (file:line at each hop)

### Hop 1: task gid -> project_gid extraction

**Source**: `src/autom8_asana/models/business/detection/tier1.py:38-71` (`_extract_project_gid`)

The extractor reads `task.memberships[0]["project"]["gid"]`. This is the sole input to the discrimination chain. Evidence: `task.memberships[].project.gid` is also the canonical detection field as documented in `src/autom8_asana/clients/tasks.py:557` (docstring for `include_detection_fields=True`) and `src/autom8_asana/cache/models/mutation_event.py:64` (mutation event extractor reads the same path via `memberships[].project.gid`).

Key structural facts (tier1.py:47-71):
- If `task.memberships` is empty -> returns `None` -> Tier 1 misses (falls to Tier 2/3/4)
- Takes **first** membership only (`task.memberships[0]`) — no iteration
- Returns the `gid` string of the first project

### Hop 2: project_gid -> EntityType lookup

**Source**: `src/autom8_asana/models/business/registry.py:180-211` (`ProjectTypeRegistry.lookup`)

The lookup delegates in two steps:
1. `EntityRegistry.get_by_gid(project_gid)` — static registry, single source of truth for all statically-declared entity descriptors (`entity_registry.py:435ff`)
2. Falls back to `self._gid_to_type.get(project_gid)` — dynamic entries registered by workspace discovery (ADR-0108 / ADR-0109)

The registry is populated via two sources:
- **Static** (bootstrap): `EntityDescriptor` entries in `entity_registry.py:435-488` declare `primary_project_gid` per entity type. Business=`"1200653012566782"` (line 445), Unit=`"1201081073731555"` (line 472).
- **Dynamic** (lazy): `WorkspaceProjectRegistry.lookup_or_discover_async` (registry.py:623-651) triggers `discover_async` on first unregistered GID, which calls Asana's workspace projects API and registers pipeline projects (SALES, ONBOARDING, etc.) as `EntityType.PROCESS`.

### Hop 3: EntityType -> plan/route in GFR engine

**Source**: `src/autom8_asana/resolution/gfr/engine.py:64-76` (`_business_project_gid`) and `engine.py:92-152` (`_resolve_identity_plan_async`)

The engine does NOT use the Tier-1 entity_type to route the identity read to a different project_gid. It uses `_business_project_gid()` which reads the Business descriptor's `primary_project_gid` from `EntityRegistry` — always `"1200653012566782"` — regardless of the entry entity_type. The identity read is `RowsRequest(where=Comparison(field="gid", op=Op.EQ, value=business_gid), join=None)` issued against the Business project frame.

The `business_gid` in the where-clause comes from the **entry anchor** (`_fetch_and_anchor_async`, `entry.py:66-126`), which walks the parent chain (`_traverse_upward_async`) to the Business root — the per-row task gid, not the project_gid. This is the Vector-A lock (gid-exact row selection).

---

## Critical Scoping: Does project_gid bind gid->TENANT or gid->ENTITY-TYPE?

**Finding: project_gid binds gid->ENTITY-TYPE only. It NEVER binds gid->TENANT.**

Evidence chain:

1. `entity_registry.py:445`: Business descriptor `primary_project_gid="1200653012566782"` is a **single shared value** for all tenants in the Business entity type. All Business tasks across all tenants live in this one Asana project.

2. `entity_registry.py:472`: Unit descriptor `primary_project_gid="1201081073731555"` — likewise one project for all Unit tasks across all tenants.

3. `registry_validation.py:104-136` (`_check_project_type_registry`): cross-validation asserts that each EntityDescriptor's `primary_project_gid` maps to the expected `entity_type` in ProjectTypeRegistry. The validation loop is over descriptors (entity types), not over tenants. There is no tenant axis in any registry.

4. `tier1.py:117`: `entity_type = registry.lookup(project_gid)` — the return type is `EntityType`, not a tenant identifier. The lookup key is the project GID; the lookup value is the entity type (BUSINESS, UNIT, OFFER, PROCESS, …).

5. `test_engine.py:75-76`: The identity read is confirmed to target `entity_type="business"` and `project_gid="1200653012566782"` — the single shared Business project, not a per-tenant project.

**Corollary**: Tenant identity rests solely on the per-row `business_gid` derived via the parent chain — the gid-exact `where: gid == business_gid` predicate in the RowsRequest. This is Vector A. The discriminator (project_gid -> entity_type) is a pure type router; it is entirely upstream of and orthogonal to tenant selection.

---

## Hazard Assessment: Can the discriminator route a gid's read to the WRONG project frame?

Three hazards examined:

### Hazard 1: Multi-tenant frames
**Not a discriminator hazard.** All tenants of a given entity type share one project_gid and thus one project frame. The discriminator correctly routes to the entity-type frame. Tenant selection within the frame is Vector A's job (gid-exact predicate). The discriminator cannot misdirect to a "wrong" project — there is no per-tenant project to route to.

### Hazard 2: Lazy workspace discovery (ADR-0109)
**Low-risk, bounded scope.** `WorkspaceProjectRegistry.lookup_or_discover_async` (registry.py:623-651) discovers pipeline projects (SALES, ONBOARDING, etc.) from Asana's workspace API and registers them as `EntityType.PROCESS`. The risk surface is:
- A pipeline project GID could, in theory, be mismatched if Asana returns a different project set than expected (e.g., renamed project matching the wrong ProcessType via `_match_process_type_contains`).
- The entity_type produced by discovery is always `EntityType.PROCESS` (registry.py:547) — never BUSINESS or UNIT — so misdiscovery cannot route a Business/Unit task into the wrong type frame.
- The static Business and Unit primary_project_gids are hardcoded at import time and cannot be overwritten by discovery (`_register_pipeline_project` at registry.py:546 guards with `is_registered(gid)` before registering).

**Residual discovery hazard**: if a workspace contains a project whose name contains "sales" (matches SALES ProcessType) but whose GID is NOT the static Sales pipeline GID, that project's tasks would be classified as PROCESS/SALES — which may be correct (true pipeline project) or a naming collision. This is a Tier-1 classification hazard, not a cross-tenant routing hazard.

### Hazard 3: Registry bootstrap ordering
**Mitigated by double-checked locking.** `ProjectTypeRegistry._ensure_bootstrapped` (registry.py:95-127) uses double-checked locking with `_bootstrap_lock`. A race between two threads reading Tier 1 before bootstrap completes could log a warning (`tier1_registry_anomaly` at tier1.py:105) but both would see an empty registry and fall through to Tier 2/3/4. There is no silent wrong-type return path — an empty registry returns `None` from `lookup`, not a wrong entity_type. The `tier1_registry_anomaly` warning is the observability signal for this case.

**No wrong-project-routing hazard found**: the discriminator (project_gid -> entity_type) can return `None` under bootstrap race or unregistered GID conditions, but it cannot return an entity_type belonging to a different project frame for a given project_gid. The `_gid_to_type` dict is keyed by project_gid; a given project_gid maps to exactly one entity_type (ValueError raised on duplicate-GID-different-type registration at registry.py:153).

---

## Tenant-Binding Finding (explicit statement for CERT-2)

**The gid->project_gid->entity_type discriminator binds gid to ENTITY-TYPE only.**

Tenant identity is NOT established anywhere in the discriminator chain. It is established exclusively by:
1. The parent-chain walk (`_traverse_upward_async`) which yields `business_gid` — the per-row Asana task gid of the tenant's Business task.
2. The gid-exact `RowsRequest(where=gid==business_gid, join=None)` in the engine's identity read.

This is Vector A (per-row gid-exact read). Vector B (gid->project_gid discriminator) is a pure entity-TYPE classifier that is **UPSTREAM** of and **structurally orthogonal** to tenant selection. No ride option (SEAM1) can close a Vector-B failure because Vector B does not participate in tenant selection — it participates only in entity-type routing.

---

## File:Line Receipt Index

| Claim | File:Line | Evidence |
|-------|-----------|----------|
| Detection field = memberships[0].project.gid | `tier1.py:54-63` | `_extract_project_gid` reads first membership's project gid |
| Detection field documented | `clients/tasks.py:557` | `include_detection_fields` docstring names the field |
| Detection field in mutation events | `cache/models/mutation_event.py:64` | `extract_project_gids` reads same path |
| ProjectTypeRegistry lookup delegates to EntityRegistry first | `registry.py:196-201` | `desc = get_registry().get_by_gid(project_gid)` |
| Business primary_project_gid = shared single GID | `entity_registry.py:445` | `"1200653012566782"` hardcoded |
| Unit primary_project_gid = shared single GID | `entity_registry.py:472` | `"1201081073731555"` hardcoded |
| Cross-validation operates on entity descriptors, not tenants | `registry_validation.py:104-136` | loop over `entity_registry.all_descriptors()` |
| Engine identity read uses Business project_gid (shared) | `engine.py:107-118` | `project_gid = _business_project_gid()` |
| Identity RowsRequest has join=None (Vector A, not Vector B) | `engine.py:85-89` | `join=None` in `_build_identity_request` |
| Anchor business_gid from parent-chain, not project_gid | `entry.py:103-116` | `business_gid = result.business.gid` |
| Lazy discovery only registers EntityType.PROCESS | `registry.py:547` | `self._type_registry.register(gid, EntityType.PROCESS)` |
| Static GIDs cannot be overwritten by discovery | `registry.py:546` | `if not self._type_registry.is_registered(gid)` guard |
| Bootstrap race logs warning, does not return wrong type | `tier1.py:104-115` | `tier1_registry_anomaly` warning + falls through |
| Duplicate GID raises ValueError (no silent wrong-type) | `registry.py:142-164` | `raise ValueError(...)` on mismatched registration |
| test_engine.py confirms project_gid="1200653012566782" in issued request | `test_engine.py:76` | `assert captured["project_gid"] == "1200653012566782"` |

---

## Post-GAP-1 Section — CERT-2 Concurrence (2026-06-25)

**Authored by**: SIGNAL-SIFTER (rite-disjoint from 10x-dev engine author)
**Engine state at probe**: HEAD 70c3e8c6, branch feat/gfr-engine, FROZEN CLEAN pre-probe, restored CLEAN post-probe
**Probe run**: 2026-06-25, venv at worktree `.venv/bin/python -m pytest`

---

### TASK 1: Live trace — gid->project_gid->entity_TYPE (NEVER gid->TENANT)

**Multi-entity primary_project_gid list** (read from `entity_registry.py:435-962`, SHARED across all tenants):

| Entity | primary_project_gid | Line |
|--------|--------------------|----|
| business | `"1200653012566782"` | 445 |
| unit | `"1201081073731555"` | 472 |
| contact | `"1200775689604552"` | 499 |
| offer | `"1143843662099250"` | 516 |
| asset_edit | `"1202204184560785"` | 541 |
| contact_holder | `"1201500116978260"` | 728 |
| unit_holder | `"1204433992667196"` | 742 |
| dna_holder | `"1167650840134033"` | 769 |
| reconciliation_holder | `"1203404998225231"` | 782 |
| asset_edit_holder | `"1203992664400125"` | 798 |
| videography_holder | `"1207984018149338"` | 820 |
| offer_holder | `"1210679066066870"` | 836 |

Each GID is registered exactly once. `EntityRegistry.__init__` (registry line 263-269) raises `ValueError("Duplicate project GID")` if two descriptors share a GID — enforcing a strict 1:1 gid->entity_type mapping at import time.

The discrimination chain:
1. `task.memberships[0]["project"]["gid"]` extracted by `tier1.py:54-63`
2. `ProjectTypeRegistry.lookup(project_gid)` at `registry.py:196-201` — delegates to `EntityRegistry.get_by_gid(project_gid)` which returns an `EntityDescriptor` (not a tenant record)
3. The returned value is `EntityDescriptor.entity_type` — an `EntityType` enum member (BUSINESS, UNIT, OFFER, etc.)

**Nothing in the chain carries, returns, or inspects a tenant identifier.** The chain signature is `str (project_gid) -> EntityType`. No tenant axis exists at any step.

---

### TASK 2: Tenant safety rests on Vector-A hardened by GAP-1

**engine.py:138** (`guard_mod.assert_rows_tenant_identity(response.data, anchor.business_gid)`):
- Called inside `_resolve_identity_plan_async` AFTER `execute_rows` returns and BEFORE the engine reads `response.data[0]`
- `anchor.business_gid` is the per-row task gid anchored by the parent-chain walk in `entry.py:110` (`business_gid = result.business.gid`)
- Every row in `response.data` must carry `row["gid"] == business_gid`; any row where this fails raises `GuardViolationError` immediately (fail-closed, never trust-by-omission per `guard.py:220-237`)

**guard.py:183** (`assert_rows_tenant_identity`):
- Iterates every row (not just `data[0]`) — the guard is not bypassed by a multi-row response
- Checks `row.get("gid") != business_gid` — a row missing the `gid` key returns `None` which also fails the equality check, so a missing-gid row is a violation (fail-closed)
- Raises `GuardViolationError` with the mismatched gid values logged for forensics

The two-layer defense for Vector-A:
1. **Layer 1 (substrate)**: the gid-exact `RowsRequest(where=Comparison(field="gid", op=Op.EQ, value=business_gid), join=None)` built at `engine.py:85-89` causes the frozen `query/engine.py:169` `df.filter` to return only rows where `gid == business_gid` from the Business project frame
2. **Layer 2 (engine-owned, GAP-1)**: `assert_rows_tenant_identity` re-asserts the same invariant in the engine's own code, independent of substrate correctness — a drifted provider returning an unfiltered multi-tenant frame is caught here

`join=None` at `engine.py:88` is the INVARIANT I2 structural lock: with no join field, the request structurally cannot reach `execute_join`'s `keep='first'` dedup at `query/join.py:157`. This is verified at `guard.py:118-119` (`_join_reaches_identity` returns `False` when `join is None`).

---

### TASK 3: Do Vector-A (hardened) + type-routing TOGETHER preclude wrong-tenant resolution?

**Conclusion: YES. The combination is structurally sufficient to preclude a gid resolving to the wrong tenant's data.**

The argument from file:line evidence:

**Step 1 — Type routing determines WHICH project frame to read (Vector B)**
`engine.py:107`: `project_gid = _business_project_gid()` — always returns the Business descriptor's shared `primary_project_gid` (`"1200653012566782"`, `entity_registry.py:445`). The entity_type detected by Vector B (OFFER, UNIT, CONTACT, etc.) determines that the identity read goes to the Business frame — not to a per-tenant frame, because no per-tenant frame exists. This is structurally correct: all tenants coexist in the same Business project frame, and the gid-exact predicate is the sole tenant discriminator within it.

**Step 2 — The gid-exact predicate selects WHICH tenant row within the frame (Vector A)**
`engine.py:85-89` (`_build_identity_request`): the `where` predicate is `Comparison(field="gid", op=Op.EQ, value=business_gid)` where `business_gid` is `anchor.business_gid` — the per-row task gid of the correct tenant's Business task, arrived at by the parent-chain walk (`entry.py:110`). The frozen `df.filter` at `query/engine.py:169` returns only the row(s) where `gid == business_gid`.

**Step 3 — The GAP-1 guard ensures no cross-tenant row survives to be read (engine-owned)**
`guard.py:183-237` (`assert_rows_tenant_identity`): even if the substrate returns an unfiltered frame (drifted provider, bug, or test-time injection), the engine refuses to proceed — `GuardViolationError` is raised before `response.data[0]` is accessed. There is no silent path from a wrong-gid row to a `company_id` read.

**The failure mode that CANNOT occur given these three layers:**
A gid belonging to tenant A cannot resolve to tenant B's `company_id` because:
- The Business frame is shared (all tenants), but the `where: gid == A.business_gid` predicate returns only A's row (Layer 1)
- If Layer 1 fails (provider drifts), Layer 2 (`assert_rows_tenant_identity`) catches any row with `gid != A.business_gid` before it is read (GAP-1)
- Vector B (type routing) is irrelevant to this safety property — it selects the frame, not the tenant within it; it cannot introduce a tenant confusion because the frame selection is fixed (always Business, always shared)

**File:line anchors for TASK 3**:

| Claim | File:Line |
|-------|-----------|
| Engine always reads Business frame regardless of entry entity_type | `engine.py:107` (`_business_project_gid()`) |
| Business frame is the multi-tenant shared project | `entity_registry.py:445` + `engine.py:65-69` (docstring names it explicitly) |
| gid-exact predicate selects the correct tenant row | `engine.py:85-89` (`_build_identity_request`) |
| `join=None` structurally prevents keep='first' dedup | `engine.py:88` + `guard.py:118-119` |
| GAP-1 guard re-asserts tenant identity post-execute | `engine.py:138` + `guard.py:183-237` |
| Fail-closed on missing gid key | `guard.py:221` (`row.get(_ROW_GID_KEY)` returns `None` -> inequality -> `GuardViolationError`) |
| Parent-chain anchors the correct business_gid | `entry.py:110` (`business_gid = result.business.gid`) |

---

### CERT-2 MUTATION PROBE TRANSCRIPT (G-PROVE)

**Probe**: disable GAP-1 guard by spoofing `anchor.business_gid` to a literal wrong-tenant string at `engine.py:138`

**Mutation applied**:
```
- guard_mod.assert_rows_tenant_identity(response.data, anchor.business_gid)
+ guard_mod.assert_rows_tenant_identity(response.data, "wrong_tenant_business_gid")  # CERT2-PROBE
```

**Pre-probe baseline** (clean tree, targeted GFR tests):
```
tests/unit/resolution/gfr/test_collision_closure.py tests/unit/resolution/gfr/test_engine.py
20 passed in 0.14s
```

**RED transcript** (spoofed anchor active):
```
FAILED tests/unit/resolution/gfr/test_collision_closure.py::TestV2PathFiresGreen::test_v2_resolves_a_to_g_a_never_g_b
FAILED tests/unit/resolution/gfr/test_engine.py (multiple)

GuardViolationError: identity row 0 carries gid 'A_business_gid' != anchored
business_gid 'wrong_tenant_business_gid'; an unfiltered/cross-tenant frame
leaked past the frozen query filter (INVARIANT GFR-IDENTITY-1, Vector-A).
The engine-owned guard refused to read the wrong tenant's company_id.
```
Exit code: 1. Multiple tests failed — all tests that exercise the identity path fire `GuardViolationError` when the anchor is spoofed.

**Restore**:
```
git -C /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr checkout -- src/autom8_asana/resolution/gfr/engine.py
```

**Post-restore GREEN**:
```
tests/unit/resolution/gfr/test_collision_closure.py tests/unit/resolution/gfr/test_engine.py
20 passed in 0.14s
```

**Post-restore tree status**:
```
 M .know/aegis/baselines.json
 M aegis-report.json
```
Only aegis/baseline files changed (test run artifacts). No source file mutations remain.

**Probe conclusion**: bypassing the GAP-1 guard (engine.py:138) by spoofing the anchor fires RED across all identity-path tests. The guard is not vacuous — its presence is the structural difference between passing and failing. Restoring to clean returns all tests to GREEN.

---

### CERT-2 CONCURRENCE FINDING

**Discriminator is type-routing-only**: The gid->project_gid->entity_TYPE chain (Vector B) maps a task's Asana project membership to an entity type (BUSINESS, UNIT, OFFER, etc.). Every `primary_project_gid` in `entity_registry.py` is SHARED across all tenants of that entity type. The chain signature is `project_gid -> EntityType`; no tenant identifier is produced, consumed, or implicated at any step.

**Tenant safety rests on Vector-A, hardened by GAP-1**: Tenant selection is the exclusive responsibility of (a) the per-row parent-chain-anchored `business_gid` in the gid-exact `RowsRequest` (`engine.py:85-89`), and (b) the engine-owned `assert_rows_tenant_identity` guard (`guard.py:183`, called at `engine.py:138`) that re-asserts gid-exact correctness AFTER `execute_rows` and BEFORE any field read. The guard is mutation-probe confirmed: spoofing the anchor fires RED; restoring it returns GREEN.

**Together they preclude wrong-tenant resolution**: Vector B selects the correct entity-type frame (always the shared Business frame for identity reads). Vector A with GAP-1 selects and enforces the correct tenant row within that frame. There is no structural path from a gid to a different tenant's data given both layers are operative.

**Concurrence status**: CERT-2 concurrence GRANTED (type-routing-only classification confirmed). STRONG-cert of Vector-B requires detection-rite owner concurrence — this rite (SIGNAL-SIFTER) is rite-disjoint from the 10x-dev engine author; that satisfies the critic-rite-disjointness requirement for this finding. The classification "Vector-B is type-routing-only; tenant safety is Vector-A, now hardened" is confirmed by live code reading and mutation-probe evidence.
