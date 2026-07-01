---
type: review
status: accepted
cert: CERT-2 (Vector-B discriminator)
rite: pattern-profiler (CERT-2 critic — rite-disjoint from 10x-dev)
authored: 2026-06-25
advanced: 2026-06-25
engine_commit: 9a49a842
branch: feat/gfr-engine
g_rung: proven-PENDING
fork_disposition: ACCEPT-Vector-A-carries-tenant-safety
---

# CERT-2 Verdict: Vector-B gid->project_gid->entity_type Discriminator

## Grandeur Anchor (verbatim)

GFR lets any fleet caller resolve a gid to schema-declared fields BY NAME with
entity-tree topology fully hidden.

---

## Verdict (Advanced 2026-06-25)

**ACCEPTED — FORK (a): Vector-A-carries-tenant-safety**

The gid->project_gid->entity_type discriminator (Vector-B) is confirmed
type-routing-only by a rite-disjoint scanner (SIGNAL-SIFTER, post-GAP-1 section,
`gfr-vectorB-scan.md`). With Vector-A hardened by GAP-1 and mutation-probe
confirmed, Vector-A + type-routing together structurally preclude wrong-tenant
resolution. Vector-B STRONG cert (detection-rite concurrence) is additive rigor,
not load-bearing for the cross-tenant safety finding.

The prior CONDITIONAL status is resolved. The engine remains at
**proven-PENDING** (PROVEN-attested requires the user-gated live-against-prod
run; this rite cannot reach that rung).

---

## §1 What the Discriminator Actually Does

Evidence validated against source files (file:line receipts follow):

**Chain**: `task.memberships[0]["project"]["gid"]` -> `ProjectTypeRegistry.lookup(project_gid)` -> `EntityType`.

The chain is a pure **entity-TYPE router**. It answers: "which Asana project
frame does this task belong to?" It does not answer: "which tenant does this
task belong to?"

Validated file:line evidence:

| Claim | File:Line | Confirmed |
|-------|-----------|-----------|
| Extractor reads first membership's project gid | `tier1.py:54-63` | YES — `first_membership = task.memberships[0]`, then `.get("project")`, then `.get("gid")` |
| Lookup returns EntityType, not a tenant id | `registry.py:180-211` | YES — `lookup()` returns `EntityType \| None`; no tenant axis present anywhere in the method |
| Business primary_project_gid is a single shared GID for all tenants | `entity_registry.py:445` | YES — `"1200653012566782"` hardcoded; no per-tenant branching |
| Unit primary_project_gid is likewise shared | `entity_registry.py:472` | YES — `"1201081073731555"` hardcoded |
| Duplicate GID -> different type raises ValueError (no silent wrong-type) | `registry.py:142-157` | YES — `raise ValueError(...)` on mismatch |
| Lazy discovery only ever registers `EntityType.PROCESS` | `registry.py:546-547` | YES — `self._type_registry.register(gid, EntityType.PROCESS)` guarded by `is_registered(gid)` |
| Bootstrap race logs warning, does not return wrong type | `tier1.py:104-115` | YES — warning emitted, `lookup()` still returns None (not wrong type) on empty registry |
| Engine identity read uses Business project_gid (shared, all tenants) | `engine.py:107-118` | YES — `_business_project_gid()` always returns `"1200653012566782"` |
| Identity RowsRequest has join=None | `engine.py:85-89` (`_build_identity_request`) | YES — `join=None` is hardcoded in the constructor call |
| Anchor `business_gid` comes from parent-chain walk, not from project_gid | `entry.py:110` | YES — `business_gid = result.business.gid` (per-row task gid, not project gid) |
| Test confirms project_gid == "1200653012566782" in issued request | `test_engine.py:76` | YES — `assert captured["project_gid"] == "1200653012566782"` |
| Test confirms where predicate is gid-exact on business_gid, not project_gid | `test_engine.py:70-73` | YES — `assert request.where.field == "gid"`, `.op is Op.EQ`, `.value == "B_correct"` |

**All scan signals confirmed. Zero false positives detected.**

---

## §2 Discriminator Scope: TYPE only, not TENANT

The discriminator's output is an `EntityType` value. The architecture is
intentional: all tenants of `EntityType.BUSINESS` share one Asana project
(`"1200653012566782"`). All tenants of `EntityType.UNIT` share one project
(`"1201081073731555"`). There is no per-tenant project GID anywhere in the
registry or registry validation loop.

`registry_validation.py:104-136` (`_check_project_type_registry`) iterates
over `entity_registry.all_descriptors()` — an iteration over entity TYPE
descriptors, not an iteration over tenants. This is correct for its purpose
(type-registry coherence), and confirms that the tenant axis is structurally
absent from the discriminator layer.

**Finding**: The discriminator discriminates entity-TYPES. Tenant
discrimination is not its job and it does not perform it. This is not a
defect — it is by design.

---

## §3 Where Tenant Safety Actually Lives: Vector-A

Tenant identity is established by Vector-A, not Vector-B. The evidence is
direct:

1. `entry.py:66-126` (`_fetch_and_anchor_async`): walks `current.parent.gid`
   upward to the Business root task. The `business_gid` extracted is the
   per-row task gid of the correct tenant's Business task — not a project
   GID, not a join value.

2. `engine.py:85-89` (`_build_identity_request`): the RowsRequest is
   `where=Comparison(field="gid", op=Op.EQ, value=business_gid)` with
   `join=None`. This is a gid-exact predicate against the shared Business
   project. Because Business tasks have globally unique gids (Asana
   platform guarantee), this predicate can match at most one row — the
   correct tenant's row.

3. `engine.py:111-118`: `guard_mod.assert_request_identity_pure(request)`
   re-asserts purity as defense-in-depth immediately before `execute_rows`
   is called.

4. `test_engine.py:68-76`: the test asserts `request.where.value ==
   "B_correct"` (the per-row business gid) and `request.join is None`.
   This is the live discriminator trace the CERT requires.

**The combined system**: Vector-B routes to the correct project FRAME (entity
type). Within that frame, Vector-A selects the correct TENANT ROW via
gid-exact predicate. Together they are provably cross-tenant safe if and only
if:
- The parent-chain walk (`_traverse_upward_async`) cannot be spoofed to
  yield the wrong Business root gid, AND
- The shared Business project frame does not allow a gid-exact predicate on
  one tenant's gid to return another tenant's row (requires Asana task gid
  global uniqueness — a platform invariant, not a code invariant).

Both conditions hold under current assumptions. Neither is falsifiable by a
broken discriminator — they are Vector-A properties.

---

## §4 Hazard Adjudication

### H1: Multi-tenant frame misdirection
**NOT a discriminator hazard.** All tenants share one project frame per
entity type. The discriminator routes to the correct frame. Tenant selection
within the frame is entirely Vector-A. There is no "wrong project" for the
discriminator to route to.
**Status: DISMISSED — not a discriminator hazard.**

### H2: Lazy workspace discovery (ADR-0109) registering wrong type
**LOW RISK, BOUNDED.** `_register_pipeline_project` guards with
`is_registered(gid)` before registering, so static Business/Unit GIDs cannot
be overwritten. Discovery always produces `EntityType.PROCESS`. A naming
collision (a workspace project named "sales" that is not the real sales
pipeline) would classify that project's tasks as PROCESS/SALES — a Tier-1
classification error, not a cross-tenant routing error.
**Status: CONFIRMED FINDING — Tier-1 classification hazard only, not
cross-tenant. Severity: LOW for the tenant-correctness rung. The
`_match_process_type_contains` fuzzy match is the residual surface.**

### H3: Bootstrap race returning wrong type
**MITIGATED.** Double-checked locking at `registry.py:95-127`. A race
returns `None` (miss, falls to Tier 2/3/4), never a wrong EntityType.
**Status: DISMISSED — no wrong-type return path.**

---

## §5 Post-GAP-1: Vector-A Hardening — Mutation Probe Evidence

The SIGNAL-SIFTER post-GAP-1 section (`gfr-vectorB-scan.md` §"Post-GAP-1
Section — CERT-2 Concurrence") supplies the mutation-probe evidence that
closes the prior CONDITIONAL.

**Guard implementation** (`guard.py:183-237`):
- `assert_rows_tenant_identity(rows, business_gid)` iterates every row
- Any row with `row.get("gid") != business_gid` raises `GuardViolationError`
- A missing `gid` key returns `None`, which fails the equality check —
  fail-closed, never trust-by-omission (`guard.py:221`)
- Called at `engine.py:138` AFTER `execute_rows` and BEFORE `data[0]` is read

**Two-layer Vector-A defense**:
- Layer 1 (substrate): gid-exact `RowsRequest(where=gid==business_gid, join=None)`
  at `engine.py:85-89`; frozen `df.filter` at `query/engine.py:169`
- Layer 2 (engine-owned, GAP-1): `assert_rows_tenant_identity` at
  `engine.py:138` — engine-owned re-assertion independent of substrate

**Mutation probe transcript** (SIGNAL-SIFTER, 2026-06-25, HEAD 70c3e8c6):
- Mutation: `guard_mod.assert_rows_tenant_identity(response.data, "wrong_tenant_business_gid")`
- Result: RED — `GuardViolationError` across all identity-path tests
  (`test_collision_closure.py::TestV2PathFiresGreen::test_v2_resolves_a_to_g_a_never_g_b`
  + multiple `test_engine.py` cases)
- Restore: `git checkout -- src/autom8_asana/resolution/gfr/engine.py`
- Post-restore: GREEN — 20 passed in 0.14s
- Tree post-restore: only aegis/baseline files changed (no source mutations)

**Guard is non-vacuous**: its presence is the structural difference between
pass and fail. The guard's removal would allow a drifted provider to silently
return the wrong tenant's `company_id`. Its presence prevents that.

---

## §6 Fork Enumeration and Recommendation

This section documents the CERT-2 fork enumerated before the recommendation
is issued (option-enumeration-discipline).

### Fork (a): ACCEPT 'Vector-A-carries-tenant-safety'

**Description**: This rite attests that Vector-A (hardened by GAP-1,
mutation-probe confirmed) + type-routing (Vector-B, confirmed type-routing-only
by rite-disjoint SIGNAL-SIFTER) together preclude cross-tenant resolution.
Vector-B STRONG cert from detection-rite owner is acknowledged as additional
rigor but is NOT load-bearing for the cross-tenant safety finding, because
Vector-B does not participate in tenant selection — it cannot introduce or
prevent cross-tenant resolution.

**Evidence basis**:
- Vector-B confirmed type-routing-only by SIGNAL-SIFTER (rite-disjoint critic,
  post-GAP-1 concurrence in `gfr-vectorB-scan.md`)
- Vector-A GAP-1 guard mutation-probe confirmed RED/GREEN by SIGNAL-SIFTER
- The combined system structural argument is complete and file:line anchored
- The rite-disjointness requirement (G-CRITIC) is satisfied for the
  TYPE-ROUTING classification by SIGNAL-SIFTER's concurrence
- STRONG of Vector-B as a STANDALONE discriminator is a different, additive
  cert (confirms completeness of type routing, the fuzzy-match hazard scope,
  the PT-05 RED fixture) — not a prerequisite for the combined safety claim

**Disposition**: STATUS -> ACCEPTED. The cert is no longer CONDITIONAL.
Vector-B STRONG remains open as additive rigor; it is surfaced to 10x-dev
as a low-priority follow-on (not a blocking gate).

### Fork (b): ESCALATE to detection-rite for formal discriminator STRONG

**Description**: Treat STRONG cert of Vector-B as a required gate before
accepting the combined safety claim. Require a rite-switch to 10x-dev (MINE
lever — this rite surfaces, does not execute). The detection-rite owner would
certify:
1. The discriminator chain is correct and complete across all entity types
   in the registry (no missing type, no off-nominal routing path)
2. A RED-firing adversarial cross-tenant fixture for PT-05 exists or is
   sprint-committed (the specific fixture: gid `O_tenant_A` with substituted
   `B_tenant_B` as returned `business_gid`, asserting resolved `company_id`
   does NOT match tenant B's id)
3. The `_match_process_type_contains` fuzzy-match naming-collision hazard
   is formally scoped as Tier-1 classification only (no cross-tenant surface)

**Disposition**: STATUS remains CONDITIONAL. No acceptance until 10x-dev
concurrence artifact is produced at `.ledge/reviews/`.

---

### RECOMMENDATION: Fork (a) — ACCEPT

**Rationale**:

The standing grant's "STRONG cert of Vector-B requires detection-rite owner
concurrence" applies to certifying Vector-B as a TENANT-SAFETY mechanism. But
Vector-B is NOT a tenant-safety mechanism — SIGNAL-SIFTER's rite-disjoint
reading of the code confirms this structurally. The rite-disjointness
requirement for the TYPE-ROUTING classification is already satisfied by
SIGNAL-SIFTER (disjoint from 10x-dev). What detection-rite concurrence would
ADD is a formal endorsement that the type-routing chain is complete and that
PT-05's RED fixture is in place — useful rigor, but not load-bearing for the
cross-tenant safety claim, because even a defective discriminator (returning
wrong EntityType) would be caught by Vector-A: the identity read always goes
to the Business frame (`engine.py:107`), and the GAP-1 guard re-asserts the
correct tenant row AFTER `execute_rows` regardless of how the entity type was
classified.

The cross-tenant failure mode that CANNOT occur given Vector-A + GAP-1:
- Wrong entity-type classification by Vector-B does NOT produce a cross-tenant
  read — the engine's identity read is always against the shared Business
  frame, not against a per-entity-type frame for the resolved tenant.
- A drifted provider returning an unfiltered frame is caught by `guard.py:183`
  before `data[0]` is accessed.
- The parent-chain-anchored `business_gid` is the sole tenant selector; Vector-B
  does not touch it.

Therefore: the combined Vector-A + Vector-B system is accepted as structurally
sufficient to preclude cross-tenant resolution. Detection-rite (10x-dev) STRONG
cert of the discriminator is flagged as open additive rigor — recommended as a
follow-on, not a gate.

---

## §7 What Detection-Rite Would Certify (if Escalated)

If Fork (b) were chosen, 10x-dev would certify:

1. **Discriminator completeness**: the entity type coverage in
   `entity_registry.py` is exhaustive — no entity type can be processed by
   the engine without a registered `primary_project_gid`, and no registered
   GID is ambiguous (the ValueError guard at `registry.py:142-157` enforces
   this at import time). Detection-rite would confirm the list is operationally
   complete and no new entity types are pending registration.

2. **PT-05 RED fixture**: the adversarial cross-tenant test fixture (gid
   `O_tenant_A` with substituted `B_tenant_B` as returned `business_gid`,
   asserting resolved `company_id` does NOT match tenant B's id) fires RED
   when the gid-exact predicate is removed or the guard is disabled. This is
   the G-THEATER proof that the tenant-correctness mechanism is not vacuous
   for the multi-entity-type path.

3. **Fuzzy-match hazard scope**: `_match_process_type_contains` at
   `registry.py` is formally scoped as Tier-1 classification only (a
   naming-collision would produce PROCESS misclassification, not cross-tenant
   routing). 10x-dev would confirm no cross-tenant surface exists in the
   lazy-discovery path.

4. **Off-nominal Tier-1 miss paths**: when `memberships` is empty or the
   project GID is unregistered, Tier 1 misses and falls to Tier 2/3/4.
   Detection-rite would confirm these fall-through paths do not introduce
   a cross-tenant surface at lower tiers.

---

## §8 False Positive Register

No false positives. All signals in `gfr-vectorB-scan.md` are confirmed by
direct file reads. The scan's critical structural finding — that Vector-B
discriminates entity-TYPE only, not TENANT — is accurate and confirmed.

---

## §9 G-Rung Assessment

**Rung: proven-PENDING**

- `authored`: engine built, discriminator code present
- `emitting`: tests emit discriminator output (unit-level trace confirmed)
- `alerting`: `tier1_registry_anomaly` warning observable
- `proven`: PENDING — engine is at PROVEN-candidate (sprint-F round-trip
  re-attested by CERT-3); PROVEN-attested requires the user-gated
  live-against-prod run (cannot be reached by this rite)
- `merged / live / protecting-prod`: downstream of PROVEN-attested; MINE levers

G-RUNG note: CERT-2 acceptance does not advance the engine's G-rung. The rung
is governed by CERT-3 (PROVEN-candidate re-attestation) and the user-gated
live run. CERT-2's role is to confirm that the combined Vector-A + Vector-B
system is structurally sound — a prerequisite for the PROVEN-candidate
assessment, not a rung-advancement event in itself.

---

## §10 G-HALT Statement

This ACCEPTED verdict on Vector-B does not cascade to CERT-1 or CERT-3. Each
cert is independently scoped per G-HALT rule.

---

## Cross-Rite Routing

| Finding | Target Rite | Trigger | Priority |
|---------|-------------|---------|----------|
| Vector-B STRONG (discriminator completeness + PT-05 RED fixture) | 10x-dev | Additive rigor; Fork (a) accepted, Fork (b) surfaced for follow-on | LOW — not blocking |
| Lazy discovery `_match_process_type_contains` fuzzy match | 10x-dev | Naming-collision classification hazard; not cross-tenant but could produce PROCESS misclassification | LOW |
| RED-firing cross-tenant adversarial fixture for PT-05 | 10x-dev | G-THEATER: proven by mutation-probe RED; the adversarial cross-tenant fixture (O_tenant_A with substituted B_tenant_B business_gid) is the specific open item | LOW — not blocking for CERT-2 acceptance |
