---
type: review
status: accepted
---

# COVERAGE-DISCLOSURE-render — Sprint 4 exit artifact (provenance-to-the-human)

- **Initiative**: provenance-to-the-human (shape sprint-4; PT-04)
- **Ruling of record**: Potnia BR-3 **(a) HONEST-FLOOR SPRINT-4** — the deck's
  batch path never runs the coverage processor (`engine.get_batch` runs no
  post-processors), so deck coverage is NOT-COMPUTED (a different class than
  computed-then-dropped); the truthful deck render is disclosed-unknown; batch
  measurement is the named increment `F5-batch-coverage-measurement`
  (co-arms `F5-coverage-THROW`), watch-registered in autom8y-data
  `.know/defer-watch.md`.
- **Branch/PR**: `prov/s4-coverage-render` → autom8y-asana PR (base `ee382897`)
- **Commits**: render build `edfd9f55` (builder; includes audited client/workflow
  hunks + the three-face formatter render + guard-presence tests) · teeth
  `02e5a46c` (numerical-adversary, rite-disjoint) · this receipt (orchestrator
  compilation — cites, does not re-derive)
- **Emission half**: autom8y-data PR #260 → `4368cbd0` MERGED (define-lite
  `309ecb05` + carry build `f4587bf9` + BR-3 supersession `85f76877`)
- **Self-cap**: MODERATE; the initiative-level attest is eunomia's (sprint-6)

## Coverage-carry trace (sidecar → render)

| Hop | Surface | Anchor |
|---|---|---|
| Sidecar computed (single-office only) | `OfferAttributionCoverageProcessor` | autom8y-data `insights/processors/offer_coverage.py`; wired `insights/library.py:1383/:1490` |
| Typed payload model | `AttributionCoverage` (`from_sidecar_payload` — values verbatim) | autom8y-data `_insights.py:396/:568` |
| Response meta slots | `ResponseMetadata.coverage`/`.coverage_expected` (+ single-office meta) | autom8y-data `api/models.py:168/:190`; projection `:894/:910`; batch hop `batch_insight_executor.py:597/:703` |
| Client fold (H5) | `_coverage_from_meta_block` siblings → `OperatorBatchMeta.coverage/.coverage_expected` (first-observer rule; G1 weights-skew ordering preserved) | asana `clients/data/_endpoints/operator.py` |
| Workflow (H6) | `_fetch_table` passthrough onto `TableResult.coverage/.coverage_expected` — NO throw arm (deck THROW not-yet-armable) | asana `workflow.py` |
| Render (H7) | `_coverage_line_html` via `_section_disclosure_html`; carried at both served `DataSection` sites in `compose_report` | asana `formatter.py` |

## Orphan-spend ceiling render spec (the three ruled faces, OFFER TABLE only)

Scope: `_COVERAGE_DISCLOSED_SECTIONS = {"OFFER TABLE"}` — the disclose-mandate is
scoped to the surface where spend is allocated (autom8y-data `db.md:180-184`);
widening is a define-altitude ruling.

1. **MEASURED** (`status=="measured"` + share): `spend attribution: ≥ 12.3%
   unattributed (orphan ads)` — a DIRECTIONAL IGNORANCE FLOOR on the
   unattributed share (C1: never a point-coverage claim, never a CI-shaped
   interval; the 87.7% complement is never presented as accuracy).
2. **NO_DATA** (or degenerate measured-without-share): `spend attribution: no
   data this window` — never 0%/100%.
3. **NOT MEASURED** (`coverage=None`, both `coverage_expected` states — the deck
   truth today): `spend attribution: not measured` — a VISIBLE token,
   structurally distinct from a silent blank; NO error, NO throw.

## Two-sided render teeth (commit `02e5a46c`, rite-disjoint adversary)

Matrix {arm} × {parent `ee382897` coverage-blind, build `edfd9f55`}:

| Arm | parent | build |
|---|---|---|
| measured floor byte-exact on composed OFFER section | **FAIL (RED-caught: silent blank)** | PASS |
| unknown token visible | **FAIL (RED-caught: silent blank)** | PASS |
| perturbed shares (0.123/0.087/0.141 each only in its own render) | build-only | PASS (value-faithful, not hardcoded) |
| no-cry-wolf (served non-offer renders NO token) | build-only | PASS |
| corrupt-dropped (`expected=True`+`None`) caught-as-disclosed | build-only | PASS (honest-floor PO-COV-3 variant) |
| no_data face, never 0/100 | build-only | PASS |
| interplay: denied table keeps S3 error-box, never a measured floor | build-only | PASS |
| interplay: meta merge first-observer / all-absent honest collapse | build-only | PASS |

PO-COV-1..5 all DISCHARGED against the contract (§6): byte-match `|delta|=0`,
non-vacuity three ways (perturbation / no-cry-wolf / genuine parent RED),
PO-COV-3 via the contract's own §Q3 honest-floor variant, PO-COV-5 at the real
coverage-blind parent (test-only overlay, zero production edits — no
defect-injection). Verdict: **TEETH-PROVEN** (adversary, self-cap MODERATE).

Near-misses filed, not silently passed: **F-SLICE** (the shared S3 test slicer
keys on the first "OFFER TABLE" literal — sidebar nav — and can mis-slice;
worked around with an id-anchored slicer, surfaced for the shared harness) ·
**F-DENIED-COV** (a denied OFFER TABLE's error section carries the not-measured
token — graded truthful-benign under the honest floor, regression-guarded
against a future measured-floor leak onto a refused table).

## PT-04 disposition (per Potnia's BR-3 pre-ruled posture)

1. Coverage survives to the render for the OFFER TABLE insight — **PASS
   (mechanism-proven)**; the deck's arriving value is None = the truthful state.
2. Ceiling visible where spend is allocated — **DEFERRED-NAMED on the deck**
   (`F5-batch-coverage-measurement`; passes literally on the single-office
   armed home). NOT rounded to green.
3. Two-sided fixture — **PASS** (stripped/absent RED-caught at parent + honest-
   floor discrimination + disclosed GREEN; PO-COV matrix above).

**PT-04: PASS-WITH-NAMED-DEFER** at MODERATE self-cap, exactly the verdict
shape Potnia pre-ruled. The eunomia sprint-6 attester re-derives with its OWN
construction; the GATE-B band clause (sprint-5) remains parked and untouched.

## Receipts

- Build: 15/15 new guard-presence + 1450 affected · Teeth: 1460 passed, 9 skipped
- `mypy src/ --strict` clean (561 files, zero net-new) · ruff format/check clean
- CD-path: an asana merge activates NO consumer surface; the deck render flips
  only at the operator-gated deploy (C5/OP-5).
