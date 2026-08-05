---
type: review
artifact_type: QA-GATE
status: accepted
verdict: GO
initiative: substrate-v2-epoch
wave: S8-2
session: session-20260803-220334-f2a75514
pr: 301
pr_addendum: 303  # second gate section appended same-file (warm seat): exemplar #2 leg-2 re-pin
pr_addendum_2: 305  # third gate section (warm seat): WU-3 arm-parity-window — NO-GO
date: 2026-08-03
reviewer: qa-adversary (P7 adversarial gate, WU-2)
reviewed_sha: b9e0d4d5 (branch fix/s8-2-budget-ledger-hardening, off main 5d62d0b8)
scope: tests/harness/substrate_gate/budget.py + test_budget.py ONLY (zero src/ changes — verified by diff stat)
---

# QA-GATE — PR #301 S8-2 budget-ledger hardening (WU-2, P7 adversarial review)

**VERDICT: GO** — all three closes discriminably bite (proven by live mutation, own hands),
the cross-process lock holds under harder-than-test contention, no HIGH/CRITICAL findings.
1 MEDIUM + 2 LOW findings are carried with explicit WU-3 conditions (below); 5 INFO notes
ledgered. **Self-assessment caps MODERATE** (P7 line — this gate's own attestation cannot
exceed MODERATE per self-ref-evidence-grade-rule; rite-disjoint corroboration arrives at
PT-03/WU-5).

Ruling consumed: RULING-potnia-s8-2-wave-entry-2026-08-03.md §2 WU-2 exit bar + §3 G3
(harden the meter BEFORE energizing the line). Counsel consumed: pythia §5 attempt-semantics
(RECEIPT-s8-0-fixture-recapture-2026-07-30.md, docs/s8-2-wave-entry-rulings).

## 1. Exit-bar conformance (WU-2 ruling §2)

| Bar | Status | Receipt |
|---|---|---|
| Corrupt-JSON fail-loud | CLOSED | `BudgetLedgerCorrupt` at budget.py:69-82; `_load` budget.py:125-148; FileNotFoundError stays legitimate-empty (budget.py:128-129); mutation-1 RED |
| Cross-process flock lock | CLOSED | blocking `LOCK_EX` budget.py:170-189, load-check-write ALL inside the lock budget.py:210-225 (no TOCTOU); mutation-2 RED; harder-race PASS |
| Multi-unit overshoot | CLOSED | pre-charge `current + units > cap`, no partial charge, budget.py:215-222; mutation-3 RED |
| Ledger path PINNED | DONE | `PINNED_LEDGER_PATH` budget.py:93, P13-amendable, repo-relative/durable, pinned by test_budget.py:254-262 |
| Cap NOT hardcoded | VERIFIED | constructor-injected (budget.py:109); grep for 11200/5600 → only the "deliberately NOT hardcoded" comment budget.py:92 |
| Discriminating tests green | VERIFIED | 295/295 own-run at b9e0d4d5 (twice: pre- and post-mutation restore, 52.9s/15.4s) + ruff check/format clean on both files |

## 2. Mutation-probe table (S8-0 precedent style — discrimination by live mutation, own hands)

| Close | Mutation applied | RED test(s) | Rest | Restored |
|---|---|---|---|---|
| 1 corrupt-refuse | pre-PR fail-open `_load` restored (`except (FileNotFoundError, JSONDecodeError): return {}` + non-dict→`{}` + bare `int()` coercion) | exactly 3: `test_corrupt_json_refuses_loudly_not_silent_reset`, `test_valid_json_but_non_dict_refuses_loudly`, `test_non_integer_day_count_refuses_loudly` | 17 GREEN | `git checkout b9e0d4d5 --` clean; suite 295/295 |
| 2 flock | lock acquisition/release stripped from `consume` (pre-PR unlocked RMW) | exactly 1: `test_cross_process_contention_never_exceeds_cap` — RED 4/4 runs via the SUM assertion (e.g. 6 procs jointly charged **131** vs cap 40, per-proc [40,22,24,19,12,14]; file value alone would have hidden it) | 19 GREEN | same |
| 3 overshoot | pre-PR `current >= cap` restored | exactly 1: `test_multi_unit_charge_never_overshoots_the_cap` | 19 GREEN (incl. `test_single_unit_boundary_unchanged_by_overshoot_fix` — proves the units==1 boundary is exactly preserved) | same |

The lock race test asserts the **sum of per-process successful charges** (test_budget.py:242-246)
AND the file value (test_budget.py:249-250) — the last-writer-wins blind spot named in the
dispatch is explicitly closed by the test's own design.

## 3. Race results (probed HARDER than the test)

- **In-PR test**: 6 procs, cap 40, 45 attempts each — GREEN at b9e0d4d5, RED under mutation-2.
- **Own probe**: **12 processes, cap 25, 35 attempts each, 3 rounds** — sum(successes) == file
  value == cap **every round**. No overshoot, no lost update, no child crash.
- **SIGKILL mid-hold** (stale-lock/deadlock probe): child took the flock and was SIGKILLed while
  holding it. A fresh `consume()` acquired in **1ms** — kernel auto-released the flock on fd
  close at process death; the leftover `.lock` file on disk is inert (flock binds the inode,
  not the file's existence). **No deadlock path.** This empirically validates the builder's
  blocking-lock rationale (budget.py:173-177).

## 4. Adversarial edge findings

| ID | Sev | Finding | Repro | Disposition |
|---|---|---|---|---|
| F-1 | MEDIUM | `consume(units)` does not validate `units >= 1`: **`consume(-3)` silently REFUNDS the day's count** (cap 5 filled → count 2) and `consume(0)` at cap succeeds as a no-op. The ledger can thereby write, then re-accept, states the cap contract forbids. Constructor validates `cap >= 1` (budget.py:112-113) but `consume` (budget.py:197) validates nothing — inconsistent. UNREACHABLE today (both callers — BudgetedPacedFetcher budget.py:244, parity.py:241 — call bare `consume()`), which is why this is not blocking. | `l=PerDayBudgetLedger(path=p,cap=5,clock=c); l.consume(5); l.consume(-3); l.count_today() == 2` | **CARRIED with WU-3 CONDITION**: add `if units < 1: raise ValueError(...)` (2 lines) BEFORE WU-3 wires caller-computed multi-unit charges — a sign/arithmetic bug in the WU-3 unit computation would otherwise fail the meter OPEN silently. |
| F-2 | LOW | Negative day-count in the ledger file accepted silently: `{"2026-07-30": -1000000}` → `count_today() == -1000000`, `consume()` proceeds (fail-open granting ~1M attempts). Same threat actor as file deletion (which by design resets to 0), but deletion grants at most `cap`; a negative grants unbounded. Within close-1's declared `day -> int` contract, outside its tampered-ledger threat model. | write the payload, `count_today()` | CARRIED: fold `v >= 0` into the `_load` value check (same lines as F-3 fix). |
| F-3 | LOW | Silent type coercion in `_load` (budget.py:143): `"7"`→7, `3.9`→3 (truncated), `true`→1 — `int(v)` coerces instead of refusing. Weakens close-1 strictness at the margins. | write each payload, `count_today()` | CARRIED: `isinstance(v, int) and not isinstance(v, bool) and v >= 0` closes F-2+F-3 together. |
| I-1 | INFO | Symlink alias: lock path derives from the GIVEN name (budget.py:167-168), so chargers addressing the same ledger via symlink vs real path use different `.lock` files → no mutual exclusion; first `consume` via a symlinked path also replaces the symlink with a regular file (`os.replace`). Non-issue under the single pinned WU-3 path. | probe H | Ledger note only. |
| I-2 | INFO | Lock-stamp truncation: `open(lock_path, "w")` (budget.py:181) truncates BEFORE the flock is held, so a waiter wipes the current holder's PID stamp. Diagnostics-only; locking correctness unaffected (flock binds the inode, not content — proven by probes A/B). | code read | Ledger note only. |
| I-3 | INFO | Blocking `LOCK_EX` is taken inside async coroutines (`BudgetedPacedFetcher.fetch` → sync `consume`, budget.py:244): a contended lock stalls the event loop. Bounded critical section + the process-singleton fetcher design makes this negligible; relevant only if multiple parity processes are ever run deliberately. | code read | Ledger note; WU-3 awareness. |
| I-4 | INFO | `{year}` template across New Year: verified by year-crossing clock probe — day keys stay authoritative (`{"2026-12-31": 1, "2027-01-01": 1}` in one file, fresh budget on the new day); the filename year is growth-bounding cosmetics only. WU-3 resolves via `.format(year=...)` at arming per budget.py:90-91. | probe G | No action. |
| I-5 | INFO | No parity-level test pins budget behavior under the retry orchestrator. Own probe: outbound 429 → `ParityOutboundError` (deliberately classifier-opaque, parity.py:125-137) → orchestrator re-raises immediately, NO in-process retry → charges == outbound invocations exactly (1==1). Invariant holds; parity.py is UNCHANGED by this PR. | retry-recharge probe | Coverage note for WU-4 window instrumentation. |

Edges probed CLEAN (no finding): wrong-shaped-nesting `{"2026-08-03": {"x": 1}}` →
`BudgetLedgerCorrupt` (TypeError branch, budget.py:144); missing ledger dir → mkdir-on-demand
(budget.py:152, 180), consistent with legitimate-empty semantics; TOCTOU — `_load` is INSIDE
the lock (budget.py:210-212), `count_today` reads lock-free but `os.replace` atomicity means
readers never see a torn ledger; day-rollover mid-sequence — key computed once inside the
locked section (budget.py:213).

## 5. Semantics check vs pythia §5 counsel — PASS

- **Semantics-agnostic ledger**: `consume(units)` charges whatever the caller counts; nothing
  in budget.py references S3, section files, or success/failure of the charged operation. The
  REJECTED S3-section-file proxy appears nowhere. Grep receipts: no `[sS]3`/boto in budget.py;
  no hardcoded 11200/5600 cap (constructor-injected only, budget.py:92 comment confirms intent).
- **Every-ATTEMPT-counts contract**: charge lands BEFORE the outbound at both integration
  points — `BudgetedPacedFetcher.fetch` (budget.py:244, proven by
  `test_attempt_counts_even_when_inner_429s`: inner 429'd, unit spent) and parity.py:236-241
  (charge inside `_attempt` before `_outbound`; file untouched by this PR — diff stat is
  budget.py + test_budget.py only). Own-hands behavioral probe at the armed parity source:
  charges == outbound invocations exactly, 429 included.
- **Hash-CLEAN verifies / S3 ops do not charge**: structurally guaranteed — the ledger has no
  hook into those paths; only `fetch()`-boundary callers charge. WU-3 must preserve this by
  instrumenting the actual Asana client call site (pagination pages individually) per counsel.
- **Pre-charge check does not shift the boundary**: `current + units > cap` at `units == 1` is
  exactly the prior `current >= cap` (asserted by
  `test_single_unit_boundary_unchanged_by_overshoot_fix`; discriminated by mutation-3).

## 6. Judgment-call rulings (flagged in dispatch)

1. **Blocking LOCK_EX vs polling_scheduler's LOCK_NB-then-skip — RATIFIED.** Skip semantics
   are correct for a scheduler tick (a missed tick is safe) and WRONG for a meter: a skipped
   lock means either proceed-unbudgeted (the exact overshoot defect this PR closes) or a
   spurious refusal. The critical section is bounded local file IO; kernel auto-release on
   process death is empirically proven (SIGKILL probe, §3) — the deadlock objection to
   blocking locks does not attach. The divergence is documented with rationale in-code
   (budget.py:173-177).
2. **`{year}` template constant vs fully-resolved path — RATIFIED.** The template makes the
   arming-time deferral explicit; a resolved constant would be stale-prone. Correctness rides
   on the in-file date keys, never the filename (year-crossing probe, I-4). WU-3 formats at
   arming time.
3. **Non-integer-day-value refusal — RULED IN-SCOPE hardening, not scope creep.** Pre-PR,
   `{"d": "banana"}` raised a bare untyped `ValueError` (loud by accident, indistinguishable
   from a code bug) and floats coerced silently. Typing it `BudgetLedgerCorrupt` completes
   close 1's refuse-loud contract at zero src/ surface. Residual laxity ledgered as F-2/F-3.

## 7. Suite + lint receipts (own hands)

- `uv run python -m pytest tests/harness/substrate_gate tests/unit/substrate -q` → **295 passed**
  at b9e0d4d5, run twice (before mutations 52.95s; after final restore 15.37s — clean-restore
  proof).
- `uv run ruff check` + `ruff format --check` on both PR files → clean.
- Mutation runs used the same suite; every mutation was restored via
  `git checkout b9e0d4d5 -- tests/harness/substrate_gate/budget.py` and the restore verified
  by empty diff + full-suite green.

## 8. What WU-3 must know (carry-forward conditions)

1. **F-1 guard before wiring units** (MEDIUM): add `units >= 1` validation to `consume` before
   any WU-3 code computes multi-unit charges; optionally close F-2/F-3 with the strict-int
   non-negative `_load` check (≤5 lines total).
2. **Cap wiring**: constructor-inject the calibrated cap (~11,200/day, 2× headroom) from the
   WU-1 instrumented HTTP-boundary count — NEVER the ~5,600 section-proxy bound (pythia §5).
3. **Instrument the Asana client call site**: charge per HTTP attempt, pagination pages
   individually; `section_count == 0 ≠ attempts == 0` (monolithic pipelines). Hash-CLEAN
   verifies and S3 ops must not charge.
4. **Resolve `PINNED_LEDGER_PATH.format(year=...)` at arming time**; the path is P13-amendable.
5. **One charger name**: address the ledger by the single pinned path only (I-1 symlink note);
   the process-singleton fetcher (`get_process_fetcher`) stays the in-process funnel.
6. **Budget refusal surfaces loudly**: `ParityBudgetExhausted`/`BudgetLedgerCorrupt` are plain
   RuntimeErrors — non-transient to core.retry by design; WU-3 receipt-writer must record a
   budget HALT as a charter L81 operator-interrupt trigger (budget exhaustion), not retry it.

---

P7 line: **self-assessment caps MODERATE.** Discrimination and race evidence above are
own-hands (not inherited from the builder), but this receipt is same-rite authorship;
STRONG on the mechanism arrives only via rite-disjoint corroboration (PT-03 fresh potnia +
cross-rite security critics at WU-5).

---

# QA GATE — PR #303 exemplar #2 leg-2 re-pin

**VERDICT: GO** — the coherent-set discipline of the pythia drift verdict §4
(RECEIPT-s8-0-fixture-recapture-2026-07-30.md, on main via #302) is satisfied on every
term, verified own-hands from the committed bytes; zero MEDIUM/LOW findings, 1 INFO.
**Self-assessment caps MODERATE** (P7 line).

- **Reviewed**: PR #303, commit 329f3571 (branch fix/s8-2-exemplar2-leg2-repin, off main
  5d62d0b8 — forks pre-#301; suite baseline 285). Diff scope: exemplars.py +
  test_exemplar_two_drift.py + fixtures/offer_1143843662099250/{offer_plane_section_mrr.parquet
  (Bin 2843→2838), watermark.json} — 4 files, nothing else.
- **Session**: session-20260803-220334-f2a75514 · wave S8-2 · reviewer qa-adversary (P7 warm seat).

## 1. Coherent-set advance (verdict §4 term 1) — PASS, own-hands recompute

Value, digest, and fixture bytes advance TOGETHER in the single commit 329f3571. I
recomputed BOTH pinned constants from the committed projection parquet bytes myself
(polars group_by section / sum mrr / count; canonical json `sorted {section: [rows, value]}`
compact separators; sha256):

| Quantity | Recomputed from bytes | Pinned constant | Match |
|---|---|---|---|
| ACTIVE | 45r / $57,085 | 45r / $57,085 (exemplars.py:175) | YES |
| OPTIMIZE - Human Review | 7r / $10,900 | 7r / $10,900 (exemplars.py:176) | YES |
| STAGED | 6r / $8,000 | 6r / $8,000 (exemplars.py:177) | YES |
| served_value | $75,985.0 | `_CURRENT_VALUE` 75_985.0 (exemplars.py:166) | YES |
| in-scope rows | 58 | test_exemplar_two_drift.py:44 `== 58` | YES |
| composition digest | sha256:4a3aca962e1b656a47a74c2d57c19d1353b024b11c98c54fee267666e5285b65 | `_CURRENT_DIGEST` (exemplars.py:170) | YES (exact) |

Coherence bonus: the projection parquet holds 4,191 rows — exactly the watermark
`row_count: 4191` (the full-plane (section, mrr) projection of the leg-2 frame, as §4
requires). The verdict's re-pin contingency ("the projection being committed and
re-deriving $75,985 from its own bytes") is discharged by direct recompute, not by
trusting the constants.

## 2. PII discipline (verdict §4 term 2) — PASS

- Parquet schema inspected own-hands: **exactly** `{section: String, mrr: Float64}` —
  no other columns. Section values are workflow labels (ACTIVE, INACTIVE, Sales
  Process, ...), no customer identity.
- **NO `dataframe.parquet` (full PII frame) entered the diff** — diff stat is exhaustive
  (4 files); `git ls-files` on the fixture dir shows only the projection + watermark;
  no untracked leakage. The full frame's sha256 `cb79eaf5…b75c261` is recorded
  comment-only (exemplars.py:155-156) for re-fetch capability, per §4.
- watermark.json: identical KEY SET to the leg-1 fixture (project_gid, watermark,
  saved_at, row_count, columns [names only], entity_type, population_degraded,
  population_min_rate) — only VALUES advanced (instant 16:12:41.349255, saved_at
  …501623, row_count 4180→4191, population_min_rate 1.0→0.8205128205128205, matching
  the verdict's anomaly-3 registration verbatim). Nothing else rode in.

## 3. Exemplar #1 untouched + C17 (verdict §4 / bar 3) — PASS

- Byte-level check: exemplars.py lines 1-138 (the whole frozen exemplar-#1 block)
  are **diff-identical** between 5d62d0b8 and 329f3571 (both diff hunks land at :139+
  and :182+, exemplar-2 region only). `$84,385` / `$79,585` wound archetype intact
  (exemplars.py:57-58).
- C17 wiring preserved: `_OFFER_SLA_SECONDS = 3600` unchanged (exemplars.py:163) and
  the governed-contract assertion `proof.sla_seconds == 3600` retained
  (test_exemplar_two_drift.py:65).

## 4. Mutation probes (determinism tripwire has teeth)

| Mutation | RED | Restored |
|---|---|---|
| `_CURRENT_VALUE` 75_985 → 75_986 | ALL 8 drift tests RED — the flip is caught at `Materialization` CONSTRUCTION (composition==served_value invariant), poisoning every exemplar-2 caller. The tripwire bites before assertion altitude. | `git checkout 329f3571 --`; 8/8 GREEN |
| `_CURRENT_DIGEST` last hex 5→4 | exactly 1 RED: `test_fixture_parquet_bytes_rederive_the_pinned_constants` (recomputed-from-bytes digest ≠ pinned), 7 GREEN — narrow discrimination | same; 8/8 GREEN; full suite 285/285 |

**Stale old-generation constants**: grep across tests/ for `614c9ab8 | 4e711a7a | 80_985 |
80985 | da977513 | == 61 | 4180` → survivors ONLY in historical prose (exemplars.py:149
GENERATIONS block + :204 docstring — the leg-1 retention §4 explicitly requires), **zero
asserting positions**. No test still pins the old generation.

## 5. Derived-constant coherence (bar 5) — PASS, re-derived

- `_DRIFT_DELTA = -8_400.0`: 75,985 − 84,385 = −8,400 ✓ (test_exemplar_two_drift.py:29).
- Docstring ledger closes exactly: shared-section shifts ACTIVE −$4,500 (61,585→57,085)
  + OPTIMIZE +$3,000 (7,900→10,900) + STAGED −$2,000 (10,000→8,000) = **−$3,500**;
  minus the $4,900 synthetic OTHER bucket = **−$8,400** headline ✓ (exemplars.py:195-201).
- leg-1→leg-2 motion: $80,985 − $75,985 = $5,000 ✓ matching the verdict's PROMINENT-flagged
  −$5,000/−6.17%; row motion 47→45 ACTIVE (2 offers) + 7→6 STAGED (1 offer) matches the
  docstring's benign-motion narrative ✓. Historical leg-1 numbers are quoted unaltered.

## 6. Suite + lint (bar 6) — PASS

`uv run python -m pytest tests/harness/substrate_gate tests/unit/substrate -q` →
**285 passed** at 329f3571 (expected on the pre-#301 fork; the 10 budget tests live on
the other branch — no conflict, no rebase needed: the two PRs share zero files).
Ruff check + format clean on both changed .py files. Post-mutation restores verified by
clean `git status` on tests/ + full-suite re-run.

## Findings

| ID | Sev | Finding | Disposition |
|---|---|---|---|
| R-1 | INFO | The bytes tripwire filters to the three in-scope sections before digesting (test_exemplar_two_drift.py:110), so corruption confined to OUT-of-scope rows of the committed projection (4,133 of 4,191 rows) would not trip it. By design — the digest is defined over the lifecycle composition, and out-of-scope rows bear no pinned constant — but a swapped fixture that preserves the 3-section stats passes. Not worth hardening at P7 economy; noted for PT-03 awareness. | Carried (ledger note only). |

**Verdict: GO.** 0 MEDIUM · 0 LOW · 1 INFO. No stale old-generation constant survived in
any asserting position. The re-pin lands exactly as the pythia §4 grant prescribed.

P7 line: **self-assessment caps MODERATE** — own-hands byte recompute and mutation
discrimination, but same-rite authorship; rite-disjoint corroboration arrives at PT-03
(fresh potnia fixture-replay) per the wave plan.

---

# QA GATE — PR #305 arm-parity-window (WU-3)

**VERDICT: NO-GO** — two blocking-class findings (F-305-1 parity-number ≠ served
active_mrr; F-305-2 refused rebuild outcomes emit clean-looking parity observations,
proven by live probe). Both are BOUNDED fixes, not architecture: an outcome guard in the
outbound + a served-number comparison leg (or an explicit pythia adjudication of the
number's definition). Everything else on the PR is strong — the guard teeth all
discriminate under mutation, the budget invariant holds on every probed path, the PROV
identity chain closes against the tf bytes, and the F-1/F-2/F-3 carries from the #301
gate are closed with discriminating tests. **Self-assessment caps MODERATE** (P7 line).

- **Reviewed**: PR #305, commit 479fc38a (branch feat/s8-2-arm-parity-window, directly
  off main 1276b732 — #301/#302 in base). Diff: src/autom8_asana/substrate/{live.py 844L,
  prov_sweep.py 113L} + harness extensions (budget.py F-closes, parity.py additive arming)
  + pyproject mypy override + 3 test files (+29 tests; 324 own-run).
- **Session**: session-20260803-220334-f2a75514 · wave S8-2 · qa-adversary (warm seat #3).

## Verification receipts (own hands)

- Suite: `uv run python -m pytest tests/harness/substrate_gate tests/unit/substrate -q`
  → **324 passed** at 479fc38a; re-run green after every mutation restore.
- Ruff clean on all 7 changed .py files; `mypy --strict` clean on live.py + prov_sweep.py;
  `mypy src` clean (574 files).
- **mypy override scope verified honest**: removing the
  `tests.harness.substrate_gate.*` follow_imports=silent override surfaces EXACTLY ONE
  error — `cases.py:112` HarnessRefusePayload SunsetBreach variance, pre-existing and
  harness-internal, precisely what the builder's comment claims. No src error is masked.
- **Zero-live-network**: every boto3 use in the new tests sits inside `with mock_aws()`
  (moto); CloudWatch in 3e tests is a recording stub (`_RecordingCloudWatch`,
  test_prov_sweep.py:40-45); the real client path is lazy-constructed only in prod use.
- **Seam-use attested**: rebuild.py NOT in the diff (Protocols/RebuildResult untouched);
  parity.py diff is additive-only (`get_process_fetcher` arming kwargs +
  `_arm_process_fetcher_in_place`; the PacedLiveParitySource class body unchanged).
- **[H17]/F-2 reachability tooth bites**: mutating live.py to reference
  `store.read_current` → `test_read_current_reachable_only_from_the_seam` RED (exactly);
  restored GREEN. live/prov_sweep are on the store-import allowlist ONLY
  (test_serve_raw_read_privacy.py:43-51 vs :56-59).
- **PROV identity chain (iteration-1 NO-GO class) closes on tf bytes**: tf
  `variable "environment"` default `"production"` (observability_alarms.tf:38-42) ==
  `observe.DEFAULT_ENVIRONMENT` (observe.py:415) == `PROV_ENVIRONMENT` (prov_sweep.py:60);
  every PROV-* alarm filters `dimensions = { environment = var.environment }`
  (substrate_v2_provability_alarms.tf:118/147/175/204); namespace
  `"Autom8y/SubstrateProvability"` == tf default (:62). Both sides test-pinned
  (tf string-diff test + heartbeat-dims test — two-sided).

## Mutation-probe table (all discriminate; all restored, 324/324 after)

| # | Guard mutated | RED test(s) | Rest |
|---|---|---|---|
| m1 | `_budget.consume()` removed from `_attempt_page` (live.py:466) | exactly 4: 3b clean-multipage-charges, 3b 429-still-charges, 3b exhaustion-halts, 3c budget-halt-receipt | 13 GREEN |
| m2 | torn-read `frame.height != row_count` disabled (live.py:202) | exactly 1: 3a torn-read row-count refuses | 16 GREEN |
| m3 | `PROV_ENVIRONMENT` → `"prod"` | exactly 1: 3e environment-matches-terraform | 3 GREEN |
| m4 | F-1 `units < 1` guard disabled (budget.py) | exactly 1: `test_f1_consume_rejects_non_positive_units` | 27 GREEN |
| m5 | conflicting-rearm refusal disabled (parity.py) | exactly 1: 3c conflicting-rearm-refuses | 16 GREEN |

## Findings by severity

| ID | Sev | Finding | Evidence / repro |
|---|---|---|---|
| F-305-1 | **HIGH — BLOCKING** | **The window's parity number is NOT the served active_mrr.** Production serve (from CODE, not receipts): `metrics/definitions/offer.py:26-43` — scope `classification="active"` + `dedup_keys=[office_phone, vertical]` + filter `mrr > 0`; `compute.py:67-79` filters sections via `CLASSIFIERS["offer"]`; `activity.py:181-207` — the "active" group is **22 sections**. live.py:106 pins **3** (`ACTIVE_MRR_SECTIONS`). Empirically (own-hands, fixture bytes at this branch): three production-ACTIVE sections are INVISIBLE to the window comparison — OPTIMIZE QUALITY - Update Targeting 1r/$1,500 + OPTIMIZE QUANTITY - Request Asset Edit 1r/$1,500 + OPTIMIZE QUANTITY - Update Offer Name 9r/$11,360 = **$14,360 of production-active MRR the window cannot see**. A v2 fetch PLAN that omits any of those sections yields a CLEAN parity read while v2-served active_mrr silently loses value — plan-driven partial refetch is exactly the machinery being armed. The dedup keys cannot even be expressed by the PII-safe fixture, so the harness *cannot* compare the served number as-built. The builder's live.py:102-105 comment discloses the narrowing honestly — but a comment is not an adjudication, and LEG-2 anchors to SERVED active_mrr. Whether the founding wound number ($79,585) coincided with the served surface is [UV-P: wound-instant served-value equals 3-section sum \| METHOD: operator/pythia historical-receipt check \| REASON: not derivable from present code — definitions differ today by construction]. | Remediate by ONE of: (a) compute the real metrics-pipeline active_mrr on BOTH in-memory frames inside the outbound and carry it in the observation + receipts (frames are live in memory; PII never persists); (b) extend the comparison set to `CLASSIFIERS["offer"].active_sections()`; (c) an explicit pythia ruling that the exemplar 3-section definition IS the LEG-2 anchor — silence is not an option at window-open. |
| F-305-2 | **HIGH — BLOCKING** | **Refused rebuild outcomes emit clean-looking parity observations.** `_outbound` (live.py:721-736) guards only `fetched is None` — never `result.outcome`. A completeness-gap fetch returns FETCH_REFUSED **with** a captured partial frame (`rebuild.py:544-547` + `_CapturingFetcher`), so the outbound builds v2 from the PARTIAL frame and returns a normal `ParityObservation`. **Proven live (own adversarial test)**: 2-section plan, one section exhausts retries → receipt `outcome=fetch_refused` AND an observation with v2 served_value 100.0, `frame_digest == content_digest` (looks coherent). The refuse-loud C16 outcome masquerades as a window data point — poisoning the WU-4 divergence ledger (a partial in-scope frame reads as a WOUND; a partial out-of-scope frame reads CLEAN). Same class covers STAGED_REJECTED-with-frame (builder's own flag 5, still unexercised). | Fix: emit an observation ONLY on `RebuildOutcome.SWAPPED`; other outcomes raise `OfferSectionFetchError` (receipted). My probe tests are adaptable as the regression tests. |
| F-305-3 | MEDIUM | **Charged prod touch with ZERO receipt on non-budget-halt raise paths.** Only `ParityBudgetExhausted` is caught for receipting (live.py:731-733); any other post-fetch raise propagates receipt-less. Proven: value-column-poor rows → `MissingValueColumnsError` from staging — 1 budget unit charged, receipts dir EMPTY. Violates P10 "every prod touch leaves a receipt". | Wrap the outbound body; write an `outcome=error` receipt on any raise after the first charge. |
| F-305-4 | MEDIUM | **Torn-read guard misses an equal-rowcount generation swap.** Proven: watermark from a "newer generation" with matching `row_count` → accepted; the stale frame wears the newer build instant (the fresh-stamped-staleness wound class). The 2-object guard cannot see section mtimes (leg-1's S3-LIST cross-check). Mitigation in-window: the v2 comparison itself would flag the divergence. | WU-4: add the section-listing cross-check or a double-read watermark byte-equality guard; or pythia-note the residual. |
| F-305-5 | MEDIUM (process) | **Merge-order collision with PR #303**: test_live pins leg-1 literals (`80_985.0` at :177/:229/:395) against fixture bytes #303 re-pins to leg-2 ($75,985). Whichever merges second goes RED at integration. | Rebase #305 over #303; pin via exemplar constants (already imported), not literals. |
| F-305-6 | LOW | Pre-budgeted singleton double-charges after in-place arming: `get_process_fetcher(budget=L)` then `arm_process_parity_fetcher(...)` → source-level + page-level charges (proven: 2 charges for 1 page). Unreachable via `arm_offer_parity_window` (fresh source, budget=None). | Guard: assert/null the source-level budget at arm time. |
| F-305-7 | LOW (doc) | 429/retry docs imply in-sweep retries that cannot occur (see ruling flag 2): ALL boundary exceptions wrap to non-transient `ParityOutboundError` before the orchestrator sees them, so `execute_with_retry_async` never retries; `retries_issued = requests − pages` counts FAILED attempts, not retries. | Doc fix at live.py:405-413/:456-462 + FetchTelemetry semantics note. |

## Rulings on the two flagged design questions

**Flag 2 — 429/retry semantics: RIGHT, but misdocumented (carry doc fix F-305-7).**
The posture — a 429 charges its unit, shrinks the AIMD window (`slot.reject()`,
live.py:474, mirroring the S8-0 parity.py:249-250 discipline), FAILS this sweep's
observation, and defers to the next paced sweep — is the P10-conservative choice:
in-sweep retries against a rate-limited API are precisely the storm the budget exists to
prevent, and pythia §5 is satisfied because every boundary ATTEMPT (success, 429, retry)
charges before the call (m1 proves the tests discriminate on this). What is WRONG is the
documentation: "per-page retry" (live.py:407, 484-490) implies in-sweep retry that is
structurally impossible — `_attempt_page` wraps every exception into non-transient
`ParityOutboundError` before the orchestrator classifies it, so the retry leg is v1-G6
uniformity, not live retry. Post-F-305-2-fix, a 429'd sweep must surface as a receipted
refusal, which completes this posture honestly.

**Flag 3 — active_mrr definition: BLOCKING as-built (F-305-1).** The receipted 3-section
set is NOT the number v1 serves — from code: served = Σ mrr over the 22-section
classifier active-set, deduped by (office_phone, vertical), mrr>0 filtered. The window
as-built proves parity of a harness-internal number and is structurally blind to
$14,360 of production-active MRR at the current snapshot. MISSION anchors to "every
business number the asana dataframe substrate serves"; LEG-2 anchors to served
active_mrr. Either the comparison covers the served definition, or pythia explicitly
rules the exemplar definition is the LEG-2 anchor — the window must not open on an
unadjudicated ambiguity of its own core number.

## WU-4 implications

WU-4 must NOT open the window on this build. Iteration-2 needs: F-305-1 resolution
(served-number leg or pythia ruling), F-305-2 outcome guard + regression tests
(adversarial probes provided), F-305-3 error receipts, #303 rebase (F-305-5). F-305-4/6/7
may ride as WU-4 conditions. The rest of the PR — budget invariant
(`count_today == requests_issued` held on clean/429/reuse/refused paths), pacing
composition, PROV chain, arming singleton discipline, F-carry closes — is sound and
should survive iteration-2 unchanged.

P7 line: **self-assessment caps MODERATE** — all discrimination and probe evidence is
own-hands (not inherited), but same-rite authorship; the NO-GO gives the DELTA-scope for
the builder's iteration-2 per critique-iteration-protocol.

---

# QA DELTA-GATE — PR #305 iteration-2

**VERDICT: GO** — both HIGH blockers from iteration-1 are RESOLVED under the pythia
referent ruling (RULING-pythia-f305-1-active-mrr-referent-2026-08-04.md, §6 binding
conditions), each resolution proven discriminating by live mutation; the delta introduced
no new blocking defect. 0 HIGH · 1 MEDIUM (carried as a BINDING WU-4 entry condition,
backstop-protected in-window) · 1 LOW carried · 3 INFO. **Self-assessment caps MODERATE**
(P7 line).

- **Reviewed**: PR #305 iteration-2, commit 33f0fbcb (branch merged main through #303;
  delta commit over merge 210321d9 touches live.py + test_live.py + builder memory only —
  parity.py / rebuild.py / prov_sweep.py UNTOUCHED by the delta: seam still additive-only).
- **DELTA discipline**: previously-passed surfaces (pacing composition, budget wiring,
  PROV chain, singleton discipline, 429 posture) NOT re-litigated except where the delta
  touched them (fetch :645-651 re-verified below).
- Suite **336/336** own-run; ruff clean; `mypy src` clean (574 files).

## 1. Fix-resolution matrix (each proven by mutation — revert → RED → restore → GREEN)

| Iter-1 finding | Fix (verified own-hands) | Mutation | RED test(s) |
|---|---|---|---|
| F-305-1 (HIGH) | LEG A rides the REAL served machinery: `compute_metric` imported live.py:74, registry `Metric` live.py:157, frame passed UNMODIFIED (`served_active_mrr` live.py:190-207); classifier-sourced 22-section set (live.py:161-170, `len==22` asserted); fail-closed coverage BEFORE any charge (live.py:648-651); dual-leg `ParityLegs` ledger rows (scalars+digests only) | mC: raw-sum substitution for `compute_metric` | exactly 2: `test_served_active_mrr_dedups_and_filters`, `test_3a_leg_a_materialization_from_full_frame` |
| F-305-1 keystone | `assert_plan_covers_active_set` (live.py:173-187) enforced in `fetch` BEFORE charge | mB: call removed from fetch | exactly 2: `test_3b_coverage_refusal_before_any_charge`, `test_3c_coverage_refusal_is_first_class_no_charge` |
| F-305-2 (HIGH) | observation ONLY on `RebuildOutcome.SWAPPED` (live.py:1037); non-SWAPPED → refusal receipt + `ParityLegRefused` (first-class, §6 #9) | mA: guard disabled | exactly 1: `test_3c_fetch_refused_is_first_class_not_an_observation` |
| F-305-3 (MED) | `write_error` (live.py:899) on ALL raise paths (:1023-1033 and :1056-1067); no raise path escapes unreceipted | mD: receipt call dropped | exactly 1: `test_3c_error_path_still_receipts` |
| F-305-4 (MED) | build-instant monotonicity guard (live.py:317-322), two-sided test | mE: guard disabled | exactly 1: `test_3a_generation_monotonicity_guard_two_sided` |
| F-305-5 (MED) | branch merged main (#303); leg-2 pins asserted ($75,985 at `test_3a_leg_b_exemplar_aggregate_from_fixture`) | — (structural) | suite green on merged fixture |
| F-305-7 (LOW) | prose corrected: NO-in-sweep-retry stated at class docstring + `retries_issued` semantics at live.py:515-518 | — (doc) | verified by read |

Coverage no-hardcode is separately proven: `test_coverage_follows_classifier_mutation`
(monkeypatched classifier set PROPAGATES into the assertion — §6 #1 is behavioral, not
prose). Restores verified: clean `git status` + 336/336 after the battery.

## 2. Per-flag rulings (the builder's five)

**Flag 1 — LEG A identity: VERIFIED IDENTICAL.** Same function object
(`autom8_asana.metrics.compute.compute_metric`), same registered `Metric` instance
(`MetricRegistry().get_metric("active_mrr")`), frame passed with NO pre-processing (the
column-presence check adds no transformation); the classifier→filter→dedup→cast→sum
order is compute.py's own pipeline — identity by construction, not reimplementation.
mC proves the tests discriminate on it. One data-contingent note (INFO): dedup
`keep="first"` is row-order-sensitive IFF sibling offers under one unit carry UNEQUAL
mrr (violating the offer.py:29-33 unit-level invariant); if that invariant ever breaks,
v1-vs-v2 row order can produce a penny-diff at identical instant — which surfaces as
W1/W3 (detected and adjudicable, not silent).

**Flag 2 — coverage keystone trust boundary: the declared-vs-actual gap EXISTS; NO
silent-loss path exists at the window; NOT blocking — BINDING WU-4 planner-contract
condition.** Proven by my lying-plan probe (own-hands, in-tree): a plan declaring the
full 22-section coverage while fetching ONE section PASSES the keystone, charges (1),
and serves — v2's omitted section contributes silent $0 *to the v2 scalar* (the hole one
level down, as feared). BUT the dual-side LEG A comparison is the structural backstop:
v1 is produced by the INDEPENDENT incumbent pipeline, so the omitted value appears in
`served_v1` and the mismatch is IMMEDIATELY visible — probe receipt legs read
`served_v1=600.0 / served_v2=100.0` and the observation carries the same divergence
into the window's classification. For value to vanish silently, BOTH sides would have
to omit it, which the v2 planner cannot cause. A frame-level §6 #9 row-presence check
is structurally impossible at this altitude: empirically (gate-2 full-projection probe)
only 6 of the 22 classifier-active sections carry ANY rows in today's prod frame — a
zero-row section is legitimately absent from a row-level frame, so "present" can only
mean FETCH-COVERED, which is exactly the plan contract. Ruling: (i) in-window, the
backstop closes the loss path by construction — no block; (ii) **BINDING WU-4 entry
condition**: the planner MUST derive `covered_section_names` from the live section
listing it actually fetched/hash-verified (gid→name reconciliation at plan-build time),
never a static declaration; (iii) post-cutover the v1 backstop disappears — coverage
must move into the serve-time provability predicate: a NAMED PT-03/S9 obligation.

**Flag 3 — PII column name in `ActiveMrrColumnMissing`: ACCEPTABLE, no tightening.**
Column NAMES are schema identifiers, not values; the committed watermark fixture already
publicly lists `office_phone` in its `columns` array (repo precedent). The message can
only carry names (`_SERVED_REQUIRED_COLUMNS` + `sorted(frame.columns)`) — no value
transits. `ParityLegs` carries scalars + digests only; dedup-key VALUES never land in a
receipt (§6 #8 verified in code).

**Flag 4 — `retries_issued` proxy: ACCEPTABLE as documented.** The field lives on the
FROZEN `FetchTelemetry` seam (renaming = seam change, correctly out of scope); the
semantics — counts FAILED attempts; no in-sweep retry exists — are now stated at the
accumulator (live.py:515-518) and the fetcher docstring. PT-03 readers consume the
docstring; carried as INFO.

**Flag 5 — `min_build_instant` threading deferral: ACCEPTABLE with a named condition.**
The guard itself is CLOSED in the library (two-sided test; mE discriminates) and the
parameter is plumbed through `build_parity_outbound` (live.py:962). WU-4 entry condition:
the runner initializes `min_build_instant` from the last served receipt's
`built_from_live_at` (fallback: the leg-2 baseline 2026-08-03T16:12:41Z) and threads it
per touch.

## 3. Delta regression checks (where the delta touched passed surfaces)

- **Budget invariant re-verified** at the changed `fetch` (:645-651): coverage refusal
  fires BEFORE any charge (`count_today() == 0` asserted in-tree + mB-discriminated);
  lying-plan probe held `count_today == requests_issued == 1`; 429/exhaustion/reuse
  invariant tests all green (iter-1 classes retained).
- **No new network**: delta test additions are moto + injected fakes only; prov_sweep
  untouched.
- **Refusal exception classes**: `ActiveMrrRefused`/`ParityLegRefused` are plain
  RuntimeErrors (non-transient to core.retry — no accidental in-process retry);
  `ActiveMrrRefused` is NOT a `rebuild.FetchRefused` subclass, so it propagates past the
  rebuilder (rebuild.py:538 catches only `FetchRefused`) to the dedicated
  refused-coverage handler — confirmed by the passing first-class test.
- **PII-safe fixture now refuses LEG A by design** (`ActiveMrrColumnMissing` on the
  (section,mrr) projection — `test_3a_leg_a_on_pii_safe_fixture_reports_missing`):
  correct, since the committed projection cannot express the served definition.

## 4. Findings by severity (iteration-2)

| ID | Sev | Finding | Disposition |
|---|---|---|---|
| M-1 | MEDIUM | Coverage keystone keys on plan-DECLARED names; a lying planner passes it (proven). In-window loss is impossible (LEG A dual-side backstop, proven 600-vs-100); post-cutover the backstop disappears. | **BINDING WU-4 entry condition** (planner derives coverage from actual fetch listing) + NAMED PT-03/S9 serve-gate obligation. Not blocking now. |
| L-1 | LOW (carried, iter-1 F-305-6) | Pre-budgeted singleton double-charge after in-place arming — delta did not touch; unreachable via `arm_offer_parity_window`. | Carry: optional arm-time `budget is None` assertion. |
| I-1 | INFO | Dedup `keep="first"` order-sensitivity contingent on the unit-level-mrr invariant (offer.py:29-33); breach surfaces as W1/W3, adjudicable. | Ledger note for the window's divergence classification. |
| I-2 | INFO | PII column-name-vs-value ruling (flag 3): acceptable, precedent-consistent. | None. |
| I-3 | INFO | `retries_issued` naming constrained by the frozen seam; semantics documented (flag 4). | None. |

## 5. WU-4 entry conditions (CONSOLIDATED, FINAL)

1. **Planner coverage contract (M-1, BINDING)**: `covered_section_names` derived from the
   live section listing actually fetched/hash-verified (gid→name reconciliation at
   plan-build), never a static declaration. Post-cutover coverage moves to the serve-time
   provability predicate (PT-03/S9 named obligation).
2. **`min_build_instant` threading (F-305-4)**: initialize from the last served receipt's
   `built_from_live_at` (fallback: leg-2 baseline 2026-08-03T16:12:41Z); thread per touch.
3. **Arming path**: fresh process, `arm_offer_parity_window` ONLY (cap 11,200 pinned;
   `{year}` ledger path resolved at arming; single pinned charger name; optional L-1
   arm-time budget-None assertion).
4. **Real Asana call site as `page_fetch`**: pagination pages charged individually;
   hash-CLEAN verifies and S3 ops never charge (pythia §5).
5. **Interrupt classes**: `ParityBudgetExhausted` (budget-halt receipt, charter L81
   operator interrupt) and `ParityLegRefused` (refusal receipts) are never retried
   in-process; refusals flow to pythia W2-vs-correct classification per rubric.
6. **Dual-leg receipts are the daily HANDOFF substrate**: LEG A `served_active_mrr` is
   the gate anchor (PT-03 Q1 / auto-flip); LEG B `exemplar_aggregate` is corpus-continuity
   ONLY — never quoted as active_mrr (ruling §4 label).
7. **Torn-read residual**: equal-rowcount swap now guarded by monotonicity; the S3-LIST
   cross-check remains optional hardening (pythia-noted residual, not an entry blocker).

P7 line: **self-assessment caps MODERATE** — all mutation discrimination and the
lying-plan/backstop evidence are own-hands, but same-rite authorship; rite-disjoint
corroboration arrives at PT-03 (fresh potnia, de novo, per-question receipts).
