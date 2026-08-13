---
type: review
status: accepted
---

# CRITIQUE — EX-4 Exec-rung instrumentation (RUNG E limb (a) receipt schema)

- **Date**: 2026-08-13
- **Critic**: `structure-evaluator` (arch) — rite-disjoint from author `principal-engineer` (10x-dev). A two-ladder separability question is a boundary question.
- **NCSR carrier**: yes — binding NCSR on the founding negative **NR-4** (§A.2 mandate; flagged the likeliest false negative in the wave).
- **Deliberate non-seat honored**: `eunomia` `verification-auditor` is the future ATTESTER of RUNG E limb (a) and is NOT this critic — critiquing-then-attesting would be dispatcher-critic degeneracy. This is the critic.
- **Under review**: `src/autom8_asana/observability/rung_receipts/{schema,join,query,__init__}.py`; `tests/unit/test_rung_receipts.py` (15 tests); `tests/fixtures/rung_receipts/*.jsonl` — on branch `ex-4-rung-e-instrumentation` (off origin/main `afdad5ed`).
- **Method**: own-hands re-run under `PYTHONPATH="$PWD/src"` (venv editable-install otherwise resolves `autom8_asana` to the MAIN tree — the wrong tree). Confirmed the import resolves to the worktree src before every run.

## Verdict at a glance

| Exit criterion | Verdict | Grade |
|---|---|---|
| **1** — receipt schema consumable mechanically; query returns a REAL receipt | **PASS** | STRONG (re-derived own-hands) |
| **2** — FS-5: two ladders separably observable; no combined field | **PASS** | STRONG (re-derived own-hands) |
| **NR-4** — NCSR on the founding negative | **STANDS (narrowed)** — author's verdict CONCUR | STRONG on code / MODERATE on CR-2-fenced bucket |

Two non-blocking **CONCERNS** and one **UNKNOWN** are recorded below. None sink an exit criterion; all are forward-looking or attester-routed.

---

## Exit criterion 1 — mechanical consumption, real receipt — PASS

**Re-ran the author's demonstrating query own-hands** over the 15 real ASR delivery fixtures (`asr_live_delivery_census.jsonl`) via `run_query`:

```
TOP-LEVEL KEYS         = ['rung_4', 'rung_e_limb_a']
rung_e_limb_a.status   = not_yet_observed
observable_occurrences = 0
required_occurrences   = 2
receipts count         = 15
SAMPLE inv=4603f63c    : block_count=42  outcome=readout  gen=None
                         attest=not_observable  reason=generation_provenance_absent
outcome tally          = {'readout': 3, 'abort': 12}
generation-is-None     = {True: 15}   (all 15)
```

This matches the author's reported readout **exactly** (`status=not_yet_observed, receipts=15`; sample `inv=4603f63c block_count=42 gen=None`).

- The schema is **durable/queryable**: `run_query` is a pure, hermetic function (no AWS call in the query path — the two read-only Logs Insights queries live in `schema.py` as constants), `to_dict()` is JSON-serialisable, and a portable JSON Schema (draft 2020-12) pins the wire contract.
- The **join is on `invocation_id`** and binds a *delivery* occurrence to its *generation* provenance (LEFT join anchored on delivery, `join.py:98-124`).
- **The "real receipt" returned is a real NOT_OBSERVABLE receipt** — a genuine `DeliveryOccurrenceReceipt` projected from a real `report_posted` event (real block_count 42, real trace_id, real timestamp), correctly classified `generation_provenance_absent`. This is the honest posture: the real telemetry shows the gap; the OBSERVABLE path is demonstrated only via a clearly-labelled SYNTHETIC teeth fixture. The exit criterion ("a query returning a real receipt, not a schema document alone") is satisfied — a real receipt over real telemetry is exactly what the query returns.
- 15/15 unit tests pass own-hands (`0.16s`).

---

## Exit criterion 2 — FS-5, two ladders separably observable — PASS

Confirmed own-hands, five independent ways:

1. **Two top-level keys, exactly** — `{'rung_4', 'rung_e_limb_a'}`. No third/aggregate key.
2. **`additionalProperties: false`** on the wire schema (`schema.py:449`), so a conformant receipt cannot grow a combined field. Verified via `RUNG_E_LIMB_A_RECEIPT_JSON_SCHEMA["additionalProperties"] is False`.
3. **RUNG-4 is a single-value sentinel enum** — `Rung4Status` has exactly one member `unattested_felt_operator_only` (`schema.py:119-127`), pinned in the JSON schema (`"enum": ["unattested_felt_operator_only"]`, L438-439). This module **never** sets it: `join.py` sets only `rung_e_limb_a_attestation`; `DeliveryOccurrenceReceipt.rung_4_attestation` defaults to the sentinel and is never passed by `join_occurrences`.
4. **Making RUNG-E flip does NOT move RUNG-4** — own-hands two-machine aggregate: `status=satisfied, observable_occurrences=2, rung4=unattested_felt_operator_only`. The rung-4 ladder holds the sentinel across every occurrence.
5. **No combined/engagement/total field anywhere** — banned-field scan over the full serialized observation: `{'engagement': False, 'combined': False, 'total': False, 'overall_rung': False}`.

**Two-sided teeth re-derived own-hands** (independent of the test file):

| input | rung_e attest | reason | rung_4 |
|---|---|---|---|
| machine / no-human | **observable** | None | sentinel |
| machine / human-in-loop | not_observable | `human_in_loop` | sentinel |
| assembled_by=human | not_observable | `assembled_by_human` | sentinel |
| block_count swap (7≠42) | not_observable | `content_hash_mismatch` | sentinel |
| generation absent (live) | not_observable | `generation_provenance_absent` | sentinel |

The teeth bite on **authorship**, not presence, and in every case the felt ladder is untouched.

**Structural credit — the fence is stronger than "no combined field":** RUNG-4's only inhabitable value is a *string sentinel*, not a boolean or number. It is therefore **arithmetically un-combinable** with RUNG-E's status — a consumer literally cannot compute an "engagement total" from a felt sentinel. The R-15 non-substitution fence is enforced not just by omission but by type. This is the correct enforcement of the fence recorded at `RULING-operator-morning-set-2026-08-13.md` R-15 (L148-160): "the exec rung does NOT substitute for rung 4, and neither may be graded in place of the other." (Citation-form note, per the dispatch: the shape/charge cite "RULING…§5 item 1"; §5 ratifies the fence as its item 1, but the fence *substance* is R-15 L148-160, which I treated as authoritative and confirmed.)

**Residual (not a defect):** the emission boundary is clean; the schema cannot prevent a *downstream* consumer from inventing its own min(rung_e, rung_4) collapse. But (a) rung_4 is a non-numeric sentinel (see above), and (b) `additionalProperties:false` bars a conformant receipt from carrying such a field. The fence holds at the boundary the schema owns.

---

## §A.2 / §A.3 — Binding NCSR on NR-4 — verdict: **STANDS (narrowed)**

**The negative under test (author, narrowed):** *no generation-provenance receipt exists, joinable to the live `report_posted` delivery receipt on `invocation_id`, attesting the delivered payload was machine-assembled / no-human-in-loop* (`report_generated` query → zero rows).

This negative has failed **5-of-5 historically as a false negative**, so I swept every refuter own-hands and took the hop one past the author's stopping point.

### Refuters swept (what each returned, including NULLs)

- **(a) The delivery chain `slack_post_entered → slack_post_attempt → report_posted` ALREADY EXISTS — the "nothing emits" claim is FALSE.**
  CONFIRMED own-hands on origin/main (`orchestrator.py`): `slack_post_entered` at L1216, `slack_post_attempt` at L154/L217/L495, `report_posted` at L1249 — fired **only after** `await slack_client.send_blocks(...)` succeeds, and `dry_run` returns before it (L1230-1245). Corroborated by the author's cited `CRITIQUE-s3-delivery-rails-2026-08-12.md §5.1` ("`report_posted` cannot fire on a failed post"; "`dry_run` returns before it"). **The author did NOT rest on a false absence:** the schema's `DeliveryReceipt` half *builds on* this live event (`DELIVERY_EVENT = "report_posted"`, `DeliveryReceipt.from_event`), and the census confirms deliveries now carry real 42-block readouts, not only 3-block aborts. Refuter (a) is correctly **absorbed, not denied** — the narrowing is honest.

- **(b) The abort tick's ~6×/day post — joinable to a generation event? → NULL.**
  CONFIRMED. The readiness-abort path (`orchestrator.py:212`) builds blocks via `_build_readiness_abort_alert(readiness)` — a **hand-built** fixed gate message (block_count 3) that **bypasses `build_slack_report`** (the readout-assembly path) — then posts via `_safe_slack_post`, firing `report_posted` with `abort_reason="readiness_gate_abort"`. So the abort tick IS delivered but carries no generation provenance and is not a machine-assembled readout. The schema correctly classifies these as `outcome=ABORT` / `generation_provenance_absent`. Author's "NULL — abort payload hand-built, bypasses generation path" is exact. (Note: even post-EX-5, aborts stay `not_observable` — the right answer.)

- **(c) `DEFER-S-5`'s "durable in Slack history, quotable by permalink" — already a limb-(a) delivery receipt? → FALLS as a refuter.**
  CONFIRMED it falls: it is the **rung-3 human-reply capture route** (a different rung), not a generation-provenance receipt. It contributes a durable-locator `permalink` field, which the schema carries as `DeliveryReceipt.permalink` (optional). Consistent with the author.

### The hop one past — refuters I ADDED (named concretely)

The author stopped at "the emission site is EX-5's WS-2 discharge — `report.py`'s block-assembly path." I confirmed that (`build_slack_report`, `report.py:251`, emits only `log.warning` lines — no provenance event) **and pushed past it** to ask: is any authorship receipt obtainable *anywhere else* in the service?

- **Whole-service grep (origin/main, all 16 `.py` under `services/account-status-recon/src`):** `report_generated | assembled_by | human_in_loop | content_hash` → **zero hits, service-wide.** The generation-provenance event does not exist anywhere in code, not merely in `report.py`.
- **Verdict store `s3://autom8y-asr-verdicts` (`verdict_store.py` / `verdict_surface.py`):** the rows object key is `dt=.../asr-verdicts-{ts}-{run8}.jsonl.gz` where `run8 = invocation_id[:8]` — so it is *join-able in principle*. But (1) it is **CR-2-fenced** (I did not read or list the bucket), and (2) its **source code** shows the rows are **per-account graded verdict cells** (`build_verdict_rows`, `_billing_cell`, `_three_way_cell`, `_axis_cells`) — the analytical DATA output, carrying **no** `assembled_by`/`human_in_loop`/`content_hash`. It is a *different construct*: it attests the per-account status verdict, not the authorship of the delivered Slack blocks. A human could hand-paste the readout while the verdict surface was machine-written; the surface is silent on it. **Does not refute.**
- **`AccountStatusComplete` EventBridge completion event (`orchestrator.py:1093-1122`):** payload `{accounts_analyzed, total_findings, all_clear, published}` — a completion *dead-man*, not a payload-authorship receipt. **Does not refute.**
- **`record_side_effect` on the Slack post (`orchestrator.py:~1258`):** payload `{block_count, text[:100]}`, status REAL/SUPPRESSED/FAILED — emitted at the **same egress** a hand-paste would traverse; identical whether blocks were machine-assembled or hand-pasted. **Does not refute — it reinforces the narrowed negative** (delivery telemetry is silent on authorship by construction).

### Verdict + corrected scope

**STANDS (narrowed).** The author's `STANDS-NARROWED` is correct and is **not** itself an over-refusal: the narrowed negative is neither over-broad ("nothing emits" — falsified by refuter (a), and the author did not claim it) nor over-narrowed into triviality (it names precisely the load-bearing thing limb (a) requires: machine-authorship of the *delivered* payload, joinable on `invocation_id`). **It does not hide an obtainable receipt** — the four candidate sources that *could* have hidden one (verdict store, completion event, side-effect breadcrumb, plus the whole-service grep) each carry either delivery-side facts or per-account data verdicts; none carry authorship of the assembled blocks. The one remaining un-inspected surface (the S3 verdict *bucket contents*) is both CR-2-fenced and, by its own code, the wrong construct.

**Scope of the standing negative, precisely:** *within the ASR service on origin/main, no code path emits a generation-provenance event, and no obtainable joinable source attests machine-assembly of the delivered payload; the gap is real and its discharge site is EX-5 (WS-2 generation mechanism), correctly labelled UV-P.* The schema's `GENERATION_EVENT = "report_generated"` contract + `GenerationReceipt` dataclass is the missing half defined ahead of its emitter — the honest move.

---

## Concerns (non-blocking)

### CONCERN-1 — the `content_hash` binding is advertised but not enforceable on the delivery side (MODERATE)

`schema.py:210-211` claims `content_hash` "binds the generated artifact to the delivered one so a swap cannot pass," and the not-observable reason enum names the swap-check `CONTENT_HASH_MISMATCH`. But the actual join check (`join.py:71-79`) compares **`block_count`**, not `content_hash` — because `report_posted` (the live delivery event) **carries no `content_hash`** (`DeliveryReceipt` has no such field; the live event emits only `channel, block_count, abort_reason, trace_id, invocation_id`). So the real swap-protection today is **block-count equality**, which is weak: two distinct 42-block payloads would pass. The author was scrupulous about naming the `message_ts`/`permalink` delivery-side gap ("recorded as a gap the delivery emitter should close, not papered over"); the **content_hash delivery-side gap deserves the same explicit naming**, and the reason label arguably oversells ("content_hash_mismatch" fires on a block-count mismatch). Not blocking — it is forward-looking (the generation side is UV-P), and block_count is a reasonable interim bind — but the symmetry of honesty should be restored: name that `report_posted` must also emit a `content_hash` for the swap-proof to be real. **Route: EX-5 / the delivery emitter, and a docstring/label correction here.**

### CONCERN-2 — `human_in_loop` fail-safe default is correct; flag it as a load-bearing choice (LOW / positive)

`GenerationReceipt.from_event` defaults `human_in_loop` to **`True`** and `assembled_by` to `unknown` on absence (`schema.py:227-235`). This is the right, pessimistic default — an under-specified generation event reads as *not* machine-authored, so a malformed EX-5 emitter cannot accidentally clear limb (a). Recorded as a **positive** structural property the attester should rely on (and EX-5 should not "fix" by defaulting to machine).

---

## Unknown

### Unknown: does limb (a) require two *consecutive* observable occurrences, or two *distinct*?
- **Question**: `observe_limb_a` marks SATISFIED on **≥2 DISTINCT** observable invocations (`join.py:141-146`). Telos RUNG-2 language says "TWO **consecutive** occurrences" (`.know/telos/asana-native-insight-delivery.md:146-149`), whereas the shape's limb-(a) shape text says "two delivery occurrences" with no adjacency clause.
- **Why it matters**: If "consecutive" is load-bearing for the exec rung, a schema that accepts two non-adjacent machine occurrences (with a hand-assembled or aborted tick between them) would over-satisfy.
- **Evidence**: R-15 (L148-160) added the exec rung but did **not** restate an adjacency requirement for limb (a); the shape §EX-4 designs to "two delivery occurrences." The schema matches the ratified shape text exactly.
- **Suggested source**: `eunomia` `verification-auditor` (the limb-(a) attester) to confirm at attestation time whether adjacency is required; or operator via Q-1. Low-confidence, attester-routed — not a defect against the ratified shape.

---

## Scope notes

- **Shape §EX-4 exit criterion 3 (one-page capture protocol, `PROTOCOL-exec-rung-capture-{date}.md`) is OUT of this critique's scope** — it is the MAIN THREAD's document authored *for the operator* (shape §EX-4: "the capture protocol is a document, not code"; PR boundary "one — the receipt schema"). Not part of the receipt-schema PR under review. Flagged only as a wave dependency for the operator + eunomia.
- The **telos remains PROPOSED** (Q-5). This instrument **OBSERVES** limb (a); it does **not** grade the telos as met, and never sets the felt rung-4 line. Confirmed structurally (§ exit-2). The exec rung never substitutes for rung 4.

## Fence attestations

- **CR-1** (no live-board write): honored — read-only throughout; no Asana write.
- **CR-2** (`s3://autom8y-asr-verdicts` not read/listed): honored — I read `verdict_store.py`/`verdict_surface.py` **source** on origin/main only; the bucket was never read or listed. CloudWatch/AWS: I performed **no** AWS calls (the query path is hermetic; the census fixture is the author's own-hands transcription per its PROVENANCE.md).
- **CR-5** (no credential material): none encountered; did not `git log -p`/`git show` any of the fenced SHAs.
- **Monorepo trap**: honored verbatim — every `autom8y` monorepo read used `git show origin/main:<path>` (the working tree is on divergent branch `fix/wss-wildcard-scope-bypass-closure`). The **4b converse** holds: this repo's worktree working tree is authoritative for the schema under review.
- No infra mutation; no `git` write/commit/push.

## Self-attestation grades

- Exit-1 query re-run: **STRONG** — re-derived own-hands, exact match to the author's report.
- Exit-2 FS-5: **STRONG** — re-derived own-hands (keys, `additionalProperties:false`, single-value sentinel, teeth, rung-4 invariance, banned-field scan).
- NR-4 STANDS(narrowed): **STRONG on code** (whole-service grep + delivery-chain + abort-path + candidate-source source-reads own-hands); **MODERATE on the CR-2-fenced bucket contents** (inferred from `verdict_surface.py`/`verdict_store.py` code that it is the wrong construct, not read directly). Net: the narrowed negative stands.
- Self-attestation cap for this critique: **MODERATE** except where explicitly re-derived own-hands (above), per the disjoint-critic ceiling.

---

*Critic: `structure-evaluator` (arch), rite-disjoint. No HANDOFF sent; no git write. This file is the EX-4 critique exit artifact for the receipt-schema PR.*
