---
type: review
status: proposed
---

# HANDOFF — arch (autom8y) -> 10x-dev (autom8y-asana): hierarchy-first entity-resolution primitive

- Date: 2026-07-08
- handoff_type: **implementation** (arch -> 10x-dev)
- Origin rite: arch (multi-repo architecture analysis)
- Target rite: 10x-dev (requirements-analyst / architect / principal-engineer / qa-adversary)
- Design references: ADR `.ledge/decisions/ADR-entity-resolution-primitive-2026-07-08.md`;
  TDD `.ledge/specs/TDD-entity-resolution-primitive-2026-07-08.md`
- Self-assessment ceiling: **MODERATE** (`self-ref-evidence-grade-rule`) — design-reasoning over a
  self-authored slate; the only live proof is the spike's own monkeypatch driver. STRONG requires an
  independent build + 2-sided QA receipt from the target rite.
- Realization rungs: **authored** (this handoff) < built < tested < merged < live. Current rung: **authored**.

Read origin/main via the intact worktree; NEVER the stale local main. Every platform-behavior claim
carries a `file:line` SVR.

---

## Premise (the felt bug)

Total Wellness Center PLAY `1215766139321621` is **HELD** fail-closed: `+13036277995` aliases the
BUSINESS card `1214127219419742` AND opportunity card `1214420107547660`, so the phone resolver
raises `ContactCardBusinessAmbiguous` (SVR spike:9-19). The authoritative fix (walk PLAY ancestors ->
first `BUSINESS_PROJECT` member -> Company ID) is proven live via the spike's monkeypatch driver
(SVR spike:46-48) and reuses shipped substrate.

---

## Items

### ITEM-1 — Build `office_resolution.py` (the hierarchy-first resolver seam) [BUILD]

- **design_references**: ADR §Decision; TDD §2.1 (signatures), §2.2 (cache pinning), §3 (reuse ledger).
- **acceptance_criteria**:
  1. New module `.../onboarding_walkthrough/office_resolution.py` exports `resolve_business_gid`, `resolve_office_guid`, `BusinessResolution` (frozen dataclass with `method`, `ancestor_depth`, `candidates`), and the four exception types (`BusinessResolutionAmbiguous`, `BusinessResolutionMissingNoBusiness`, `BusinessResolutionDepthExhausted`, `DivergentOfficeResolution`).
  2. The walk self-warms a **fresh local `HierarchyIndex()`** via live `tasks.get_async` `parent.gid` reads (no `UnifiedTaskStore` dependency); returns `method="hierarchy"` on success.
  3. The discriminator uses `get_registry().get_by_gid(project_gid)` (SVR `entity_registry.py:299`) with `BUSINESS_PROJECT` (SVR `project_registry.py:21`) as the fallback literal.
  4. `resolve_business_gid` ships **BUSINESS-only** with a private `project_gid` parameter seam (FORK-1); NO `EntityType|EntityCategory` generalization.
- **TL-A falsifiable prediction**: A unit test that constructs `HierarchyIndex()`, `register`s three synthetic nodes (child->parent->BUSINESS-member root), and calls the walk resolves the root gid at `ancestor_depth==2` WITHOUT any store handle — proving store-independence. If it needs a `UnifiedTaskStore`, the design is falsified.
- **TL-B SRC citations**: `hierarchy.py:57,87-90,96,160-182` (`:175` empty-on-unregistered); `entity_registry.py:299,445-446,1203`; `project_registry.py:21`; `template_comment.py:217-229` (`_company_id_from_task`).
- **TL-C adversarial disposition**: The COLD-INDEX trap (a naive `get_ancestor_chain(play_gid)` returns `[]` on an unregistered gid, SVR `hierarchy.py:175`) is the primary failure mode Candidates 2/3 flagged; this item's AC-2 forecloses it by mandating self-warm. qa-adversary must assert the walk NEVER calls `get_ancestor_chain(play_gid)` against a cold shared index.

### ITEM-2 — Repoint SITE 1: `template_comment._resolve_office_guid` [BUILD]

- **design_references**: TDD §4 SITE 1; ADR §Consequences (crown-jewel preserved).
- **acceptance_criteria**:
  1. `template_comment.py:245` (`_business_gid_by_phone` call) is replaced by `office_resolution.resolve_business_gid(...)` as PRIMARY; phone remains AUTOMATIC fallback on `business_gid is None`.
  2. All `TemplateCommentRefused` LOUD-refusal paths (`:241-260`) preserved.
  3. The `TaskOfficeMismatch` verify (`template_comment.py:319-327`) is **byte-for-byte unchanged**; it now compares against the hierarchy-resolved guid.
- **TL-A falsifiable prediction**: `post_template_comment(task_gid=1215766139321621, execute=False)` dry-run RESOLVES (no `ContactCardBusinessAmbiguous`) and composes a routing line for office guid `7363c7ea-66f8-487f-9f6e-c7a12a63d33f`. If it still refuses ambiguous, the repoint is falsified.
- **TL-B SRC citations**: `template_comment.py:232-261,288-327` (`_resolve_office_guid`, `post_template_comment`, `TaskOfficeMismatch` at `:319-327`); spike:24-28 (chain), spike:27 (Company ID).
- **TL-C adversarial disposition**: Risk — the fallback silently masks a hierarchy regression. Mitigation: `method` provenance is logged; a `method="phone"` on a well-parented office is a watch signal (see DEFER-WATCH-1). qa-adversary must confirm the crosscheck (`phone_crosscheck=True`) raises `DivergentOfficeResolution` on a deliberately-mismatched fixture (teeth).

### ITEM-3 — Repoint SITE 2: `contact_synthesis.resolve_ranked_cards` + `post_contact_card` [BUILD]

- **design_references**: TDD §4 SITE 2; FORK-5 (signature migration).
- **acceptance_criteria**:
  1. `resolve_ranked_cards` gains a `task_gid` param; `contact_synthesis.py:434` uses the walk as PRIMARY, `office_phone` as deprecation-window fallback/crosscheck.
  2. `post_contact_card` threads `play_gid` (already in scope, SVR `:468,499`) into `resolve_ranked_cards`.
  3. `_business_gid_by_phone` (`:374-414`) RETAINED (fallback + S2S tool); its `ContactCardBusinessAmbiguous` on >1 (`:406-410`) preserved.
  4. Confirm NO external caller depends on the phone-only entry before any future deletion.
- **TL-A falsifiable prediction**: `post_contact_card(play_gid=1215766139321621, execute=False)` returns a non-`no_holder` outcome (a ranked card set) rather than raising `ContactCardBusinessAmbiguous`. If it still raises on TWC, the repoint is falsified.
- **TL-B SRC citations**: `contact_synthesis.py:374-414,417-459,465-547` (`:434` phone call, `:503` post-card call, `:468,499` play_gid scope).
- **TL-C adversarial disposition**: Risk — the `office_phone`->`play_gid` signature flip touches the public `post_contact_card` contract. Mitigation: callers already pass `play_gid` (`:468`); `office_phone` becomes a pure override. qa-adversary must verify no in-tree caller breaks and that `no_holder`/`no_contacts` outcome codes are unchanged.

### ITEM-4 — 2-sided QA (hierarchy resolves TWC; phone-only office works; B5 non-regression) [TEST]

- **design_references**: TDD §6 (T-1..T-6).
- **acceptance_criteria**:
  1. **T-1**: TWC PLAY resolves via hierarchy to `1214127219419742` / Company ID `7363c7ea-…`; the phone path on the SAME office refuses ambiguous (two-sided teeth).
  2. **T-2**: a clean single-Business office resolves identically by BOTH paths (`phone_crosscheck=True`, no divergence); a walk-`None` orphan fixture falls back to phone (`method="phone"`).
  3. **T-3**: `office_resolution.py` imports NO `DataServiceClient`/`get_gid_map`/vertical export (grep EMPTY); network dependency is `tasks.get_async` only. B5 failure mode unreachable.
  4. **T-4/T-5/T-6**: multi-Business chain -> `BusinessResolutionAmbiguous`; depth-exhausted -> `BusinessResolutionDepthExhausted` (distinct from no-business); crown-jewel `TaskOfficeMismatch` preserved.
- **TL-A falsifiable prediction**: `grep -n "get_gid_map\|DataServiceClient" office_resolution.py` returns 0 lines AND T-1 resolves under `NullCacheProvider()`. If either fails, the B5-safety / correctness claim is falsified.
- **TL-B SRC citations**: spike:9-19 (ambiguity), spike:24-28 (chain), spike:46-48 (proof driver); `contact_synthesis.py:429` (B5 comment); `clients/tasks.py:209-235` (cache pinning rationale); defect:47-53 (`NullCacheProvider` unblock).
- **TL-C adversarial disposition**: The design is self-referential; the target rite's QA IS the external corroboration that lifts MODERATE -> STRONG. qa-adversary must run T-1..T-6 against LIVE Asana under `NullCacheProvider()` and produce an independent receipt — NOT re-cite the spike driver.

### ITEM-5 (DEFER) — S2S `intake_resolve.resolve_business` hierarchy-aware overload [DEFER-WATCH]

- **design_references**: TDD §4 SITE 3 (FORK-4).
- **acceptance_criteria (when reactivated)**: additive optional `task_gid` on `BusinessResolveRequest`; when present, prefer a hierarchy walk (store-backed via `get_parent_chain_async`, SVR `unified.py:709`), else O(1) `GidLookupIndex`; ADR-INT-001 never-404 preserved.
- **deferral rationale**: SEPARATE process/store; accepts phone with no task-gid; the felt bug is the walkthrough. NOT a gate on ITEM-1..4.
- **watch-trigger**: an S2S caller reports a phone-collision resolve error on `/v1/resolve/business`, OR a hierarchy-rooted caller (one holding a task_gid) is added to the S2S consumers.
- **owner-rite**: 10x-dev (autom8y-asana). **escalation-path**: file as a follow-up ticket referencing this HANDOFF ITEM-5.
- **TL-B SRC citations**: `intake_resolve.py:69-157`; `intake_resolve_service.py:56-97`.

### ITEM-6 (DEFER) — SIBLING-1 cache hit-path projection-coverage; unpin `NullCacheProvider` [DEFER-WATCH]

- **design_references**: TDD §2.2, §5, §7 Phase 4; ADR §Consequences (SIBLING-1 coupling).
- **acceptance_criteria (when reactivated)**: the resolver drops the `NullCacheProvider()` pin and runs cached reads once the fleet-wide hit-path coverage check (serve-from-cache ONLY IF stored keys cover the requested projection, else miss+hydrate `union(stored ∪ requested ∪ STANDARD)`) lands (SVR defect:57-59).
- **deferral rationale**: the coverage-check is a separate fleet substrate fix; pinning `NullCacheProvider()` matches the current floodgates unblock, so it costs nothing today.
- **watch-trigger**: SIBLING-1's hit-path coverage-check PR merges to origin/main (grep `clients/tasks.py` for a projection-coverage guard on the hit path).
- **owner-rite**: 10x-dev / platform. **escalation-path**: reference `DEFECT-taskcache-cross-reader-section-starvation-2026-07-08.md`.
- **TL-B SRC citations**: `clients/tasks.py:209-235`; `models/business/fields.py:268` (memberships.section deliberately EXCLUDED comment; `STANDARD_TASK_OPT_FIELDS` declared at :232); defect:20-37,57-59. <!-- CH-02 cleared 2026-07-08: re-anchored :271→:268 per ADVERSARY-REPORT-entity-resolution-1. CH-01 accepted-advisory: the TL-A per-item predictions are build-gates (immediate), not ≥180-day-horizon predictions. -->

### ITEM-7 (DEFER) — SIBLING-2 floodgates per-office Pages deploy accumulation [DEFER-WATCH]

- **design_references**: MAP sibling-2 findings; `host_bundle.py:109-178`, `floodgates/batch.py`.
- **deferral rationale**: orthogonal to office resolution; single-office runs work; not load-bearing to the flagship.
- **watch-trigger**: a batch fan-out of N>1 offices is attempted and a prior office's deck is observed orphaned/overwritten at a stale Pages URL.
- **owner-rite**: 10x-dev (autom8y-asana). **escalation-path**: separate spike/TDD; do NOT fold into this seam.

---

## Realization ladder (summary)

| Rung | Gate |
|---|---|
| authored | this HANDOFF + ADR + TDD exist |
| built | ITEM-1..3 landed; `office_resolution.py` compiles, TWC dry-run resolves |
| tested | ITEM-4 T-1..T-6 GREEN under `NullCacheProvider()` — the external corroboration leg |
| merged | Phase-1 PR merged to origin/main |
| live | Phase-2 shadow crosscheck wave: zero `DivergentOfficeResolution` across ACTIVE offices |

## Watch-registered DEFER items

- **DEFER-WATCH-1** (provenance drift): a `method="phone"` resolution on a **well-parented** office = a hidden hierarchy gap. Watch the fallback rate; a nonzero rate on parented PLAYs escalates.
- **DEFER-WATCH-ITEM-5** (S2S overload) — trigger: S2S phone-collision or a hierarchy-rooted S2S caller.
- **DEFER-WATCH-ITEM-6** (SIBLING-1 unpin) — trigger: fleet coverage-check lands.
- **DEFER-WATCH-ITEM-7** (SIBLING-2 accumulation) — trigger: N>1 batch fan-out orphans a prior deck.
