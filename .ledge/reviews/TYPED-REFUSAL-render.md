---
type: review
status: accepted
---

# TYPED-REFUSAL-render — Sprint 3 exit artifact (provenance-to-the-human)

- **Initiative**: provenance-to-the-human (frame `.sos/wip/frames/provenance-to-the-human.md` §2 predicate, refusal clause; shape sprint-3)
- **Branch/PR**: `prov/s3-typed-refusal` → autom8y-asana PR #228 (base `08d9800d`)
- **Commits**: guard `c295a99b` (integrity-guard-author) · teeth `c0cafe25` (numerical-adversary, rite-disjoint) · this receipt (orchestrator compilation — cites, does not re-derive)
- **Self-cap**: MODERATE (self-ref rule; the initiative-level verified-realized attest is eunomia's alone at sprint-6 — NOT claimed here)

## Realization predicate (refusal clause, VERBATIM scope)

> a failed/degenerate compute renders a TYPED "denied" refusal distinguishable
> from "no-data" empty; AND a deliberately provenance-stripped or silent-empty
> input is CAUGHT by a two-sided fixture AT THE RENDER SURFACE (RED without
> the disclosure, GREEN with). NOT "the field is emitted by the data layer" /
> "PRs merged".

## The defect (live at parent `08d9800d` — genuine gap, not injected)

`OperatorAccessDeniedError` in `_prefetch_operator_tables` → comment "leave this
table empty and continue" → `continue` → key ABSENT from `_operator_batch` →
`_fetch_table`'s `.get(table,{}).get(office,[])` coerced absence to `[]` →
`TableResult(success=True, data=[])` → rendered EMPTY. The broad-catch arm rode
the same path. Denied / errored / no-data were indistinguishable on the
published deck (C2 drift; frame R7 / SVR-8).

## The guard (G4, adopts R8 — commit `c295a99b`)

- `_OperatorTableDenial` frozen dataclass, `kind: Literal["denied"]`
  discriminant — the admin-ui `ApiResult` `ok:false` grammar analogue
  (autom8y-admin-ui `types.ts:73-74`), adopted not invented.
  `workflow.py:90-125`; union type widened `:181-183`.
- Write path: BOTH catch arms now WRITE the marker into
  `self._operator_batch[spec.table_name]` (`_prefetch_operator_tables:799,819`)
  — a present value, not an absence; the daily run still never aborts.
- **Fire-seam** (named for the disjoint adversary): `_fetch_table:938` —
  `if isinstance(entry, _OperatorTableDenial):` ORDERED BEFORE the
  `.get(office_phone, [])` empty-coercion → `TableResult(success=False,
  error_type=…, error_message=…)` → formatter error channel
  (`formatter.py:298-308` dispatch → `_render_error_section:684-687`
  `error-box`) — vs `_render_empty_section:679-682` `<p class="empty">`.
- `formatter.py` render kernel NOT edited (the channel pre-existed; the denied
  path now reaches it). `composite.py` guarded seam NOT touched.

## Two-sided teeth AT THE RENDER (commit `c0cafe25`, rite-disjoint adversary)

Fixture `tests/unit/automation/workflows/test_insights_denied_render_teeth.py`
drives the REAL path (write-arm → fire-seam → `compose_report`) and asserts on
the CONSUMED composed HTML. RED-before proven at parent `08d9800d` via a
throwaway worktree with a TEST-ONLY overlay (production diff EMPTY — verified;
discriminating-canary doctrine, no defect injection). Matrix:

| Arm | parent `08d9800d` | guard `c295a99b`+teeth |
|---|---|---|
| denied → typed error-box, not empty | **FAIL (RED-caught)** — rendered empty | PASS (GREEN) |
| genuinely-empty → empty, not error-box | PASS | PASS |
| denied vs empty structurally distinct | **FAIL (RED-caught)** — collapsed to 'empty' | PASS (GREEN) |
| non-vacuity: no denial → zero error-boxes | PASS | PASS |
| denial does not leak to other tables | **FAIL (RED-caught)** | PASS (GREEN) |
| broad-catch (RuntimeError) → typed marker | **FAIL (RED-caught)** | PASS (GREEN) |
| all-denied → no-op (prior deck protected) | **FAIL (RED-caught)** — all-empty deck overwrote prior good deck | PASS (GREEN) |

Parent run: 5 failed / 2 passed. Guard run: 7 passed. Non-vacuity + sole
discriminator (`error-box` vs `<p class="empty">`) proven; cheap signals
(row_count, file-exists, valid-HTML, upload-success) proven BLIND — identical
on correct and corrupt. Verdict: **TEETH-PROVEN** (adversary, self-cap
MODERATE).

## Defects closed (filed, not silently passed)

- **DEF-1** (load-bearing): denied null-coerced to empty render at the point of action.
- **DEF-2**: broad-catch unexpected errors rendered empty the same way.
- **DEF-3**: all-tables-denied published an all-empty deck OVER a prior good
  deck (silent-wrong-outcome class); now `tables_succeeded==0` no-op guard
  fires (denials count as failed).

## PT-03 disposition

1. Denied path routes through the formatter error channel instead of
   publishing empty — YES (fire-seam → `success=False` → `:298-308`).
2. Marker typed, discriminated, non-null-coercible (G4, adopts R8) — YES.
3. Two-sided teeth at the render, denied/empty structurally + visually
   distinct, green-after-alone rejected — YES (matrix above; RED on the real
   parent defect).

**PT-03: PASS** at MODERATE self-cap. The eunomia sprint-6 attester re-derives
with its OWN construction; this artifact hands it the fire-seam + fixture
locations and inherits it nothing.

## Receipts

- `uv run pytest tests/unit/automation/workflows/ -p no:xdist` → 884 passed, 8 skipped
- formatter + lambda export suites → 260 passed · `mypy src/ --strict` clean · ruff clean
- PR #228 CI: full matrix green (22 pass; Convention/Integration skips are the repo's standard skip-state)
- CD-path: asana push-to-main triggers CI/coverage/scan only — the merge
  activates NO consumer surface; the deck render flips only at the separate
  operator-gated deploy (C5/OP-5).
