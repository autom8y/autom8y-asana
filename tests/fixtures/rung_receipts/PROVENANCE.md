# RUNG E limb (a) fixtures — provenance

## `asr_live_delivery_census.jsonl` — REAL, own-hands

15 real `report_posted` (delivery) events, transcribed verbatim from an
own-hands, read-only CloudWatch Logs Insights query run by the EX-4 author:

- **log group**: `/aws/lambda/autom8y-account-status-recon`
- **region**: `us-east-1`, account `696318035277`
- **queryId**: `7c59f3d8-821c-4b47-9034-f5d02a3d3fc8` (status Complete, 57 rows)
- **window**: ~60h ending 2026-08-13
- **read-only**: `logs start-query` / `logs get-query-results` only. No
  mutation, no invoke. CR-2-safe: the `s3://autom8y-asr-verdicts` bucket was
  never read or listed; this is a CloudWatch Logs read of the ASR lambda's own
  log group.

Distribution (real): 15 distinct `invocation_id`s, all delivered.
- 3 **readout-class** (`abort_reason: report_success`, `block_count: 42`) —
  real readouts posted to `#account-health`.
- 12 **abort-class** (`abort_reason: readiness_gate_abort`, `block_count: 3`).

The same census queried `event = "report_generated"` and returned **zero
rows** — hence NO generation fixture is drawn from live data. The generation
half is genuinely absent (this is the EX-4 founding finding, narrowed).

## The count-preserving swap fixture — DERIVED (CC-1 swap-detector teeth)

`test_swap_detector_closure.py` builds its swap fixture **in code** (helper
`_swap`), not as a checked-in JSONL, because it must be derived from a REAL
machine-generated occurrence for the teeth to mean anything. Derivation:

1. Call the actual EX-5 mechanism `readout.generation.render(...)` over the
   synthetic `tests/fixtures/readout/rows_response_item1a.json` → a
   `GeneratedOccurrence` with `blocks`, `text`, and a real `content_hash`
   (= `canonical_payload_hash(blocks, text)`, REC-001).
2. Deep-copy `blocks` and overwrite ONLY the `say_able_number` slot's `text` +
   `say_able_value` with a different, hand-pasted-style payload, and pair it with
   a different fallback `text`. This is the **count-preserving swap**: the block
   COUNT is unchanged (`len(swapped) == occ.block_count`) but the CONTENT differs,
   so `canonical_payload_hash(swapped, swapped_text) != occ.content_hash`.

Why count-preserving is the load-bearing property: the pre-CC-1 join only
compared `block_count`, so a same-length swap slipped through as `observable`
(RED capture `RED-verbatim.txt` / `RED-reconverge.txt`). A swap that CHANGED the
count would have been caught on the coarse block-count check and would NOT
exercise the content-hash teeth. The fixture is deliberately length-invariant so
the ONLY signal that can catch it is clause 4a (the content-hash comparison).

The swap is SYNTHETIC/derived: no live surface emits a swapped delivery, and no
defect is injected into production code — the swap is a deliberately-wrong INPUT
that the repaired join CORRECTLY REJECTS (`content_hash_mismatch`), paired with an
honest input that passes (`observable`). See `discriminating-canary-doctrine`.

## `readout_with_machine_generation.jsonl` — SYNTHETIC (teeth)

A single tick's delivery + a matching `report_generated` provenance event
(`assembled_by: machine`, `human_in_loop: false`). SYNTHETIC because no live
surface emits `report_generated` today (UV-P — EX-5 is the discharge site).
Used only to prove the join has two-sided teeth: it flips to OBSERVABLE when a
machine-generation receipt is present, and (with `human_in_loop: true`) stays
NOT_OBSERVABLE. It is NOT evidence that limb (a) is met.
