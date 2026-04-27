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

## Appendix B — POST-P7.A DRIFT items (added 2026-04-27 by thermia.thermal-monitor)

Three SPEC/DOC drift items surfaced by the lens-3 cross-check (heat-mapper) and live AWS predicate execution at P7.A.3 of the thermia procession `cache-freshness-procession-2026-04-27`. All three are TELOS-ADJACENT (affect lens-3 observability-completeness operator-traceability). None blocks Track A close; all are filed to hygiene rite for spec/doc patching (no code changes required).

Source artifacts:
- `.ledge/reviews/P7A-cross-check-lens3-observability-2026-04-27.md`
- `.ledge/reviews/P7A-alert-predicates-2026-04-27.md` (live AWS evidence)
- `.ledge/reviews/P7A-track-A-close-2026-04-27.md` §3

### B.1 DRIFT-1 — P4 ALERT-3 namespace mis-spec

**Affected file**: `.ledge/specs/cache-freshness-observability.md` §3.3 (and §A.4 ALERT-3 row in dossier).

**Drift**: P4 spec claims ALERT-3 (`WarmFailure` >= 1/hr, `entity_type=offer`) lives in namespace `autom8y/cache-warmer`. Live AWS scan (P7.A.3 PRED-3..5) confirms the actual failure metric is `autom8/lambda::StoryWarmFailure` (pre-existing warmer Lambda metric). Namespace `autom8y/cache-warmer` contains ONLY `CoalescerDedupCount` (per ADR-006, emitted from `coalescer.py:34-67`); does NOT contain a `WarmFailure` metric.

**Resolution path**:
1. Patch P4 spec §3.3 ALERT-3 row: change namespace `autom8y/cache-warmer` → `autom8/lambda`; metric name `WarmFailure` → `StoryWarmFailure` (plus dimension `entity_type=offer` if such dimension exists on the existing emit; if not, a new emit-side dimension or alarm-without-dimension scope clarification).
2. Author **ADR-007** as a follow-up to ADR-006: differentiate the three production CW namespaces — `Autom8y/FreshnessProbe` (CLI-side, Pascal case), `autom8y/cache-warmer` (coalescer dedup), `autom8/lambda` (warmer-side StoryWarm{Success,Failure,Duration}). ADR-006 currently overgeneralizes to a 2-namespace model.
3. Update Batch-D Terraform (when authored) to reference the correct namespace+metric per the patched spec.

**Owner**: hygiene rite (or thermia rite via secondary cycle if Batch-D timing forces).

### B.2 DRIFT-2 — Runbook DMS-1 metric-name placeholder

**Affected file**: `.ledge/specs/cache-freshness-runbook.md` (Stale-2 / DMS-1 section, around line 239 per heat-mapper C-2).

**Drift**: Runbook DMS-1 Step 1 contains literal placeholder `[DMS_METRIC_NAME]`. A paged operator cannot execute the recommended CloudWatch query without consulting `autom8y_telemetry` package source. This **fails lens-3 observability-completeness criterion** ("operator can answer from telemetry alone without source code knowledge").

**Resolution path**:
Replace the `[DMS_METRIC_NAME]` placeholder with the explicit CloudWatch query template:

```bash
aws cloudwatch get-metric-statistics \
  --namespace autom8/lambda \
  --metric-name StoryWarmSuccess \
  --start-time $(date -u -d "24 hours ago" +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum
```

Result `Sum < 1` over the 24h window = DMS heartbeat failure = ALERT-4 fires.

**Owner**: hygiene rite (1-line patch; trivial diff).

### B.3 DRIFT-3 — P4 ALERT-5 over-claim

**Affected file**: `.ledge/specs/cache-freshness-observability.md` §3.3 (ALERT-5 row).

**Drift**: P4 spec specifies ALERT-5 (`FreshnessError` >= 2/hr) as a CloudWatch metric alarm. Implementation (WI-8 at `__main__.py:738-780`) emits the FreshnessError condition only as STDERR friendly lines, NOT as a CloudWatch metric (`FreshnessErrorCount` does NOT exist in `Autom8y/FreshnessProbe` namespace per P7.A.3 PRED-2). Acceptance §A.4 already adjudicated this as ACCEPTED present implementation; spec needs to catch up.

**Resolution path**:
Patch P4 spec ALERT-5 row to reframe as a CloudWatch Logs Insights query rather than a metric alarm. Sample reframe:

> ALERT-5: CloudWatch Logs Insights query against the CLI-host log group, filter pattern `[FreshnessError]`, threshold `>=2 occurrences in 1h`, alarm-via-LogsInsights-scheduled-query.

Alternatively (DEFERRED for future procession; NOT immediate): add `FreshnessErrorCount` CW metric with `kind` dimension (mapping to the 6 botocore branches in WI-8) and re-instate metric alarm. This requires code change; out of hygiene rite scope.

**Owner**: hygiene rite (spec patch only, current scope); future procession owner for code-level remediation if production volume warrants the upgrade.

### B.4 Process notes (no action required)

- **FLAG-5 carry-forward**: thermia worktree's `.claude/agents/` shows hygiene agents (worktree-config staleness from when worktree was last touched while hygiene was engaged). Recordable for future `/hygiene` cycle. Main-repo `.claude/agents/` is the active-dispatch ground truth — verifiable via `ari rite current`.
- **MINOR-OBS-1** (xdist test flake at `tests/unit/persistence/test_reorder.py::test_property_moves_produce_desired_order`): unchanged from original Appendix scope. NOT in P7 scope.

### B.5 Receipts

- Track A close commit (carrying this appendix): see thermia branch `thermia/cache-freshness-procession-2026-04-27` after this commit.
- Verification Attestation §V.3 in `HANDOFF-10x-dev-to-thermia-2026-04-27.md` cross-references this appendix as the resolution surface.
- Live AWS evidence basis: `.ledge/reviews/P7A-alert-predicates-2026-04-27.md` PRED-1..PRED-11 (account `696318035277`).

## Attester Acceptance

**Acceptance verdict**: ACCEPTED.
**Engaging rite**: hygiene (PRIMARY; mechanically verified — `ari rite current` returns `Active Rite: hygiene`; main-repo `.claude/agents/` contains 5 hygiene agents `potnia`, `code-smeller`, `architect-enforcer`, `janitor`, `audit-lead`).
**Engagement timestamp**: 2026-04-27T~21:30Z (UTC).
**Engaging session**: continues thermia procession session `session-20260427-185944-cde32d7b` (cache-freshness-procession-2026-04-27 parent procession; cross-rite-handoff is rite-switch, not session-restart, since hygiene work is in-service of the same parent telos discharge).
**Receiving worktree**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.worktrees/thermia-cache-procession` (for Appendix B DRIFT items touching `.ledge/specs/` and `.ledge/decisions/`); main repo `/Users/tomtenuta/Code/a8/repos/autom8y-asana` (for Area A `src/` cleanup, Area B `.gitignore` amendment, Area C `tests/` seed-pinning).

### H.1 Inbound bundle acknowledgment

Four scope areas accepted:

- **Area A** — D7 env-matrix legacy-cruft remediation (12 file:line items in 5 files: `models/base.py`, `cache/integration/factory.py`, `api/models.py`, `settings.py`).
- **Area B** — `**/.ledge/*` gitignore amendment (3 OPTIONS surfaced; hygiene rite owns selection).
- **Area C** — MINOR-OBS-1 xdist test flake (`test_reorder.py::test_property_moves_produce_desired_order`).
- **Appendix B** — POST-P7.A DRIFT items (DRIFT-1 P4 ALERT-3 namespace; DRIFT-2 Runbook DMS placeholder; DRIFT-3 P4 ALERT-5 spec reframe).

### H.2 Engagement flow (Potnia-dispatched plan to follow)

The hygiene rite engages in two independently-shippable workstreams:

- **Workstream 1 — Procession-completion**: Appendix B (DRIFT-1, DRIFT-2, DRIFT-3) — touches `.ledge/specs/cache-freshness-observability.md`, `.ledge/specs/cache-freshness-runbook.md`, and authors `.ledge/decisions/ADR-007-cw-namespace-tri-partition.md`. All on thermia branch `thermia/cache-freshness-procession-2026-04-27`. Tightens design substrate before Batch-D Terraform authoring.
- **Workstream 2 — Repo hygiene**: Areas A + B + C — touches `src/`, `.gitignore`, `tests/`. Lands on a new branch off main (`hygiene/cache-cleanup-2026-04-27` proposed) as separate PR(s).

Workstream 1 is sequenced FIRST since Batch-D Terraform authoring is operator-paced and benefits from corrected spec substrate. Workstream 2 is parallel-safe and lands independently.

### H.3 Workstream 2 Option-B selection bias (gitignore)

For §5 gitignore-fix Option selection, hygiene rite's working preference is **Option C** (track `.ledge/**` by default, only `.ledge/shelf/` allow-listed if needed). Rationale:

- Eliminates the recurrence-vector entirely (matches "track work product unless excluded" convention).
- The cost (broader change) is mitigated by the demonstrated pattern across recent commits: `.ledge/handoffs/`, `.ledge/decisions/`, `.ledge/reviews/`, `.ledge/specs/` are all now load-bearing canonical work-product directories.
- The 5-design-ref loss in the predecessor 10x-dev sprint occurred under the regime that Option B (process-level fix) preserves.
- Option A's per-subdirectory allow-list requires schema-stability for 4-5 subdirectory names; future additions (e.g., `.ledge/spikes/`) require gitignore amendments — friction Option C avoids.

Final selection deferred to architect-enforcer review per hygiene-rite proper convention; H.3 records the receiving rite's working bias for transparency.

### H.4 Workstream 1 spec-patch sequencing

Within Workstream 1 (Appendix B), sequencing:

1. **DRIFT-2** (Runbook DMS-1 placeholder) — 1-line patch, lowest blast radius, quickest to land.
2. **DRIFT-1** (P4 ALERT-3 namespace + ADR-007) — spec patch + ADR authoring; requires architect-enforcer planning.
3. **DRIFT-3** (P4 ALERT-5 spec reframe) — bundles with DRIFT-1 since both touch P4 spec §3.3.

ADR-007 amends ADR-006 (CW namespace strategy). Required because ADR-006 currently overgeneralizes to a 2-namespace model (`Autom8y/FreshnessProbe` + `autom8y/cache-warmer`) but live AWS scan (P7.A.3 PRED-1..11) confirms a 3-namespace reality including `autom8/lambda` for warmer-side metrics. ADR-007 author: architect-enforcer.

### H.5 MINOR-OBS-1 disposition (Area C)

Per §6 recommendation: pin Hypothesis seed OR `@pytest.mark.no_xdist`. Hygiene rite's working preference: **`@pytest.mark.no_xdist`** marker (cleaner; preserves Hypothesis's exploratory property-test value; isolates the schedule-non-determinism root cause). Final selection deferred to janitor's execution-time judgment.

### H.6 Cross-rite ownership clarifications (preserved from §A.7 ownership FLAGs)

Two items from earlier parent appendix ownership-FLAG carry-forward (XC-3 namespace casing debt, XC-4 schema_version discipline) — RESOLVED by P7.A.3 live AWS evidence:

- **XC-3** namespace casing — RESOLVED via P7.A.3 PRED-2 (`Autom8y/FreshnessProbe` Pascal vs `autom8y/cache-warmer` lowercase vs `autom8/lambda` lowercase). 3-tier namespace is empirically correct; ADR-007 documents the tri-partition (Workstream 1 DRIFT-1 scope).
- **XC-4** schema_version discipline — DEFER-FOLLOWUP (not in current hygiene scope; ADR-007 sets the precedent for future namespace ADRs).

### H.7 Pythia touchpoint disposition

Hygiene rite engages without a fresh Pythia touchpoint at acceptance (the hygiene workflow does not have rite-internal Pythia cadence equivalent to thermia's PT-A1..A5). The procession-level Pythia consciousness chain remains intact via the thermia procession's PT-A4/A5 schedule; hygiene work is filed as a procession-side discharge, not a fresh sprint.

### H.8 Receipts

- Acceptance authored by hygiene rite at: 2026-04-27T~21:30Z.
- Inbound dossier prior commits on thermia branch: `f66208f2` (P5b initial), `5323d0bf` (XC-3/XC-4/ALERT-3/5 appendix), `dba50f8a` (Appendix B P7.A DRIFT items).
- Acceptance commit (this artifact): authored on thermia branch `thermia/cache-freshness-procession-2026-04-27` with `git add -f` (gitignore `**/.ledge/*` workaround; same scar that motivates Workstream 2 Area B).
