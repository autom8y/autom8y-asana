---
type: handoff
station: transfer (docs → autom8 monolith owner)
procession: inquisition-2026-06-08
source_rite: docs (knowledge station)
target: autom8 monolith owner (SEAM-2 entity-binding rebinding)
date: 2026-06-08
initiative: dataframe-resolution-coherence
seam: SEAM-2
dependency_gate: SEAM-1 live (PR #111 merged + legacy_fallback_enabled=False + S3 migration)
status: proposed
evidence_grade: STRONG-on-mechanism (file:line both repos, recon handoff HANDOFF-recon-dataframe-resolution-2026-06-08.md)
---

# SEAM-2 Production Handoff — autom8 Monolith Entity-Binding Rebinding

## What This Handoff Is

Three consumers in the autom8 monolith read DataFrames bound to `entity=project` when they need offer or unit economics. The `entity=project` frame carries no economics columns (`mrr`, `offer_id`, `cost`, `weekly_ad_spend`, `discount`). Each consumer masks-to-empty or fills $0 silently. This is the FM-3 wrong-source entity-binding defect class.

This handoff delivers the exact binding loci, the fix description, the behavioral change to accept, the proof standard, and the dependency gate. No production code changes are made here — this repo (autom8y-asana) does not own the autom8 monolith.

## Dependency Gate

**Do NOT merge SEAM-2 until SEAM-1 is live.** SEAM-1 live means:
1. PR #111 (`cr3-dfr/seam1-entity-identity` → `main`) merged.
2. `legacy_fallback_enabled=False` flipped in the production deployment.
3. S3 key migration complete (legacy entity-agnostic keys copied to `{project_gid}/{entity_type}/` paths, then deleted).

Until step 3 is confirmed, the entity-keyed S3 paths do not exist for existing data. SEAM-2 consumers switching to `entity=offer` before step 3 will cold-miss every request (offer-domain is cache-only → `None` → empty denominator → every MRR calculation returns $0 or raises).

## Consumer Binding Loci (autom8 monolith — cross-repo)

### Consumer 1 — BusinessOffers active_offers_frame

**File:line**: `business_offers/main.py:91` (autom8 monolith)
**Current behavior**: `BusinessOffers` is a `Project` subclass. Its `active_offers_frame()` method calls `get_df(entity=project, ...)`. The `entity=project` frame has no `offer_id` column. The method then filters `offer_id.isna()` — which matches ALL rows because `offer_id` is absent from the project frame — and returns the wrong set (or no rows, depending on the filter direction).
**Fix**: rebind to `entity=offer`. The offer frame carries `offer_id`, `mrr`, `cost`, `weekly_ad_spend` from the cascade extraction at `schemas/offer.py:41-89` in autom8y-asana.
**Downstream**: `BusinessOffers.get_section_group_phone_vertical_pairs` (autom8 `business_offers/main.py:310-370`) — the active-offer denominator (the 7 vs 62 source); this also needs the rebinding.

### Consumer 2 — payments/mrr.py units economics

**File:line**: `payments/mrr.py:242-254` (autom8 monolith)
**Current behavior**: `BusinessUnits` (a `Project` subclass) reads `entity=project`. The project frame carries no `mrr`, `weekly_ad_spend`, or `discount` columns. Lines 242-254 contain:
```python
if col not in frame.columns: frame[col] = 0   # ← silent $0 fill
```
followed by `fillna(0)`. Every unit's MRR and ad spend is silently $0 — a production data-accuracy error, not an exception.
**Fix**: rebind to `entity=unit`. The unit frame carries unit economics columns. Remove the `if col not in: = 0` + `fillna(0)` patterns — replace with explicit DEGRADED handling or raise if columns are absent.

### Consumer 3 — ad_reporting ECS controller

**File:line**: `entry_points/jobs/ecs/ad_reporting/controller.py:12` (autom8 monolith)
**Current behavior**: LIVE SCHEDULED FAN-OUT. The controller fans out ad reporting via `OfferHolders`, which is compounded from `BusinessOffers` (Consumer 1). Because Consumer 1 uses the wrong entity binding, the fan-out operates on the wrong set. This is the live-degraded ECS job observed in the recon (`HANDOFF-recon-dataframe-resolution-2026-06-08.md:46`).
**Fix**: depends on Consumer 1 rebinding. Once `BusinessOffers.active_offers_frame` returns the correct offer-entity frame, `OfferHolders` and the ad_reporting fan-out will operate on the correct set without further changes to this controller — verify the downstream chain.

## Behavioral Change to Accept

**fillna(0) removal is correct behavior.** Where `entity=project` currently fills missing economics as $0, the entity-keyed frame will surface `DEGRADED` status instead (via the `population_receipt_below_floor` signal in autom8y-asana). $0 revenue must never be served silently when the frame is absent or degraded:

- Before fix: MRR = $0 (silent, looks like real $0 revenue, blocks alerting)
- After fix: frame absent → DEGRADED status → visible error, not silent $0

Any downstream code that treats $0 as a valid economic value (revenue dashboards, billing calculations, SLA metrics) must be audited for this assumption change before SEAM-2 merges.

## Proof Standard (broken-fixture-RED + live active-offer count)

The SEAM-2 fix is proven when:

1. **Broken-fixture-RED**: author a test fixture that calls `BusinessOffers.active_offers_frame()` with the old `entity=project` binding and assert it returns an incorrect/empty set. Run it RED (it passes with the wrong binding). Apply the fix. Run GREEN (it passes with `entity=offer`).

2. **Live active-offer count**: after SEAM-1 is live and SEAM-2 is merged, run:
   ```
   python -m autom8_asana.metrics active_mrr --entity-type offer
   ```
   in autom8y-asana to verify the count = 62 rows / ~$79,485. Then verify in the autom8 monolith that `BusinessOffers.active_offers_frame()` returns a row count consistent with 62 active offers (not 7, not 0).

3. **ad_reporting fan-out count**: verify the `ad_reporting` ECS controller fans out to the correct number of offer holders (consistent with the 62-denominator, not the 7-row collision artifact or a $0 set).

## What SEAM-2 Does NOT Change

- CR-3 GATE-2 / the 7-day soak: orthogonal and unblocked. SEAM-2 is independent of CR-3.
- autom8y-asana (this repo): no production code changes. All SEAM-1 code lives on PR #111 / branch `cr3-dfr/seam1-entity-identity`. SEAM-2 is purely autom8 monolith work.
- The `Project.get_df` and `Section.get_df` arms of CR-3 (autom8 `project/main.py:1643`, `section/main.py:713`): these carry no economics by design. They are not SEAM-2 targets.

## Cross-References

| Artifact | Purpose |
|---|---|
| `.sos/wip/inquisition/HANDOFF-s1-seam1-proven-2026-06-08.md` | SEAM-1 proof handoff (GREEN/RED matrix, operator levers) |
| `.sos/wip/inquisition/HANDOFF-recon-dataframe-resolution-2026-06-08.md:38-48` | Full failure-mode matrix with file:line for both repos |
| `.know/design-constraints.md` GAP-011 / EC-020 | SEAM-2 gap and evolution constraint |
| `.know/scar-tissue.md` SCAR-DFR-001 | Entity-identity defect class record + defensive pattern |
| `.know/telos/dataframe-resolution-coherence.md` | Campaign telos and DEFER manifest |

*SEAM-2 NOT STARTED. Production levers stay the operator. Do not merge SEAM-2 before SEAM-1 is confirmed live.*
