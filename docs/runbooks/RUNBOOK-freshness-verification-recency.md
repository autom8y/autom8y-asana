# Freshness / Verification-Recency Runbook

> **Ops catalog item: SRE-003** (freshness-verification-recency procession,
> `.ledge/spikes/HANDOFF-10x-dev-to-sre-2026-05-27.md` item SRE-003).
> This is the discoverable runbook referenced by the alarm
> `autom8-asana-section-name-contract-violation-error` (`alarm_description:
> "Runbook: freshness-verification-recency"`).
>
> Authored by: observability-engineer (sre rite), 2026-05-28.
> Naming note: the repo convention is `docs/runbooks/RUNBOOK-feature-name.md`
> (see `docs/runbooks/README.md`); placed here rather than `.ledge/` so the alarm
> description resolves to a known location. The work-item ID **SRE-003** is reused
> from the 10x-dev→sre handoff; it is unrelated to the April artifact
> `.ledge/reviews/SRE-003-preflight-observability-review-2026-04-21.md`.

## Problem Statement

The metrics `freshness` signal historically measured **mutation-recency**
(`now − min(parquet mtime)`) — how long since the data last *changed*. On the
prod fleet this produced a 62-day false-staleness signal for stable-but-current
data (a section can be correct yet unchanged for months). The
freshness-verification-recency feature (PR #67, `cbfb61ca`) introduces
**verification-recency** as the trustworthy freshness gauge, scoped to
active-classified sections, and adds a contract-violation alarm.

**Severity of a `SectionNameContractViolationError` alarm: P1 (Degraded)** — a
section's re-seed failed; `verification_age` for that entity may be silently
weaker than it appears. Not a P0 outage (data is still served; freshness signal
is degraded, not absent).

## Quick Diagnosis

| Symptom | Likely Cause | Jump To |
|---------|--------------|---------|
| `SectionNameContractViolationError` alarm fired (≥1) | A section warmed/stamped but `name` is still null → re-seed failed | [Alarm: Contract Violation](#alarm-sectionnamecontractviolationerror) |
| WARN-tier `section_name_contract_violation` in logs, no alarm | Expected first-deploy re-seed window (`reseed_window=true`); self-clears on warm cadence | [Expected First-Deploy Behavior](#expected-first-deploy-behavior) |
| `verification_age` climbing across the fleet, no contract violation | Dropped section coverage, or stamp-phase write failing silently | [verification_age climb](#verification_age-is-climbing) |
| `section_last_verified_stamp_failed` in logs | Stamp-phase exception swallowed under the warm broad-catch (S3 5xx / throttling) | [Stamp-phase failure](#section_last_verified_stamp_failed-silent-degradation-guard) |
| Signal reads ~62d again under a new label | Feature inert: manifest degraded to `mutation_age` (no in-scope section stamped) | [verification_age climb](#verification_age-is-climbing) |

## SLI Definition

**`verification_age` = `now − min(last_verified_at)`** over the
**active-classified sections** of an entity
(`CLASSIFIERS[entity_type].active_sections()`, resolved against the manifest).
This is the trustworthy freshness gauge. [ADR-006 §Decision 1–4]

- `last_verified_at` is stamped per-section at the probe site
  (`progressive.py::_probe_freshness`) on every probe verdict ≠ `PROBE_FAILED`,
  but only when cached content is confirmed to match live Asana at stamp time
  (CLEAN stamps directly post-prober-fix; delta-requiring verdicts stamp only on
  delta-apply success). [ADR-006 §Decision-5]
- Scope is **active-classified sections only** (denominator-integrity): empty,
  cold, or unclassified sections do not set the floor. [ADR-006 §Decision-3]
- It **replaces** the old mutation-age 62d false-signal as the alarmable freshness
  SLI. The old signal is RETAINED as `mutation_age` — context-only, **do not
  alarm**. [ADR-006 §Decision-4]

Observed live baseline (fleet, 2026-05-28): `verification_age ≈ 40m`, scoped to
active-classified sections; `last_verified_at` + `name` populated on all warmed
entity manifests.

## SLO / Threshold Guidance

The alarmable threshold should be **derived from the EventBridge warm schedule,
not the arbitrary 6h TTL.** [ADR-006 closing §, `__main__.py:164` re-grounding]

- `verification_age` should sit at **≤ ~N× the scheduled-warm interval**. A
  section that exceeds that ceiling indicates **dropped coverage** (its probe
  stopped running and its stamp aged out) — the highest-value output of this
  signal. [ADR-006 §Alternatives (a) — the dropped-coverage detection that a
  project-level heartbeat cannot express]
- The legacy `6h` default (ADR-001 §Decision-2) is **re-grounded** to track the
  warm cadence. Reuse the per-class SLA machinery
  (`sla_profile.py`, `active=21600s`) rather than inventing a new constant.
- Current observed baseline (~40m) is well within any cadence-derived ceiling.
  When the warm interval is read from the EventBridge rule, set the alarm
  threshold to a small multiple of it (e.g. 2–3× the interval) so a single
  missed warm does not page but sustained dropped coverage does.

> Note: the `verification_age` ceiling alarm is a separate (future) alarm from the
> contract-violation alarm documented below. The contract-violation alarm is the
> one that is currently live; the cadence-derived `verification_age` ceiling is the
> SLO target this runbook records for when it is wired.

## Metrics Catalog

| Metric / event | Type | Alarmable? | Semantics |
|----------------|------|-----------|-----------|
| `verification_age` | SLI (metric) | **YES** (`--strict`) | `now − min(last_verified_at)` over active-classified sections. The trustworthy freshness gauge. [ADR-006 §Decision-4] |
| `mutation_age` | context (metric) | **NO — do not alarm** | `now − min(parquet mtime)`, the old write-age signal. Retained for diagnostics ("current but unchanged 62d" is a legitimate, non-alarming observation). [ADR-006 §Decision-4] |
| `section_name_contract_violation` | structured log event | tiered (see below) | Emitted at `progressive.py:489-535`. **WARN** = `reseed_window=true` = expected first-deploy never-warmed window. **ERROR** = `reseed_window=false` = a section warmed/stamped but `name` still null = a true contract violation (re-seed ran and failed). [ADR-006 §Decision-7 / §Decision-7a] |
| `section_last_verified_stamp_failed` | structured log event | silent-degradation guard | Emitted when the stamp phase fails under the warm broad-catch (S3 5xx, throttling during `get_manifest_async` / `_save_manifest_async`). Lets silent stamp-starvation be alarmed separately from the `verification_age` climb it would otherwise cause. [ADR-006 §Decision-9; TDD §2.2] |

Note: `section_name_contract_violation` is a **log event**, not a CloudWatch
metric. The live alarm runs off a **CloudWatch Logs metric filter** that promotes
only the ERROR tier into the `Autom8y/FreshnessProbe / SectionNameContractViolationError`
metric. [`.ledge/spikes/HANDOFF-sre-to-sre-crossrepo-2026-05-27.md`]

## Live Alarm Reference

| Field | Value |
|-------|-------|
| Alarm name | `autom8-asana-section-name-contract-violation-error` |
| Metric | `Autom8y/FreshnessProbe / SectionNameContractViolationError` |
| Log metric filter (corrected, live 2026-05-28 09:09 UTC) | `{ ($.event="section_name_contract_violation") && ($.extra.reseed_window IS FALSE) && ($.level="error") }` |
| Source log group | `/aws/lambda/autom8-asana-cache-warmer` |
| Comparison / threshold | `GreaterThanOrEqualToThreshold`, threshold `1`, statistic `Sum`, period `3600`, evaluation_periods `1` |
| Missing data | `treat_missing_data = notBreaching` |
| Notify | SNS → `autom8y-platform-alerts` |
| Terraform source | `autom8y/terraform/services/asana/main.tf` (alongside the existing alarm block) |
| Current state | `OK`, metric Sum=0 (no violations) |
| `actions_enabled` | **`false`** — suppressed pending bake (see defer-watch `section-name-contract-alarm-actions-enable`) |

> The metric filter **structurally excludes** the WARN tier (`reseed_window=true`)
> so it can never increment the metric — the alarm is incapable of paging on the
> expected first-deploy re-seed window. This exclusion lives in the filter pattern,
> not merely the alarm threshold, and is the load-bearing precision guarantee.
> [ADR-006 §Decision-7a]

## Alarm: `SectionNameContractViolationError`

### What it means

A section has been **stamped/warmed** (re-seed pass ran — proven by ≥1 in-scope
section having `last_verified_at != None`) **but its `name` is still null**
(`reseed_window=false`). This is a **true contract violation**: the re-seed
attempted to repopulate the section name from `Section.name` at warm entry and
**failed for that section**. With ≥2 sections, a null `name` means the active
section join cannot resolve and `verification_age` for that entity is not
trustworthy. [ADR-006 §Decision-7 / §Decision-7a]

### First triage steps

1. **Identify the offending project/entity.** Find the ERROR-tier emission in the
   warmer log group `/aws/lambda/autom8-asana-cache-warmer`:
   ```
   filter @message like /section_name_contract_violation/
   | filter level = "error"
   ```
   The structured event carries the entity / project context in `$.extra`.
2. **Inspect that project's manifest.** Confirm which section(s) have
   `name=null` while `last_verified_at` is populated (the contradictory pair that
   defines the violation).
3. **Read the warm logs for that project's most recent scheduled warm.** The
   re-seed runs inside `_probe_freshness` (`progressive.py:316`); the name source
   is `Section.name` from `_list_sections()` (`progressive.py:508`). A null at
   warm entry means the **live Asana `Section.name` was itself null/missing** for
   that section, or the re-seed thread did not reach the stamp block.
4. **Confirm it is not a stamp-write failure in disguise** — check for
   `section_last_verified_stamp_failed` in the same warm window. If present, the
   manifest write failed and the contract violation is a downstream artifact; fix
   the write path first.
5. **Route the fix.** Re-seed failure for a section is a code/data path issue →
   route to **10x-dev** (manifest re-seed path) unless it is an Asana-side null
   `Section.name`, which is a data condition to confirm with the project owner.

### Do NOT page on WARN

The WARN tier (`reseed_window=true`) is **not paged by design** — it is
structurally excluded from the metric filter. If you see WARN-tier
`section_name_contract_violation` in logs with no alarm, that is correct behavior
(see below). Do not add an alarm on the WARN tier.

## Expected First-Deploy Behavior

On first deploy, **every** existing prod manifest carries `name=null` fleet-wide
(the historical `mark_section_complete` wipe), so the §Decision-7 data-state
condition is raw-true on every project until that project's first post-deploy warm
runs the re-seed. This is the **re-seed window**:

- Each fleet project emits **one WARN-tier** `section_name_contract_violation`
  (`reseed_window=true`) on its first post-deploy warm, then **self-clears** on the
  warm cadence as the re-seed populates `name` from `Section.name`. The warm
  cadence IS the backfill — there is no separate backfill job. [ADR-006 §Decision-7a]
- Live-measured first deploy: ~10 of 11 fleet projects emitted one WARN each, then
  cleared. As of 2026-05-28 the fleet is **fully warmed** — the re-seed window is
  **cleared**; `name` + `last_verified_at` are populated on all warmed manifests.

> **For a future re-deploy or cold-fleet bring-up:** expect the WARN-tier re-seed
> window to reappear transiently. This is benign and self-healing. Do NOT escalate
> WARN-tier emissions or wire an alarm on them. Only `reseed_window=false` (ERROR)
> is an incident.

## `verification_age` is Climbing

If `verification_age` rises across the fleet **without** a contract violation:

1. **Dropped coverage** — a section's probe stopped running, so its
   `last_verified_at` aged out and became the dominant `min`. This is the signal
   working as designed (it surfaces the section that fell out of coverage).
   Identify the oldest-stamped section in the manifest and check why its probe is
   not running.
2. **Stamp-phase failure** — check for `section_last_verified_stamp_failed`
   (below). A failing stamp write makes every section look unverified.
3. **Feature-inert / degraded-to-mutation** — if NO in-scope section has been
   stamped, the reader degrades to the `mutation_age` signal (conservative; no
   fabricated fresh number). If the number looks like the old ~62d under a new
   label, the re-seed has not run for that entity — treat as the inert-feature
   condition and re-run a warm. [ADR-006 §Decision-6 / §Decision-7]

## `section_last_verified_stamp_failed` (Silent-Degradation Guard)

The stamp block lives under the warm BROAD-CATCH (`progressive.py:379`). A
stamp-phase exception (S3 5xx, throttling during `get_manifest_async` /
`_save_manifest_async`) would otherwise be swallowed: no sections stamped that
warm, warm reports success, and the operator cannot distinguish "stamp write
failed" from "genuinely not verified." This metric is emitted on the failure
branch so silent stamp starvation is alarmable separately from the
`verification_age` climb it would cause. [ADR-006 §Decision-9; TDD §2.2]

If you see this event: the manifest write is failing (check S3 throttling /
warmer Lambda IAM / transient 5xx). The fix is on the write path, not the
freshness logic.

## Null-Watermark Residual (Documented Non-Regression)

The in-scope prober fix (closing the false-CLEAN channel) runs **only inside the
`watermark is not None` branch**. Sections with `watermark=null` retain the
pre-existing **hash-only** change detection. [ADR-006 §Decision-4 scope caveat;
QA gate rev-2 D8]

- Prod-confirmed counts (2026-05-27): **~21/34 offer** sections and **~4/17 unit**
  sections have `watermark=null`.
- For these sections, the `verification_age` stamp is **no stronger than the old
  signal was for them** — a false-CLEAN on a null-watermark section can still
  stamp it as verified. This is a **documented residual, not a regression** (it is
  no worse than the prior mutation signal was for those sections).
- Operational implication: a green `verification_age` does **not** guarantee
  end-to-end content correctness for null-watermark sections. If correctness is in
  doubt for an offer/unit entity, do not treat `verification_age` as proof of
  content freshness for its null-watermark sections — corroborate by other means.

## Prevention

- Keep the metric-filter WARN exclusion intact (`reseed_window=false` AND
  `level=error`) — never widen it to the event name alone, or first deploy pages
  ~10× for expected behavior.
- Derive the `verification_age` ceiling alarm threshold from the EventBridge warm
  cadence when it is wired; do not reuse the arbitrary 6h TTL.
- When closing the null-watermark residual is feasible, prefer carrying watermarks
  through completion so the prober fix covers those sections too.

## See Also

- ADR-006 — `.ledge/decisions/ADR-006-freshness-equals-verification-recency.md`
  (the why; Decisions 1–9, §Decision-7a re-seed-window suppression)
- TDD — `.ledge/specs/freshness-verification-recency.tdd.md`
- QA gate — `.ledge/reviews/QA-freshness-verification-recency-gate.md`
- HANDOFF (10x-dev→sre) — `.ledge/spikes/HANDOFF-10x-dev-to-sre-2026-05-27.md` (item SRE-003)
- HANDOFF (sre→sre cross-repo, the alarm TF) — `.ledge/spikes/HANDOFF-sre-to-sre-crossrepo-2026-05-27.md`
- Defer-watch — `.know/defer-watch.yaml` entry `section-name-contract-alarm-actions-enable` (the `actions_enabled` flip)
