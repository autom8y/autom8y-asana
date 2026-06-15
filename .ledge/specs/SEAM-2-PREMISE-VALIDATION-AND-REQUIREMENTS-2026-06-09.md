---
type: spec
spec_kind: premise-validation + requirements
initiative: dataframe-resolution-coherence
seam: SEAM-2 (autom8 monolith consumer entity-binding rebind)
rite: 10x-dev (requirements phase)
date: 2026-06-09
supersedes_premise_of: .ledge/handoffs/HANDOFF-10x-dev-to-autom8-seam2-entity-binding-2026-06-08.md
rung: "SEAM-2 substrate premise-validated"  # premise-validation < design < build < shipped < verified-realized
evidence_grade: STRONG-on-substrate (live S3/ECS/git receipts, first-party) ; adversarially critiqued (N4: 3 GREEN, 1 RED banked — unit substrate hollow)
status: proposed
discipline: >
  Every load-bearing premise re-derived LIVE this pass from origin/main (e686ba06) + production AWS,
  never from the stale local cr3/gate2 checkout (3bbb9bc8). The charter's premise #1 ("backfill 33
  projects") is REFUTED at source — recorded here as the headline correction. No production code
  changed. No consumer rebound. Production-mutating levers stay the operator's.
---

# SEAM-2 — Premise-Validation & Requirements (corrected)

> **Telos:** honest offer-economics — `active_mrr` served from the entity-keyed offer substrate so the
> denominator is the true active-offer set (**62 / $79,485**), not a stale/empty fossil.
> **Rung driven here:** *SEAM-1 fully-live / SEAM-2 substrate premise-validated.* We author the
> requirements + the real precondition set. **We rebind zero consumers.**

---

## N4 — ADVERSARIAL CRITIQUE OUTCOME (rite-disjoint panel, 2026-06-09)

A 4-critic adversarial panel (`wf_19471486-815`, default-to-REFUTED) attacked the load-bearing claims.
**Core premise inversion SURVIVED (3× GREEN); one RED landed on the unit substrate.**

| Lens | Verdict | Receipt |
|---|---|---|
| domain-model | 🟢 GREEN | holder projects = distinct entity types; no economics consumer reads mrr from a holder gid; `.../1210679066066870/offer/` empty in S3 |
| consumer-fanout | 🟢 GREEN | every read = `Project.get_df → fetch_project_rows(project_gid=self.gid)`, single gid; no 34-way fan-out |
| fallback-risk | 🟢 GREEN | 7-row collision LIVE (legacy root watermark `2026-06-09T12:51Z`, DuckDB=7 active); `storage.py:977` guard closes the hole with `fallback=False` |
| substrate-freshness | 🔴 **RED** | unit `mrr`/`weekly_ad_spend`/`discount` **100% NULL** across 3021 rows / 13 parquet (column present, genuinely empty) |

**Amendments banked from N4 (this revision):**
1. **Unit substrate is HOLLOW, not complete** — promoted `DEFER-SEAM2-UNIT-POPULATION` to a **HARD GATE** blocking Consumer-2 rebind (§2, §9). The headline §0 conclusion is corrected: complete **offer-side**, hollow **unit-side**.
2. **§8 `legacy_fallback=False` is a CODE+DEPLOY change, not a config/env flip** — no `LEGACY_FALLBACK` env plumbing; all construction sites default `True` (`progressive.py:298`, `legacy.py:130`, `section_persistence.py:1050`).
3. **Consumer 3 reads a THIRD project** `OfferHolders` (`1210679066066870`) via its own `get_df` (borrows Consumer 1's pv-pairs only as a mask) — added to residual-PV (§2, §3).
4. **Consumer 1 FM-3 mechanism** restated as content/scope collision (the legacy frame *carries* `offer_id`; wrong-7 is content, not a missing column) (§3).
5. The 7-row collision is **confirmed live** (not moot) — strengthens §2 gate-item-2's rationale.

---

## 0. HEADLINE — the charter's premise #1 is REFUTED at source

The incoming charter (and the 2026-06-08 recon handoff) carried the precondition:

> *"only 1 of 34 project prefixes carries `offer/sections/` … routing any consumer to `entity=offer`
> before the other 33 are backfilled ⇒ cold-miss ⇒ $0/raise."*

**This is a misdiagnosis built on a wrong mental model** (offers distributed across all 34 client
projects). Live S3 + origin/main source prove the actual architecture:

- **Each entity type has ONE canonical project** holding all its entities *as sections* (incl. the
  HOLDER entity types, each its own distinct canonical project — N4 domain-model):
  - `core/project_registry.py:24-28` → `OFFER_PROJECT = "1143843662099250"`, `UNIT_PROJECT = "1201081073731555"`, `OFFER_HOLDER_PROJECT = "1210679066066870"`, `UNIT_HOLDER_PROJECT = "1204433992667196"` (also `CONTACT_PROJECT`, `ASSET_EDIT_PROJECT`, …).
  - `core/entity_registry.py:511-531` offer `primary_project_gid="1143843662099250"` (category=LEAF); `:830-843` `offer_holder` `primary_project_gid="1210679066066870"` (category=HOLDER, `holder_for="offer"`) — a *different* entity type, not a second offer-bearing project. `OfferHolder` exposes offers only as sub-models resolved via `SUB_MODEL_PROJECT=BusinessOffers` (`1143843662099250`).
  - `models/business/offer.py:87 PRIMARY_PROJECT_GID`, `section_timeline_service.py:84 BUSINESS_OFFERS_PROJECT_GID`.
- The **v2 entity frame exists for exactly the project each SEAM-2 consumer reads** — but *presence ≠ population* (the FM-4 lesson, re-applied to ourselves):
  - offer → `s3://autom8-s3/dataframes/1143843662099250/offer/sections/` = **11 parquet, 62 rows, genuinely populated** (N4 confirmed `mrr>0` real dollars) — **1/1 ✓ POPULATED**
  - unit  → `s3://autom8-s3/dataframes/1201081073731555/unit/sections/`  = present + fresh (13 parquet, 3021 rows) **but `mrr`/`weekly_ad_spend`/`discount` 100% NULL** — **1/1 PRESENT, 0/1 POPULATED 🔴**
- The consumers read **one canonical project each**, not a 34-way fan-out (N4 consumer-fanout — every read = `Project.get_df → fetch_project_rows(project_gid=self.gid)`):
  - Consumer 1 `BusinessOffers(Project)` — `business_offers/main.py:67 PROJECT_GID = "1143843662099250"`.
  - Consumer 2 `BusinessUnits(Project)` — `business_units/main.py:39 PROJECT_GID = "1201081073731555"`.
  - Consumer 3 reads a *third* project `OfferHolders` — `offer_holders/main.py:18 PROJECT_GID = "1210679066066870"` (its own `get_df`; borrows Consumer 1's pv-pairs only as a mask).

**∴ The structural premise holds — single-canonical-project, no 34-way fan-out, no 33-project
backfill.** The 33 client-project legacy `sections/` frames are orthogonal hygiene (the migration
*delete* step), **not** a SEAM-2 blocker.

**BUT (N4 RED): substrate completeness is offer-side only.** The OFFER substrate is complete +
populated (62/$79,485). The **UNIT substrate is present-but-hollow** — its economics columns are
entirely null, so Consumer-2 rebind to `entity=unit` is **NOT substrate-ready** and is **hard-gated**
on unit-economics population (§2). We do not round up: *presence is not population* — the very contract
this campaign exists to enforce, caught applying to our own readiness claim.

This correction is the load-bearing output of the requirements phase: it converts SEAM-2 from
"blocked on a large backfill" to "gated only on a single operator config flip + a soak window."

---

## 1. Live premise matrix (N1 — every row a first-party receipt)

| # | Premise | Verdict | Receipt (this pass) |
|---|---|---|---|
| A | origin/main HEAD | 🟢 GREEN | `e686ba06239a1d92abb2d3428914051ae2b4675d` (gh api `/commits/main` ∧ `git ls-remote` agree) |
| B | #111 SEAM-1 / #108 gate / #103 PQ-5 / #112 re-pin merged | 🟢 GREEN | REST: `7fa56d19` / `da3b2150` / `76246f48` / `e686ba06`, all `merged:true` |
| C | AWS auth persists | 🟢 GREEN | `sts get-caller-identity` → acct `696318035277`, `user/tom.tenuta` |
| D | Receiver substrate | 🟢 GREEN | `autom8y-asana-service:494` (byte-identical to 493): cpu=2048 mem=8192 image `…asana:e686ba0`, running 1/1 on **autom8y-cluster** |
| **P1-offer** | **offer frame exists + POPULATED** | **🟢 PV-PASS · charter REFUTED** | single-canonical-project (§0); `1143843662099250/offer/sections/` = 11pq / 62 rows / real `mrr>0` (N4) |
| **P1-unit** | **unit frame populated** | **🔴 RED (N4)** | `1201081073731555/unit/sections/` present+fresh (3021 rows) but `mrr`/`weekly_ad_spend`/`discount` **100% NULL** — present ≠ populated |
| **P1-holder** | **Consumer-3 OfferHolders substrate** | **🟡 UNVERIFIED** | `1210679066066870` (Consumer 3's read) not in this matrix; verify before ad_reporting trusts its cardinality |
| **P2** | **dependency gate** | **🟡 RE-CHARACTERIZED** | #111 merged ✓ · `legacy_fallback_enabled=False` **NOT done** & is a **CODE change** (no env plumbing; default `True` `storage.py:347`; all ctor sites default) · offer frame populated ✓ · **unit frame hollow → hard gate** · "delete 33 legacy" = hygiene, not blocker |
| P3 | S3 v2 layout `…/{gid}/{entity_type}/sections/` | 🟢 GREEN | `offline.py:8,42`; per-gid census: 0 legacy-only, 1 v2-only, 33 both-layouts |
| P4 | bare `active_mrr` auto-routes to offer scope | 🟢 GREEN | `metrics/definitions/offer.py` `_ACTIVE_OFFER_SCOPE(entity_type="offer", classification="active", dedup=[office_phone,vertical])`, filter `mrr>0` |
| P5 | CR-3 soak | 🟡 IN-PROGRESS | g2-cutover guards **5/5 OK** (but `treat_missing=notBreaching` ⇒ OK-on-absence / AMBER); ~5/7d, completes **2026-06-11T12:25:08Z**; `error-count-high` touched 10.0 (==threshold, not over) @ 06-09 11:29 |
| P6 | premise corrections | 🟢 CONFIRMED | receiver on **autom8y-cluster** (not autom8-cluster); live rev **494** (not 493); `active_mrr` ∉ AMP (`outcome_total`→`[]`) |
| G-DENOM | active offer denominator = 62 / $79,485 | 🟢 PV-PASS (rite-disjoint grade) | 11 parquet under canonical offer prefix (own `s3 ls`) + entity-aware reader (`offline.py:42`) + sound polars scope (own `git show`) + eunomia same-HEAD same-day re-fire `value=79485.0`/shape `(62,4)`. *First-party numeric re-derivation BLOCKED by worktree uv-workspace path breakage (`autom8y-api-schemas` editable dep) — noted, not rounded up.* |
| AMBER-2 | receiver SLI/EMF | 🟡 DARK | AMP `outcome_total` → empty vector |

**HALT premises:** none RED. P2 and P5 are amber-gated on operator levers + the soak clock, not on engineering work.

---

## 2. The REAL dependency gate (re-characterized)

SEAM-2 consumer rebind is safe to *merge & deploy* when **all** hold:

1. ✅ **#111 (SEAM-1) merged** — DONE (`7fa56d19` in `origin/main`).
2. ⚠️ **`legacy_fallback_enabled=False` in production** — **NOT done**, and (N4 correction) it is a **CODE+DEPLOY change, not a config/env flip**: there is no `LEGACY_FALLBACK` env plumbing and every construction site (`progressive.py:298`, `legacy.py:130`, `section_persistence.py:1050`) instantiates `S3DataFrameStorage(...)` without the arg → live default `True`. *Why load-bearing (N4-confirmed live):* with fallback `True`, a `None` v2 offer read falls back via `storage.py:1162/1258/1339` to the legacy entity-agnostic root — which for `1143843662099250` is the **live 7-row collision** (legacy `dataframe.parquet` rewritten today, watermark `2026-06-09T12:51Z`, DuckDB = 7 active rows). With `fallback=False`, `storage.py:977` returns `None` *before* any legacy read → honest DEGRADED. This is the no-silent-wrong-value guarantee SEAM-2 depends on.
3. **v2 entity frames POPULATED for the projects each consumer reads** — **SPLIT**:
   - **offer** (`1143843662099250`) → ✅ **DONE** (62 rows, real economics) — Consumer 1 + Consumer 3-mask ready.
   - **unit** (`1201081073731555`) → 🔴 **HARD GATE — NOT done.** Frame present but `mrr`/`weekly_ad_spend`/`discount` 100% NULL (N4). **Consumer-2 rebind MUST NOT proceed until unit economics populate** (else the rebind ships a guaranteed DEGRADED/$0 unit denominator — the FM-4 it claims to close). Root-cause the unit-economics extraction/warm before rebind.
4. 🟡 **Consumer-3 substrate** (`1210679066066870` OfferHolders) — verify its v2 frame is present/populated before trusting ad_reporting fan-out cardinality (N4 consumer-fanout residual).
5. 🕒 **CR-3 soak complete** (~2026-06-11T12:25Z) — sequencing courtesy so a monolith deploy does not perturb the receiver soak window. Orthogonal to correctness; an IC/operator call.

**The `legacy sections/` delete of 33 client-projects** is explicitly **out of the SEAM-2 gate** — it is migration hygiene (operator lever, task #53(d) HELD), and deleting it does not change any offer/unit read.

---

## 3. Per-consumer rebind plan (DESTINATION rite — autom8 monolith; NOT executed here)

> No edits made in this artifact. File:line are rebind targets for the monolith owner.

### Consumer 1 — `BusinessOffers.active_offers_frame`
- **Locus:** `apis/asana_api/objects/project/models/business_offers/main.py:199-207` (reads `super().active_frame.copy()` then filters `offer_id.isna()`); class `PROJECT_GID = "1143843662099250"` (L67). Denominator sibling: `get_section_group_phone_vertical_pairs` (L310-375 — the 7-vs-62 source).
- **Current (FM-3):** reads the **project-entity / legacy-scoped** frame for `1143843662099250`, which is the wrong *scope* for offer economics. (N4 precision: the legacy frame *carries* an `offer_id` column — identical 25-col schema — so the defect is **content/scope collision** (only 7 offer-tagged active rows at the collision key), **not** a literally-absent column. The `offer_id.isna()` filter then yields the wrong set regardless.)
- **Fix:** rebind the underlying frame read to **`entity=offer`**. The offer frame carries `offer_id, mrr, cost, weekly_ad_spend` (`schemas/offer.py`, `extractors/offer.py`).
- **Cold-miss risk:** **NONE now** — the offer frame for `1143843662099250` exists (62 rows). (Contingent on gate-item 2: fallback=False, so a transient miss surfaces DEGRADED, not the 7-row fossil.)

### Consumer 2 — `payments/mrr.py` unit economics
- **Locus:** `entry_points/debug/payments/mrr.py:242-254` — `frame = UNITS.query_frame(UNITS, sections="ALL", …)`; `UNITS` = `BusinessUnits` (`PROJECT_GID="1201081073731555"`).
- **Current (FM-4 silent $0):**
  ```python
  for col in ["mrr", "weekly_ad_spend", "discount"]:
      if col not in frame.columns: frame[col] = 0      # mask-to-zero on absent columns
  frame["mrr"] = frame["mrr"].fillna(0)
  frame["weekly_ad_spend"] = frame["weekly_ad_spend"].fillna(0)
  frame["discount"] = frame["discount"].fillna(0).astype(float)
  ```
- **Fix:** rebind to **`entity=unit`** (unit frame carries the economics columns). Then remove the masks **per-column judgment**:
  - `mrr`, `weekly_ad_spend`: **remove** the `if-not-in`+`fillna(0)` → absent ⇒ DEGRADED/raise, never silent $0 (a real $0 and an absent frame must be distinguishable).
  - `discount`: `fillna(0)` *may* be legitimate (no-discount = 0) — owner decides; if kept, document the intent so it is not mistaken for the FM-4 mask.

### Consumer 3 — `ad_reporting` ECS controller (derivative, mechanism corrected by N4)
- **Locus:** `entry_points/jobs/ecs/ad_reporting/controller.py:12` (dup `runs/ecs/…:12`) → `OfferHolders().active_offer_holders_frame` → `OfferHolders.get_df(sections="ALL")` on its **own** `PROJECT_GID = "1210679066066870"` (`offer_holders/main.py:18`). It does **NOT** read Consumer 1's frame — it borrows `BusinessOffers().active_offer_phone_vertical_pairs` only as a MultiIndex filter **mask** (`offer_holders/main.py:41,50-63`).
- **Fix:** **no direct binding change** — but its correctness has **two** dependencies: (a) Consumer 1's pv-pairs denominator (the 7-vs-62 mask source) must be correct, and (b) the OfferHolders project (`1210679066066870`) v2 frame must be present/populated (P1-holder residual). If (b) is absent with `fallback=True`, the fan-out can silently key off a legacy/collision set — the same FM-3 class on an unverified project. Verify the fan-out cardinality matches the 62-denominator (not 7, not 0) **and** that `1210679066066870` is substrate-ready.

---

## 4. Behavioral change to accept (carry into the monolith PR description)

`fillna(0)` removal **is the correct behavior**. Where the project-entity binding currently fills
missing economics as $0, the entity-keyed frame surfaces **DEGRADED** (the `population_receipt_below_floor`
signal in autom8y-asana) instead:

- **Before:** MRR = $0, silent — looks like real $0 revenue, blocks alerting.
- **After:** frame absent/degraded → visible DEGRADED, not silent $0.

Any downstream that treats $0 as a *valid economic value* (revenue dashboards, billing, SLA metrics)
must be audited for this assumption flip before the SEAM-2 PR merges.

---

## 5. Proof standard (G-THEATER — broken-fixture-RED, never green-run alone)

A consumer rebind is proven when **all three** hold:

1. **Broken-fixture-RED:** author a fixture asserting the *old* `entity=project` binding returns the
   incorrect/empty set; run it RED on the unfixed binding, GREEN after rebind. (Mirror of the SEAM-1
   `_entity_segment` mutation proof eunomia re-verified load-bearing.)
2. **Live active-offer count:** post-rebind, `python -m autom8_asana.metrics active_mrr --entity-type offer`
   = 62 / ~$79,485; then in the monolith `BusinessOffers.active_offers_frame` returns a count consistent
   with 62 (not 7, not 0).
3. **ad_reporting fan-out cardinality:** Consumer 3 fans out to a holder count consistent with the
   62-denominator (not the 7-row collision, not a $0 set).
4. **Unit economics non-null (Consumer-2 HARD precondition):** before Consumer-2 rebind, the unit frame
   `1201081073731555/unit/sections/` must carry **non-null `mrr`/`weekly_ad_spend`** for a sane fraction
   of active units (today: 100% null — N4). The broken-fixture here is the inverse of the others: assert
   the rebind surfaces a *populated* unit MRR (not DEGRADED/$0) — RED while the frame is hollow, GREEN
   once the unit-economics extraction is fixed and warmed.

---

## 6. Options enumerated (N2 /shape — sequencing of the operator levers)

| Option | Sequence | Trade-off | Verdict |
|---|---|---|---|
| **A (recommended)** | flip `legacy_fallback=False` → confirm 62-stable → soak completes (06-11) → rebind consumers → deploy → verify | Maximizes safety: the no-silent-wrong-value guarantee is *in place before* any consumer trusts the offer frame. | ✅ **RECOMMENDED** |
| B | rebind first, flip fallback later | A transient v2 miss during the window serves the 7-row fossil silently — reintroduces the exact defect SEAM-2 closes. | ❌ rejected (violates the telos) |
| C | also delete 33 legacy `sections/` before rebind | Couples SEAM-2 to migration hygiene that does not gate it; enlarges the irreversible surface for no correctness gain. | ❌ rejected (scope creep; keep DEFERred) |

**Recommended path = Option A.** Note all three mutating steps (fallback flip, rebind merge+deploy,
legacy delete) are **operator levers** — surfaced in §8, none executed here.

---

## 7. Rung statement (G-RUNG — not rounded up)

- **SEAM-1: live** (`origin/main e686ba06`, deployed `autom8y-asana-service:494`, image `e686ba0`, 62/$79,485 served).
- **SEAM-2 substrate: premise-validated** (this artifact) — **offer-side substrate complete + populated; unit-side present-but-hollow (hard-gated)**; gate re-characterized; plan + proof-standard authored; adversarially critiqued (N4, 1 RED banked). **No consumer rebound. No code shipped.**
- **SEAM-2 consumer rebind: NOT STARTED** — destination = autom8 monolith rite.
- **Full telos (`verified_realized` cross-repo): PENDING-SEAM-2.**
- **CR-3 soak: in-progress, NOT protecting-prod** (AMBER guards + dark SLI; positive-signal hardening is a separate sre/observability frontier).

---

## 8. Operator-mutating levers (surfaced, NOT executed)

```
# Gate-item 2 — set legacy_fallback_enabled=False (the no-silent-wrong-value guarantee).
#   N4: this is a CODE+DEPLOY change (no env lever) — pass legacy_fallback_enabled=False at the
#   S3DataFrameStorage construction sites (progressive.py:298, legacy.py:130, section_persistence.py:1050)
#   or add env plumbing; then redeploy receiver on autom8y-cluster. NOT a runtime config flip.
# UNIT-POPULATION (HARD GATE, Consumer-2) — fix + warm the unit-economics extraction so
#   1201081073731555/unit/sections/ carries non-null mrr/weekly_ad_spend (today 100% null). Engineering
#   work, not purely an operator lever — likely a unit extractor/warm-config defect to root-cause first.
# Soak — IC confirm CR-3 clean through ~2026-06-11T12:25:08Z before perturbing with a monolith deploy
# SEAM-2 rebind — merge the monolith PR (entity=project → offer/unit; fillna removal) then deploy
#   (Consumer-1 + Consumer-3 offer-side may proceed once fallback+soak clear; Consumer-2 BLOCKED on unit-population)
# Migration hygiene (DEFERred, not a SEAM-2 gate) — delete 33 client-project legacy sections/ post-confirm
```

## 9. DEFER manifest (watch-registered, not scope-crept)

- **GATE-SEAM2-FALLBACK-FLIP** — `legacy_fallback_enabled=False` (CODE+DEPLOY change per N4; gate-item 2). Offer-side rebind precondition.
- **🔴 HARD-GATE-SEAM2-UNIT-POPULATION** — `1201081073731555/unit/sections/` economics measured **100% NULL** (N4). **Blocks Consumer-2 rebind.** Root-cause + fix + warm the unit-economics extraction before rebind (no longer a low-stakes DEFER — it is a measured hard gate).
- **DEFER-SEAM2-HOLDER-SUBSTRATE** — verify `1210679066066870` (Consumer-3 OfferHolders) v2 frame present/populated before trusting ad_reporting cardinality (N4 consumer-fanout residual).
- **DEFER-LEGACY-DELETE** — 33 client-project legacy `sections/` (migration hygiene; task #53(d) HELD).
- **DEFER-AMBER-1/2** — OK-on-absence g2 guards + dark receiver SLI/EMF (sre/observability frontier).
- **DEFER-G-DENOM-FIRSTPARTY-CLI** — repair the worktree uv-workspace path so the active_mrr CLI re-derives 62/$79,485 first-party (env hygiene; rite-disjoint receipt currently carries it).

---

*10x-dev rite, requirements phase, 2026-06-09. Premise re-derived live from origin/main + production AWS;
the stale local checkout was never trusted. Charter premise #1 refuted at source. Adversarially critiqued
by a rite-disjoint panel (N4): the structural inversion survived 3×; one RED banked (unit substrate hollow)
which became a hard gate; precision corrections folded in. Production levers stay the operator's.*
