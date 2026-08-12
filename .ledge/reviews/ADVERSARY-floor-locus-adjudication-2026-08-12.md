---
type: review
subtype: adversary-report
artifact_type: ADVERSARY-REPORT
status: proposed
target_handoff: ".ledge/reviews/ADJUDICATION-floor-locus-endstate-2026-08-12.md (PR #346, branch docs/adjudication-floor-locus @ 040b61ed)"
target_handoff_sha: "sha256:9e1bfb29abaa3cdf6012d945452ef5108f22490193304e710bd9cccae664f56c"
challenger_agent: arch-adversary
initiative: substrate-v2-epoch
wave: S8-2
date: 2026-08-12
iter: 1
delta_scope_attested: false
verdict: PASS-WITH-CONDITIONS
adversary_disposition: CONCUR-WITH-FLAGS
tl_a_status: PASS
tl_b_status: CHALLENGE
tl_c_status: CHALLENGE
code_truth_anchor: "origin/main 7f81e515 (matches the adjudication's own anchor; all probes run 2026-08-12)"
evidence_grade_ceiling: MODERATE   # self-ref-evidence-grade-rule — adversary's own grades cap at MODERATE; probe outputs are re-runnable receipts
challenges_raised:
  - id: CH-01
    taxonomy_id: AC-01
    tl_clause: A
    severity: FLAG
    target_element: "§2 Locus E + §4 'Consequence for the BRIDGE' (lines 413-431, 544-552)"
    rationale: "The union projection's BLOCKING_AT_PUBLISH mapping is a new authored constant with no named authority, and the E derivation was never run against the ACTUAL vendored manifest — whose only nonnull_over_active_subset declaration (business_offers.active_offers_frame: offer_id, project shape) would, under a future project-entity publish gate, permanently refuse the production project frame (100%-NULL offer_id per the ADR's own D3 rationale) and resurrect the halt class the operator killed."
    falsification_pathway: "Run the E derivation against consumer_column_requirements.vendored.json as it exists; state the entity-scoping rule and the BLOCKING_AT_PUBLISH authority in the ratification packet; show the offer-entity projection reproduces the bridge set AND disclose the project-entity consequence. If the formula already fixes scoping unambiguously and the disclosure lands, CH-01 downgrades to ADVISORY."
    remediation_hint: "One paragraph in the myron /frame packet: projection rule = floor_columns(entity) over declarations whose query_shape.entity_type == entity; BLOCKING_AT_PUBLISH = {nonnull_over_active_subset, present_all_rows} (or narrower) authored WHERE, ratified BY WHOM; derivation-vs-manifest receipt attached."
  - id: CH-02
    taxonomy_id: AC-UNMAPPED
    tl_clause: B
    severity: ADVISORY
    target_element: "§1.6 corroboration paragraph (lines 300-306)"
    rationale: "Evidence-attribution drift: the quoted 'LegitimatelySparse … $8,775/7-row null-fossil' rationale at post_build_population_receipt.py:62-68 is the UNIT entity's comment ('not every active unit runs ads / carries a discount'), deployed as corroboration for the OFFER floor rescope. The offer entry (mrr, offer_id) does exclude cost/weekly_ad_spend, so the direction survives — but the 'independently-reached precedent' is weaker than presented."
    falsification_pathway: "Show an offer-scoped statement of the same rationale elsewhere in the receipt module or its ADR lineage; then the corroboration stands as written."
    remediation_hint: "Requalify the sentence: the unit rationale is analogous precedent, not offer-scoped precedent. [KNOW-CANDIDATE] filed (§TL-B) for the evidence-attribution-drift pattern."
  - id: CH-03
    taxonomy_id: AC-01
    tl_clause: C
    severity: FLAG
    target_element: "§7 axis table (lines 648-655) vs §4 'Main tradeoff' (lines 554-565)"
    rationale: "The door ruling's axis table omits the authority-relocation axis that §4 itself names as the main tradeoff. Discharging F-4 (monolith source binding) — a stated precondition of H1's governance story — transfers publish-floor authority cross-repo; retracting consumer control at that point is a Rider-3-class cross-repo contract event. Rider 3 covers token SEMANTICS; nothing covers declaration AUTHORITY. H1 is corridor-revertible only while F-4 stays undischarged, yet H1's anti-drift story requires F-4 discharged."
    falsification_pathway: "Either (a) extend Rider 3 (or add Rider 4) naming the F-4 discharge as door-adjacent under H1 with the declaration-authority rule in the ratification packet, or (b) demonstrate that the vendored-manifest CI gate keeps unilateral in-repo veto over any cross-repo declaration change post-binding — which would keep the authority in-repo and the corridor ruling intact as written."
    remediation_hint: "Rider 4: 'publish-blocking declaration authority — who may author population_expectation values that project into the publish floor, and which repo's review gates it — is ratified with the endstate, and the F-4 source-binding discharge is door-adjacent under H1.'"
  - id: CH-04
    taxonomy_id: AC-02
    tl_clause: C
    severity: FLAG
    target_element: "UV-P-2, UV-P-3 (lines 717-719); §4 dissent items 1 and 6"
    rationale: "UV-P-2 (One-Gate population predicate cheap under load) and UV-P-3 (many-consumers premise) are load-bearing for the H1-vs-B choice — the adjudication itself says UV-P-3 is dispositive at dissent 6 — but carry no discharge owner, artifact path, or deadline. 'deferred-to-operator' is disposition-forcing only if the ratification interview actually poses the question."
    falsification_pathway: "Name the discharge artifact + owner for each: UV-P-2 → an implementation-sprint latency receipt (path named in the /frame packet); UV-P-3 → a question posed verbatim in the operator ratification interview with the B-fallback stated. When both carry owners, CH-04 closes."
    remediation_hint: "UV-P-1 is DISCHARGED-CONFIRMED by this report's probe (§TL-A below); record that in the packet and carry only UV-P-2/3 forward."
  - id: CH-05
    taxonomy_id: AC-UNMAPPED
    tl_clause: B
    severity: ADVISORY
    target_element: "frontmatter + §8 (no arch-ref literature grounding)"
    rationale: "An architecture adjudication whose central argument is a drift/duplication anti-pattern (three divergent floor definitions) and a boundary-relocation (consumer-declared contracts) cites zero architecture literature. Platform-internal receipts are excellent; external grounding (AQ:SRC-004 Mo et al. anti-pattern cumulative error-proneness; DP:SRC-005 Evans bounded contexts for the consumer-declaration boundary) would lift the ratification packet. ADVISORY only — the artifact is 10x-dev rite and not bound to the arch HANDOFF schema."
    falsification_pathway: "n/a (advisory; no verdict weight)"
    remediation_hint: "Optional: one citation line each on §1.6 (drift) and §2 Locus D (bounded-context boundary)."
arch_ref_citations:
  - "AQ:SRC-004"   # Mo et al. 2019 — architecture anti-patterns, cumulative error-proneness: grounds the CH-01/§1.6 drift-class framing
  - "AQ:SRC-006"   # Martin 2002 — dependency direction/ADP: grounds the CH-03 authority-relocation coupling argument
  - "DP:SRC-005"   # Evans 2003 — bounded contexts: grounds reading Locus D as a context-boundary contract
  - "AV:SRC-001"   # Messick 1989 — construct validity: grounds the door-ruling axis-completeness challenge (construct underrepresentation)
---

# ADVERSARY-REPORT — floor-locus endstate adjudication (P8 challenge, iter 1)

## 1. Challenge Summary

**VERDICT: PASS-WITH-CONDITIONS.** Zero BLOCKING challenges. The adjudication is the
strongest-receipted artifact this adversary has challenged in this lineage: **all 16+
file:line receipts I probed verified exactly; both executable probes reproduced; and the
inherited premise it flagged as its own highest-value falsification target SURVIVED the
falsification attempt with a precision qualifier.** Three FLAGs and two ADVISORYs stand:

- **CH-01 (FLAG)** — Locus E's projection rule is under-specified: the BLOCKING_AT_PUBLISH
  mapping is an unauthored new constant, and the derivation was never run against the
  actual manifest, whose only strong declaration would permanently refuse a future
  project-entity publish gate.
- **CH-02 (ADVISORY)** — one corroborating quote in §1.6 is unit-scoped, deployed as
  offer-scoped precedent.
- **CH-03 (FLAG)** — the CORRIDOR ruling's axis table omits the authority-relocation
  axis; F-4 discharge is door-adjacent under H1 and no rider covers declaration authority.
- **CH-04 (FLAG)** — UV-P-2/UV-P-3 lack discharge owners; UV-P-3 is self-declared
  dispositive for H1-vs-B.
- **CH-05 (ADVISORY)** — no external architecture-literature grounding.

The centerpiece empirical result: **the polars null-dedup collapse premise is TRUE on the
repo's pinned polars 1.38.1, through the actual compute path.** The blocking case for
`office_phone`/`vertical` in the bridge and the H1 union STANDS, now on probe evidence
rather than inheritance.

## 2. TL-A Analysis — predictions / quasi-predictive claims

The artifact carries no `predictions:[]` block; it uses the house-frozen UV-P syntax
(three labels, §8) as its forward-claim substrate. Audit per label:

**UV-P-1 (null-dedup collapse) — DISCHARGED-CONFIRMED by probe.** Executed 2026-08-12,
polars 1.38.1 (repo pin), two layers:

- *Layer 1 — raw call shape (`compute.py:116` form).* Frame of 6 rows:
  `unique(subset=["office_phone","vertical"], keep="first")` returned 4 rows.
  Two rows sharing `(null, "law")` **COLLAPSED 2→1** (mrr 200.0 silently dropped;
  input Σmrr 2100.0 → 1500.0). Two rows with null phone but **distinct** verticals
  `(null,"law")`/`(null,"hvac")` did **NOT** collapse.
- *Layer 2 — the ACTUAL served path.* `compute_metric(ACTIVE_MRR, frame)` over 4 distinct
  offers in a classifier-active section, two sharing `(null office_phone, "law")` →
  **3 rows survive; offer-B (mrr 200.0) silently dropped; the served sum would be 1200
  instead of 1400 — a 14% undercount with zero signal.** Which offer survives depends on
  frame row order.

**Precision qualifier the spike's wording elides:** nulls join **per-key**, so collapse
requires the FULL composite key to match under null-equality — null phone + SAME vertical.
Distinct-vertical rows never collapse. This does not weaken the blocking case: vertical is
a low-cardinality column, so same-vertical collisions among unprovisioned offers are the
expected shape, and the L2 probe shows the corruption is silent in the exact production
call. **Consequence: the bridge's `{mrr, office_phone, vertical}` rationale and H1's
blocking-at-publish rationale for the dedup keys HOLD. UV-P-1 should be recorded as
discharged-confirmed in the ratification packet.**

**UV-P-2 / UV-P-3 — open, and under-owned (CH-04, FLAG).** Both lack a discharge artifact
and owner. UV-P-3 ("MANY consumers") is dispositive per the adjudication's own dissent
item 6; a deferred-to-operator label with no interview question named is not yet
disposition-forcing.

**Quasi-predictive body claims check (AC-02 sweep):** the load-bearing forward claims
("cheap at the One-Gate", "ports as data onto InsightDefinition", "many consumers") are
all either UV-P-labelled or scoped as scoring-table judgments with named evidence. No
unlabelled load-bearing forward claim found. TL-A: **PASS** (CH-04 rides clause C).

## 3. TL-B Analysis — citation resolution and invocation

Every platform-internal receipt sampled was probed by direct Read at `origin/main
7f81e515` (the artifact's own anchor, which is the current main tip). Resolution table:

| Claimed receipt | Probed | Result |
|---|---|---|
| `freshness.py:154` `_VALUE_COLUMNS = (cost, mrr, offer_id, weekly_ad_spend)` | Read | EXACT |
| `freshness.py:158` `_DIGEST_SCHEME = "sv2-canonical-digest-1"` frozen-for-seam-life | Read | EXACT |
| `rebuild.py:366-421` validate() 3-check order; `:379-384` null floor | Read | EXACT |
| `rebuild.py:732-751` `_value_columns_with_nulls`, module-local import at `:741`, absent-column = null-equivalent | Read | EXACT |
| `post_build_population_receipt.py:60-70` `{offer: (mrr, offer_id), unit: (mrr,)}`, WARN ≥0.80 | Read | EXACT — but see CH-02 attribution flag |
| vendored manifest: 2 consumers; `offer_id` @ `nonnull_over_active_subset` (project shape) | Read | EXACT |
| `entity_registry.py:559` `key_columns=(office_phone, vertical, offer_id)` | Read | EXACT |
| `serve.py:31-37` RefuseReason CLOSED; `:111-120` `read(aid)` FROZEN v1.0, no consumer identity | Read | EXACT |
| `test_seam_contracts.py` member-for-member enum guard (`:58-63`) + `EXPECTED_EXPORTS = 24` (`:39`) | Read | EXACT (cited :60-65/:38; off-by-≤2, content holds) |
| `substrate/__init__.py:75` `AcceptancePredicates` in frozen `__all__`; `DefaultAcceptancePredicates` non-exported, injected `live.py:779` | Read + grep | EXACT |
| `query/models.py:304-313` `required_columns` wire field, additive default-None | Read | EXACT |
| `engine.py:615-658` `_derive_column_contract`; schema-membership not df.columns; population manifest `:652-657` contract-gated | Read | EXACT |
| `field_contract_maps.py:141-144` 3-token vocabulary incl. `nonnull_over_active_subset`; `:240-253` validate-then-store; `:326-357` union derivation; `:360-374` drift check schema-only | Read | EXACT |
| `population_expectation` "validated then never read" | grep src/ + tests/ | CONFIRMED — loader + dataclass + 2 test fixtures only; zero in engine.py, zero in rebuild.py |
| ADR-fm5-armb `status: accepted`, D3 rationale (100%-NULL offer_id) | Read | EXACT |
| `Expr.meta.root_names()` total derivation | uv run probe | CONFIRMED — `['from_stage','to_stage','transition_type']`, `['exited_at','entered_at']` |

**Frontmatter-theater check: NEGATIVE** — the receipts are invoked in body reasoning, not
listed decoratively. One attribution drift found (CH-02, ADVISORY): the §1.6
"LegitimatelySparse … $8,775/7-row null-fossil" quote is real and at the cited lines, but
it is the **unit** entry's rationale ("not every active unit runs ads / carries a
discount"), deployed as corroboration for the **offer** rescope. The offer entry's
exclusion of `cost`/`weekly_ad_spend` is consistent with the reading, so the direction
survives; the "independently-reached precedent" framing overstates. [KNOW-CANDIDATE:
evidence-attribution-drift — a verbatim quote cited at correct file:line but scoped to a
different entity than the claim it corroborates; no AC-01..05 entry captures
citation-scope mismatch.]

External grounding: none present (CH-05, ADVISORY — artifact is 10x-dev rite; the arch
HANDOFF schema does not bind it). TL-B: **CHALLENGE** (advisory-severity only).

## 4. TL-C Analysis — disposition-forcing audit + per-target findings

### T1 — the inherited premise (dispatch priority 1): SURVIVES falsification
Probe result in §2. The premise is now empirically grounded on the pinned polars version
through the actual compute path. **The falsification attempt FAILED — which is the
strongest possible outcome for the adjudication's dependent claims.** Both the bridge
rationale and the H1 blocking case for dedup keys hold. One consequence quantified for the
record: had the premise been false, the bridge would over-block two columns
(`office_phone`, `vertical`) whose nulls would be harmless; instead the probe shows a
14%-class silent undercount is constructible today with two same-vertical unprovisioned
offers.

### T2 — three-floors finding: VERIFIED
All three definitions (plus the fourth resolution-index entry) exist at the cited sites
with the claimed sets, strengths, and scopes. None is a misread; the vendored manifest's
role (presence-only, per-consumer, typed-incomplete) is stated accurately. RC-C
present-state drift is fact, not forecast.

### T3 — the 90%-built claim: VERIFIED IN FULL
Every element of the claimed FM-5/ARM-B substrate exists and does what the adjudication
says: wire field, SSOT union derivation, One-Gate enforcement (schema-membership by
design, per ADR D3), per-column population counts computed contract-gated at
`engine.py:652-657`, and `population_expectation` validated-then-inert (grep receipt
above). "The endstate work is wiring, not building" survives. Residual honesty check also
verified: the drift guard IS toothless (schema-only mode, `field_contract_maps.py:360-374`)
— the adjudication discloses this itself (dissent 2, F-4).

### T4 — union projection failure modes (dispatch priority 4): CH-01 FLAG
Steelman executed. The scenario where H1 is worse than status-quo-B-like governance is
concrete and buildable from the repo's own artifacts: the ONLY existing
`nonnull_over_active_subset` declaration (`business_offers.active_offers_frame` →
`offer_id`, project shape) projected through E onto a future project-entity publish gate
would refuse the production project frame **permanently** (its `offer_id` is 100%-NULL per
the ADR's own D3 rationale) — resurrecting the exact W2 halt class the operator just
killed, at fleet scale, via a declaration nobody in this repo authored for that purpose.
The adjudication's `floor_columns(entity)` formula is entity-scoped, which likely
neutralizes the OFFER-bridge case (the equivalence claim survives the charitable reading),
but: (a) the entity-scoping rule is never stated as a rule; (b) the BLOCKING_AT_PUBLISH
token-classification is a NEW authored constant — the anti-drift theorem ("divergence
unconstructable") covers the floor-vs-declarations relation but NOT the projection-rule-
vs-operator-intent relation; (c) the "bridge is exactly ⋃ of the single declared blocking
consumer (active_mrr)" claim references a manifest entry that DOES NOT EXIST yet —
internally consistent (Locus D derives it) but the byte-for-byte equivalence proof needs
the derivation implemented first, against the real manifest, with the project-entity
consequence disclosed. Governability at S10 scale is a governance question the packet
must pose, not answer silently.

### T5 — the door ruling (dispatch priority 5): CH-03 FLAG
The §7 axis table tests code, data, seam, customer, and verification axes — soundly. It
omits the axis §4 itself names as the main tradeoff: WHO controls publication halting.
Ruling challenge, precisely: **CORRIDOR is defensible for the code change in this repo
today** (2 declared consumers, vendored manifest in-repo, toothless guard = authority
de facto in-repo, `git revert` restores the constant). It becomes door-adjacent at
exactly the moment H1's governance story is realized: F-4 discharge binds the manifest to
a monolith-owned source, after which retracting consumer authority over this repo's
publish floor is a cross-repo contract retraction — Rider-3-shaped, but Rider 3 covers
token semantics only. The corridor ruling and the governance story currently hold on
MUTUALLY EXCLUSIVE states of F-4. Not BLOCKING: the trade is stated plainly in §4, the
operator is the ratifier, and the fix is one rider. But the ratification packet must not
inherit the §7 table as axis-complete [AV:SRC-001 — construct underrepresentation applies
to door tests too].

### T6 — A6/Seam-4 frozen surfaces (dispatch priority 6): VERIFIED — Locus A does not revive
`SubstrateReader.read(aid) -> ServedNumber` FROZEN v1.0 with no consumer identity
(`serve.py:111-120`); `RefuseReason` CLOSED four-member enum (`:31-37`) with
member-for-member guard test and the C13 precedent showing the sanctioned escape is an
additive payload marker, not a member; `EXPECTED_EXPORTS = 24` guard live. Three
frozen-surface touches for a Seam-4 column check is accurately counted. The A6
falsified-at-Seam-4 / confirmed-at-One-Gate split is sound and is the adjudication's best
structural move — it is what makes Locus D cheap.

### T7 — adjacent finding F-1 (dispatch priority 7): REPRODUCED EXACTLY
Offline fixture, all 9 registered metrics, frame carrying EVERY column any definition
touches: **3 survive (`active_mrr`, `active_ad_spend`, `weekly_transitions`), 6 raise
`ColumnNotFoundError`** — the three conversions on `from_stage`, the two durations and
`stalled_entities` on `exited_at`. The defect is structural (Step-1 select at
`compute.py:83-97` drops filter roots before Step-3 applies the filter at `:106-107`), so
even a perfect frame cannot save them. The adjudication's probed-claim credibility is
INTACT — this adversary found zero fabricated or inflated probe results. F-1's routing
(10x-dev defect, independent) is correct; note it also means H1's "derive the declaration
from the definition" mechanism is only demonstrable on 3 of 9 registry entries until the
lifecycle family is repaired — already disclosed at dissent 5.

## 5. Remediation Pathway (conditions of the PASS)

Ordered; each points at the artifact element that must change. These are conditions on
the RATIFICATION PACKET (the myron `/frame` + pythia `/shape` consumption per digest item
6), not on the adjudication's recommendation, which stands.

1. **[CH-01 → §2 Locus E / §4 bridge-equivalence]** State the projection scoping rule as
   a rule (entity-scoped, per the `floor_columns(entity)` formula); name the author and
   ratification authority of the BLOCKING_AT_PUBLISH token classification; run the E
   derivation against `consumer_column_requirements.vendored.json` AS IT EXISTS and attach
   the receipt — including the disclosure that the existing `offer_id` /
   `nonnull_over_active_subset` project-shape declaration would permanently refuse a
   future project-entity publish gate (100%-NULL `offer_id`) unless rescoped or excluded
   by the scoping rule.
2. **[CH-03 → §7]** Add Rider 4 (or extend Rider 3): publish-blocking declaration
   AUTHORITY — who may author `population_expectation` values that project into the
   publish floor and which repo's review gates them — is part of the endstate
   ratification; the F-4 source-binding discharge is door-adjacent under H1.
3. **[CH-04 → §8 UV-P block]** Record UV-P-1 as DISCHARGED-CONFIRMED (this report's probe,
   re-runnable at the scratchpad script or trivially reconstructable from §2 above). Carry
   UV-P-2 and UV-P-3 forward with named discharge artifacts and owners: UV-P-2 → a latency
   receipt path in the implementation sprint; UV-P-3 → a verbatim question in the operator
   ratification interview with the Locus-B fallback stated.
4. **[CH-02 → §1.6]** (Advisory) Requalify the unit-comment corroboration as analogous,
   not offer-scoped, precedent.
5. **[CH-05]** (Advisory, optional) One external citation each at §1.6 (drift class) and
   §2 Locus D (bounded-context boundary).

## 6. Falsification of This Report

What would revise THIS verdict:

- **CH-01 falsifier**: if the Locus E formula's entity-scoping is shown to be unambiguous
  as written AND the BLOCKING_AT_PUBLISH mapping is shown to be already fixed by the
  existing `_VALID_POPULATION_EXPECTATIONS` vocabulary semantics (i.e., no new constant is
  needed), CH-01 downgrades to ADVISORY and the verdict tends to PASS on remediation of
  CH-03/CH-04 alone.
- **Premise-probe falsifier**: the probe used `str`-typed key columns. If the production
  offer frame's dedup keys are a dtype whose null semantics differ under
  `unique(subset=…)` (e.g., Categorical), the CONFIRMED status weakens — pathway: re-run
  the Layer-2 probe with production dtypes from `OFFER_SCHEMA`. Until shown, CONFIRMED
  stands at MODERATE (probe-receipted, single-version, single-dtype-family).
- **Door-ruling falsifier**: a demonstration that the vendored-manifest CI gate retains
  unilateral in-repo veto over cross-repo declaration changes post-F-4-binding would
  collapse CH-03's authority-relocation argument and restore the §7 table as
  axis-complete.
- **Verdict-inflation check**: if a second rite-disjoint reader finds a BLOCKING-class
  defect this challenge missed (in particular in §3's scoring table, which I audited for
  arithmetic and weighting-disclosure but did not re-derive cell-by-cell), this PASS-WITH-
  CONDITIONS was too generous — that is the standing falsification condition on every
  non-BLOCK verdict this agent renders.

Self-grade: **MODERATE ceiling** (self-ref-evidence-grade-rule — no rite-disjoint second
grader on this report yet). Probe outputs are re-runnable receipts; all Read receipts are
at the shared anchor `7f81e515`. This challenge is iteration 1 of a 2-iteration cap; a
BLOCK at iteration 2 would escalate per T5b, but nothing found here forecasts one.

— arch-adversary, 2026-08-12
