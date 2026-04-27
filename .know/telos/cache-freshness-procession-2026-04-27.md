---
type: telos
initiative_slug: cache-freshness-procession-2026-04-27
parent_initiative: verify-active-mrr-provenance
authored_at: 2026-04-27T16:59:44Z
authored_by: thermia.potnia (procession coordinator)
session_id: session-20260427-185944-cde32d7b
rite: thermia
worktree: .worktrees/thermia-cache-procession/
branch: thermia/cache-freshness-procession-2026-04-27
schema_version: 1
---

# Telos Inception — cache-freshness-procession-2026-04-27

## inception_anchor

- **framed_at**: 2026-04-27
- **frame_artifact**: `.ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md` (inbound dossier from 10x-dev rite)
- **secondary_frame_artifacts** (RECONSTRUCTED, see Provenance Note below):
  - `.ledge/specs/verify-active-mrr-provenance.prd.md` (parent PRD)
  - `.ledge/specs/freshness-module.tdd.md` (parent T3 TDD)
  - `.ledge/specs/handoff-dossier-schema.tdd.md` (parent T4 TDD)
  - `.ledge/decisions/ADR-001-metrics-cli-declares-freshness.md` (parent ADR-1)
  - `.ledge/decisions/ADR-002-rite-handoff-envelope-thermia.md` (parent ADR-2)
- **why_this_initiative_exists**: The 10x-dev rite shipped a freshness signal for the `active_mrr` CLI but, per Axiom 1 critic-rite-disjointness, cannot self-attest the `verified_realized` telos gate. The thermia rite receives the dossier of deferred concerns (D5 section-coverage telemetry, D10 cache_warmer schedule + per-section TTL, NG4 force-warm CLI affordance, NG8 freshness SLA enforcement, D7 env-matrix legacy-cruft inventory) and must discharge them — culminating in thermal-monitor attesting the parent initiative's `verified_realized` gate by the 2026-05-27 deadline.

## scope (per Attester Acceptance §, dossier line 167+)

Thermia accepts ownership of:

- **D5** — section-coverage telemetry (deferred from PRD NG5)
- **D10** — cache_warmer Lambda schedule audit + per-section TTL design (deferred from PRD NG7)
- **NG4** — force-warm CLI affordance (declared in PRD NG4, not implemented by 10x-dev)
- **NG8** — freshness SLA enforcement (publish-blocking gates, automated re-warm triggers)
- **D8** — `verified_realized` telos attestation by 2026-05-27 (parent initiative discharge)
- **D7** *provisional* — env-matrix legacy-cruft remediation. Per user SQ-2 decision: **secondary-handoff to hygiene rite** rather than thermia ownership. Heat-mapper 6-gate assessment confirms cache-architecture-irrelevance, then thermia produces a structured `/cross-rite-handoff --to=hygiene` dossier with the 12-line file:line inventory from parent dossier §7.

## shipped_definition

- **code_or_artifact_landed** (target — populated as procession proceeds):
  - Heat-mapper 6-gate assessment artifact: `.sos/wip/thermia/heat-mapper-assessment-cache-freshness-2026-04-27.md`
  - Thermodynamicist architecture spec: `.ledge/specs/cache-freshness-architecture.tdd.md`
  - Capacity-engineer capacity + TTL spec: `.ledge/specs/cache-freshness-capacity-spec.md`
  - Thermal-monitor observability + SLO design: `.ledge/specs/cache-freshness-observability.md`
  - Force-warm CLI affordance + SLA gates: implementation handoff to 10x-dev (suspended thermia → 10x-dev re-handoff)
  - Hygiene secondary handoff: `.ledge/handoffs/HANDOFF-thermia-to-hygiene-{date}.md` (D7 disposition per SQ-2)
  - Redesign-as-followup recommendation (per SQ-1 best-of-both): `.ledge/spikes/cache-architecture-redesign-recommendation-2026-04-27.md` (if heat-mapper's 6-gate identifies clearly-scoring alternatives)
- **user_visible_surface**: thermia's contribution is design-substrate + attestation; user-visible runtime artifacts ship via downstream 10x-dev re-handoff + the verified parent initiative's existing CLI surface.

## verified_realized_definition (D8 discharge gate)

Per user SQ-3 decision: **BOTH design-review + in-anger-probe** verification mode.

- **Design-review attestation** (pre-impl): thermal-monitor reviews thermia's design artifacts (heat-mapper assessment, thermodynamicist spec, capacity spec, observability spec). Each artifact must pass the cross-architecture-validation 11-lens rubric (per `hygiene-11-check-rubric` adapted for thermia's domain).
- **In-anger probe attestation** (post-impl): thermal-monitor validates deployed force-warm + telemetry + SLA enforcement against `s3://autom8-s3/dataframes/1143843662099250/sections/`. Probe set:
  - Force-warm CLI invocation reduces oldest-parquet age below threshold within N seconds.
  - Telemetry surfaces alert on max_mtime > SLA threshold within M seconds of breach.
  - Force-warm + freshness CLI compose: post-warm freshness signal shows fresh state with no manual intervention.
- **verification_method**: dual-stage attestation per above
- **verification_deadline**: 2026-05-27
- **rite_disjoint_attester**: thermia.thermal-monitor (de-facto verification-auditor — see Pantheon-Role Disambiguation below)
- **fallback_attester**: sre.observability-engineer (per dossier §8.1 latent decision #2 — SLO-shaped surface fits observability-engineer charter; activation predicate per `.ledge/specs/handoff-dossier-schema.tdd.md` §5)

## attestation_status

- **inception**: INSCRIBED (this telos declaration, authored 2026-04-27)
- **shipped**: UNATTESTED (procession in P0; populated as artifacts land)
- **verified_realized**: UNATTESTED (discharged by thermal-monitor at parent initiative gate, by 2026-05-27)

## Pantheon-Role Disambiguation

The parent dossier (`HANDOFF-10x-dev-to-thermia-2026-04-27.md`) names `thermia.verification-auditor` as primary attester. The thermia rite pantheon (per `ari rite current` and `.claude/agents/`) contains: potnia, heat-mapper, systems-thermodynamicist, capacity-engineer, thermal-monitor. **No agent named `verification-auditor` exists.** Per receiving-rite authority over its own pantheon-role mapping (recorded in dossier §Attester Acceptance authored at commit `37932b89`), `thermia.thermal-monitor` discharges the verification gate — closest semantic fit per its charter ("cross-architecture validation").

## Provenance Note (Reconstructed Design References)

The 10x-dev sprint (predecessor session `session-20260427-154543-c703e121`) authored five design artifacts to disk in the `.worktrees/active-mrr-freshness/` worktree, but the `**/.ledge/*` gitignore pattern silently caused `git add` to skip them. Only the dossier + sidecar + INDEX + QA report were force-added. At sprint wrap, the worktree was removed, **permanently destroying the on-disk source files**.

The thermia procession's first commits will include **RECONSTRUCTED** versions of:
- `.ledge/specs/verify-active-mrr-provenance.prd.md` — reconstructed from dossier quotations, conversation-memory of authoring, and surviving QA report's PRD section anchor citations.
- `.ledge/specs/freshness-module.tdd.md` — reverse-engineered from the merged `src/autom8_asana/metrics/freshness.py` + `src/autom8_asana/metrics/__main__.py` + adversarial test fixtures + engineer's return summary.
- `.ledge/specs/handoff-dossier-schema.tdd.md` — reconstructed from the surviving dossier-as-exemplar + architect's return summary describing the 6-section schema.
- `.ledge/decisions/ADR-001-metrics-cli-declares-freshness.md` — reconstructed from dossier references + freshness.py module structure.
- `.ledge/decisions/ADR-002-rite-handoff-envelope-thermia.md` — reconstructed from dossier-frontmatter + 4-alternatives summary + Pythia P2 conformance verdict.

Each reconstructed artifact carries a `[RECONSTRUCTED-2026-04-27]` tag in frontmatter with provenance pointers. The originals are not byte-perfect recoverable; reconstructions are semantic-fidelity preserving.

**Sprint-retro item** (logged for future hygiene/eunomia work): the `**/.ledge/*` gitignore pattern should be amended to `**/.ledge/{specs,decisions,reviews,handoffs}/` allow-list (or equivalent), or engineer dispatches must explicitly include `git add -f` for all `.ledge/` writes. This is filed as an open follow-up for the hygiene secondary-handoff (SQ-2 disposition).

## procession_phases (per thermia.potnia consult)

- **P0** — pre-flight stakeholder interview + reconstruction + telos inception (CURRENT)
- **P1** — heat-mapper 6-gate assessment (gates D7 disposition + redesign-vs-operationalize)
- **P2** — systems-thermodynamicist architecture spec (cache pattern, consistency, failure modes)
- **P3** — capacity-engineer per-section TTL + warmer schedule + force-warm sizing
- **P4** — thermal-monitor observability + SLO + alerting design
- **P5** — handoff dossier authoring (thermia → 10x-dev for impl) + hygiene secondary-handoff (D7)
- **P6** — 10x-dev impl phase (suspended on this rite; requires CC restart + rite switch)
- **P7** — thermal-monitor design-review + in-anger-probe attestation (discharges D8 telos)
- **close** — `/sos wrap` + `/cross-rite-handoff` to whichever rite owns post-attestation hygiene
