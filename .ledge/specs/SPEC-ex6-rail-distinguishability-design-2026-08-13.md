---
type: spec
status: proposed
---

# SPEC — EX-6 rail distinguishability & delivery (design limb)

> Wave: exec-insight-delivery · Sprint: EX-6 (WS-3) · Rite: 10x-dev / principal-engineer
> Date: 2026-08-13 · Scope: **DESIGN LIMB ONLY** (parallel with EX-5; receipt limb sequenced)
> Governing inputs: `RAILS-insight-delivery-verified-2026-08-12.md` §5-§6 ·
> `.sos/wip/frames/exec-insight-delivery.shape.md` §EX-6 (L414-472) ·
> `RULING-operator-morning-set-2026-08-13.md` R-7/R-14/R-15

This spec documents the executable contract shipped in
`src/autom8_asana/observability/rail_delivery/`. It is a forward-looking artifact
for the **EX-5 generator** (which fills the shape), the **application limb** (which
wires it into the monorepo ASR service), and the **rite-disjoint critic**. It is
not a session report — the contract is the code; the module docstrings carry the
per-line RAILS/shape provenance.

## 1. What the design limb owns (and what it does NOT)

DOES (built + proven here against SYNTHETIC block payloads, no live post):
- The four distinguishability duties D-1..D-4 as executable, receipted checks.
- The block budget: an EXPLICIT, stated budget + an overflow contract that never
  truncates silently.
- The delivery-receipt SHAPE EX-4's join consumes, carrying a real `content_hash`.

Does NOT (out of scope, explicitly deferred):
- UV-P-C-3 (exit crit 3 — Phase-3 receipt limb): needs EX-5's real postable payload.
- Any live Slack post.
- Any monorepo change. The live ASR `report_posted` chain lives in the monorepo
  (`services/account-status-recon/**`); it is not touched. See §7.

## 2. Homonym guard — "D-4"

Throughout THIS spec, **D-4** = the RAILS D-1..D-4 fallback-`text` duty
(RAILS…:607). It is NOT the operator morning-set gate-(b) ruling (which is a
different lineage; R-7 rules Slack delivery stays autonomous — Asana writes only).

## 3. Distinguishability — D-1..D-4 (`distinguishability.py`, `occupants.py`)

`#account-health` is a *co-tenanted* channel (not dark): the readiness-abort alert
posts 6×/day and both live occupants open with `"Account Status Reconciliation"`.
The inherited rule (`report.py:70-76` D-6, quoted at RAILS…:591-596) is **one
token, one meaning, channel-wide**. The reserved tokens each occupant already
claims are encoded in `DEFAULT_ACCOUNT_HEALTH_OCCUPANTS` (`occupants.py`,
provenance RAILS…:576-607).

| Duty | Surface | Rule | Failure mode |
|---|---|---|---|
| **D-1** | header block | MUST NOT begin (normalised) with a reserved header prefix | visible — largest token |
| **D-2** | identity glyph | MUST carry a distinct glyph unused in-channel; no alert glyph may leak anywhere | reads as an alert |
| **D-3** | context footer | MUST name a distinct producer, not `account-status-recon | readiness gate` | mis-attributes the readout |
| **D-4** | fallback `text` | MUST be non-empty and not open like the incumbent | **SILENT** — notification/mobile line |

**Joint sufficiency (exit crit 1).** `evaluate()` returns
`distinguishable = D1 ∧ D2 ∧ D3 ∧ D4`, and names `missed_surfaces`. Three-of-four
is *not* 75% distinguishable — it is indistinguishable at the surface it missed.
`test_three_of_four_is_indistinguishable_not_seventy_five_percent` is the teeth.

**D-4 at the surface it governs (exit crit 2).** `check_d4_fallback_text` takes
the fallback `text` and NOT the blocks. `test_d4_fails_at_the_text_surface_even_
when_desktop_blocks_are_distinct` proves a readout with a perfectly distinct
desktop render but an incumbent-shaped notification line FAILS D-4 — a desktop-
blocks-only receipt would miss it. The passing D-4 receipt's `detail` attests it
inspected the notification surface directly.

**`:scissors:` reconciliation.** D-2 forbids the *identity* glyph from being
`:scissors:` (a readout headed by scissors reads as a truncation) and forbids
alert glyphs anywhere — but it TOLERATES `:scissors:` on a non-header truncation
marker, because `:scissors:` means "truncation" channel-wide (one token, one
meaning). This lets the overflow marker (§4) coexist with D-2.
`test_d2_tolerates_scissors_on_a_non_header_truncation_marker` +
`test_overflowing_readout_self_marks_and_stays_distinguishable` are the compose
proofs.

## 4. Block budget & overflow (`block_budget.py`)

Two inherited facts (RAILS…:643-708): Slack truncates at **50 blocks with no
marker of any kind**, and the budget is **per message, not per channel**.

- **Per message, not per channel (exit crit 5).** `BlockBudget` and `plan()` take
  ONLY the readout's own framing + item count. No channel/traffic parameter may
  enter — enforced structurally by
  `test_budget_signature_has_no_channel_or_cotenant_input`. Co-tenancy (§3) and
  the ceiling (§4) are independent problems.
- **Explicit budget (exit crit 4).** `BlockBudget` states `framing_blocks`,
  `blocks_per_item`, and derives `item_ceiling` — a stated number, never emergent.
  `available_body_blocks = max_blocks(50) − reserved_blocks(10) − framing_blocks`;
  `item_ceiling = (available_body_blocks − 1 marker reserve) // blocks_per_item`.
- **Overflow is explicit and observable (exit crit 4).** `plan()` never truncates
  silently: on overflow it caps `shown_items` at the ceiling and sets
  `truncation_marker_present=True`. `truncation_marker_block()` emits a
  complete-by-construction marker: `:scissors: Showing k of n. The counts above
  are complete; …`. Completeness is carried by the COUNTS, not by a drill-out
  pointer — the incumbent's pointer currently 404s (NF-1, owned by S5,
  RAILS…:694-708), so `drill_pointer` defaults to absent.
- **Hard-ceiling invariant.** `rendered_block_total ≤ 50` for any item count, by
  construction — fuzzed 0..300 across blocks_per_item ∈ {1,2,3} in
  `test_rendered_total_never_exceeds_the_hard_slack_ceiling`.

## 5. Delivery-receipt shape + EX-4 CONCERN-1 (`delivery_receipt.py`)

EX-4's `GenerationReceipt.content_hash` exists to "bind the generated artifact to
the delivered one so a swap cannot pass," but EX-4's `DeliveryReceipt` (projected
from `report_posted`) carries **no** `content_hash` — so the swap-check has only
one side (**CONCERN-1**).

This module ships a `DeliveryReceipt` that mirrors EX-4's `report_posted` wire
shape field-for-field AND adds `content_hash`, computed by `content_hash(blocks,
text)` — a canonical (sorted-key, whitespace-free) sha256. Both halves carrying
the same canonical hash let EX-4 assert `delivery.content_hash ==
generation.content_hash`; a swapped/hand-edited payload flips the hash and cannot
pass (`test_swapped_payload_fails_the_swap_check`).

`DELIVERY_RECEIPT_JSON_SCHEMA` is the exact wire fragment (EX-4 delivery fields ∪
`content_hash`). **Coordination (not an edit to EX-4):** EX-4's
`RUNG_E_LIMB_A_RECEIPT_JSON_SCHEMA.delivery` sub-object should gain
`content_hash` (type string) to consume this field. That edit belongs to EX-4 /
observability-engineer on the receipt limb; this module supplies the field, the
canonical function, and the swap-check.

## 6. Readout shape (`readout.py`)

`Readout` + `render()` compose §3 and §4 into one artifact: the buildable shape
EX-5 targets. `render()` produces `(blocks, text)` + a `BudgetReceipt` + a
`DistinguishabilityReceipt`; `RenderedReadout.deliverable = distinguishable ∧
within_ceiling`. `default_budget()` states framing = header+summary+divider+footer
= 4 blocks, and `test_*_render_accounting` proves the stated budget matches the
actual render (no drift).

## 7. Monorepo boundary — NO HALT

The design limb does **not** require a monorepo change and does not HALT. Negative
swept per §A.3:
- **Validators/budget/receipt are standalone** — nothing here imports or edits
  `services/account-status-recon/**`; all three surfaces are proven against
  synthetic payloads.
- **D-2 completeness NARROWS:** the reserved-alert set is seeded with the
  verbatim-known `:warning:` (==Severity.HIGH); the full SDK severity glyph set is
  a monorepo fact (UV-P below). D-2 is complete for the known tokens and
  extend-only (`ChannelOccupants.with_sdk_severity_glyphs`) — the mechanism works;
  the negative-space of D-2 is only as complete as the seeded set.
- **Application limb WILL touch the monorepo + EX-4 schema** (out of scope here):
  wiring the readout into ASR's `send_blocks` egress, emitting `content_hash` on
  `report_posted`, and adding `content_hash` to EX-4's delivery schema. Surfaced
  as coordination, not a HALT.

## 8. Carried UV-Ps

- `[UV-P: exhaustive ASR SDK severity glyph set beyond :warning: | METHOD: read
  autom8y_reconciliation report.py _severity_emoji at origin/main (monorepo) |
  REASON: SDK not importable in autom8y-asana; monorepo out of scope. Reserved-
  alert set is seeded + extend-only.]` — narrows D-2 negative-space completeness.
- **UV-P-C-3** (unchanged, NOT discharged here): a readout-class payload posts to
  `#account-health` observed via `report_posted`/`block_count`. Needs EX-5's real
  payload + a live post; Phase-3 receipt limb.
- **UV-P-S3-2** (unchanged): whether a second bot identity exists — a Slack-
  workspace fact, not assumed. The design does not depend on one.

## 9. Test map

| Suite | Proves |
|---|---|
| `tests/unit/test_rail_distinguishability.py` | D-1..D-4 two-sided; joint sufficiency; D-4 at the text surface |
| `tests/unit/test_rail_block_budget.py` | explicit budget; overflow never silent; per-message-not-per-channel; ≤50 invariant |
| `tests/unit/test_rail_delivery_receipt.py` | content_hash determinism/sensitivity; CONCERN-1 swap-check; EX-4 wire-shape compat |
| `tests/unit/test_rail_readout_shape.py` | budget+distinguishability compose; render accounting matches stated budget |

Run: `cd <worktree> && export PYTHONPATH="$PWD/src" && python -m pytest
tests/unit/test_rail_*.py -q` → 40 passed. ruff + mypy clean.
