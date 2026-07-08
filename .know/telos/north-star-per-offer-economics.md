---
type: telos
initiative_slug: north-star-per-offer-economics
authored_at: 2026-07-08T00:00:00Z
authored_by: main-thread (Claude) at OPERATOR DIRECTION — drafted for ratification; user-sovereign per telos-integrity-ref §3 Gate-A
ratified_by: "operator (Tom Tenuta) — countersigned 2026-07-08 (as-amended on landing, rounds 1+2)"
rite: "cross-rite crusade (C-0 probe/investigation · C-1 CROSS-REPO dimension-feed: 10x-dev asana-side + data-analyst/DRE data-side · GAP-2 eCPS ratification: data-analyst+DRE+STAKEHOLDER · C-2 hygiene/data-analyst coverage-floor · C-3 know/hygiene · C-4 observability/ops PARKED · C-5 security · C-6 NEW 10x-dev defect-repair + data-analyst co-diagnose · eunomia rite-disjoint close) — per-crusade rite assignment emerges in the shape. AMENDED 2026-07-08: C-1 re-scoped producer-build -> dimension-feed per the two 2026-07-08 spikes; ROUND-2 adds C-6 SD-02 repair, orphan disclosure, pre-2025 ANY-platform join."
schema_version: 1
code_truth_anchor: "local HEAD f3d8eec1 (main) — re-anchored by myron at frame-authoring via `git rev-parse HEAD`; NOT inherited blindly. Prior arc (asana-realization-tail-convergence) closed at d7a136c3 per PT-E; HEAD advanced to f3d8eec1 (#198 tier-1 opt_fields). Feature census INDEX pinned stale at 8980bcd7 — that staleness is itself a C-3 signal."
ratification_status: "RATIFIED 2026-07-08 — operator (Tom Tenuta) countersigned 2026-07-08 (standing countersign 'as-amended on landing', rounds 1+2). Gate-A CLOSED — the MAIN THREAD verified this amendment (rounds 1 and 2) against the THREE spike rulings (the two 2026-07-08 premise spikes: SPIKE-c0-denominator-probe-ruling + SPIKE-legacy-monolith-truth-decomposition; ROUND-2: SPIKE-asset-linkage-coverage-measurement, ALL 4 legs MEASURED LIVE against prod RDS, zero blocked) and flipped it. Dispatch UNBLOCKED. The two [OPERATOR-SET] draft values (`verification_deadline` = 2026-07-29 SET AT GATE-A CLOSE per draft guidance formula (C-0 FULLY discharged, GAP-2 ratified, fork RULED — gate satisfied; ~3wk per predecessor precedent; operator may amend); `rite_disjoint_attester` = eunomia, rite-disjoint from all author rites, three-evidence-leg at close, UV-P-7 Bash caveat carried) are blessed-as-drafted per the predecessor's countersign-as-drafted precedent unless the operator amends."
---

# Telos Declaration — north-star-per-offer-economics (Real-Time Per-Offer Unit Economics)

> **RATIFIED 2026-07-08 — operator (Tom Tenuta) countersigned, as-amended on landing (rounds 1+2).** Drafted by the
> main thread at operator direction (user-sovereign per `telos-integrity-ref` §3 Gate-A),
> mirroring the dyn-enum / asana-realization-tail-convergence precedent. The telos block below is carried **VERBATIM** from
> the frame (`.sos/wip/frames/north-star-per-offer-economics.md` frontmatter, myron
> 2026-07-08, AMENDED by pythia 2026-07-08 rounds 1+2). Both **[OPERATOR-SET]** fields approved
> as-amended at Gate-A close (`verification_deadline` 2026-07-29 · `rite_disjoint_attester` eunomia, UV-P-7 Bash caveat carried to close empanel).
> **Gate-A is CLOSED** — track dispatch is unblocked per the standing countersign
> (`.sos/wip/frames/north-star-per-offer-economics.shape.md` pythia forthcoming — the
> shape models C-0 FULLY DISCHARGED + C-1…C-6 cross-repo seams + rite transitions; the first
> cross-rite sync gates on C-0 live-prod iris leg complete). Amendable at any `/frame`.

```yaml
telos:
  initiative_slug: north-star-per-offer-economics

  inception_anchor:
    framed_at: "2026-07-08"
    frame_artifact: ".sos/wip/frames/north-star-per-offer-economics.md"
    why_this_initiative_exists: >
      An offer-portfolio (Hormozi-style) business's atomic decision unit is the individual
      OFFER, yet leadership sees only book-wide MRR (metrics/definitions/offer.py:26-45 defines
      active_mrr as a phone+vertical-deduped COMPANY-level P&L line) and a single pooled
      ad-spend number (active_ad_spend, same dedup) — every reallocation is intuition, not data.
      No metric anywhere joins a payment amount to an offer_id/offer_gid; the north-star number
      has NO PRODUCER. This arc stands ON the integrity substrate the CLOSED predecessor
      (asana-realization-tail-convergence, verified_realized ATTESTED-WITH-FLAG) laid: (a) all
      five knowledge registers now read TRUE against the code at a fresh SHA (register-reality
      drift ended), and (b) the drift-audit-discipline was promoted to a knossos FLEET PRIMITIVE
      (knossos/rites/shared/mena/drift-audit-discipline/INDEX.lego.md). Records-truth is no
      longer the debt; PRODUCING a trustworthy per-offer P&L is. Two of the three blockers are
      plausibly solved-in-code-but-dark and the $0-dashboard defense already exists as a
      three-part built guardrail — so the entry move is a NO-CODE live probe (C-0) that SIZES
      the build, not a build.
      AMENDMENT 2026-07-08 (pythia re-frame, grounded at SPIKE-c0-denominator-probe-ruling +
      SPIKE-legacy-monolith-truth-decomposition): the C-0 probe CODE-HALF has now DISCHARGED and
      RESHAPED this premise. The stakeholder interview corrected the business: this is a marketing
      AGENCY optimizing CLIENT-side campaign offers; per-offer REVENUE is structurally
      non-attributable in BOTH legacy and modern (payments terminate at (office_phone, vertical),
      1:many over business_offers, NO FK to offers — legacy spike §3.3 / D15; modern
      _platform.py:306-440). Operator decision: the north-star number is per-offer COST-EFFICIENCY
      (CPS/eCPS on ACTUAL ad spend) THIS ARC, no proxy revenue allocation. And the CPS/eCPS pipeline
      ALREADY LARGELY EXISTS in autom8y-data (cps=spend/scheds, ecps=spend/effective_scheds; ARMED
      offer_level_stats at offer grain; EntityMetrics.cps/ecps exposed; asana consumes at
      frame_type="offer"; HTML report renders CPS). The real work is a DIMENSION-FEED
      (asana pushes the AssetEdit (office_phone, vertical, asset_id, offer_id) enrollment it already
      EXTRACTS but never pushes — asset_edit.py:106,127; gid_push has NO offer_id push surface,
      grep -c offer_id = 0 SVR-confirmed) + an eCPS DEFINITION RATIFICATION (GAP-2, operator-
      sovereign) + a COVERAGE-TRUST floor (GAP-3, now load-bearing) + a SURFACE-EXPOSURE. The C-0
      LIVE-PROD-HALF remains owed to iris. See the amended statement + success_criteria below.
      ROUND-2 GROUNDING (2026-07-08, SPIKE-asset-linkage-coverage-measurement — ALL 4 legs MEASURED
      LIVE against prod RDS nhc-db, zero blocked legs; C-0 now FULLY DISCHARGED): junction-path spend
      coverage among hierarchy-intact rows = 2024 99.6% / 2025 98.8% / 2026 100.00% (the operator
      confirmed exactly — the 18.7% direct-column figure measured the WRONG path and is retired). The
      P&L attribution key is adsets.offer_id, MEASURED 66,350/66,354 = 99.99% populated — so per-offer
      spend/CPS rides ads_insights -> ads -> adsets.offer_id, and assets.offer_id (2,444/42,511 = 5.7%
      fleet-wide; 62.4% of the 2026 cohort) is NOT an attribution key. The REAL modern coverage hole is
      ORPHAN AD_IDS: 11.6-14.1% of 2024-2026 spend sits on ads_insights.ad_id values with NO ads row at
      all (hierarchy-incomplete, not asset-linkage). assets_ad_creatives = 93,768 rows. Shared assets
      are the MAIN BODY of spend (57.9% of asset-linked spend flows to NULL-offer_id assets; 792 assets
      span >1 operational offer) — SHARED-BY-DESIGN confirmed. TWO DEFECTS gate denominator quality:
      (1) orphan ad_ids (backlog-with-trigger + surface disclosure); (2) account_status (SD-02 registry)
      is EMPTY in prod (0 rows, MAX(synced_at)=NULL — the 4h cache-warmer push is not landing). Also:
      pre-2025 history needs an ANY-platform junction join (the facebook->meta enum-drift era; the
      canonical platform-matched join undercounts pre-2025 spend by up to ~60%).

  statement: >
    [SUPERSEDED-BY the two 2026-07-08 spikes — original preserved below the line for records-truth.]
    AMENDED STATEMENT (2026-07-08 pythia re-frame): The agency makes per-offer
    KILL / SCALE / REPRICE / ALLOCATE decisions on real per-offer COST EFFICIENCY (CPS/eCPS on
    ACTUAL ad spend), not book-wide sums — the per-offer CPS/eCPS number (which ALREADY EXISTS in
    autom8y-data) goes LIVE and TRUSTWORTHY on a leadership surface, made real by: (1) a CROSS-REPO
    DIMENSION-FEED — autom8y-asana pushes the AssetEdit (office_phone, vertical, asset_id, offer_id)
    enrollment it already extracts but never pushes, so autom8y-data populates assets.offer_id and
    offer-grain spend lights up via the /query path (NOT the account-locked /drill); (2) the eCPS
    "effective" definition RATIFIED with the stakeholder (GAP-2 — an operator-sovereign checkpoint
    that GATES the number being called trustworthy); and (3) the coverage/population floor (now
    LOAD-BEARING, because ad_creatives.asset_id is only ~18.7% populated per an in-code figure) wired
    as a live alarm so partial-coverage spend is alarmable, not silently under-counted. The
    denominator + coverage state is confirmed BEFORE the feed is built (C-0 gates C-1). Trust bar:
    reconciled-strict to autom8y-data db.md truth. Win bar: the number LIVE + TRUSTWORTHY on a
    surface (value-in-use not required this arc). Build home: cross-repo (asana feeds, data computes).
    ROUND-2 (2026-07-08, measurement spike landed): FORK-SHARED-ASSET-GRAIN is RULED —
    ADSET-DECLARED ATTRIBUTION + VERTICAL-POOLED ASSETS. Per-offer spend/CPS attributes via
    adsets.offer_id (MEASURED 99.99% populated), the P&L-critical data-side path being the
    ads_insights -> ads -> adsets.offer_id join (ANY-platform for pre-2025 history per the
    facebook->meta enum-drift finding). The AssetEdit dimension-feed DEMOTES to a SUPPORTING leg
    (the DEDICATED-vs-SHARED signal + dedication tracking for vertical-pooled creative intelligence),
    non-P&L-critical; assets.offer_id (5.7%) is NOT promoted to an attribution key. The arc SHIPS at
    ~86-88% coverage with the ORPHAN-AD_IDS spend share (11.6-14.1%, no ads row) VISIBLY DISCLOSED on
    both win surfaces (the number is honest about its denominator); orphan-ingestion is a data-analyst
    backlog item. A NEW leg C-6 repairs the EMPTY account_status (SD-02) registry that the coverage
    floor depends on. C-0 is FULLY DISCHARGED.
    Autonomy: autonomous to the merge/prod line (agents open PRs; never merge/flip prod flags).
    #
    # --- ORIGINAL STATEMENT (SUPERSEDED 2026-07-08; preserved, not deleted) ---
    #   "a per-offer payment-linked REVENUE metric joins payment amounts to offer_id and is
    #    registered; ... the built population-receipt floor is wired as a live alarm so the number
    #    is trustworthy, not silently degraded to $0. The denominator is confirmed BEFORE the
    #    producer is built (C-0 gates C-1)."
    #   SUPERSEDED because: per-offer revenue is structurally non-attributable (payments 1:many over
    #    offers, no FK — legacy §3.3/D15, modern _platform.py); and the metric is not a build
    #    (it exists in autom8y-data) but a DIMENSION-FEED. Per SPIKE-c0-denominator-probe-ruling +
    #    SPIKE-legacy-monolith-truth-decomposition, 2026-07-08.

  success_criteria:  # AMENDED 2026-07-08 (pythia re-frame). VERBATIM downstream; no paraphrase. Original KR1 SUPERSEDED-BY the two 2026-07-08 spikes (revenue -> cost-efficiency dimension-feed); preserved at the bottom of this block.
    - "ATTRIBUTION-KEY (KR1, RULED ROUND-2 2026-07-08 by the measurement spike): per-offer spend/CPS attributes via ADSETS.OFFER_ID — the ads_insights -> ads -> adsets.offer_id join (MEASURED 66,350/66,354 = 99.99% populated; ANY-platform join for pre-2025 history per the facebook->meta enum-drift finding). This is the P&L-critical data-side path. assets.offer_id (5.7% fleet-wide) is NOT promoted to an attribution key; the AssetEdit dimension-feed DEMOTES to a SUPPORTING creative-intelligence leg (the DEDICATED-vs-SHARED signal + dedication tracking, vertical-pooled), non-P&L-critical. FORK-SHARED-ASSET-GRAIN is thereby RULED: ADSET-DECLARED ATTRIBUTION + VERTICAL-POOLED ASSETS (assets stay intentionally cross-offer; 57.9% of asset-linked spend is shared)."
    - "DIMENSION-FEED (KR1b, was 'PRODUCER'; DEMOTED ROUND-2 to a supporting leg): the per-offer CPS/eCPS number — which ALREADY EXISTS in autom8y-data (cps=spend/scheds library.py:1939-1987; ecps=spend/effective_scheds library.py:2504-2519; ARMED offer_level_stats at grain [offer_id,office_phone,vertical] library.py:1295-1375; EntityMetrics.cps/ecps _insights.py:187-190; asana consumes at frame_type='offer' data_service_entities.py:45-181; HTML report renders CPS formatter.py:70-112) — goes LIVE on a leadership surface by CLOSING the asset<->offer dimension: autom8y-asana PUSHES the AssetEdit (office_phone, vertical, asset_id, offer_id) enrollment it already EXTRACTS but never pushes (asset_edit.py:106,127 SVR-confirmed; gid_push has NO offer_id push surface, grep -c offer_id = 0), autom8y-data POPULATES assets.offer_id, and offer-grain spend lights up via the /query SQL-GROUP-BY path (NOT the account-locked /drill — GAP-5 SCAR-027). The legacy spike CONFIRMS this linkage existed in the monolith and was DROPPED in decomposition (§3.2/D11; canonical_paths.py prefers the unpopulated assets-offers path and silently no-ops). GAP-1 DOMAIN CORRECTION (operator interview 2026-07-08): assets are INTENTIONALLY cross-offer — creatives are deliberately reused across offers WITHIN equivalence classes (same-cost | same-vertical && similar-name | similar-concept); a NULL offer_id may mean SHARED-BY-DESIGN, not missing data (the DB's current offer_id-presence+vertical check is a known simplifying PROXY that ignores the similarity principles). Therefore the feed MUST carry a DEDICATED-vs-SHARED signal (do NOT force a false 1:1), and the attribution grain for SHARED-asset spend is an OPEN fork (FORK-SHARED-ASSET-GRAIN — candidate rulings class-grain rollup / split-allocation / vertical-pool-only, ruled AFTER a measurement spike + an operator principle ruling, Phase-2 interview in flight). Build home: CROSS-REPO (asana feeds, data computes). NOT a payment->offer revenue producer — per-offer revenue is structurally non-attributable (below)."
    - "eCPS TWO-METRICS IMPLEMENTATION (KR1b — GAP-2 RATIFIED 2026-07-08, operator interview this session; NO LONGER a pending decision): operator ruling = 'Two metrics, honestly named.' (a) ecps KEEPS its algebra spend/effective_scheds (library.py:2504-2519) but the UI LABEL is renamed 'Expected CPS' -> 'Effective CPS' (formatter.py:74); (b) a NET-NEW SIBLING metric = spend/solid_scheds (the probabilistic expectation model, library.py:2291-2351) is REGISTERED, labeled 'Expected CPS' (working name e.g. xcps — final name to the data-analyst rite). This is an IMPLEMENTATION leg (relabel + register sibling + a name-collision GUARD on solid_scheds semantics: legacy deterministic scheds-fut_pen vs modern probability-weighted), NOT a ratification gate. Ratification receipt: operator interview 2026-07-08. The legacy lineage (spike §3.1/B9: legacy ecps = a BACKWARD-LOOKING multiplier, zero probabilistic machinery) is the evidence the ruling rests on."
    - "DENOMINATOR + COVERAGE (KR2): the ACTIVE-set registry (gid_push _is_status_push_enabled enabled-by-default :439-443; [SD-02]) and the vertical enum-option-SET (gid_push VOCAB_SYNC_ENABLED DEFAULT-OFF :654,688-690, SHIP-DARK) are CONFIRMED live-and-congruent in prod, or activated — AND the offer-grain SPEND COVERAGE is MEASURED via a data-analyst + DRE measurement spike (SUPERSEDES the 18.7% figure — that measured the sparse DIRECT column ad_creatives.asset_id; modern ads should link via the assets_ad_creatives JUNCTION table through ads->adsets->campaigns, so real coverage is UNMEASURED and expected MUCH HIGHER). The spike measures: (a) true asset-linkage coverage on MODERN ads via the junction path; (b) shared-vs-dedicated spend magnitude; (c) the iris live-prod legs (assets.offer_id prod state, offer-frame usage, SD-02 registry) — proven by measurement, not inferred from code presence."
    - "COVERAGE-FLOOR / TRUST (KR3, now LOAD-BEARING; MEASURED ROUND-2): junction-path spend coverage among hierarchy-intact rows is MEASURED ~99-100% (2024 99.6% / 2025 98.8% / 2026 100.00%) — the 18.7% direct-column figure is RETIRED. The REAL modern hole is ORPHAN AD_IDS (11.6-14.1% of 2024-2026 spend has NO ads row). The arc SHIPS at ~86-88% coverage with the orphan-spend share VISIBLY DISCLOSED on BOTH win surfaces (the number is HONEST about its denominator — a coverage-floor/trust-leg SEMANTIC, not silent under-counting). The number still CANNOT SHIP without the coverage/disclosure gate — the built population-receipt floor (POPULATION_WARN_THRESHOLD=0.80, ACTIVE-scoped, _VALUE_COLUMNS_BY_ENTITY offer=(mrr,offer_id) post_build_population_receipt.py:54,60-62) captured, documented, and wired as a LIVE alarm so a present-but-partial economics frame is alarmable, not silently under-counted. C-2 is a CORRECTNESS MULTIPLIER, not parallel-cheap-optional. Carry the cross-cutover status-vocab DRIFT (reschedule ns->nc; convs widened; scheds redefined — legacy §1.3/B6, D5) as a C-2/C-3 display+guard concern: cross-cutover rate comparisons are INVALID without status-level reconciliation."
    - "SD-02 REGISTRY REPAIR (KR4, NEW leg C-6, ROUND-2): account_status (the SD-02 ACTIVE-set registry) is MEASURED EMPTY in prod (0 rows, MAX(synced_at)=NULL) despite the push machinery + enabled-by-default flag — the 4h cache-warmer snapshot push is NOT landing. Root-cause asana-side push -> data-side endpoint and REPAIR. This FEEDS the ACTIVE-scoped coverage floor, so C-2 DEPENDS ON it."
    - "DENOMINATOR-BEFORE-PROBE: C-0 is a HARD PREDECESSOR of C-1. It is now FULLY DISCHARGED ROUND-2 — code-half (both 2026-07-08 spikes) + live-prod-half (the measurement spike, ALL 4 legs MEASURED LIVE, zero blocked). E1's gate condition is SATISFIED and C-1's scope is RULED (adset-declared attribution). The C-0 ruling artifacts precede the C-1 PR in the record."
    - "NOT-definition: NOT 'the dimension-feed PR merged' — the predicate is a rite-disjoint attester observing a real per-offer CPS/eCPS figure on the actual user surface (dashboard/export) with the denominator + coverage confirmed live, the eCPS definition RATIFIED, and the coverage-floor alarm biting, per-item file:line receipts throughout. Self-assessment caps MODERATE; STRONG belongs to the rite-disjoint attester at close."
    #
    # --- ORIGINAL KR1 'PRODUCER' (SUPERSEDED 2026-07-08; preserved, not deleted) ---
    #   "PRODUCER (KR1): a per-offer payment-linked REVENUE metric is registered and joins a payment
    #    amount to offer_id ... Its build SCOPE — extractor column vs metric definition vs autom8_data
    #    contract gap — is RULED by C-0."
    #   SUPERSEDED because per-offer REVENUE is structurally non-attributable in BOTH legacy and
    #   modern: payments terminate at (office_phone, vertical), 1:many over business_offers, no FK to
    #   offers (legacy §3.3/D15; modern _platform.py:306-440). Operator decision: cost-efficiency
    #   (CPS/eCPS) only this arc, no proxy revenue allocation. And the metric is NOT a build — it
    #   EXISTS in autom8y-data; the work is a DIMENSION-FEED (KR1 above).

  constraints:  # AMENDED 2026-07-08 (pythia re-frame)
    - "DENOMINATOR-BEFORE-PROBE (load-bearing): C-0 gates C-1. The C-0 CODE-HALF is DISCHARGED (both 2026-07-08 spikes ruled the shape: a CROSS-REPO dimension-feed, not a producer build); the C-0 LIVE-PROD-HALF (iris) still gates the C-1 feed — no feed build lands before iris confirms assets.offer_id emptiness + real coverage % + offer-frame prod behavior."
    - "C-1 IS A CROSS-REPO DIMENSION-FEED, not a producer build: autom8y-asana PUSHES the AssetEdit (office_phone, vertical, asset_id, offer_id) enrollment (rides gid_push rails) -> autom8y-data POPULATES assets.offer_id -> offer-grain spend via the /query path. The metric ALREADY EXISTS in autom8y-data (do NOT rebuild it)."
    - "eCPS DEFINITION is RATIFIED (GAP-2, 2026-07-08 operator ruling 'Two metrics, honestly named'): ecps KEEPS spend/effective_scheds but relabels 'Expected CPS'->'Effective CPS'; a NET-NEW spend/solid_scheds sibling is registered as 'Expected CPS'. This is now an IMPLEMENTATION leg (relabel + register sibling + name-collision guard), NOT a pending decision. Do NOT re-open the definitional call."
    - "C-2 coverage floor is LOAD-BEARING (not parallel-cheap-optional): offer-grain spend is PARTIAL (true % UNMEASURED — the 18.7% direct-column figure is SUPERSEDED pending a junction-path measurement spike via assets_ad_creatives; expected higher but still partial + SHARED-asset spend is open-grain), so the coverage/population gate is a correctness multiplier the number cannot ship without. The three-part $0-defense already exists at HEAD (CAPTURE + ACTIVATE, not construct)."
    - "trust bar: reconciled-strict to autom8y-data db.md truth. win bar: the number LIVE + TRUSTWORTHY on a surface (value-in-use NOT required this arc)."
    - "autonomy: autonomous to the merge/prod line — agents open PRs; agents NEVER merge or flip prod flags without the operator."
    - "atomic per-repo PR boundary; in-repo over host-only; the autom8_data data-side populate + the monolith are CROSS-PLANE legs — frame-and-hand-off, NOT built in the asana checkout. (Note: C-1 is INHERENTLY cross-repo — the asana feed is LOCAL; the data-side populate is a HANDOFF.)"
    - "self-assessment caps MODERATE; STRONG needs rite-disjoint corroboration at the close gate (eunomia, three-evidence-leg)."
    - "operator-sovereign pre-step: the leaked ASANA_PAT is LIVE (rotation-pending, NOT agent-routable) — a pre-step the operator owns, not a workstream leg any agent executes."
    - "assets are INTENTIONALLY cross-offer (GAP-1 domain correction): a NULL offer_id may be SHARED-BY-DESIGN, not missing. The feed carries a DEDICATED-vs-SHARED signal (no false 1:1); SHARED-asset attribution grain is FORK-SHARED-ASSET-GRAIN, ruled AFTER measurement + an operator principle ruling (Phase-2 in flight). Do NOT force shared spend to a single offer."
    - "per-offer REVENUE is OUT this arc (structurally non-attributable, no proxy allocation); cost-efficiency (CPS/eCPS) only."

  shipped_definition:
    code_or_artifact_landed: []  # MISSING — nothing landed at framing. AMENDED 2026-07-08: populated by: C-0 probe ruling artifacts (the two 2026-07-08 spikes — CODE-HALF; + the iris LIVE-PROD ruling) + C-1 asana-side DIMENSION-FEED PR (AssetEdit enrollment push on gid_push rails) + the autom8_data-side assets.offer_id POPULATE HANDOFF + the GAP-2 eCPS-ratification decision record + C-2 coverage-floor activation PR + surface-exposure (cps/ecps onto the leadership surface) + C-3 census-refresh + drift-guard-source-binding PR + C-5 anti-IDOR test/doc PR + C-6 SD-02 push/endpoint repair PR. C-4 self-fires when the number ships.
    user_visible_surface: >
      [OPERATOR-SET — draft wording AMENDED 2026-07-08 (revenue -> cost-efficiency per the two spikes);
      blessed-as-is until you amend]
      The agency opens a leadership surface (the HTML insights report or an export) and sees real
      per-offer COST EFFICIENCY — a per-offer CPS and eCPS on ACTUAL ad spend, at offer grain — not a
      single book-wide sum and one pooled ad-spend number. The number is trustworthy: (1) offer-grain
      spend has lit up because the asset<->offer dimension is fed (assets.offer_id populated from the
      AssetEdit enrollment asana already extracts); (2) a present-but-partial-coverage economics frame
      trips a LIVE coverage-floor alarm rather than silently under-counting spend; and (3) the eCPS
      definition is honestly named per the RATIFIED GAP-2 ruling ('Two metrics, honestly named' —
      'Effective CPS' = spend/effective_scheds; a NET-NEW 'Expected CPS' = spend/solid_scheds), so each
      label means what leadership thinks it means. WIN SURFACE = BOTH (operator 2026-07-08): the number
      is live+trustworthy on BOTH the HTML insights report AND the exports route (cps/ecps columns,
      coverage-gated). On this the agency can KILL a client offer with per-offer CPS above the cost
      floor, SCALE the lowest-CPS offers, REPRICE against margin-negative cost floors, and ALLOCATE the
      marginal ad dollar across the ranked offer set — on data, not intuition.
      (Per-offer REVENUE / ROAS-on-actual-payments is OUT this arc — structurally non-attributable.)

  verified_realized_definition:
    user_visible_evidence:
      # The realization predicate, sliced into testable legs. AMENDED 2026-07-08 (pythia re-frame):
      # PRODUCER->DIMENSION-FEED; NEW eCPS-RATIFICATION leg; TRUST->COVERAGE-FLOOR. Deadline/attester [OPERATOR-SET].
      - "DIMENSION-FEED leg (was PRODUCER): the asset<->offer dimension is fed — a fresh inspection shows autom8y-asana PUSHES the AssetEdit (office_phone, vertical, asset_id, offer_id) enrollment (asset_edit.py:106,127; on gid_push rails) and autom8y-data assets.offer_id is POPULATED — AND the rite-disjoint attester observes a real per-offer CPS/eCPS figure on the actual user surface (via the /query path, NOT /drill), not a company-level sum. The metric itself pre-exists in autom8y-data; the leg proves the FEED lit up offer-grain spend."
      - "eCPS-RATIFICATION leg (NEW — stakeholder-sovereign): the eCPS 'effective' definition is RATIFIED with the stakeholder (data-analyst + DRE evidence in hand: effective_scheds status-filter vs solid_scheds expectation-model vs the 'Expected CPS' label) — a decision record exists and the number-called-trustworthy gate is passed. Evidence is in hand; the DECISION is the operator/stakeholder's, not the attester's."
      - "COVERAGE-FLOOR / TRUST leg (was TRUST): the population/coverage floor (0.80, ACTIVE-scoped) is demonstrably wired as a LIVE alarm — a present-but-PARTIAL-coverage economics frame RED-trips it (discriminating: the truthful adequately-covered frame passes GREEN), teeth-proven per discriminating-canary doctrine, not presence-proven. Load-bearing because offer-grain spend coverage is PARTIAL (the ~18.7% direct-column figure is SUPERSEDED; true % via the junction-path measurement spike)."
      - "DENOMINATOR-BEFORE-PROBE leg: the C-0 probe ruling (CODE-HALF discharged by the two 2026-07-08 spikes; LIVE-PROD-HALF by iris) exists and PRECEDES the C-1 dimension-feed PR in the git/artifact record — the feed scope cites the C-0 ruling, proving the sequencing constraint held."
    verification_method: cross-stream-corroboration  # [OPERATOR-SET DRAFT] — telemetry (live dashboard/alarm) + iris prod-state probe + rite-disjoint attester surface-observation; confirm at Gate-A countersign
    verification_deadline: "2026-07-29"  # [OPERATOR-SET] SET AT GATE-A CLOSE 2026-07-08 per the draft guidance formula (probe-gated: C-0 FULLY discharged incl. the live-prod measurement spike, GAP-2 ratified, fork RULED — gate satisfied; ~3wk per predecessor precedent; operator may amend). Drives Naxos TELOS_OVERDUE.
    rite_disjoint_attester: "eunomia"  # [OPERATOR-SET DRAFT] — rite-disjoint from all author rites (10x-dev/hygiene/data-analyst/DRE/know/security); three-evidence-leg at close. AMENDED 2026-07-08: the eCPS-ratification (GAP-2) is a STAKEHOLDER-SOVEREIGN checkpoint UPSTREAM of the attester (data-analyst + DRE present evidence; the stakeholder decides) — the attester verifies that ratification HAPPENED, it does not make the definitional call. CAVEAT: carry the predecessor's UV-P-7 (eunomia verification-auditor Bash grant — the dimension-feed/coverage proof is probe/grep-heavy; confirm at close-gate empanel, signal-sifter re-route precedent).

  attestation_status:
    inception: RATIFIED      # Gate-A CLOSED 2026-07-08 — standing countersign (rounds 1+2 as-amended) executed at main-thread verification against the three spike rulings
    shipped: MISSING
    verified_realized: UNATTESTED
    last_eunomia_advisory: null

  receipt_grammar:
    per_item_file_line_anchors:
      # AMENDED 2026-07-08 (pythia re-frame): the two 2026-07-08 spikes reshaped Blocker-A from a
      # "missing producer" to a "dropped dimension-feed". New anchors added; original Blocker-A
      # anchors RETAINED (they still prove the per-offer payment/revenue metric is absent — which is
      # WHY the number is cost-efficiency, not revenue). SVR re-read at f3d8eec1 by pythia 2026-07-08.
      #
      # DIMENSION-FEED — the asset<->offer enrollment asana EXTRACTS but never PUSHES (the true GAP-1):
      - "src/autom8_asana/dataframes/schemas/asset_edit.py:106"     # asset_id field extracted
      - "src/autom8_asana/dataframes/schemas/asset_edit.py:127"     # offer_id field extracted — the four-tuple (office_phone, vertical, asset_id, offer_id) is KNOWN asana-side
      - "src/autom8_asana/services/gid_push.py:312,557,919"         # the three push surfaces — grep -c offer_id = 0: NONE carries offer_id (the dropped write-back half; legacy §3.2/D11)
      # The metric ALREADY EXISTS in autom8y-data (do NOT rebuild — cross-repo anchors, from the C-0 spike):
      # autom8y-data library.py:1939-1987 (cps), :2504-2519 (ecps), :1295-1375 (offer_level_stats ARMED); _insights.py:187-190 (EntityMetrics.cps/ecps)
      # Asana CONSUMES it at frame_type="offer":
      - "src/autom8_asana/query/data_service_entities.py:45-181"    # cps/ecps exposed at frame_type='offer' (leads/campaigns/ads/adsets factories)
      - "src/autom8_asana/automation/workflows/insights/formatter.py:73-74"  # 'cps'->'CPS', 'ecps'->'Expected CPS' (GAP-2 drifted UI label)
      - "src/autom8_asana/api/routes/exports.py:110-118"           # PHASE_1_DEFAULT_COLUMNS has NO cps/ecps (GAP-4 surface-exposure)
      # Blocker-A original anchors — RETAINED: prove per-offer PAYMENT/REVENUE metric is absent (=> cost-efficiency, not revenue):
      - "src/autom8_asana/metrics/definitions/offer.py:26-65"       # ONLY active_mrr + active_ad_spend, both _ACTIVE_OFFER_SCOPE company-level; no per-offer payment metric (per-offer revenue is non-attributable — legacy §3.3/D15)
      - "src/autom8_asana/reconciliation/processor.py:126-172"      # unit<->offer matching is activity-state/section-move only; carries NO payment amount to an offer
      # Blocker-B — the denominator flags (asymmetric: one enabled-by-default, one SHIP-DARK):
      - "src/autom8_asana/services/gid_push.py:439-443"             # _is_status_push_enabled() ENABLED-BY-DEFAULT (val not in {false,0,no}) — registry may already populate in prod
      - "src/autom8_asana/services/gid_push.py:650-690,919"         # VOCAB_SYNC_ENABLED DEFAULT-OFF (SHIP-DARK, unset->False); push_vocabulary_to_data_service — denominator enum plausibly inert
      - "src/autom8_asana/automation/workflows/active_offer_enumeration.py:1-58"  # enumerate_active_offers — canonical ACTIVE-set definition; population-state not code-determinable
      # Trust floor — the built $0-defense (capture + activate, C-2):
      - "src/autom8_asana/dataframes/builders/post_build_population_receipt.py:54,60-62"  # POPULATION_WARN_THRESHOLD=0.80; _VALUE_COLUMNS_BY_ENTITY offer=(mrr,offer_id)
      - "src/autom8_asana/dataframes/builders/null_number_recovery.py:1-30"  # silent-$0 GID-only warm-path cure
      # Drift-guard schema-only gap (C-3):
      - "src/autom8_asana/dataframes/contracts/field_contract_maps.py:360-402"  # requirements_drift_check(None) -> schema-only mode, no source comparison; toothless until monolith_source binds
      # Census staleness (C-3) and delivery obs (C-4):
      - ".know/feat/INDEX.md:10"                                    # source_hash 8980bcd7 vs HEAD f3d8eec1; ~52 post-census new source files
      - ".know/feat/INDEX.md (exports-route obs_status F, OBS-EXPORTS-001, deadline 2026-06-15 LAPSED)"  # C-4 delivery-obs; sli_heartbeat.py/event_loop_monitor.py may partially close — C-0/C-3 confirms
      # Anti-IDOR invariant (C-5):
      - "src/autom8_asana/auth/per_business_provider.py:1-20"       # business_id DOMINATES office_phone; one-mint->one-provider->one-client; undocumented, IDOR-relevant
    cross_stream_concurrence: false   # set true ONLY at verified_realized=ATTESTED (all legs corroborated by the rite-disjoint attester)
    code_verbatim_match: true         # anchors SVR file-read/grep-probed at f3d8eec1 by myron 2026-07-08; RE-VERIFIED + EXTENDED at f3d8eec1 by pythia 2026-07-08 (re-frame): asset_edit.py:106/127 (four-tuple extracted), gid_push grep -c offer_id = 0 (never pushed), data_service_entities.py:45-181 (asana consumes cps at offer frame), formatter.py:73-74 ('Expected CPS' drifted label), exports.py:110-118 (no cps/ecps in defaults). Every crusade re-verifies its anchors at dispatch (drift expected, staleness is a finding). Amendments grounded at the two 2026-07-08 spikes.
```

## Realization predicate (the one line that gates close — VERBATIM)

> "Verified-realized" = a rite-disjoint attester (eunomia) observes a real per-offer CPS/eCPS figure on the actual user
> surface (dashboard/export) with the denominator + coverage confirmed live (junction-path ~99-100%, orphan-share ~12-14% disclosed),
> the eCPS definition RATIFIED with the stakeholder ('Two metrics, honestly named'), the coverage-floor alarm biting (teeth-proven per
> discriminating-canary), and the C-0 denominator-before-probe ruling preceding the C-1 dimension-feed PR in the artifact record —
> NOT "the dimension-feed PR merged". Self-assessment caps MODERATE; STRONG belongs to the rite-disjoint attester at close.

This predicate is carried into **every** sprint's exit criteria per the forthcoming shape
(`.sos/wip/frames/north-star-per-offer-economics.shape.md`, pythia — the shape models C-0 FULLY DISCHARGED + C-1…C-6 cross-repo seams + rite transitions), and is the sole content of the **close gate**
rite-disjoint telos gate (eunomia, three-evidence-leg). The close-gate attestation is the telos proof,
not an afterthought. Self-assessment caps **MODERATE**; **STRONG** additionally requires rite-disjoint corroboration.

## Carried flags (the operator should know)

- **Gate-A CLOSED 2026-07-08 (standing countersign EXECUTED, rounds 1+2 as-amended)** — the
  operator issued "countersign as-amended on landing" (interview, this session); the MAIN THREAD
  verified rounds 1 and 2 against the THREE spike rulings (the two 2026-07-08 premise spikes
  + the measurement spike) and flipped it. Dispatch UNBLOCKED. The two `[OPERATOR-SET]`
  fields (`verification_deadline` = 2026-07-29, set at close per draft guidance;
  `rite_disjoint_attester` = eunomia) are blessed-as-drafted per the predecessor's countersign-as-drafted
  precedent unless the operator amends.
- **C-0 FULLY DISCHARGED 2026-07-08 (ROUND-2)** — code-half (the two 2026-07-08 premise spikes:
  SPIKE-c0-denominator-probe-ruling + SPIKE-legacy-monolith-truth-decomposition); live-prod-half
  (SPIKE-asset-linkage-coverage-measurement, ALL 4 legs MEASURED LIVE against prod RDS, zero blocked).
  E1's gate condition is SATISFIED; C-1's scope is RULED (adset-declared attribution, 99.99% populated).
  The measurement spike fixed the 18.7% direct-column mis-measurement (junction-path coverage now
  measured: 2024 99.6% / 2025 98.8% / 2026 100.00%); the real modern hole is orphan ad_ids (11.6-14.1%,
  no ads row).
- **The leaked ASANA_PAT is LIVE and operator-sovereign** — rotation-pending, NOT agent-routable.
  The single highest-severity open residual (inherited from asana-realization-tail-convergence, PT-E FLAG-1).
  Named as an operator pre-step.
- **C-1 RE-SCOPED 2026-07-08 (AMENDMENT)** — the metric already exists in autom8y-data; C-1 is now
  a CROSS-REPO DIMENSION-FEED (asana pushes AssetEdit enrollment; data populates assets.offer_id),
  NOT a producer build. The ADSET-DECLARED ATTRIBUTION path (adsets.offer_id 99.99%) is P&L-critical;
  the AssetEdit feed DEMOTES to a supporting creative-intelligence leg (non-P&L).
- **eCPS TWO-METRICS (GAP-2) RATIFIED 2026-07-08 (no longer a gate)** — operator ruling
  'Two metrics, honestly named': ecps relabels 'Expected CPS'->'Effective CPS'; a NET-NEW
  spend/solid_scheds sibling registers as 'Expected CPS'. Now an IMPLEMENTATION leg (C-1b),
  not a ratification gate. Ratification receipt: operator interview 2026-07-08.
- **FORK-SHARED-ASSET-GRAIN RULED ROUND-2 2026-07-08** — ADSET-DECLARED ATTRIBUTION + VERTICAL-POOLED ASSETS
  (measured: adsets.offer_id 99.99%, assets.offer_id 5.7% NOT promoted, shared-spend 57.9%). Per-offer spend
  via adsets.offer_id; assets vertical-pooled for creative intelligence. The equivalence-class model re-routed
  to the autom8y-data defer-watch (AD-CREATION-ACCURACY).
- **The ~18.7% coverage figure RETIRED (MEASURED ROUND-2)** — it measured the wrong path (sparse direct column).
  Junction-path coverage MEASURED: 2024 99.6% / 2025 98.8% / 2026 100.00%. The real modern hole is ORPHAN AD_IDS
  (11.6-14.1% of spend, no ads row) — data-analyst backlog fix + VISIBLE surface disclosure; the arc ships at
  ~86-88% with the orphan share disclosed.
- **C-2 COVERAGE-FLOOR LOAD-BEARING (now DEPENDS ON C-6)** — the population floor (0.80, ACTIVE-scoped) is
  critical; offer-grain spend coverage is PARTIAL. C-2 DEPENDS ON the NEW C-6 SD-02 registry repair —
  `account_status` is EMPTY in prod (0 rows, MAX(synced_at)=NULL; the 4h cache-warmer push not landing).
- **NEW C-6 LEG ROUND-2: SD-02 REGISTRY REPAIR** — account_status (ACTIVE-set registry) is MEASURED EMPTY in
  prod despite enabled-by-default flag. New seam C-6 repairs the asana-side push -> data-side endpoint chain;
  C-2 coverage floor DEPENDS ON this repair landing.
- **NEW ROUND-2: orphan ad_ids = REAL DENOMINATOR HOLE** — 11.6-14.1% of 2024-2026 spend has no ads row.
  Data-analyst backlog fix (BACKLOG-WITH-TRIGGER); arc SHIPS at ~86-88% with orphan share VISIBLY DISCLOSED
  on both win surfaces (honest denominator).
- **NEW ROUND-2: pre-2025 needs ANY-platform junction join** — facebook->meta enum-drift era; canonical
  platform-matched join undercounts pre-2025 by up to ~60% (measured convergence at 2025-Q2+).
- **Gates cap at MODERATE** pending rite-disjoint attestation — `self_ref_cap: MODERATE`. STRONG
  belongs to the rite-disjoint attester (eunomia, three-evidence-leg) at the close gate, not to
  any author rite.
- **The metric ALREADY EXISTS in autom8y-data** — do NOT rebuild cps/ecps/offer_level_stats.
  ROUND-2: P&L-critical path is adsets.offer_id attribution (99.99%); AssetEdit feed demoted
  to supporting creative-intelligence leg. Per-offer REVENUE is OUT (structurally non-attributable).
- **WIN SURFACE = BOTH (operator 2026-07-08)** — the number ships live+trustworthy on BOTH the HTML
  insights report AND the exports route (cps/ecps columns, coverage-gated), with orphan-ad_ids share
  (11.6-14.1%) VISIBLY DISCLOSED on both surfaces.
- **Standing meta through-line** — Pythia/Potnia service prompt/context/workflow engineering
  across every cross-rite dispatch for maximal specialist performance.
- **Amendment trail** — the 2026-07-08 supersessions are marked SUPERSEDED-BY (not silently
  rewritten) throughout, grounded at SPIKE-c0-denominator-probe-ruling-2026-07-08.md +
  SPIKE-legacy-monolith-truth-decomposition-2026-07-08.md + (ROUND-2)
  SPIKE-asset-linkage-coverage-measurement-2026-07-08.md (all 4 legs MEASURED LIVE). HEAD re-confirmed
  `f3d8eec1`.

## Evidence Grade

`[STRUCTURAL | MODERATE]` — pre-build inception declaration; `self_ref_cap: MODERATE` per
`self-ref-evidence-grade-rule`. AMENDED 2026-07-08 (pythia re-frame): the amendments are grounded at
the two 2026-07-08 spikes (SPIKE-c0-denominator-probe-ruling — 5-scout swarm; SPIKE-legacy-monolith-
truth-decomposition — 20-agent ultracode, TRUTHS-ONLY, `not_a_reference_implementation`), and ROUND-2 at
the measurement spike (SPIKE-asset-linkage-coverage-measurement, all 4 legs MEASURED LIVE); the new
dimension-feed anchors are first-party SVR-read at `f3d8eec1` by pythia this pass (`asset_edit.py:106,127`
extracted four-tuple; `gid_push` grep -c offer_id = 0 never pushed; `data_service_entities.py:45-181`
asana consumes cps at offer frame; `formatter.py:73-74` 'Expected CPS' drifted label; `exports.py:110-118`
no cps/ecps in defaults). The original blocker findings (myron 2026-07-08 SVR) are RETAINED (they prove
per-offer revenue is absent => cost-efficiency). C-0's CODE-HALF is DISCHARGED; the LIVE-PROD-HALF
(iris — `assets.offer_id` emptiness, real coverage %, offer-frame prod behavior, registry population)
remains OWED to iris. The eCPS ratification (GAP-2) is stakeholder-sovereign — evidence in hand, decision
complete (operator interview 2026-07-08). Realization attestation belongs to the rite-disjoint attester
(eunomia) at the close gate, not to any author rite. All spikes cap MODERATE (self-referential corpora);
the amendment inherits that ceiling.
