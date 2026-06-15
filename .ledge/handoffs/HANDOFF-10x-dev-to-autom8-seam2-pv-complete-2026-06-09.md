---
type: handoff
handoff_type: implementation   # requirements/PV (10x-dev) → build (autom8 monolith rite)
station: rite-switch seam (10x-dev requirements → autom8/framing)
source_rite: 10x-dev (requirements phase)
target: autom8 monolith owner / autom8 framing rite (SEAM-2 consumer rebind)
date: 2026-06-09
initiative: dataframe-resolution-coherence
seam: SEAM-2
supersedes_premise_of: .ledge/handoffs/HANDOFF-10x-dev-to-autom8-seam2-entity-binding-2026-06-08.md
design_reference: .ledge/specs/SEAM-2-PREMISE-VALIDATION-AND-REQUIREMENTS-2026-06-09.md
evidence_grade: STRONG-on-substrate (first-party live receipts) ; adversarially critiqued (N4: 3 GREEN, 1 RED)
status: proposed
---

# SEAM-2 PV-Complete → Monolith Rebind (rungs named honestly)

> **STOP point.** This is the 10x-dev → autom8-monolith rite boundary. Requirements/premise-validation
> is done; the consumer rebind is the destination rite's work. **No consumer rebound here. No code
> shipped. Production levers stay the operator's.** Route the next `/frame` to `autom8/framing`.

## Rung statement (G-RUNG — not rounded up)

| Element | Rung | Honest qualifier |
|---|---|---|
| SEAM-1 entity-identity contract | **live** | origin/main `e686ba06`, deployed `autom8y-asana-service:494` (2048/8192, image `e686ba0`), 1/1 on autom8y-cluster; active_mrr served 62/$79,485 |
| SEAM-2 **offer-side** substrate | **premise-validated, substrate-ready** | offer frame complete + populated (62/$79,485); Consumer-1 + Consumer-3-mask path clear — *pending* the fallback code-change + soak |
| SEAM-2 **unit-side** substrate | **🔴 HARD-GATED** | unit frame present but economics **100% NULL** (N4) — Consumer-2 rebind BLOCKED until unit-economics populate |
| SEAM-2 consumer rebind | **NOT STARTED** | destination = autom8 monolith rite |
| Full telos (`verified_realized` cross-repo) | **PENDING-SEAM-2** | unchanged |

## What changed vs the 2026-06-08 handoff (read this first)

The prior handoff carried a **misdiagnosed precondition** ("backfill 33 projects with offer prefixes").
Live S3 + origin/main source + a rite-disjoint adversarial panel (N4) **refuted** it:

1. **Single-canonical-project per entity** (`project_registry.py:24-28`): offers live ONLY under
   `OFFER_PROJECT=1143843662099250`, units ONLY under `UNIT_PROJECT=1201081073731555`. Consumers read
   **one project each** (`Project.get_df → fetch_project_rows(project_gid=self.gid)`), never a 34-way
   fan-out. **There is no 33-project backfill.** The 33 client-project legacy `sections/` are orthogonal
   migration hygiene.
2. **Offer substrate is complete + populated** (62 rows, real economics). Consumer-1 rebind to
   `entity=offer` is **cold-miss-safe now**.
3. **Unit substrate is present-but-HOLLOW** (N4 RED): `1201081073731555/unit/sections/` has 3021 rows
   but `mrr`/`weekly_ad_spend`/`discount` are 100% null. **Consumer-2 rebind would ship a guaranteed
   DEGRADED/$0 unit denominator** — the FM-4 it claims to close. **HARD GATE.**
4. **Consumer-3 reads a THIRD project** `OfferHolders` (`1210679066066870`), not Consumer-1's frame —
   its substrate is unverified (residual-PV).

## The real gate (replaces "backfill 33")

A consumer rebind is safe to merge+deploy when **its** preconditions hold:

- **Consumer-1 (BusinessOffers → `entity=offer`)** & **Consumer-3 (ad_reporting):**
  1. ✅ #111 merged.
  2. ⚠️ `legacy_fallback_enabled=False` — **CODE+DEPLOY change** (no env lever; ctor sites default `True`:
     `progressive.py:298`, `legacy.py:130`, `section_persistence.py:1050`). Closes the **live 7-row
     collision** (`storage.py:977` guard; legacy root rewritten today, DuckDB=7).
  3. 🟡 verify `1210679066066870` OfferHolders v2 frame present/populated (Consumer-3 residual).
  4. 🕒 CR-3 soak clean through ~2026-06-11T12:25Z (IC sequencing courtesy).
- **Consumer-2 (payments/mrr → `entity=unit`, remove `fillna(0)`):** all of the above **PLUS**
  🔴 **unit economics populated** — root-cause + fix + warm the unit extractor so `mrr`/`weekly_ad_spend`
  are non-null. **Today: blocked.**

## Consumer rebind plan + proof standard

Full per-consumer loci, behavioral-change note (DEGRADED vs silent $0), options (Option A recommended),
and the broken-fixture-RED proof standard are in the **design_reference spec** (`§3`, `§4`, `§5`, `§6`).
Proof standard summary: broken-fixture-RED + live `active_mrr --entity-type offer`=62/$79,485 +
ad_reporting cardinality consistent with 62 + (Consumer-2) non-null unit MRR.

## DEFER / HARD-GATE manifest (watch-registered)

- 🔴 **HARD-GATE-SEAM2-UNIT-POPULATION** — unit economics 100% null; blocks Consumer-2. *(engineering work — unit extractor/warm)*
- **GATE-SEAM2-FALLBACK-FLIP** — `legacy_fallback_enabled=False` (code+deploy); offer-side precondition. *(operator lever)*
- **DEFER-SEAM2-HOLDER-SUBSTRATE** — verify `1210679066066870` populated (Consumer-3).
- **DEFER-LEGACY-DELETE** — 33 client-project legacy `sections/` (hygiene; task #53(d) HELD). *(operator lever)*
- **DEFER-AMBER-1/2** — OK-on-absence g2 guards + dark receiver SLI/EMF (sre/observability frontier).
- **DEFER-G-DENOM-FIRSTPARTY-CLI** — repair worktree uv-workspace path so the active_mrr CLI re-derives first-party.

## Routing

- **Next `/frame` → `autom8/framing`** for the SEAM-2 consumer rebind (the build).
- **Parallel, independent of SEAM-2 → `sre`/observability:** the unit-population hard gate is itself a
  data-population defect (unit extractor/warm) that the autom8y-asana side may need to fix first — and
  the AMBER-1/2 observability hardening. Either can proceed without the monolith rebind.
- Do **NOT** dispatch the destination rite's specialists from here. Production-mutating levers
  (fallback code-change+deploy, the rebind merge+deploy, legacy delete, soak sign-off) stay the operator's.

*10x-dev requirements phase, 2026-06-09. SEAM-1 live; SEAM-2 offer-side substrate-ready, unit-side
hard-gated; consumer rebind NOT started. Every claim re-derived from origin/main + production AWS and
adversarially critiqued (N4). The stale local checkout was never trusted.*
