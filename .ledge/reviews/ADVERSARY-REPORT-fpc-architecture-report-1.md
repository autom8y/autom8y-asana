---
type: adversary-report
subtype: arch-adversary-challenge
target_handoff: ".ledge/reviews/fpc-architecture-report-2026-06-09.md"
target_handoff_sha: "blob-sha1:3c845526838d293461cf8bd8477888f9240a0976"
challenger_agent: arch-adversary
initiative: "fpc-architecture-mapping"
date: "2026-06-09"
iter: 1
verdict: PASS-WITH-CONDITIONS
adversary_disposition: CONCUR-WITH-FLAGS
tl_a_status: PASS
tl_b_status: CHALLENGE
tl_c_status: PASS
delta_scope_attested: false
challenges_raised:
  - id: CH-01
    taxonomy_id: AC-02
    tl_clause: B
    severity: BLOCKING
    target_element: "assessment §0/§1/§2-AP-4:191/§4.4; report §3.4 inherits"
    rationale: "Load-bearing negative recovery grep claimed EMPTY is FALSE at origin/main (6 hits in dataframes/storage.py)."
    falsification_pathway: "Re-paste grep scoped to number-cell recovery (exclude CB recovery_timeout); if genuinely empty, keystone holds."
    remediation_hint: "assessment §0 + §2 AP-4 :191 — corrected pathspec + corrected live output."
  - id: CH-02
    taxonomy_id: AC-05
    tl_clause: A
    severity: FLAG
    target_element: "report §10 + §4 Phase exit criteria"
    rationale: "Phase-1 exits read as completion gates; only Phase-2 coherent>=100 is a true falsifiable prediction. FLAG at MAPPED rung."
    falsification_pathway: "On HANDOFF promotion, lift Phase-2 coherent>=100 into a structured prediction (expiry <=180d)."
    remediation_hint: "Add predictions:[] entry for Phase-2 coherent-count on HANDOFF promotion."
arch_ref_citations:
  - "AQ:SRC-004"
  - "AQ:SRC-008"
  - "AV:SRC-001"
  - "DP:SRC-005"
---

# ADVERSARY-REPORT — FPC Architecture Report (iter 1)

## 1. Challenge Summary

**VERDICT: PASS-WITH-CONDITIONS** (adversary_disposition: CONCUR-WITH-FLAGS).

This is a substantively grounded, rung-disciplined MAPPED+ranked analysis whose
headline G-THEATER canary I independently reproduced RED. It clears TL-A and TL-C.
One BLOCKING-grade TL-B receipt falsification holds it short of clean PASS.

- **CH-01 (AC-02 / TL-B / BLOCKING)**: the keystone NEGATIVE recovery grep, pasted as
  returning EMPTY, returns 6 hits at origin/main when its exact pathspec is re-run.
  G-PROVE breach on a load-bearing receipt.
- **CH-02 (AC-05 / TL-A / FLAG)**: Phase-1 exit criteria read as completion gates, not
  falsifiable predictions; FLAG-only because the artifact sits at MAPPED rung and ships
  no \`predictions:[]\` ledger. The Phase-2 \`coherent>=100\` claim is a genuine prediction
  and is the report's TL-A strength.

Iteration: 1 (CHALLENGED-1). No handoff-ledger and no prior ADVERSARY-REPORT for this
slug exist; delta_scope_attested: false (correct for iter=1).

## 2. TL-A Analysis — Falsifiable Prediction / RED Demo

**Status: PASS.** The G-THEATER demo is REAL, not asserted. I re-ran the report's
exact §3.2 SQL against the live parquet (\`/tmp/u8o\`, \`/tmp/u8u\`) and reproduced the
pasted output bit-for-bit:

| metric | report claim (§3.2) | adversary re-run | match |
|---|---|---|---|
| total_joined | 2001 | 2001 | YES |
| gun | 571 | 571 | YES |
| coherent | 0 | 0 | YES |
| unit.mrr nonnull/total | 0/3021 | 0/3021 | YES |
| offer.mrr nonnull/total | 1325/4070 | 1325/4070 | YES |

The proposed coherence invariant fires maximally RED on the 571-gun. The GRANDEUR
ANCHOR's G-THEATER proof condition — "the coherence invariant MUST fire RED against
the known 571-unit divergence" — is satisfied with an independently-verified live
receipt, not a diagram. The §3.3 GREEN demo (synthetic coherent pair → gun=0,
coherent_pass=1) correctly demonstrates the invariant distinguishes coherent from
incoherent pairs; this is the construct-validity discriminant per [AV:SRC-001
Messick 1989] [MODERATE] (the instrument measures what it claims — coherence, not
mere presence).

The report's strongest falsifiable forward claim is the Phase-2 exit: "coherent moves
from 0 to >= 100 phones" with the explicit instruction "Re-run the canary after deploy."
That IS disposition-forcing and observable. It is the load-bearing TL-A element and it
holds. (Its packaging is FLAGged under CH-02 — see §3/§5.)

No AC-05 conflation drives a BLOCK here: at MAPPED rung the artifact is analysis, not a
predictions-ledger HANDOFF, so completion-gate language is tolerated as FLAG.

## 3. TL-B Analysis — Citation / Receipt Resolution

**Status: CHALLENGE (one BLOCKING falsification; all other sampled receipts hold).**

Sample-verified 10 receipts against origin/main (HEAD \`50ebfe33...\`, which I confirmed
matches the report's declared \`head:\` — G-PREMISE check passed, the local tree is the
stale cr3/gate2 branch but I read origin/main):

| # | receipt | claim | origin/main verify | verdict |
|---|---|---|---|---|
| R1 | path correction §1 | \`core/entity_registry.py\` not \`dataframes/...\` | \`core/...\` exists; no \`dataframes/entity_registry.py\` | HOLDS |
| R2 | \`post_build_population_receipt.py:60-61\` | \`_VALUE_COLUMNS_BY_ENTITY={"offer":("mrr","offer_id")}\` | exact match | HOLDS |
| R3 | \`cf_utils.py:46-50\` | \`case "number": return cf_data.get("number_value")\` | exact match | HOLDS |
| R4 | negative recovery grep → EMPTY | "zero recovery path" keystone | **6 hits in storage.py** | **FALSIFIED (CH-01)** |
| R5 | \`asset_edit.py:147-151\` D3 | schema dtype Float64, cf:Score | exact match | HOLDS |
| R6 | opt_fields symmetry | LIST \`fields.py:69\` == GET \`hierarchy_warmer.py:43\` both number_value | both present | HOLDS |
| D1 | \`unit.py:38-41\` vs \`models/.../unit.py:118\` | Decimal schema vs EnumField model | exact match | HOLDS |
| D2 | \`offer.py:70-73\` vs \`models/.../offer.py:136\` | Utf8 schema vs NumberField model | exact match | HOLDS |
| HEAD | frontmatter \`head:\` | \`50ebfe33...\` | == \`git rev-parse origin/main\` | HOLDS |

**CH-01 detail (BLOCKING).** Both the assessment (§0 "No null-recovery backstop ...
→ EMPTY"; §1 keystone "the lattice has zero recovery path for a list-path number
drop"; §2 AP-4 negative receipt :191; §4.4) and the report (§3.4 root-cause inheritance)
rest on:

\`\`\`
git grep -E 'recover|repair_null|refetch_via_get|number.*fallback' origin/main -- 'src/autom8_asana/dataframes/**'  ->  EMPTY
\`\`\`

Re-run of the **exact pasted pathspec** at origin/main returns 6 hits:
\`\`\`
src/autom8_asana/dataframes/storage.py:284:  recovery_timeout=60.0,
storage.py:313,546,547,614,615:  circuit-breaker recovery / HALF_OPEN recovery prose
\`\`\`

The hits are circuit-breaker recovery, NOT number-cell null-recovery — so the analytic
CONCLUSION (no GET-path backstop for a list-path number drop) is plausibly still correct.
But the receipt AS PASTED is false: it claims EMPTY and is not. Per G-PROVE, a pasted-but-
false receipt anchoring a keystone judgment ("zero recovery path") is a structural defect
in the falsification chain — it is the cumulative-anti-pattern class [AQ:SRC-004 Mo et al.
2019] [STRONG] applied to the report's own provenance. This is the single condition that
holds the artifact at PASS-WITH-CONDITIONS rather than PASS.

All other load-bearing receipts — including the matrix cells driving the leverage
rankings (D1/D2/D3 drift, R2 floor dict, R6 opt_fields symmetry) — verify exactly.
TL-B is one corrected grep away from clean.

## 4. TL-C Analysis — Adversarial Disposition / Rung Discipline

**Status: PASS.** No round-up; all G-gates honored.

- **G-RUNG (MAPPED, not designed/built)**: HONORED. Frontmatter \`rung: MAPPED+ranked\`;
  banner "does NOT claim designed/built/live/verified-realized. No src/ edits. No
  consumer rebinds. No fixes land here." The FieldContract dataclass in §4 Phase 3 is
  explicitly framed as "north-star spec" and routed to CRR-001 as "a feature build, not
  a refactor ... full sprint of 10x-dev work" — i.e. NOT built here. No rung round-up
  detected.
- **G-PROPAGATE (shared FPC, no orphans)**: HONORED. §4 Phase 2 "the recovery must be
  wired through a single shared contract point — not per-field orphan patches"; §4 Phase
  3 "G-PROPAGATE compliance: the FPC shared contract IS the sole propagation point. There
  are no per-field orphan patches." The single-FieldContract-derives-all design is the
  correct propagation discipline [DP:SRC-005 Evans 2003] [MODERATE] (single
  source-of-truth / anti-corruption between schema and model layers).
- **G-DENOM (per-field policy, no blanket null-fill)**: HONORED. §2 AP-3, §4 Phase 1
  action 5, and §5 Population-types all bind each cell to \`ActiveSubset / Total /
  LegitimatelySparse\` — explicitly "not blanket null-fill" and "not Total (which would
  fire on legitimately sparse entities)." The offer.mrr 62/\$79,485 active-subset anchor
  is carried as the denominator. Correct G-DENOM posture.
- **Held-as-DEFER (not pulled into scope)**: CORRECT.
  - unit-MRR cure (the cell-0 fix) is held to **Phase 2**, gated on UK-4 + CR-3 soak —
    NOT pulled into the MAPPED analysis. Good.
  - SEAM-2 / monolith consumers correctly routed to **CRR-002** as cross-repo discovery
    ("no in-repo manifest"), LOW-confidence inferred edges — not asserted as in-scope fact.
  - Live-probe / runtime-under-load explicitly OUT-OF-SCOPE (§8): "latency, throughput,
    failure modes ... not load-tested here." Correct boundary.
- **Generated-verification fitness function**: the parity test (§4 Phase 1 action 4) is
  cited [AQ:SRC-008 Ford et al. 2017] [MODERATE] as an evolutionary-architecture fitness
  function — appropriate grounding; it is proposed (MAPPED), not built.

No finding is silently dropped: §10 disposition checklist dispositions every AP-1..AP-5,
FM-1..FM-4, UK-1..UK-5, and both boundary leaks. G-PROPAGATE's "no orphan" discipline is
mirrored in the report's own "no finding orphaned" close.

## 5. Remediation Pathway (PASS-WITH-CONDITIONS)

Ordered, each pointing to the section that must change. Supplying these revises the
verdict to PASS:

1. **[BLOCKING — CH-01] Correct the negative recovery grep receipt.** In the assessment
   §0 ("Receipts I re-ran live") and §2 AP-4 (:191), the pasted grep
   \`'src/autom8_asana/dataframes/**' → EMPTY\` is false (6 \`storage.py\` CB-recovery hits).
   Re-paste a grep scoped to number-cell recovery — e.g. exclude \`storage.py\` or tighten
   the pattern to \`repair_null|refetch_via_get|number_value.*(recover|refetch|fallback)\`
   — with the corrected live output. If the tightened grep is genuinely EMPTY, the "zero
   recovery path for a list-path number drop" keystone (assessment §1; report §3.4) stands
   and CH-01 clears. If it is non-empty, the keystone judgment must be revised before the
   report ships as a HANDOFF.
2. **[FLAG — CH-02] On HANDOFF promotion only:** lift the Phase-2 \`coherent>=100\` claim
   (report §4 Phase 2 "N>=2 throughline-promotion trigger") into a structured prediction
   with \`falsification_condition: "post-Phase-2-deploy office_phone canary still shows
   coherent=0"\` and \`expiry <=180d\`. At MAPPED rung this is documented-risk only; it does
   not block.

CH-02 is non-blocking; CH-01 is the sole gating condition.

## 6. Falsification of This Report

What concrete observation revises THIS verdict (anti-dogma; adversary-epistemic-integrity
applies recursively):

- **Revises CH-01 to clear (→ PASS)**: a re-run of the corrected, number-scoped recovery
  grep at origin/main returning genuinely EMPTY. I challenged the receipt's *fidelity*
  (it claimed EMPTY and was not), not the *conclusion*. If the author demonstrates the
  conclusion survives a correctly-scoped grep, CH-01 dissolves and the verdict is PASS.
- **Would escalate CH-01 to full BLOCK**: if the corrected grep returns number-cell
  recovery hits — i.e. a list-path number-recovery backstop DOES exist in \`dataframes/\`
  — then the entire AP-1/AP-4 keystone ("zero recovery path") is falsified and the
  recommendation chain (Phase 2 "the fix that moves coherent from 0 to non-zero") rests
  on a false premise. I did not find such a backstop in my sampling, so I did not BLOCK;
  a rite-disjoint grader who finds one would be entitled to.
- **Revises TL-A**: if a third party re-runs the §3.2 canary against the same parquet and
  gets gun≠571, my PASS on TL-A is falsified. I reproduced 571/2001/0 exactly, so this
  observation is currently the strongest pillar.
- **Self-citation discipline**: this report cites AQ:SRC-004, AQ:SRC-008, AV:SRC-001,
  DP:SRC-005 (resolved in arch-ref INDEX) for its challenge framing — the adversary is
  subject to TL-B. Per self-ref-evidence-grade-rule my own grades cap at MODERATE absent
  a rite-disjoint second grader; the canary re-run is the externally-reproducible anchor
  that a second grader can independently falsify.
