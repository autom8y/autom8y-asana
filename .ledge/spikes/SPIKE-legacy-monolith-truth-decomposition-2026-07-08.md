---
type: spike
subtype: legacy-truth-decomposition
status: accepted
initiative: north-star-per-offer-economics
generated_at: 2026-07-08
generator: "ultracode workflow - 10 haiku sweepers + 3 provenance readers + 3 adversarial verifiers + 3-lens fable panel"
source: /Users/tomtenuta/code/a8/autom8
self_assessment_cap: MODERATE
not_a_reference_implementation: true
---

# SPIKE: Legacy Monolith Truth Decomposition

## Executive Summary

1. The legacy `autom8` monolith is a managed-performance ad agency for local health practices, not a self-serve SaaS; the practice (chiropractor) is the tenant root, billed via Stripe.
2. The commercial unit is `(office_phone, vertical)` — a practice's presence in one of ~50 hardcoded service categories (NOT 3), and this composite key survived decomposition into the modern `account_key`.
3. Offer is a global SKU; `business_offers` is the per-client `(office_phone, offer_id)` sale; the offer lifecycle is an Asana section state machine where transitions ARE the commercial events.
4. The funnel is leads → scheds → {patient | no-show | cancel}, and conversion truth (`status='patient'`) is minted by humans at the Asana consultation-feedback flow.
5. eCPS "effective" is a backward-looking status-ratio multiplier — hindsight, never forecast; zero probabilistic machinery exists in the monolith. This is the GAP-2 crown ruling.
6. Per-offer revenue is structurally unattributable by schema in BOTH systems: payments carry no FK to offers; terminal grain is `(office_phone, vertical_id)`, 1:many over business_offers.
7. The asset↔offer identity round-trip's write-back half was DROPPED in decomposition; `assets.offer_id` exists but is unpopulated — this is THE gap blocking spend→offer attribution.
8. Money-out (employee commissions/payouts), the Meta CAPI outbound conversion loop, and the conversion-truth write path are orphaned truths with no confirmed modern owner.
9. Verifiers killed a swath of doc-layer fabrications: "3 verticals," "CPA = spend/scheds," "20 minutes," "13 stages," "internal_costs eCPS," and a 20-month LTV revenue column that does not exist.
10. Evidence grade capped MODERATE: self-referential corpus, first-party file-reads, adversarially cross-checked; legacy code may lag current prod behavior.

---

## DISCLAIMER — READ BEFORE USE

> **Legacy `autom8` is NOT a reference implementation.**
> This document extracts **TRUTHS** — schema facts, formula lineage, and connection topology proven by direct file:line reads — for the purpose of ratifying modern-fleet decomposition decisions. It does **NOT** endorse legacy structure, formulas, or code as a target to reproduce. Several extracted truths are documented **defects** (type mismatches, unit bugs, non-attributability, format fragility) that are truths precisely because they explain observed behavior — not because they should be carried forward. Where the legacy's own documentation layer invented metric semantics, those inventions were **refuted** by verifiers and are recorded in the honesty ledger below, not in the truth sections. Business truth here is what the **formulas and schemas prove**, not what the docs say. Any claim without a file:line formula should be treated as uncertain and is flagged as such.

All anchors are legacy (`/Users/tomtenuta/code/a8/autom8/`) unless marked `[modern]`. "Modern status" compares against the 2026-07-08 fleet truth anchor (autom8y-data / autom8y-ads / autom8y-asana).

---

## 1. The Business Truths

*(Panel lens 1, edited for coherence. Modern-status tags carried; refuted variants excluded to the honesty ledger.)*

### 1.1 Commercial model and the tenant unit

**B1 — Managed-performance agency, not self-serve SaaS.** The root commercial entity is the practice: `sql/objects/chiropractors.py:13-138` (guid PK, `office_phone` UNIQUE, `stripe_id`, relationships to payments/leads/appointments/campaigns). The agency runs the client's Meta/TikTok ads, books appointments into the client's calendar, and bills the client via Stripe subscription. **Modern: CARRIED** — chiropractors remains tenant-root.

**B2 — The commercial unit is `(office_phone, vertical)`.** PhoneVerticalPair is the canonical composite key across insights, payments, and ad lifecycle (`sql/objects/insights.py:107` office_phone class-PK; payments `vertical_id` computed column). **Caveat (uncertain, flagged):** the "immutable" tenant key is operationally mutable — `sql/scripts/change_office_phone.sql` exists with no captured blast-radius/cache-invalidation procedure across S3 frames, `Businesses().df`, and Asana custom fields. **Modern: CARRIED** (`account_key = office_phone::vertical`; `business_id` REFUTED).

**B3 — Verticals are ~50 hardcoded service categories, not 3.** `apis/contente_api/models/vertical/main.py:19-80` defines ~50 enum members (CHIROPRACTIC, NEUROPATHY, WEIGHT_LOSS, DENTISTRY, OPTOMETRY, IV_THERAPY, ADHD, PSYCHOLOGY, MARKETING, PARTNER…) with a fragile **three-way registration contract**: enum member + `sql_verticals` row + `VERTICAL_NAMES` map (registration instructions at `:106-115`). Unknown verticals fail-fast to `Vertical.NONE` (offer-creation fail-fast) and fire a once-per-container Slack alert to `admin-ops` (`:82-120`); `db_verticals()` at `:12-16` shows enum and DB table are parallel sources of truth (drift hazard). **Modern: CARRIED** as dimension; the dyn-enum sync spike is the modern producer for this contract.

### 1.2 Offer, business_offer, and the section state machine

**B4 — Offer = global product SKU; business_offer = the per-client sale.** Offers carry `offer_id` (Integer autoincrement PK), `cost` (cents), `category`→vertical (`sql/objects/offers.py:24-46`); BusinessOffers is the `(office_phone, offer_id)` instantiation carrying commercial terms — `ad_spend` budget, `reserve_fee`/`reserve_cost`, `force_payment`, calendar/employee routing (`sql/objects/business_offers.py:30-79`). One SKU, many client instances (1:M). **Known scar (CONFIRMED):** `business_offers.offer_id` is `String(45)` FK to an Integer PK (`business_offers.py:35,37,53` vs `offers.py:27`). **Modern: CARRIED** — offer_level_stats armed at `(offer_id, office_phone, vertical)`.

**B5 — The offer lifecycle is an Asana section state machine, and section transitions ARE the commercial events.** The BusinessOffers project partitions offers into activating (5 states) → active (52 states incl. STAGING/STAGED/OPTIMIZE-*) → inactive (3); transitions trigger ad creation, approval, and budget reconciliation as side effects (business_offers SECTIONS; design-constraints TENSION-002). Asana custom fields are the authoritative business-metadata store; SQL holds analytical facts. **Modern: CARRIED** structurally — autom8y-asana senses this plane; state semantics still live Asana-side.

### 1.3 Funnel and conversion truth

**B6 — Funnel is leads → scheds → {patient | no-show | cancel}; conversion truth is minted by humans.** From `sql/objects/leads.py:1107-1174` (verifier-CONFIRMED): `scheds` = any appointment row with non-null status; `convs` = status `'patient'` ONLY; `ns` = `['no_show','no-show','reschedule']`; `nc` = `['cancelled']`. **Reschedules count as no-shows.** The terminal write is the Asana consultation-feedback flow: `sql_leads.put(id, status='patient', client_ltv=conv_amt)` (`process/consultation/pending_feedback/main.py:144-148`). **Modern: DRIFTED** — status partition remapped (reschedule moved ns→nc; convs widened to `patient|paid|finished`) and scheds redefined (COUNT_DISTINCT dedup + type='appt' filter + lead-creation-date attribution); **cross-cutover ns_rate/nc_rate comparisons are INVALID without status-level reconciliation.**

**B7 — Deep-funnel truth is distrusted; the business is managed from the upper funnel.** `ltv` is manually-entered `client_ltv` (cents/100) minted at consultation feedback; `roas = ltv/spend` rides on it. **Modern: CARRIED philosophically** — CohortMaturityGate demotes ltv (refusal signals S1-S3); CPS/eCPS remain the management surface, consistent with the agency framing. (The "20-month lead_conversions revenue LTV" story is REFUTED — see ledger.)

### 1.4 Cost vocabulary and the eCPS crown

**B8 — Cost vocabulary is exact and denominator-specific.** `CPL = spend/leads` (`df_utils.py:115-118`); `CPS = spend/scheds` (`df_utils.py:120-123`, SQL variant `insights.py:1901-1907`); `CPA = spend/convs` (`insights.py:1941-1949`, `df_utils.py:135-138`). Verifiers REFUTED both "CPA = spend/scheds" and "CPA = spend/leads" — denominator drift was endemic in the legacy's own docs. **Modern: CARRIED** for cps/cpl (None-on-zero replaces 0-on-zero; witness-cohort grain added).

**B9 — eCPS lineage (crown jewel): legacy "effective" is a hindsight failure-rate multiplier, not a forecast.** `ecps = cps × 1/(1 − nsr_ncr/rate_factor)` where `nsr_ncr = (ns_nc/solid_scheds)×100` and legacy `solid_scheds = scheds − fut_pen` is itself DETERMINISTIC (`sql/objects/insights.py:2296-2309`, `:2025-2033`, `:1736-1744`; verifier-CONFIRMED). A repo-wide grep for probability arrays / show-weights / `expected` returned ZERO hits. The stakeholder's "e means modeling over expectations" is UNSUPPORTED by both legacy and modern code. **Full ruling in §3.1 (GAP-2 input).**

**B10 — "20m" means per-20,000 impressions, a confidence-normalization for cross-offer comparison.** `lp20m = leads/(imp/20000)`, `sp20m = scheds/(imp/20000)` (`df_utils.py:167-185`). "20 minutes" and "20 months" readings are REFUTED fabrications. **Modern: DROPPED/unverified** — no confirmed counterpart.

### 1.5 Optimization levers and money paths

**B11 — Managed by threshold buckets and a composite health score.** Offers bucketed failing / at_risk / underperforming / performant off `GOOD_CPL≤$50`, `GOOD_CPS≤$150`, `GOOD_ECPS≤$215` (project insights main.py:23-25, 622-630); `offer_score` weighted from health_scoring `OFFER_WEIGHTS`; delivered via the CHI bot to the `customer-health` Slack channel. **Modern: CARRIED-WITH-DRIFT** (correcting a prior "DROPPED" flag) — `score_engine.py` / `bucketing.py` carry the failing/at_risk/underperforming/performant ladder, BUT `bucketing.py` uses generic 0/25/50/75 thresholds, so the **cost cutoffs (50/150/215) may have drifted — carry as a verify item.**

**B12 — Revenue is `(customer, vertical)`-grained Stripe billing with a typed payment taxonomy.** `billing_reason = '{vertical_id}•{payment_type}'` parsed by persisted `SUBSTRING_INDEX` computed columns (`sql/objects/payments.py:82-96`); payment types: ad_spend (client wallet passthrough), solution_fee (agency take), processing_fee, setup_fee, one_off (`stripe_api/api.py:423-451`). **Known live defect (CONFIRMED):** `setup_fee_payments` omits the `/100` divisor (`stripe_api/api.py:439-441`), propagating a unit bug into `total_payments`. **Modern: CARRIED verbatim** — same computed columns, same `•` delimiter, same no-validation fragility (INV-003); **setup-fee bug carry-status UNVERIFIED — canary it.**

**B13 — Per-offer revenue is structurally unattributable — by schema, not by accident.** No FK exists from payments to offers/business_offers; terminal revenue grain is `(office_phone, vertical_id)`, 1:many over business_offers (`payments.py:41-101`). Per-offer ROAS on actual payments was never possible. **Modern: CARRIED defect** — Payment model still has no `offer_id`. **Full ruling in §3.3.**

**B14 — "Budget" means Asana allocation, never platform truth; "spend" means platform actuals.** `campaigns.weekly_ad_spend` is written from the Asana task at put_record time and goes stale between saves (`campaign/main.py:77`); Meta's daily/lifetime/budget_remaining fields are fetched and discarded; actual spend is `ads_insights.spend` at `(ad, date, platform)` (`ads_insights.py:61,71`). The `"budget"` query dimension conflates the two sources with no enforcement (`ads_insights.py:911-927`). **Modern: PARTIALLY CARRIED** — ad-grain actuals kept separate; budget demoted to display dimension; full conflation resolution unverified.

**B15 — The client operates a prepaid ad wallet the agency meters out.** `balance` = rolling sum of payments in; `spent` = rolling ad spend out (14-day `SENSITIVITY_WINDOW`, `payments.py:38`); `diff = balance − spent` feeds `effective_balance`/`balance_units`, clamping daily budget multipliers — weekly cadence with a Wednesday anchor in V1, fixed horizon in V2 (`payments.py:184-208`; **V1/V2 formulas not re-verified this pass — flagged uncertain**). **Modern: CARRIED-WITH-DRIFT** (correcting a prior "DROPPED" flag) — budget reconciliation lives in autom8y-ads `reconciliation/service.py`, but DRIFTED: legacy `diff = budget − total_spent` → modern `variance = collected − spend` (`test_reconciliation_parity.py`); `balance_units` is now consumer-derived. **Sign-convention trap for name-porters.** The legacy rolling balance/spent/diff data substrate (`SENSITIVITY_WINDOW`, rolling_sum partition) was NOT located in the modern fleet — if dropped, the reconciliation capability has no modern data floor. **Flagged uncertain.**

**B16 — Money-out exists: employee commissions off the Asana Commission project (💰).** Paid on payroll-Tuesday cadence via CommissionBot posting Employee Commission Reports to Slack (`apis/slack_api/bots/commission/main.py:21-273`; plus payouts/reconciliations bots). A whole economics leg. **Modern: DROPPED/unaddressed** — grep of autom8y-data for `commission|payout` returned zero hits. **See §3.4.**

**B17 — The business closes the loop with ad platforms using its own funnel truth.** Meta CAPI events Lead→Schedule→InitiateCheckout→Purchase are pushed server-side with SHA-256-hashed PII; Purchase carries `conversion_value = leads.client_ltv` (`apis/meta_api/objects/conversion_event/*`; `purchase.py:82-87`). The agency's proprietary conversion data trains platform delivery. **Modern: DROPPED/unverified.** **See §3.4.**

---

## 2. The Data Truths + asana|sql Connection Topology

*(Panel lens 2. Deduplicated against §1 — entries here carry the schema/grain/key detail and the connection topology; commercial framing lives in §1.)*

### 2.1 Entity / Grain / Key Catalog

**D1 — Tenant root is dual-keyed; analytics collapses to office_phone.** `guid` (String(36) PK, system UUID) + `office_phone` (UNIQUE, operable business key) — `sql/objects/chiropractors.py:14-19,32`. **Modern: CARRIED** — `Chiropractor.__grain_columns__=['office_phone']`; `business_id` REFUTED; guid survives only as FK plumbing.

**D2 — PhoneVerticalPair is the canonical composite filter key.** `(office_phone, vertical)` filters every multi-tenant insight query. **Important nuance (verifier CONFIRMED):** `sql/objects/insights.py:107` is the ORM **class-level PK**, NOT row grain — query-time grain is dimension-driven. Downstream consumers must not treat insights rows as one-per-office_phone without checking the `stmt()` dimensions. **Modern: CARRIED** — `account_key = office_phone || '::' || COALESCE(vertical,'')`; multi-fact drill hardcoded to `['office_phone','vertical']`.

**D3 — Offer vs BusinessOffer vs Vertical are three distinct grains.** Offers = global SKU (`offer_id` Integer autoincrement PK, `offers.py:27`; cost in cents; `category` FK→`verticals.key`). BusinessOffers = operator-specific config, composite PK `(office_phone, offer_id)` + UniqueConstraint (`business_offers.py:35,37,53`), adds `ad_spend`, `reserve_fee`, `force_payment`. Cardinality 1 Offer → M BusinessOffers. **Type defect CARRIED live:** `business_offers.offer_id` `String(45)` FK to Integer PK — MySQL coerces. **Modern: CARRIED** — offer_level_stats grain `(offer_id, office_phone, vertical)`.

**D4 — Vertical is a ~50-value hardcoded enum with dual DB registration.** (Cross-ref B3.) Enum and DB table are parallel sources of truth (drift hazard); unknowns return `Vertical.NONE`. **Modern: CARRIED** as dimension.

**D5 — Appointment status vocabulary is the load-bearing denominator definition.** `sql/objects/leads.py:1110-1174` (re-verified): `scheds` = ANY non-null `appt_status` = 1; `convs` = `"patient"` ONLY; `ns` = `["no_show","no-show","reschedule"]`; `nc` = `["cancelled"]`; `ns_nc` = union. **Status vocabularies are NOT enum-constrained** — all raw `String(N)`. **Modern: DRIFTED** — partition remapped (`reschedule`→nc; convs widened to `patient|paid|finished`); scheds becomes COUNT_DISTINCT with type='appt' filter + lead-creation-date attribution (`[modern] library.py:632-660, 923-998`). **Modern registry has an internal cross-wiring defect** (comment "No shows (status=cancelled)" over a no-show/rescheduling condition, `library.py:920`) — **recommend cleanup before GAP-2 ratification cites these definitions.**

**D6 — Lead funnel grain is numeric `id`, joined to appointments by phone.** `Leads.id` PK autoincrement, `phone` UNIQUE (soft), `office_phone` FK→chiropractors; `Appointments.phone` FK→`Leads.phone`; `LeadConversions.lead_id` FK ON DELETE CASCADE (`leads.py:35-41`, `appointments.py:36-42`, `lead_conversions.py:14-45`). Appointments prefer `chiropractor_guid`, fall back to `office_phone` (defensive — signals missing guids in prod). **Modern: CARRIED** (grain), partial drift on attribution.

**D7 — `LeadConversions.event`(JSON) writers are Meta CAPI, not Asana.** The "possible inbound Asana sync" claim is REFUTED: writers are Meta Conversions-API event objects (`apis/meta_api/objects/conversion_event/*.py` → `sql_lead_conversions_temp.put`, e.g. `lead.py:48`, `schedule.py:56`, `purchase.py:66`). `event_name` = CAPI class name (`conversion_event/main.py:41`); `event_id = sha256(class.lead_id)` (`:43`). Server-side ad-conversion tracking pushed TO Meta.

### 2.2 Asana ↔ SQL Connection Topology

**D8 — Two-directional, identity-critical boundary.** Asana is source-of-truth for business metadata; SQL is system-of-record. **SQL→Asana:** `offer/update.py` Update.run() pushes `offer_id`, `ad_spend/100`→WeeklyAdSpend, cost, vertical enum, AssetId via BatchAPI. **Asana→SQL:** `BusinessOffers.get_df()` satellite projection → write-back to `business_offers`, `assets`, `asset_verticals`. Cadence: webhook/handler on-demand per gid (not batch polling); `update_businesses` ECS job (~4hr daily) re-hydrates. **Modern: PARTIALLY DROPPED** — the write-back half of the identity loop did not survive (see D11 / §3.2).

**D9 — The satellite/offer_contract seam is a dormant refusal guard over a live fossil bug.** The live project-entity satellite read projection OMITS `offer_id` → all `offer_id` NaN in consumer reads. The drop-mask silently excludes those rows at THREE sites (verifier-CONFIRMED): `business_offers/main.py:164-166` (activating), `:203-205` (active), `:223-226` (inactive) — `nan_offer_gids = _df.loc[_df["offer_id"].isna(),"gid"]; mask = ~_df["gid"].isin(nan_offer_gids)`. No error, log, or contract check on this path. `offer_contract.py:209-248` `assert_offer_contract()` (`DEFAULT_REQUIRED_COLUMNS=("offer_id",)`) would HARD-FAIL here but is DORMANT (no live call site). **Modern: the fossil has become permanent state** — the omission is now structural.

### 2.3 Identity Minting & the Four-Tuple Linkage

**D10 — `offer_id` is SQL-minted, Asana-echoed, SQL-written-back.** `offer/update.py:164-185,641-645`: when task name ≠ default AND `offer.offer_id` is None → `_create_offer()` POSTs to contente → `self.offer.offer_id = res.json.get("id", None)` → asserted non-null (raises OfferCreationError) → persisted via `sql_business_offers.put(office_phone=..., offer_id=..., **updates_needed)`. **Modern: CARRIED** shape.

**D11 — `asset_id` is a list, auto-provisioned from `(office_phone, vertical)`, stored as brittle text.** `asset_id.py:39-40`: when both `office_phone` and `vertical` present and field empty → `self.set(list(set([p.id for p in self.task.default_assets])))`. Stored in Asana TextList as `"[1,2,3]"` OR `"1,2,3"`; read coercion via `ast.literal_eval` + comma-split fallback (format-fragile). Junction: `asset_verticals` (asset_id FK→assets.id, vertical_id FK→verticals.id). **Modern: DROPPED write-back** — `assets.offer_id` FK column exists but is UNPOPULATED; `ad_creatives.asset_id` only ~18.7% populated. autom8y-asana AssetEdit knows the full `(office_phone, vertical, asset_id, offer_id)` tuple but has NO push path to autom8y-data. **This stranded identity is THE decomposition gap blocking spend→offer attribution (see §3.2).**

**D12 — The four-tuple was maintained SQL-side via FK chains, Asana-side via custom fields.** `assets.chiropractor_id`→`chiropractors.guid`→office_phone; `assets.offer_id`→`offers.offer_id`→`offers.category`→`verticals.key`; `asset_verticals` bridges asset↔vertical. **Collation mismatch** (`offers.category` utf8mb4_unicode_ci vs `verticals.key` utf8mb4_0900_ai_ci) forces explicit `collate()` in joins to avoid MySQL 1267 (`business_offers.py:636-644`). **Modern: DRIFTED** — office_phone/vertical resolved enrichment-side via 5-hop join, not denormalized-at-write; **[modern]** `Adset.offer_id` FK target changed from `business_offers.guid` to global `offers.offer_id` (`_advertising.py:53`), and the assets-offers path is priority-1 preferred (but unpopulated, so the deprecated adset path actually carries resolution — an inverted preference; `canonical_paths.py:473-498`).

### 2.4 Money Paths

**D13 — Meta spend → SQL at ad×day×platform grain; "budget" is a misnamed Asana allocation.** `ads_insights.spend` Float (cents), PK `(ad_id, date, platform)`, metric SUM→Integer (`sql/objects/ad_objects/ads_insights.py:61,71,109-115`). Meta's daily_budget/lifetime_budget are FETCHED but NEVER persisted. The conflation at `ads_insights.py:911-927`: dimension `("weekly_ad_spend","budget")` returns `case(Campaigns.weekly_ad_spend>0 → weekly_ad_spend; BusinessOffers.ad_spend>0 → ad_spend/100; else None)` — ALLOCATION (Asana config, offer-save-stale), NOT Meta actuals. **Modern: CARRIED** (actuals kept separate; budget as ANY_VALUE display-only dimension, `[modern] library.py:1330`). **New modern failure mode:** enrichment-side join means orphan/chain-break rows (NULL adset_id/campaign_id) silently fall out of tenant-scoped spend — a failure legacy denormalization did not have.

**D14 — Stripe payments → SQL; vertical/type derived from bullet-delimited `billing_reason`.** `payments.amount` Integer cents; `dedupe_key = coalesce(invoice_number, cast(id))` (`:103-115`); `vertical_id`/`payment_type` are persisted COMPUTED columns via `SUBSTRING_INDEX(billing_reason,'•',...)` (`:82-96`). Minted at ingest as `f'{vertical_id}•{payment_type}'` (weak; defaults to 0/chiropractor default). Refunds negated (×−1, `pull_payments/controller.py:103`). `SENSITIVITY_WINDOW=14d` hardcoded (`:38`). `amount` metric SUM cast Integer, coalesce 0, divisor=100, distinct by (dedupe_key, invoice_status) — verifier CONFIRMED. **setup_fee_payments unit bug CONFIRMED** (missing /100, `stripe_api/api.py:439-441`). **Modern: CARRIED verbatim** — same Computed columns, same fragility (INV-003; `vertical_id` str here but int elsewhere).

**D15 — Payment→Offer attribution is STRUCTURALLY IMPOSSIBLE.** Payments have NO FK to offers/business_offers; only `office_phone`→chiropractors. Terminal revenue grain is `(office_phone, vertical_id)`, 1:many over business_offers. `business_offers.ad_spend` exists but is manual Asana config, never fed from payments. **Modern: CARRIED as a defect, not a regression** (`[modern] _platform.py:306-440` — no `offer_id`). **Full ruling in §3.3.**

**Tenant-key mutability caveat (uncertain, flagged):** `sql/scripts/change_office_phone.sql` (re-verified to exist) MUTATES the "immutable" tenant key by hand — no captured blast-radius/cache-invalidation procedure. (Cross-ref B2 caveat.)

---

## 3. Decomposition Gap Rulings

*(Panel lens 3. Rulings are DECOMPOSITION verdicts against the modern fleet. The eCPS/effective ruling is FIRST and is explicitly a GAP-2 ratification INPUT — the stakeholder decides; this is evidence, not a verdict.)*

### 3.1 eCPS / "effective" lineage — the crown ruling — **GAP-2 RATIFICATION INPUT (evidence, not verdict; stakeholder decides)**

**Legacy maintained:** `effective` is a *backward-looking status-ratio multiplier*, nothing more. `sql/objects/insights.py:2296-2309`: `effective_clause = 1 − (nsr_ncr/rate_factor)`, `ecps = case(effective_clause > 0, round_cast_num(cps × (1/effective_clause)), else_=0)`, where `nsr_ncr = (ns_nc/solid_scheds)×rate_factor` (`:2025-2033`) and legacy `solid_scheds = scheds − fut_pen` (`:1736-1744`) is itself DETERMINISTIC. A repo-wide grep for probability arrays / show-weights / `expected` returned **ZERO hits** (verifier CONFIRMED). The monolith inflates observed CPS by the *historically-observed* no-show+cancel rate.

**Modern fleet does:** `ecps = spend/effective_scheds`, where `effective_scheds` is a *status-filtered denominator* — `COUNT_DISTINCT` appointments with status ∈ {scheduled, confirmed, pending, patient, requested, rescheduled} (`[modern] autom8y-data insights/library.py:1024-1049, 2504-2519`). Separately, `solid_scheds` is *re-minted* as a probability-weighted denominator (pending 0.30, fut_confirmed 0.80, fut_scheduled 0.50, fut_requested 0.40, fut_rescheduled 0.55; `[modern] library.py:2292-2340`) feeding RATE metrics ONLY — **never eCPS** (`[modern] library.py:2288-2290` explicitly disambiguates).

**Verdict: DRIFTED.** Same *intent* (cost per non-lost schedule), incompatible *algebra*: legacy scales the numerator-ratio up; modern shrinks the denominator set. **Values will not reconcile** when statuses distribute unevenly.

**GAP-2 recommendation (INPUT to ratification, NOT a verdict — stakeholder decides):**
- Adopt **`effective_scheds` (the status-filter candidate) as the legitimate heir**, and **reject the stakeholder's "e = modeling over expectations" reading.** Legacy evidence is dispositive on intent: `effective` was *always hindsight, never forecast*; the modern status-filter preserves that semantic. `solid_scheds`'s probabilistic weighting is a **NET-NEW invention** that must not be back-fitted onto the "e".
- **Two hazards flagged for ratifiers:** (a) the UI label "Expected CPS" matches *neither* legacy nor modern algebra and should be renamed; (b) modern reuses the legacy identifier `solid_scheds` with changed semantics (legacy: deterministic `scheds − fut_pen`; modern: probability-weighted) — a **name-collision trap** for anyone porting formulas by name; modern `nsr_ncr` also inherits `NOW()`-dependent snapshot contamination (`[modern] library.py:2447-2475`).
- **Owner: autom8y-data** (registry definition + central ratification).

### 3.2 Asset↔offer identity linkage — the load-bearing loss

**Legacy maintained:** a *closed round-trip*. `offer_id` minted in SQL → pushed to Asana `OfferId`/`AssetId` custom fields → written back to `business_offers` + `asset_verticals`; `assets.offer_id` FK populated by this loop (`offer/update.py:164-655`, `asset_id.py:39-40`). Asana knew *and persisted* the `(office_phone, vertical, asset_id, offer_id)` four-tuple into SQL. (Cross-ref D10-D12.)

**Modern fleet does:** the *read* half survives; the *write-back* half is gone. `[modern] assets.offer_id` exists as an FK (`_advertising.py:165`) but is UNPOPULATED; `ad_creatives.asset_id` only ~18.7% populated (documented in-schema, `_advertising.py:235-241`). autom8y-asana `AssetEdit` still *knows* the full tuple (`models/business/asset_edit.py:121-160`) but **no push path to autom8y-data exists.**

**Verdict: DROPPED.** The single decomposition gap that structurally blocks spend→offer attribution. The legacy "fossil bug" (project-entity read omitting `offer_id`, D9) has effectively become the *permanent modern state* — knowledge is stranded Asana-side. **Consequence:** per-offer spend is unresolvable except via the fragile adset fallback; `[modern] canonical_paths.py` *prefers* the unpopulated `ASSETS_OFFERS_PATH` (priority-1) over the working `ADSETS_OFFERS_PATH` (priority-2), so the "preferred" path silently no-ops.
- **Owner: autom8y-asana** (build the AssetEdit→data push) **+ autom8y-data** (accept + backfill `assets.offer_id`).
- **Watch (flagged):** if `assets.offer_id` is ever backfilled, join behavior flips silently from adset-fallback to asset-primary — worth a canary. (Note: "unpopulated" is a DATA-state claim not verifiable from schema code alone; the FK column exists.)

### 3.3 Payment→offer non-attributability — CARRIED (a defect, not a regression)

**Legacy maintained:** payments have NO FK to offers/business_offers; terminal revenue grain is `(office_phone, vertical_id)` (`payments.py`; deep-read B). **Modern fleet does:** identical — `[modern] Payment` model (`core/models/_platform.py:306-440`) has `office_phone` FK + computed `vertical_id`, no `offer_id`.

**Verdict: CARRIED.** `(office_phone, vertical)` remains 1:many over `business_offers`, so per-offer REVENUE and per-offer ROAS-on-actual-payments are structurally impossible in *both* systems. Inherited limitation, not a decomposition break — **but combined with §3.2, neither the spend leg nor the revenue leg can reach offer grain, so offer-level ROAS is DOUBLY BLOCKED.** The `billing_reason` `'{vertical_id}•{payment_type}'` SUBSTRING_INDEX fragility carried verbatim (`[modern] _platform.py:415-433`), including no-validation/malformed-input risk.
- **Owner: autom8y-data** (would require a schema decision to attach `offer_id` at ingest; likely out of scope — **recommend documenting as a permanent constraint**).

### 3.4 Orphaned truths — legacy encoded, NO modern service confirmed owner

- **Employee commissions / payouts** (`slack_api/bots/commission`, `payouts`, `reconciliations`): a whole money-*out* economics leg (payroll-Tuesday commission computation off the Asana 💰 project). Grep of autom8y-data for `commission|payout` returned ZERO hits. **Verdict: DROPPED (or un-migrated).** Owner TBD — likely autom8y-data (economics) or a future payouts service.
- **Meta CAPI outbound conversion loop** (SQL→Meta, `conversion_event/{lead,schedule,initiate_checkout,purchase}.py`; Purchase carries `conversion_value = client_ltv`): the *only* SQL→ad-platform outbound direction; no modern facet or repo owns it. **Verdict: unverified/ORPHANED.** Candidate owner: autom8y-ads. (Monitored by `terraform/observability_meta_capi.tf`, `cron(0 14 * * ? *)`.)
- **Conversion-truth write path** (`process/consultation/pending_feedback/main.py:144-148` writes `status='patient', client_ltv=conv_amt`): where a lead *becomes* a conversion — terminal funnel truth. No modern writer located. Candidate owner: autom8y-asana (conduction) → autom8y-data.
- **Vertical definition mechanism**: the ~50-value hardcoded `Vertical(Enum)` with a three-way dual-registration contract (enum + `sql_verticals` + `VERTICAL_NAMES`, `vertical/main.py:19-120`) — a load-bearing enum-vs-DB drift risk absent from the corpus. Intersects the live dyn-enum-contract work; **owner: autom8y-asana (producer) + autom8y-data (consumer).**

### 3.5 Staleness findings worth carrying (decomposition-relevant)

- **`setup_fee_payments` /100 divisor bug** (`stripe_api/api.py:439-441`, CONFIRMED): cents-vs-dollars inconsistency propagating into `total_payments`. Modern Stripe-ingest path NOT inspected — **carry as a canary: verify the divisor bug did not survive.**
- **Health-scoring DID carry** (correcting a prior "MISSING" flag): `offer_score`/bucket ladder lives in autom8y-data (`score_engine.py`, `bucketing.py`). **Verify** the legacy `GOOD_CPL=50/GOOD_CPS=150/GOOD_ECPS=215` cutoffs transferred — `bucketing.py` uses generic 0/25/50/75 thresholds, so the *cost cutoffs* may have drifted.
- **Budget reconciliation DID carry** into autom8y-ads (`reconciliation/service.py`) but **DRIFTED**: legacy `diff = budget − total_spent` (budget-centric) → modern `variance = collected − spend` (collection-centric), per `test_reconciliation_parity.py`. `balance_units` now consumer-derived. **Sign-convention trap for name-porters.**
- **`business_offers.offer_id` String(45)-FK-to-Integer-PK mismatch** and **`Adsets.offer_id`→`business_offers.guid`** (a non-unique, non-PK String(36) column — semantically/typologically broken, not a clean operator+offer link) both CONFIRMED live; the modern fleet re-pointed `Adset.offer_id` to `offers.offer_id` (int) — cleaner FK but a changed join target that **invalidates naive legacy-vs-modern adset joins.**

---

## 4. Staleness + Refuted-Claims Ledger (Honesty Section)

*What the verifiers killed. Recorded here so these fabrications never re-enter the truth sections.*

### 4.1 REFUTED metric/semantics claims

| Claim (as asserted by legacy docs/facets) | Verdict | Ground truth (file:line) |
|---|---|---|
| eCPS := `(spend + internal_costs)/scheds` ("operational overhead") | **REFUTED** | No `internal_costs` term anywhere in `sql/`. Actual: `ecps = cps × 1/(1 − nsr_ncr/rate_factor)`, `insights.py:2296-2309` |
| CPA := `spend/scheds` | **REFUTED** | `cpa = spend/convs`, `insights.py:1941-1949`, `df_utils.py:135-138` (spend/scheds is CPS) |
| CPA := `spend/leads` | **REFUTED** | That is CPL; `cpa = spend/convs` |
| conversion_rate := `lead_clicks/leads` | **REFUTED/UNSUPPORTED** | `conv_rate = convs/(scheds − fut_pen)`, `df_utils.py:145-150` |
| lp20m := "Landing Page visits within 20 minutes" | **REFUTED** | `leads/(imp/20000)` — per-20k-impressions, `df_utils.py:167-170` |
| sp20m := "Schedule Page visits within 20 minutes" / "scheduled_sales/20m" | **REFUTED** | `scheds/(imp/20000)`, `df_utils.py:177-180` |
| lctr := `lclicks/contacts` | **REFUTED** | `lclicks/imp`, `df_utils.py:105-108`; SQL variant per-1k-imp×rate_factor, `insights.py:1857-1862` |
| ltv := sum(`lead_conversions.revenue`) over 20-month window / leads | **REFUTED** | `lead_conversions` has NO revenue column (`lead_conversions.py:17-44`); LTV from `leads.client_ltv/100` (`leads.py:135-142`) |
| "Three verticals partition the market" | **REFUTED** | ~50 verticals, `vertical/main.py:19-80` |
| Core pipeline = ProcessProject with "13 lifecycle stages" | **UNSUPPORTED** | Tree shows 9 pipeline models + 19 consultation types; "13" matches neither; "activation" is not a model |
| approval_completion := `count(approval≠'pending')/count(tasks)×100`; 4-value approval vocab | **UNSUPPORTED** | Own evidence admits "enum values not hardcoded"; formula + vocab fabricated |
| targeting_effectiveness := `sum(platforms)×radius_miles`; JSON targeting payload | **UNSUPPORTED** | No formula/schema at cited locations; only custom-field existence. Same pattern: offer_engagement, pipeline_stage vocab |
| Lead statuses {new, contacted, converted}; Appt {pending, completed, no_show, cancelled} | **UNSUPPORTED** | Cited lines show only `String(20)` columns. Actual appt literals: {pending, patient, no_show, no-show, reschedule, cancelled} (`leads.py:1125-1201`) |
| `LeadConversions.event` JSON stores Asana webhook events | **REFUTED** | Writers are Meta CAPI (`conversion_event/*.py`) — outbound to Meta, not Asana inbound |

### 4.2 CONFIRMED defects/facts (truths that are bugs)

- `setup_fee_payments` missing `/100` divisor — `stripe_api/api.py:439-441` (propagates into `total_payments` `:461+`).
- `business_offers.offer_id` `String(45)` FK to Integer PK — `business_offers.py:35,37,53` vs `offers.py:27`.
- `Adsets.offer_id` Integer FK to `business_offers.guid` (String(36), non-unique, non-PK) — `adsets.py:39,47` — typologically broken.
- Live business_offers frames silently drop NaN-`offer_id` rows at 3 sites — `business_offers/main.py:164-166, 203-205, 223-226`.
- `sql/scripts/change_office_phone.sql` mutates the "immutable" tenant key with no captured procedure.
- `Session.OK = (200,201,202,…,226)` IS defined (`utils/requests/session.py:15`) — REFUTES the stale "Session.OK never defined / likely {200,201,204}" flag.

### 4.3 NOT re-verified this pass (carry as uncertain — do NOT round up)

- S3/CacheService TTL claims (300s task / 120s Offer TTLs, SECTION_DF_CACHE line ranges); batch_api mechanics (SCAR-021 `modified_at`); `Task.__new__` factory routing.
- Reconcile budget V1/V2 formulas (`planned_spend`, `balance_units`, `effective_balance`, `V2_HORIZON_DAYS`) — file paths cited but not opened.
- Protocol-docs cadence/SLA claims (`AUTOM8_PROTOCOL.md`, p50/p99 targets); Meta/TikTok API dimension claims (`BASE_INSIGHTS`, TikTok daily-insights endpoint).
- Modern Stripe-ingestion path (setup-fee bug carry-status unknown); legacy rolling balance/spent/diff substrate presence in modern fleet.
- Payment `payment_type` vocab modern carry-status; `Leads.channel`, `Calls.status`, `Payments.invoice_status` value sets (deep-read surfaced PAID|REFUNDED|VOIDED|UNPAID for invoice_status but no facet carries it).

### 4.4 Coverage gaps surfaced but out-of-scope for the data-plane rulings (flagged, not resolved)

Money-out bots (chi/commission/payouts/reconciliations); appointment sources beyond Calendly (email-parse `sync_booking`, GHL calendars, TrackStat); calls/messages ingestion (GHL `pull_highlevel_messages`, Twilio Calls, transcription pipeline); client ad-approval web surface (`pages/ad_previews/`); ~2/3 of the entry-point inventory (handlers, ECS jobs, `runs/` data-destruction ops, FastAPI serving shell); geo/demographic targeting subsystem (`data/us_tracts_with_acs.gpkg`, census/geonames/zipcode APIs); ~30 `apis/` sub-packages with live-vs-dead status unestablished. `.archive/` is a confirmed NON-GAP (only archived poetry files).

---

## Evidence Grade Footer

**Grade: [STRUCTURAL | MODERATE].**

- **STRUCTURAL** for schema/grain/key/formula claims carrying an exact file:line anchor confirmed by first-party file-reads and adversarial cross-check.
- **MODERATE ceiling** enforced by self-referential-evidence-grade discipline: the corpus is self-referential (the fleet auditing its own legacy origin), so no claim rises to STRONG without external corroboration.
- All truth-section claims are first-party file-reads, adversarially cross-checked by three verifier lenses (code-support, modern-coherence, completeness); refuted claims are quarantined to §4.
- **Legacy code may lag current production behavior.** Modern-status tags reflect the 2026-07-08 fleet truth anchor, not live prod verification. Uncertain claims are carried flagged, not rounded up.
- **`not_a_reference_implementation: true`** — legacy is a source of truths, not a target to reproduce.
