---
type: handoff
status: proposed
engagement_state: PENDING-HYGIENE-ENGAGEMENT
handoff_type: cleanup
schema_version: 1
originating_rite: thermia
receiving_rite: hygiene
fallback_rite: null  # cleanup work is fungible across hygiene-shaped rites
originating_session: session-20260427-185944-cde32d7b
authored_on: 2026-04-27
authored_by: thermia.potnia (orchestration via general-purpose author)
worktree: .worktrees/thermia-cache-procession/
branch: thermia/cache-freshness-procession-2026-04-27
initiative_slug: cache-freshness-procession-2026-04-27
parent_initiative: verify-active-mrr-provenance
prd_anchor: .ledge/specs/verify-active-mrr-provenance.prd.md
attestation_required: false  # cleanup handoff; no attestation chain back to thermia
verification_deadline: null  # hygiene engages on its own cadence
index_entry_appended: true
---

# HANDOFF — thermia → hygiene (cache-freshness-procession-2026-04-27)

This dossier transfers cleanup-shaped concerns surfaced during the thermia cache-freshness procession from the originating thermia rite to the receiving hygiene rite. Three work areas are bundled: (A) D7 env-matrix legacy-cruft remediation (12 file:line items in 5 files); (B) `**/.ledge/*` gitignore amendment to mitigate a recurrence-vector that cost the predecessor 10x-dev sprint approximately 1000+ lines of design-reference artifacts; and (C) MINOR-OBS-1 xdist test-flake disposition.

This is a `handoff_type: cleanup` artifact. Per the cleanup-handoff variant, no attestation chain back to thermia is required (`attestation_required: false`); the hygiene rite engages on its own cadence and records engagement via the empty `## Attester Acceptance` heading at the end of this dossier. There is no `## Verification Attestation` heading because there is no chain-back-to-thermia obligation.

## 1. Cleanup Scope Summary (3 Work Areas)

This dossier carries three discrete cleanup-shaped work areas. Each is independently dispositionable by hygiene; bundling reflects authoring economy, not coupling.

- **Area A — D7 env-matrix legacy-cruft remediation**: 12 file:line items in 5 files (`src/autom8_asana/models/base.py`, `src/autom8_asana/cache/integration/factory.py`, `src/autom8_asana/api/models.py`, `src/autom8_asana/settings.py`). All references to the legacy `AUTOM8Y_ENV` token, which is cruft of an earlier multi-env era. Confirmed cleanup-shaped per heat-mapper P1 Q3.
- **Area B — `**/.ledge/*` gitignore amendment**: recurrence-vector mitigation for the silent gitignore add-skip + worktree-removal-at-wrap interaction that cost the predecessor 10x-dev sprint approximately 1000+ lines of design-reference artifacts (PRD + 2 TDDs + 2 ADRs). Three options surfaced (§5); decision-holder is hygiene.
- **Area C — MINOR-OBS-1 xdist test flake**: `tests/unit/persistence/test_reorder.py::test_property_moves_produce_desired_order` (Hypothesis property test) fails intermittently under xdist parallel execution; passes deterministically in isolation. Pre-existing per parent dossier `.ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md:186`.

## 2. Cache-Irrelevance Verdict (heat-mapper P1 Q3)

The thermia heat-mapper P1 Q3 disposition adjudicated all 12 D7 items against cache-architecture relevance using the 6-gate framework. The verdict, recorded verbatim from `.sos/wip/thermia/heat-mapper-assessment-cache-freshness-2026-04-27.md:308`:

> **D7 disposition confirmed**: All 12 items are cleanup-shaped. No item is cache-architecture-load-bearing. Factory items 3–5 are cache-adjacent but are self-consistent with the existing architecture and carry no freshness-SLA risk. Secondary handoff to hygiene rite is confirmed per SQ-2 presumption. Thermia will produce a structured hygiene handoff dossier containing this 12-item inventory.

**Note on items 3–5 (factory.py)**, recorded verbatim from `.sos/wip/thermia/heat-mapper-assessment-cache-freshness-2026-04-27.md:306`:

> **Note on items 3–5 (factory.py)**: `CacheProviderFactory` uses `AUTOM8Y_ENV` in its auto-detection chain (Tier 4: `AUTOM8Y_ENV=production/staging → Redis if REDIS_HOST set`). This is a cache-architecture-adjacent reference, not a cache-architecture-critical one. The PRD already affirms there is one production bucket, no multi-env buckets. The `AUTOM8Y_ENV` detection in `factory.py` is used to select the Redis vs. InMemory provider for the task-entity cache, not for the parquet DataFrame tier. Replacing it with a simpler `settings.is_production` check (already used at `factory.py:153`) is hygiene-shaped cleanup, not a cache-architecture decision. This does not warrant user adjudication.

**Structural translation for hygiene**: items 3–5 in `src/autom8_asana/cache/integration/factory.py` are cache-ADJACENT — they govern Redis-vs-InMemory tier selection for the task-entity cache — but are NOT load-bearing for parquet/DataFrame freshness (which is the thermia procession's load-bearing surface). Replacement with `settings.is_production` is a single-prod-bucket-affirmation simplification, not a cache-architecture refactor. Hygiene-shaped.

## 3. D7 Inventory (12 Items, Verbatim from Parent Dossier §7)

Reproduced verbatim from `.ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md:138-161` for hygiene-rite consumption.

**Capture command (verbatim)**: `rg -n 'AUTOM8Y_ENV|autom8-s3-(staging|dev|prod)' src/`

**Capture timestamp**: 2026-04-27T14:55:43Z.

**Total match count**: 12.

| file_path | line_number | matched_text |
|---|---|---|
| src/autom8_asana/models/base.py | 14 | `# for test clarity. Controlled via AUTOM8Y_ENV.` |
| src/autom8_asana/models/base.py | 17 | `if os.environ.get("AUTOM8Y_ENV", "production") not in ("test", "local", "LOCAL")` |
| src/autom8_asana/cache/integration/factory.py | 32 | `4. Environment-based auto-detection (AUTOM8Y_ENV)` |
| src/autom8_asana/cache/integration/factory.py | 36 | `- AUTOM8Y_ENV=production/staging: Prefer Redis if REDIS_HOST configured` |
| src/autom8_asana/cache/integration/factory.py | 37 | `- AUTOM8Y_ENV=local/test or not set: Use InMemory` |
| src/autom8_asana/api/models.py | 44 | `if os.environ.get("AUTOM8Y_ENV", "production") not in ("test", "local", "LOCAL")` |
| src/autom8_asana/settings.py | 554 | `# Override autom8y_env with explicit alias so AUTOM8Y_ENV is read directly,` |
| src/autom8_asana/settings.py | 560 | `"AUTOM8Y_ENV",  # canonical (Tier 1)` |
| src/autom8_asana/settings.py | 590 | `with ASANA_CW_ENVIRONMENT to avoid collision with AUTOM8Y_ENV. The env_prefix` |
| src/autom8_asana/settings.py | 801 | `# SDK-standard environment field. AUTOM8Y_ENV is the canonical Tier 1 name.` |
| src/autom8_asana/settings.py | 805 | `"AUTOM8Y_ENV",  # canonical (Tier 1)` |
| src/autom8_asana/settings.py | 845 | `Uses the explicit-only pattern: only fires when AUTOM8Y_ENV` |

(Zero matches against the multi-env bucket pattern `autom8-s3-(staging|dev|prod)`. All 12 matches are `AUTOM8Y_ENV` references.)

Items 3–5 (`src/autom8_asana/cache/integration/factory.py:32`, `:36`, `:37`) are cache-ADJACENT per heat-mapper P1 Q3 (see §2 above) but cleanup-shaped — replacement with `settings.is_production` (already used at `src/autom8_asana/cache/integration/factory.py:153`) is the hygiene-rite's structural recommendation; no cache-architecture decision is required.

## 4. Canary-in-Production Constraint Reference (PRD §6 C-1, Verbatim)

The hygiene rite MUST treat the PRD §6 C-1 constraint as load-bearing during D7 remediation. Re-introducing multi-env logic during cleanup would violate the canary-in-production model the platform has standardized on. PRD §6 C-1 is reproduced verbatim from `.ledge/specs/verify-active-mrr-provenance.prd.md:254-267`:

> - **C-1**: **CANARY-IN-PRODUCTION**. The ecosystem has standardized on a
>   single production cache bucket (`autom8-s3`); there are no multi-env
>   cache buckets. The legacy `AUTOM8Y_ENV` token is cruft of an earlier
>   multi-env era and is scheduled for thermia/hygiene cleanup per D7.
>   Bucket→env binding is established by stakeholder affirmation (D6), NOT
>   by IaC introspection.
>
>   **Structural verification receipt (D6 affirmation)**:
>   - source: `session-20260427-154543-c703e121`
>   - event: pre-PRD interview Q2.2 / D6
>   - user: `tom@tenuta.io`
>   - date: 2026-04-27
>   - marker_token: "Bucket autom8-s3 IS the production cache bucket
>     (stakeholder affirmation by user tom@tenuta.io on 2026-04-27)"

**Hygiene rite constraint**: D7 cleanup is permitted to remove or replace `AUTOM8Y_ENV` references (e.g., with `settings.is_production`) but is NOT permitted to re-introduce multi-env switches (e.g., reintroducing `autom8-s3-staging` or `autom8-s3-dev` bucket name templates). The single-prod-bucket affirmation is the load-bearing premise the freshness-signal feature ships against.

## 5. Gitignore-Fix Proposal (THREE OPTIONS — Hygiene Rite Owns Selection)

The `**/.ledge/*` gitignore pattern at `.gitignore:72-74` and `.gitignore:92-94` (the pattern is duplicated under both the Knossos and KNOSSOS:START infra-ignores blocks) silently swallowed 5 design-reference files in the predecessor 10x-dev sprint: 1 PRD + 2 TDDs + 2 ADRs, totalling approximately 1000+ lines. The artifacts were lost when the 10x-dev worktree was wrap-removed. The thermia procession reconstructed them at P0 pre-flight using `git add -f`, but the recurrence-vector remains for any future rite that authors `.ledge/` artifacts in a worktree.

Three remediation options are surfaced for hygiene-rite adjudication. **Decision-holder is hygiene rite**; thermia does NOT pre-decide here.

**Option A — Subdirectory allow-list amendment**:

Amend `.gitignore:72-74` and `.gitignore:92-94` to allow-list the four canonical `.ledge/` subdirectories that store work-product artifacts:

```
**/.ledge/*
!**/.ledge/shelf/
!**/.ledge/shelf/**
!**/.ledge/specs/
!**/.ledge/specs/**
!**/.ledge/decisions/
!**/.ledge/decisions/**
!**/.ledge/reviews/
!**/.ledge/reviews/**
!**/.ledge/handoffs/
!**/.ledge/handoffs/**
```

Pros: tracks the load-bearing artifact directories by default; eliminates the silent-add-skip recurrence-vector for engineer-authored design refs and handoff dossiers. Cons: requires schema-stability for the four subdirectory names; may need a fifth allow-list rule if `.ledge/spikes/` is added later.

**Option B — Process-level fix (no gitignore change)**:

Enforce `git add -f` for all `.ledge/`-targeted writes in engineer dispatch checklists. No gitignore change. The recurrence-vector remains structurally but is process-mitigated.

Pros: zero gitignore-pattern complexity; preserves existing default-deny posture for unknown `.ledge/` content. Cons: relies on engineer discipline at dispatch time; no structural backstop if checklist is skipped or misread; the predecessor sprint's loss occurred under exactly this regime.

**Option C — Track `.ledge/**` by default**:

Replace the `**/.ledge/*` pattern with a permissive default — only `.ledge/shelf/` (currently allow-listed) gets explicit treatment; everything else under `.ledge/` is tracked.

```
# Knossos
.knossos/
.claude/CLAUDE.md
**/.sos/*
!**/.sos/archive/
!**/.sos/archive/**
# .ledge/ tracked by default; only ephemeral subdirs gitignored as needed
```

Pros: simplest; eliminates the recurrence-vector entirely; matches the conventional default of "track work product unless excluded." Cons: broader change; may capture noise (e.g., scratch artifacts, large diffs, or any future ephemeral subdirectories) that the existing default-deny posture currently filters out.

**Sprint-retro context**: The predecessor 10x-dev sprint LOST 5 design-ref files (~1000+ lines) due to silent gitignore add-skip + worktree-removal-at-wrap interaction. Reconstruction was costly (general-purpose dispatch at thermia P0 pre-flight; cited under the `reconstruction:` block in `.ledge/specs/handoff-dossier-schema.tdd.md:16-27`). The recurrence-vector still exists for any future rite using `.ledge/` artifacts.

**Decision-holder**: hygiene rite. Thermia surfaces the three options + sprint-retro evidence; selection and implementation belong to hygiene.

## 6. MINOR-OBS-1 Disposition

Carried forward verbatim from parent dossier `.ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md:186` and confirmed by thermia heat-mapper P1 Q5 (recorded at `.sos/wip/thermia/heat-mapper-assessment-cache-freshness-2026-04-27.md:312-322`).

- **Symptom**: `tests/unit/persistence/test_reorder.py::test_property_moves_produce_desired_order` (Hypothesis property test) fails intermittently under xdist parallel execution; passes deterministically in isolation.
- **Pre-existing status**: NOT introduced by the cache-freshness-procession or by the predecessor verify-active-mrr-provenance initiative. Pre-existing per parent dossier §8.2 `MINOR-OBS-1`.
- **Cache-architecture relevance**: NONE. The test exercises ordering logic in `src/autom8_asana/persistence/` (reorder semantics), not cache freshness or invalidation. Heat-mapper P1 Q5 verdict at `.sos/wip/thermia/heat-mapper-assessment-cache-freshness-2026-04-27.md:320`: "Not cache-architecture-relevant. The test exercises ordering logic in persistence, not cache freshness or invalidation. The failure mode (xdist scheduling non-determinism with Hypothesis seed) is a test-infrastructure issue."
- **Recommendation (per QA-T9)**: pin Hypothesis seed OR mark `@pytest.mark.no_xdist` on `tests/unit/persistence/test_reorder.py::test_property_moves_produce_desired_order`.
- **Decision-holder**: hygiene rite (test-hygiene engagement). SQ-4 default disposition surfaced this item to hygiene per parent dossier §8.2 default.

## 7. Receipt-Grammar Discipline

This dossier complies with the receipt-grammar discipline carried forward from the parent dossier:

- All inventory anchors are `file:line` (e.g., `src/autom8_asana/cache/integration/factory.py:36`).
- All 12 D7 items have explicit `file_path` + `line_number` citation in §3.
- No aspirational tokens (`should`, `will`, `eventually`, `TODO`, `FIXME`, `[placeholder]`, `[TBD]`) appear in body claims about completed work; the only `should` is bound to verbatim quotes from external authorities (e.g., the schema TDD's recommendations) or to OPTION descriptions in §5 that are explicitly hygiene-decision-pending.
- All capture commands and timestamps in §3 are reproduced verbatim from the parent dossier (no paraphrase).
- Heat-mapper P1 Q3 + Q5 verdicts are quoted verbatim from `.sos/wip/thermia/heat-mapper-assessment-cache-freshness-2026-04-27.md` with file:line citations.
- PRD §6 C-1 is quoted verbatim from `.ledge/specs/verify-active-mrr-provenance.prd.md:254-267`.

## Appendix — Procession Follow-Ups Surfaced Post-Authoring

This appendix collects three procession follow-up concerns surfaced post-authoring of the base dossier (after thermia commit `f66208f2`). They are out-of-scope-for-this-procession and land with the hygiene rite for follow-up. The base dossier (sections 1–7) is unchanged; this appendix is additive.

Provenance: PT-1 Concern 8 FLAG (Appendices A–B); PT-4 Concern 3 FLAG (Appendix C). Authored by 10x-dev session `session-20260427-205201-668a10f4` per T#45 dispatch.

### Appendix A — XC-3: Casing-inconsistency fleet debt (PT-1 Concern 8 FLAG)

ADR-006 (CloudWatch namespace strategy) adopted a dual-namespace decision for cache-freshness emissions:

- `Autom8y/FreshnessProbe` (Pascal) — new CLI freshness-probe metrics
- `autom8y/cache-warmer` (lowercase, existing Terraform-set runtime namespace) — coalescer/warmer metrics, joining existing peers

The casing inconsistency between Pascal `Autom8y/X` and lowercase `autom8y/x` namespaces was inherited intentionally by ADR-006 (`./.ledge/decisions/ADR-006-cloudwatch-namespace-strategy.md:202-206` Rationale §6 "Capitalization is inherited, not unified"). Fleet-wide unification is explicitly out-of-scope for the cache-freshness procession.

**Hygiene-shaped concern**: a casing-cleanup ADR should consider unifying namespaces across the fleet. NOT load-bearing for cache-freshness functionality — every existing alarm, dashboard, and Logs Insights query targeting the current lowercase namespace would invalidate on rename (per ADR-006 Alternatives §"REJECTED: Unified namespace casing", `./.ledge/decisions/ADR-006-cloudwatch-namespace-strategy.md:266-276`).

**Discovery-only inventory** (file:line anchors; no remediation proposal):

| # | Anchor | Namespace declared | Casing |
|---|---|---|---|
| 1 | `src/autom8_asana/lambda_handlers/cache_warmer.py:70` | `Autom8y/AsanaCacheWarmer` (DMS namespace constant `DMS_NAMESPACE`) | Pascal |
| 2 | `src/autom8_asana/lambda_handlers/cache_warmer.py:20` | `autom8/cache-warmer` (docstring default for `CLOUDWATCH_NAMESPACE` env var — note: missing trailing 'y' in `autom8` is itself a separate inconsistency from the env-var-set value) | lowercase |
| 3 | `terraform/services/asana/main.tf:265` (autom8y repo) | `ASANA_CW_NAMESPACE = "autom8y/cache-warmer"` (the `service-lambda-scheduled` module sets this env var on the deployed Lambda — discovery-only — no remediation proposal) | lowercase |
| 4 | `src/autom8_asana/metrics/cloudwatch_emit.py:40` | `FRESHNESS_PROBE_NAMESPACE: str = "Autom8y/FreshnessProbe"` | Pascal |
| 5 | `terraform/services/asana/main.tf:419` (autom8y repo, per ADR-006 §Context) | `autom8y/unit-reconciliation` (unit-reconciliation Lambda) — discovery-only — no remediation proposal | lowercase |

(Six-plus Pascal `Autom8y/...` vs lowercase `autom8y/...` namespaces across the fleet; full inventory pending hygiene-rite scan — discovery-only — no remediation proposal.)

**Decision-holder**: hygiene rite at follow-up procession.

### Appendix B — XC-4: schema_version=1 forward-author cooperation discipline (PT-1 Concern 8 FLAG)

ADR-005 (`./.ledge/decisions/ADR-005-ttl-manifest-schema-and-sidecar.md:206-262`) declared `schema_version: 1` for the TTL manifest YAML + S3 sidecar JSON, with an explicit additive-evolution contract (V-1 validator rule + the "Additive evolution" subsection):

- Additive changes (new optional fields, new top-level keys) MUST NOT bump `schema_version`.
- Breaking changes (required-field addition, type change, enum-value removal, override-precedence rule change) MUST bump `schema_version` and MUST be ratified by a successor ADR.

The contract works ONLY if subsequent schema-touching ADRs honor the rule. No machine-enforced bump-detection currently exists; the validator at the engineer-chosen module emits the rule verbatim in its docstring (per ADR-005 Consequences §Negative, `./.ledge/decisions/ADR-005-ttl-manifest-schema-and-sidecar.md:450-453`) as a permanent reminder, but reminder-only.

**Discovery-only — no remediation proposal**: this is a process-discipline gap, not a code defect. The ADR-005 contract is internally consistent; the gap is that future schema-touching authors may inadvertently breach the rule without mechanical detection.

**Suggested mitigation pathways** (hygiene rite chooses; this appendix surfaces, does not pre-decide):

- (i) **ADR-template addendum**: any ADR touching a `schema_version`'d artifact MUST include a "schema-bump rationale" subsection citing whether the change is additive (no bump) or breaking (bump + cite predecessor ADR). Lowest-cost, highest-discipline-dependence.
- (ii) **Schema-validator extension**: machine-enforced bump-detection on schema field changes. The validator (per ADR-005 §Validation contract) reads `schema_version` at parse time; an extension could compare declared version against a structural hash of the schema and emit a CI-time warning on mismatch.
- (iii) **Out-of-band linter / pre-commit hook**: detects schema-touching changes (any diff to ADR-005's schema definitions or to validator V-1 through V-6 rules) and flags the PR for a bump-rationale review. Highest-cost, lowest-discipline-dependence.

**Anchors**:
- `./.ledge/decisions/ADR-005-ttl-manifest-schema-and-sidecar.md:206-209` (V-1 validator rule)
- `./.ledge/decisions/ADR-005-ttl-manifest-schema-and-sidecar.md:240-262` ("Additive evolution" subsection)
- `./.ledge/decisions/ADR-005-ttl-manifest-schema-and-sidecar.md:450-453` (Consequences §Negative — "Schema version field discipline depends on future ADRs respecting it")

**Decision-holder**: hygiene rite.

### Appendix C — ALERT-3 + ALERT-5 ownership clarification (PT-4 Concern 3 FLAG)

P4 observability spec (`./.ledge/specs/cache-freshness-observability.md`) §3 declared six alerts. ADR-006 (`./.ledge/decisions/ADR-006-cloudwatch-namespace-strategy.md`) Decision §"Alarm-vs-metric matrix" closed alarm-vs-metric questions for the six new metric emissions but did not re-decide the existing-fleet alarms for ALERT-3 and ALERT-5. Disposition table:

| Alert | Metric | Status (post-Batch-D) | Anchor |
|---|---|---|---|
| ALERT-1 | `MaxParquetAgeSeconds` (`> 21600`, single eval, P2 WARNING) | Wired (alarm definition stashed for Batch-D) | `./.ledge/specs/cache-freshness-observability.md:159-181` |
| ALERT-2 | `MaxParquetAgeSeconds` (`> 21600` for 30 min, P1 CRITICAL) | Wired (alarm definition stashed for Batch-D) | `./.ledge/specs/cache-freshness-observability.md:184-205` |
| ALERT-3 | `WarmFailure ≥ 1/hr` (entity_type=offer) | UNCLEAR — see open question 1 below | `./.ledge/specs/cache-freshness-observability.md:209-231` |
| ALERT-4 | DMS heartbeat absent (24h) | Wired via Batch-B Path B (Terraform alarm stashed) | `./.ledge/specs/cache-freshness-observability.md:235-256` |
| ALERT-5 | `FreshnessError ≥ 2/hr` | UNCLEAR — see open question 2 below | `./.ledge/specs/cache-freshness-observability.md:260-272` |
| ALERT-6 | `SectionCoverageDelta` informational | NO ALARM per C-6 hard constraint (mechanically enforced by `c6_guard_check()`) | `./.ledge/specs/cache-freshness-observability.md:276-278` |

**Open questions for hygiene rite to clarify** (verifiable predicates):

1. **ALERT-3 ownership**: Does ALERT-3 consume an existing fleet metric (`WarmSuccess`/`WarmFailure` emitted at `src/autom8_asana/lambda_handlers/cache_warmer.py:473` and `src/autom8_asana/lambda_handlers/cache_warmer.py:501`), and if so, is the alarm authored elsewhere in fleet IaC (e.g., the autom8y repo's `terraform/services/asana/main.tf` `service-lambda-scheduled` module's existing `lambda_errors` alarm)? Verifiable predicate: `grep -rn "WarmFailure\|lambda_errors" terraform/` in the autom8y repo OR an explicit "no such alarm exists" finding from hygiene-rite IaC scan.

2. **ALERT-5 ownership**: Is ALERT-5 a thermia-followup-procession concern, or hygiene-shaped, or in-scope for the cache-freshness procession but missed? Context: the `FreshnessError` exception class exists at `src/autom8_asana/metrics/freshness.py:32` (with `KIND_AUTH`/`KIND_NOT_FOUND`/`KIND_NETWORK`/`KIND_UNKNOWN` discriminators); the emission pathway for a `FreshnessErrorCount` CloudWatch metric (per P4 spec §3 ALERT-5 emission path, `./.ledge/specs/cache-freshness-observability.md:268`) is not yet wired; the alarm is not authored. Verifiable predicate: search for `FreshnessErrorCount` emission site in `src/autom8_asana/metrics/cloudwatch_emit.py` OR `src/autom8_asana/metrics/__main__.py` — absence is the load-bearing finding.

**Decision-holder**: hygiene rite (or thermia if reclassified at P7).

**Receipt-grammar discipline**: every claim in this appendix carries a `file:line` anchor or an explicit "discovery-only — no remediation proposal" tag. No aspirational tokens (`should`, `will`, `eventually`, `TODO`, `FIXME`, `[placeholder]`, `[TBD]`) in body claims about completed work; the only `should` is bound to suggested mitigation pathways in Appendix B which are explicitly hygiene-decision-pending.

## Attester Acceptance
