---
type: review
artifact_type: QA-GATE
status: accepted
verdict: GO
initiative: substrate-v2-epoch
wave: S8-2
pr: 347
date: 2026-08-12
reviewer: qa-adversary (P7 adversarial gate, floor-bridge DELTA)
reviewed_sha: bc1fbbd2 (branch fix/s8-2-floor-bridge, 3 commits off main 7f81e515; spike digest consumed from origin/main 538d2486)
scope: tiered population floor bridge per SPIKE-population-floor-scope-2026-08-12 ratification digest items 1/2/3/4
binding_spike: .ledge/spikes/SPIKE-population-floor-scope-2026-08-12.md
---

# QA-GATE — PR #347 S8-2 tiered population-floor bridge (P7 adversarial review)

**VERDICT: GO** — zero CRITICAL/HIGH/MEDIUM findings. All three live mutations bite
(own hands), both full suites green own-hands (385 substrate+harness, 1484 dataframes),
all CI gates clean, all five frozen surfaces byte-equal vs origin/main by direct
extraction-diff (not the builder's tests), and the load-bearing dedup-collapse premise is
**independently EMPIRICALLY CONFIRMED** on a real production frame through the actual
compute path. 2 LOW + 4 INFO findings carried; 1 obligation carried (not a gap).
**Self-assessment caps MODERATE** per self-ref-evidence-grade-rule; rite-disjoint
corroboration arrives at PT-03.

Env note: `uv sync --extra dev` 401'd on CodeArtifact (as forecast); all runs used the
main-tree venv with `PYTHONPATH=<worktree>/src:<worktree>`; import resolution verified to
point at THIS worktree for `autom8_asana`, `substrate.population_floor`, and
`substrate.rebuild` before any suite ran. polars 1.38.1.

## 1. Standard duties

| Duty | Status | Receipt |
|---|---|---|
| Full suites own-hands | GREEN | 385 passed (tests/unit/substrate + tests/harness, 129.9s); 1484 passed + 2 skipped + 2 xfailed (tests/unit/dataframes, 59.0s — suite untouched by this diff; skips/xfails are suite-internal marks, not PR regressions) |
| ruff format --check | CLEAN | 1428 files already formatted |
| ruff check + RUF100 | CLEAN | `ruff check src/ --extend-select RUF100` → All checks passed; repo-wide `ruff check .` → All checks passed |
| mypy --strict | CLEAN | Success: no issues found in 584 source files |
| Mutation 1 (blocking→warning demotion: `office_phone` moved to warn tier) | **RED as required** | 4 tests failed incl. `test_null_dedup_key_on_active_row_refuses[office_phone]`, `test_null_dedup_key_would_silently_collapse_the_served_sum[office_phone]`, `test_offer_floor_is_decoupled_from_the_digest_set`, `test_warning_payload_carries_no_cell_values` |
| Mutation 2 (warning emission removed at rebuild.py floor evaluation) | **RED as required** | 7 tests failed across test_population_floor.py (4) + test_live.py (3, incl. `test_3c_provisioning_lag_null_serves_and_surfaces_per_offer`) |
| Mutation 3 (dense-zero killed: emit only when warnings non-empty) | **RED as required** | 1 test failed: `test_demoted_null_on_inactive_row_produces_no_warning` (asserts `emitter.calls == [(0, _DAY)]`). Narrow but biting — carried as F-6 INFO |
| Restore clean | VERIFIED | `git diff` on src/tests/terraform empty vs PR head after each restore; final suite state = the green runs above |

## 2. Frozen-surface diff (against origin/main, by extraction, not builder tests)

| Surface | Result |
|---|---|
| `src/autom8_asana/substrate/__init__.py` | BYTE-EQUAL (empty diff vs origin/main) |
| `AcceptancePredicates` Protocol (rebuild.py:317) | BYTE-EQUAL (532-byte class body extracted from both trees, identical) |
| `RebuildOutcome` | BYTE-EQUAL (941 bytes) |
| `canonical_digest` | BYTE-EQUAL (3152 bytes) |
| `_VALUE_COLUMNS` assignment | BYTE-EQUAL (`("cost", "mrr", "offer_id", "weekly_ad_spend")`, freshness.py:163) |
| `_DIGEST_SCHEME` | BYTE-EQUAL (`"sv2-canonical-digest-1"`, freshness.py:167) |

freshness.py's only delta is a 9-line COMMENT above `_VALUE_COLUMNS` (the "NOT THE
POPULATION FLOOR" pointer) — no executable or constant bytes changed. Seam-use claim
holds: `floor`/`warning_sink` are new fields on `DefaultAcceptancePredicates` (the
concrete implementation), the Protocol surface is untouched. `population_floor` imports
nothing from `freshness` (copy-by-value decoupling), and `_value_columns_with_nulls`
(the digest-set reader) is retired from rebuild.py.

## 3. The six flagged targets — rulings

### T1 — Absent-column semantics: PASS (flip exists but is unreachable on-schema; direction is fail-closed)

Absent blocking column == null-equivalent (population_floor.py:118-131). The genuine
behavior flip: a frame with all four old `_VALUE_COLUMNS` clean but NO `office_phone`
column previously PASSED the floor (old offenders: `[]`) and now REFUSES (new offenders:
`['office_phone']`) — reproduced live. Probed reachability across every publish path:

- The SOLE production `DefaultAcceptancePredicates` construction is live.py:827
  (`rebuild_offer_v2`); no other src/ call site exists (grep-verified).
- Rows branch: `safe_dataframe_construct(rows, OFFER_SCHEMA)` (live.py:724) materializes
  the FULL schema — a row dict missing the `office_phone`/`vertical` KEYS entirely still
  yields present columns with nulls (probed live).
- Typed-empty branch: `pl.DataFrame(schema=OFFER_SCHEMA.to_polars_schema())` materializes
  all schema columns at 0 rows (probed live); a 0-active frame refuses at `min_rows`
  BEFORE the column check — the pre-bridge refusal, no new class.
- `active_offer_rows` filters rows, never columns; OFFER_SCHEMA carries
  `office_phone` + `vertical` (schemas/offer.py:19/28).

And on the unreachable off-schema frame the flip direction is strictly safer: pre-bridge
that frame would have SWAPPED (old floor blind to `office_phone`, digest doesn't read it)
and then raised `ActiveMrrColumnMissing` at leg computation — a corrupt publish over a
healthy artifact. Post-bridge it refuses PRE-swap. Ruled: claim covers every publish path.

### T2 — Dedup-collapse guard premise: EMPIRICALLY CONFIRMED (independent, own construction)

The new refusal class rests on "polars `unique(subset, keep='first')` treats nulls as
equal." Probed independently on polars 1.38.1, twice:

1. **Raw premise**: 4-row frame, two DISTINCT offers with null `office_phone` + same
   `vertical` → `unique(subset=["office_phone","vertical"], keep="first")` returns 2 rows
   with exactly ONE null-key row surviving; sum 430.0 → 140.0. Nulls DO collapse.
2. **Real frame, actual compute path**: real production offer frame (4192×33, 67
   classifier-active rows, baseline `served_active_mrr` = 78285.0 / 59 deduped rows —
   consistent with the live LEG A number). Nulled `office_phone` on 2 DISTINCT active
   chiropractic offers (mrr 3500.0 + 1500.0) → `served_active_mrr` (the REAL
   `compute_metric` path, metrics/compute.py:116 dedup) returned 74785.0 / 58 rows:
   **one distinct offer silently vanished and the served number lost $3,500 with no
   error**. `OFFER_PUBLISH_FLOOR.blocking_columns_with_nulls` on that exact wounded
   frame → `{'office_phone'}` → REFUSES.

The spike's load-bearing fact #3 and the blocking-tier rationale hold. The wu1-era
2-column fixture parquet (`offer_plane_section_mrr.parquet`, 4191×2) is a LEG-B
section-composition shape and cannot exercise this — the forensics full-frame capture was
used instead. Also proven: one floor evaluation per touch maximum (`validate` runs once
at rebuild.py:589; the CAS retry loop in `_publish` never re-validates), so a warning can
never be double-counted per touch.

### T3 — Emission density / PROV-7 alarm semantics: PASS (no spurious flap, no silent miss within authored semantics)

Enumerated emission per touch outcome:

| Touch outcome | Emits? | Alarm effect |
|---|---|---|
| Clean publish | 0.0 | Maximum=0, not >0 → OK (dense-zero return-to-OK) |
| Floor-refused (blocking null) | count (pre-verdict, rebuild.py:397-400) | wound still counted — a blocking failure never masks the warn tier (mutation-2 test `test_warning_fires_even_when_a_blocking_column_refuses`) |
| Pre-validate refusal (budget/coverage/fetch/C16) | nothing | missing data → `treat_missing_data=notBreaching` → no false state; evaluator absence is PROV-2's job (as the tf comment states) |
| Wounded publish | count>0 | Maximum>0 in that 900s period → ALARM, 1-of-1 |

Flap: 0.0 datapoints cannot breach `GreaterThanThreshold 0`; a wounded evaluation
tickets, then the alarm auto-returns to OK on subsequent missing/zero periods and a NEW
wound re-tickets — per-wound ticketing, which is the deliberate threshold-0 design, not a
flap. Miss: every EVALUATED wound lands a >0 Maximum in its period (statistic Maximum is
correct for mixed 0/N periods). tf↔emitter identity verified two ways: the F-1 binding
tripwire (`test_terraform_alarms_bind_to_emitted_metric_identities`, run green own-hands)
now asserts 7 alarms, unions BOTH emitters, and string-pins namespace
(`Autom8y/SubstrateProvability` == var default), metric name, and the `{environment}`
dim-set; plus direct code-read of `build_metric_data` vs the alarm resource. Alarm is
AUTHORED-not-applied (DP-4a door), paging unarmed — matches digest item 2.

Two seams carried (below): the best-effort CW put swallow (F-1 LOW) and the inherited
period variable (F-2 LOW).

### T4 — data_quality_warnings tri-state: PASS at all six write sites

The tri-state is decided by ONE object (`DataQualityWarningCollector.fired`), not
per-site hand-wiring — `null` = floor never evaluated, `[]` = evaluated clean,
populated = evaluated wounded. Probed live: never-ran → `blocks() is None`; ran-clean →
`[]`; refused-with-warnings (blocking `mrr` null + warn `offer_id` null on the same row)
→ `ValidationFailure` AND `[{gid, section, null_cols:['offer_id']}]`. Site enumeration:

| Write site | warnings arg | Result |
|---|---|---|
| `write_budget_halt` (live.py:1043) | not passed → `_base` default None | `null` — budget halts are always pre-floor (HTTP boundary). Honest |
| `write_refusal` refused-coverage (`ActiveMrrRefused`, raised in fetch) | `dq.blocks()` | fired=False → `null` deliberately ✓ |
| `write_error` (first generic except) | `dq.blocks()` | `null` pre-floor / honest post-floor |
| `write_refusal` refused-{outcome} (non-SWAPPED) | `dq.blocks()` | STAGED_REJECTED → populated/`[]`; FETCH_REFUSED → `null`. Honest both ways |
| `write_error` (v2 materialization) | `dq.blocks()` | floor ran → `[]`/populated |
| `write_served` | `dq.blocks()` | `[]`/populated |

`_base` writes the key unconditionally (live.py:947), so the field is never absent — a
reader can rely on the tri-state. parity_run.py:412-414 carries it onto the one-screen
summary for the daily digest (digest item 2's per-offer named lines).

### T5 — PII: PASS (no cell VALUE reaches reason/detail/receipt; adversarial attempts failed)

`office_phone` values are PII (the codebase's own `_composition_digest` discipline,
live.py §6 #8). Attack attempts, all live:

- Frame with `office_phone = "+1 (555) 867-5309"` and a blocking `mrr` null →
  `ValidationFailure.reason` = `"null value column(s) ['mrr'] on active rows"` — column
  NAMES only; the receipt `detail` shape (rebuild.py:592
  `f"validation failed [{check}]: {reason}"`) carries no cell value; the warning wire
  form carries no cell value.
- Phone-shaped GID cell (`gid="555-867-5309"`): the gid IS carried — by design, per the
  parity receipt contract (gid + section + column names are the permitted identifiers);
  `null_cols` carried only `["cost","offer_id"]` — names, never values.
- Misconfigured custom floor with `office_phone` in the WARNING tier: the per-row block
  still carries only the column NAME (`null_cols:["office_phone"]`), never the value —
  the module docstring's "office_phone can never appear in null_columns" holds for
  OFFER_PUBLISH_FLOOR specifically, and even the violated variant leaks no value.
- Tier-integrity guards bite: empty blocking tier → ValueError; overlapping tiers →
  ValueError (both probed live).
- The PROV-7 metric is `{environment}`-dimensioned only — no per-offer dimension
  (unbounded-cardinality guard, observe.py comment) — verified in `build_metric_data`.

### T6 — Mixed-floor PT-03 ledger note: OUT OF PR SCOPE, carried as an obligation

The PR diff touches exactly 10 files: 6 src/, 3 tests/, 1 terraform/ — **zero**
`.ledge/`/`.sos/` writes (diff-stat verified). Digest item 3 ("now, mid-window, + PT-03
ledger note — mixed-floor cycles disclosed; cycle 1 served under the strict floor") is
therefore NOT discharged by this PR and is NOT a PR gap: it is a **carried obligation**
on the operator/potnia at PT-03 evidence-close — the PT-03 Q1 ledger must record that
window cycles before this bridge ran under the strict economic floor and cycles after it
run under the tiered floor. Flagging here so the obligation survives the gate.

## 4. Findings (severity | repro | disposition)

- **F-1 LOW — best-effort CW put swallow is the one miss seam.**
  `CloudWatchDataQualityEmitter.emit_active_row_economic_nulls` swallows every put
  exception (observe.py, BLE001-waived): a wounded publish proceeds with a warning log
  but NO PROV-7 datapoint if CloudWatch rejects the put. Deliberate per docstring ("a
  data-quality emit must not fail a publish the floor accepted") and mitigated — the
  receipt channel (`data_quality_warnings`) is fed by the collector BEFORE the emitter
  and never degrades, and the `substrate_data_quality_emit_failed` log is loud. Carry;
  no action required for the bridge.
- **F-2 LOW — PROV-7 period inherits `var.evaluation_schedule_seconds` (900s), a
  variable documented as the SCHEDULED sweep cadence (PROV-1/3/4).** PROV-7's emission
  is EVENT-driven (publish-time), not scheduled; retuning the sweep cadence would
  silently retune PROV-7's alarm window too. Behavior today is correct
  (notBreaching absorbs sparsity). Suggest a dedicated period var or a comment at the
  variable when the locus adjudication lands. Carry.
- **F-3 INFO — off-schema absent-blocking-column flip (T1)**: serve→refuse flip exists
  only on frames not constructible via the sole production path; direction fail-closed
  and strictly better than main's swap-then-error. No action.
- **F-4 INFO — misconfigured floor naming `gid`/`section` as a warning column** would
  produce a duplicate-column select inside `null_warnings` → exception → error receipt
  (fail-loud, not silent; F-305-3 leaves a receipt). Unreachable with the two shipped
  floors. No action.
- **F-5 INFO — per-wound re-ticketing lifecycle (T3)**: ALARM→auto-OK (~1 period via
  notBreaching)→re-ALARM on the next wound. This matches the threshold-0 "ANY wounded
  row tickets" ratification intent; noting it so nobody later reads the auto-OK as
  "wound cured." No action.
- **F-6 INFO — mutation-3 (dense-zero) is caught by exactly ONE assertion**
  (`test_demoted_null_on_inactive_row_produces_no_warning`, the `emitter.calls == [(0,
  _DAY)]` line). It bites, but the dense-zero discipline hangs on a single test whose
  NAME is about inactive-row scoping. A dedicated clean-case-emits test would make the
  intent legible. Nice-to-have; not blocking.
- **OBLIGATION (carried, not a finding) — PT-03 mixed-floor ledger note** per T6.

## 5. Acid test

A production failure mode not tested here that would surprise me: none found. The three
incident-class inputs (provisioning-lag `offer_id` null → serves + warns + tickets;
null dedup key → refuses; degenerate/empty → refuses) are each proven with teeth, both
sides, on real frame shapes.

**GO.**
