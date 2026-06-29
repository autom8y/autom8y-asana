---
type: handoff
handoff_kind: blocker-escalation
handoff_type: assessment
schema_version: "1.0"
status: proposed
handoff_status: pending
cross_repo: true
from: account-status-recon (consumer · data-analyst rite — BI-trustworthiness inquisition)
to: autom8y-asana producer team (CR-3 clean-break cutover · offer-axis producer — receiver query surface + section-warm lane)
from_thread: account-status-recon BI-trustworthiness inquisition (customer-report altitude; #account-health three-way reconciliation)
to_thread: CR-3 clean-break cutover / offer-axis producer (POST /v1/query/offer/rows receiver surface + scheduled cache_warmer lane)
date: 2026-06-08
severity: P0-consumer-blocking (offer-axis blackout; gates ASR customer re-enable N5)
blocking: true
non_prescriptive: true   # this doc signals the blocker + live receipts + coherence + invariants + open questions. The remediation altitude and shape are the producer's.
discipline: "Read-only coherence/blocker handoff. ASR asserts consumption + live HTTP status only — status/code/retry-hint, NO row material, NO secret material. The warm lane, the offer DataFrame production, the cutover sequencing are the producer's single-writer domain."
initiative: "CR-3 clean-break cutover · R3 GATE-2 receiver LANDING (proven → merged → live)"
related:
  - .ledge/handoffs/HANDOFF-releaser-to-sre-10xdev-cr3-gate2-release-sequencing-2026-06-08.md   # the rung you fold into; Trap-4 warm-lane-paused posture; G-RUNG vocabulary
  - .ledge/handoffs/HANDOFF-cr3-to-auth-producer-credential-coherence-2026-06-06.md             # structural exemplar — cross-repo, read-only, §Held + A-n shape
  - autom8y/.know/telos/recon-services-inquisition.md                                            # SHARED falsifiability telos one altitude up ("empty == clean" lie; population floor; ItemsAnalyzed==0 alarm ads+asr)
  - .sos/wip/frames/g2-vertical-semantics-contract.md                                            # OPEN: (office_phone, vertical) meaning still being adjudicated; telos_status DECLARED
  - autom8y/services/account-status-recon/.sos/wip/inquisition/account-status-recon-bi-trustworthiness/ATTESTATION-sre-PT-R-2026-06-05.md  # ASR dry-run + 147/147 blackout history
references:
  - src/autom8_asana/api/routes/query.py:564-575          # the 503 envelope emit site (catch CacheNotWarmError → CACHE_NOT_WARMED, details.retry_after_seconds:30)
  - src/autom8_asana/services/query_service.py:625        # the message origin: raise CacheNotWarmError(f"DataFrame unavailable for {entity_type}.") — matches the live body verbatim
  - src/autom8_asana/services/universal_strategy.py:741-861 # offer is body_parameterized=False → cache-only; miss → return None (:861); NO build-on-miss (the contract docstring :751-758)
  - src/autom8_asana/core/entity_registry.py:517-533      # offer descriptor (warmable=True, warm_priority=3, default_ttl_seconds=180, primary_project_gid 1143843662099250)
  - src/autom8_asana/lambda_handlers/cache_warmer.py:638-720 # the out-of-band scheduled warmer; offer in cascade_warm_order (~:723-741; :652-653 is the docstring); discovery-fail early return (:714-720)
  - src/autom8_asana/api/preload/progressive.py:139,598,608-618 # API-startup preload warm path; per-project failure is swallowed+logged (progressive_preload_project_failed)
  - src/autom8_asana/cache/dataframe/factory.py:49,205,214,191-202 # L1 per-process MemoryTier / L2 S3 ProgressiveTier; provider None when s3.bucket unset
  - src/autom8_asana/services/errors.py:253,276           # CacheNotReadyError.error_code → CACHE_NOT_WARMED; CacheNotWarmError (status_hint 503); TDD-SERVICE-LAYER-001 / ADR-SLE-003
  - autom8y-api-schemas envelopes.py (EXTERNAL published package — not an autom8y-asana repo file) # ErrorDetail.retryable default False + UNUSED typed retry_after_seconds field (the contradiction site)
  - autom8y/services/account-status-recon/src/account_status_recon/fetcher.py:275-366 # ASR consumer: fetch_offers POSTs /v1/query/offer/rows twice (active + activating); wraps any exception → degraded axis (:363-366)
  - .know/feat/exports-route.md:217                        # documented wire contract: 503 / CACHE_NOT_WARMED / retry_after_seconds:30
  - .know/scar-tissue.md                                   # SCAR-CW-001 — the producer's own cold-start failure taxonomy
---

# HANDOFF — ASR offer-axis read 503s CACHE_NOT_WARMED on a persistently-cold offer DataFrame (consumer → CR-3 offer-axis producer)

> **Non-prescriptive by design.** This document signals the blocker, lays out the live receipts, the
> contextual coherence with your CR-3 cutover and our *shared* population-floor telos, the invariants any
> sound remediation must preserve, and the open design questions. It deliberately does **not** prescribe a
> fix. Whether and when the offer warm lane re-arms inside the cutover soak — and the shape of that — is
> yours to own. ASR asserts consumption and live HTTP status only.

> **⚠️ READ §2 FIRST.** A live probe with ASR's own SA token, run 2026-06-08, finds the offer query
> surface returning **503 CACHE_NOT_WARMED persistently across ~8 minutes** — not a transient warm-up
> window. The offer DataFrame is not in the warm cache, and (per your own contract) the offer path does
> **not** build on miss. This is the producer-side mechanism behind ASR's offers-axis blackout. It is
> almost certainly a *coherent consequence of the CR-3 warm-lane being deliberately quiesced* (Trap-4),
> not a defect — but ASR cannot self-heal it, and it gates the customer re-enable.

## §1. The Blocker (one breath)

ASR's customer-facing `#account-health` report is a **three-way reconciliation** joining billing
(autom8y-data), **offers (autom8y-asana)**, and campaigns (autom8y-ads) on `(office_phone, vertical)`.
The offers axis reads through `POST /v1/query/offer/rows`. That surface is currently returning
**503 `CACHE_NOT_WARMED` / "DataFrame unavailable for offer."** on every call, persistently. With the
offers axis down, the three-way cannot complete, and ASR's end-to-end dry-run returns
`accounts_analyzed=0 / pipeline_readiness=fail`. ASR holds its schedule **DISABLED** rather than post a
blackout as success. The offer DataFrame must be present in the warm cache when the query route is live —
*or* the 503 contract that gates the cold path must be honestly retryable — for ASR to re-arm. **The
blocker is real, the producer owns the warm lane, and it folds into your in-flight CR-3 cutover rather
than sitting beside it.**

## §2. The Receipt (live, status/code/hint only — NO row material)

Live probe, **2026-06-08**, against `https://asana.api.autom8y.io`, with **ASR's own SA token**:

```
POST /v1/query/offer/rows
body: {"classification":"active","select":["gid","name","section","office",
       "office_phone","vertical","offer_id","weekly_ad_spend","platforms"],"limit":N,"offset":0}

→ HTTP 503
{"error":{"code":"CACHE_NOT_WARMED",
          "message":"DataFrame unavailable for offer.",
          "details":{"retry_after_seconds":30},
          "retryable":false, ...}}
```

**Persistence (diagnostic):** three probe-pairs over ~8 minutes — **10:10Z, 10:12Z, 10:17Z — ALL 503**,
zero state change. This is **not** a brief warm-up window. ASR issues the offer read twice per cycle
(`classification:"active"` and `classification:"activating"`); both legs degrade identically.

**Why the persistence is the load-bearing signal:** your own contract makes offer
`body_parameterized=False` → **cache-only**; a miss returns `None` (`universal_strategy.py:861`) and the
offer path does **not** launch a request-time build. A transient build window would surface the *different*
code `CACHE_BUILD_IN_PROGRESS` and self-resolve in ~25–30s. Seeing `CACHE_NOT_WARMED` (not
`CACHE_BUILD_IN_PROGRESS`) hold for 8 minutes means the **out-of-band warm lane has not materialized +
persisted the offer frame** — consumer retries cannot warm it; only the scheduled warmer can.

> *Verification posture: ASR verified the receipt is **code-faithful** — every field is reproducible from
> the producer source cited in `references` (the verbatim message at `query_service.py:625`, the 503 tuple
> at `query.py:564-575`, the `retry_after_seconds:30` literal at `query.py:574`). ASR could not inspect
> producer runtime state; cross-repo runtime claims below are tagged `[UV-P]`.*

## §3. Root Localization (what the recon found — producer-side, non-prescriptive)

The 503 itself is **working as designed** — the offer path is fail-loud-not-silent: it 503s rather than
serving an empty frame. The defect, if any, is **upstream of the raise** — the warm cache is empty for
offer. ASR's archaeology localized the candidate causes but **cannot discriminate among them from the
consumer side** (they produce byte-identical 503s); the discriminator lives in *your* warmer/preload
logs and metrics, not in the query response:

- **`[UV-P: offer frame absent from S3 (L2) | METHOD: cross-repo source read only, no AWS access | REASON: ASR has no S3 ListObjects / CloudWatch on the producer account]`** — L1 MemoryTier is per-process (`factory.py:205`), but L2 is the durable S3 `ProgressiveTier` (`factory.py:214`). A merely-cold container should backfill from L2 on first miss; an 8-minute persistent 503 implies the offer frame is **absent from L2 as well** — i.e. *neither* warm path has successfully materialized + persisted offer.
- Candidate cause families (all consistent with the receipt, none excludable without producer telemetry):
  1. **The scheduled `cache_warmer` Lambda has not successfully populated offer** — not scheduled / not firing in-window / `EntityProjectRegistry` discovery failing (`cache_warmer.py:714-720` → `success=False`, warms nothing). The producer's own dead-man's-switch (`LastSuccessTimestamp`, alarm `cache_warmer_bulk_cadence_dms`) exists precisely because this has failed before.
  2. **Offer build yields zero rows / hard-fails → nothing persisted** — persist is gated on a non-empty result; a failed cascade source (`business`/`unit`) or an empty/mis-resolved offer project GID leaves no L2 entry → permanent miss. (`progressive.py:608-618` swallows per-project preload failure and returns without persisting.)
  3. **S3 not configured for the cache provider in the deployed task** — `initialize_dataframe_cache` returns `None` when `settings.s3.bucket` is unset (`factory.py:191-202`); then `_get_dataframe` skips L2 entirely and falls straight to `return None` → 503 forever.
- **The most coherent read (offered as context, NOT asserted as root cause):** per your own
  `HANDOFF-releaser-to-sre-10xdev-cr3-gate2-release-sequencing-2026-06-08.md`, **Trap-4 — "section warmer
  reserved=0 + schedule DISABLED"** — the warm lane is *intentionally paused* during the GATE-2 soak.
  **A cold offer axis is the expected shadow of a deliberately-quiesced warm lane mid-cutover.**
  ASR surfaces this as the high-probability mechanism, not as a fault to assign.

## §4. Contextual Coherence (this is the *same crusade*, one altitude up)

- **Shared falsifiability telos.** `autom8y/.know/telos/recon-services-inquisition.md` carries the exact
  thesis ASR carries: *"empty == clean" is a structural lie* — `all_clear` with no population floor emits
  the same green whether it reconciled a full population or zero records. That telos names the same floor
  discipline (`gate.py PopulationFloorCheck` / `metrics.py:159` AllClear-on-empty) and the `ItemsAnalyzed==0`
  alarm (ads + asr, telos lines 36/70). **ASR's
  `accounts_analyzed=0 / pipeline_readiness=fail` is the *positive proof that the floor fires* — the
  inquisition's discipline catching a real empty-population blackout, not a regression.** You and ASR are
  downstream and upstream of one crusade.
- **Offers is 1 of 3 axes; the other axis is already proven curable.** Billing (autom8y-data) is **FIXED**
  in the same 2026-06-08 dry-run (`200 / 65 rows`). Campaigns (autom8y-ads) is also down. The offer-axis
  warmth is one of the two remaining gates between a falsifiable-degraded pipeline and a trustworthy
  customer report.
- **The schedule is held DISABLED on purpose.** ASR will not post a blackout as success. This is the
  inquisition working: degraded BI must be *falsifiable before it debuts*. The offer-axis blocker is what
  keeps the customer re-enable (N5) correctly held.
- **CR-3 *is* the offer-axis producer.** Your cutover makes the autom8y-asana receiver the authoritative
  offer/project-frame producer, replacing legacy in-process `Project.get_df()`. The offer axis ASR joins
  on is produced by *exactly* this surface. ASR is not reporting a stranger's bug — it is reporting the
  consumer-felt edge of your own cutover's deliberately-paused warm lane.
- **The producer speaks ASR's join-key language natively.** autom8y-asana runs its own internal
  `(office_phone, vertical)` reconciliation (`reconciliation/processor.py`), and the offer metric scope is
  `dedup_keys=["office_phone","vertical"]` (`metrics/definitions/offer.py`). The vocabulary is shared; the
  meaning of that key is **not yet frozen** (see §6).

## §5. Downstream Posture (what ASR does, and does not do)

- ASR holds its `#account-health` schedule **DISABLED** and will keep it disabled until the offer axis is
  live-verified.
- ASR will **live-verify** by re-probing `POST /v1/query/offer/rows` and confirming **200-with-rows for
  both `active` and `activating`** before re-enabling — not a 200-empty, not a code read, not a producer
  assertion. *Empty == clean is the lie ASR exists to refuse; ASR will not accept a 200-empty as warm.*
- ASR will **not paper over** the blocker: no synthetic offers, no last-known-good substitution, no
  silent axis-drop that posts as success. The degraded state stays falsifiable until the axis is genuinely
  warm.
- ASR **cannot self-heal** this: a fleet/consumer read cannot warm the producer's out-of-band cache, and
  the `retry_after_seconds:30` hint is inert on the offer path (no request-time build to wait for). The
  lever is the producer's.

## §6. Constraints Any Remediation Must Honor (non-prescriptive — these are invariants, not solutions)

- **The offer DataFrame must be present in the warm cache (L2/S3) when the offer query route is live — OR
  the 503 cold-path contract must be honestly retryable** such that a conforming consumer can wait-and-warm
  deterministically. ASR needs one of these two truths; it does not prescribe which.
- **A 200 must mean a genuinely-populated offer frame, not a warmed-empty one.** Per the shared
  population-floor telos, a 200-with-zero-rows that ASR cannot distinguish from a real empty population is
  the *exact failure mode the inquisition exists to prevent*. Whatever re-arms the warm lane must preserve
  the population floor — an empty offer build must remain *loud* (a 503 / a degraded signal), never a
  silent green.
- **CR-3 sequencing is sovereign and mid-flight.** The warm lane is *intentionally* paused (Trap-4); the
  GATE-2 artifact (`29ee052`) is in a 7-day proven→live soak. ASR does **not** ask you to un-pause outside
  your cutover discipline. The constraint is: ASR's customer re-enable needs a warm offer axis *at some
  named rung of the cutover* — whether that is a re-armed warmer inside the soak, a post-cutover warm-lane
  restoration, or an interim warm of the offer entity only, is yours to design and sequence.
- **`(office_phone, vertical)` semantics are NOT frozen.** The G2 Vertical-Semantics Contract
  (`.sos/wip/frames/g2-vertical-semantics-contract.md`, `telos_status: DECLARED`) is an open product-altitude
  adjudication of what that grouping identity *means* (task-intrinsic vs. ancestry-cascade vs.
  defined-precedence). Any offer-axis remediation must not silently assume a frozen vertical semantics, and
  ASR's join correctness is downstream of that unresolved meaning.
- **Single-writer fences hold.** The producer owns the warm-lane schedule, the offer DataFrame production,
  the cutover sequencing, and the `CACHE_NOT_WARMED` contract surface. ASR asserts consumption + live
  status only and writes nothing.
- **IaC lands in the monorepo, not here.** autom8y-asana carries zero Terraform (`find -name "*.tf"` → 0).
  Any warmer schedule / EventBridge / alarm change routes to `autom8y/autom8y` (`terraform/services/asana/`),
  which this repo cannot apply. ASR flags this only so the remediation isn't mis-routed.
- **Anti-theater / no-rounding (G-RUNG).** The true rung is: *offer axis = cold-never-warmed (UV-P on
  which cause); ASR pipeline = `accounts_analyzed=0 / pipeline_readiness=fail`; ASR schedule = held
  DISABLED; billing axis = FIXED (200/65).* ASR states it there and does not round to "asana is broken"
  or to "ASR is ready."

## §7. Open Questions for the Producer Side (A-1..A-6)

- **A-1 (the discriminator ASR cannot see).** Has the scheduled `cache_warmer` (or the API-startup preload)
  successfully materialized **and persisted to S3 (L2)** an offer frame in the deployed environment? Which
  of §3's cause families is the real one — warmer-not-firing, offer-build-zero/fail, or S3-not-configured?
  (Distinguishable from `cache_warmer_*` / `progressive_preload_project_failed` / `swr_build_failed`
  logs + `LastSuccessTimestamp` + an S3 ListObjects on the offer key — none of which ASR can read.)
- **A-2 (Trap-4 / cutover sequencing).** Is the offer warm lane being cold a *deliberate* consequence of
  the GATE-2 soak (warmer reserved=0 + schedule DISABLED), and at what **named rung of the CR-3 cutover**
  does the offer axis become reliably warm for downstream consumers? ASR needs to know which rung gates its
  N5 re-enable.
- **A-3 (the retry-contract contradiction — surfaced as a question, not a fix).** The 503 envelope emits
  **two retry signals that disagree**: `error.retryable: false` (top-level typed field, `ErrorDetail`
  default in shared `autom8y-api-schemas/envelopes.py`, never set by the route) **and**
  `error.details.retry_after_seconds: 30` (a free-form key the route stuffs into `details` at
  `query.py:574`), while the *typed* top-level `ErrorDetail.retry_after_seconds` field sits empty. A
  spec-compliant consumer keying off `retryable` treats this as **terminal**; one keying off
  `details.retry_after_seconds` retries. **Which is the producer's intended contract for `CACHE_NOT_WARMED`?**
  (Note the asymmetry ASR observed for context, not as a prescription: the sibling `CACHE_BUILD_IN_PROGRESS`
  503 emits a real `Retry-After` header; `CACHE_NOT_WARMED` emits neither, and carries `retryable:false`.)
  And — is `30s` even meaningful for *offer*, given offer has no request-time build for a consumer to wait on?
- **A-4 (fleet scope, not offer-only).** The `retryable`/`retry_after_seconds` shape lives in the **shared**
  `autom8y-api-schemas` envelope, and the same route file emits `CACHE_NOT_WARMED` at three sites
  (`query.py:574, 693, 816`). If the contract is reshaped, is that an offer-only or a fleet-wide
  `CACHE_NOT_WARMED`-emitter decision? ASR raises this only so the question is scoped honestly.
- **A-5 (population-floor preservation).** When the offer warm lane re-arms, what guarantees a 200 carries a
  *genuinely populated* offer frame rather than a warmed-empty one? Does an empty/degraded offer build stay
  **loud** (503 / `CASCADE_NOT_READY` / degraded signal) rather than silently 200-empty? (This is the
  invariant ASR's whole inquisition rests on; ASR needs to know the producer's posture, not to design it.)
- **A-6 (vertical semantics dependency).** Does the G2 `(office_phone, vertical)` adjudication
  (`telos_status: DECLARED`) affect what the offer frame's `vertical` column *means* once warm? ASR's join
  correctness depends on the answer; ASR does not assume it is frozen.

## §8. Held — autom8y-asana producer single-writer domain

The scheduled `cache_warmer` lane + its EventBridge schedule/DMS · the offer DataFrame production and its
S3/L2 persistence · the `CACHE_NOT_WARMED` / `CACHE_NOT_WARM` / `CASCADE_NOT_READY` error contract and the
shared envelope `retryable`/`retry_after_seconds` shape · the CR-3 cutover sequencing and the Trap-4
warm-lane pause · the G2 vertical-semantics adjudication · the offer query surface. ASR holds its customer
re-enable (N5) and schedule-DISABLED behind a producer-confirmed + ASR-live-verified warm offer axis, and
never writes producer material.

## §9. @ References

- `@.ledge/handoffs/HANDOFF-releaser-to-sre-10xdev-cr3-gate2-release-sequencing-2026-06-08.md` — the CR-3 GATE-2 soak rung + **Trap-4** warm-lane-paused posture + G-RUNG vocabulary you fold this into.
- `@autom8y/.know/telos/recon-services-inquisition.md` — the **shared** "empty == clean" population-floor telos (the floor discipline `gate.py PopulationFloorCheck` / `metrics.py:159` + the `ItemsAnalyzed==0` alarm, telos lines 36/70). Strongest same-crusade anchor.
- `@.sos/wip/frames/g2-vertical-semantics-contract.md` — the open `(office_phone, vertical)` meaning (constraint: do not assume frozen).
- `@src/autom8_asana/services/query_service.py:625` · `@src/autom8_asana/api/routes/query.py:564-575` — message origin + 503 emit site (matches the receipt verbatim).
- `@src/autom8_asana/services/universal_strategy.py:741-861` — offer cache-only / `None`-on-miss / no build-on-miss contract.
- `@src/autom8_asana/lambda_handlers/cache_warmer.py:638-720` · `@src/autom8_asana/api/preload/progressive.py:139,608-618` — the two out-of-band warm paths.
- `@src/autom8_asana/cache/dataframe/factory.py:49,205,214,191-202` — L1 per-process / L2 S3 tier topology + provider-None-when-unconfigured.
- `@src/autom8_asana/services/errors.py:253,276` · `@autom8y-api-schemas/.../envelopes.py` — the error contract + the `retryable`/`retry_after_seconds` contradiction site.
- `@.know/feat/exports-route.md:217` · `@.know/scar-tissue.md` (SCAR-CW-001) — the documented 503 wire contract + the producer's own cold-start taxonomy.
- `@src/autom8_asana/reconciliation/processor.py` · `@src/autom8_asana/metrics/definitions/offer.py` — the producer's own `(office_phone, vertical)` reconciliation + the offer scope `dedup_keys` (shared vocabulary).
- `@autom8y/services/account-status-recon/src/account_status_recon/fetcher.py:275-366` — the ASR consumer call site (twice-per-cycle; degraded-axis on any exception).
- `@autom8y/services/account-status-recon/.sos/wip/inquisition/.../ATTESTATION-sre-PT-R-2026-06-05.md` — ASR dry-run + the 147/147 blackout history.

## Realization Rung (G-RUNG — no rounding)

- Offer axis: **cold-never-warmed** (live 503 × 3 over 8 min; `[UV-P]` on which of §3's cause families) → **warm-verified** only on a producer-confirmed materialized+persisted offer frame **and** an ASR live 200-with-rows on both `active` and `activating`.
- ASR pipeline: **`accounts_analyzed=0 / pipeline_readiness=fail`** (offers + campaigns down; billing FIXED 200/65) — stated at exactly that rung, not rounded.
- ASR `#account-health` schedule: **held DISABLED** → re-enable (N5) only after the offer axis is warm-verified and the campaigns axis clears.
- This blocker: **proposed** → accepted on the producer's A-1..A-6 reply.

*ASR (consumer) → CR-3 offer-axis producer blocker handoff, 2026-06-08. Read-only; consumption + live HTTP status asserted (status/code/retry-hint only), no row material, no secret material handled. Cross-repo claims tagged `[UV-P]`. Same crusade, one altitude up — the population floor is firing, not failing. Reply via A-1..A-6; A-3 carries the `retryable:false` vs `retry_after_seconds:30` contradiction as an open question, not a prescription.*
