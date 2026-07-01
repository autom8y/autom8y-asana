---
type: handoff   # shelf-discoverability; cross-rite-handoff schema status (below) remains authoritative
artifact_id: HANDOFF-rnd-to-10x-dyn-enum-contract-2026-06-30
schema_version: "1.0"
source_rite: rnd
target_rite: 10x-dev
handoff_type: implementation
priority: high
blocking: false   # rnd spike is complete; the spike closes regardless of target response
initiative: Dynamic Enum-Option-Set Sync Contract (dyn-enum-contract)
created_at: 2026-06-30T00:00:00Z
status: pending

source_artifacts:
  - .ledge/spikes/SCOUT-dyn-enum-contract.md
  - .ledge/spikes/INTEGRATE-dyn-enum-contract.md
  - .ledge/spikes/PROTO-dyn-enum-contract.md
  - .ledge/spikes/MOONSHOT-dyn-enum-contract.md
  - .ledge/spikes/TRANSFER-dyn-enum-contract.md
  - .sos/wip/spikes/dyn-enum-contract/canary1_fk_parent.py
  - .sos/wip/spikes/dyn-enum-contract/canary2_empty_publish.py

provenance:
  - { source: ".ledge/spikes/TRANSFER-dyn-enum-contract.md", type: artifact, grade: moderate }
  - { source: ".ledge/spikes/MOONSHOT-dyn-enum-contract.md", type: artifact, grade: moderate }
  - { source: ".ledge/spikes/PROTO-dyn-enum-contract.md", type: artifact, grade: moderate }
  - { source: ".know/telos/gfr-dynvocab.md", type: artifact, grade: moderate }
  - { source: ".sos/wip/spikes/dyn-enum-contract/canary1_fk_parent.py", type: code, grade: moderate }
  - { source: ".sos/wip/spikes/dyn-enum-contract/canary2_empty_publish.py", type: code, grade: moderate }
evidence_grade: moderate

tradeoff_points:
  - attribute: "fan-out scalability"
    tradeoff: "single-producer PUSH chosen over a registry/pull topology"
    rationale: "reversible waypoint (Option B at cardinality 1); registry is a one-way door held DEFER until the N>=3 trigger"
  - attribute: "completeness (vocabulary retirement)"
    tradeoff: "additive-only / DELETE-forbidden trades the ability to hard-remove options for FK-parent referential safety"
    rationale: "verticals is an FK-parent (43,057 asset_verticals rows); DELETE orphans children — proven unsafe (canary1_fk_parent.py:389-393)"
  - attribute: "coupling"
    tradeoff: "a NEW /vocabularies/sync endpoint over extending /account-status/sync"
    rationale: "extra=forbid makes a new field on the existing contract BREAKING (BC-1, _account_status_sync.py:67,102)"

items:
  - id: IMP-001
    summary: "Build the per-instance additive-upsert vocab-sync contract (Asana live enum_options -> autom8y-data verticals), compose-up-ready. Moonshot M0."
    priority: high
    estimated_effort: "~6.5 person-days build + sprint-0 entry-criteria resolution"
    design_references:
      - ".ledge/spikes/TRANSFER-dyn-enum-contract.md#3-production-gap-analysis--requirements"
      - ".ledge/spikes/INTEGRATE-dyn-enum-contract.md#integration-approach (Option A)"
      - ".sos/wip/spikes/dyn-enum-contract/canary1_fk_parent.py:182-201 (additive-upsert mechanism, REFERENCE ONLY)"
      - ".sos/wip/spikes/dyn-enum-contract/canary2_empty_publish.py:134-190 (hard-refuse guard, REFERENCE ONLY)"
    acceptance_criteria:
      - "[FR-001] NEW POST /api/v1/vocabularies/sync (generic plural path, field_key discriminator='vertical', extra=forbid, S2S, rate-limit, fleet envelopes); rejects unknown fields 422; is NOT a modification of /account-status/sync (BC-1)"
      - "[FR-002] cross-service key is normalize(option.name)->vertical_key; no enum_option.gid or vertical_id persisted as key; whitespace/case-variant name round-trips to the same key on both sides"
      - "[FR-003] vocab_upsert: INSERT new keys, UPDATE name/enabled on existing, NEVER DELETE; staging test confirms existing ids preserved, new key inserted, campaigns/asset_verticals/offers references still resolve"
      - "[FR-004] hard-refuse guard replaces the leaf guard for the vocab path: empty->REFUSE+ALERT, missing any FK-referenced key->REFUSE+ALERT, healthy full set->PASS; coverage query unions 3 FK edges INCLUDING offers.category string-edge"
      - "[FR-005] producer reads CustomFieldsClient.get(vertical_cf_gid).enum_options (not hardcoded valid_values); creds via AWS Secrets Manager autom8y/asana/asana-pat; flag-gated; deploy-gate asserts first real publish lands"
      - "[FR-006] drift observer emits WARN + metric only; zero auto-mutation; no codegen-from-model; no phantom-mint (ADR-S4-001)"
      - "[FR-007] name-uniqueness guard: UPDATE name only when non-colliding; collision -> per-row WARN + refuse-the-row; verticals.vertical_name unique=True honored"
      - "[NFR-001] single-writer-per-field_key via transaction-scoped advisory lock; different field_keys + readers not blocked; lock releases at txn end"
      - "[NFR-002] idempotent no-op-suppressing upsert; re-running an identical publish touches zero rows"
      - "[NFR-003] S2S JWT + rate-limit + x-fleet-* envelopes on the new endpoint (parity with account_status.py:41,66-70,85)"
      - "[NFR-004] structured JSON logging (no print); publish-count canary metric; deploy-gate assertion against ship-dark"
    notes: "Mechanism is spike-PROVEN two-sided (canary1_fk_parent.py:389-393; canary2_empty_publish.py:328-332). Prototype code is REFERENCE ONLY — reimplement against production contracts. The two CRITICAL gaps are G2 (DB engine, see EC-1) and G6 (vocab_upsert is genuinely new code)."
    dependencies: []

  - id: IMP-002
    summary: "First-sync reconciliation dry-run + schema-discovery re-point to live enum_options. Moonshot M1 (gated on M0 convergence + a consumer-compat check)."
    priority: medium
    estimated_effort: "~1.5 person-days (within the 6.5 total)"
    design_references:
      - ".ledge/spikes/MOONSHOT-dyn-enum-contract.md#rr3 (first-sync reconciliation)"
      - ".ledge/spikes/MOONSHOT-dyn-enum-contract.md#42-sequenced-retirement (M1)"
      - ".ledge/spikes/INTEGRATE-dyn-enum-contract.md (resolver_schema.py:366 asana_configured door)"
    acceptance_criteria:
      - "[FR-008] read-only first-sync dry-run classifies each option MATCH/INSERT-CANDIDATE/ORPHAN-RISK; first real sync REFUSED on any ORPHAN-RISK; emits a reconciliation report; mutates nothing"
      - "[FR-009] schema-discovery values_source:'asana_configured' serves live options; reversible config flip; consumer-compat verified before flip (EC-4)"
    notes: "M1 is gated: enter only after M0 shows clean #4<->#6 convergence and the EC-4 consumer-compat check passes."
    dependencies: ["IMP-001"]
---

# HANDOFF: rnd -> 10x-dev — Dynamic Enum-Option-Set Sync Contract

## Context

A five-wave rnd /spike (scout TRIAL -> integration FK-parent correction -> prototype GO -> moonshot Option F /
DEFER-1 -> this transfer) established the feasibility of contractualizing a dynamic relationship to Asana
custom-field enum-OPTION-SETS that "syncs in" to the sibling `autom8y-data` service. The mechanism is
**spike-PROVEN** via two two-sided discriminating canaries with captured output
(`.sos/wip/spikes/dyn-enum-contract/canary1_fk_parent.py:389-393` and
`.sos/wip/spikes/dyn-enum-contract/canary2_empty_publish.py:328-332`). The production contract is **NOT YET
BUILT**: this HANDOFF transfers a CONDITIONAL GO for a fresh build, not a refactor of prototype code.

The build is a per-instance contract: `autom8y-asana` reads its OWN live Asana `enum_options`, projects a
typed snapshot keyed on the portable option NAME (`vertical_key`), and pushes it to `autom8y-data`, which
**upserts additively** onto its FK-parent `verticals` table (insert-new / update-name-enabled / never delete).
It composes a production idiom the team already runs at N>=2 (account-status + gid-mappings), corrected from
snapshot-replace to additive-upsert because the target is an FK-parent dimension, not a leaf store.

## Evidence Partition (Gate-C discipline)

Per `telos-integrity-ref` §3 Gate C, claim tokens carry per-item receipts. This HANDOFF rigorously separates
**spike-PROVEN** (the mechanism, with canary + captured-output receipts) from **NOT-BUILT** (the entire
production contract, expressed as requirements, never as completion claims).

- **Spike-PROVEN**: additive-upsert preserves FK integrity where snapshot-replace orphans children — two-sided
  canary with teeth (`.sos/wip/spikes/dyn-enum-contract/canary1_fk_parent.py:389-393`; captured verdicts
  `.ledge/spikes/PROTO-dyn-enum-contract.md:126,152,164`).
- **Spike-PROVEN**: the FK-parent hard-refuse guard discriminates empty/truncated reads from healthy ones,
  replacing the leaf-calibrated empty guard at `src/autom8_asana/services/gid_push.py:514-519` — two-sided
  canary with teeth (`.sos/wip/spikes/dyn-enum-contract/canary2_empty_publish.py:328-332`; captured verdicts
  `.ledge/spikes/PROTO-dyn-enum-contract.md:227,249,281`).
- **NOT-BUILT (requirements, not claims)**: the `vocab_upsert` store, the `/vocabularies/sync` endpoint, the
  drift observer, the live-Asana read, and the reconciliation dry-run are specified in IMP-001/IMP-002
  acceptance criteria; none is asserted as shipped/verified.
- **NO production telos exists** for this initiative: `.know/telos/dyn-enum-contract.md` is absent (verified).
  No user-visible outcome is declared and none is attested. `[UNATTESTED — DEFER-POST-HANDOFF | defer-watch:
  dyn-enum-contract/EC-3-telos-frame]` — see Telos note below.

## Production Gaps (transferred from TRANSFER §3.1)

Severity-rated; two are CRITICAL, which is why the verdict is CONDITIONAL GO (never unconditional). Full
table with effort + impact-if-unaddressed at `.ledge/spikes/TRANSFER-dyn-enum-contract.md#31-production-gap-analysis`.

| Gap | Severity | One-line |
|-----|----------|----------|
| G2 DB engine UNRESOLVED | **CRITICAL** | determines upsert syntax + lock primitive; resolve at EC-1 before build |
| G6 vocab_upsert store | **CRITICAL** | genuinely new code; snapshot-replace orphans 43,057 FK rows (`_advertising.py:326`) |
| G1 live Asana read | HIGH | offline fixture -> `CustomFieldsClient.get`; AWS Secrets Manager creds |
| G3 coverage query | HIGH | must include `offers.category` string-edge (`_platform.py:162`) |
| G5 consumer endpoint | HIGH | NEW endpoint; extending account-status is BREAKING (BC-1) |
| G9 concurrency + name-collision | HIGH | advisory lock + `vertical_name` unique=True guard (`_platform.py:147`) |
| G10 first-sync reconciliation | HIGH | read-only dry-run; refuse on ORPHAN-RISK |
| G13 no telos / frame | HIGH (process) | user-sovereign `/frame` is the entry gate (EC-3) |
| G4/G7/G11/G12 | MEDIUM | transport, drift observer, disabled-option policy, schema-discovery re-point |
| G8 logging | LOW | structured logging + canary metric |

## Non-Negotiable Constraints (what MUST NOT change)

The receiving rite must preserve these; changing any one breaks the validated hypothesis. WHY-anchored table
at `.ledge/spikes/TRANSFER-dyn-enum-contract.md#33-non-negotiable-constraints-what-must-not-change-preserve-list`.

1. **CON-001/002/003 — the three compose-up LOCKS**: generic endpoint `/api/v1/vocabularies/sync` (never
   `/verticals/sync`); `field_key` discriminator present from row one; NAME-keying (never gid / `vertical_id`
   as the cross-service key). These keep the DEFER-1 registry door open without a rewrite
   (`.ledge/spikes/MOONSHOT-dyn-enum-contract.md:275-288`).
2. **CON-004 — additive-only / DELETE-forbidden** on `verticals` (FK-parent; spike-PROVEN unsafe to DELETE at
   `.sos/wip/spikes/dyn-enum-contract/canary1_fk_parent.py:389-393`; data-side invariant `services/vertical.py:9`).
3. **CON-005 — drift-gate-not-codegen** (ADR-S4-001 one-way door, `.know/telos/gfr-dynvocab.md:78`).
4. **CON-006 — FROZEN cf-type set**; option-set is a sidecar to `enum`/`multi_enum`, never a 7th type
   (`.know/telos/gfr-dynvocab.md:47`).
5. **CON-007 — strictly-additive to the gfr 105-test certified spine** (`.know/telos/gfr-dynvocab.md:51,79`).
6. **CON-008 — Asana live `enum_options` = single source-of-record**; data ingests one-way.
7. **CON-009 — legacy `Vertical(Enum)` / `_missing_` stays NON-CANONICAL**, never extended
   (`.ledge/spikes/INTEGRATE-dyn-enum-contract.md:160`).
8. **CON-010 — NEW endpoint, never extend `/account-status/sync`** (`extra="forbid"` => BC-1).

## Entry-Criteria / Blockers (sprint-0 — resolve or escalate BEFORE building)

These are conditions on the GO; they gate the build, not polish it.

- **EC-1 (CRITICAL) — `verticals` DB engine UNRESOLVED.** Priors disagree (`INTEGRATE-dyn-enum-contract.md:42`
  "MySQL leaf" vs `PROTO-dyn-enum-contract.md:293` "PostgreSQL staging"; flagged
  `MOONSHOT-dyn-enum-contract.md:78`). Determines upsert syntax (`ON CONFLICT` vs `ON DUPLICATE KEY UPDATE`)
  and lock primitive (`pg_advisory_xact_lock` vs `GET_LOCK`). The sprint-0 architect MUST settle this by
  inspecting the autom8y-data migration/engine config before building `vocab_upsert`.
  `[UNATTESTED — DEFER-POST-HANDOFF | defer-watch: dyn-enum-contract/EC-1-db-engine]`
- **EC-2 (HIGH) — live-Asana credential path is operator-shell-only.** The live read needs the Asana PAT from
  AWS Secrets Manager `autom8y/asana/asana-pat`; confirm the warmer runtime has the secret-fetch scope (do not
  assume CI parity). `[UNATTESTED — DEFER-POST-HANDOFF | defer-watch: dyn-enum-contract/EC-2-credential-path]`
- **EC-3 (HIGH, process) — no production telos; `/frame` is USER-SOVEREIGN.** See Telos note below.
- **EC-4 (MEDIUM) — schema-discovery consumer-compat gate** before re-pointing `SEMANTIC_ANNOTATIONS`
  (IMP-002 / `INTEGRATE-dyn-enum-contract.md:251` flags a 2x-effort risk).

## Risks (transferred from TRANSFER §4)

Structured prob/impact/mitigation table at `.ledge/spikes/TRANSFER-dyn-enum-contract.md#4-technical-risk-assessment`.
Highest-attention items for the build:

- **TR-2 (Med/Med) — `vertical_name` unique-constraint collision** on `UPDATE SET name` (NEW moonshot finding,
  `_platform.py:147`). Mitigation the build MUST implement: FR-007 name-uniqueness guard (update only when
  non-colliding; collision -> per-row WARN + refuse-the-row; never auto-resolve).
- **TR-3 (Med/High) — first-sync key-mismatch.** Mitigation: FR-008 reconciliation dry-run; refuse on ORPHAN-RISK.
- **TR-4 (Med/High) — `offers.category` string-edge omitted** from coverage. Mitigation: FR-004 third union clause.
- **TR-7 (Med/High) — DB-engine syntax/lock mismatch.** Mitigation: EC-1.
- **TR-6 (Med/Med) — ship-dark via feature flag.** Mitigation: NFR-004 publish-count metric + deploy-gate.

DORA framing [PE:SRC-001 Forsgren, Humble & Kim 2018] [MODERATE | 0.77 @ 2026-03-31]: neutral-to-positive —
reduces change-failure-rate (removes 4-6-source hand-reconciliation) and MTTR (typed hard-refuse vs cryptic
`KeyError`). [PLATFORM-HEURISTIC: DORA gating threshold is operational convention.]

## DEFER-1 Boundary (watch item — NOT in this build scope)

The fleet cf-contract REGISTRY (moonshot Option F full form: generic `cf_vocabularies` carrier at cardinality
N + declarative coherence layer) is **DEFER** and OUT of this build's scope. The receiving rite builds ONLY
the per-instance contract, compose-up-ready. The registry is a one-way door once 2+ services bind.

**DEFER-1 N>=3 escalation trigger** (restated from `.ledge/spikes/MOONSHOT-dyn-enum-contract.md:468-475`): a
2nd option-set vocabulary binds `/vocabularies/sync` (a 2nd `field_key`) **AND** a 3rd consuming service
requests the vocabulary (e.g., `scheduling-stratum` materializes). On trigger: escalate to user/leadership
(strategic bet) AND back to technology-scout (fresh build-vs-buy). Do NOT build the registry pre-trigger.
`[UNATTESTED — DEFER-POST-HANDOFF | defer-watch: dyn-enum-contract/DEFER-1-registry]`

## Recommendation — CONDITIONAL GO

**CONDITIONAL GO** for productionization of the per-instance additive-upsert vocab-sync contract.

- **GO basis**: the two load-bearing mechanism uncertainties are spike-PROVEN with two-sided discriminating
  canaries (`.sos/wip/spikes/dyn-enum-contract/canary1_fk_parent.py:389-393`,
  `.sos/wip/spikes/dyn-enum-contract/canary2_empty_publish.py:328-332`); the build composes an N>=2 production
  idiom with zero new dependency; migration phases M0-M3 are reversible.
- **CONDITIONS (sprint-0 order)**: (1) EC-1 resolved (DB engine); (2) EC-3 satisfied (user authors
  `/frame` + telos); (3) EC-2 confirmed (credential path); (4) the three compose-up LOCKS held (FR-001/002/003);
  (5) the `offers.category` string-edge in the coverage query from day one (FR-004 / TR-4).
- **Adoption J-curve** [PE:SRC-007 DORA team 2024] [MODERATE | 0.77 @ 2026-03-31]: SHALLOW — the dip is
  confined to the two genuinely-new surfaces (`vocab_upsert` store + coverage guard). **Recovery criteria**:
  >=30 days of clean sync cycles with the drift observer showing zero unresolved divergence (M1/M3 convergence,
  `.ledge/spikes/MOONSHOT-dyn-enum-contract.md:457-464`).

## Notes for Target Rite

- **Prototype code is REFERENCE ONLY.** The two canaries (SQLite, hardcoded fixtures, `print()`, no S2S/HTTP,
  no live Asana) prove the mechanism DECISION, not a portable codebase. Start fresh against the IMP-001/IMP-002
  acceptance criteria; see the prototype-to-production translation table at
  `.ledge/spikes/TRANSFER-dyn-enum-contract.md#2-prototype-to-production-translation-table-reference-only`.
- **Domain-expertise flag**: the build needs familiarity with the autom8y-data FK graph and the cache-warmer
  push topology. If the 10x-dev sprint lacks this context, pull the integration-researcher's INTEGRATE doc
  (hidden-deps HD-1..HD-7) before sprint-0 — the FK-parent correction is the load-bearing finding.
- **The handoff is `implementation`, not `strategic_evaluation`**: the only strategic-bet item (the registry)
  is explicitly DEFER and out of scope, so there is no go/no-go for strategy to make here.

## Telos / Gate-C Note (user-sovereign — NOT authored by tech-transfer)

This is a SPIKE; no production telos exists. Per `telos-integrity-ref` §3 Gate A, the 10x-dev **inception
gate** is a `/frame {dyn-enum-contract}` that produces `.know/telos/dyn-enum-contract.md` with the §2 schema
fields — `inception_anchor`, `shipped_definition.user_visible_surface`, `verified_realized_definition`
(method, deadline, rite-disjoint attester) — **declared by the USER**. Tech-transfer surfaces this requirement
and MUST NOT author it (user-sovereign declaration is the load-bearing semantic). Until the telos exists, the
initiative has no verification-realized gate and cannot close honestly.
`[UNATTESTED — DEFER-POST-HANDOFF | defer-watch: dyn-enum-contract/EC-3-telos-frame]`

## Attestation Table (absolute paths)

| Artifact | Absolute path | Status |
|----------|---------------|--------|
| This HANDOFF | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/handoffs/HANDOFF-rnd-to-10x-dyn-enum-contract-2026-06-30.md` | Authored (this file) |
| TRANSFER | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/TRANSFER-dyn-enum-contract.md` | Written + verified present |
| Canary 1 (spike-PROVEN) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/spikes/dyn-enum-contract/canary1_fk_parent.py` | Read; two-sided verdict `:389-393` |
| Canary 2 (spike-PROVEN) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/spikes/dyn-enum-contract/canary2_empty_publish.py` | Read; two-sided verdict `:328-332` |
| Scout | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/SCOUT-dyn-enum-contract.md` | Read |
| Integration | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/INTEGRATE-dyn-enum-contract.md` | Read |
| Prototype | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/PROTO-dyn-enum-contract.md` | Read |
| Moonshot | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/MOONSHOT-dyn-enum-contract.md` | Read |
| HARD-constraint source | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.know/telos/gfr-dynvocab.md` | Verified present (`:47,51,78,79`) |
| Production telos (EC-3) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.know/telos/dyn-enum-contract.md` | ABSENT — user-sovereign `/frame` is the entry gate |

---

> **Evidence grade**: `[STRUCTURAL | MODERATE]` — self-referential ceiling per `self-ref-evidence-grade-rule`;
> rnd-dk caps at MODERATE. The spike's GO is feasibility-grade; this HANDOFF's GO is CONDITIONAL and partitions
> spike-PROVEN (canary receipts) from NOT-BUILT (requirements). Production realization belongs to the 10x-dev
> build + a rite-disjoint attester against a user-authored telos, not to this transfer.
