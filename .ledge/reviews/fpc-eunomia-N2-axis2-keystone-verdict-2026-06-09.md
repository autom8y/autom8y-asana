---
type: review
status: accepted
---
# FPC Axis-2 Keystone — eunomia (verification-auditor) Rite-Disjoint Re-Derivation

**Date**: 2026-06-09
**Critic rite**: eunomia (rite-disjoint from 10x-dev authoring rite — G-CRITIC)
**Agent**: verification-auditor (N2 — the Axis-2 keystone receipt 10x-dev deferred)
**Evidence ceiling**: eunomia-auditor self-assessment caps MODERATE; STRONG attaches
to the design-under-critique via this rite-disjoint re-derivation.
**Source anchor**: receipts re-fired against `origin/main = 50ebfe3381a627df868887ca3cdf9e223e1f9a90`
(working tree at `3bbb9bc8`; all source via `git show origin/main:<path>`).

---

## VERDICT (execution-altitude): BRANCH A — cache-reuse VIABLE. Path-canon ④ heals the 571.

**n with non-null number_value / n sampled = 15/15.** Every sampled null-unit gid
carries a non-null `MRR.number_value` in its self-keyed cached GET-copy. The unit
frame's NULL is a **path-asymmetry materialization drop (FR-2 / AP-1)**, NOT
null-at-source. The cure works on the cache substrate alone — zero new Asana GET.

---

## G-THEATER — coherence invariant re-fired RED (my own re-derivation, not inherited)

DuckDB CLI over my own download (`/tmp/eun_u` unit sections, `/tmp/eun_o` offer
sections, project gids `UNIT=1201081073731555` / `OFFER=1143843662099250`):

```
| total_joined | gun | coherent |
| 2001         | 571 | 0        |
```

mrr census re-fired: `unit.mrr` **0/3021** (100% null), `offer.mrr` **1325/4070**.
RED=571 / coherent=0 reproduced exactly against the PV anchor. The gun fires on a
broken-fixture-RED, never a green-run-alone.

---

## STEP 1 — NULL-UNIT-GIDS sampled (n=15)

Derived by joining unit↔offer on `office_phone` where `offer.mrr NOT NULL AND unit.mrr IS NULL`:

| unit_gid | unit_name | office_phone | unit_mrr (frame) | offer_mrr (join) |
|---|---|---|---:|---:|
| 1199595892774942 | Palmetto Clinics — Integrative Therapy | +18649537836 | NULL | 1185 |
| 1199595892774944 | Palmetto Clinics — Testosterone Therapy | +18649537836 | NULL | 1185 |
| 1199965498890341 | Palmetto Clinics — Weight Loss | +18649537836 | NULL | 1185 |
| 1200087475234528 | First Choice Medical Center — Neuropathy | +13605758897 | NULL | 550 |
| 1200585406043690 | Balanced Body Holistic Healthcare — Neuropathy | +12018805145 | NULL | 600 |
| 1200804835344553 | Hoosier Health Plus — SoftWave Therapy | +17656417700 | NULL | 485 |
| 1200823338038287 | Jenkins Chiropractic — Chiropractic | +14087717207 | NULL | 550 |
| 1200836133305609 | Lake Wylie Back Pain Relief — Chiropractic | +18038316500 | NULL | 550 |
| 1200839804770770 | American Chiropractic Medical Services — Spinal Decompression | +18104200801 | NULL | 570 |
| 1200839805152873 | Thiele Chiropractic — Chiropractic | +18606438003 | NULL | 542 |
| 1200839805319469 | Gonzales Chiropractic — Chiropractic | +12018580444 | NULL | 700 |
| 1200839805433889 | Neural FX - Rancho Cucamonga — Chiropractic | +19093601700 | NULL | 700 |
| 1200839805628474 | Baker Chiropractic & Rehab — Chiropractic | +16605824357 | NULL | 1300 |
| 1200839807912502 | Parrish Chiropractic Center, P.C. — Chiropractic | +16105307700 | NULL | 425 |
| 1200839808122423 | West LA Neuro-Kinesiology — Spinal Decompression | +13104277374 | NULL | 900 |

All 15 confirmed leaf units in project `1201081073731555` (membership-verified), absent from the offer frame.

---

## STEP 2 — CACHE-BODY-STORE located

**Path**: `s3://autom8-s3/asana-cache/tasks/<gid>/task.json`
(bucket = `ASANA_CACHE_S3_BUCKET=autom8-s3` per `.env/defaults:21` @ origin/main — NOT
the empty org-branded `autom8y-s3`, which has an explicit IAM deny).

**This IS the canonical recovery read-point** (G-PROVE @ origin/main):
- `cache/backends/s3.py:271` → `f"{self._config.prefix}/tasks/{key}/{entry_type.value}.json"` → `tasks/<gid>/task.json` is the persisted `EntryType.TASK` GET-copy.
- `cache/backends/memory.py:431` → `:task` versioned keys are the warmer GET-copies stored via `put_batch_async`.
- This is the same store the spike's recovery mechanism reuses
  (`warm_cache.get_versioned`, `hierarchy_warmer.py:186`) — NOT an orphan store.
- The `tasks/<gid>/` directory's other files (`stories.json`, `subtasks.json`, etc.)
  are sub-resources; **`task.json` is the cf-bearing body** (69 custom_fields confirmed).
- `task-data-cache-v3/` and `task-cache/` were probed but the cf-body lives in `tasks/<gid>/task.json`.

---

## STEP 3 — Per-gid number_value / display_value receipts (pasted)

All 15 bodies present in cache (no leaf-unit GET-copy missing — directly refutes
Branch B's "no self-keyed GET copy exists for leaf units"):

```
unit_gid          gid_match  in_unit_proj  mrr.number_value   display_value
1199595892774942  True       True          1185               1185
1199595892774944  True       True          1185               1185
1199965498890341  True       True          1185               1185
1200087475234528  True       True          550                550
1200585406043690  True       True          550                550      <- DIVERGES from offer 600
1200804835344553  True       True          485                485
1200823338038287  True       True          550                550
1200836133305609  True       True          550                550
1200839804770770  True       True          570                570
1200839805152873  True       True          542                542
1200839805319469  True       True          700                700
1200839805433889  True       True          550                550      <- DIVERGES from offer 700
1200839805628474  True       True          1300               1300
1200839807912502  True       True          425                425
1200839808122423  True       True          900                900
SAMPLED n=15 | non-null number_value: 15 | null: 0 | no MRR field: 0
```

Sample cf shape (divergent gid `1200839805433889`):
`{'name':'MRR','resource_subtype':'number','number_value':550,'display_value':'550','text_value':None}`

**Offer-bleed REFUTED (G-CRITIC rigor)**: 2/15 unit body MRR values DIVERGE from the
offer join value (`1200585406043690` unit=550 vs offer=600; `1200839805433889` unit=550
vs offer=700). If the unit body were contaminated by the offer sibling's value or by a
section-aggregate, all 15 would match. The divergence proves each body holds the unit's
**own** MRR custom field.

**Extraction-primitive match (G-PROVE @ origin/main)**: `cf_utils.py:49-50`
`case "number": return cf_data.get("number_value")`. The sampled bodies have
`resource_subtype:"number"` + `number_value` populated → `extract_cf_value` returns
1185/550/… The recovery read of these cached bodies heals the cell deterministically.

---

## STEP 4 — VERDICT: Branch A (cache-reuse VIABLE), 15/15

- The GET-copy carries non-null `number_value` for **every** sampled null-frame row.
- Path-canon ④ (recovery reading `tasks/<gid>/task.json` via `get_versioned`) heals them.
- The cure is field-agnostic and **zero-new-GET** on the warm path — CR-3-safe at the
  mechanism altitude (single-uvicorn-worker / SlowAPI ceiling untouched), provided the
  implementation holds the spike's line: a cache miss degrades to honest null, never an N+1 GET.
- The cured magnitude on this sample = 15/15 → the 571 is expected to fall substantially
  toward `coherent>0` (NFR-2) on operator re-warm. RUNG held: **mechanism + substrate
  proven from cache**; live-magnitude is operator-gated (Step 5).

**This resolves the keystone CONDITION (1) Axis-2 cache-population** that 10x-dev deferred
(spike sentinel `test_LIVE_get_copy_actually_carries_number_value_for_571_phones` was
SKIPPED). The cache substrate answers it: the value is **path-stripped, present on GET,
dropped on the list/frame path** — exactly the FR-2 path-asymmetry the FPC design targets.

---

## STEP 5 — RESIDUAL bounded (what the cache CANNOT answer — operator ASANA_PAT lever)

The cache substrate proves the **cached GET-copy** carries `number_value`. It does NOT,
and cannot, prove:

1. **LIVE-source parity**: whether the *current live Asana source* (not the cached copy,
   which for `1199595892774942` reflects `modified_at: 2026-03-29`, file cached `2026-04-30`)
   still carries the same `number_value`. If a unit's MRR was *later cleared* in Asana,
   the cache is stale-positive and a live re-warm would correctly yield honest null for
   that row. ASANA_PAT is UNSET — this needs a live `get_async(gid, opt_fields=BASE_OPT_FIELDS)`.
   **Bound: sampling shows the cache is positive; the cache→live delta is the only
   remaining unknown, and it can only REDUCE the cure magnitude, never invert the Branch.**

2. **Full-571 generalization**: I sampled 15 of 571. The 15/15 hit-rate is a strong
   signal but not a census. An operator re-warm + re-run of the §2 DuckDB 571 canary on
   live S3 parquet (spike sentinel `test_LIVE_571_gun_falls_after_rewarm`, SKIPPED) is
   the only way to read the exact `coherent` lift. **Bound: Branch A holds for the
   sampled population; the magnitude across all 571 is operator-re-warm-gated.**

3. **FM-A (Asana non-determinism)** remains a MITIGATION not a GUARANTEE: same-task +
   same-opt_fields determinism between the cached GET copy and the list frame is assumed;
   temporal server drift is out of scope of any cache read.

---

## Disposition of the 4 conditions (rite-disjoint)

- **(1) Axis-2 cache-population [keystone]** — **RESOLVED → Branch A.** 15/15 cached
  GET-copies carry non-null `number_value`; store is the canonical recovery read-point.
  Residual = live-source parity + full-571 census (operator ASANA_PAT/re-warm only).
- **(2) Axis-1 FieldContract `(value_type,provenance)` key** — NOT in this dispatch's
  scope; the cache evidence does not bear on the enum-source/numeric-schema
  representational gap for `unit.discount`. Carry forward to the design critique.
- **(3) offer_id Utf8↔Int64 cross-frame** — NOT closed by this evidence; per-(entity,name)
  contract does not span the cross-frame dtype. Carry forward.
- **(4) Axis-4 parity-RED asserted-only (no generator)** — NOT addressed here; the parity
  generator does not yet exist. The coherence-RED half (571) IS re-fired and honest; the
  parity-RED half remains generator-gated (honest downgrade, not theater).

**G-RUNG**: Tops out at "Axis-2 keystone RESOLVED (Branch A) from cache substrate +
coherence-RED re-fired." NOT rounded to "FPC live / verified-realized." Live population
(coherent off 0) is operator-gated and unproven here.

---

## Product-Altitude ADVISORY (telos-integrity, non-blocking, `-ADVISORY` suffix load-bearing)

**FLAG-ADVISORY** — `.know/telos/dataframe-resolution-coherence.md` exists, but the FPC
shipped_definition's healing claim ("path-canon ④ heals the 571") is now backed by a
per-item file:line receipt for the *mechanism + cache substrate* (this artifact), while the
*verified_realized* user-visible outcome (coherent>0 on live S3) carries a deferred receipt
gated on the operator ASANA_PAT re-warm probe. This is the correct posture: surface to the
/go inception-gap panel + close-comment; does NOT halt any rite-transition (Authority
Contract clause 2). User adjudicates the operator probe per OQ-1.
