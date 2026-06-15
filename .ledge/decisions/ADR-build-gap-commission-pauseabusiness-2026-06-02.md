---
type: decision
status: proposed
id: ADR-build-gap-commission-pauseabusiness
date: 2026-06-02
author: architect (10x-dev)
initiative: receiver-bulk-fanout-integration-readiness
consumer_visible: false
related:
  - ADR-honest-empty-200-serving-2026-06-02
  - ADR-warm-set-reconcile-and-converge-2026-06-02
tdd: .sos/wip/thermia/TDD-receiver-warm-convergence-2026-06-02.md
---

# ADR — Build-gap root cause + fix (Commission + PauseABusinessUnit)

## Status

PROPOSED. Commission: mechanism identified, fix is a consequence of warm-set reconcile (ADR-3).
PauseABusinessUnit: NEEDS A BOUNDED PRINCIPAL-ENGINEER SPIKE — root cause is empirically
undecidable read-only.

## Context + posture

DEFAULT-TO-REFUTED. I did NOT assert a "merge-write defect" until I read the build/persist path.
The path read REFUTES a merge-write *code* defect for Commission. Each project is adjudicated
separately below. Evidence is the P0 spike S3 probe (`receiver-frameless-gid-disposition.md`,
verified 2026-06-02) plus my read of `builders/progressive.py`, `section_persistence.py`,
`services/universal_strategy.py` (canonical `src/`).

## Commission `1201627461398630` — MECHANISM IDENTIFIED (no merge-write code defect)

**Evidence:** 10/10 sections complete, `total_rows=1480`, `last_verified_at=2026-06-02T08:48`
(current). Merged `dataframe.parquet` absent; 7 of 10 section parquets present (3 zero-row
sections wrote none).

**Path read (refutes a merge-write defect):** with a complete manifest,
`_check_resume_and_probe` sets `sections_to_fetch = manifest.get_incomplete_section_gids()` = `[]`
(`progressive.py:301`), so no sections are re-fetched and `_section_dfs` stays empty.
`_merge_section_dataframes` then reads the **persisted section parquets from S3** via
`merge_sections_to_dataframe_async` (`progressive.py:582-612`) → `total_rows=1480 > 0` → the
`if total_rows > 0:` gate at `progressive.py:771` is satisfied → `write_final_artifacts_async`
WOULD fire. **The merge-write code is correct.**

**Why is the frame absent then?** Because `build_progressive_async` was never run to completion
for Commission *since its sections completed*: Commission is a consumer-queried GID **absent from
the 23-key warm set** (CF-3), so it was never in the warm loop, and its sections completed via
progressive section-writes without a final completing build invocation reaching Step 6.

**Fix:** add Commission to the warm set (ADR-3 / WS-2). The next warm cycle invokes
`build_progressive_async` → resume merges the 7 persisted section parquets → `1480>0` → Step-6
write persists the merged frame. **No new code beyond ADR-3's reconcile.** This is the cheapest
correct fix and does not invent a defect the path read does not support.

**Residual risk (flagged):** if a Commission build DOES run and STILL fails to persist, there is a
latent merge/persist-boundary defect (e.g., a silent exception in `write_final_artifacts_async`
classified as `BuildResult.ERROR`) invisible to read-only inspection. The LIVE-probe acceptance
catches this.

## PauseABusinessUnit `1206330409791366` — NEEDS DEEPER SPIKE (do not guess)

**Evidence:** 1/4 sections complete (TEMPLATE=83 rows — the section the subclass
`SECTIONS={"ignore":("template",)}` EXCLUDES from the consumed frame); 3 sections stuck
`status=in_progress` since 2026-05-31; `last_verified_at=null` (never reached the prober, which
runs only `if manifest.is_complete()`, `progressive.py:350`).

**Two candidate mechanisms, NOT disambiguable read-only:**

1. **Stale-in-progress reclamation works; build just never re-ran.** The manifest already models
   this: `get_incomplete_section_gids(stale_timeout_seconds=300)` treats an `IN_PROGRESS` section
   older than 300s as incomplete/re-fetchable (`section_persistence.py:149-169`). Sections stuck
   since 05-31 are >>300s → the NEXT build re-fetches them. Under this mechanism Pause is like
   Commission: ADR-3 warm-set add fixes it for free.
2. **The 3 sections re-fail every attempt (per-section fetch error).** If
   `_fetch_and_persist_section` returns `False`/raises for those 3 on every run (deleted section,
   permission, data-shape error), they re-enter `IN_PROGRESS`/`FAILED` each build, the manifest
   never reaches `is_complete()`, no merge-write ever. The `SectionResult` outcome would be `ERROR`
   with a manifest `error` message (`progressive.py:1087,1097`) — the read-only signal needed to
   disambiguate, which the spike receipt did not capture.

**Why no fix is asserted:** the P0 spike states the live Asana read is genuinely blocked in this
repo (no iris agent file, no `ASANA_TOKEN`). Mechanism 1 (free fix) vs mechanism 2 (real
per-section defect) is empirically undecidable read-only.

**Decision: route a bounded P-E spike** — re-invoke `build_progressive_async` for
`1206330409791366`, OR read the manifest `sections[*].error` for the 3 stuck GIDs. If mechanism 1:
no extra work. If mechanism 2: the spike returns the section-level error and a targeted fix is
scoped then. Do NOT block ADR-3 on this.

**Framing nuance:** Pause's only built section (TEMPLATE) is consumer-*ignored*. A cleanly-built
Pause may post-merge have small/zero ACTIVE rows → Pause may legitimately resolve to
**honest-empty-200 (ADR-1)** even after a clean build. The spike must distinguish "3 sections
failed to build" (mechanism 2, real defect) from "3 sections built, no consumer-active rows"
(honest-empty, ADR-1 covers it).

## Alternatives considered

1. **Assert a merge-write defect and patch the merge/persist code.** Rejected — the path read
   shows the merge-write is correct for a complete manifest with rows; patching a non-defect would
   be guessing against evidence (DEFAULT-TO-REFUTED).
2. **Manually backfill the 3 frames out-of-band (one-shot script).** Rejected as the *fix* — it
   resolves the symptom for today's 3 GIDs but not the mechanism; any future GID that completes
   sections without a completing build invocation regresses. The warm-loop fix (ADR-3) is the
   durable mechanism. (A one-shot backfill is acceptable as an *operational* expedient AFTER the
   mechanism is fixed, if cutover timing demands it — but it is not the architectural decision.)
3. **Guess Pause is mechanism 1 and ship ADR-3 only.** Rejected — if it is mechanism 2, the
   re-gate will fail on Pause and burn a cycle. The bounded spike is cheaper than a failed re-gate.

## Consequences

- Commission's build-gap closes as a consequence of ADR-3 (zero marginal code).
- Pause's disposition is deferred to a bounded spike that returns a definite mechanism + (if
   needed) a scoped fix — no guessed code lands.
- The acceptance criteria are LIVE probes (Commission serves 1480 rows; Pause serves a valid
   frame OR honest-empty-200 with the spike naming which mechanism), so a latent defect cannot
   pass silently.

## Reversibility

Two-way door — both fixes are warm-loop/registry-driven (ADR-3) or a bounded spike; no
irreversible state change introduced by this ADR itself.
