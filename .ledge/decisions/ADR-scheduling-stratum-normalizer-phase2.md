---
type: decision
decision_subtype: adr
id: ADR-scheduling-stratum-normalizer-phase2
artifact_id: ADR-scheduling-stratum-normalizer-phase2
schema_version: "1.0"
status: accepted
lifecycle_status: accepted
date: "2026-06-30"
rite: 10x-dev
initiative: "scheduling-stratum + enrollment fleet primitive — Phase 2 (asana normalizer-seam)"
deciders:
  - principal-engineer (10x-dev, N3/Phase-2 build)
consulted:
  - architect (scheduling-stratum-stratum-enrollment-primitive ARCH adjudication, PASS-WITH-CONDITIONS/MODERATE)
  - autom8y-data Phase-1 (PR #218 sync + enrollment contract)
informed:
  - qa-adversary (N5 /qa external critic — re-fires the option-(c) probe + grep-zero fitness)
supersedes: []
superseded_by: []
---

# ADR: Cascade-change invalidation = option (c) periodic divergence-reconciliation sweep

## Status

Accepted (Phase-2 build-time decision). Merge-ready; NOT merged, NOT live. The
snapshot-push and the reconciliation sweep both ship DARK (default-off gates).

## Context

The scheduling-stratum primitive splits the legacy `CustomCalUrl` cascade into two
planes (architecture-adjudicated):

- **stratum** — a freshness-stamped projection of the provider identity, resolved by
  the asana normalizer and pushed to autom8y-data
  (`POST /api/v1/scheduling-stratum/sync`, PR #218).
- **enrollment** — the operator-attested posture (append-only override log,
  `POST /api/v1/scheduling-enrollment/override`, PR #218), carrying
  `cascade_changed_at` + `requires_reattestation`.

A cascade SOURCE field can change underneath an existing operator override (e.g. an
office migrates from Acuity to Calendly). When that happens the freshly-resolved
stratum snapshot diverges from the enrolled `override_stratum`, and the override
silently goes stale. The primitive needs an **invalidation mechanism** that detects
this divergence and forces re-attestation — fail-closed, so a stale override never
silently serves the wrong provider.

Three mechanisms were on the table (the architect's CH-DELTA-01 framing):

- **(a) per-guid transactional coupling** — at snapshot-push time, write-through into
  the enrollment table in the same logical transaction as the stratum upsert.
- **(b) batch-level retry-with-backoff** — couple invalidation to the push batch, with
  a bounded retry envelope on partial failure.
- **(c) periodic divergence-reconciliation sweep** — a standalone, scheduled pass,
  INDEPENDENT of the snapshot-push path, that reads the already-synced stratum +
  enrollment per office and back-fills divergences.

## Decision

**Adopt option (c).** Cascade-change invalidation is a standalone periodic
reconciliation sweep (`services/scheduling_enrollment_reconcile.py`), decoupled from
the snapshot-push path entirely.

Detection (PURE `detect_divergence`): for each office carrying BOTH a fresh stratum
snapshot and an enrollment override, divergence fires when the snapshot stratum no
longer equals the enrolled `override_stratum` AND the snapshot was synced strictly
after the override was written (`synced_at > override.created_at`). The temporal
guard prevents a just-written override from being immediately re-flagged on the next
pass (idempotent under repeated runs).

Back-fill (fail-CLOSED): on divergence the sweep APPENDS a new override
(`actor=operator`, `override_stratum=<the operator's EXISTING enrolled stratum,
PRESERVED>`, `override_ghl_calendar_id=<the operator's enrolled calendar, PRESERVED>`,
`cascade_changed_at=NOW()`, `requires_reattestation=True`,
`notes="cascade_field_change_detected_by_normalizer"`). The append-only enrollment log
records the change; `requires_reattestation=True` is the fail-closed flag. The back-fill
does NOT auto-adopt the newly-detected snapshot stratum — it would misrepresent the
enrollment as "now enrolled in <new provider>" when the operator never chose it. The
row honestly reads "still enrolled in <X>, flagged for re-attestation"; the live
fail-closed safety is delivered by the Phase-1 resolver (see the F-1 seam below).

### The F-1 cross-PR fail-closed seam (resolver dominance)

The fail-closed teeth are LOAD-BEARING in the Phase-1 resolver
(`autom8y-data` PR #218 `scheduling_posture.resolve_effective_posture`), NOT in the
back-fill payload's stratum value. The resolver fails closed to GHL whenever an
override is flagged `requires_reattestation=True` AND has not been operator-re-attested
since the cascade change (`attested_at >= cascade_changed_at`) — **regardless of whether
the live snapshot corroborates the enrolled stratum**.

This closes the N5 F-1 fail-open: the earlier resolver let a *self-corroborating* snapshot
(one whose stratum equals the flagged `override_stratum`) silently re-open the override,
so the re-attestation teeth never bit. Two surfaces depended on that exception — the
back-fill (when it adopted the new stratum, it was always self-corroborating) AND any
office whose snapshot later **flaps back** to the enrolled value while re-attestation is
still pending. Both now fail closed. The cross-PR seam is locked by a composed test on
each side (`test_scheduling_posture.py::TestComposedReconcileSeam` and
`test_scheduling_enrollment_reconcile.py::test_composed_sweep_backfill_fails_closed_against_resolver_replica`)
— the seam the isolated Phase-1/Phase-2 suites could not see. The architecture's further
"AND the current stratum depends on the changed field" refinement RELAXES fail-closed and
is deliberately DEFERRED (it would re-introduce a snapshot-gated exception); the
strictly-safe baseline ships.

## Why (a) is STRUCK

Option (a) is a **cross-service two-phase write**: the asana normalizer would have to
atomically commit a stratum upsert in autom8y-data AND an enrollment override in
autom8y-data within one guarded transaction spanning the push. This is not
**TL-A4-coherent**:

- The asana service is the SoE; autom8y-data is the SoR. The normalizer holds no
  transaction handle on the SoR — it speaks to two *separate bounded HTTP routes*
  (`/scheduling-stratum/sync` and `/scheduling-enrollment/override`) that, by Phase-1
  design (TL-A2), do NOT share a store or a transaction (the stratum store and the
  enrollment store are deliberately disjoint; only the posture orchestrator reads
  across them). There is no two-phase-commit primitive across these routes.
- A partial failure (stratum upsert succeeds, override append fails) would leave the
  two planes inconsistent with no rollback path — exactly the corruption the split was
  designed to avoid.

So per-guid transactional coupling is STRUCK as structurally infeasible across the
service boundary.

## Why (b) is acceptable-but-not-chosen

Option (b) (batch retry-with-backoff coupled to the push) is the acceptable fallback:
it avoids the two-phase-write trap by treating invalidation as a best-effort batch
side-effect with bounded retries. It is rejected in favour of (c) only because (c)
**decouples invalidation cadence from the snapshot cadence entirely** — the sweep can
run on its own schedule, degrades to a no-op rather than corrupting either table on
partial failure, and keeps the push path single-responsibility (resolve + project +
POST, nothing else). (b) remains a valid alternative if a future constraint makes a
standalone sweep schedule undesirable.

## Consequences

- The sweep is a separate, independently-gated process
  (`SCHEDULING_ENROLLMENT_RECONCILE_ENABLED`, default-off). It reads via injected
  `fetch_snapshot` / `fetch_enrollment` and writes via an injected `post_override`, so
  the divergence logic is PURE and exercisable as a dry-run with zero live calls.
- Eventual consistency: a cascade change is invalidated on the next sweep pass, not
  synchronously at push time. This is acceptable — the stratum read route already
  fails closed to GHL beyond its freshness TTL, so a not-yet-reconciled office degrades
  safely rather than serving a wrong-but-confident provider.
- The push path and the sweep share NO state and NO transaction, preserving the
  Phase-1 bounded-route disjointness.

## Related build decisions (recorded here for the seam)

### Placement of the eight source fields — Offer, not UnitHolder

The monolith sources all eight cascade fields from `unit_holder.*`. In autom8y-asana,
however, `UnitHolder` is a thin `HolderFactory` container with ZERO custom-field
descriptors — it is structurally not a field-bearing entity. The field-bearing
scheduling entity here is **Offer**, where the legacy cascade OUTPUT field
(`custom_cal_url`) already reads successfully today. The eight cascade INPUTS are
therefore declared alongside `custom_cal_url` on Offer. This DIVERGES from the literal
HANDOFF text ("offer.py") only in that it CONFIRMS it against the working
autom8y-asana entity, and DIVERGES from N1's monolith ground-truth (`unit_holder.*`)
because the two codebases split entities differently. The live confirmation that the
Offer task's Asana manifest carries these eight (vs. the Units task) is the operator's
post-deploy workspace-probe residual (per N1; no prod PAT was pulled at build time).

### Contract deviation from the HANDOFF row shape

The HANDOFF described the snapshot row as
`{guid, stratum, custom_ghl_id, ghl_calendar_id, resolved_at, synced_at, snapshot_source}`.
The ACTUAL Phase-1 contract (PR #218) is narrower and is what the build targets:

- `SchedulingStratumEntry` (extra=forbid) carries EXACTLY
  `{guid, stratum, custom_ghl_id, ghl_calendar_id, resolved_at}`.
- `synced_at` is **server-assigned** (it appears only on the read response, never on a
  pushed entry).
- `snapshot_source` lives on the **envelope** (`SchedulingStratumSyncRequest`), not on
  the entry.

The build emits the exact PR #218 shapes; the contract-match test validates the built
payload against an extra=forbid replica so an envelope-only key on an entry is caught.

### The `{duration}_min_ghl_id` empty-fallback — carried, not dropped

The monolith GHL resolver falls back to a duration-specific `{word}_min_ghl_id` field
when the explicit `custom_ghl_id` is empty. The fallback LOGIC is built and tested as
the PURE `derive_effective_ghl_id`; the LIVE read of the duration-keyed field family
(not one of the eight FORK-UVP source fields; needs offer-duration context) is an
explicit, additively-activatable deferral — pass a resolved `duration_fallback_id` to
fold it in, no resolver change required.

## Prediction Ledger

Falsifiable predictions underwriting deferred design choices. Each carries a claim, a
falsification condition, an expiry, and a named curator; when a prediction is falsified
before expiry the linked decision is re-adjudicated.

### TL-A7 — stratum volatility underwrites the materialized-projection TTL (DEFER-5)

- **id**: TL-A7
- **claim**: scheduling-provider stratum is structurally low-volatility, validating the
  option-(iii) ~4-8h-TTL materialized projection (the freshness-stamped stratum snapshot
  refreshed on the sweep/push cadence rather than resolved per-request).
- **falsification_condition**: per-office cascade-field mutation rate > 2%/week measured
  over a rolling 30/90-day window (i.e. more than ~2% of offices change a cascade SOURCE
  field week-over-week — the stratum is then volatile enough that a multi-hour TTL serves
  stale providers materially often).
- **expiry**: 2026-12-27
- **curator**: build team / SRE owner — assign at Phase-2 kick-off.
- **re-adjudication trigger**: if falsified before expiry, re-adjudicate the projection
  freshness model — SHORTEN the TTL/sweep cycle toward real-time, or move to
  EVENT-DRIVEN invalidation (push-time or webhook-triggered reconciliation) instead of the
  periodic sweep. The option-(c) sweep cadence (`SCHEDULING_ENROLLMENT_RECONCILE_*`) and
  the stratum freshness TTL are the two levers; the fail-closed-to-GHL posture beyond TTL
  (and the F-1 re-attestation dominance above) bounds the blast radius of a wrong
  prediction in the interim — a volatile-but-not-yet-reconciled office degrades safely to
  GHL rather than serving a confidently-wrong provider.
