---
type: adr
adr_id: ADR-pipeline-export-engine-left-preservation-guard
initiative: project-asana-pipeline-extraction
phase: 1
sprint: sprint-2
created: 2026-04-28
rite: 10x-dev
specialist: architect
status: accepted
session_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
upstream_artifacts:
  - .ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md
companion_tdd: .ledge/specs/TDD-pipeline-export-phase1.md
resolves: ENGINE-DESIGN-Q1
self_ref_cap: MODERATE
---

# ADR — Engine LEFT-PRESERVATION GUARD: Mechanism Selection

## §1 Title

Engine LEFT-PRESERVATION GUARD: Mechanism Selection — (a) PRIMARY DEFENSE post-EXPLAIN assertion vs (b) ESCAPE VALVE caller opt-in.

## §2 Status

**accepted** (Sprint 2 architect, 2026-04-28).

This ADR is forward-binding on Phase 2 implementation; Phase 1 carries the design constraint via the ExportRequest contract reservation (`ExportOptions.model_config = ConfigDict(extra="allow")` per TDD §3.2 + spike handoff §6 P1-C-02 at L533-549) but does not implement either mechanism (Phase 1 ships single-entity export per spike handoff §3:230-232).

## §3 Context

### 3.1 Spike-Surfaced Defect Class

Spike handoff §3 critic_substitution_chain at L194-237 surfaces a divergent finding between S3 PROTO and S4 MOONSHOT regarding Polars LazyFrame optimizer behavior on LEFT JOIN with non-null equality predicates. Verbatim from spike handoff §3:198-200:

> S3 PROTO §7 LL.378-388 framing as "semantic contract change callers must be aware of"; S4 MOONSHOT §4 Claim 2 LL.326-364 framing as "wrong-result silent failure equivalent to B-R1; underweighted".

Empirically (spike handoff §8 evidence row 4, citing PROTO-cascade-vs-join.md:232-244 verbatim INNER JOIN header): when a Phase 2 C5-PATH dispatch occurs with `request.join.how == "left"` and a non-IS-NULL equality predicate targets a join-target column, the Polars 1.38.1 optimizer rewrites LEFT JOIN to INNER JOIN. Rows where the join target is NULL are silently excluded from the result.

This is a **silent denominator shift** at query-result altitude — the F-HYG-CF-A class of failure (RETROSPECTIVE-VD3-2026-04-18.md:145, cited at spike handoff §8 evidence row 23): a result is produced; the result LOOKS correct; downstream consumers cannot tell rows were dropped.

### 3.2 Spike Handoff §3 Verbatim (lines 201-237)

The spike adjudicated three candidate mechanisms (verbatim from spike handoff at L201-225):

> **(a) PRIMARY DEFENSE — POST-EXPLAIN ASSERTION**: invoke `lazy_frame.explain()` before `.collect()`; parse the resulting plan; assert the top-level join node header matches `request.join.how`. If the optimizer rewrote LEFT-to-INNER, either (i) raise LeftJoinRewrittenError, OR (ii) re-execute with a defensive coalesce/anti-join post-step that restores the LEFT-OUTER row set.
>
> **(b) EXPLICIT CALLER OPT-IN**: if the ExportRequest contract (Phase 1 Sprint 1) admits a `predicate_join_semantics` field with values {"preserve-outer", "allow-inner-rewrite"}, then "allow-inner-rewrite" disables defense (a) for the request. Default MUST be "preserve-outer" — fail-loud, not silent.
>
> **(c) DOCUMENTATION-ONLY (REJECTED as sole defense)**: the platform has burned on the F-HYG-CF-A "documentation without mechanism" pattern (RETROSPECTIVE-VD3-2026-04-18.md:145). Documentation alone is INSUFFICIENT per telos-integrity-ref §3 Gate B precedent.

### 3.3 The Phase 1 Architect's Question

Per spike handoff §3 escalation at L227-237 (verbatim):

> ENGINE-DESIGN-Q1: the Phase 1 architect (Sprint 2) MUST decide between (a) and (b) above when designing the dual-mount router and format-negotiation surface. Phase 1 ships single-entity export so the LEFT-rewrite question does not fire in Phase 1 proper, BUT the Sprint 1 ExportRequest contract MUST NOT foreclose either (a) or (b). Specifically: the contract MUST leave room for an optional `predicate_join_semantics` field even if Phase 1 does not populate it. See §6 phase_1_constraints constraint P1-C-04.

This ADR resolves ENGINE-DESIGN-Q1.

## §4 Decision

**HYBRID** — both mechanisms (a) AND (b) are adopted. Mechanism (a) is the engine's default Phase 2 behavior (fail-loud, structurally enforced); mechanism (b) is the caller's explicit escape valve (opt-out for callers with corroborating reason to accept INNER semantics).

### 4.1 Binding Specification (Phase 2 implementation territory)

**Mechanism (a) PRIMARY DEFENSE — Engine-Side, ALWAYS-ON Default:**

- When the Phase 2 boundary_predicate dispatch (spike handoff §3:157-184) classifies a request as C5-PATH AND `request.join.how == "left"`:
  - The engine MUST invoke `lazy_frame.explain()` before `.collect()`.
  - The engine MUST parse the resulting plan and assert the top-level join node header matches `request.join.how`.
  - On mismatch (LEFT rewritten to INNER), the engine MUST execute one of:
    - Sub-option (i): raise `LeftJoinRewrittenError` (fail-loud).
    - Sub-option (ii): re-execute with a defensive coalesce / anti-join post-step that restores the LEFT-OUTER row set.
  - The Phase 2 implementation ADR (separate, Phase 2 architect) selects between (i) and (ii) based on engine-internal performance characteristics measured at Phase 2 PROTO altitude. This ADR does NOT prejudge that selection; it binds the GUARD's existence and default-on posture.

**Mechanism (b) ESCAPE VALVE — Caller Opt-In, Default OFF:**

- The Phase 2 ExportRequest contract MUST admit `options.predicate_join_semantics` with values `{"preserve-outer", "allow-inner-rewrite"}`.
- Default value: `"preserve-outer"` (fail-loud — mechanism (a) is active).
- When the caller explicitly sets `"allow-inner-rewrite"`, mechanism (a)'s assertion is DISABLED for that request; the engine emits a structured warning in the response meta indicating the override was applied.

### 4.2 Phase 1 Carry-Forward (TDD §3.2 binding)

Phase 1 contract leaves room for the future `predicate_join_semantics` field via `ExportOptions.model_config = ConfigDict(extra="allow")` (TDD §3.2; satisfies spike handoff §6 P1-C-02 at L533-549). Phase 1 does NOT populate the field; Phase 2 architect adds it as a typed member when the boundary_predicate dispatch ships.

## §5 Rationale

### 5.1 Why (a) Alone Is Insufficient

Mechanism (a) is the engine's structural defense, but there exist legitimate caller use cases where INNER semantics ARE the desired behavior — e.g., a downstream BI consumer that intentionally wants the inner join because they will perform NULL-row analysis separately. Without (b), such callers must either (1) issue a separate request with `how="inner"` directly (loses the predicate-pushdown optimization the C5 path delivers under LEFT) OR (2) accept the engine's `LeftJoinRewrittenError` and work around it. Both options are friction the escape valve eliminates.

### 5.2 Why (b) Alone Is Insufficient

Mechanism (b) places the burden of correctness on the caller. The default would be `"preserve-outer"`, which is correct, but in the absence of (a) the engine has NO structural enforcement. A caller who omits `predicate_join_semantics` (relying on the default) and a future contract change that flips the default to `"allow-inner-rewrite"` (or a serialization bug that drops the field) would silently degrade the caller's results. This is the F-HYG-CF-A failure pattern at one remove (silent denominator shift via default-drift). Mechanism (a) closes that class of failure structurally.

### 5.3 Why HYBRID Is Correct

(a) provides STRUCTURAL fail-loud enforcement: the engine cannot silently deliver INNER results when LEFT was requested. The mechanism is at the load-bearing seam (engine post-EXPLAIN, before .collect()) where every C5-PATH LEFT request flows through.

(b) provides EXPLICIT caller-side override: when the caller has corroborating context that INNER semantics are acceptable, they signal it by setting `"allow-inner-rewrite"`. The override is observable in request logs (URL or body parameter, not a hidden default).

The hybrid satisfies the fail-loud-vs-fail-silent discipline (spike handoff §3:238-247, citing F-HYG-CF-A precedent at RETROSPECTIVE-VD3-2026-04-18.md:145): the silent failure mode (LEFT→INNER rewrite) is structurally precluded by (a); the loud failure mode (`LeftJoinRewrittenError` or response-meta warning) surfaces both engine-side enforcement and caller-side override events to operators.

### 5.4 Empirical Evidence (Spike Trail)

- S3 PROTO §5 LL.230-247 (cited at spike handoff §8 evidence row 4): verbatim `.explain()` output showing INNER JOIN header replaces LEFT JOIN under equality predicate on join-target column.
- S3 PROTO §5 LL.250-262 (cited at spike handoff §8 evidence row 5): IS_NULL predicate preserves LEFT JOIN — confirms the rewrite is operator-class-conditional, supporting (a)'s post-EXPLAIN assertion as the correct triage point.
- S4 MOONSHOT §4 Claim 2 (cited at spike handoff §8 evidence row 4 + §3:198-200): elevated the S3 framing from "semantic contract change" to "wrong-result silent failure equivalent to B-R1" — DIVERGE resolved in this ADR by adopting (a) as the structural answer.

## §6 Consequences

### 6.1 Phase 2 Architecture Commitments

Phase 2 boundary_predicate dispatch (spike handoff §3:157-184) MUST accommodate this mechanism:

- The C5-PATH branch (spike handoff §3:166-171) gains a post-EXPLAIN guard step inserted between predicate-tree compile and `.collect()`. Spike handoff §4 phase_2_boundary at L287-293 already names this surface ("NEW: post-EXPLAIN guard module ... Phase 2 architect decides module shape") — this ADR's mechanism (a) is the body of that module.
- The PATH-B branch (spike handoff §3:173-178) is out of scope for this ADR — different mechanism class (cross-service); separate ADR if surfaced.
- The ExportRequest contract gains an OPTIONAL `options.predicate_join_semantics` field. Phase 1 reserves the slot via `extra="allow"` per TDD §3.2; Phase 2 promotes it to a typed `Literal["preserve-outer", "allow-inner-rewrite"]` field with default `"preserve-outer"`.

### 6.2 ENGINE-DESIGN-Q1 Discharge

This ADR is the EC-04 discharge artifact (spike handoff §9 entry condition at L831-839 verbatim):

> Sprint 2 ADR MUST explicitly acknowledge the s3_s4_divergence_resolution mechanism (§3) as a Phase 2 design requirement. ADR MAY defer mechanism-(a)-vs-(b) selection to Phase 2, BUT MUST NOT silently omit the constraint. ENGINE-DESIGN-Q1 MUST appear in the ADR's "Phase 2 forward-binding constraints" section.

ENGINE-DESIGN-Q1 is hereby recorded as a Phase 2 forward-binding constraint per §4 of this ADR. This ADR does NOT defer the mechanism-(a)-vs-(b) selection — it makes the binding HYBRID decision now.

### 6.3 Performance Implications (Phase 2 PROTO scope)

Mechanism (a) adds an `.explain()` call + plan parse on every C5-PATH LEFT request. Polars `.explain()` is documented as cheap (no data materialization; see spike handoff §8 evidence row 21 citing docs.pola.rs/user-guide/lazy/optimizations/), but the plan-parse step is new code and warrants benchmark measurement at Phase 2 PROTO altitude. Sub-option (ii) (anti-join restoration) is materially more expensive than sub-option (i) (raise LeftJoinRewrittenError). The Phase 2 PROTO MUST measure both and the Phase 2 implementation ADR selects.

### 6.4 Caller-Visible Surface

Mechanism (b) is caller-observable (a request field). Mechanism (a) is engine-internal except when sub-option (i) raises `LeftJoinRewrittenError` or sub-option (ii) emits the response-meta warning. Documentation MUST surface both behaviors to API consumers; the Phase 2 contract README + OpenAPI schema MUST describe the field semantics.

### 6.5 Reversibility

The Phase 2 boundary_predicate dispatch (and therefore this guard's invocation site) is reversible per spike handoff §3:273-282 + evidence row 18 (C5 reversibility highest, single-line revert weak form). If the guard's performance impact is unacceptable, sub-option (i) (raise) is more reversible than sub-option (ii) (anti-join restoration). This ADR does not foreclose reversal.

## §7 Alternatives Considered

### 7.1 Mechanism (a) Alone (REJECTED)

Engine-side post-EXPLAIN assertion with NO caller opt-in. Forces all callers to either accept LEFT semantics or issue a separate `how="inner"` request (losing the C5 predicate-pushdown optimization for the explicit-INNER case). Rejected per §5.1: legitimate INNER-want callers exist; no escape valve creates friction.

### 7.2 Mechanism (b) Alone (REJECTED)

Caller-opt-in field with no engine-side enforcement. Default `"preserve-outer"` is correct, but the engine has no structural defense against default-drift, serialization bugs, or callers who omit the field unintentionally. Rejected per §5.2: the F-HYG-CF-A failure pattern (silent denominator shift) re-emerges at one remove (default-drift). Structural enforcement at the engine seam (mechanism (a)) is required.

### 7.3 Mechanism (c) DOCUMENTATION-ONLY (REJECTED — F-HYG-CF-A precedent)

The spike handoff at §3:221-225 (verbatim):

> **DOCUMENTATION-ONLY (REJECTED as sole defense)**: the platform has burned on the F-HYG-CF-A "documentation without mechanism" pattern (RETROSPECTIVE-VD3-2026-04-18.md:145). Documentation alone is INSUFFICIENT per telos-integrity-ref §3 Gate B precedent.

This ADR concurs with the spike's rejection. Documentation describing the LEFT→INNER rewrite as a known caller-managed concern, with no engine-side or contract-side mechanism, has the form of the Vanguard "wave-level CLOSED" anti-pattern: a claim authored at one altitude that downstream consumers cannot mechanically verify. Per F-HYG-CF-A canonical at RETROSPECTIVE-VD3-2026-04-18.md:145 (cited at spike handoff §8 evidence row 23 + telos-integrity-ref §3 Gate-B), receipt-grammar discipline requires per-item enforcement (here: per-request engine-side assertion). Documentation-only is FORMALLY REJECTED as sole defense.

### 7.4 Defer the Decision to Phase 2 (REJECTED)

Spike handoff §9 EC-04 at L831-839 admits this option ("ADR MAY defer mechanism-(a)-vs-(b) selection to Phase 2") with the caveat "BUT MUST NOT silently omit the constraint." Deferring would satisfy the literal entry condition but would defer a load-bearing design decision past the architect-attestation altitude (Sprint 2). The Phase 2 architect would inherit the decision without the Sprint 2 architect's rite-disjoint critic perspective on the Phase 1 contract surface. REJECTED in favor of a binding HYBRID decision now (§4); the Phase 2 architect retains decision authority on the SUB-OPTION (i) vs (ii) selection within mechanism (a) per §4.1.

## §8 Compliance — EC-04 Satisfaction

This ADR satisfies spike handoff §9 entry condition EC-04 (L831-839 verbatim):

| EC-04 requirement | This ADR's satisfaction |
|---|---|
| "Sprint 2 ADR MUST explicitly acknowledge the s3_s4_divergence_resolution mechanism (§3) as a Phase 2 design requirement." | §3.2 quotes verbatim; §4 binds the mechanism. |
| "ADR MAY defer mechanism-(a)-vs-(b) selection to Phase 2, BUT MUST NOT silently omit the constraint." | §4 makes the HYBRID binding decision; selection NOT deferred. |
| "ENGINE-DESIGN-Q1 MUST appear in the ADR's 'Phase 2 forward-binding constraints' section." | §6.1 + §6.2 enumerate Phase 2 forward-binding consequences and explicitly discharge ENGINE-DESIGN-Q1. |

Phase 1 contract (TDD §3.2 ExportOptions with `extra="allow"`) preserves the option-enumeration-discipline: future addition of `predicate_join_semantics` is non-breaking per spike handoff §6 P1-C-02 (L533-549).

## §9 Citations

- Spike handoff §3 verdict: `.ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md:111`
- Spike handoff §3 critic_substitution_chain: `.ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md:194-237`
- Spike handoff §3 ENGINE-DESIGN-Q1 escalation: `.ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md:227-237`
- Spike handoff §6 P1-C-02 contract reservation: `.ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md:533-549`
- Spike handoff §9 EC-04 entry condition: `.ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md:831-839`
- Spike handoff §4 phase_2_boundary post-EXPLAIN guard module: `.ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md:287-293`
- Spike handoff §8 evidence trail rows 4, 5, 21, 23 (Polars EXPLAIN empirical + F-HYG-CF-A precedent)
- F-HYG-CF-A canonical: `RETROSPECTIVE-VD3-2026-04-18.md:145` (per spike handoff evidence row 23)
- Companion TDD: `.ledge/specs/TDD-pipeline-export-phase1.md` §10

End of ADR. Zero pending markers. EC-04 discharge complete.
