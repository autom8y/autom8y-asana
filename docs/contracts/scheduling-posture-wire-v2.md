# Scheduling-Posture Wire Contract v2 (FROZEN)

> Status: FROZEN 2026-07-01 (FORK-1 Option 2 — thick-wire / projection-complete).
> Authority: `.ledge/decisions/FORK-RULINGS-scheduling-posture-build-2026-07-01.md`
> (FROZEN WIRE CONTRACT) + `.ledge/specs/TDD-scheduling-posture-substrate-2026-07-01.md`
> §10 Option 2.
>
> This is the **first atomic pinned commit** of the scheduling-posture substrate
> build. BOTH legs build against it and never against a moving seam:
> the autom8y-asana **producer** leg emits it; the autom8y-data **consumer** leg
> gates on it. The producer is the single writer — a pure projection of Asana
> `custom_cal_status` (enrollment) + the cascade (stratum). Land-order:
> contract commit → producer emit → consumer gate.

## The frozen block (byte-identical, do not paraphrase)

```
SCHEDULING-POSTURE WIRE CONTRACT v2 (FROZEN 2026-07-01, FORK-1 Option 2)
SchedulingStratumEntry fields (extends v1 {guid, stratum, custom_ghl_id, ghl_calendar_id, resolved_at}):
  enrolled: bool                          # REQUIRED. Producer-derived from Asana custom_cal_status (INACTIVE -> false; absent/unset follows the legacy ACTIVE default -> true). De-enrolled offices STAY PRESENT with enrolled=false -- NEVER omitted from the snapshot.
  canonical_destination_url: string|null  # Producer-built for the cascade-winning provider via the RESIDENT formatters. null when no provider URL resolves.
  ghl_ownership: "client_owned" | "internal_duration" | "none"   # REQUIRED. From derive_effective_ghl_id precedence: explicit custom_ghl_id -> client_owned; duration fallback -> internal_duration; neither -> none.
Envelope unchanged: {snapshot_source, entries, source_timestamp, entry_count}; entry model extra="forbid".
```

## Realization map (producer side, this repo)

| Contract field | Producer home | Receipt |
|----------------|---------------|---------|
| `enrolled` | `normalizer/scheduling_extractor.py` — `derive_enrolled(custom_cal_status)` (INACTIVE → false; absent/unset → true). Carried on `ExtractedScheduling` and stamped onto `StratumResult`. | R-NEW-1 |
| `canonical_destination_url` | `normalizer/scheduling_stratum.py` — `resolve_stratum` builds the cascade winner's URL via the RESIDENT formatters (`format_trackstat_url`, `format_sked_url`, `build_ghl_url`); DIRECT/URL providers forward the raw winning value; `null` when no winner. | R-NEW-2 |
| `ghl_ownership` | `normalizer/scheduling_stratum.py` — `derive_ghl_ownership(custom_ghl_id, duration_fallback_id)`, derived pre-fold in the extractor. | ESC-1 / obligation 4 |

## Load-bearing invariants

- **Enrolled-bit representation (HARD CONSTRAINT).** De-enrolled offices STAY
  PRESENT in the snapshot with `enrolled=false` — NEVER omitted. This keeps the
  data-side Opt2 shrink-guard honest (churn ≠ deletion), preserves the I1
  whole-source DELETE semantics, and cures CH-01 by projecting current-state
  every sync.
- **Completeness contract (I2).** The whole-snapshot push MUST iterate the FULL
  active-office set, never a completed-entities partial. A partial batch fed to
  the data side's whole-source DELETE would mass-wipe live enrolled offices. The
  producer entry point (`lambda_handlers/scheduling_stratum_snapshot.py`) refuses
  to push when the office set cannot be proven complete.
- **extra="forbid".** The entry model forbids stray keys; the envelope-only
  fields (`snapshot_source` / `source_timestamp` / server-assigned `synced_at`)
  MUST NOT appear on an entry.

## Activation posture (DEFAULT-DARK)

The whole mechanism is DARK. The live push is gated behind
`SCHEDULING_STRATUM_PUSH_ENABLED` (DEFAULT-OFF). The I2 periodic full-snapshot
trigger is a HARD pre-activation gate (FORK-2, DEFER-with-watch): the EventBridge
schedule wiring is a **releaser-seam** item (this repo carries no IaC for it) —
see `lambda_handlers/scheduling_stratum_snapshot.py`. Apply / merge / activate /
schedule remain reserved operator levers.

---

## v2.1 AMENDMENT (2026-08-10, RUL-22 ninth source field)

> Additive to v2. Nothing above changes. Authority:
> `.ledge/decisions/ADR-gcal-intent-surface-contract-2026-08-10.md` §2.4. This block
> MUST be byte-identical to the autom8y-data copy of this contract.

```
SCHEDULING-POSTURE WIRE CONTRACT v2.1 (AMENDED 2026-08-10, RUL-22 ninth source field)
Additive to v2. SchedulingStratumEntry gains ONE optional field:
  served_calendar_id: string|null   # OPTIONAL (default null). The calendar identity of the CASCADE WINNER at raw calendar-id grain, INTENT-SOURCED ONLY.
                                    # google_cal_id wins -> the stripped Google Calendar ID. custom_ghl_id wins -> the RAW effective GHL id (NOT the widget URL).
                                    # Every other winner, and the inactive terminal -> null. NEVER sourced, joined, defaulted or backfilled from business_offers.
Read side: SchedulingStratumReadResponse gains served_calendar_id (nullable); it is NULL on every fail-closed GHL branch.
Producer emission is gated by SCHEDULING_STRATUM_SERVED_CALENDAR_ID_ENABLED (DEFAULT-OFF); when off the KEY IS OMITTED (extra="forbid" rejects unknown keys, not values).
Envelope unchanged: {snapshot_source, entries, source_timestamp, entry_count}; entry model extra="forbid" — UNCHANGED and NOT relaxed.
```

## v2.1 producer realization (this repo)

| Contract field | Producer home | Receipt |
|----------------|---------------|---------|
| `served_calendar_id` | `normalizer/scheduling_stratum.py` — `resolve_stratum` derives it via `_derive_served_calendar_id` (google_cal_id winner → stripped id; custom_ghl_id winner → RAW effective GHL id, NOT `build_ghl_url`; else `null`). Carried on `StratumResult`; emitted by `services/scheduling_stratum_push.build_stratum_entry` only when the emission flag is on. | RUL-22 |

## v2.1 load-bearing invariants

- **INTENT-SOURCED ONLY (C-1).** `served_calendar_id` is NEVER sourced, joined,
  defaulted, inferred, or backfilled from `business_offers` (or `master_cal` /
  `master_cal_id` / any operations table), in any repo, on any code path. Its only
  input is the cascade winner already selected from the Asana-intent frame.
- **`NO_CANONICAL_URL_FIELDS`.** A `google_cal_id` winner has no provider booking
  page: `canonical_destination_url` is `null` for it (never the raw calendar id).
- **DEFAULT-OFF emission + flag-OFF-first rollback.** The key is OMITTED (not
  `null`) until `SCHEDULING_STRATUM_SERVED_CALENDAR_ID_ENABLED` is truthy. Land
  order: data migration 027 → data image → producer (flag off) → operator flip on.
  Rollback flips the flag OFF first, confirms one clean push, then rolls images.
- **PII.** The raw value MAY be a primary-calendar mailbox address. It is NEVER
  logged, trace-attributed, or metric-dimensioned by the producer; only the
  `served_calendar_id_emitted` bool is observable.
- **Cascade position is OPEN (FORK-CASCADE-POS / RUL-6).** `google_cal_id`'s
  priority relative to `custom_ghl_id` is an operator ruling, not frozen here; it
  lives in a single `CASCADE_PRIORITY` index. Built at the interim index-7
  recommendation, INERT until an office is populated.
