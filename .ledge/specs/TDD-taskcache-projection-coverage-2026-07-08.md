---
type: spec
status: proposed
---

# TDD: Projection-Honest Entry (PHE) — TASK-cache hit-path projection coverage + F-2 env bind + sibling substrate dispositions

- **Date**: 2026-07-08
- **ADR**: `.ledge/decisions/ADR-taskcache-projection-coverage-2026-07-08.md` (ACCEPTED)
- **Fresh root (READ-ROOT for every anchor below)**: `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.knossos/worktrees/wt.arch.sibling-substrate.20260708T182700.d865d7` @ `5b5c249a` (origin/main, POST-#214). All file:line anchors re-derived on this root at authoring time (SVR). Paths below are relative to `src/autom8_asana/` unless stated.
- **Telos**: daily client trust; silent-wrong-outcome is the enemy; the batch machine must not false-HALT. Every failure direction of this design is a LOUD bounded-cost re-fetch, never a narrowed serve.
- **Evidence grade**: MODERATE (self-referential cap). External lifts: qa-adversary live canary leg; operator env census.

---

## 1. Problem (receipts)

1. **Hit path serves without coverage**: `clients/tasks.py:207-235` — `_cache_get(task_gid, EntryType.TASK)` at :208; on hit (:210) `cached_entry.data` returns at :216/:231-235 with only a warn-only hardcoded `custom_fields` canary (:225-230). No check that the entry covers the requested projection.
2. **Cache key is opt_fields-blind**: FR-CLIENT-002 (tasks.py:187); `base.py:83-121` `_cache_get` is gid+EntryType only.
3. **Miss-path union covers only the first reader**: tasks.py:244-271 — `_resolve_opt_fields(opt_fields)` (:264) ∪ `STANDARD_TASK_OPT_FIELDS` (:265), fetched (:267), cached (:271). Reader-2 with projection Q ⊄ reader-1's union is starved.
4. **STANDARD deliberately excludes `memberships.section.*`**: `models/business/fields.py:232-256` (tuple), :268-270 (exclusion rationale). The proven starvation pair: C-1-guard-first read poisoned the ACTIVE-section preflight (`link_on_play.py:158-167` requests `memberships.section.gid/name`) → `section=None` → false-HALT (DEFECT-taskcache-cross-reader-section-starvation-2026-07-08).
5. **F-2 dead knobs**: `config.py:651-652` documents `ASANA_CACHE_ENABLED`/`ASANA_CACHE_PROVIDER`; `config.py:855` is `cache: CacheConfig = field(default_factory=CacheConfig)`; `CacheConfig.from_env()` (config.py:781-816) is never called on the default path (`client.py:121`, :140-143). Only working disable: `AsanaClient(cache_provider=NullCacheProvider())` (`_defaults/cache.py:25`).
6. **Live exposure today**: floodgates batch driver constructs plain `AsanaClient()` (`automation/workflows/onboarding_walkthrough/floodgates/batch.py:276`) — never pinned on main.

## 2. Design overview

Persist the hydration projection as entry metadata at write; gate hits on a pure string-set subset check; treat non-coverage as a miss that re-hydrates a monotonically-widening union and REPLACES the entry. Ship the F-2 env bind in the same train as the rollback lever.

### 2.1 The coverage predicate (exact)

New pure module `cache/models/coverage.py` (~40 lines, stdlib only):

```python
def stored_projection(entry: CacheEntry) -> frozenset[str] | None:
    """The projection this entry was hydrated at, or None if UNKNOWN.

    Reads entry.metadata["opt_fields_used"] (the key create_completeness_metadata
    already emits, completeness.py:302, and UnifiedTaskStore already writes,
    unified.py:412/:474). Absent OR EMPTY normalizes to None (coverage-UNKNOWN):
    completeness.py:302 emits `opt_fields or []`, so a historical
    put_async(opt_fields=None) write yields [] and must not claim empty coverage.
    """
    raw = entry.metadata.get("opt_fields_used")
    if not raw:
        return None
    return frozenset(raw)

def projection_covers(entry: CacheEntry, requested: Iterable[str]) -> bool:
    """True iff the entry's stored projection is KNOWN and superset of requested.

    Exact-string subset on dotted opt_fields strings. NO prefix implication:
    stored "custom_fields" does NOT cover "custom_fields.display_value" (Asana
    compact objects genuinely differ). Every predicate error is a re-fetch,
    never a narrowed serve. UNKNOWN => not covered => miss-once-and-heal — **scoped to NON-EMPTY requests (arch ratification 2026-07-08, QA DEFECT-1)**: an EMPTY resolved projection demands nothing, and the predicate `requested ⊆ stored` is vacuously TRUE for ∅ against ANY live entry (including UNKNOWN). Serving empty requests from UNKNOWN entries is therefore predicate-CONSISTENT, not a deviation; without it every default-path `get(gid)` reader would degrade to a permanent per-read re-fetch. `_cache_get_covering` implements exactly this.
    """
    sp = stored_projection(entry)
    return sp is not None and frozenset(requested) <= sp
```

- `requested` is the **RESOLVED** set: for TASK, `_resolve_opt_fields(caller_opt_fields)` (tasks.py:292-326 — caller ∪ `_MINIMUM_OPT_FIELDS` at :325, or `STANDARD_TASK_OPT_FIELDS` when None per :316-319). For sibling clients: the caller's literal opt_fields (empty request trivially covered by any KNOWN entry).
- The predicate runs on **metadata before the raw/model branch** (tasks.py:231-235), so `raw=True` and model paths are identical by construction. No data-shape introspection: `parent=None`-vs-key-missing and empty-list-vs-absent ambiguities are structurally out of scope.

### 2.2 Entry schema / metadata changes + migration

- **Authority slot = the base `CacheEntry.metadata` dict** (entry.py:107). It serializes at entry.py:212 (`to_dict`) and defaults at :343 (`from_dict`) — schema-free, no version bump. Old code reading new entries ignores the key; new code reading old entries sees UNKNOWN. **Rollback = revert commit; entries stay valid both directions.**
- **`EntityCacheEntry.opt_fields` typed field (entry.py:380-381) is deliberately NOT the authority**: `staleness_coordinator._extend_ttl` reconstructs a base `CacheEntry` on TTL extension, spread-preserving only the metadata dict (`staleness_coordinator.py:253` — `metadata={**entry.metadata, "extension_count": new_count}`); typed subclass fields would be silently dropped. A regression test pins metadata survival through `_extend_ttl` and through soft-invalidate (`mutation_invalidator.py:286` uses `replace(entry, freshness_stamp=...)` — metadata preserved; test-pinned, no code change).
- **Metadata written**: `{"opt_fields_used": sorted(set(opt_fields)), "completeness_level": infer_completeness_level(list(opt_fields)).value}` — same keys `create_completeness_metadata` emits (completeness.py:280-302; `infer_completeness_level` at :190), so BaseClient-written and UnifiedTaskStore-written entries are predicate-compatible.
- **Migration**: none, self-healing. Pre-fix entries (bare `CacheEntry` from base.py:155-161 with empty metadata) and empty-list `opt_fields_used` entries are UNKNOWN ⇒ treated as miss ONCE, re-fetched at the union, rewritten projection-honest. In-memory providers (`_defaults/cache.py:136`, process-local dicts) reset per process — most fleets migrate instantly. Shared Redis/tiered populations drain within max entity TTL or heal on first read. `InMemoryCacheProvider.set_versioned` unconditionally overwrites (`_defaults/cache.py:250`+), so the widened entry always lands. **WATCH (QA DEFECT-3, design-inherent)**: a sibling-client coverage-miss over a LEGACY (UNKNOWN) entry replaces it with only the requested projection (the stored union term is empty for UNKNOWN), so a later empty-request reader sees a narrower entry than the legacy compact shape — the same pre-existing silent-narrow class for undeclared-demand readers; the TASK path is immune via its STANDARD union term. Escalate only if sibling default-path readers exhibit demand the census did not declare.

### 2.3 Re-hydration + TTL semantics (coverage-miss)

**FETCH-UNION-THEN-REPLACE with TTL reset. Merge is rejected.**

- Fetch ONE coherent snapshot at projection `union(resolved_requested ∪ STANDARD_TASK_OPT_FIELDS ∪ stored_projection(old_entry))`. The stored-projection term is the **anti-thrash keystone**: entry projections are monotonically non-decreasing within a cache lifetime, so two disjoint readers converge after ONE widening fetch instead of ping-ponging. Worst case: k re-fetches per gid per lifetime, k = genuinely-new field families (empirically ≤2).
- REPLACE `entry.data` wholesale; stamp `opt_fields_used` = that union. **Why not merge**: deep-merging stale stored JSON with a fresh fetch splices two `modified_at` snapshots into one object — torn reads, a NEW silent-wrong-outcome class. Because the fetch union includes the stored projection, replace loses zero fields.
- TTL resets via the existing `_resolve_entity_ttl(data)` (tasks.py:270) — honest, every byte is fresh; version re-derives from new `modified_at` (base.py:148-149).
- **Uncertain-fresh doctrine** (grafted): the fresh HTTP payload is authoritative and is served directly to the caller regardless of any predicate judgment — the miss path returns the HTTP payload (tasks.py:267-277), so no retry loop is structurally possible within a call. A persistently-uncovered (gid, demand) pair degrades to loud per-read fetches (cache-off for that pair) via the `cache_coverage_miss` counter — never wrong data.
- Bare `get_async(opt_fields=None)` still collapses to STANDARD exactly as today (tasks.py:316-319).

### 2.4 Observability

- Structured log/metric `cache_coverage_miss` on every coverage-miss: `{gid, entry_type, missing_fields: sorted(requested - stored), stored_count}`. This is the amplification tripwire; only if a hot recurring pair emerges does a CURATED implication entry get considered (never generic prefix heuristics).
- The existing `custom_fields` canary (tasks.py:225-230) is **retained, demoted** to cross-writer telemetry (fires only for metadata-less writers).
- **Requested-prefix loud canary on TRUSTED hits** (grafted, defense-in-depth): after `projection_covers` passes, WARN if any requested family's top-level prefix (`f.split(".", 1)[0]`) is absent as a key in served data — catches a lying writer (metadata stamping fields it did not fetch). Warn-only, can never cost a false miss. Labeled **UV-P** on Asana top-level key-presence semantics until QA's live leg pins it.

## 3. Integration points (all verified on fresh root @ 5b5c249a)

| # | File:line | Change |
|---|---|---|
| 1 | `clients/tasks.py:208` | Hoist `resolved = self._resolve_opt_fields(opt_fields)` above the lookup; replace `_cache_get(task_gid, EntryType.TASK)` with `_cache_get_covering(task_gid, EntryType.TASK, resolved)` |
| 2 | `clients/tasks.py:225-230` | Canary retained, demoted to cross-writer telemetry; add requested-prefix WARN canary on trusted hits |
| 3 | `clients/tasks.py:264-266` | Miss superset union gains `stored_projection(old_entry) or set()` term on coverage-miss |
| 4 | `clients/tasks.py:271` | `_cache_set(..., opt_fields=superset_opt_fields)` |
| 5 | `clients/base.py:83-121` | NEW `_cache_get_covering(key, entry_type, requested_opt_fields) -> CacheEntry | None` beside `_cache_get`: wraps it; returns None + `cache_coverage_miss` log when entry exists but `projection_covers` is False, so callers' existing miss paths fire unchanged. Must expose the stale entry to the TASK caller for the union term (return-tuple or a `_cache_peek` helper — implementer's choice, keep `_cache_get` signature untouched) |
| 6 | `clients/base.py:123-177` | `_cache_set` gains kwarg `opt_fields: Sequence[str] | None = None`; when provided, sets `metadata={"opt_fields_used": sorted(set(opt_fields)), "completeness_level": infer_completeness_level(...).value}` on the `CacheEntry` constructed at :155-161 |
| 7 | `cache/models/coverage.py` | NEW pure module: `stored_projection()` + `projection_covers()` (§2.1) |
| 8 | `cache/models/completeness.py:280-302` | Reused as metadata-key authority (`opt_fields_used` at :302; `infer_completeness_level` at :190). Harmonize: empty list = UNKNOWN in the predicate |
| 9 | `cache/models/entry.py:107/:212/:343` | No change — metadata slot + round-trip verified; :380-381 typed fields deliberately NOT the authority (test-pinned) |
| 10 | `cache/integration/staleness_coordinator.py:253` | No change — `{**entry.metadata, ...}` spread preserves projection; regression test pins it |
| 11 | `cache/integration/mutation_invalidator.py:286` | No change — `replace()` preserves metadata; test-pinned |
| 12 | `cache/providers/unified.py:412/:474` | No change — already writes `opt_fields_used` via `create_completeness_metadata(opt_fields)`; predicate-compatible day one (e.g. `hierarchy_warmer.py:246` passes `opt_fields=_HIERARCHY_OPT_FIELDS`) |
| 13 | `cache/integration/autom8_adapter.py:292-300` AND `:382-389` | **MUST, same PR**: both bare `CacheEntry(TASK)` warm-write sites gain the fetcher's projection metadata (opt_fields known at call sites) — else warmed entries are UNKNOWN and the warmer degrades to prefetch-without-serve (pure cost) |
| 14 | `cache/integration/loader.py:24/:95-106` | `load_task_entry` gains optional `opt_fields` kwarg, default None = UNKNOWN. Exported (`cache/__init__.py:110/:219`), zero internal callers — release-note the external contract |
| 15 | `clients/projects.py:105/:119`; `clients/sections.py:113/:127`; `clients/users.py:102/:116`; `clients/custom_fields.py:108/:122` | Sibling entity clients: same 3-line pattern (`_cache_get_covering` + `opt_fields=` threading). Re-hydration union = requested ∪ stored (no STANDARD analogue). Separate commit in the flagship PR; splittable to immediate fast-follow with zero rework |
| 16 | `config.py:855` | F-2 bind: `default_factory=CacheConfig` → `default_factory=CacheConfig.from_env` (§5) |
| 17 | `automation/workflows/onboarding_walkthrough/office_resolution.py:32-38` | ITEM-6 unpin site: docstring pin contract updated once flagship + canary land (§7) |
| 18 | `automation/workflows/onboarding_walkthrough/link_on_play.py:158-167` | Hoist inline preflight projection to module constant `_PREFLIGHT_OPT_FIELDS` (no behavior change; enables registry test §6.3) |

Blast radius: code surface SMALL (BaseClient +1 kwarg +1 helper, one ~40-line pure module, TASK hit/miss path, four one-pattern sibling clients, two warm-write sites, tests). Runtime surface WIDE — 35 src files call `tasks.get_async/get` (grep census on fresh root) — but the ONLY behavior delta is coverage-miss ⇒ extra fetch.

## 4. Performance budget

- Per-hit: one frozenset build over resolved request (~16-30 short strings) + one subset check — O(|requested|) hashing, low single-digit µs vs 20-50ms per saved HTTP call. The only new hit-path work beyond that is hoisting `_resolve_opt_fields`, which already ran on every miss.
- Per-entry storage: +~300-700 bytes (sorted string list).
- Write amplification: zero steady-state; transient re-fetch is union-monotone convergent (≤k per gid per lifetime). Worst case: a 40k-call batch over a fully-legacy cache = at most one extra fetch per distinct gid — exactly a cold-cache pass, strictly never worse than today's NullCacheProvider workaround, strictly better after first touch. Observable via `cache_coverage_miss`.

## 5. F-2 resolution: BIND from_env on the default path

- **The one-line fix**: `config.py:855` `cache: CacheConfig = field(default_factory=CacheConfig)` → `field(default_factory=CacheConfig.from_env)`. `from_env` (config.py:781-816) constructs a fresh Pydantic `CacheSettings` per call; factory chain already honors the result (`factory.py:67` enabled→`NullCacheProvider`; `:72-73` explicit provider; `create_cache_provider` at :259, `explicit_provider` wins at :282-287). Precedence preserved exactly as documented (config.py:787): explicit `AsanaConfig(cache=...)` bypasses the default_factory (client.py:121); explicit `AsanaClient(cache_provider=...)` still wins (client.py:140-143).
- **Why bind, not delete**: `ASANA_CACHE_ENABLED=false` becomes the zero-code-mutation operator kill-switch for the whole coverage machinery — live BEFORE ITEM-6 widens exposure. Deletion would orphan the from_env/CacheSettings/factory apparatus and remove the cheapest blast-radius lever at maximum exposure. The doc-vs-behavior lie dies in the doc's favor.
- **Guardrails (grafted)**: (1) startup INFO log — `"cache config bound from env: enabled=X provider=Y"` — any behavior flip is loud; (2) **pre-merge fleet env census**: grep deploy/env manifests for pre-existing `ASANA_CACHE_*` exports; any found flip is an operator-ratification fork before merge; (3) changelog callout; (4) regression test: monkeypatch `ASANA_CACHE_ENABLED=false` ⇒ default `AsanaClient()`'s provider is `NullCacheProvider`; unset env ⇒ auto-detect behavior byte-identical (the test that was impossible to write truthfully before the bind); (5) verify CI env is clean of `ASANA_CACHE_*`.

## 6. Test plan

### 6.1 THE 2-SIDED STARVATION CANARY (sprint gate)

In `tests/unit/clients/test_tasks_cache_superset_hydration.py` (extends the existing suite; fixtures at :80-100 already model live shapes — `"parent": None` at :88) or a sibling module, with a **fake transport** that echoes exactly the requested `opt_fields` params (memberships elements carry `section` iff `memberships.section.*` was requested — reproducing the proven probe):

- **RED-before** (run against CURRENT hit path, pre-fix): reader-1 `get_async(gid, opt_fields=["gid", "name"])` (the C-1-guard projection), then reader-2 `get_async(gid, opt_fields=["memberships.section.gid", "memberships.section.name"])`. Assert reader-2's served data carries the `section` family OR a second HTTP fetch occurred whose params include `memberships.section.name`. **This test FAILS on current main**: the second read HITs (one total HTTP call) and serves section-less memberships (`section=None`) — the exact false-HALT poisoning from DEFECT-taskcache-cross-reader-section-starvation-2026-07-08.
- **GREEN-after**: same sequence post-fix ⇒ coverage-miss ⇒ second HTTP call carrying the union (asserted at the params level to include `memberships.section.*` AND reader-1's stored projection term), reader-2's data carries `memberships.section`.
- **TEETH / no-defect arm** (grafted): reader-2 with requested ⊆ stored union ⇒ HIT with **ZERO** extra HTTP calls — proves the predicate bites only on the defect and the cache still serves.
- **Ping-pong regression** (grafted): alternate the two disjoint readers ×N on one gid ⇒ exactly **2 total HTTP calls** (initial + one widening) — pins the union-monotone anti-thrash property of the stored-projection term.

### 6.2 Predicate + metadata unit tests (`tests/unit/cache/test_coverage_predicate.py`)

- Subset semantics: exact-string only; stored `custom_fields` does NOT cover `custom_fields.display_value`; equal sets covered; empty request covered by ANY live entry — KNOWN or UNKNOWN (vacuous truth; arch-ratified per QA DEFECT-1).
- UNKNOWN normalization: metadata absent ⇒ None; `opt_fields_used: []` ⇒ None (the `completeness.py:302 opt_fields or []` shape); both ⇒ miss-once.
- raw/model parity: predicate result identical regardless of the `raw` flag (runs pre-branch).
- **Metadata survival invariants**: projection survives `staleness_coordinator._extend_ttl` (the `{**entry.metadata,...}` spread at :253) and `mutation_invalidator` soft-invalidate (`replace()` at :286); a test constructing an `EntityCacheEntry` proves typed `opt_fields` (:380-381) would NOT survive `_extend_ttl` — pinning why metadata is the authority.
- Serialization round-trip: `opt_fields_used` survives `to_dict`/`from_dict` (entry.py:212/:343).

### 6.3 Caller-constant registry coherence test (grafted from superset lens)

New `tests/unit/clients/test_projection_registry_coverage.py`, parametrized over every registered in-repo caller constant — `STANDARD_TASK_OPT_FIELDS`, `DETECTION_OPT_FIELDS` (fields.py:282-286), `_MINIMUM_OPT_FIELDS` (tasks.py:41-47), `BASE_OPT_FIELDS` (dataframes/builders/fields.py:35), `_HIERARCHY_OPT_FIELDS` (hierarchy_warmer.py:28), `field_write_service._TASK_OPT_FIELDS` (:56), `office_resolution._WALK_OPT_FIELDS` (:69), `link_on_play._PREFLIGHT_OPT_FIELDS` (hoisted from :158-167) — asserting each projection is **served covered after first hydration** (write at that projection ⇒ read at that projection HITs with zero extra fetches; cross-pair reads converge in ≤1 widening). Docstring rule: **new `get_async` caller projections MUST be module constants registered here** — projection growth stays visible and deliberate.

### 6.4 Writer-census tests

- Warmer honesty: both `autom8_adapter` write sites (:292-300, :382-389) produce entries whose first `get_async` read at the fetcher's projection HITs (no re-fetch) — RED without the ITEM-C fix.
- `loader.load_task_entry` with `opt_fields=` stamps metadata; without ⇒ UNKNOWN ⇒ heals on first read.
- Existing non-poisoning guard stays GREEN: `test_tasks_cache_superset_hydration.py:270-311` (list_async/subtasks_async write no TASK entries); `test_min_opt_fields_detection_coherence.py:25-31` unchanged.

### 6.5 Interaction + F-2 tests

- **Coverage-miss × staleness single-fetch**: a coverage-miss on a soft-stale entry does ONE fetch satisfying both (no double-fetch) — the one explicit test the design claim needs before grading above asserted.
- F-2 regression per §5 guardrail (4); sibling-client coverage tests mirror §6.1 minimally per client.

## 7. ITEM-6 unpin plan + DEFER-WATCH-1 (the five-step ladder)

1. **Land** SIBLING-1 flagship + siblings + warmer/loader fix + F-2 bind as ONE train (kill-switch exists before exposure widens).
2. **Gate** on §6.1 canary (RED-before reproduced, GREEN-after, teeth, ping-pong) — qa-adversary runs the live leg (self-assessment caps MODERATE; external leg is the STRONG lift).
3. **Unpin**: remove `NullCacheProvider()` pins from the entity-resolver caller drivers per the pin contract at `office_resolution.py:32-38` (the module makes no cache decision; callers pin); update that docstring; retire the scratchpad floodgates driver pin. Note: `batch.py:276` constructs plain `AsanaClient()` and was NEVER pinned — it is exposed TODAY and becomes protected at merge, before any unpin step.
4. **Watch**: (a) **DEFER-WATCH-1** — `method="phone"` provenance rate stays **0** on well-parented offices (`office_resolution.py:83-92`; `BusinessResolution.method` at :92) — the starvation tripwire; (b) `cache_coverage_miss` counter with `missing_fields` payload — the amplification tripwire.
5. **Rollback**: `ASANA_CACHE_ENABLED=false` (live via §5) or plain revert — schema-free metadata makes rollback symmetric.

## 8. SIBLING-2: floodgates accumulating deploy — Option B, stage-INTO-deck-host (right-sized; SEPARATE spike/TDD)

**Defect**: `host_bundle.stage_deck_bundle` (host_bundle.py:109-178) stages ONE office (`<root>/<slug>/index.html` + `_headers` at :165); `office_runner` nests per office (`office_deploy_root = deploy_base / play_gid`, office_runner.py:197) and surfaces `wrangler pages deploy <office-root>` (:137-144). Pages custom domain is latest-deployment-only ⇒ per-office deploys 404 every prior office including LIVE client decks. Worked around 2026-07-08 by hand-assembled combined root.

**Chosen shape** (ratified direction; implementation belongs to its own TDD per ITEM-7 DEFER-WATCH discipline — do NOT fold into the SIBLING-1 seam):
1. **Wave-shared root**: drop the `/play_gid` nesting at office_runner.py:197 (one line; 32-hex slug dirs are collision-free by `_SLUG_RE`, host_bundle.py:68); stage all offices of a wave into `deploy_base` directly; surface **ONE** wrangler command per wave (`_surface_wrangler_command` signature unchanged, :137-144).
2. **Cross-wave accumulation**: point `--deploy-base` (batch.py:252) at the deck-host checkout's `public/` (verified: `~/Code/a8t/deck-host/wrangler.toml` — `name = "deck-host"`, `pages_build_output_dir = "public"`; committed `config/deck-manifest.json`; `bin/verify.js`). `stage_deck_bundle` is already accumulation-compatible (slug-dir write + idempotent byte-constant `_headers`).
3. **Root-hygiene fail-closed guard**: allowlist = `_headers` + dirs matching `^[0-9a-f]{32}$`; any stray path REFUSES the stage before wrangler can publish it (closes the doctrine-vs-enforcement gap that goes live once the root is shared).
4. **No-orphan predicate**: every slug in `config/deck-manifest.json` must exist in the staged root before the wrangler command is surfaced (loud failure closes the 404-orphan class).
5. **Cross-repo `_headers` parity**: deck-host's `public/_headers` must byte-equal `HEADERS_FILE_CONTENT` (host_bundle.py:56) — two copies must not drift. Byte-parity + WS-GUARD headers non-negotiable; served-parity re-check via the existing `verify_bundle_parity` (host_bundle.py:181) predicate.
6. **Reserved lever stands**: runner SURFACES wrangler, never runs it; manifest update + git commit + wrangler execution = operator.

**Rejected**: Option A (accumulating root inside floodgates) — re-mints the deck-host ledger in ephemeral `.sos` state; a fresh checkout re-orphans LIVE decks (the silent-404 class re-minted). Option C (CF API additive upload) — fights Pages' immutable whole-tree snapshots, abandons the wrangler lever + parity harness for an unproven CF contract.

**HARD PRECONDITION (operator)**: deck-host `public/` is STALE (verified: holds only the SUPERSEDED `od67utt5a5gdbidn6b5dszjjoi` slug). Backfill from the LIVE deployed slug set — **PV the deployed site, never a local manifest** (standing scar) — then `bin/verify.js` + `verify_bundle_parity` per slug before the first accumulated deploy.

## 9. ITEM-5: S2S intake_resolve hierarchy overload (ticket spec — NOT a gate)

Additive-only, zero change for existing callers. Estimate: S (~1 day incl. contract tests).

1. `BusinessResolveRequest` (`api/routes/intake_resolve_models.py:17`) gains optional `task_gid: str | None = None`; `office_phone` contract unchanged.
2. `resolve_business` (`api/routes/intake_resolve.py:69`): `task_gid` present ⇒ delegate to the SHIPPED store-independent resolver `office_resolution.resolve_business_gid` (:217, on main since #214; walk read at :260 uses `_WALK_OPT_FIELDS` :69 — exactly the cross-reader shape the coverage guard exists for). Absent ⇒ existing O(1) `GidLookupIndex` phone path byte-identical.
3. Response additively carries provenance (`method: "hierarchy"|"phone"`, `ancestor_depth` — `BusinessResolution` fields at office_resolution.py:83-94), extending DEFER-WATCH-1 to the S2S surface.
4. **Loud-refusal mapping** (grafted): `BusinessResolutionAmbiguous` ⇒ structured 4xx collision envelope (never silent first-match); depth-exhausted/no-business ⇒ fallback to the phone path iff `office_phone` also supplied (tagged in provenance), else existing not-found semantics. The never-404-vs-loud-4xx tension on the S2S surface is the consuming service's contract call — ratify at ticket time.
5. Acceptance: phone-only requests byte-identical pre/post; task_gid happy/ambiguous/exhausted/fallback-tagged paths tested.
6. **Sequencing**: AFTER SIBLING-1 merge + ITEM-6 unpin (so the route needs no pin). If forced earlier: route's client pins `NullCacheProvider` per the documented unblock — one line, removed at unpin.

## 10. Phased rollout with rollback

| Phase | Content | Gate | Rollback |
|---|---|---|---|
| P0 | Pre-merge fleet env census for `ASANA_CACHE_*` exports | Any found flip ⇒ operator ratifies | n/a |
| P1 | ONE PR train: coverage module + BaseClient + TASK flagship + sibling clients (separate commit) + warmer/loader threading + F-2 bind + full §6 suite | 2-sided canary RED-before/GREEN-after + teeth + ping-pong; existing suites GREEN | revert PR (schema-free metadata, symmetric) |
| P2 | qa-adversary live leg: canary suite against live Asana; UV-P prefix-canary axiom probe | qa verdict | `ASANA_CACHE_ENABLED=false` |
| P3 | ITEM-6 unpin (resolver caller drivers; docstring; scratchpad driver retirement) | P2 green | re-pin `NullCacheProvider` (one line per driver) or env kill-switch |
| P4 | Watch window: DEFER-WATCH-1 `method="phone"` = 0 on well-parented offices; `cache_coverage_miss` hot-pair scan | nonzero ⇒ escalate per watch registry | env kill-switch stays available |
| P5 | ITEM-5 ticket; SIBLING-2 spike/TDD (own artifact) | independent | independent |

## 11. Risks (carried from ADR, implementation-facing)

R1 exact-string false-negatives ⇒ spurious re-fetches (mitigate: `cache_coverage_miss` telemetry; curated implication only on empirical hot pair). R2 warmer neutering if ITEM-C slips (promoted to same-PR MUST; both write sites :292 and :382). R3 future contributor moves projection to typed field and `_extend_ttl` drops it (invariant test §6.2). R4 out-of-repo `load_task_entry` writers keep writing UNKNOWN entries (fail-safe; release-note; watch UNKNOWN-churn). R5 Redis value growth ~0.5KB/entry (state in PR for capacity review). R6 F-2 bind flips dormant env vars live (census + startup log + changelog). R7 sibling-client review pressure ⇒ split fast-follow (zero rework). R8 coverage-miss × staleness interaction (one explicit test, §6.5).
