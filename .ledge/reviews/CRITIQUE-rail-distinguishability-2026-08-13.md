---
type: review
status: accepted
artifact: CRITIQUE
subject: EX-6 rail distinguishability & delivery — DESIGN LIMB
wave: exec-insight-delivery
sprint: EX-6 (WS-3)
author_under_review: 10x-dev / principal-engineer (co-seat: sre / observability-engineer — Phase-3 receipt limb)
critic_rite: eunomia (verification-auditor) — operator-ruled substitute for the non-dispatchable hygiene/audit-lead
critic_disjointness: disjoint from BOTH 10x-dev (author) AND sre (co-seat) ✅
date: 2026-08-13
worktree: .knossos/worktrees/ex-6-rail-distinguishability
worktree_head: afdad5edaf9bc6a5603558cf5d509309e7a5544d (off origin/main afdad5ed)
self_attestation_ceiling: MODERATE (self-ref-evidence-grade-rule); STRONG only where re-derived own-hands
verdict: DESIGN-LIMB LANDABLE — receipt limb correctly HELD on Phase-3 / monorepo / operator
---

# CRITIQUE — EX-6 rail distinguishability (design limb)

Rite-disjoint critic: **eunomia / verification-auditor**. The shape (§EX-6) names
`hygiene / audit-lead` as the disjoint critic and **disqualifies `sre` as critic
because it co-authors** the receipt limb; audit-lead is non-dispatchable, so this
seat is the operator-ruled substitute. Eunomia is disjoint from BOTH the author
(10x-dev) and the co-seat (sre) — the critic-substitution rule satisfied on a real
co-seat, not a hypothetical.

Every leg below was **re-derived with my own hands** (three-evidence-leg
discipline): (a) the keystones re-run UNCACHED, (b) fresh discriminating teeth I
constructed myself — NOT the author's tests, (c) the module surfaces exercised
directly via a Python session I drove. The author's 40 tests and the spec were
treated as CONTEXT, never as EVIDENCE.

---

## Verdict at a glance

| # | Verify item | Verdict |
|---|---|---|
| 1 | Re-run UNCACHED → 40/40 | **PASS** — `40 passed in 0.20s` (`-p no:cacheprovider`) |
| 2 | D-1..D-4 joint + D-4 at fallback-text surface (own construction) | **PASS** — own render()-path teeth, two-sided |
| 3 | Block budget ≤50 + overflow never silent + no channel param (own fuzz) | **PASS** — 4000 random draws + boundary + signature fence |
| 4 | Delivery-receipt content_hash swap-check (own construction) | **PASS** — swap fails, canonicalisation stable, field-set == EX-4 ∪ content_hash |
| 5 | No monorepo import, no live Slack post, no git | **PASS** — stdlib + own submodules only; account-status-recon hits are string DATA |
| — | D-2 NARROWS honest? / UV-P-C-3 not overclaimed? / UV-P-S3-2 handled? / Phase-3 dep surfaced? / C-7·R-7? | **All CONFIRMED** (below) |

**DESIGN-LIMB VERDICT: LANDABLE.** Exit criteria 1, 2, 4, 5, 6 are met and
own-hands-verified. Criterion 3 (UV-P-C-3) is correctly NOT claimed — it is held
on the Phase-3 receipt limb (needs EX-5's real payload + a live post). No
monorepo mutation, no live Slack post, no infra mutation.

---

## Leg (a) — keystone re-run UNCACHED [STRONG, own-hands]

```
cd <worktree> && export PYTHONPATH="$PWD/src"
python -m pytest tests/unit/test_rail_*.py -p no:cacheprovider -q
→ 40 passed in 0.20s
```

Function count re-counted by hand from source (not inherited): 15 + 12 + 8 + 5 =
**40** `def test_*` across the four suites. The venv editable-install would have
resolved `autom8_asana` to the MAIN tree; I confirmed `PYTHONPATH="$PWD/src"`
resolves it to the worktree
(`.knossos/worktrees/ex-6-rail-distinguishability/src/autom8_asana`) before every
run. ruff `All checks passed!`; mypy `Success: no issues found in 6 source files`
— the spec's "ruff + mypy clean" claim (SPEC §9) verified own-hands.

## Leg (b) — own-construction teeth [STRONG, own-hands]

I constructed teeth in defect classes the author's suite does **not** occupy, ran
them through a Python session (no files written to the tree — all via stdin; tree
confirmed unpolluted afterward). **28 own-hands assertions, all GREEN.**

### D-4-at-the-fallback-text teeth (item 2)

The author's D-4 teeth (`test_rail_distinguishability.py:131`) collide the text
via `evaluate()` on **hand-built** blocks. My fresh construction drives the full
`render()` **compose path** with a PRISTINE desktop render (distinct header,
distinct `:chart_with_upwards_trend:` glyph — not the author's `:bar_chart:`,
distinct footer) but an incumbent-shaped notification line
(`"Account Status Reconciliation aborted at readiness gate for 3 units."`). The
author's render()-path tests only ever collide on the HEADER — never on text —
so this is genuinely outside the author's ledger.

Result: desktop D-1/D-2/D-3 all PASS; **D-4 FAILS at `surface == "fallback_text"`**
(`distinguishability.py:300-344` takes `text`, never the blocks), naming
`collided_with == "account status reconciliation"`; the joint verdict is
`distinguishable == False` with `missed_surfaces == ("fallback_text",)` — it names
the missed surface, it does **not** report "75%" (`evaluate()` is the AND of four,
`distinguishability.py:347-371`). Two-sided: the same render with a distinct text
returns `distinguishable == True`, `missed_surfaces == ()`. Surface-independence
confirmed: a header-only collision misses `("header",)` while D-4 still passes —
the surfaces are attributed independently, so "3-of-4" always names WHICH one.

⚠ Homonym cleared: this is the **RAILS `:607` fallback-`text` duty**, not the
morning gate-(b) ruling. The build guards the homonym explicitly (SPEC §2); R-7
(`RULING…:88-99`) is a different lineage and rules **Slack delivery stays
autonomous** — consistent with, and not conflated by, this D-4.

### Block-budget teeth (item 3)

Author fuzzed `range(0,300)` × bpi∈{1,2,3}. My fuzz: **4000 random draws** of
`(framing∈[0,39], blocks_per_item∈[1,12], total_items∈[0,5000])`, plus an explicit
overflow-boundary sweep at `item_ceiling` and `item_ceiling+1` for
framing∈{0,4,10,25,39} × bpi∈{1,2,5}. Findings:
- `rendered_block_total ≤ 50` held for **all 4000** draws (`block_budget.py:146`
  reserves exactly one marker block; `:92` holds one back in `item_ceiling`).
- **Overflow is never silent**: every `truncated` plan carried
  `truncation_marker_present == True`; at exactly `item_ceiling` no marker, at
  `ceiling+1` a marked truncation still ≤50. `complete iff dropped==0` exact.
- **Structural per-message fence** (`plan`/`BlockBudget` cannot take a
  channel/co-tenant param): `BlockBudget.__dataclass_fields__ ==
  {framing_blocks, blocks_per_item, max_blocks, reserved_blocks}` and
  `signature(plan).parameters == {budget, total_items}`. None of
  `{channel, cotenant, co_tenant, channel_traffic, other_blocks, occupants,
  traffic, siblings}` appears in the budget API OR in `truncation_marker_block`.
  The per-message/per-channel independence (RAILS `:655-660`, shape exit crit 5)
  is enforced by the type, not by convention.

### content_hash swap-check teeth (item 4)

`content_hash` (`delivery_receipt.py:53-68`) is canonical JSON (sorted keys,
whitespace-free) → `sha256:`. My constructions:
- Positive control: matching delivered payload → `content_hash_matches` True.
- **Hand-swap**: a single-digit body edit ("3 offers moved" → "4 offers moved")
  → `content_hash_matches` **False**. A swapped payload cannot pass — the exact
  CONCERN-1 guarantee (`delivery_receipt.py:130-137`).
- Fresh angle the author didn't test — **canonicalisation stability**: a
  semantically-identical payload with dict keys in a DIFFERENT insertion order
  hashes IDENTICALLY (no false-positive swap), while a trailing-space text edit
  flips the hash (byte-sensitive). Both behaviours are load-bearing for a
  cross-sprint contract and both hold.
- **Field-set mate**: `DeliveryReceipt.to_dict()` keys ==
  `{invocation_id, channel, block_count, delivered_at, outcome, trace_id,
  message_ts, permalink}` ∪ `{content_hash}`. I read EX-4's field set directly
  from `git show origin/main:src/autom8_asana/observability/rung_receipts/schema.py`
  (its `DeliveryReceipt`, lines ~172-179) — NOT from the author's mirror constant.
  `outcome` is a bare wire-string ("readout") mirroring EX-4's `DeliveryOutcome`
  StrEnum value, so the wire form is compatible.

## Leg (c) — surfaces exercised directly [MODERATE→STRONG on the exercised paths]

There is no user-facing CLI at this altitude (design limb; nothing posts). The
"surface" here is the Python API a downstream consumer (EX-5, EX-4 join) touches.
I exercised `render()`, `evaluate()`, `plan()`, `content_hash()`,
`content_hash_matches()`, `DeliveryReceipt.for_payload().to_dict()`, and
`ChannelOccupants.with_sdk_severity_glyphs()` directly in my own session and read
their returns verbatim (above). No leg was inherited.

---

## NR-6 / negative-family sweep — the EX-6 negatives

The author asserted a NEGATIVE — *"the design limb requires no monorepo change"* —
STANDS with a **D-2 NARROWS**. My rulings:

### D-2 NARROWS — CONFIRMED genuine (STANDS, narrowed) [STRONG, own-hands]

Refuter run: is `sdk_severity_glyphs_complete=False` a false "complete" wearing a
UV-P costume? **Refuted — it is honest.** Own-hands proof:
- With the seed-only default (`occupants.py:117-127`), a REAL ASR severity glyph
  outside the verbatim-known seed (I used `:rotating_light:`) is **NOT caught** —
  D-2 PASSES. That is the exact negative-space gap the UV-P names
  (`occupants.py:39-45`), and the PASS `detail` is honestly annotated
  `"…verbatim-known seed, not the full SDK severity set — see occupants UV-P"`
  (`distinguishability.py:250-257`). It does **not** claim "complete."
- `with_sdk_severity_glyphs({":rotating_light:"})` (`occupants.py:102-112`) is a
  strict **union** (`reserved_alert_glyphs | frozenset(glyphs)`) that flips
  `sdk_severity_glyphs_complete=True` — extend-only, never removes; the `:warning:`
  seed is preserved; the original frozen occupants are unmutated. After folding,
  the SAME glyph IS caught (D-2 fails) and the PASS-note drops.

Ruling: D-2 completeness is a genuine carried UV-P, not a false "complete"; the
extend-only path is honest and the application limb can pass the authoritative set
without a code change. **The mechanism is complete for the known token; the
negative-space is only as complete as the seed — and the code says so.**

### UV-P-C-3 — correctly NOT discharged (no overclaim) [STRONG]

Exit crit 3 (a readout-class payload posts to `#account-health`, observed via
`report_posted`/`block_count`) is the Phase-3 receipt limb — it needs EX-5's real
payload + a LIVE post. The design limb does NOT claim it: `__init__.py:9-11`,
SPEC §1/§8, and the frame entry-criterion E2 all mark it out of scope. I grepped
the limb for any live-post surface (`WebClient`, `chat_postMessage`, `.post(`,
`requests`, `httpx`, `slack_sdk`) → **NONE**. No overclaim.

### UV-P-S3-2 (second bot identity) — UNKNOWN, correctly NOT resolved either way [PASS, NR-6(c)]

The design neither assumes a second bot identity EXISTS nor asserts one does NOT.
SPEC §8 records it as "a Slack-workspace fact, not assumed. The design does not
depend on one," and the shape's "must not: assume a second bot identity exists"
is honoured. No code path branches on bot identity. NR-6(c) satisfied — the
UNKNOWN is preserved as UNKNOWN.

### The Phase-3 / application-limb monorepo dependency — surfaced as coordination, NOT absorbed [PASS]

The author surfaces (SPEC §5/§7, `delivery_receipt.py:24-30`,146-148) that the
application limb WILL: (i) wire the readout into ASR's `send_blocks` egress,
(ii) emit `content_hash` on `report_posted`, (iii) add `content_hash` to EX-4's
delivery schema. Each is named as **out-of-scope coordination**, explicitly NOT an
edit to EX-4's frozen schema and NOT a monorepo change in this PR. I verified the
non-absorption: the limb imports nothing from `services/account-status-recon/**`
and edits no EX-4 file (the `DELIVERY_RECEIPT_JSON_SCHEMA` fragment,
`delivery_receipt.py:144-170`, is a standalone fragment, not a splice). Correctly
surfaced, not silently absorbed.

### C-7 / R-7 — no human addressed; rail autonomy is the PRODUCER's [PASS]

No code path addresses a human reader. The only readout-authored prose that could
is the truncation marker (`block_budget.py:180-186`): `":scissors: Showing k of n.
The counts above are complete; N item(s) are not shown here."` — factual/descriptive,
no `@mention`, no "you", no directive, no operator-attributed address. R-7
(`RULING…:88-99`) rules Slack delivery stays autonomous (Asana writes only); the
autonomy exercised here is the **producer's** (authoring a distinguishable message
shape), not authority to address a reader on the operator's behalf (C-7,
shape §EX-6 "must not"). Clean.

---

## §A.3 reporting duty

**Refuters swept, with returns (incl. NULLs):**

| Refuter | Return |
|---|---|
| Does D-4 secretly read the desktop blocks (so a blocks-only receipt would pass)? | **NULL** — `check_d4_fallback_text` takes `text`; own render()-path teeth confirm a pristine-blocks + dirty-text readout FAILS D-4 |
| Is "3-of-4" reported as 75% anywhere? | **NULL** — `evaluate()` is the AND; `missed_surfaces` names the surface; no ratio surfaced |
| Can any `(framing,bpi,total)` breach 50 blocks or truncate silently? | **NULL** — 0/4000 breaches; every truncation marked |
| Can a channel/co-tenant param enter the budget? | **NULL** — signature fence: not in fields, params, or the marker builder |
| Can a swapped payload pass content_hash? | **NULL** — single-digit swap → False; canonicalisation stable |
| Is `sdk_severity_glyphs_complete=False` a false "complete"? | **NULL (refuted)** — an unseen severity glyph provably slips the seed; PASS is annotated as narrow; extend-only union honest |
| Does the receipt field-set actually mate with EX-4 read from origin/main? | **NULL** — keys == EX-4's 8 ∪ {content_hash}, verified against `git show origin/main:…schema.py` |
| Any monorepo import / live post / git / subprocess / infra mutation? | **NULL** — grep NONE; imports are stdlib + own submodules |
| Does the tree get polluted by the build or my probes? | **NULL** — build is new files only (one out-of-scope tracked edit: the author's `principal-engineer/MEMORY.md`); my probes wrote nothing |

**The hop one past, named concretely** (what the NEXT seat must verify, that this
limb does NOT and CANNOT):
1. **`content_hash` parity with EX-5's generation side** — the swap-check is only
   meaningful if EX-5's `report_generated.content_hash` hashes the payload with
   the SAME canonical function. The contract is stated (`delivery_receipt.py:53-61`)
   but EX-5's generator does not yet exist; parity is unproven until EX-5 lands and
   calls an identical `content_hash(blocks, text)` over the same `{blocks,text}`
   object. **This is the load-bearing cross-sprint risk.** If EX-5 canonicalises
   differently (e.g., includes a timestamp, or hashes pre-render), every honest
   delivery reads as a swap.
2. **EX-4 schema splice** — `RUNG_E_LIMB_A_RECEIPT_JSON_SCHEMA.delivery` must gain
   `content_hash` (string). Until observability-engineer makes that edit on the
   receipt limb, EX-4's join still has one-sided hash and CONCERN-1 remains open in
   EX-4 even though this limb closed its half.
3. **UV-P-C-3 live post** — a real SDK-built multi-block payload posted to
   `#account-health` and read back via `report_posted`/`block_count` (Phase-3).
4. **The full ASR SDK severity glyph set** — `with_sdk_severity_glyphs(…)` must be
   called at application time with the real `_severity_emoji` mapping read from the
   monorepo `report.py`; until then D-2's alert-glyph negative-space is `{:warning:}`
   only.

**Refuter I ADDED (not in the author's suite):** content_hash **canonicalisation
stability** — a dict-key-reordered but semantically-identical payload must hash
IDENTICALLY (else innocent re-serialisation reads as a swap). The author tested
sensitivity (flips on change) but not stability (no false-positive on reorder). I
constructed it; it holds. This strengthens, not weakens, the CONCERN-1 closure.

**Verdict: STANDS with D-2 NARROWS.** The author's negative — "the design limb
requires no monorepo change" — STANDS. Corrected scope: it stands **for the design
limb's own three surfaces** (validators, budget, receipt shape), all proven against
synthetic payloads; it does NOT extend to the application limb, which WILL touch the
monorepo (`send_blocks`, `report_posted.content_hash`) and EX-4's schema — and that
is correctly surfaced as coordination, not smuggled into this PR. The single honest
NARROWS is D-2's severity-glyph negative-space, carried as a live UV-P with an
extend-only discharge path.

---

## Landability determination

**The DESIGN-LIMB code is LANDABLE**, with the receipt limb correctly HELD on
Phase-3 / monorepo / operator:

- Exit crit 1 (D-1..D-4 jointly, per-duty receipts, 3-of-4≠75%): **MET**.
- Exit crit 2 (D-4 at the fallback-text surface): **MET** — own-hands two-sided.
- Exit crit 3 (UV-P-C-3 discharged): **HELD** — Phase-3 receipt limb; correctly
  not claimed. Not a defect of this limb.
- Exit crit 4 (overflow explicit, never silent): **MET** — own fuzz.
- Exit crit 5 (per message, not per channel): **MET** — structural signature fence.
- Exit crit 6 (delivery receipt EX-4 consumes): **MET** — field-set mates; the
  EX-4 schema splice + EX-5 hash-parity are the named hops for the next seat.

Blocking dependencies that must NOT be treated as landed by this PR: the EX-4
schema splice, EX-5 content_hash parity, the live UV-P-C-3 post, and the full SDK
severity set. All four are honestly carried, none silently absorbed.

**Fences honoured:** no live-board write; `s3://autom8y-asr-verdicts` not read; no
credential material; no `git log -p` / `git show` of the fenced SHAs; no monorepo
read (the `autom8y` monorepo trap path was never touched — all reads were in THIS
autom8y-asana tree, working-tree-authoritative per 4b converse); no infra mutation;
no live Slack post; C-9 respected. No git write/commit/push performed.

---

## Self-attestation grade

**MODERATE ceiling** per `self-ref-evidence-grade-rule` — a knossos rite (eunomia)
attesting a knossos-fleet surface built by another knossos rite (10x-dev). In-fleet
rite-disjointness (eunomia ≠ 10x-dev ≠ sre) lifts this above pure self-attestation:
I re-ran the keystones uncached (leg a), constructed 28 fresh discriminating
assertions outside the author's ledger (leg b), and exercised every surface directly
(leg c) — treating the author's 40 tests and spec as CONTEXT, never EVIDENCE
(dispatcher-critic-degeneracy guard). STRONG language is used ONLY for the
own-hands-re-derived facts (the uncached 40/40, the fuzz counts, the swap-check, the
D-2 narrowness demonstration); the cross-sprint parity claims (EX-5 hash, EX-4
splice) are held at their honest UV-P altitude, not attested.
