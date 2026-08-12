---
type: review
artifact_type: DEFECT
status: proposed
initiative: substrate-v2-epoch (adjacent finding — metrics layer, routed separately)
date: 2026-08-12
discovered_by: architect adjudication (ADJUDICATION-floor-locus-endstate-2026-08-12.md, probed); independently REPRODUCED by arch-adversary (ADVERSARY-floor-locus-adjudication-2026-08-12.md T7)
severity: HIGH (6 of 9 registered metrics unservable), contained (none of the 6 is currently consumer-wired to a serving path known to this arc)
---

# DEFECT — six of nine registered metrics raise ColumnNotFoundError through compute_metric

**Reproduction (twice-probed, offline fixture):** every `lifecycle.py` metric whose
`filter_expr` roots fall outside the Step-1 column-select set fails structurally —
`compute_metric` selects columns FIRST (compute.py:83-97, scope-derived set), then
applies `filter_expr`, so any filter referencing a column not in the select set raises
`ColumnNotFoundError` **even on a frame carrying every column**. 9 registered → 3
survive (active_mrr among them) → 6 raise.

**Class:** structural select-before-filter ordering, not data-dependent. The fix space
(not decided here): widen the select set by `filter_expr.meta.root_names()` (the
adjudication verified `pl.Expr.meta.root_names()` yields a total consumed-column
derivation today, no schema change) — which is ALSO the same derivation the H1
endstate needs, so the fix and the endstate share machinery.

**Route:** separate corridor unit, NOT mid-window scope. Candidate owner: the endstate
DELTA (post-window) since the derivation machinery is shared; or an independent small
fix if any of the 6 metrics is needed sooner. Rides the daily digest; PT-03-relevant
only as context (active_mrr is unaffected — verified serving today).
