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
| autom8y-dev-x | 2 | MEDIUM | completed (7 atomic commits; PR [#2](https://github.com/autom8y/autom8y-dev-x/pull/2) merged @ `447c1b08`; Sprint-A/B/C audits PASS; pytest 3831/0/17 no-env verified; Step-4 `[profiles.cli]` SKIP-WITH-RATIONALE per ADR-0001 truthful-contract — chose rationale-in-header pattern, diverges from autom8y-data empty-block pattern — see ECO-BLOCK-003 UPSTREAM-001; Step 7 SKIP zero S3 bindings; atomicity advisory on `e24cbc9` bundling 3 pre-session platform-infra deletions, non-blocking per hygiene-11-check Lens 2) | ../autom8y-dev-x-fleet-hygiene | hygiene/sprint-env-secret-platformization | `autom8y-asana/.ledge/reviews/HANDOFF-RESPONSE-hygiene-autom8y-dev-x-to-hygiene-fleet-2026-04-20.md` | [#2](https://github.com/autom8y/autom8y-dev-x/pull/2) |
| autom8y-hermes | 2 | MEDIUM | completed (Case B confirmed — decoupling intentional; nix flake + Iris ServiceJWT SSM load-bearing; canonical `.know/env-loader.md` landed 8b9963b1; ecosystem-rite handoff dispatched non-blocking; remote-topology structural finding: no GitHub remote — main integration deferred to ecosystem rite disposition of ECO-BLOCK-002) | ../autom8y-hermes-fleet-hygiene | hygiene/sprint-env-secret-platformization | `autom8y-hermes-fleet-hygiene/.ledge/reviews/AUDIT-env-loader-decoupling-2026-04-20.md` | local-mirror-only; see ECO-BLOCK-002 ([HANDOFF-hermes-to-ecosystem](../../../autom8y-hermes-fleet-hygiene/.ledge/reviews/HANDOFF-hermes-to-ecosystem-2026-04-20.md)); commits `8b9963b1..daea69d8` |
| autom8y-val01b | 2 | MEDIUM | reclassified-source-of-truth (proposed — pending ESC-1 vocabulary ratification by fleet Potnia; ADR-val01b-source-of-truth-reclassification-2026-04-20; worktree IS the autom8y monorepo which authors the Layer 1-2 contract; Sprint-A collapsed to ADR + `.know/env-loader-source-of-truth.md` squash-merged to main @ `de8c64d3` + fleet-replan HANDOFF draft; AUDIT PASS single-pass 2026-04-20; 3 forward-pointing handoffs — ESC-1 dashboard vocab, ESC-2 playbook revision cross-rite, ESC-3 Wave-4 ECO-001 obsolescence embedded in RESPONSE; 5 fleet-replan items REPLAN-001..REPLAN-006-SRE-REVIEW; ECO-BLOCK-004 tracks cross-fleet gaps) | ../autom8y-val01b-fleet-hygiene | hygiene/val01b-source-of-truth (squash-merged) | `autom8y-val01b-fleet-hygiene/.ledge/reviews/HANDOFF-RESPONSE-hygiene-val01b-to-hygiene-fleet-2026-04-20.md` | [#111](https://github.com/autom8y/autom8y/pull/111) |
| autom8y-api-schemas | 3 | LOW | opted-out | ../autom8y-api-schemas-fleet-hygiene | hygiene/sprint-env-secret-platformization | `autom8y-asana/.ledge/reviews/HANDOFF-RESPONSE-hygiene-autom8y-api-schemas-to-hygiene-fleet-2026-04-20.md` | [#3](https://github.com/autom8y/autom8y-api-schemas/pull/3) |
| autom8y-workflows | 3 | LOW | opted-out | ../autom8y-workflows-fleet-hygiene | hygiene/sprint-env-secret-platformization | `autom8y-workflows-fleet-hygiene/.ledge/reviews/HANDOFF-RESPONSE-hygiene-autom8y-workflows-to-hygiene-fleet-2026-04-20.md` | [#5](https://github.com/autom8y/autom8y-workflows/pull/5) |
| autom8y-data | 3 | LOW | completed (remediation — "reference repo" premise falsified on inspection; 3 PLAYBOOK gaps closed; Pythia Disposition B ratified empty-`[profiles.cli]`-with-rationale for CLI-less satellites; upstream-feedback UPSTREAM-001..003 filed as ECO-BLOCK-003) | ../autom8y-data-fleet-hygiene | hygiene/sprint-env-secret-platformization | `autom8y-data-fleet-hygiene/.ledge/reviews/HANDOFF-RESPONSE-fleet-data-env-2026-04-20.md` | [#30](https://github.com/autom8y/autom8y-data/pull/30) |

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
| ECO-BLOCK-002 | Hermes .envrc loader decoupling governance | 2026-04-20 | autom8y-hermes (Case B) | Hermes cannot adopt `use autom8y` loader because (a) nix flake is load-bearing (predates fork; `flake.nix` + `uv2nix` build) and (b) `_iris_ssm_fetch()` implements Iris-specific ServiceJWT SSM topology (SERVICE_API_KEY, IRIS_SERVICE_CLIENT_ID, ANTHROPIC_API_KEY from `/autom8y/platform/iris/*`). Canonical `.know/env-loader.md` landed at hermes commit `8b9963b1` documenting the divergence. Cross-rite handoff to ecosystem rite (`autom8y-hermes-fleet-hygiene/.ledge/reviews/HANDOFF-hermes-to-ecosystem-2026-04-20.md`) enumerates 5 options: 3 ruled-in (i) sanction-variance, (ii) design nix-compatible `use autom8y` variant / `use autom8y_iris` composite, (iii) status-quo doc-only closure; 2 ruled-out (iv) drop nix, (v) second loader surface. No forced recommendation. Related deferred audit follow-ups: F.2 (ADR candidate: nix flake as frozen design constraint — tied to option (i)/(iii) disposition), F.7 (90d `expires_after` on `.know/env-loader.md` vs ecosystem-decision timeline). | OPEN (non-blocking for hermes closure — audit PASS 2026-04-20) | ecosystem rite — decide (i)/(ii)/(iii); if (ii), design migration sprint and coordinate with ECO-001 (promote canonical loader to `.a8/autom8y/`) |
| ECO-BLOCK-004 | val01b source-of-truth reclassification governance gaps | 2026-04-20 | autom8y-val01b (Sprint-A reclassified) | Val01b Sprint-A discovered that the worktree IS the autom8y monorepo authoring the fleet contract (canonical loader at `.a8/scripts/a8-devenv.sh:310-417`, canonical bucket in `services.yaml:167`+`terraform/shared/`, secretspec tooling at `tools/secretspec-cross-validator/`). Reclassified Wave 2 → source-of-truth via ADR-val01b-source-of-truth-reclassification-2026-04-20. Four governance gaps surfaced: (1) **ESC-1** dashboard terminal vocabulary lacks `reclassified-source-of-truth` value — 4 existing values (`completed`/`aligned`/`opted-out`/`deferred-to-ecosystem`) all misrepresent the outcome; HANDOFF at `autom8y-val01b-fleet-hygiene/.ledge/reviews/HANDOFF-hygiene-val01b-to-fleet-dashboard-vocabulary-2026-04-20.md`. (2) **ESC-2** PLAYBOOK §B STOP-GATE has 3 branches (template-copy / satellite-sprint / opt-out); source-of-truth is a structurally new 4th branch. Cross-rite HANDOFF to hygiene-asana architect-enforcer at `autom8y-val01b-fleet-hygiene/.ledge/reviews/HANDOFF-hygiene-val01b-to-hygiene-asana-playbook-revision-2026-04-20.md` with 3 revision-spec items + 5 detection heuristics. (3) **ESC-3** Wave-4 ECO-001 ("Promote canonical .know/env-loader.md to ecosystem") obsoleted by reclassification — canonical already lives in val01b worktree; fleet Potnia should strike or redefine. (4) **REPLAN** 5 deferred work items (env.defaults materialization + ecosystem.conf materialization + 5-service secretspec gap [ads/calendly-intake/commission-report/email-booking-intake/payout-report] + missing ADR-ENV-NAMING-CONVENTION + DEPRECATED production.example deletion) packaged as fleet-replan HANDOFF at `autom8y-val01b-fleet-hygiene/.ledge/reviews/HANDOFF-hygiene-val01b-to-fleet-replan-2026-04-20.md`. | OPEN (non-blocking for val01b Sprint-A closure — AUDIT PASS single-pass, PR @ `de68eed6`) | fleet Potnia (ESC-1 + ESC-3) + hygiene-asana architect-enforcer (ESC-2 cross-rite) + fleet-replan sprint scheduling (REPLAN-001..REPLAN-006-SRE-REVIEW) |
| ECO-BLOCK-003 | PLAYBOOK clarification backlog (3 candidates; UPSTREAM-001 evidence now dual-satellite) | 2026-04-20 | autom8y-data (#30, Pythia Disposition B), autom8y-dev-x (#2, rationale-in-header variant) | Three PLAYBOOK clarifications surfaced during FLEET-data alignment audit, routed as upstream-feedback to asana hygiene rite (non-blocking for satellite closure). **UPSTREAM-001** (STRUCTURAL/MODERATE): PLAYBOOK Step 4 decision branch (`PLAYBOOK:171-175`) literally reads "skip if no CLI surface", but fleet grep-discoverability (`rg '\[profiles.cli\]' repos/`) benefits from empty-block-with-rationale pattern for CLI-less satellites. **Now has dual-satellite evidence of the divergence surface**: (i) `autom8y-data/secretspec.toml:143-161` — empty `[profiles.cli]` block + 17-line inline rationale (Pythia Disposition B ratifies as superior); (ii) `autom8y-dev-x/secretspec.toml:1-19` — no `[profiles.cli]` block, rationale appended to file-header comment block citing ADR-0001 + `cli.py:357-363` graceful-degradation line range. Both honor ADR-0001 truthful-contract test. dev-x choice was independent (pre-sprint execution without awareness of Disposition B); the independent convergence on "document the skip" is signal that PLAYBOOK's literal-skip interpretation is ambiguous and both executors felt compelled to document. Clarification blast radius: any future CLI-less satellite will pick one of these two patterns (or a third) without upstream guidance — fleet grep-discoverability of the skip rationale is already inconsistent. **UPSTREAM-002** (TACTICAL/MODERATE): PLAYBOOK Step 2 Layer 3 guidance (`PLAYBOOK:136`) lacks sub-rubric distinguishing safe-to-commit structural defaults (port, database-name-as-placeholder) from secret-adjacent identifiers that leak infra topology (production RDS hostname, KMS ARN). Evidence: `autom8y-data/.env/defaults.example:26-29` deliberately omits DB_HOST (G-9 class). **UPSTREAM-003** (TACTICAL/WEAK): PLAYBOOK Step 6 acceptance (`PLAYBOOK:201`) leaves worked-example variable selection implicit ("one satellite-specific variable"). Advisory — pick most-complex layer interaction or highest fresh-clone friction. Evidence: `autom8y-data/.know/env-loader.md:60-96` (DB_HOST chosen); `autom8y-dev-x/.know/env-loader.md` chose `DEVCONSOLE_LLM_API_KEY` walking `config.py:37-40` fallback to `ANTHROPIC_API_KEY` (highest-interest layer interaction for dev-x). Full proposal texts: `autom8y-data-fleet-hygiene/.ledge/reviews/ALIGNMENT-MEMO-fleet-data-env-2026-04-20.md` §Residual risks; dev-x divergence documented in `autom8y-asana/.ledge/reviews/HANDOFF-RESPONSE-hygiene-autom8y-dev-x-to-hygiene-fleet-2026-04-20.md` §6.1. | OPEN (non-blocking for autom8y-data AND autom8y-dev-x closures — both PRs merged) | asana hygiene rite — ratify Disposition B into PLAYBOOK Step 4 (or choose alt pattern; dual evidence now forces an explicit choice); optional Step 2 + Step 6 rubric additions. If Disposition B rejected upstream, both autom8y-data and autom8y-dev-x audits revert to CONDITIONAL pending pattern realignment. Coordinate with Wave 4 ECO-001 canonical-loader promotion. |

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
