---
type: decision
status: accepted
artifact_id: RULING-operator-adr007-ratification-2026-08-12
initiative: option4-verification-axis-gate
session: session-20260811-115247-a1ccd942
date: 2026-08-12
conducted: "2026-08-12 ~11:50-12:05Z, two AskUserQuestion batches (7 decisions), per the operator's inscribed interview protocol"
subject: ADR-007-verification-axis-gate-2026-08-12.md — the two signature blocks + the architect's four flagged items + one altitude question created by ruling R-i
binding_note: "Nothing not explicitly ruled here may be recorded as decided."
---

# OPERATOR RATIFICATION DIGEST — ADR-007 sitting

## Rulings (7)

| # | Item | Ruling | Content |
|---|---|---|---|
| R-i | §1.2 amendment text (signature item i) | **AMENDED-RATIFIED** | Text ratified as drafted EXCEPT the VERIFICATION GRAIN clause is **softened binding → advisory**. The MONOTONICITY clause and the non-aliasing extension ratify as written. P-5 ("all classified sections") remains the OPERATIVE RULING; the advisory clause spares contract-fence ceremony only — it does not open the denominator (see R-alt). |
| R-ii | V = 14,400s / abort 28,800s (signature item ii) | **RATIFIED-PROVISIONAL** | Numbers go live marked PROVISIONAL with both evidence riders attached. **Auto-confirm or auto-reopen at the 14-day soak's close** (the stage-2 evidence event) — no separate sitting needed; the soak verdict executes the disposition. |
| R-alt | Denominator change process (created by R-i's softening) | **RATIFIED** | "Escalate only at the wall": the build MUST attempt all-classified first; only a demonstrated impossibility WITH RECEIPTS may return to the operator; no pre-emptive narrowing. |
| R-O3 | `backfill_used` vs `verification_backfill_used` spelling | **DELEGATED-WITH-INSCRIPTION** | The architect decides at the producer-leg PR. MANDATORY: the choice is inscribed in that PR's body AND the naming fence is amended in the same PR — the delegation is loud, never silent. |
| R-O14 | Citation framing for the 28,800s justification | **REFUSED-AS-POSED** | "Wrong question" — the justification prose does not bind future citations. The number stands per R-ii; ADR §4.1's horizon-alignment derivation remains the ADR's own argument, unconstrained. |
| R-O4 | Metrics CLI expression of "unprovable" | **DELEGATED** | Settled inside the CLI leg against ADR-001's retained exit-code matrix, disclosed in that leg's PR. |
| R-O8 | Classifier-vocabulary drift presentation | **HOLD** | Revisit trigger: **K-0a census result** (do all 27 classified names resolve today). Until then the drafted strict rule stands as draft text, unratified. |

## Recommendation divergences (stated once at the sitting, not re-argued)
- R-i: recommendation was binding grain; operator softened.
- R-O3: recommendation was the one-word `verification_backfill_used` confirmation; operator delegated (with the inscription mitigation).
- R-O14: recommendation was horizon-alignment-canonical; operator declined to constrain citations.
- R-O8: recommendation was refuse+named-disclosure now; operator held for the census.
Aligned: R-ii, R-alt, R-O4.

## Explicitly deferred
- R-O8 (trigger: K-0a). · V's absolute confirmation (trigger: soak close, automatic per R-ii).

## Assumptions remaining UNCONFIRMED
1. The 14-day soak's design (grid, pass criteria beyond the registered P-9 kill-switch bar) is drafted in the build plan, not yet ratified.
2. The interpretive layering of R-i (P-5 operative / advisory = ceremony relief) was pinned via R-alt's stem assumption being accepted; recorded as confirmed-by-construction.

## Consequence for ADR-007
Both RATIFICATION-PENDING blocks flip to their outcomes above; a RATIFICATION RECORD
section pointing here is appended to the ADR. The ADR body text is otherwise
untouched — this file is the binding record.
