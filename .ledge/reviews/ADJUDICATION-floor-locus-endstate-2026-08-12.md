---
artifact_id: ADJUDICATION-floor-locus-endstate-2026-08-12
schema_version: "1.0"
type: review
artifact_type: review
slug: floor-locus-endstate-2026-08-12
rite: 10x-dev
station: adjudication (architect-led option-enumeration; arch-adversary challenge NEXT)
initiative: substrate-v2-epoch
wave: S8-2
date: 2026-08-12
status: proposed
created_by: architect
evidence_grade: MODERATE
self_grade_ceiling_rationale: "self-ref-evidence-grade-rule — architect adjudicating a design question in its own rite caps at MODERATE; STRONG requires the arch-adversary challenge (P8) plus an in-anger warm-cycle window"
code_truth_anchor: "origin/main 7f81e515 (pulled 2026-08-12)"
consumes:
  - .ledge/spikes/SPIKE-population-floor-scope-2026-08-12.md   # digest item 5 — the delegation
  - .ledge/decisions/ADR-fm5-armb-required-column-contract-locus-2026-06-26.md
  - .ledge/specs/CHARTER-substrate-v2-epoch-2026-07-27.md      # P3/P5/P7/P8/P9
  - .ledge/decisions/CHARTER-decision-space-of-record-2026-07-30.md
produces_for:
  - arch-adversary (P8 challenge)
  - myron /frame + pythia /shape (spike digest item 6 — the landing path)
---

# ADJUDICATION — Floor-locus ENDSTATE for the substrate-v2 dataframes pipeline

> **Scope.** This is an **option slate + recommendation**, NOT a decision. Per spike
> digest item 5 the endstate locus is EXPLICITLY DEFERRED to operator ratification
> after adversarial challenge. Nothing here authorizes a code change.

---

## §0 — Executive summary (read this if you read nothing else)

Three findings reframe the question the delegation asked.

1. **The repo does not have ONE floor with a locus problem. It has THREE floors
   with a consolidation problem — and they have ALREADY DRIFTED.** The substrate
   publish floor says the offer value columns are `{cost, mrr, offer_id,
   weekly_ad_spend}` (blocking, zero-null). The v1 post-build receipt says they are
   `{mrr, offer_id}` (warn-only, 80% rate). The consumer manifest says the project
   shape needs `{offer_id}` with `population_expectation: nonnull_over_active_subset`
   (declared, **inert** — never enforced). RC-C drift is not a future risk here; it
   is the present state. **Adding a fourth definition — whether registry-governed or
   schema-tagged — makes the disease worse, not better.**

2. **A6 IS FALSIFIED AS STATED.** Per-consumer column checking is NOT cheap at "the
   S5 serving contract." `SubstrateReader.read(aid) -> ServedNumber` is a FROZEN
   Protocol carrying no consumer identity; `RefuseReason` is a FROZEN CLOSED enum
   with a guard test; the reader never holds a parsed frame. Three frozen-seam
   touches ⇒ a Seam-4 version event, which is door-adjacent under P8. **But A6 is
   TRUE at a different serve boundary the spike did not name:** the query One-Gate
   (`QueryEngine._derive_column_contract`), where a per-consumer, per-request column
   contract is ALREADY LIVE, ADR-ratified, and canary-proven. The spike conflated
   "serve-time" with "Seam 4."

3. **The mechanism the operator is asking to be invented mostly already exists and
   is ratified.** FM-5 ARM-B landed a two-layer consumer-declaration substrate
   (vendored manifest → SSOT derivation → authoritative wire field → one enforcement
   site) whose declaration schema ALREADY carries a `population_expectation` token
   with the exact value `nonnull_over_active_subset`. It is validated at load and
   then **never read again**. The endstate is not a new locus; it is **finishing an
   accepted one and making the publish floor a projection of it.**

**RECOMMENDATION: Locus D+E hybrid — "declare once, project twice."** One consumer-
declaration SSOT; two derived projections (publish-floor union; serve-time
per-consumer evaluation). Substrate Seam 4 stays a frame-integrity gate and is not
touched. Full statement at §5.

**DOOR RULING: CORRIDOR, with two named door-adjacent riders** (§7).

---

## §1 — Verified ground truth

Every claim below was read at `origin/main 7f81e515` on 2026-08-12. Empirical probes
are marked `[PROBE]` and are re-runnable.

### 1.1 (a) The S5 serving contract — what it validates TODAY, and what column checks would cost

`GatedSubstrateReader.read()` (`src/autom8_asana/substrate/serve.py:409-464`) runs
exactly four checks, in order:

| # | Check | Failure |
|---|---|---|
| 1 | `store.read_current(aid)` resolves | `ArtifactMissing` → `MISSING`; `PointerCorrupt` → `CORRUPT` |
| 2 | `digest_of_frame(frame_bytes)` derives | exception → `CORRUPT` (`serve.py:435-444`) |
| 3 | age arm: `now - built_from_live_at <= sla_seconds` | → `STALE` (`freshness.py:108`) |
| 4 | digest arm: `served_digest == proof.content_digest` | → `CORRUPT` (`freshness.py:110`) |

Plus one non-gating disclosure (future-dated proof, `serve.py:471-473`).

**Freshness, plane, digest, existence. Zero column semantics.** The reader never sees
a column name and never holds a frame — `Provable(frame=bytes, proof=…)`
(`serve.py:90-95`); the adapters pass bytes through (`serve_adapters.py:77`, `:216-221`).

Cost of adding a column-level per-consumer check HERE, itemized:

- **Frozen Protocol signature.** `SubstrateReader.read(self, aid: ArtifactId) ->
  ServedNumber` (`serve.py:114`) carries NO consumer identity. `ArtifactId` is
  `(project_gid, entity_type)` only. Adding a consumer/required-columns parameter
  mutates a surface declared `FROZEN v1.0` (`serve.py:112`) and re-exported from the
  guarded package root (`substrate/__init__.py:82`).
- **Frozen CLOSED enum.** `RefuseReason` = `{stale, corrupt, missing, divergent}`
  (`serve.py:31-37`), asserted member-for-member by
  `tests/unit/substrate/test_seam_contracts.py:60-65`. A fresh, digest-consistent
  artifact that merely lacks a column the caller needs is none of those four. The C13
  precedent (`serve.py:40-60`) shows the sanctioned escape is an **additive payload
  marker**, not a new member — but a payload marker does not answer *whether to refuse*.
- **Frame materialization contract.** `type DigestOfFrame = Callable[[bytes], str]`
  (`serve.py:144`) returns a digest, discarding the frame. The production default
  `digest_of_canonical_frame_bytes` (`prov_sweep.py:63-74`) **already materializes a
  `pl.DataFrame` per call** — so the CPU cost of a null scan is marginal, but the
  reader cannot reach it without a second injected callable or a widened alias.
- **Export-count guard.** `EXPECTED_EXPORTS = 24` with the comment "count change =
  architect finding" (`test_seam_contracts.py:38`).

> **A6 VERDICT — FALSIFIED at Seam 4; CONFIRMED at the query One-Gate.**
> At Seam 4 the extension is three frozen-surface touches ⇒ a seam-version event ⇒
> door-adjacent under charter P8, not "cheap." At `QueryEngine` it is genuinely cheap:
> the request field, the SSOT derivation, the single enforcement site, and the
> per-column population count are **all already built** (§1.2).

`[PROBE]` `sed -n '409,464p' src/autom8_asana/substrate/serve.py` · `sed -n '31,37p'`
· `sed -n '56,86p' src/autom8_asana/substrate/__init__.py`

### 1.2 The already-ratified consumer-column contract (the finding the brief did not anticipate)

`ADR-fm5-armb-required-column-contract-locus-2026-06-26.md` — **status: accepted** —
ratified a **two-layer consumer-declared column contract**, enforced at a single site:

| Layer | Artifact | Status |
|---|---|---|
| L1 declaration (build-time seed) | `src/autom8_asana/dataframes/contracts/consumer_column_requirements.vendored.json` | LIVE, 2 consumers declared |
| SSOT derivation | `field_contract_maps.derive_required_columns(entity_type, endpoint)` — union over matching consumers (`:326-357`) | LIVE |
| L2 wire field (authoritative at runtime) | `RowsRequest.required_columns` (`query/models.py:304-313`) | LIVE on `POST /v1/query/{entity}/rows` |
| Enforcement (One-Gate SITE) | `QueryEngine._derive_column_contract` (`query/engine.py:615-658`) | LIVE |
| Typed signal | `RowsMeta.contract_complete` + `unservable_required_columns` + `column_manifest` (`models.py:487-514`) | LIVE |
| Two-sided canary | `tests/unit/query/test_fm5_armb_canary.py` (RED + GREEN arms) | LIVE |

Two properties of this substrate are decisive for the adjudication:

**(i) The declaration schema ALREADY carries population semantics — and they are inert.**

```
_VALID_POPULATION_EXPECTATIONS = frozenset(
    {"present_any", "present_all_rows", "nonnull_over_active_subset"}
)            # field_contract_maps.py:141-143
_VALID_ON_MISSING = frozenset({"typed_incomplete"})   # :144
```

`ConsumerRequirement.population_expectation` (`:171`) is parsed, range-validated
(`:240-247`), stored — and then **never read by any consumer of the module.**
`[PROBE]` `grep -rn "population_expectation" --include="*.py" src/` returns hits only
in the loader and the dataclass; zero in `engine.py`, zero in `rebuild.py`.

**(ii) The gate is deliberately PRESENCE-only, and the ADR names the gap.**
`_derive_column_contract` computes completeness from **schema membership**, never
`df.columns` (`engine.py:646-649`), for a reason the ADR states verbatim: "the
production project parquet carries a 100%-NULL `offer_id` that a physical-presence
check would mis-read as COMPLETE." The population data IS already computed —
`column_manifest["population"] = {c: df[c].drop_nulls().len() …}` (`engine.py:653-657`)
— but explicitly as "belt-and-braces," **advisory, not a gate**.

So the exact semantic the population floor needs (`nonnull_over_active_subset`) is
declared in the manifest, the exact measurement is computed at the gate, and the two
are not wired together. **That unwired seam IS the endstate work.**

### 1.3 (b) Is every consumer's consumed-column set mechanically derivable?

**Partially — and the exceptions are load-bearing.**

`compute_metric` (`metrics/compute.py:66-120`) consumes, in order: `section` (iff
`scope.classification` is set, `:67-79`), then selects **`{"name" if present} ∪
dedup_keys ∪ expr.column`** (`:83-97`), then applies `expr.filter_expr` (`:106-107`)
and `scope.pre_filters` (`:110-112`), then `unique(subset=dedup_keys, keep="first")`
(`:116`).

The naive derivation `{expr.column} ∪ dedup_keys ∪ {section if classification}` is
**INCOMPLETE**, and the incompleteness is not theoretical:

`[PROBE]` — executed 2026-08-12, `uv run python`:
```
metrics: ['active_ad_spend', 'active_mrr', 'onboarding_to_implementation_conversion',
          'outreach_to_sales_conversion', 'sales_to_onboarding_conversion',
          'stage_duration_median', 'stage_duration_p95', 'stalled_entities',
          'weekly_transitions']
compute_metric(outreach_to_sales_conversion, well-formed frame)
  → RAISED ColumnNotFoundError: unable to find column "from_stage";
    valid columns: ["entity_gid"]
```

**Six of the nine registered metrics are structurally unrunnable through
`compute_metric` today** — every `lifecycle.py` metric whose `filter_expr` roots
(`from_stage`, `to_stage`, `transition_type`, `exited_at`, `entered_at`) fall outside
the Step-1 select set. Only `active_mrr`, `active_ad_spend` (filter roots ⊆
`{expr.column}`) and `weekly_transitions` (no filter) survive.

This matters two ways: (a) any derived-floor design that reads only
`Scope.dedup_keys + expr.column + classification` inherits a **silently incomplete**
consumed set — an RC-C drift generator by construction; (b) it is a latent live defect
in the lifecycle metric family, adjacent to this adjudication and worth a separate
finding.

**A TOTAL derivation is available** and costs one line:

`[PROBE]` polars 1.38.1 — `pl.Expr.meta.root_names()` returns
`['from_stage','to_stage','transition_type']` for the conversion filter and
`['exited_at','entered_at']` for the stall filter. So:

```
consumed(metric) = {expr.column}
                 ∪ set(scope.dedup_keys or [])
                 ∪ ({"section"} if scope.classification else ∅)
                 ∪ roots(expr.filter_expr) ∪ ⋃ roots(scope.pre_filters)
```
is mechanically total **today**, with no schema change — at the cost of one
third-party introspection API dependency (`Expr.meta`).

### 1.4 Consumers OUTSIDE the metric registry — and what protects them under each locus

| Consumer | Frame access | Column set known at… | Derivable from a definition? |
|---|---|---|---|
| `metrics/__main__.py` CLI | `compute_metric` (`:837`) | definition | yes (with §1.3 total derivation) |
| `substrate/live.py` parity leg | `compute_metric` (`:234`) via `served_active_mrr` (`:219-236`) | definition | yes |
| **`POST /v1/query/{entity}/rows`** | `QueryEngine.execute_rows` | **REQUEST TIME** — `where` predicate + `select` + `required_columns` are caller-supplied (`query/models.py:279-313`) | **NO — impossible in principle** |
| `POST /v1/query/{entity}/aggregate` | `QueryEngine.execute_aggregate` | REQUEST TIME (`group_by`, agg specs, HAVING) | NO |
| MCP paths | share the `DataFrameCache` key surface (`serve_adapters.py:248-255`) | REQUEST TIME | NO |
| Lambda direct readers (`traffic_offer_divergence_tripwire.py:905`, `enrollment_intent_bridge.py:657`) | raw `boto3 + pl.read_parquet` | code-local | not registered anywhere |

**This table is the decisive evidence for the operator's binding qualifier.** The
largest and fastest-growing consumer class — the query/MCP API — has **no definition
to derive from, by design**. Its column need is a property of the *request*, not of
any registry. A locus that can only express a per-entity or per-column set is
structurally incapable of serving it, and the insights pipeline the operator is
protecting is exactly that class.

Correspondingly: **a per-consumer contract is the only locus that covers all three
consumer shapes** (definition-declared, manifest-declared, request-declared), because
`required_columns` is the one carrier that all three can populate.

### 1.5 (c) The rebuild/publish floor seam — injectable or frozen-embedded? (architect ruling)

Mechanics, exactly:

```
DefaultAcceptancePredicates.validate()                        rebuild.py:366-421
  active = active_predicate(frame) or frame                        :368-370
  if active.height < min_rows: FAIL                                :371-378
  null_columns = _value_columns_with_nulls(active); if any: FAIL   :379-384
_value_columns_with_nulls(frame)                              rebuild.py:732-751
  from autom8_asana.substrate.freshness import _VALUE_COLUMNS      :741   ← module-local import
  offenders = {c for c in _VALUE_COLUMNS if absent or null_count>0} :743-750
_VALUE_COLUMNS = ("cost","mrr","offer_id","weekly_ad_spend")  freshness.py:154
_DIGEST_SCHEME = "sv2-canonical-digest-1"                     freshness.py:158
canonical_digest() selects sorted(_VALUE_COLUMNS)             freshness.py:258-264
```

Wiring site: `live.rebuild_offer_v2` constructs
`DefaultAcceptancePredicates(active_predicate=active_offer_rows)` (`live.py:778-780`)
— the *row* predicate is injected; the *column* set is not.

**RULING (architect, on the mechanics fork the spike disclosed at line 51):**

> **The floor set is FROZEN-SEAM-ADJACENT at the constant, but the change is
> SEAM-USE, not a seam amendment — provided three conditions hold.**
>
> - `AcceptancePredicates` (the **Protocol**) is in the frozen `__all__`
>   (`substrate/__init__.py:75`) and is injected per-rebuild (`rebuild.py:480`,
>   `:523`, `:533`). Any conforming validator may be supplied. **The seam is open.**
> - `DefaultAcceptancePredicates` is a **non-exported** concrete dataclass with
>   defaulted fields. Adding a `floor_columns: tuple[str,...] | None = None` field
>   (or a `floor_source` callable) is an additive change to an S4-owned
>   implementation. **Not a seam change.**
> - `_VALUE_COLUMNS` is **double-duty and MUST NOT MOVE**: it is the pinned column
>   set of the FROZEN `sv2-canonical-digest-1` scheme (`freshness.py:145-158`, "stable
>   for the life of the FROZEN v1.0 seam"). The re-use at `rebuild.py:741` was
>   deliberate ("ONE value-column source of truth (no drift enum)", `rebuild.py:336`)
>   and is precisely the coupling that must now be cut.
>
> **Three conditions for SEAM-USE classification:** (1) `_VALUE_COLUMNS` is read-only
> and unchanged; (2) the new floor set is a **separate** definition with its own name;
> (3) `AcceptancePredicates.validate`'s signature is untouched. If any is violated —
> in particular if a design proposes narrowing `_VALUE_COLUMNS` so the digest and the
> floor stay one constant — it becomes an **architect finding AND a digest-scheme
> version event**, i.e. door territory. **REFUSE that shape.**

### 1.6 The consolidation finding — three floors, already drifted

| # | Definition | Site | Offer set | Bite | Scope |
|---|---|---|---|---|---|
| 1 | `_VALUE_COLUMNS` | `substrate/freshness.py:154` | `cost, mrr, offer_id, weekly_ad_spend` | **BLOCK publish**, zero-null | v2 active rows |
| 2 | `_VALUE_COLUMNS_BY_ENTITY` | `dataframes/builders/post_build_population_receipt.py:60-70` | `mrr, offer_id` (`unit`: `mrr` only) | **WARN**, ≥80% non-null rate | v1 active/activating |
| 3 | `consumer_column_requirements.vendored.json` | `contracts/…vendored.json` | `offer_id` (project shape) | typed-incomplete, **presence only** | per-consumer, per-endpoint |
| (4) | `EntityDescriptor.key_columns` | `core/entity_registry.py:559` | `office_phone, vertical, offer_id` | resolution index | per-entity |

Three answers to "what are the offer value columns," three enforcement strengths, and
the v1 receipt's own docstring records the reasoning that produced the divergence:
`weekly_ad_spend` and `discount` are **"LegitimatelySparse … including them would
manufacture false WARNs, the $8,775/7-row null-fossil anti-precedent"**
(`post_build_population_receipt.py:63-70`). That is an in-repo, independently-reached,
earlier precedent that `cost` and `weekly_ad_spend` do **not** belong in a blocking
floor — which corroborates the bridge's `{mrr, office_phone, vertical}` rescope on
evidence the bridge did not cite.

**RC-C drift is not a hypothetical criterion in this adjudication. It is the observed
present state, and it is the strongest argument against any locus that mints a fourth
definition.**

### 1.7 (d) Fleet-kit (S10) dimension

S10's bar is verbatim: *"a sibling repo can `/frame` DIRECTLY from the kit
(template-application bar)"*, templatizing **GATE-PROVEN forms only, not speculative**
(`substrate-v2-epoch.shape.md:330-352`); `S8 → S10` and `S9 → S10` are hard edges
(`:641-642`).

`[PROBE]` `autom8y-data` (the first sibling per P1-fleet): its consumer model is
`InsightDefinition` (`src/autom8_data/analytics/insights/models.py:135+`) — a
declarative per-insight spec with `required_filters` (`:263`), `internal_columns`
(`:316`), and per-metric column guarantees (`:352`). Insights **compose** many metrics
over one frame. There is **no** per-entity value-column registry and **no** schema-tag
substrate to receive a per-entity or per-column form.

Consequence: a **per-consumer declaration form** ports as data (each `InsightDefinition`
gains a population declaration; the derivation is a one-function port). A **per-entity
registry form** would have to be invented in the sibling from scratch and would be
*more* pigeonholing there than here, because one entity feeds many insights with
disjoint column needs. A **schema-tag form** requires the sibling to have a comparable
`ColumnDef` lattice, which it does not.

---

## §2 — The option slate

Loci 1–3 are the delegation's candidates. D, E, F are enumerated additions (per
`option-enumeration-discipline`); F is an enabling mechanism that composes with any
of A/D rather than a rival locus.

### Locus A — Serve-time per-consumer DERIVED from the metric definition
*(delegation candidate 1)*

Each metric's refusal predicate derives its blocking columns from its own `Metric`
(value column + dedup keys + section scope + filter roots) at read time. Publish floor
retreats to frame sanity (`min_rows`, digest self-consistency, proof well-formedness).

- **Construction**: no config; the floor is a pure function of the definition. Strongest
  possible anti-RC-C property *for definition-declared consumers*.
- **Fatal gap**: covers only the 3 (of 9) runnable metric-registry consumers. The query
  API, aggregate API, MCP, and lambda readers have no `Metric` — under Locus A **they
  are protected by nothing**. §1.4.
- **Fatal gap 2**: "serve-time" reads as Seam 4, where A6 is falsified (§1.1). At the
  query One-Gate it is not derivable at all (no definition exists).
- **Latent cost**: requires the §1.3 total derivation (`Expr.meta.root_names()`), i.e.
  a polars-internals dependency, or the lifecycle-metric defect must be fixed first.

### Locus B — Registry-governed per-entity `serving_floor_columns` (C17 pattern)
*(delegation candidate 2)*

`EntityDescriptor` gains a governed field beside `freshness_sla_seconds`
(`entity_registry.py:189`), operator-ratifiable, one set per entity.

- **Strong**: proven in-repo pattern (C17 landed `86aeb0d3`); operator-visible;
  trivially injectable into `DefaultAcceptancePredicates`; cheapest to ship.
- **Fatal for the binding qualifier**: consumer-blind **by construction**. One set per
  entity cannot express "`active_mrr` needs `{mrr, office_phone, vertical}` while
  `active_ad_spend` needs `{weekly_ad_spend, office_phone, vertical}` while insight-X
  needs `{cost, section, vertical}`." The floor is either the union (over-refusal — the
  W2 shape the operator just ruled against) or an intersection (under-protection —
  confidently wrong). **This is the definition of pigeonholing the pipeline.**
- **Drift**: mints definition #4. Nothing binds it to what any consumer reads.

### Locus C — Schema-tagged columns (`floor: blocking | warning` per `ColumnDef`)
*(delegation candidate 3)*

`ColumnDef` (`dataframes/models/schema.py:38-43`) gains a floor tag; travels with the
entity schema.

- **Strong**: best "travels with the data" story; `ColumnDef.nullable` already exists as
  a precedent and `DataFrameSchema.to_dict()` already serializes it (`:173`).
- **Structural mismatch**: the real predicate is **conditional** —
  `non-null over the classifier-ACTIVE subset` — and a per-column tag cannot carry the
  subset predicate. It would need a companion active-predicate reference, i.e. Locus B
  smuggled in beside it.
- **Semantic-collision hazard (named precedent)**: `nullable` is consumed by
  `DataFrameSchema.validate_row` (`:193`) as a *row-validation* property. Overloading it
  — or adding a near-synonym next to it — reproduces the exact failure the FM-5 ADR
  rejected as **D2-A: "SEMANTIC COLLISION (load-bearing reject)"** when folding column
  completeness into `honest_contract_complete`.
- Consumer-blind, same as B. Mints definition #4.

### Locus D — **Consumer-contract locus: complete the ratified FM-5 ARM-B substrate**
*(enumerated)*

Wire `population_expectation` from declared-and-inert to enforced. Concretely: the
One-Gate derivation (`engine.py:615-658`) evaluates each declared column against its
declared expectation (`present_any` / `present_all_rows` / `nonnull_over_active_subset`)
using the population it **already computes** at `:653-657`, and flips
`contract_complete` accordingly. `required_columns` on the wire stays authoritative for
request-time consumers; the manifest stays the build-time/CI seed. Definition-declared
consumers (metrics) get a manifest entry **derived** from their `Metric` (§1.3), so
there is one declaration substrate, not two.

- **Adds a predicate, not a mechanism.** Declaration schema: exists. SSOT: exists. Wire
  field: exists. Enforcement site: exists. Population measurement: exists. Canary: exists.
- Per-consumer by construction — covers all three consumer shapes (§1.4).
- Anti-drift: the enforcement reads the same declaration the consumer authored.
- **Gap**: on its own it protects only at READ time. It does not stop a null-poisoned
  artifact from being published and served to an *undeclared* consumer. That is what E
  is for.

### Locus E — **Publish floor as a PROJECTION of declared consumer contracts**
*(enumerated)*

The publish-time blocking set is not authored; it is **derived**:
`floor_columns(entity) = ⋃ { c : c declared by some consumer with
population_expectation ∈ BLOCKING_AT_PUBLISH }`, injected into
`DefaultAcceptancePredicates` via the new `floor_columns` field (§1.5 SEAM-USE ruling).
`_VALUE_COLUMNS` is untouched.

- Kills RC-C by construction: the floor **cannot** diverge from what a consumer declared,
  because it is computed from the declarations.
- Kills over-refusal: a column no consumer blocks on cannot block a publish.
- Self-narrowing and self-widening: a new consumer declaring a new blocking column
  widens the floor with no floor edit — the extensibility the operator asked for.
- **Gap**: an *undeclared* consumer is invisible to the floor. Mitigated by (i) the
  manifest CI parity check the FM-5 ADR already established, (ii) the PROV-7 warning
  channel already ratified in the spike digest, (iii) `on_missing` remaining a closed
  vocabulary so a silent opt-out is unconstructable.

### Locus F — **Published population manifest (side-car)** *(enumerated; enabling, composable)*

At publish, the rebuilder measures per-column non-null counts over the active subset
once and writes them as an **additive sibling key** on the CAS pointer
(`store.py:383-386` writes `{"version_id", "proof"}`; `_proof_from_json` reads only
named keys at `:533-542`, so an added top-level `"population"` key is backward-safe and
does NOT touch the FROZEN 3-field `FreshnessProof`). Consumers then evaluate their own
predicate against the manifest **without parsing the frame**.

- Decouples MEASURE (producer, once, cheap) from DECIDE (each consumer, O(1)).
- This is what makes per-consumer evaluation cheap at N-consumer scale, and it is the
  only enumerated way to give the Seam-4 read path column awareness **without** touching
  `SubstrateReader.read` or `RefuseReason` (the consumer, not the reader, decides).
- **Cost**: a new observable on the pointer ⇒ a store-format compatibility question; and
  it duplicates data derivable from the frame, so it must be digest-bound or it becomes
  its own drift surface.
- **Disposition**: NOT required for the endstate. Recommended as a **deferred enabler**,
  reconsidered when either (a) a consumer needs the decision pre-parse, or (b) frame
  parse cost at read becomes measurable.

### Hybrid H1 — **D + E: "declare once, project twice"** *(the recommendation)*

ONE declaration substrate (FM-5 ARM-B, extended with enforced population semantics);
TWO derived projections:

```
                 consumer declarations  (manifest L1  +  wire required_columns L2)
                              │  field_contract_maps SSOT
              ┌───────────────┴────────────────┐
   PUBLISH projection                 SERVE projection
   floor_columns = ⋃ blocking          per-request evaluation at the
   → DefaultAcceptancePredicates       QueryEngine One-Gate
     (floor_columns field, SEAM-USE)   (contract_complete + named columns)
              │                                 │
     artifact never published          undeclared/ad-hoc consumer gets a
     null-poisoned for a               typed per-request answer, no publish halt
     DECLARED blocking consumer
                              │
              everything else → PROV-7 metric + digest line (ratified)

   Substrate Seam 4 (freshness · digest · existence) — UNTOUCHED
```

### Hybrid H2 — **B + D** *(seriously considered; rejected — reasoning at §4)*

Registry-governed per-entity floor as the **default** (fast, operator-visible), with the
per-consumer contract layered above it for consumers wanting more. Rejected because the
per-entity default is exactly the pigeonholing the qualifier forbids, and two coexisting
sources of blocking truth reproduce §1.6 with better documentation.

---

## §3 — Per-criterion scoring

Scale: **++** strong / **+** adequate / **0** neutral / **−** weak / **−−** disqualifying
on that criterion.

| Criterion (weight) | A serve-derived | B registry | C schema-tag | **H1 = D+E** | H2 = B+D | F (enabler) |
|---|---|---|---|---|---|---|
| **Multi-consumer extensibility** (BINDING) | − covers 3 of 9 metrics; zero coverage of the request-time class | **−−** consumer-blind by construction | **−−** consumer-blind; cannot carry the active-subset predicate | **++** all three consumer shapes; new consumer = new declaration, no core edit | + but the default layer stays blind | + orthogonal |
| **RC-C drift resistance** | ++ for its covered subset; 0 elsewhere | −− mints definition #4, unbound to any reader | −− mints definition #4 | **++** floor is *computed from* the declarations — divergence unconstructable | − two blocking truths coexist | 0 unless digest-bound |
| **P3 subtraction posture** | + no config, but needs `Expr.meta` + a lifecycle-metric fix | + tiny diff, but +1 config home | − new tag semantics beside `nullable` | **++** adds a *predicate* to a ratified mechanism; net −1 floor definition at consolidation | 0 net +1 home | − net +1 observable |
| **Frozen-seam compatibility** | **−−** requires 3 frozen-surface touches at Seam 4 (§1.1) | ++ registry is not frozen | + `ColumnDef` not frozen | **++** SEAM-USE only (§1.5); `_VALUE_COLUMNS` untouched; `read()`/`RefuseReason` untouched | ++ | + additive pointer key; needs a compat ruling |
| **Migration cost from the BRIDGE** `{mrr, office_phone, vertical}` | high — bridge set has no `Metric` carrier at publish time | **low** — bridge set becomes the descriptor value verbatim | medium — retag 3 columns across schemas | **low** — bridge set is exactly `⋃` of one declared consumer (`active_mrr`: `mrr` + dedup keys); the bridge *is* H1's first projection, computed by hand | low | n/a |
| **Fleet-template reusability (S10)** | − sibling has no `Metric`; has `InsightDefinition` | − sibling has no per-entity value registry; would be invented | − sibling has no `ColumnDef` lattice | **++** declaration form ports as data onto `InsightDefinition`; derivation is one function | 0 | + |
| **Blast radius if WRONG** | medium-high — a seam-version event is expensive to unwind | **low** — one field, revert | medium — tags spread across schemas | **low-medium** — declaration schema is `schema_version`-ed and cross-repo; see §7 | medium | medium |
| **Honest floor: never confidently wrong** (charter §2) | + within coverage; **−** silent for uncovered consumers | − union over-refuses or intersection under-protects | − same | **++** blocking for declared consumers; typed-loud for the rest; nothing silent | + | + |

**Rank: H1 ≫ B ≈ H2 > A > C.**
B ranks second **only** on cost-to-ship and blast radius — it fails the binding
qualifier, which is dispositive. A is the delegation's own recommendation and is
*directionally right* (derive, don't configure) but was scoped to the wrong consumer
population and the wrong seam.

---

## §4 — Recommendation

> **RECOMMEND Hybrid H1 (Locus D + Locus E): one consumer-declaration substrate; two
> derived projections. Substrate Seam 4 untouched. `_VALUE_COLUMNS` untouched. The
> publish floor becomes a computed projection of declared consumer contracts, not an
> authored constant. Locus F deferred as a named enabler. Loci B and C rejected on the
> binding qualifier; Locus A absorbed (its derivation logic becomes how metric
> consumers author their declaration).**

**Rationale in four moves.**

1. **The operator's qualifier selects the locus almost by itself.** "Many consumers,
   ASR is one implementation, don't pigeonhole" is a statement that the blocking set is
   a property of the **consumer**, not of the entity and not of the column. B and C both
   locate it on the entity/column. Only a per-consumer carrier can express it, and only
   `required_columns` (or a manifest entry) is a carrier all three consumer shapes can
   populate (§1.4).

2. **The mechanism is already ratified — completing it is subtraction, inventing a
   parallel one is addition.** FM-5 ARM-B chose O3 over O1 ("each consumer
   re-implements") and O2 ("wire-only, no build-time parity") for reasons that apply
   verbatim to the population question. Its declaration schema already contains
   `nonnull_over_active_subset`. Minting a registry or schema-tag locus now would
   fork the contract lattice from the ADR that governs it, six weeks after ratification.

3. **The publish floor should be a PROJECTION, not a peer.** §1.6 shows three
   independently-authored answers to "what are the offer value columns," already
   divergent. Every locus that *authors* a fourth answer inherits that failure mode. E
   makes the floor uncomputable-as-divergent: it is `⋃` over the declarations, so
   "the floor drifted from what consumers need" is not a bug you can write.

4. **It respects every frozen surface, so it is corridor work.** Under the §1.5 ruling
   H1 is SEAM-USE: an additive field on a non-exported dataclass, an additive predicate
   at an existing One-Gate, zero changes to `_VALUE_COLUMNS`, `SubstrateReader.read`,
   `RefuseReason`, or the export count. P7 economy holds — no door is opened.

**Consequence for the BRIDGE (already ratified, ships now).** The bridge set
`{mrr, office_phone, vertical}` is **exactly** `⋃` of the single declared blocking
consumer (`active_mrr`: value column `mrr` + dedup keys `office_phone, vertical`),
computed by hand. So the bridge is not a detour from H1 — **it is H1's first projection,
hardcoded.** The endstate DELTA is therefore: replace the hardcoded tuple with the
derivation that produces it, and prove by test that the derivation reproduces the
bridge set byte-for-byte at the moment of the swap. That is the cheapest possible
bridge→endstate landing, and it gives myron/pythia (digest item 6) a landing path with
a built-in equivalence proof.

### Main tradeoff (stated plainly)

**H1 moves the blocking decision from a place the platform controls to a place
consumers control.** Under the status quo, one constant in this repo decides what may
be published. Under H1, the union of consumer declarations decides. That is the
extensibility the operator asked for and it is also the cost: a consumer that declares
too aggressively can halt publication for everyone (the over-refusal class returns
through a new door), and a consumer that declares nothing is protected by nothing but
the warning channel. The mitigations — closed `on_missing` vocabulary, CI parity on the
manifest, PROV-7 alarm, and the `min_rows` + digest + proof floor that always remains —
are real but are **governance, not construction**. H1 trades a construction guarantee
for a governed one. That trade should be made consciously.

The spike's own tradeoff also stands and is inherited unchanged: **the window stops
FORCING data fixes.** Three provisioning wounds were cured this week because serving
halted. A metric + a digest line is easier to ignore than a halted window. H1 does not
solve that; it relocates it into PROV-7's alarm discipline.

### Dissent-worthy weaknesses (honest list — arch-adversary should start here)

1. **A6's inverse is untested.** I falsified "serve-time is cheap at Seam 4" by reading
   the frozen surfaces. I did **not** measure the cost of the population predicate at
   the `QueryEngine` One-Gate under load. `column_manifest` already scans every served
   column (`engine.py:653-657`) and is computed only when a contract is declared — but
   I have no latency receipt. **Claim: cheap. Evidence: structural, not measured.**
2. **The declaration substrate is CROSS-REPO and half-bound.** The manifest is
   monolith-owned; `requirements_drift_check` runs in **schema-only mode** because the
   source path has not been handed back (`field_contract_maps.py:360-371`, telos DEFER).
   H1 makes the publish floor depend on a manifest whose freshness guard is currently
   toothless. That is a real load-bearing weakness and the adversary should press it.
3. **`population_expectation` may not be expressive enough.** It has three tokens.
   `nonnull_over_active_subset` hard-codes "active" as *the* subset — but "active" is the
   OFFER classifier's notion (`live.py:192-216`). A sibling entity, or an insight scoped
   to a non-active section, has no token. Widening the enum is additive but is a
   **cross-repo schema event** (`schema_version: 1`).
4. **The dedup-collapse hazard is asserted, not proven here.** The spike states polars
   `unique(subset, keep="first")` treats nulls as equal, silently collapsing distinct
   offers. I read the call site (`compute.py:116`) and the claim is consistent with it,
   but **I did not run a null-key collapse probe.** If that premise is wrong, the case
   for `office_phone`/`vertical` being *blocking* (rather than warning) weakens
   materially — and so does the bridge. **This is the single highest-value falsification
   target in this document.**
5. **Six of nine metrics are broken (§1.3) and I am recommending a design that leans on
   metric definitions as declaration sources.** The recommendation survives (the query
   API doesn't use `Metric` at all, and the two live offer metrics are among the three
   that work) — but "derive the declaration from the definition" is untested on 2/3 of
   the registry, and the lifecycle family would need repair before it could declare.
6. **Locus B is genuinely cheaper and I may be over-weighting the qualifier.** If the
   real consumer population stays at "active_mrr plus two or three siblings on the same
   entity," B ships in a day, is operator-visible, and is trivially reversible. My case
   against it rests on a *projected* consumer population (the insights pipeline). If
   that projection is wrong, B is the better call and H1 is over-engineering — a direct
   charter §3 violation ("do NOT gold-plate"). **The adversary should test whether the
   many-consumers premise is evidenced or assumed.**
7. **Self-referential grading.** Architect adjudicating an architect-owned design
   question in its own rite. `[MODERATE]` ceiling per `self-ref-evidence-grade-rule`;
   nothing here is STRONG until the P8 challenge and an in-anger window.

---

## §5 — What the recommendation is NOT

- **Not** a proposal to touch `_VALUE_COLUMNS`, `_DIGEST_SCHEME`, `canonical_digest`,
  `FreshnessProof`, `SubstrateReader.read`, `RefuseReason`, `RefusePayload`, or the
  24-symbol export surface.
- **Not** a proposal to move the bridge. The bridge ships as ratified.
- **Not** a proposal to re-open the tiered/PROV-7/timing decisions (digest items 1–4,
  operator-DECIDED).
- **Not** an S10 kit commitment (§7 rider 2).
- **Not** a plan. The landing path is myron `/frame` + pythia `/shape` per digest item 6.

---

## §6 — Adjacent findings surfaced (not decided here; per charter §7 "surfaced as findings, not absorbed")

| # | Finding | Evidence | Suggested route |
|---|---|---|---|
| F-1 | **Six of nine registered metrics raise `ColumnNotFoundError` through `compute_metric`** — every `lifecycle.py` metric whose `filter_expr` roots fall outside the Step-1 select set | §1.3 `[PROBE]`; `compute.py:83-97` vs `definitions/lifecycle.py:53-57,107,121,156` | 10x-dev defect; independent of this adjudication |
| F-2 | `population_expectation` / `on_missing` are **validated then never read** — a declared-and-inert contract field | `field_contract_maps.py:141-144,240-253`; zero consumers | folds into H1; is a standalone finding if H1 is rejected |
| F-3 | **Three divergent value-column definitions** (§1.6) with no binding between them | `freshness.py:154` vs `post_build_population_receipt.py:60-70` vs the vendored manifest | consolidation target; the endstate's real prize |
| F-4 | `requirements_drift_check` is stuck in **schema-only mode** — the manifest freshness guard has no teeth until the monolith source path is handed back | `field_contract_maps.py:360-371` | blocks H1's governance story; needs a telos-DEFER discharge |
| F-5 | Lambda readers (`traffic_offer_divergence_tripwire.py:905`, `enrollment_intent_bridge.py:657`) read frames via raw `boto3 + pl.read_parquet`, **bypassing every gate and every contract** | grep, §1.4 | inventory item; no locus protects them |

---

## §7 — Door-vs-corridor ruling

> **RULING: the floor-locus endstate is a CORRIDOR decision (P7 economy, auto-ratifying
> under P8), with TWO explicitly named door-adjacent riders that must NOT be bundled
> into the same ratification.**

**Why corridor.** Charter P8 reserves the operator for **one-way doors**; P9 makes
design/build/merge autonomous. Test each irreversibility axis:

| Axis | Assessment |
|---|---|
| Code reversibility | Additive field + additive predicate + additive derivation. `git revert` restores the prior floor exactly. **Two-way.** |
| Data reversibility | While a narrower floor is live, artifacts publish that a stricter floor would have refused. They are immutable S3 versions — but the **current** pointer is replaced on the next warm cycle (SLA 3600s, `entity_registry.py:473+`). Worst case is one cycle of a narrower floor, then full restoration. **Recoverable within ~1h.** |
| Frozen-seam exposure | Zero, under the §1.5 SEAM-USE conditions. **No seam-version event.** |
| Customer/money/external-commitment exposure (charter core §5b) | The served number's *definition* is unchanged; only the refusal predicate over inputs moves. No customer surface, no spend, no external commitment. **Not on the sensitive list.** |
| Independent verification available (charter core §6) | Yes: two-sided discriminating canary + qa gate + arch-adversary. Autonomy is licensed. |

**Rider 1 — the shape that WOULD be a door (pre-refused).** Any design that narrows
`_VALUE_COLUMNS` so the digest set and the floor set stay one constant is a
**`sv2-canonical-digest-1` scheme version event**: every published `content_digest`
re-derives differently, every live proof becomes CORRUPT at the gate, and the parity
window's digest lineage breaks. That is one-way and operator-reserved. **This
recommendation is constructed specifically to avoid it, and the shape should be
refused on sight if it appears in any downstream plan.**

**Rider 2 — S10 fleet-kit propagation is a SEPARATE, door-class commitment.** Once the
form is templatized and applied to `autom8y-data` and siblings, retraction is an
N-repo migration and — because the declaration schema is a cross-repo wire contract
with `schema_version: 1` — a coordinated breaking change. **Do not ratify the endstate
locus and its fleet propagation in the same act.** S10's own entry criterion already
demands GATE-PROVEN forms (`shape.md:342`); the honest gate is ≥1 in-anger warm-cycle
window under the endstate in this repo first.

**Rider 3 — the cross-repo declaration schema is the real irreversibility.** Widening
`_VALID_POPULATION_EXPECTATIONS` is additive and safe; **re-defining an existing
token's meaning is not**, because the monolith authors against it. Recommend a standing
rule: population-expectation tokens are append-only, and semantic change requires
`schema_version: 2`.

---

## §8 — Evidence and grade

**Grade: `[STRUCTURAL | MODERATE]`.** Ceiling per `self-ref-evidence-grade-rule`
(architect adjudicating an architect-owned question in its own rite).

Direct-inspection receipts (all at `origin/main 7f81e515`, 2026-08-12):
`substrate/serve.py:31-37,90-95,111-120,144,374-473` ·
`substrate/serve_adapters.py:67-101,206-231,248-255` ·
`substrate/freshness.py:92-112,145-158,224-281` ·
`substrate/rebuild.py:312-322,325-421,732-751` ·
`substrate/store.py:383-386,525-542` ·
`substrate/prov_sweep.py:63-74` ·
`substrate/live.py:192-216,219-236,755-782` ·
`substrate/__init__.py:56-86` ·
`tests/unit/substrate/test_seam_contracts.py:38,52-65` ·
`metrics/compute.py:66-120` · `metrics/metric.py:18-54` · `metrics/expr.py:53-58` ·
`metrics/definitions/offer.py:20-60` · `metrics/definitions/lifecycle.py:32-175` ·
`query/engine.py:60-300,615-658` · `query/models.py:274-314,487-514` ·
`dataframes/contracts/field_contract_maps.py:141-144,164-183,240-265,326-371` ·
`dataframes/contracts/consumer_column_requirements.vendored.json` ·
`dataframes/builders/post_build_population_receipt.py:1-75` ·
`dataframes/models/schema.py:19-44,160-195` · `core/entity_registry.py:96-200,473-620` ·
`.ledge/decisions/ADR-fm5-armb-required-column-contract-locus-2026-06-26.md` ·
`.ledge/specs/CHARTER-substrate-v2-epoch-2026-07-27.md:60-125` ·
`.sos/wip/frames/substrate-v2-epoch.shape.md:300-360,637-650` ·
`/Users/tomtenuta/Code/a8/a8/repos/autom8y-data/src/autom8_data/analytics/insights/models.py:135-370`

Executable probes (re-runnable):
`uv run python -c "…compute_metric(outreach_to_sales_conversion, …)"` →
`ColumnNotFoundError: unable to find column "from_stage"` ·
`pl.Expr.meta.root_names()` on the three filter families → total root extraction (polars 1.38.1) ·
`grep -rn "population_expectation" --include="*.py" src/` → loader + dataclass only.

**Unverified premises carried forward:**

`[UV-P: polars unique(subset, keep="first") treats null dedup keys as equal, silently collapsing distinct offers | METHOD: deferred-to-adversary-probe | REASON: inherited from SPIKE §Load-bearing-facts-3; call site read (compute.py:116) and consistent, but no collapse probe was run in this adjudication — §4 dissent item 4 names it the highest-value falsification target]`

`[UV-P: the population predicate at the QueryEngine One-Gate is cheap under production load | METHOD: deferred-to-implementation-benchmark | REASON: structural argument only (the column_manifest scan already exists at engine.py:653-657 and is contract-gated); no latency receipt taken — §4 dissent item 1]`

`[UV-P: the insights pipeline will carry MANY consumers with heterogeneous column needs | METHOD: deferred-to-operator | REASON: the binding qualifier is an operator statement of intent, not an observed consumer census; if the population stays small and homogeneous, Locus B is the better call — §4 dissent item 6]`
