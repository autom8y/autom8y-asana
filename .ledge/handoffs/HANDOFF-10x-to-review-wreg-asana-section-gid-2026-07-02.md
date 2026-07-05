---
type: handoff
artifact_subtype: 10x-to-review
initiative: asana-cutover-readiness-credential-topology
handoff_type: assessment
from_rite: 10x-dev
to: review (rite-disjoint STRONG cert) → operator (merge)
from_station: /qa GO (qa-adversary, terminal gate, MODERATE)
created: 2026-07-02
status: proposed
rung: proven-in-PR (MODERATE; SCAR-REG-001 OPEN — CLOSED = /review STRONG + user merge)
telos: root charge = .sos/wip/frames/asana-cutover-readiness-sequencing.shape.md (§5 sprint-4-reg, PT-04)
---

# HANDOFF: 10x-dev (close) → review — W-REG-proper closes SCAR-REG-001 (PR #190)

> **Boundary**: 10x-dev BUILT + adversarially validated (**/qa GO, MODERATE**) the W-REG section-GID
> replacement that drives SCAR-REG-001 from OPEN → **proven-in-PR**. PR #190 OPEN, NOT merged.
> This crux caps at MODERATE (same-rite critic). **`/review` is the rite-disjoint STRONG cert**; the
> merge is the operator's. SCAR-REG-001 CLOSES only at `/review` STRONG + user merge. This is the
> LAST POLE of the asana-cutover-readiness charge.

## §1 · What was built (PR #190 `feat/wreg-live-section-gids`, off origin/main 7dc41c01)
Design LOCKED (TDD `.ledge/specs/TDD-asana-pat-read-route-and-wreg.md`); entered at /build. **Option B (import-time join-wiring)** chosen — the module derives `EXCLUDED_SECTION_GIDS`/`UNIT_SECTION_GIDS`/`EXCLUDED_GID_TO_NAME` from a single `_RECEIPT_NAME_TO_GID` (17 pairs) via `_build_live_registry → join_section_registry` at import (`section_registry.py:456`), raising `SectionRegistryError` fail-closed on `blocks_live_wiring` (`:420→429`). Monolith taxonomy vendored READ-only.
| Commit | Node | Change |
|---|---|---|
| `f097ccae` | N1 | 17-map replacement (4 excluded + 13 unit; UNIT 15→13, Account Review/Error → EXCLUDED only); removed 5 `VERIFY-BEFORE-PROD` markers + the `_looks_sequential` heuristic (it false-fired on the real …565→…571 run). |
| `a1db99d5` | N2a | fail-closed HALT (`SectionRegistryError`) on the live frozenset-producing path when `blocks_live_wiring`. |
| `6a9f9db0` | N3 | two-sided wrong-bucket fixture + gate-bite proof (`test_section_registry_live_wreg.py`, 14 tests). |
| `773f11c0` | N2b | re-export `assert_no_plaintext_pat_in_caller` from `auth/__init__` + documented caller-image contract (Pythia FORK-N2b = Disposition B; leg-i test already existed). |

## §2 · /qa verdict — GO (7 axes PASS)
- **Zero-transposition**: independent AST-literal-eval re-derivation from the on-disk receipt §2 = **17/17 identical char-for-char** (triple-verified: receipt-order + bucket-grouped fixture + external audit).
- **N2a NOT theater**: full live-path trace `reconciliation_runner:120 → engine → processor.py:35/165 ← section_registry.py:456 ← _build_live_registry:388 → raise :429`; no ungated source. Mutation M2 (defect reintroduced) → the service **cannot import/start**.
- **Two-sided teeth**: 4/4 mutations bit + restored (transposed digit / Tier-1 removal / gate-neuter / wrong-bucket vendoring).
- **15→13 shrink correct**; **no false fabricated-warning**; **no scope-creep** (PR footprint exactly 5 files; the 3 `taxonomy_divergence` findings stay INFO, do NOT trip `blocks_live_wiring`).
- Proof surface: ruff/mypy-strict/RUF100 clean; 250 targeted tests pass; full 13,960-suite has **0 PR regressions** (3 failures reproduce at merge-base — environmental).

## §3 · What `/review` must verify for STRONG (the MODERATE→STRONG delta)
Rite-disjoint re-attestation of: (1) the 17-GID transcription vs the receipt §2 (re-derive independently); (2) the N2a gate genuinely on the live consumption path (not theater); (3) the fixture genuinely two-sided (mutate-and-check); (4) the 15→13 UNIT shrink + Account Review/Error EXCLUDED-only; (5) no scope-creep + R-REG-4 kept INFO; (6) rung honesty (proven-in-PR, SCAR-REG-001 still OPEN). STRONG = disjoint concurrence; then operator merge → **SCAR-REG-001 CLOSED**.

## §4 · Pre-review / pre-merge recommendations (optional, non-blocking)
1. **[LOW — provenance] Commit the W-IRIS receipt.** `.ledge/reviews/W-IRIS-section-gid-receipt-2026-07-02.md` is the transcription source-of-truth but is **untracked** (GIDs non-secret per receipt §6). Committing it (to the PR branch or main) makes the transcription chain auditable in-tree for `/review`'s re-derivation.
2. **[LOW — polish] Uninformative import error.** `section_registry.py:465-467`: an excluded-name/receipt drift dies with a bare `KeyError` instead of a `SectionRegistryError` with operator guidance. Fail-loud is preserved; polish only.

## §5 · DEFER register (watch-registered — NOT scope-crept into this crux)
- The 5 credential-topology DEFERs (`.know/defer-watch.yaml`).
- **#927 `SERVICE_CLIENT_ID=asana` root-cause** (iris finding: the deployed service's own S2S identity is a bare name, not `sa_`-prefixed → its self-mint 401s → plausible metrics-export SEAL cause) → **route sre/10x, separate** (now watch-registered).
- R-REG-4 `taxonomy_divergence` (Next Steps / Account Review / Account Error EXCLUDED-but-not-monolith-`ignore`) — INFO, surfaced, NOT auto-reconciled.

## §6 · Security disclosure (honest, operator's call)
During /qa, the ambient `ASANA_PAT` **value entered the qa session transcript** via a careless `${ASANA_PAT:-NO}` shell expansion (all subsequent runs used `env -u ASANA_PAT`; the PR is unaffected). Combined with iris's note that a bare plaintext `ASANA_PAT` sits in the interactive session env: **rotating the asana bot PAT is worth considering.** (Distinct from the git-history leak the operator ruled ephemeral.) Reserved lever — surfaced, not pulled.

## §7 · Rung ladder + user-sovereign levers
`authored < emitting < alerting < proven < merged < live < protecting-prod`. **Now at `proven` (proven-in-PR / MODERATE).** SCAR-REG-001 CLOSES at `/review` STRONG + user merge; `verified_realized` stays HELD until live deploy. **User-sovereign (surfaced, never pulled):** the PR merge · deploy · the live Asana section-GID WRITE · rollback · token rotation.

*Anchors: PR #190 (`feat/wreg-live-section-gids`, commits f097ccae/a1db99d5/6a9f9db0/773f11c0) · receipt `.ledge/reviews/W-IRIS-section-gid-receipt-2026-07-02.md` · TDD `.ledge/specs/TDD-asana-pat-read-route-and-wreg.md` · ADR `.ledge/decisions/ADR-asana-pat-read-route-forkR-2026-07-02.md` · prior handoffs (security, 10x-to-operator, operator-to-iris-wreg).*
