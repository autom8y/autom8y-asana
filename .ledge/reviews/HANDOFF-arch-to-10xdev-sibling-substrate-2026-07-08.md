---
type: review
status: proposed
---

# HANDOFF: arch → 10x-dev (autom8y-asana) — sibling-substrate sprint: PHE projection coverage + F-2 bind + sibling dispositions

- **handoff_type**: implementation (arch → 10x-dev, autom8y-asana rite)
- **Date**: 2026-07-08
- **Fresh root (re-derive nothing — anchors verified here)**: `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.knossos/worktrees/wt.arch.sibling-substrate.20260708T182700.d865d7` @ `5b5c249a` (origin/main, POST-#214). NEVER read the stale local main.
- **Design authority**: ADR `.ledge/decisions/ADR-taskcache-projection-coverage-2026-07-08.md` (ACCEPTED); TDD `.ledge/specs/TDD-taskcache-projection-coverage-2026-07-08.md` (this handoff's items reference TDD sections).
- **Prior receipts**: DEFECT-taskcache-cross-reader-section-starvation-2026-07-08.md; FRAME-sibling-substrate-arch-sprint-2026-07-08.md; HANDOFF-arch-to-10xdev-entity-resolution-2026-07-08.md (ITEM-5/6/7 reactivating here); DEFECT-floodgates-optfields-blind-cache-poisoning-2026-07-07.md.
- **Telos frame**: daily client trust; silent-wrong-outcome is the enemy; the batch machine must not false-HALT. Every failure direction of the design is a loud bounded re-fetch, never a narrowed serve.
- **Evidence grade**: MODERATE (self-referential cap). External lifts: qa-adversary live canary leg (P2); operator env census (P0).
- **Predictions discipline**: all TL-A predictions below are **BUILD-GATES — immediate, falsifiable at build/test time**, not horizon predictions. Each one, if falsified, halts its item.

## Realization rungs (name them in receipts)

`BUILT` → `MERGED` → `CANARY-PROVEN` (2-sided suite green incl. RED-before archived run) → `LIVE-LEG-PROVEN` (qa-adversary against live Asana) → `UNPINNED` (ITEM-6 executed) → `WATCHED-LIVE` (DEFER-WATCH-1 = 0 through one batch wave). The flagship's done-bar is `UNPINNED`; `WATCHED-LIVE` is the realization rung that closes the arc.

---

## ITEM-A (FLAGSHIP): PHE coverage predicate + TASK hit-path guard + 2-sided starvation canary

**Scope**: TDD §2, §3 rows 1-11, §6.1-6.3.

**Acceptance criteria**:
1. New pure module `src/autom8_asana/cache/models/coverage.py` with `stored_projection()` + `projection_covers()` exactly per TDD §2.1: exact-string subset; absent-or-EMPTY `opt_fields_used` ⇒ UNKNOWN ⇒ not covered; no prefix implication.
2. `BaseClient._cache_set` gains `opt_fields: Sequence[str] | None = None` kwarg writing `opt_fields_used` + `completeness_level` into the metadata of the `CacheEntry` constructed at `clients/base.py:155-161` — same keys as `create_completeness_metadata` (completeness.py:302).
3. `BaseClient._cache_get_covering` returns miss (None) + structured `cache_coverage_miss` log `{gid, entry_type, missing_fields, stored_count}` when the entry exists but coverage fails; existing `_cache_get` signature untouched.
4. `tasks.py` hit path: `_resolve_opt_fields` hoisted above the lookup; `_cache_get_covering` replaces `_cache_get` at :208; predicate runs BEFORE the raw/model branch (:231-235); custom_fields canary (:225-230) retained/demoted; requested-prefix WARN canary added on trusted hits (UV-P labeled).
5. `tasks.py` miss path: coverage-miss union = `resolved ∪ STANDARD_TASK_OPT_FIELDS ∪ stored_projection(old_entry)`; REPLACE + TTL reset via existing `_resolve_entity_ttl` (:270); `_cache_set(..., opt_fields=superset_opt_fields)` at :271.
6. §6.1 canary suite lands with an ARCHIVED RED-before run (test executed against pre-fix hit path — commit-ordered or via a pinned-revision CI job) and GREEN-after, plus TEETH arm and ping-pong bound.
7. §6.2 predicate/metadata unit tests: UNKNOWN normalization (incl. `opt_fields_used: []`), raw/model parity, metadata survival through `_extend_ttl` (staleness_coordinator.py:253) and soft-invalidate (mutation_invalidator.py:286), serialization round-trip (entry.py:212/:343), and the typed-field-drops proof pinning why metadata is the authority.
8. §6.3 caller-constant registry test parametrized over all 8 registered constants; `link_on_play.py:158-167` inline projection hoisted to `_PREFLIGHT_OPT_FIELDS` (no behavior change).
9. Existing suites stay GREEN: `test_tasks_cache_superset_hydration.py:105-268` and `:270-311`; `test_min_opt_fields_detection_coherence.py:25-31`.
10. `cache_coverage_miss` emitted as structured log/metric (the amplification tripwire).

**Design references**: ADR forks (a)(b); TDD §2.1-2.4, §3 rows 1-11, §6.1-6.3.

**TL-A falsifiable prediction (BUILD-GATE)**: With a fake transport echoing exactly the requested opt_fields, on CURRENT main (5b5c249a) the sequence [reader-1 `get_async(opt_fields=["gid","name"])`, reader-2 `get_async(opt_fields=["memberships.section.gid","memberships.section.name"])`] produces exactly ONE HTTP call and reader-2 is served memberships WITHOUT section — the canary test FAILS pre-fix. Post-fix the same sequence produces exactly TWO HTTP calls, the second carrying `memberships.section.*` in params, and reader-2's data carries the section family. Additionally: alternating the two readers ×10 produces exactly 2 total HTTP calls post-fix; a reader with requested ⊆ stored produces ZERO extra calls. If any arm fails, the design premise is falsified — HALT and return to arch.

**TL-B SRC citations (verified on fresh root)**: hit path tasks.py:207-235 (guardless serve at :216; warn-only canary :225-230); miss union :264-271; `_resolve_opt_fields` :292-326 (None→STANDARD :316-319; merge :325); `_MINIMUM_OPT_FIELDS` :41-47; STANDARD fields.py:232-256; section exclusion :268-270; `_cache_get`/`_cache_set` base.py:83-121/:123-177 (CacheEntry :155-161, version :148-149); metadata slot entry.py:107, round-trip :212/:343, EntityCacheEntry typed fields :380-381; `create_completeness_metadata` completeness.py:280-302 (`opt_fields_used` :302; `or []` empty shape :302); UnifiedTaskStore already-honest writes unified.py:412/:474; `_extend_ttl` metadata spread staleness_coordinator.py:253; soft-invalidate `replace()` mutation_invalidator.py:286; live-shape fixture `"parent": None` test_tasks_cache_superset_hydration.py:88; preflight projection link_on_play.py:158-167.

**TL-C adversarial disposition**: The predicate is deliberately dumb — expect qa to attack (i) semantically-implied fields (stored `custom_fields.enum_value` vs requested `custom_fields.enum_value.name`): answer is one loud re-fetch, by design, telemetered; (ii) merge-vs-replace: replace is load-bearing (torn-read class) — any "optimize by merging" review suggestion is REJECTED per ADR fork (b); (iii) the prefix WARN canary's Asana key-presence axiom is UV-P — qa live-probes it, and it is warn-only so falsification costs a spurious WARN, never a wrong serve; (iv) a G-THEATER check: the RED-before is the CURRENT hit path failing a new test, NOT an injected defect — discriminating-canary doctrine mode 2 (genuine production gap under an architect ruling).

---

## ITEM-B: sibling entity clients (projects / sections / users / custom_fields)

**Scope**: TDD §3 row 15. Same 3-line pattern per client; re-hydration union = requested ∪ stored (no STANDARD analogue). Separate commit in the flagship PR; **splittable to an immediate fast-follow PR if review pressure demands — zero rework** (shared predicate module).

**Acceptance criteria**: `_cache_get_covering` + `opt_fields=` threading at projects.py:105/:119, sections.py:113/:127, users.py:102/:116, custom_fields.py:108/:122; one minimal 2-sided coverage test per client (miss-widen + covered-hit-zero-fetch).

**Design references**: ADR fork (d); TDD §3 row 15.

**TL-A falsifiable prediction (BUILD-GATE)**: on current main each of the four hit paths serves a cached entry regardless of requested opt_fields (a narrow-write-then-wide-read test FAILS pre-fix on each client); post-fix each converges in ≤1 widening fetch. If any client's cache flow differs from the TASK pattern in a way that breaks the 3-line graft, HALT that client and file it to watch — do not bend the predicate.

**TL-B SRC citations**: projects.py:105 (`_cache_get(project_gid, EntryType.PROJECT)`), :119 (`_cache_set`); sections.py:113/:127; users.py:102/:116; custom_fields.py:108/:122 — all verified guardless-serve on fresh root.

**TL-C adversarial disposition**: demand diversity is far lower than TASK — expect qa to challenge necessity; the answer is class-closure at near-zero marginal cost, and the fork is pre-ratified as splittable. SECTION entries have no `modified_at` (entry.py comment near :39) — version derivation falls to `datetime.now` per base.py:149; assert the widened REPLACE still lands (set_versioned overwrite semantics, `_defaults/cache.py:250`+).

---

## ITEM-C: warmer + loader projection threading (MUST — same PR as ITEM-A)

**Scope**: TDD §3 rows 13-14, §6.4.

**Acceptance criteria**: BOTH `autom8_adapter.py` bare `CacheEntry(TASK)` write sites (:292-300 and :382-389) stamp the fetcher's projection into metadata; `loader.load_task_entry` (:24, CacheEntry at :95-106) **AND the sibling batch writer `loader.load_task_entries` (:285, generic `CacheEntry(entry_type=entry_type)`) — CH-02** gain optional `opt_fields` kwarg (default None = UNKNOWN); the census grep-assertion covers BOTH loader sites (:24 and :285); release-note the exported contract (`cache/__init__.py:110/:219`); §6.4 warmer-honesty test RED without this item, GREEN with it. <!-- CH-01/CH-02 cleared 2026-07-08 per ADVERSARY-REPORT-sibling-substrate-1; CH-03 accepted-advisory (the P2 qa live leg explicitly probes the top-level-key-presence axiom, TDD §10 P2). -->

**Design references**: ADR fork (c); TDD §3 rows 13-14.

**TL-A falsifiable prediction (BUILD-GATE)**: without this item, a warm-written entry's FIRST `get_async` read at the warmer's own projection coverage-misses and re-fetches (test proves the warmer is neutered to prefetch-without-serve); with it, that read HITs with zero fetches. If the fetcher's opt_fields are NOT derivable at either adapter call site, the design premise is falsified — HALT and return to arch.

**TL-B SRC citations**: autom8_adapter.py:292-300 (bare CacheEntry, no metadata kwarg — verified) and :382-389 (second bare construct, batched via `cache.set_batch` at :392); loader.py:24/:95-106 (bare CacheEntry + `set_versioned`); hierarchy_warmer.py:246 already passes `opt_fields=_HIERARCHY_OPT_FIELDS` through `unified_store.put_async` (the already-honest path, unified.py:412).

**TL-C adversarial disposition**: the trap is fixing only :292 and missing :382 — the census found TWO bare TASK writers in the adapter; qa should grep-assert zero remaining `CacheEntry(` TASK constructions without projection metadata outside test fixtures.

---

## ITEM-D: F-2 env bind + kill-switch (same train, lands BEFORE unpin)

**Scope**: TDD §5, §10 P0.

**Acceptance criteria**: one-line bind at config.py:855 (`default_factory=CacheConfig.from_env`); startup INFO log of bound values; regression test — `ASANA_CACHE_ENABLED=false` ⇒ default `AsanaClient()` provider is `NullCacheProvider`; unset env ⇒ auto-detect byte-identical; explicit `AsanaConfig(cache=...)` and explicit `cache_provider=` precedence untouched (test both); CI env verified clean of `ASANA_CACHE_*`; changelog callout; **P0 operator census executed pre-merge** (any pre-existing `ASANA_CACHE_*` export in fleet deploy configs is an operator-ratification fork).

**Design references**: ADR fork (e); TDD §5.

**TL-A falsifiable prediction (BUILD-GATE)**: on current main, a test setting `ASANA_CACHE_ENABLED=false` then constructing default `AsanaClient()` gets a NON-null provider (proving the dead knob — this test is truthfully writable only as an xfail/inverted assertion pre-fix); post-bind the same test passes with `NullCacheProvider`. If `from_env` turns out to read a cached/singleton settings object (contradicting config.py:781-816's fresh-construction), HALT — the kill-switch would be unreliable.

**TL-B SRC citations**: config.py:855 (`cache: CacheConfig = field(default_factory=CacheConfig)` — verified verbatim); from_env :781-816; documented knobs :651-652; client.py:121 (default `AsanaConfig()`), :140-143 (`create_cache_provider(config=..., explicit_provider=cache_provider)`); factory.py:67 (enabled→Null), :72-73 (explicit provider), :259/:282-287 (explicit_provider precedence); NullCacheProvider `_defaults/cache.py:25` (set_versioned no-op :60).

**TL-C adversarial disposition**: the one real hazard is an environment that set the knob years ago expecting the documented behavior that never worked — the census is the control, and the operator ratifies any found flip. Test-env leakage (CI exporting `ASANA_CACHE_*`) would silently flip test posture — assert-clean in conftest.

---

## ITEM-E: ITEM-6 unpin + watches (post-merge, gated on P2)

**Scope**: TDD §7 (five-step ladder), §10 P3-P4.

**Acceptance criteria**: pins removed from entity-resolver caller drivers ONLY after CANARY-PROVEN + LIVE-LEG-PROVEN; `office_resolution.py:32-38` pin-contract docstring updated; scratchpad floodgates driver pin retired; DEFER-WATCH-1 live (method="phone" rate observable, expected 0 on well-parented offices); `cache_coverage_miss` counter observable; rollback rehearsed (env kill-switch or re-pin).

**Design references**: ADR fork (g); TDD §7.

**TL-A falsifiable prediction (BUILD-GATE)**: `batch.py:276` constructs plain `AsanaClient()` on main (verified) — therefore the flagship protects a LIVE-EXPOSED surface at merge with ZERO changes to batch.py, and after unpin the resolver walk (`office_resolution.py:260`, `_WALK_OPT_FIELDS` :69) resolves `method="hierarchy"` on well-parented offices with zero phone fallbacks in the first watched wave. A nonzero `method="phone"` rate on a well-parented office falsifies the fix (or reveals a hierarchy gap) — either way it fires the watch, loudly.

**TL-B SRC citations**: office_resolution.py:32-38 (pin contract: "the resolver's CALLERS construct AsanaClient(cache_provider=NullCacheProvider())... This module makes no cache-provider decision" — verified verbatim in docstring); :69 `_WALK_OPT_FIELDS`; :83-92 method provenance; :217 `resolve_business_gid`; :260 walk read; batch.py:276 plain `AsanaClient()`.

**TL-C adversarial disposition**: the tempting shortcut is unpinning in the same PR as the flagship — REFUSED: the ladder exists so the kill-switch and canary precede exposure. Watch the counter for hot pairs before declaring WATCHED-LIVE.

---

## ITEM-F: SIBLING-2 — floodgates accumulating deploy via deck-host (SEPARATE spike/TDD; direction ratified)

**Scope**: TDD §8. Do NOT fold into the SIBLING-1 seam (ITEM-7 DEFER-WATCH discipline, HANDOFF-arch-to-10xdev-entity-resolution-2026-07-08.md).

**Acceptance criteria (for the follow-on TDD, not this PR)**: wave-shared root (office_runner.py:197 one-liner); `--deploy-base` → deck-host `public/`; root-hygiene fail-closed allowlist (`_headers` + `^[0-9a-f]{32}$`); manifest-superset no-orphan predicate pre-surface; cross-repo `_headers` byte-parity vs `HEADERS_FILE_CONTENT`; ONE surfaced wrangler command per wave; runner never executes wrangler; **hard precondition**: operator backfill of deck-host stale `public/` PV'd against the LIVE deployed slug set — and the backfill reconciles slug **SHAPE**, not just presence (CH-01): the stale base32 dir `od67utt5a5gdbidn6b5dszjjoi` is **SUPERSEDED-DEAD** (PV'd 2026-07-08: `decks.cntently.com/od67…/` → HTTP 404 while the 8 live 32-hex slugs serve 200), so the backfill **DELETES it** rather than widening the allowlist; the allowlist refusing base32 is CORRECT behavior against dead legacy shapes. The live set at backfill time = the 8 verified 32-hex slugs (SL `20768802…`, WB `3806daae…`, TWC `11569a80…`, + `cc17b4e1…`/`a4d5dae4…`/`f2098904…`/`b7f85895…`/`0fe2aad0…`).

**Design references**: ADR fork (f); TDD §8.

**TL-A falsifiable prediction (BUILD-GATE, for the spike)**: staging two offices into one shared root via the existing `stage_deck_bundle` yields both slug dirs + ONE byte-identical `_headers` with per-slug `verify_bundle_parity` passing — proving accumulation-compatibility WITHOUT modifying `stage_deck_bundle`. If `stage_deck_bundle` mutates or removes sibling slug dirs, the Option-B premise is falsified — HALT the spike.

**TL-B SRC citations**: host_bundle.py:109 `stage_deck_bundle`, :165 verbatim `_headers` write, :56 `HEADERS_FILE_CONTENT`, :68 `_SLUG_RE`, :79 `mint_slug`, :181 `verify_bundle_parity`; office_runner.py:197 (`deploy_base / play_gid`), :137-144 (`_surface_wrangler_command`); batch.py:134/:252 (deploy_base plumbing + default); deck-host verified: `~/Code/a8t/deck-host/wrangler.toml` (`name=deck-host`, `pages_build_output_dir=public`), `public/` holds only stale `od67utt5a5gdbidn6b5dszjjoi` + `_headers`, `bin/verify.js`, `config/deck-manifest.json`.

**TL-C adversarial disposition**: the killer failure is a partial-root deploy 404ing a LIVE client deck — the no-orphan predicate must be fail-closed and run BEFORE the wrangler command is surfaced; the backfill precondition is operator-sovereign and PV'd against the deployed site (stale-slug scar: I HALTed on od67→404 once already).

---

## ITEM-G: ITEM-5 — S2S intake_resolve `task_gid` overload (TICKET, not a gate)

**Scope**: TDD §9. Sequenced AFTER ITEM-E.

**Acceptance criteria**: additive `task_gid: str | None = None` on `BusinessResolveRequest`; delegation to `office_resolution.resolve_business_gid` when present; phone path byte-identical when absent (contract tests); provenance (`method`, `ancestor_depth`) in response; `BusinessResolutionAmbiguous` ⇒ structured 4xx, never silent first-match; fallback-to-phone tagged in provenance; consumer ratifies the never-404-vs-loud-4xx call at ticket time.

**Design references**: ADR fork (g) tail; TDD §9.

**TL-A falsifiable prediction (BUILD-GATE)**: existing phone-only contract tests pass byte-identical pre/post (any diff falsifies "additive-only" — HALT).

**TL-B SRC citations**: intake_resolve.py:69 `resolve_business` (phone-only via GidLookupIndex — verified); intake_resolve_models.py:17 `BusinessResolveRequest`; office_resolution.py:217/:260/:83-94.

**TL-C adversarial disposition**: scope-creep guard — this is a ticket; any attempt to gate SIBLING-1 or ITEM-E on it is refused.

---

## Watch registry (every DEFER, per defer-watch-manifest)

| ID | Deferred item | Deferral rationale | Watch-trigger | Escalation path | Owner |
|---|---|---|---|---|---|
| DW-1 | `method="phone"` provenance rate (DEFER-WATCH-1, carried) | Fix expected to hold rate at 0 | Nonzero rate on an office with `parent.gid != None` | Investigate hierarchy gap vs coverage regression; re-pin if regression | 10x-dev |
| DW-2 | Curated implication table for exact-string false-negatives | Empirical entry criterion only; premature now | `cache_coverage_miss` shows a hot recurring (stored, missing) pair | Add ONE curated implication entry + test; never generic prefix heuristics | 10x-dev |
| DW-3 | Relationship caches (SUBTASKS/DEPENDENCIES/DEPENDENTS) | List-shaped whole-value entries; no proven starvation pair | Cross-reader projection-divergence defect on a relationship cache | Extend predicate pattern; own TDD if shape differs | arch |
| DW-4 | Unified-store read-side demand coherence | Batch readers' demand ⊆ BASE holds today, not test-enforced | Any unified-store reader's demand widens beyond BASE | Coherence property test on the unified read surface | 10x-dev |
| DW-5 | Out-of-repo `load_task_entry` writers | Fail-safe (UNKNOWN ⇒ miss-once); external contract release-noted | Elevated UNKNOWN-churn rate post-deploy | Trace external caller; thread opt_fields | 10x-dev |
| DW-6 | Coverage-miss × staleness/FreshnessIntent | One-fetch-satisfies-both is designed + tested (§6.5) but not live-graded | Double-fetch observed on a soft-stale coverage-miss | Instrument + fix the coordination point | 10x-dev |
| DW-7 | SIBLING-2 implementation (ITEM-7 carried) | Single-office runs work; not load-bearing to flagship | A batch fan-out N>1 attempted, or a prior office's deck observed orphaned at a stale Pages URL | Execute ITEM-F spike/TDD | 10x-dev |
| DW-8 | F-2 census residue | Bind is safe if census clean | Census finds a pre-existing `ASANA_CACHE_*` export | Operator ratifies the flip before merge | operator |
| DW-9 | Sibling entity caches beyond the four (stories/portfolios etc.) | No `_cache_get` hit-serve found on those paths this census | Starvation defect on any non-TASK entity cache | Apply the 3-line pattern | 10x-dev |

## Sequencing summary

P0 census → P1 one PR train (ITEM-A + B + C + D) gated on the 2-sided canary → P2 qa live leg → P3 unpin (ITEM-E) → P4 watch window → P5 ITEM-F spike/TDD and ITEM-G ticket, independent. Rollback at every rung: env kill-switch (post-D) or symmetric revert (schema-free metadata).
