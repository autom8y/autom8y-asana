---
type: spec
spec_subtype: coordination-dashboard
status: proposed
lifecycle_state: in_progress
links_to: HANDOFF-hygiene-asana-to-hygiene-fleet-2026-04-20
parent_session: session-20260415-010441-e0231c37
created_at: "2026-04-20T00:00:00Z"
---

# Fleet coordination — env/secret platformization

Live status per satellite. Each satellite CC session owns its row; the parent session in autom8y-asana flips the fleet HANDOFF to `completed` when all rows are terminal (`completed`, `aligned`, `opted-out`, or `deferred-to-ecosystem`).

## Status table

| Satellite | Wave | Priority | Status | Worktree | Branch | HANDOFF-RESPONSE | PR |
|-----------|------|----------|--------|----------|--------|------------------|-----|
| autom8y-ads | 1 | HIGH | completed (merge-through-known-red; scope-exonerated against ECO-BLOCK-001) | ../autom8y-ads-fleet-hygiene | hygiene/sprint-env-secret-platformization | `autom8y-ads-fleet-hygiene/.ledge/reviews/HANDOFF-RESPONSE-hygiene-autom8y-ads-to-hygiene-fleet-2026-04-20.md` | [#12](https://github.com/autom8y/autom8y-ads/pull/12) |
| autom8y-scheduling | 1 | HIGH | completed (admin-merge; main-branch dep block scope-exonerated) | ../autom8y-scheduling-fleet-hygiene | hygiene/sprint-env-secret-platformization | `autom8y-scheduling-fleet-hygiene/.ledge/reviews/HANDOFF-RESPONSE-hygiene-autom8y-scheduling-to-hygiene-fleet-2026-04-20.md` | [#8](https://github.com/autom8y/autom8y-scheduling/pull/8) |
| autom8y-sms | 1 | HIGH | pending | ../autom8y-sms-fleet-hygiene | hygiene/sprint-env-secret-platformization | — | — |
| autom8y-dev-x | 2 | MEDIUM | pending | ../autom8y-dev-x-fleet-hygiene | hygiene/sprint-env-secret-platformization | — | — |
| autom8y-hermes | 2 | MEDIUM | pending (STOP-GATE risk — non-standard .envrc) | ../autom8y-hermes-fleet-hygiene | hygiene/sprint-env-secret-platformization | — | — |
| autom8y-val01b | 2 | MEDIUM | pending | ../autom8y-val01b-fleet-hygiene | hygiene/sprint-env-secret-platformization | — | — |
| autom8y-api-schemas | 3 | LOW | opted-out | ../autom8y-api-schemas-fleet-hygiene | hygiene/sprint-env-secret-platformization | `autom8y-asana/.ledge/reviews/HANDOFF-RESPONSE-hygiene-autom8y-api-schemas-to-hygiene-fleet-2026-04-20.md` | [#3](https://github.com/autom8y/autom8y-api-schemas/pull/3) |
| autom8y-workflows | 3 | LOW | opted-out | ../autom8y-workflows-fleet-hygiene | hygiene/sprint-env-secret-platformization | `autom8y-workflows-fleet-hygiene/.ledge/reviews/HANDOFF-RESPONSE-hygiene-autom8y-workflows-to-hygiene-fleet-2026-04-20.md` | [#5](https://github.com/autom8y/autom8y-workflows/pull/5) |
| autom8y-data | 3 | LOW | completed (remediation — premise falsified; 3 gaps closed; Pythia Disposition B; upstream-feedback UPSTREAM-001..003 filed) | ../autom8y-data-fleet-hygiene | hygiene/sprint-env-secret-platformization | `autom8y-data-fleet-hygiene/.ledge/reviews/HANDOFF-RESPONSE-fleet-data-env-2026-04-20.md` | pending /pr |

## Canonical source artifacts (all in autom8y-asana)

- HANDOFF: `.ledge/reviews/HANDOFF-hygiene-asana-to-hygiene-fleet-2026-04-20.md`
- Playbook: `.ledge/specs/PLAYBOOK-satellite-env-platformization.md`
- ADR-0001: `.ledge/decisions/ADR-env-secret-profile-split.md`
- ADR-0002: `.ledge/decisions/ADR-bucket-naming.md`
- TDD-preflight: `.ledge/specs/TDD-cli-preflight-contract.md`
- TDD-lambda: `.ledge/specs/TDD-lambda-default-bucket-refactor.md`
- .know/: `.know/env-loader.md`
- AUDITs: `.ledge/reviews/AUDIT-env-secrets-sprint-{A,B,C,C-delta,D}.md`
- Smell inventory: `.ledge/reviews/smell-inventory-env-secrets-2026-04-20.md`

## Update protocol

Each satellite CC session, upon terminal state, edits its row in the table: `status`, `HANDOFF-RESPONSE` path, `PR` URL. The parent session in autom8y-asana reads this dashboard to decide when to flip the fleet HANDOFF to `completed` and emit the subsequent ECO-001 (ecosystem rite) + SRE-001 (SRE rite) Wave 4 handoffs.

## Ecosystem-scoped blockers (cross-fleet)

Blockers that surfaced in multiple satellite sprints and are NOT caused by the env/secret sprint itself. Satellite sprints scope-exonerate and merge through; these require a separate rite to remediate.

| ID | Surface | First observed | Satellites affected | Scope | Status | Next rite |
|---|---|---|---|---|---|---|
| ECO-BLOCK-001 | CodeArtifact publish gap | 2026-04-20 | autom8y-ads (#12), autom8y-scheduling (#8) | `autom8y-api-schemas>=1.9.0` pinned in satellites' `pyproject.toml`; only `<=1.8.0` published to the internal CodeArtifact index. Breaks `Convention Check`, `Lint & Type Check`, `OpenAPI Spec Drift`, `Integration Tests` on main AND on all satellite PRs. Confirmed pre-existing on each satellite's `main` HEAD (via `gh run list --branch main`). | OPEN | ecosystem rite or release manager — publish `autom8y-api-schemas` 1.9.0 to CodeArtifact, OR unpin satellites to `<=1.8.0` |

**Remediation owner**: parent session (autom8y-asana) at Wave 4 transition — either route to ecosystem rite via ECO-001 handoff, or raise with release management independently.

**Sprint-local handling** (documented in case future satellite sprints hit same class of blocker): Potnia through-line discipline — if a CI failure is (a) identical to main HEAD and (b) touches zero files in sprint scope, Potnia may recommend admin-merge with explicit stakeholder authorization. Scope-exoneration must be cited in both the HANDOFF-RESPONSE and the dashboard row status cell.

## Terminal status vocabulary

- `completed` — satellite sprint executed playbook steps, PR merged
- `aligned` — reference-pattern satellite (autom8y-data) found zero-gap; no remediation needed
- `opted-out` — satellite is pure library / no runtime env surface; opt-out documented
- `deferred-to-ecosystem` — satellite STOP-GATE failed non-trivially; ecosystem rite handoff emitted

## Launch order recommendation

1. Wave 3 opt-outs first (autom8y-api-schemas, autom8y-workflows) — close quickly, clear dashboard
2. Wave 1 HIGH (autom8y-ads, autom8y-scheduling, autom8y-sms) in parallel — core delta work
3. Wave 2 MEDIUM (autom8y-dev-x, autom8y-hermes, autom8y-val01b) concurrent with or after Wave 1
4. Wave 3 autom8y-data last as the alignment capstone

## Cross-session monitoring

From any CC session: `/sessions --all` lists every active session across worktrees. Use it to check fleet progress.
