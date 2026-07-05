---
type: handoff
artifact_subtype: review-to-operator
initiative: asana-readiness-hygiene
handoff_type: validation
from_rite: review
to: operator (merge-readiness) + follow-on framing
from_station: case-reporter (rite-disjoint critic)
created: 2026-07-01
status: proposed
promise_axis: evidence-grade
cleanup_surface: STRONG (evidence-grade axis, single rite-disjoint mechanical re-fire)
realization: audit-verified / pre-merge (merged + drift-guarded-over-time UNATTESTED)
reconcile_telos: "EXIT 0 — SeamRungCeiling=proven ≤ LicensedCeiling=merged; verified_realized UNATTESTED (untouched)"
verdict: .ledge/reviews/asana-readiness-hygiene-review-disjoint-verdict.md
target_branch: "hygiene/asana-readiness @ 3e5bb3e7 (LOCAL/unpushed; 19 commits off cb4b4201)"
---

# HANDOFF: review → operator — asana-readiness-hygiene (merge-readiness, 2026-07-01)

> **Who reads this**: the operator (merge-decision) + any follow-on `/frame`.
> **Boundary**: the review rite has BANKED **cleanup-surface STRONG (evidence-grade axis, single
> rite-disjoint mechanical re-fire)** — verdict in `.ledge/reviews/asana-readiness-hygiene-review-disjoint-verdict.md`.
> Realization stays **audit-verified / pre-merge**; `merged` + `drift-guarded-over-time` are
> **UNATTESTED** (branch LOCAL). All production levers are the operator's. Reading cleanup-surface
> STRONG as merged/realized = axis-mismatch.

## §1 · What the review BANKED (evidence-grade axis)

The rite-disjoint critic re-derived every proof from code+tooling (never re-reading the in-rite audit):
- **36/36** dead-`noqa` removals — each re-injected → `ruff --extend-select RUF100` RED at its `{path}:{line}` → revert → GREEN (the critic's OWN two-sided receipts). [verdict §Evidence-Matrix]
- **Drift-guard teeth** — a fresh dead `# noqa: F401` on the live `api/main.py:49` import → RUF100 RED + gate fails → revert → GREEN. [verdict, teeth row]
- **KEEP-floor** — `idempotency.py` zero-diff + a **two-sided exemption proof** (remove R1 → `:770` RED → restore → GREEN). [verdict, KEEP-floor rows]
- **Deterministic surface** — 4/4 GREEN (`ruff format --check` 1199 · `ruff check` · `ruff check src/ --extend-select RUF100` · `mypy src/ --strict` 535). [verdict, surface rows]
- **Health A** across all 5 categories; 0 Crit/High/Med; **G-DENOM = 50 evidence items**.
- `reconcile-telos` EXIT 0 at the pre-merge ceiling (`proven ≤ merged`; verified_realized UNATTESTED, untouched).

## §2 · Merge-readiness → OPERATOR (the sole gate is D2)

The cleanup is review-attested and merge-ready **once D2 is ratified**. Operator levers (surfaced, NOT executed):
- **D2 — the sole merge gate** `[OPEN — operator ratify/amend/revert]`: commit `3e5bb3e7` added `secretspec.toml` to `.gitignore`, a reserved-lever edit made under a corrected false premise (`cb4b4201:.gitignore` had **0** secretspec lines — the "tracked-and-ignored drift" was dirty-tree-only, so "keep ignored" required *adding* the entry). Mechanically correct; NOT ratified by review. Accept as-is, amend, or revert `3e5bb3e7`-scoped-to-`.gitignore` before merge.
- **Push** `git push -u origin hygiene/asana-readiness` (branch ref durable in-repo even if `/tmp/hygiene-readiness` is pruned).
- **Merge** to `main` (gated on D2). Cleanup-surface STRONG is banked; no further rite-side gate.
- **Worktree cleanup** `git worktree remove /tmp/hygiene-readiness` (branch ref persists).

## §3 · Follow-on routing (watch-registered DEFER — each a named item)

| Item | Route | Trigger |
|---|---|---|
| 67 narrowings (62 multi-code `type:ignore` + 5 file-blanket E402) | `/frame` → **hygiene-pass-2** | manual per-site mypy bisection on the now-vacancy-free floor |
| ASANA_PAT `_ARN`-first vs `--provider env` coherence gap | **arch + security** (separate initiative) | `auth/bot_pat.py` `@lru_cache`+`_ARN` resolution blinds the manifest's env-check |
| `secretspec.toml.example` | **operator** | untracking removes the manifest from fresh checkouts/CI — decide if a committed template is warranted |
| L-001 `just lint-noqa-drift` mise-shim gap | **sre / 10x-dev** | recipe body proven RED directly; the `just` wrapper's mise shim needs a CI runner check (does NOT block merge) |
| `merged` + `verified-realized` (drift-guarded-over-time) | **post-merge + telos deadline 2026-07-15** | rite-disjoint attester observes no dead-noqa re-accretion post-merge → flips telos `verified_realized: ATTESTED`, `cross_stream_concurrence: true` |

## §4 · Rung ladder (honest CAP)

| Rung | State |
|---|---|
| scanned / planned / executed / gate-green | ✓ |
| audit-verified (MODERATE) | ✓ (hygiene audit-lead) |
| **cleanup-surface STRONG (evidence-grade axis, single rite-disjoint mechanical re-fire)** | ✓ **THIS review** |
| merged | ✗ operator (gated on D2) |
| drift-guarded-over-time / verified-realized | ✗ post-merge + telos deadline 2026-07-15 (rite-disjoint attester) |

*Review close. Cleanup-surface STRONG banked; realization pre-merge. Do NOT dispatch the operator's
merge/push — the operator switches rites. Follow-on (hygiene-pass-2, arch/security) routes via a fresh `/frame`.*
