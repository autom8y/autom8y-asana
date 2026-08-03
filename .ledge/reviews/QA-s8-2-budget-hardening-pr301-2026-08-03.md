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
