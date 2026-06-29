---
type: handoff
handoff_type: assessment   # consumer-side defect evidence → autom8y-asana producer team → fold into FPC
station: cross-repo seam (autom8 monolith sre / G2-consumer → autom8y-asana producer / FPC initiative)
source_rite: sre
source_repo: /Users/tomtenuta/Code/autom8
target_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
target: autom8y-asana FPC owners (operator-gated) → fold the column-fidelity contract gap into FPC Phase-2
date: 2026-06-11
initiative: g2-satellite-column-fidelity-contract
extends:
  - .ledge/handoffs/HANDOFF-10x-dev-fpc-phase1-built-2026-06-09.md   # FPC Phase-1 BUILT; Phase-2 = the cure
  - .ledge/handoffs/HANDOFF-10x-dev-fpc-design-ratified-2026-06-09.md
  - .know/telos/dataframe-resolution-coherence.md                    # the coherence canary telos
evidence_grade: STRONG (consumer break + producer schema + contract derivation all re-pulled live this session; CR-3-safe; no producer code touched)
self_ref_cap: MODERATE→STRONG (sre-authored from the consumer vantage; STRONG on the symptom/class receipts, MODERATE on the exact producer projection-locus — assessment Q1 closes it)
status: proposed
discipline: >
  Surfaced from the consumer side (autom8 monolith) — the producer team's FPC/coherence work
  has limited visibility into which columns DOWNSTREAM consumers structurally require. We
  deliberately did NOT hotfix a consumer-side guard: a `_df.get("offer_id")` band-aid in the
  monolith would have HIDDEN a producer-side contract defect and shipped a green build over a
  silent regression — the exact anti-pattern the clean-break + canary-signal-contract exist to
  prevent. Every claim below is file:line-anchored and re-pulled live (CloudTrail/RDS/logs +
  git blame + both repos' source). Production levers (any monolith guard, any satellite
  projection change, the S7 gate) stay the operator's.
---

# HANDOFF — sre → autom8y-asana · G2 satellite column-fidelity contract gap

> **The ask in one line:** the satellite `/v1/query` contract surface validates *row/section
> completeness* and *3 resolution keys*, but **not the column-schema the consumer's code
> requires** — so consumer-needed columns outside those keys (`offer_id`, and `project_gid`
> per the open `#85`) drop **silently**, breaking real daily prod jobs. This is one CLASS, not
> two bugs. Fold a **consumer-required-column contract + a column-fidelity coherence canary**
> into FPC Phase-2.

## 1. The triggering symptom (1st-order — receipted)

A monolith ECS job (`refresh_asana_pr_frames` — daily "Asana Performance Reports") **exit-1s on
every run** in its `offers` branch:

```
2026-06-10 07:20:59 / 2026-06-11 06:38:32 / 2026-06-11 07:53:02  (daily, /ecs/autom8_refresh_asana_pr_frames_controller_prod)
AsanaAPI - ERROR - Error fetching performance report: 'offer_id'
KeyError: 'offer_id'
    nan_offer_gids = _df.loc[_df["offer_id"].isna(), "gid"]
```

- **Consumer locus (autom8 monolith):** `@apis/asana_api/objects/project/models/business_offers/main.py:164` (`activating_offers_frame`), `:203` (`active_offers_frame`), `:223` (sibling). Each does `_df = super().active_frame.copy()` → `_df["offer_id"]`. `super().active_frame` is the **`Project.get_df()` satellite frame**.
- **git blame:** the access is from `2025-04-02` ("v2") — **unchanged, pre-cutover code.** The consumer did not regress; it worked when the legacy in-process producer supplied `offer_id`. The bug appears now because `Path:"satellite"` serves this frame (confirmed live: `get_df_path Path:"satellite" GetDfSatellite:1.0` for "Business Offers" in the 2026-06-10 fleet-recovery run).
- **Severity:** degrade-not-break — the offers performance-report frame fails to refresh into its S3 warm-cache (`s3://.../asana-cache/insights-frames/`), so its 3 consumers (the **CHI Slack bot**, the **OpenAI client-concierge QOP trainer**, and **per-offer in-Asana insight managers**) read stale-or-on-demand. Nothing corrupts; a daily prod job is red.

## 2. Root cause (the contract is column-blind — receipted both sides)

**The producer DECLARES `offer_id`** — `@src/autom8_asana/dataframes/schemas/offer.py:42` (`name="offer_id"` in `OFFER_COLUMNS`, composed into the `offer` schema at `:93-97`). So this is **not** "the producer forgot the column." It is that **the frame the monolith actually consumes for `active_offers_frame` does not carry it**, and **nothing in the contract surface catches that**:

- **`honest_contract_complete` is a ROW/SECTION-completeness flag, not a column check** — `@src/autom8_asana/query/engine.py:525` `_derive_honest_contract_complete(project_gid)` derives it from the **SectionPersistence manifest** (returns False on `honest_contract_no_section_persistence` / `honest_contract_no_manifest`, `:548/:561`). Field/model: `@src/autom8_asana/query/models.py:432`. A frame can be `honest_contract_complete=True` while **missing any column the consumer needs.**
- **The monolith's own column-contract checks only the 3 resolution keys** — `office_phone / vertical / gid` (the live `satellite_column_contract` EMF: `has_office_phone/has_vertical/has_gid/contract_held`; bridge flag `@apis/asana_api/satellite/_bridge.py` `HONEST_CONTRACT_FLAG`). `offer_id` is **outside** that check.

⇒ **The cutover guarantees resolution-key presence + section materialization, but NOT the full column-schema downstream consumers depend on.** `offer_id` (a non-resolution-key offer attribute) falls in the unguarded gap. *(Assessment Q1: is the monolith's `active_frame` get_df requesting the BASE/section schema rather than the `offer` schema that carries `offer_id`, or is the column projected-then-pruned (all-null drop)? That locus is producer-side and the one MODERATE link in this chain.)*

## 3. The CLASS — this is `#85`'s sibling, not a coincidence (2nd-order)

The autom8 monolith already tracks **`#85` — "CR-3 BLOCKER: Section satellite 400 — `fetch_section_rows` missing `project_gid`."** That is the **identical failure shape on a different frame + column:**

| Instance | Frame | Missing column | Consumer break | Status |
|---|---|---|---|---|
| **#85** | Section satellite | `project_gid` | `fetch_section_rows` 400 | known, open |
| **THIS** | Offer/Business satellite | `offer_id` | `business_offers/main.py:164` daily exit-1 | new, this handoff |

Two instances ⇒ a **structural gap, not a pair of one-offs.** The contract surface has no general notion of "the set of columns each consumer requires from this frame." Until that exists, **every consumer-required non-key column is a latent silent-drop.** `@src/autom8_asana/dataframes/schemas/offer.py` + the section schema are the producer's *declared* truth; the gap is that **declared ≠ contractually-delivered-and-verified** at the `/v1/query` boundary.

## 4. Why this is the FPC initiative's problem — and its missing input (coherence)

autom8y-asana already owns the right home: the **Field-Provenance-&-Population-Contract (FPC)** initiative (`@.ledge/handoffs/HANDOFF-10x-dev-fpc-phase1-built-2026-06-09.md`, `@.know/telos/dataframe-resolution-coherence.md`) — Phase-1 BUILT (observability pillars), Phase-2 = the cure, with a **coherence canary** ("the 571 coherence canary STILL fires RED by construction"). FPC is *exactly* about field provenance + population fidelity of the resolved DataFrames.

**The missing input FPC needs from the consumer side:** FPC + the coherence canary reason about producer-side population coherence; they do **not** know **which columns each DOWNSTREAM consumer structurally requires**. `offer_id` (and `project_gid`) are precisely that — real, breaking consumer requirements invisible from inside the producer. **This handoff is that input:** fold a **consumer-required-column contract** (the union of columns each get_df caller indexes) into the FPC population-contract, and have the coherence canary assert it — so a frame that is `honest_contract_complete=True` but column-lossy fires the canary RED instead of an opaque consumer `KeyError`.

## 5. Third-order conditions revealed along this thread (canary-cleanup + boy-scout)

These compounded the gap and must travel with it so the campground leaves cleaner:

1. **The failure is SILENT end-to-end.** The monolith's new fleet-obs controller-exit/`DB_REBOOT_FAILED` alarms (PRs #71/#74) watch **`/ecs/autom8_refresh_frames_controller_prod` only** — the `asana_pr_frames` controller's daily exit-1 **pages nobody.** A column-fidelity canary on the producer is the *right* layer to catch this (vs N consumer-side alarms). [Owner: monolith sre — noted for coherence; not autom8y-asana's to fix, but it's WHY this ran red unseen.]
2. **The S7 cutover gate shares the blind spot.** S7 = 7-day `Path:satellite ≥99%` (`@.sos/wip/frames/cr3-cutover-closure-procession.shape.md` §S7). "Satellite-served + honest_contract_complete" can be **column-lossy**, so **S7 GREEN does not imply consumer-complete frames.** Retiring the legacy `get_df` fallback (the S7 telos, task #74) on a contract that doesn't validate columns would convert this silent-degrade into a hard outage for the 3 consumers. **The column-fidelity contract is a precondition for honest S7.**
3. **The 7-month fleet dormancy masked it.** The fleet was DISABLED 2025-11-25 → 2026-06-09; this daily exit-1 only became visible on re-enable. Dormant subsystems hide contract drift — the satellite contract gap existed silently the whole time.
4. **Blast surface is wider than this one report.** `offer_id` is consumed across `business_offers` (`:164/:203/:223/:598/:635`) and the offer-holder insight managers — any get_df caller indexing a non-key column is exposed; the performance-report job is merely the canary that surfaced it.

## 6. Recommendation (durable — no consumer band-aid)

1. **[autom8y-asana / FPC Phase-2] Add a consumer-required-column contract + canary assertion.** Define, per query-shape (offer/section/etc.), the column set consumers contractually require (seed: `offer_id` for offer frames, `project_gid` for section frames). Have `/v1/query` either guarantee+populate them or return a typed, non-silent contract-incomplete signal (mirroring the 503 `honest_contract_complete=False` path at `@query/models.py:446`, but for columns). Wire the coherence canary to fire RED on a column-fidelity miss.
2. **[autom8y-asana] Close `offer_id` (this) + `project_gid` (#85) as the first two instances** under that contract — confirm Q1 (schema-selection vs projection-prune) and fix at the projection/schema-selection layer in `@query/engine.py` / the offer & section schemas.
3. **[monolith sre — explicitly NOT a hotfix-guard]** Hold the consumer red until the producer contract lands; the daily exit-1 is the honest signal. (If an interim availability bridge is later ratified, it must be a *loud, ticketed, time-boxed* degrade — never a silent `.get()`.)
4. **[monolith sre — boy-scout, separate]** Extend the controller-exit alarm to the sibling controllers; dispose the un-migrated zombie schedule `autom8_refresh_asana_pr_frames_prod` (100%-failing direct Lambda, defer-watch `@.sos/wip/DEFER-WATCH-zombie-asana-pr-frames-schedule-2026-06-11.yaml`). Both are monolith-owned and tracked; named here only for coherence.

## 7. Assessment questions (for the autom8y-asana FPC owners)

- **Q1 (the one MODERATE link):** for the monolith's `Project.active_frame`/`activating_frame` get_df, does `/v1/query` select the **base/section** schema (no `offer_id`) or the **offer** schema (`OFFER_COLUMNS`)? Is `offer_id` projected-then-pruned (all-null drop), or never selected? (Decides schema-selection-fix vs projection-fix.)
- **Q2:** does FPC's population-contract have a slot for **consumer-required columns**, or is it producer-coherence-only? If the latter, is this the right time to add the consumer axis?
- **Q3:** can the coherence canary be extended to assert a **declared column set is present+populated** on a representative frame, RED-by-construction like the 571 canary?
- **Q4:** should `offer_id` + `project_gid` be unified into a single **column-fidelity workstream** in FPC Phase-2, or handled as point-fixes with the contract as follow-on?

## 8. Cross-references / art (verified live this session)

- **Consumer break:** `@/Users/tomtenuta/Code/autom8/apis/asana_api/objects/project/models/business_offers/main.py:164,203,223`
- **Producer schema (offer_id declared):** `@src/autom8_asana/dataframes/schemas/offer.py:42,93`
- **Contract derivation (section-completeness, not columns):** `@src/autom8_asana/query/engine.py:525` · model `@src/autom8_asana/query/models.py:432`
- **Bridge contract flag:** `@/Users/tomtenuta/Code/autom8/apis/asana_api/satellite/_bridge.py` (`HONEST_CONTRACT_FLAG`)
- **FPC initiative (the home):** `@.ledge/handoffs/HANDOFF-10x-dev-fpc-phase1-built-2026-06-09.md` · `@.know/telos/dataframe-resolution-coherence.md`
- **Sibling instance:** autom8 task `#85` (Section satellite missing `project_gid`)
- **S7 gate (shares the blind spot):** `@/Users/tomtenuta/Code/autom8/.sos/wip/frames/cr3-cutover-closure-procession.shape.md` §S7 · task #74
- **Spike that surfaced this:** `@/Users/tomtenuta/Code/autom8/.sos/wip/SPIKE-asana-pr-frames-modern-comparator.md` §2/§6
