---
type: handoff
artifact_id: HANDOFF-data-analyst-to-owner-asana-windowed-mrr-2026-07-04
schema_version: "1.0"
source_rite: data-analyst (asana-windowed-mrr-mile; session 2026-07-04)
target_rite: owner/eunomia (attestation validation before eunomia handoff)
handoff_type: verdict-transfer
priority: high
blocking: false
status: proposed
emitted_at: "2026-07-04T~11:00Z"
expires_after: "60d"
initiative_source: lamp-first value mile leg 1 of 2 (ENGAGE-asana-windowed-mrr-mile)
initiative_target: owner decision — DEFER-register enriched-frame capture vs accept unservability
evidence_grade: MODERATE
evidence_grade_rationale: |
  Self-referential fleet attestation of a guard's teeth caps at MODERATE per
  self-ref-evidence-grade-rule; STRONG requires the rite-disjoint eunomia leg.
  Within the cap: 3-lens unanimous adversarial refutation panel (high
  confidence each), two-sided discriminating canary with real RED/GREEN run
  receipts, independent disjoint re-derivation (grain-integrity-engineer)
  matching the authored golden exactly, zero material discrepancies.
---

# HANDOFF — Asana Windowed active_mrr (data-analyst → owner/eunomia)

## Verdict: PUNCH-LIST (no number servable; forcing one would be fabrication)

**No windowed active_mrr number is emitted.** The ZERO-BUILD dated offline
substrate is dimensionally incapable of producing one: the `mrr` summand and
the `section` ACTIVE-classifier — both load-bearing inputs to `active_mrr` —
exist in **0 of 352** offline parquet files (broad rescan: 0 of 672 across all
`/repos`). The charge explicitly blesses this outcome ("punch-list it — do NOT
force a number", ENGAGE charge §Rails). Never round: this mile's honest rung is
**authored + refusal-PROVEN**, not "number produced".

## 1. The ruled definition (DEFINE — model-provenance-author)

- **Interpretation ruled: interp-B (as-of).** `active_mrr` = sum of `mrr`
  (cast Float64, filtered `mrr IS NOT NULL AND mrr > 0`) over offers whose
  Asana board `section` (lowercased) ∈ `OFFER_CLASSIFIER.sections_for("active")`,
  deduplicated `unique(subset=["office_phone","vertical"], keep="first")`,
  computed as-of the latest offline snapshot inside the demand week 6/21–6/27.
- Authoritative definition: `src/autom8_asana/metrics/definitions/offer.py:20-43`.
- Computation path: `src/autom8_asana/metrics/compute.py:66-129`
  (classification `:67-79` — hard-raises `ValueError` if `section` absent;
  dedup `:114-116`).
- ACTIVE membership: `src/autom8_asana/models/business/activity.py:181-208`
  (`OFFER_CLASSIFIER`, project_gid `1143843662099250`).
- Denominator ruling: ACTIVE population = section-set membership as-of the
  snapshot, then collapsed to one row per `(office_phone, vertical)` Unit-PVP.
  The population is **unmaterializable offline** — the column that defines
  membership does not exist in the substrate.
- No temporal selector exists on the live CLI (only `--strict` /
  `--staleness-threshold` / `--sla-profile`): `src/autom8_asana/metrics/__main__.py:568-629`
  — confirming "for a week" is a definition question, not a flag.

## 2. Premise refinements vs the charge (path-shift class — caught live)

| Charge premise | Live finding |
|---|---|
| "6/27 as-of read IS directly servable (6/27 ∈ set)" | **REFUTED.** Dated dirs: 6/24 (×6), 6/25 (×3), 6/29 (×1). No 6/26/6/27/6/28. Latest in-week snapshot = `20260625_105550`, manifest `created_at` **2026-06-25T10:55:50.459814+00:00** |
| "dated offline offer parquet" serves active_mrr | **REFUTED.** Substrate is raw MySQL: `offers.parquet` (7 cols: guid, offer_id, name, name_60_char, description, cost, category), `business_offers.parquet` (22 cols; `office_phone` present, **no mrr/vertical/section**). `mrr`/`office_phone`/`vertical` are Asana task cascade fields (`src/autom8_asana/dataframes/extractors/offer.py:21-26`), never exported to MySQL |
| DEFER-4: inspect `analyst.duckdb` for earlier days | **CLOSED-EMPTY.** `analyst.duckdb` contains 0 tables (introspected read-only via duckdb) |
| Anchor basenames (`offer.py:20-43` etc.) | **CONFIRMED at refined subpaths** (all five anchors re-verified verbatim; see §1) |

## 3. Adversarial refutation panel (3 disjoint lenses — unanimous, high confidence)

Claim under test: *"windowed active_mrr CANNOT be trustworthily served from the
substrate."* Each lens tried to **refute** it; all returned `refuted=false`:

- **join-reconstruction** (grain-integrity-engineer): no equivalence-provable
  reconstruction. `vertical` recoverable only via fan-out (873/1023
  office_phones → >1 vertical, max 34) — structurally rejected per G1.
  `account_status` (the only table with the right shape:
  office_phone+vertical+pipeline_section) is **0 rows in all 11 snapshots**.
- **schema-exhaustive-proxy** (numerical-adversary): all 32 tables of the
  snapshot roster checked; **9 proxies enumerated and rejected** as untraced
  fabrications (e.g. `pipeline_section` = CRM taxonomy ≠ Asana board sections;
  `payments.amount` = Stripe charges ≠ Unit-level MRR; `offers.cost` =
  one-time cost ≠ MRR; `disabled` = binary flag ≠ 20-member section set).
- **date-coverage-artifact** (model-provenance-author): the enriched
  S3-mirror layout (`dataframes/{project_gid}/{entity_type}/sections/*.parquet`,
  `src/autom8_asana/dataframes/storage.py:326,332`) is a real code path but has
  **zero local dated capture**; 672-parquet broad scan: 0 carry mrr/section.

Total: **21 proxy paths considered and rejected** as untraced. Zero traced
alternatives found.

## 4. Two-sided fixture (VERIFY — the discriminating canary, teeth proven)

Fixture: `tests/unit/metrics/test_windowed_active_mrr_canary.py` (new test
file; **zero edits under `src/`** — the guard graded is pre-existing production
code, lineage-disjoint from the fixture author; critic-never-author upheld).

**GREEN** — 8/8 tests pass; golden synthetic enriched frame through the REAL
`compute_metric(ACTIVE_MRR, df)` = **4250.0** over exactly 3 deduped unit rows,
with post-dedup cardinality AND grain-key identity asserted (not just the sum).
No regression: `tests/unit/metrics/` **429 passed**.

```
........                                                                 [100%]
8 passed in 0.31s
```

**RED-1 (dedup-dropped — the Query-Engine trap):** fixture-local
`_broken_sum_no_dedup` inflates to **6000.0 (+1750.0)**; canary bites:

```
AssertionError: CANARY BIT: dedup-dropped sum 6000.0 != ruled 4250.0 (inflated by 1750.0)
PROBE_EXIT=1
```

**RED-2 (substrate refusal — the punch-list teeth):** feeding the REAL
`20260625_105550/business_offers.parquet` (shape 1315×22) to `compute_metric`
hard-raises at `src/autom8_asana/metrics/compute.py:69`:

```
ValueError: Classification filter requires 'section' column, but DataFrame has
columns: ['id', 'guid', 'office_phone', 'ad_spend', ...]
PROBE_EXIT=1
```

Today's substrate is **REFUSED, not silently mis-summed** (typed,
non-null-coercible — G4 already enforced in production).

**RED-3 (wrong-window):** the out-of-week snapshot `20260629_143620`
(created_at 2026-06-29) is rejected by the as-of validator:

```
ValueError: as-of snapshot 2026-06-29T14:36:20.214213+00:00 (date 2026-06-29)
is OUT-OF-WINDOW for demand week 2026-06-21..2026-06-27
PROBE_EXIT=1
```

**Non-vacuity (two-sided):** on a no-sibling frame the broken variant EQUALS
the real path (4250.0 == 4250.0) — the discriminator bites ONLY on the defect.
The in-week 6/25 manifest GREENs the window validator. No defect injected into
working code.

**Independent disjoint re-derivation** (grain-integrity-engineer): golden
re-derived row-by-row = **4250.0, exact match**; canary re-run 8 passed /
0 skipped (RED arms genuinely armed); red probe re-run still bites; G1
cardinality + `keep="first"` order-invariance verified (sibling mrr equal —
Unit-level semantics). Discrepancies: **none material**. One portability note:
RED-2/RED-3 skipif-gate on sibling-repo presence (they ran armed here; on a
host without `autom8y-data` they skip and the 3 fixture-local tests remain the
floor).

Note: the golden 4250.0 is a **synthetic contract-pin**, not a production
number — it pins the definition + dedup shape so the moment the substrate DOES
carry the enriched frame, the windowed read is already contract-guarded.

## 5. Coverage disposition (honest — DoD item 5)

- Demand week 6/21–6/27: even if the columns existed, in-week snapshots cover
  only **6/24 and 6/25** (2 of 7 days). 6/21–6/23 absent (charge's
  orphan-backup 6/23 not present in the clean set); 6/26–6/27 absent
  (refutes the charge's assumed 6/27).
- Honest as-of anchor if served: **2026-06-25T10:55:50Z** (`20260625_105550`
  manifest `created_at`), NOT end-of-week.
- Owner truncation ruling: **moot for this mile** (no number servable at any
  in-week date); recorded for the successor mile.

## 6. Actionability (DoD item 6 — the decision this punch-list feeds)

The owner decides THIS WEEK, on this punch-list:

1. **DEFER-5 (proposed):** register "capture the enriched section-partitioned
   offer frame (`office_phone`, `vertical`, `mrr`, `section`) into the dated
   offline export" — the S3 sections mirror already exists as a code path
   (`storage.py:326-332`); the gap is dated *retention* of it. Refutable
   trigger: refuted if the owner rules windowed active_mrr not worth a
   capture-build, or if another arc lands dated retention of the sections
   mirror first. Per the freeze: this is a DEFER registration, **not** a
   build-in-sitting.
2. Or **accept unservability**: windowed/as-of active_mrr remains structurally
   impossible offline; the live CLI remains latest-only.

Without one of these dispositions the punch-list is a demo; with it, it is the
receipt.

## 7. Freeze compliance (DoD item 7)

Zero violations: no MotherDuck touched, no S3 retention built, no
`--force-warm`, no new production flag, no `src/` edits. Artifacts created:
1 new test file + this HANDOFF + session-scratch receipt files
(`scratchpad/receipts/{green,red-dedup,red-substrate,red-window,full-metrics}.txt`
+ 3 probe scripts; verbatim tails inlined above — the fixture itself is the
durable, re-runnable receipt).

## 8. Equivalence obligation (G6 — stated OPEN, not asserted)

Any future produced number MUST be proven equal (reconciliation byte-match of
the deduped frame, or |Δsum| < declared tolerance) to the live `active_mrr`
over the enriched frame of the SAME snapshot. Presently **unsatisfiable
offline** (the referent frame cannot be reconstructed — §3). The obligation is
the gate the DEFER-5 capture path must clear; it is not rounded away.
