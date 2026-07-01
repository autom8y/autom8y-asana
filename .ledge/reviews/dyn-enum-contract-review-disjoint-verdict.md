---
type: review
status: accepted
artifact_subtype: review-disjoint-verdict
promise_axis: evidence-grade
initiative: dyn-enum-contract
attestation_target: cb4b4201
attester: "case-reporter (review rite — rite-disjoint from 10x-dev; scan: signal-sifter; assess: pattern-profiler)"
authored: "2026-07-01"
scan_artifact: SCAN-dyn-enum-contract.md
assess_artifact: ASSESS-dyn-enum-contract.md
attestation_source: ".ledge/reviews/dyn-enum-contract-10x-to-review-handoff.md + .know/telos/dyn-enum-contract.md"
realization_axis: HELD-merged
verified_realized_status: "UNATTESTED — DEFER PT-07-live"
two_axis_phrasing_law: in-effect
telos_deadline: "2026-07-23"
---

# Review-Disjoint Verdict: dyn-enum-contract

> TWO-AXIS DISCIPLINE IN EFFECT throughout this artifact.
> promise_axis: evidence-grade (NOT realization).
> Axis-2 realization rung: HELD at merged.
> verified-realized: UNATTESTED — DEFER PT-07-live.
>
> Reading producer-surface STRONG as feature-realized = axis-mismatch (forbidden).

---

## 1. Verdict Headline

**producer-surface STRONG (evidence-grade axis, single rite-disjoint mechanical re-fire) — 6/6 surfaces carry the critic's OWN two-sided RED-then-GREEN.**

The review rite (signal-sifter + pattern-profiler + case-reporter, rite-disjoint from 10x-dev) independently re-fired all 6 producer guard surfaces at commit `cb4b4201` in isolated worktree `/tmp/dyn-enum-qa`. Every surface produced the expected RED under the critic's OWN breaking mutation, then returned to GREEN on revert. No surface was re-read from a 10x-dev receipt or a CI dashboard. ORIGIN was untouched; no push occurred.

**verified-realized: UNATTESTED — DEFER PT-07-live.** The live cross-repo round-trip (producer → autom8y-data consumer additive upsert → observable `verticals` row state with FK children intact) was not probed. The consumer (autom8y-data sprint-2) is absent from the producer worktree. PT-07-live is the named verification gate; telos deadline 2026-07-23.

This verdict upgrades the producer-surface evidence grade from MODERATE (10x-dev self-attestation ceiling, G-CRITIC / self-ref-evidence-grade-rule) to producer-surface STRONG (evidence-grade axis, single rite-disjoint mechanical re-fire). The realization rung is HELD at **merged**. verified-realized remains UNATTESTED.

---

## 2. GREEN/RED Matrix

Reproduced from SCAN-dyn-enum-contract.md via ASSESS-dyn-enum-contract.md — no re-run at this station.

| Surface | Description | Critic's Mutation | RED Evidence (pre-revert) | GREEN Confirmation (post-revert) | Status |
|---------|-------------|-------------------|--------------------------|----------------------------------|--------|
| **S1** | gfr-spine 207 non-regression gate | n/a (gate only — RED = contamination failure mode, not expected) | n/a | 207 passed (pre: 1.25s; post-all-surfaces: 0.50s) — certified GFR spine untouched | **GREEN** |
| **S2** | Two-sided hard-REFUSE canary (floor predicate `gid_push.py:981`) | `< floor` → `>= floor` (floor predicate inverted) | 2 FAILED: truncated set published; healthy-at-floor refused — both canary teeth inverted | 2 passed in 0.43s | **TWO-SIDED GREEN** |
| **S3-Dir1** | Drift-WARN never-warn (all 3 predicates `gid_push.py:900/905/913`) | `> 0` → `> 999999` (threshold suppressed — observer silenced) | 3 FAILED: fire-side returned `[]` — observer blind to all drift signals | 8 passed in 0.43s (all TestVocabDriftObserver — both directions restored) | **TWO-SIDED GREEN** |
| **S3-Dir2** | Drift-WARN always-warn | `> 0` → `>= 0` (fires on zero-count — always alarm) | 3 FAILED: clean-side received `[(signal, 0), ...]` — observer alarmed on zero-count signals | (combined revert with S3-Dir1 above) | **TWO-SIDED GREEN** |
| **S4-Lock A** | Endpoint path `/api/v1/vocabularies/sync` (`gid_push.py:1032`) | `→ /verticals/sync` | 3 FAILED: path assertion, AST-literal assertion, URL construction assertion all bit | 3 passed in 0.40s | **TWO-SIDED GREEN** |
| **S4-Lock B** | `field_key: Literal["vertical"]` + `extra="forbid"` (`vocabulary_sync.py:66-68`) | `Literal["vertical"]` → `str` AND `extra="forbid"` → `extra="ignore"` (discriminator weakened) | 2 FAILED: DID NOT RAISE ValidationError on non-"vertical" key; DID NOT RAISE ValidationError on unknown field | 5 passed in 0.14s | **TWO-SIDED GREEN** |
| **S4-Lock C** | NAME-keying (`vertical_key=normalize_vertical_key(opt.name)`, `gid_push.py:845`) | `vertical_key=opt.gid` (GID substituted for name) | 3 FAILED: gid appears on wire; name-collision test fails (gids differ, names were same); round-trip key mismatch | 3 passed in 0.40s | **TWO-SIDED GREEN** |
| **S5** | AST-purity of `detect_vocab_drift` (`gid_push.py:853-916`) | Inject `emit_metric("DriftProbeStarted", 1)` into function body (external-state call) | AST-PURITY FAIL: 1 forbidden external-state call detected at injected line — ADR-S4-001 violation caught | AST-PURITY PASS: 169 nodes walked, 0 external-state calls, ADR-S4-001 confirmed | **TWO-SIDED GREEN** |
| **S6** | Ship-dark DEFAULT OFF (`gid_push.py:690`) | default `""` → `"1"` (unset env now truthy — ship-dark broken) | 3 FAILED: unset env returns True; sibling flags no longer isolate; canary skip-push check fails | 5 passed in 0.38s | **TWO-SIDED GREEN** |

**Receipt summary: 6/6 logical surfaces ATTESTED (9 distinct surface-state confirmations). Total RED observations: 19 failing test instances + 1 AST-PURITY FAIL across 8 mutation directions. All 9 surface-states restored GREEN post-revert.**

Cleanup confirmed: worktree `/tmp/dyn-enum-qa` removed; working tree clean; no push; ORIGIN UNTOUCHED. `VOCAB_SYNC_ENABLED` was NEVER set in the environment during any probe. Main repo HEAD at probe time: `f4f924d2` (unmodified).

---

## 3. Health Report Card

Grades from ASSESS-dyn-enum-contract.md (pattern-profiler, review rite) — used as-is per FULL mode protocol. case-reporter does not re-grade.

| Category | Grade | Key Finding |
|----------|-------|-------------|
| Complexity | **A** | 0 critical/high/medium. gid_push.py at 1041 lines is a background Low (file-length heuristic); vocab-sync guards are bounded, discrete, and independently testable within the larger file. |
| Testing | **A** | 0 critical/high/medium. 6/6 surfaces carry two-sided mutation receipts; 19 RED observations across 8 mutation directions; 69/69 vocab-specific tests pass; 207/207 gfr-spine non-regression confirmed pre and post. |
| Dependencies | **A** | 0 critical/high/medium. verified-realized cross-repo round-trip is explicitly deferred PT-07-live (Low — managed, named, dated 2026-07-23). No supply chain concerns in the producer surface; 151 packages resolved at cb4b4201 without incident. |
| Structure | **A** | 0 critical/high/medium. Ship-dark confirmed (unset → False default). Lock A (generic path), Lock B (Literal["vertical"] + extra="forbid"), Lock C (NAME-keying) all mutation-verified. Entrypoint gate fires before transport. Compose-up architecture intact. |
| Hygiene | **A** | 0 critical/high/medium. AST-purity of `detect_vocab_drift` confirmed (169 nodes walked, 0 external-state calls, ADR-S4-001 held). NEVER-advisory docstrings for gid/vertical_id keying present. Low-2: telos `attestation_status.shipped: MISSING` — bookkeeping gap, not a code deficiency. |
| **Overall** | **A** | **Median [A, A, A, A, A] = A; weakest category = A; no floor-drag rules triggered (no D, no F, not 3+ categories at C or below); 0 critical, 0 high, 0 medium across all five categories.** |

### Findings by Severity

**Critical**: None.
**High**: None.
**Medium**: None.

**Low (two notes — both non-blocking):**

**[LOW-1] gid_push.py file length** (`src/autom8_asana/services/gid_push.py`, cb4b4201, 1041 lines). Category: Complexity. File exceeds the 500-line heuristic [PLATFORM-HEURISTIC: 500-line threshold]. Vocab-sync section is isolated within the larger file; signal-sifter found 0 complexity signals. No immediate action required. If gid_push.py grows further, extract the vocab-sync block into `src/autom8_asana/services/vocab_sync.py`. The bounded nature of the current addition does not warrant refactoring now.

**[LOW-2] Telos bookkeeping: `attestation_status.shipped: MISSING`** (`.know/telos/dyn-enum-contract.md:48`). Category: Hygiene. Telos was authored pre-build with `shipped: MISSING`. Sprint-1 producer PR #175 at cb4b4201 has since landed; `code_or_artifact_landed` has not been updated. 10x-dev should update at sprint-1 wrap: set `shipped: LANDED`, populate `code_or_artifact_landed` with file:line anchors for `gid_push.py` vocab-sync functions and `contracts/vocabulary_sync.py`, set `code_verbatim_match: true`. Gate-B applies at `/sos wrap`. No code changes required.

---

## 4. Two Rungs — Named Explicitly

| Axis | Rung / Grade | State |
|------|-------------|-------|
| **Realization axis — producer rung** | **merged** | PR #175 squash `cb4b4201` merged to `main`, ship-dark (`VOCAB_SYNC_ENABLED` default OFF; zero production callers). HELD at merged — not shipped, not verified-realized. |
| **Evidence-grade axis — producer-surface** | **STRONG (evidence-grade axis, single rite-disjoint mechanical re-fire)** | This verdict. Upgrades from MODERATE (10x-dev self-attestation ceiling, G-CRITIC / self-ref-evidence-grade-rule) by independent rite-disjoint mechanical re-fire of all 6 surfaces. The upgrade lands in this verdict ONLY — it does not edit the telos, the handoff, or the producer code. |
| **Realization axis — verified-realized** | **UNATTESTED → PT-07-live** | The live cross-repo round-trip has not been probed. Consumer (autom8y-data sprint-2) absent. Explicitly deferred — see §5. |

Reading producer-surface STRONG (evidence-grade axis) as feature-realized = axis-mismatch (forbidden). The realization rung ceiling is **merged**.

---

## 5. DEFER Envelope — G-DEFER, Watch-Registered (NOT a Silent Drop)

**verified-realized: UNATTESTED — DEFER-1, watch-registered.**

| Field | Value |
|-------|-------|
| DEFER label | DEFER-1 (watch-registered) |
| What is deferred | The full verified-realized predicate: a NEW or renamed Asana enum_option round-trips into `autom8y-data.verticals` via additive-upsert with existing ids + FK children (campaigns / asset_verticals ~43K / offers.category) intact within one sync cycle, AND an empty/truncated Asana read is hard-REFUSED with an alert (never applied) — asserted by a LIVE integration test on a real option-set round-trip. NOT "endpoint merged", NOT "PRs green". |
| **Watch-trigger** | **autom8y-data consumer DEPLOYED + `VOCAB_SYNC_ENABLED` flipped ON → the live round-trip harness (`tests/integration/test_dyn_enum_roundtrip.py`) fires at PT-07-live.** Consumer deployment is the unlock; enable-order (BC-1 / CON-010) requires consumer deployed BEFORE the producer flag is turned ON. |
| Telos deadline | **2026-07-23** (telos `verification_deadline`, operator-ratified 2026-07-01) |
| Rite-disjoint attester at PT-07-live | review-rite external critic (`.know/telos/dyn-enum-contract.md:69`) |
| Naxos signal | TELOS_OVERDUE fires if verified-realized remains UNATTESTED after 2026-07-23 |

The DEFER-1 watch-trigger fires when the full consumer-deploy + flag-enable + live-harness-run sequence completes. This verdict does NOT advance the watch-trigger. Production-mutating levers (`VOCAB_SYNC_ENABLED`, merges, consumer deploy, `ari sync`) remain the operator's.

---

## 6. Recommend-in-Handoff: PT-07-Live Acceptance Shape

**This section recommends only. It does NOT execute, dispatch, or initiate any action. Sprint-2 decisions and production-mutating levers remain the operator's.**

The dre consumer (autom8y-data sprint-2) inherits the following acceptance shape for the PT-07-live verification gate.

### 6a. The 6 Harness Legs (`tests/integration/test_dyn_enum_roundtrip.py`)

| Leg | Test Case | Acceptance Criterion |
|-----|-----------|---------------------|
| **POS-NEW** | A new Asana enum_option (not yet in `verticals`) round-trips via additive upsert | New row in `verticals` with correct `vertical_key`; existing rows untouched; FK children (campaigns / asset_verticals / offers.category STRING edge) intact |
| **POS-RENAME-SAMEKEY** | An existing option renamed — same normalized key (name-text changes, key unchanged) | `vertical_name` updated in place; `vertical_id` and FK edges preserved; no new row inserted |
| **POS-RENAME-NEWKEY** | An existing option renamed to a new normalized key | New row inserted for the new key; old row NOT deleted; no FK orphans |
| **NEG-empty** | Empty Asana read (0 options returned) sent to the producer | Hard-REFUSE: floor predicate fires; no write to `verticals`; alarm emitted; database state unchanged |
| **NEG-truncated** | Truncated set (count below floor threshold) | Hard-REFUSE: same as NEG-empty; guard fires; no partial write |
| **IDEMPOTENCE** | Full sync run twice on the same live option-set without changes | Row state identical after second run; no duplicate rows; no spurious updates |

### 6b. Enable-Order (BC-1 / CON-010)

Consumer DEPLOYED before `VOCAB_SYNC_ENABLED` flipped ON. Sequence:

1. autom8y-core model-promotion (`VocabularySyncRequest` home) — prerequisite for consumer import
2. autom8y-data sprint-2 consumer endpoint (`POST /api/v1/vocabularies/sync`) deployed
3. ONLY THEN: `VOCAB_SYNC_ENABLED=1` (or `true`/`yes`) set in the producer environment
4. PT-07-live harness fires: `AUTOM8Y_DATA_URL=… AUTOM8Y_DATA_API_KEY=… DYN_ENUM_LIVE_ROUNDTRIP=1 ./.venv/bin/python -m pytest tests/integration/test_dyn_enum_roundtrip.py -m integration -v`

### 6c. G-PROPAGATE Point

The `/vocabularies/sync` contract + 3 locks + `[PROPOSE→autom8y-core]` model home is the G-PROPAGATE propagation point. `VocabularySyncRequest` (`field_key: Literal["vertical"]`, `extra="forbid"`, NAME-keyed payload) currently lives in the autom8y-asana producer (`src/autom8_asana/contracts/vocabulary_sync.py`). Cross-fleet reuse and consumer import require promotion to autom8y-core as the canonical model home. This is a prerequisite for both sprint-2 and PT-07-live legs to close. Promotion timing: post-sprint-2 consumer wire-format confirmation (do NOT promote pre-consumer-sprint — the format confirmation is the signal).

---

## 7. Cross-Rite Routing

**Routed, NOT dispatched from this verdict. Operator controls session initiation and rite-switching.**

| Concern | Target Session / Rite | Action |
|---------|----------------------|--------|
| Consumer endpoint: `POST /api/v1/vocabularies/sync` + `VerticalService.upsert_by_key` + FK coverage | **autom8y-data sprint-2 — operator's dre session** | Operator initiates dre session in autom8y-data repo. Implementation shape: route THROUGH `VerticalService.create`, extend with update-name; MySQL `ON DUPLICATE KEY UPDATE` (EC-1 resolution confirms engine first); no `GET_LOCK` per ADR §4; 3-edge FK coverage including `offers.category` STRING edge (`_platform.py:162`); `extra=forbid`→422; NEVER DELETE |
| `VocabularySyncRequest` model home promotion | **autom8y-core model-promotion (minor bump)** | Must land before the consumer can import; prerequisite for both sprint-2 and PT-07-live. Do NOT promote pre-sprint-2 wire-format confirmation |
| PT-07-live live round-trip attestation | **review rite — signal-sifter at PT-07** | After consumer deployed + flag ON: signal-sifter runs the 6-leg harness rite-disjoint; attester per `.know/telos/dyn-enum-contract.md:69` |
| Telos bookkeeping gap (LOW-2) | **10x-dev sprint-1 wrap** | Update `.know/telos/dyn-enum-contract.md`: `shipped: LANDED`, file:line anchors, `code_verbatim_match: true`; no code changes required; Gate-B applies at `/sos wrap` |

---

## 8. What STOPS Here

This review touched the producer surface read-mostly in an isolated worktree (`/tmp/dyn-enum-qa`, ORIGIN untouched) and via reverted mutations only. The following remain the operator's levers — review did not execute any of them and MUST NOT:

- `VOCAB_SYNC_ENABLED` — production flag; remains OFF until the operator enables it post consumer-deploy (BC-1 sequence)
- Merges — no new merges were created or staged by this review
- Consumer deploy (autom8y-data sprint-2) — a separate operator-initiated dre session
- `ari sync` — rite-switching is the operator's action
- autom8y-core model-promotion — a separate operator-initiated minor bump

The only write artifact produced by this review rite is this verdict document. Worktree `/tmp/dyn-enum-qa` was removed post-probe with nothing to commit and working tree clean.

---

## Handoff Criteria Checklist

- [x] Verdict headline present — both axes; two-axis phrasing law enforced throughout
- [x] GREEN/RED matrix — 6/6 logical surfaces ATTESTED (9 distinct surface-state confirmations; 19 RED observations + 1 AST-PURITY FAIL; all restored GREEN)
- [x] Health grades — 5 categories + Overall all A; two Low notes recorded; no Critical/High/Medium
- [x] Two rungs named explicitly — producer = merged; producer-surface = STRONG (evidence-grade axis, single rite-disjoint mechanical re-fire); verified-realized = UNATTESTED → PT-07-live
- [x] DEFER envelope — G-DEFER watch-registered; watch-trigger named; telos deadline 2026-07-23; NOT a silent drop
- [x] Recommend-in-handoff — 6 PT-07-live harness legs + enable-order (BC-1) + G-PROPAGATE point documented
- [x] Cross-rite routing table — dre consumer sprint-2 + autom8y-core promotion + PT-07-live + LOW-2 bookkeeping
- [x] What STOPS — production-mutating levers enumerated; review touched none
- [x] promise_axis: evidence-grade in frontmatter (NOT realization)
- [x] Frontmatter: type: review, status: accepted, artifact_subtype: review-disjoint-verdict, initiative: dyn-enum-contract, attestation_target: cb4b4201

---

*Review mode: FULL | Attested by review rite (signal-sifter + pattern-profiler + case-reporter) — rite-disjoint from 10x-dev | Commit: cb4b4201 | 2026-07-01*
