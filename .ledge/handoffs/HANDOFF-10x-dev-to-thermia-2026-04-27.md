---
type: handoff
status: ATTESTED-PENDING-THERMIA
handoff_type: implementation
schema_version: 1
originating_rite: 10x-dev
receiving_rite: thermia
fallback_rite: sre

originating_session: session-20260427-154543-c703e121
authored_on: 2026-04-27
authored_by: principal-engineer
worktree: .worktrees/active-mrr-freshness/
branch: feat/active-mrr-freshness-signal

initiative_slug: verify-active-mrr-provenance
prd_anchor: .ledge/specs/verify-active-mrr-provenance.prd.md
tdd_anchor: .ledge/specs/handoff-dossier-schema.tdd.md
adr_anchor: .ledge/decisions/ADR-002-rite-handoff-envelope-thermia.md

attestation_required: true
attestation_chain: "thermia.verification-auditor (primary), sre.incident-commander|observability-engineer (fallback)"
verification_deadline: 2026-05-27

design_references:
  - .ledge/specs/verify-active-mrr-provenance.prd.md
  - .ledge/specs/freshness-module.tdd.md
  - .ledge/specs/handoff-dossier-schema.tdd.md
  - .ledge/decisions/ADR-002-rite-handoff-envelope-thermia.md

index_entry_appended: true
---

# HANDOFF — 10x-dev → thermia (verify-active-mrr-provenance)

This dossier transfers the cache-architecture concerns deferred from PRD `verify-active-mrr-provenance` (D5, D7, D10, telos verified-realized gate per D8) from the originating 10x-dev rite to the receiving thermia rite. Sre is the documented fallback per the activation predicate in `.ledge/specs/handoff-dossier-schema.tdd.md` §5.

The 10x-dev rite has shipped the freshness-signal feature (commits `09cc368e` + `ce565759`) and validated it via in-anger-dogfood probes against the `autom8-s3` production cache bucket (recorded in the QA verdict at `.ledge/reviews/QA-T9-verify-active-mrr-provenance.md` Phase B). The telos `verified_realized` gate cannot be discharged by the originating rite per Axiom 1 critic-rite-disjointness (`external-critique-gate-cross-rite-residency`); discharge is the receiving rite's contribution at or before 2026-05-27.

## 1. Classifier ACTIVE-Section List

The canonical Asana section names that the offer classifier maps to `AccountActivity.ACTIVE` at handoff time:

- active
- restart - request testimonial
- run optimizations

**Source anchor**: `src/autom8_asana/models/business/activity.py:76` — the `sections_for` method definition on `SectionClassifier`. The `CLASSIFIERS` dict that exposes the offer classifier lives at `src/autom8_asana/models/business/activity.py:317`.

**Capture method**: captured at T10 commit time via `python -c 'from autom8_asana.models.business.activity import CLASSIFIERS, AccountActivity; print(CLASSIFIERS["offer"].sections_for(AccountActivity.ACTIVE))'` executed inside the worktree.

**Capture timestamp**: 2026-04-27T14:55:43Z.

## 2. Parquet Section List (as of handoff date)

**Capture command (verbatim)**: `aws s3 ls s3://autom8-s3/dataframes/1143843662099250/sections/ --recursive`

**Capture timestamp**: 2026-04-27T14:55:43Z.

**Row count**: 14 parquet objects.

| section_gid | parquet_path | LastModified | size_bytes |
|---|---|---|---|
| 1143843662099256 | s3://autom8-s3/dataframes/1143843662099250/sections/1143843662099256.parquet | 2026-04-26T10:00:47Z | 13381 |
| 1143843662099257 | s3://autom8-s3/dataframes/1143843662099250/sections/1143843662099257.parquet | 2026-04-27T14:01:10Z | 62414 |
| 1155403608336729 | s3://autom8-s3/dataframes/1143843662099250/sections/1155403608336729.parquet | 2026-03-26T04:17:44Z | 8990 |
| 1199511476245249 | s3://autom8-s3/dataframes/1143843662099250/sections/1199511476245249.parquet | 2026-04-27T10:00:48Z | 12414 |
| 1201105736066893 | s3://autom8-s3/dataframes/1143843662099250/sections/1201105736066893.parquet | 2026-04-22T16:58:35Z | 109102 |
| 1201131323536610 | s3://autom8-s3/dataframes/1143843662099250/sections/1201131323536610.parquet | 2026-04-20T20:26:43Z | 11051 |
| 1201990715810461 | s3://autom8-s3/dataframes/1143843662099250/sections/1201990715810461.parquet | 2026-04-20T15:00:28Z | 9551 |
| 1201990715810462 | s3://autom8-s3/dataframes/1143843662099250/sections/1201990715810462.parquet | 2026-04-09T13:44:45Z | 8894 |
| 1202005604742382 | s3://autom8-s3/dataframes/1143843662099250/sections/1202005604742382.parquet | 2026-04-12T06:00:27Z | 15610 |
| 1202496785025459 | s3://autom8-s3/dataframes/1143843662099250/sections/1202496785025459.parquet | 2026-04-25T18:00:53Z | 11840 |
| 1204152425074370 | s3://autom8-s3/dataframes/1143843662099250/sections/1204152425074370.parquet | 2026-04-03T20:42:29Z | 2449 |
| 1207396100287952 | s3://autom8-s3/dataframes/1143843662099250/sections/1207396100287952.parquet | 2026-04-20T20:26:43Z | 9854 |
| 1208667647433692 | s3://autom8-s3/dataframes/1143843662099250/sections/1208667647433692.parquet | 2026-04-25T18:00:52Z | 11463 |
| 1209233681691558 | s3://autom8-s3/dataframes/1143843662099250/sections/1209233681691558.parquet | 2026-04-09T13:44:45Z | 2449 |

## 3. Per-Section Mtime Histogram (Artifact)

The per-section mtime histogram is authored as a sidecar JSON artifact alongside this dossier:

- **Sidecar path** (relative to worktree root): `.ledge/handoffs/2026-04-27-section-mtimes.json`
- **Reference timestamp `now_iso`** (against which `age_seconds_at_handoff` is computed): 2026-04-27T14:55:43Z

**JSON schema** (per `.ledge/specs/handoff-dossier-schema.tdd.md` §2 Section 3 — array of objects with these four keys per row):

```json
[
  {
    "section_gid": "string",
    "parquet_path": "s3://autom8-s3/dataframes/1143843662099250/sections/{section_gid}.parquet",
    "last_modified_iso": "YYYY-MM-DDTHH:MM:SSZ",
    "age_seconds_at_handoff": 12345
  }
]
```

The sidecar contains 14 rows (one per parquet object listed in §2). Min `age_seconds_at_handoff` = 3273s (newest: `1143843662099257.parquet` @ 2026-04-27T14:01:10Z). Max `age_seconds_at_handoff` = 2803079s (oldest: `1155403608336729.parquet` @ 2026-03-26T04:17:44Z, ≈32d 11h 17m).

## 4. Bucket→Env Stakeholder Affirmation

The bucket→env binding `autom8-s3 = production` rests on a stakeholder-guarantee-affirmation event recorded in the originating session's pre-PRD interview. This dossier carries the affirmation forward verbatim — NO new claims are appended.

**Citation header**:
- source: `session-20260427-154543-c703e121`
- event: pre-PRD interview Q2.2 / D6
- user: `tom@tenuta.io`
- date: 2026-04-27

> "It is. Use the stakeholder guarantee affirmation"

**Cross-reference anchor**: PRD §6 C-1 lines 195-202 contain the structural_verification_receipt formalizing this affirmation. The `marker_token` on that receipt — "Bucket autom8-s3 IS the production cache bucket (stakeholder affirmation by user tom@tenuta.io on 2026-04-27" — establishes the load-bearing evidence cited in `.know/env-loader.md` Stakeholder Affirmation Addendum (lines 160-174).

## 5. cache_warmer Schedule — Open Question (D10)

> What is the trigger and frequency of `src/autom8_asana/lambda_handlers/cache_warmer.py` invocations? What guarantees re-warm of stale sections? What is the documented per-section TTL, if any? Verifiable by inspecting the Lambda's CloudWatch Events / EventBridge rule (or equivalent scheduling primitive) AND by reading the handler's entry-point logic and any per-section TTL gating it implements.

**Anchor**: `src/autom8_asana/lambda_handlers/cache_warmer.py:1` — structural pointer; this sprint did NOT modify the Lambda (PRD C-4).

**Deferral rationale**: PRD D10 + PRD NG7 explicitly defer the cache_warmer schedule and per-section TTL design to thermia. The 10x-dev rite reads cache state but does not own re-warm orchestration.

## 6. Section-Coverage Deferral Rationale (D5)

10x-dev does NOT compute section-coverage. Classifier-vs-parquet diff (this dossier's sections 1 and 2) is a read-only artifact at handoff time only. Telemetry, alerting, and Asana-side drift reconciliation are thermia's domain.

**Empty-sections-are-expected note** — verbatim from PRD §6 C-6 line 222:

> "Empty sections in parquet are EXPECTED behavior, not a coverage gap. Classifier-vs-parquet section count diffs are informational, not failure conditions."

This is structurally correct: per PRD C-4 line 213 the cache_warmer Lambda writes parquet only for sections that contain tasks; an empty section is by-design and is NOT a coverage gap.

**Cross-references**:
- PRD §2 NG5 line 57: section-coverage signal in the freshness output is OUT-OF-SCOPE (deferred entirely to thermia).
- PRD §6 C-6 lines 220-222: empty-sections-are-expected; `--strict` does NOT promote section-count-diff to non-zero exit (per D3).
- PRD §9 D5 line 307: section-coverage diagnostic DEFERRED to thermia.

## 7. Env-Matrix Legacy-Cruft Inventory (D7)

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

**Discovery-only declaration**: This is a discovery-only inventory per Pythia P1 verdict on Concern 2. NO remediation proposal is offered at this altitude. Remediation is thermia's responsibility per PRD D7.

## 8. Telos Handoff and Attester Fallback Condition (D8)

- **Primary attester**: thermia.verification-auditor is the primary rite-disjoint attester.
- **Fallback attester**: sre.incident-commander OR sre.observability-engineer is the fallback iff the thermia rite is not registered in the platform manifest at handoff time, per the fallback activation predicate in `.ledge/specs/handoff-dossier-schema.tdd.md` §5.
- **Verification deadline**: 2026-05-27.
- **PRD telos cross-reference**: PRD §7 telos block (lines 224-263).

**Forward-references**: the empty `## Attester Acceptance` and `## Verification Attestation` headings appended at the end of this dossier body are the receiving rite's insertion points (per `.ledge/specs/handoff-dossier-schema.tdd.md` §4.3 and §4.4).

### 8.1 Latent Decisions Surfaced

The architect phase (T4) surfaced three latent decisions for engineer-discretion disposition (per Pythia P2). The principal-engineer's positions, recorded here for thermia / sre / Potnia visibility:

1. **INDEX.md scope** (TDD §4.5): RECOMMEND merge-time consolidation. At merge-to-main, the worktree's `.ledge/handoffs/INDEX.md` should be merged into the main-branch `.ledge/handoffs/INDEX.md` (creating the directory if absent), and per-worktree INDEX entries appended to a project-wide INDEX. Rationale: a per-rite or per-receiving-rite INDEX would fragment discoverability across the fleet; a single project-wide INDEX matches the established artifact-locality pattern (one `.ledge/decisions/`, one `.ledge/specs/` per repo). Decision holder: Potnia at merge time.
2. **Fallback agent disambiguation** (TDD §5.1): RECOMMEND `sre.observability-engineer` for THIS initiative. Rationale: the verification surface is freshness/SLO-shaped (parquet mtime → staleness threshold → strict-mode promotion), not incident-runbook-shaped. The disambiguation rule "observability-engineer for SLO-shaped, incident-commander for degraded-state response" applies cleanly. Decision holder: the activating sre rite at fallback-predicate firing time.
3. **Sre rite awareness of `cross-rite-handoff` convention** (ADR-002 Negative §1): FLAG as precondition for fallback-path activation. If sre rite agents are unaware of the cross-rite-handoff schema (HANDOFF-* naming, INDEX.md scanning, `## Fallback Activation Record` heading), the fallback path is dormant. Suggested mitigation: a cross-rite-handoff inheritance note in the sre rite's documentation, or a fleet-level discoverability sweep at the next sre-rite onboarding event. Decision holder: sre rite Potnia at activation; not load-bearing for engineer T10 commit.

### 8.2 Pre-Existing Observations Surfaced from QA (T9)

Two pre-existing observations from the T9 QA report (`.ledge/reviews/QA-T9-verify-active-mrr-provenance.md` Defect Summary), surfaced here for thermia visibility — neither is a regression introduced by this initiative; both are candidates for future thermia-shaped consideration when designing the freshness-SLA UX.

1. **MINOR-OBS-1** (pre-existing test flake): `tests/unit/persistence/test_reorder.py::test_property_moves_produce_desired_order` (Hypothesis property test) fails intermittently under xdist parallel execution; passes deterministically in isolation. Pre-existing. NOT a release blocker. Recommendation per QA: file as a test-hygiene ticket; pin Hypothesis seed or mark `@pytest.mark.no_xdist`.
2. **MINOR-OBS-2** (pre-existing UX gap): `load_project_dataframe` at `src/autom8_asana/metrics/__main__.py:234` raises a raw botocore `ClientError(NoSuchBucket)` traceback when `ASANA_CACHE_S3_BUCKET` is set to a non-existent bucket name. The existing exception handler at line 235 catches only `(ValueError, FileNotFoundError)`. The freshness-module's own `AC-4.2 not-found` mapping at `src/autom8_asana/metrics/freshness.py:164-177` is correct, but the upstream bucket-typo case is reached BEFORE the freshness probe. Pre-existing and structurally upstream of T6+T7. Candidate consideration when thermia designs freshness-SLA UX: extend `load_project_dataframe`'s exception surface to map botocore `ClientError(NoSuchBucket)` to a friendly stderr line analogous to AC-4.2.

## Attester Acceptance

## Verification Attestation
