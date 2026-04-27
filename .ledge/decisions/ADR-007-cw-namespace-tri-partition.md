---
type: decision
status: accepted
adr_id: ADR-007
title: CloudWatch namespace tri-partition (warmer-side / DMS / CLI-side)
authored_on: 2026-04-28
authored_by: hygiene.architect-enforcer (procession-side authoring; hygiene W1.P1)
amends: ADR-006
procession_id: cache-freshness-procession-2026-04-27
parent_handoff: .ledge/handoffs/HANDOFF-thermia-to-hygiene-2026-04-27.md
evidence_basis: .ledge/reviews/P7A-alert-predicates-2026-04-27.md
---

# ADR-007 — CloudWatch namespace tri-partition

## Status

Accepted. Amends ADR-006 (CloudWatch namespace strategy).

## Context

ADR-006 codified a 2-namespace model for CloudWatch metric emission in this codebase:

- `Autom8y/FreshnessProbe` (Pascal case) — CLI-side metrics emitted from `src/autom8_asana/metrics/cloudwatch_emit.py`.
- `autom8y/cache-warmer` (lowercase) — coalescer dedup metric `CoalescerDedupCount` emitted from `src/autom8_asana/cache/dataframe/coalescer.py:34-67`.

The thermia procession's P7.A.3 live AWS predicate execution (`.ledge/reviews/P7A-alert-predicates-2026-04-27.md`) and follow-up source-code archaeology confirmed a **3rd active production namespace** that ADR-006 did not document:

- `Autom8y/AsanaCacheWarmer` (Pascal case) — Dead-Man's-Switch heartbeat. Emitted from `src/autom8_asana/lambda_handlers/cache_warmer.py:845` via `autom8y_telemetry.aws.emit_success_timestamp(DMS_NAMESPACE)` where `DMS_NAMESPACE = "Autom8y/AsanaCacheWarmer"` is a hardcoded constant at `cache_warmer.py:70`. Production AWS scan confirms this namespace contains the metric `LastSuccessTimestamp`.

Additionally, the warmer-side metrics `WarmSuccess` / `WarmFailure` / `WarmDuration` / `RowsWarmed` / `CheckpointSaved` / `CheckpointResumed` (emitted from `cache_warmer.py:473,478,484,501,525,545,566` via the local `emit_metric` helper at `src/autom8_asana/lambda_handlers/cloudwatch.py`) target a **runtime-configured namespace** sourced from `settings.observability.cloudwatch_namespace` (Pydantic field at `settings.py:604`). Production deployment value matches the coalescer namespace (`autom8y/cache-warmer` lowercase), evidenced empirically by the presence of `CoalescerDedupCount` in that namespace and the absence of the warmer metrics from any other Autom8y* / autom8y/* namespace as of 2026-04-27.

## Decision

CloudWatch namespace topology for this codebase is **tri-partitioned** as follows:

| Layer | Namespace | Casing | Source of truth | Metrics |
|---|---|---|---|---|
| **CLI-side** | `Autom8y/FreshnessProbe` | Pascal | hardcoded in `src/autom8_asana/metrics/cloudwatch_emit.py` (`ALL_CLI_METRICS` frozenset + `c6_guard_check`) | `MaxParquetAgeSeconds`, `ForceWarmLatencySeconds`, `SectionCount`, `SectionAgeP95Seconds`, `SectionCoverageDelta` |
| **Warmer DMS** | `Autom8y/AsanaCacheWarmer` | Pascal | hardcoded constant `DMS_NAMESPACE` at `src/autom8_asana/lambda_handlers/cache_warmer.py:70` | `LastSuccessTimestamp` (via `autom8y_telemetry.aws.emit_success_timestamp`) |
| **Warmer-side metrics** | runtime-configured (production: `autom8y/cache-warmer` lowercase) | lowercase (production) | Pydantic `settings.observability.cloudwatch_namespace` at `src/autom8_asana/settings.py:604`; `emit_metric` default fallback at `src/autom8_asana/lambda_handlers/cloudwatch.py` | `WarmSuccess`, `WarmFailure`, `WarmDuration`, `RowsWarmed`, `CheckpointSaved`, `CheckpointResumed`, `TotalDuration`, `CoalescerDedupCount` |

**Implications**:

1. **CLI-side and DMS namespaces are intentionally hardcoded** — Pascal case, no env-var override. This protects against accidental misrouting of safety-critical observability surfaces.

2. **Warmer-side namespace is intentionally runtime-configured** — supports per-environment overrides (e.g., a future canary-vs-mainstream split in observability surfaces). Production value is `autom8y/cache-warmer` (lowercase, with 'y'), matching the coalescer's emission target. The cache_warmer.py:20 module-docstring claim of `autom8/cache-warmer` (no 'y') is **OUTDATED** and should be patched in a follow-on.

3. **Three Pascal-case namespaces** (`Autom8y/FreshnessProbe`, `Autom8y/AsanaCacheWarmer`, plus existing `Autom8y/AsanaAudit` etc. for other initiatives) follow the fleet-level `Autom8y/{Service}{Surface}` pattern. The lowercase `autom8y/cache-warmer` is the singular outlier in casing — accepted because it matches production deployment env var; not pursuing a Pascal-case rename in this ADR (would require coordinated env-var rename + Lambda redeploy + alarm Terraform updates).

## Consequences

### Positive

- ALERT-3 / ALERT-4 / ALERT-5 alarm definitions in Batch-D Terraform have unambiguous namespace + metric anchors per the table above.
- Operator runbooks (`cache-freshness-runbook.md`) can cite explicit namespace/metric pairs without `[PLACEHOLDER]` tokens; lens-3 observability-completeness criterion satisfies operator-runnability without source-code consultation.
- Casing inconsistency between `Autom8y/*` (Pascal) and `autom8y/cache-warmer` (lowercase) is documented as a known production-deployment state, not silent drift.

### Negative

- The cache_warmer.py:20 docstring drift (claims default `autom8/cache-warmer` no-'y') remains unaddressed by this ADR. Filed as DEFER-FOLLOWUP for a future hygiene-rite cycle (low blast-radius docstring fix).
- The 3rd namespace existing-but-undocumented in ADR-006 was a P7.A scope-discovery cost. Future ADRs documenting CW namespaces should pre-enumerate ALL active production namespaces via live `aws cloudwatch list-metrics` scans before authoring. Captured as a process-improvement note for thermia P4 successor processions.

### Neutral

- ADR-006 is AMENDED, not REPLACED. ADR-006's Sections on `Autom8y/FreshnessProbe` (CLI-side) and `autom8y/cache-warmer` (coalescer / warmer-side) remain VALID. ADR-007 adds the `Autom8y/AsanaCacheWarmer` (DMS) layer and clarifies that warmer-side namespace is runtime-configured rather than hardcoded.
- Track B (P7.B) in-anger-probes (Probes 1, 2, 3, 5) operate against the deployed fleet and will validate this 3-namespace topology empirically. Failures during Track B targeting `autom8/lambda::StoryWarmFailure` (a different module — asana-stories warmer, NOT cache-warmer) would surface as REJECTED-REOPEN; the cache-warmer's `WarmFailure` lives at the runtime-config namespace per this ADR.

## Verification

- `aws cloudwatch list-metrics --namespace "Autom8y/FreshnessProbe"` → 5 metrics (per P7.A.3 PRED-2).
- `aws cloudwatch list-metrics --namespace "Autom8y/AsanaCacheWarmer"` → 1 metric `LastSuccessTimestamp` (per 2026-04-28 hygiene W1.P1 verification).
- `aws cloudwatch list-metrics --namespace "autom8y/cache-warmer"` → 1 metric `CoalescerDedupCount` today; expanding to include `WarmSuccess`/`WarmFailure`/`WarmDuration` etc. once warmer Lambda's emit_metric path actually fires (warmer hasn't logged a success/failure event yet, per P7.A.3 evidence).
- Source anchors: `cache_warmer.py:70` (`DMS_NAMESPACE`), `cache_warmer.py:845` (DMS emit), `cache_warmer.py:473,478,484,501,525,545,566` (warmer-side emits), `cloudwatch_emit.py` (CLI-side), `settings.py:604` (runtime-config field).

## References

- ADR-006 (CW namespace strategy, 2-namespace model — AMENDED by this ADR)
- `.ledge/reviews/P7A-alert-predicates-2026-04-27.md` (live-AWS predicate evidence; CORRECTION note in §10 supersedes the artifact's earlier `autom8/lambda::StoryWarmFailure` framing for ALERT-3 backing metric)
- `.ledge/specs/cache-freshness-observability.md` §3.3 (ALERT-3, ALERT-4 namespace anchors)
- `.ledge/specs/cache-freshness-runbook.md` Scenario DMS-1 (operator-runnable CW query template)
