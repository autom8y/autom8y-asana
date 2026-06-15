---
type: handoff
handoff_type: validation
status: proposed
source_rite: eunomia
target_rite: sre
title: Eunomia verdict (STRONG-WITHHELD-PENDING-STABILITY) + the reliability frontier (AMBER-2, deploy-gate, Node20, config-overload)
date: 2026-06-10
verdict_artifact: .ledge/reviews/EUNOMIA-VERDICT-coherent-node-strong-cert-2026-06-10.md
---

# HANDOFF — eunomia → sre — verdict + reliability frontier

## The verdict you inherit
**STRONG-GRANTED** (converted 2026-06-10 ~14:00Z) on the FPC Phase-2 `coherent≥100` node. All gates
GREEN with bit-exact independent receipts (re-derived `coherent=561/gun=10/unit.mrr=723/3021`; G-DENOM
honest — Templates 3/68; residual gun classified null-at-source; IAM live≡TF 3/3 warmer roles) AND the
stability series discharged: **three consecutive autonomous warm writes (13:07 heal → 13:30 POINT-1,
independent invocation, denials=0 → 13:46 POINT-2) all bit-identical** — deterministic, idempotent,
re-clobber-free. Optional belt-and-braces: log the 16:00Z entity-cron pass holding the band (~561/10/723).
The TELOS remains NOT verified-realized (five-signal — SEAM-2, AC-6, valid soak, fallback flip).

## sre work items (ranked; receipts in the verdict + E4 report)
1. **CRITICAL — metrics-smoke-gate deploy hang** (burns the 30-min `satellite-deploy-asana` lock per
   deploy, false-reds healthy deploys): (a) `timeout 60` on `aws ecs execute-command`
   (`autom8y scripts/metrics-smoke-gate.sh:149-154`); (b) land branch `10xdev/probe-sidecar-primitive`
   (`b9554366` — the /ready-gated scrape); (c) split the gate into a non-blocking downstream job so the
   deploy job releases the concurrency slot (`satellite-receiver.yml:57-59,339`).
2. **HIGH — Node20 action deprecation, hard date 2026-06-16 (six days):** re-pin `actions/*` +
   `aws-actions/*` to Node24-ready releases across `satellite-receiver.yml` + autom8y-workflows
   `satellite-ci-reusable.yml`; resolve the `configure-aws-credentials` two-SHA skew (`e3dd6a42` vs `7474bc46`).
3. **HIGH — CodeArtifact token fetch retry/timeout** at 4 call sites (3× reusable workflow:287/508/1197,
   1× asana test.yml:129) — `--cli-connect-timeout 15 --cli-read-timeout 30` + 3-attempt loop.
4. **HIGH — AMBER-2 SLI still dark** (`EcsServiceDenominatorAbsent`): the `:503` deploy was another
   re-test window; if still dark, the emit→scrape gap is yours. A dark SLI cannot certify the soak.
5. **MED — `ASANA_CACHE_S3_PREFIX` overload split:** one env var drives BOTH the task-cache `S3Settings.prefix`
   AND dataframe storage (set to `asana-cache/project-frames/`); the cure is now decoupled (pinned constant)
   but the next consumer will trip it. Config-hygiene: separate vars (coordinate w/ architect).
6. **MED — bulk/section lanes** carry the IAM grant (live+TF) but have NOT empirically exercised the
   cold-read heal path (bulk was rate-limited on live fetches) — verify a heal/deny event on their next
   durable-read cycle.

## Operator-review items carried (NOT sre's, surfaced)
- CHANGE-001 (live-smoke forcing function — nightly OIDC CI job recommended) — needs operator ack
  (`.ledge/specs/PLAN-eunomia-stub-theater-remediation-2026-06-10.md`).
- UK-2 (#114) — now informed by `discount:335` healing live (the drift cell surfacing).
- CR-3 Stage-B→Secret-2 (soak-gated, AC-6 RED) · AC-6 cutover (#36/R2) · `legacy_fallback=False`.

## Watch-register (DEFER)
Throughline candidate `integration-boundary-fidelity` (N_applied=1; promotes at N≥2) · stub-census
Top-10 (2 HIGH) · CHANGE-002..005 · D-1 docstring nit · Option-2 S3-as-store-read-tier · #97 warmer fast-lane.

## Rungs (never round up)
Node = `independently-re-derived` (STRONG pending the mechanical stability series). Telos =
NOT verified-realized (five-signal gates on SEAM-2 + AC-6 + valid soak + fallback-flip).

Next `/frame` → `sre/framing`.
