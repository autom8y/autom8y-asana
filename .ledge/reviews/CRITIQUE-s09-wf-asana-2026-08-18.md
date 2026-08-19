---
type: review
status: rendered
artifact_subtype: rite-disjoint-critique
author: structure-evaluator@arch (rite-disjoint critic; transcribed by the S-09 author seat as scribe — main-thread Write denied)
initiative: dic-comprehensive-landing
sprint: S-09 (W-F asana fleet-class cure lane)
date: 2026-08-18
verdicts:
  pr_a_autom8y_asana_382: GO-WITH-CONDITIONS (5 conditions, A-1..A-5)
  pr_b_autom8y_1647: GO-WITH-CONDITIONS (B-1 BLOCKING; B-2, B-3)
self_assessment_cap: MODERATE
---

# CRITIQUE — S-09 W-F asana lane (structure-evaluator@arch, rite-disjoint)

> Transcribed verbatim from the critic's verdict as relayed by the dispatching main
> thread 2026-08-18. Scribe = the S-09 author seat (seat-materialized general-purpose
> agent; the critic's harness cannot write .md files). Scribe additions are confined to
> the "Scribe notes" section at the end — the findings and conditions are the critic's.

## Verdict summary

Own-hands re-derivation performed by the critic: the author's RED-before was verified
REAL from a pristine `844bbde5` archive tree — **4 failed / 2 passed exactly, no
G-THEATER**; consumer census clean; S-COR-2 deferral CONCURRED.

- **PR A (autom8y-asana #382): GO-WITH-CONDITIONS** — 5 conditions (A-1..A-5).
- **PR B (autom8y/autom8y #1647): GO-WITH-CONDITIONS** — **B-1 BLOCKING**; B-2, B-3.

## Key findings

1. **A-1**: the `-> dict[str, Any]` annotation on `_omit_unobserved_sub_entities`
   ERASES the model's entire serialization JSON-schema (all 8 properties gone; critic's
   three-way probe: no-annotation → properties=['found','has_unit'] retained, wire
   byte-identical both arms; doesn't bite today only because `intake_resolve.py:51`
   mounts `include_in_schema=False`).
2. **A-2**: the 503 blast radius is real — `stages/resolve.py:85` unguarded +
   `orchestrator.py:224` critical → HTTP 500 to Calendly; mitigation exists (503 IS in
   the SDK's `retryable_status_codes`, autom8y-http `config.py:127-130`,
   backoff+jitter) but retries amplify Asana call volume exactly when Asana is
   unhealthy (the 429-storm lineage), and `SUBTASK_OBSERVATION_FAILED` has ZERO
   alarm/metric binding anywhere (SCAR-ALARM-BINDING-001 shape).
3. **A-3**: the author's residual-1 framing is INVERTED — `HOLDER_TYPES` is SEVEN
   holders created in one gather (`intake_create_service.py`); "listing EMPTY"
   (protected) needs all 7 un-indexed while "non-empty missing unit_holder" (still
   bites) needs one — the cure protects the rarer lag shape; compounding: the probe
   gates on `created.unit_gid` (Phase-3 Unit task) while `has_unit` reports the
   `unit_holder` business subtask — different objects.
4. **A-4**: the found=false wire also changed (both keys now omitted; pre-cure receipt
   at autom8y `CERT-intake-cf-1-gate2-2026-08-09.md:429`) — benign but missing from
   the disposition's §1 table.
5. **A-5**: "66/66" double-counts the F-9 suite (real: 60+6),
   `test_intake_resolve_models.py` is in-scope not adjacent,
   `test_intake_resolve_business_index.py` lives under `tests/unit/services/`.
6. **B-1 (BLOCKING)**: `cache_warmer.py:64` → `:1137` calls
   `push_status_to_data_service`; `_is_status_push_enabled()` is DEFAULT-ON
   (`gid_push.py:449-452`); gates 2+3 (`AUTOM8Y_DATA_URL`/`API_KEY` absent) ARE the
   current wall and the PR sets both → the apply un-gates the account-status push on
   all three warmer Lambdas, undeclared; the codebase's own lever is
   `STATUS_PUSH_ENABLED=false` (`status_push.py:1-30`); the Lambda lane's push set is
   narrower (`completed_entities ∩ PIPELINE_TYPE_BY_PROJECT_GID`, "mapped=[unit]" per
   `push_orchestrator.py`) so snapshot-replace last-writer-wins across two runtimes is
   the SCAR-SEAM1-PROBER-001 plane-split shape; vocab sync stays dark (DEFAULT-OFF
   idiom — the distinction was known and not swept).
7. **B-2**: post-deploy the WS-D ASANA leg goes quietly-partial — 1-column-keyed
   entities are structurally dropped (`gid_lookup` mints `pv1:{phone}` 2-segment,
   `extract_mappings_from_index` gates `len(parts)==3`, silent debug skip) and the
   mechanism is key ARITY, not project membership.

## Condition set (verbatim)

- **A-1**: delete the `-> dict[str, Any]` return annotation (verify:
  `model_json_schema(mode="serialization")` regains properties; `model_dump`
  byte-identical both arms).
- **A-2**: restate DISPOSITION §1 residual 3 with the real blast radius + SDK-retry
  mitigation + amplification cost; for the signal binding, EITHER add the metric/alarm
  binding in-PR if it fits the lane's fences, OR name an OWNED card (named owner +
  trigger, not "routed").
- **A-3**: re-derive residual 1 against the 7-holder gather shape or convert to an
  explicit UV-P named for discharge by S-04's live observation.
- **A-4/A-5**: paper corrections in the DISPOSITION (append-style corrections, never
  silent rewrites).
- **B-1 (BLOCKING)**: add `STATUS_PUSH_ENABLED = "false"` to `environment_variables`
  on ALL THREE warmer modules in #1647 — this preserves the status quo (the push is
  dark today); do NOT arm the dual-run — arming would need an operator word, which has
  not been given. State the choice + the critic's finding in the PR body.
- **B-2**: register the coverage-denominator gate (T2 census or map-coverage metric)
  with owner + trigger in the DISPOSITION as a precondition on READING the deadman
  post-deploy.
- **B-3**: keep the terraform-plan UV-P open until the CI plan posts; cite the posted
  plan when it does.

Also: fill the DISPOSITION §7 slot by reference to this critique file.

## Scribe notes (transcription fidelity)

- Path normalizations verified own-hands by the scribe at origin/main `676ec9be`:
  the critic's `stages/resolve.py:85` = `services/calendly-intake/src/calendly_intake/`
  `pipeline/stages/resolve.py:85` (unguarded `resolve_business_async` call); the
  critic's `orchestrator.py:224` = `.../pipeline/orchestrator.py:224`
  (`("resolve", resolve_stage(asana_client), True)` — critical). All other cited
  referents re-verified as given: `gid_push.py:447-451` default-on;
  `cache_warmer.py:64/:1137`; `intake_create_service.py:45-53` (7 holders) + `:440`
  (single gather) + `:200` (Phase-3 `unit_gid`); autom8y-http `config.py:127-130`
  (503 retryable); `CERT-intake-cf-1-gate2-2026-08-09.md:429` (pre-cure found=false
  wire carrying both explicit falses).
- Discharge state is recorded in `DISPOSITION-wf-asana-lane-2026-08-18.md` §8.

> Authored under seat-materialization: general-purpose agent preloaded verbatim with
> integrity-architect.md + pipeline-steward.md (dre unseated in dispatcher; pythia
> Option-5 2026-08-18) — scribe role only for this artifact; the critique content is
> structure-evaluator@arch's.
