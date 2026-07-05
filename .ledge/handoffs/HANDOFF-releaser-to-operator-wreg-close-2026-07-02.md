---
type: handoff
artifact_subtype: releaser-close
initiative: asana-cutover-readiness-credential-topology
handoff_type: validation
from_rite: releaser
to: operator + sre (deployed-reachable / prod-health, rite-disjoint)
from_station: N5 seam (release-executor merge + pipeline-monitor deploy-dispatch)
created: 2026-07-02
status: proposed
rung: merged + DEPLOY-DISPATCHED (releaser CAP; verified_realized HELD, sre-disjoint)
telos: root charge = .sos/wip/frames/asana-cutover-readiness-sequencing.shape.md
---

# HANDOFF: releaser (close) — W-REG landed → SCAR-REG-001 CLOSED → DEPLOY-DISPATCHED

> **Boundary**: PR #190 (W-REG live section-GIDs, /review STRONG-attested) is **MERGED to main → SCAR-REG-001
> CLOSED → DEPLOY-DISPATCHED**. This is the final act of the asana-cutover-readiness charge's LAST POLE.
> The releaser CAP is DEPLOY-DISPATCHED — **deployed-reachable / verified_realized are rite-disjoint (sre),
> HELD**. The live Asana section-GID WRITE, rollback, PAT-rotation, and any prod promotion beyond the
> auto-dispatch remain the operator's.

## §1 · Receipts (Gate-C — every close-claim carries a live anchor)
- **MERGED**: squash **`2d7d39d98c46e959c38bb6b942bca9c3a5149ae7`** on `main` (tip; *"W-REG: replace 19 fabricated section-GIDs with live W-IRIS receipt (SCAR-REG-001) (#190)"*), `mergedAt 2026-07-02T13:38:14Z`, branch deleted. → **SCAR-REG-001 CLOSED (merged rung).**
- **Scope**: exactly 6 files — the 5 W-REG files (`auth/__init__.py`, `reconciliation/section_registry.py`, 3 tests) + the folded-in W-IRIS receipt (resolved the `section_registry.py:318` dangling citation). Zero bleed from the main-merge.
- **CI**: 24 required checks green / 0 fail on the merge head `23bd579f`; `mergeable MERGEABLE / mergeStateStatus CLEAN` re-pulled LIVE immediately before merge (G-PREMISE).
- **DEPLOY-DISPATCHED**: `Test@main` run **`28594437830`** = success → `Satellite Dispatch` run **`28594795831`** = success (2d7d39d9). The deploy is dispatched to the downstream a8 pipeline.

## §2 · What closed
**SCAR-REG-001** — the 19 fabricated sequential-placeholder section-GIDs (`…600-603` + `…610-624`) that would have silently misrouted every account between active/activating/inactive buckets — are replaced on `main` with the **live-verified 17-map** from the W-IRIS receipt (4 excluded + 13 unit, dual-anchored to the monolith `BusinessUnits.SECTIONS` taxonomy), behind an import-time fail-closed gate that halts on any undispositioned live section. The last pole of the asana-cutover-readiness charge is landed.

## §3 · Honest rung (never rounded up)
`authored < emitting < alerting < proven < merged < live < protecting-prod`. Reached: **merged + DEPLOY-DISPATCHED** (the releaser CAP). **A merge/dispatch is NOT "live in prod."**
- `deployed-reachable` / `verified_realized` = **[UNATTESTED — DEFER-POST-HANDOFF]** — rite-disjoint (sre/eunomia): requires the downstream a8 deploy to converge (ECS steadyState on the new `autom8y-asana-service` task-def revision) + a green health signal. Not releaser's to claim.
- Releaser executed; it did NOT re-certify — the STRONG grade is /review's (rite-disjoint, already earned). Landing claims self-cap at MODERATE.

## §4 · Next (all rite-disjoint / user-sovereign)
- **[sre]** Confirm `deployed-reachable`: the a8 deploy run for `2d7d39d9` completes → ECS steadyState on the new task-def rev → health green. (The prior W-IRIS 200 already proved the *route* reachable; this confirms the *data* replacement is live.)
- **[user-sovereign]** The **live Asana section-GID WRITE** was never part of this procession (READ + registry-data only) — it stays yours if/when a write-back is ever wanted.
- **[user-sovereign]** **PAT rotation** — the ambient `ASANA_PAT` entered a prior agent transcript + sits in the interactive env; rotation worth considering (distinct from the git-history leak). Watch-registered.

## §5 · DEFER register (watch-registered — NOT scope-crept into this landing)
`.know/defer-watch.yaml`: the 5 credential-topology DEFERs · **#927** (`SERVICE_CLIENT_ID=asana` self-mint 401 → metrics-export SEAL, → sre/10x) · **R-REG-4** taxonomy_divergence (INFO) · **the `:465-467` bare-KeyError polish** (deferred at this seam per FORK-RECOS, → /hygiene or /10x) · the leaked-history + interactive-env PAT dispositions.

## §6 · Rung ladder + user-sovereign levers
User-sovereign (surfaced, never pulled by the rite): prod deploy-apply beyond the auto-dispatch · rollback · error-budget freeze · PAT rotation · the live Asana section-GID WRITE. Route `deployed-reachable` confirmation toward **sre/framing** (do NOT dispatch sre specialists from here).

*Releaser close. SCAR-REG-001 CLOSED (squash 2d7d39d9); DEPLOY-DISPATCHED (Satellite Dispatch 28594795831). verified_realized HELD (deploy-gated, sre-disjoint). The asana-cutover-readiness LAST POLE is landed.*
