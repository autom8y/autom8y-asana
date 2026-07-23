---
type: decision
status: accepted
---

# ADR: TASK-cache hit-path projection coverage — metadata-persisted projection (PHE: Projection-Honest Entry)

- **Date**: 2026-07-08
- **Status**: ACCEPTED (pythia adjudication, arch sprint sibling-substrate)
- **Fresh root**: `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.knossos/worktrees/wt.arch.sibling-substrate.20260708T182700.d865d7` @ `5b5c249a` (origin/main, POST-#214). Every file:line below re-derived on this root at authoring time (SVR).
- **Companion spec**: `.ledge/specs/TDD-taskcache-projection-coverage-2026-07-08.md`
- **Handoff**: `.ledge/reviews/HANDOFF-arch-to-10xdev-sibling-substrate-2026-07-08.md`
- **Evidence grade**: MODERATE (self-referential cap per self-ref-evidence-grade-rule; the qa-adversary live canary leg is the external lift)

## Context

Proven two-sided defect (`.ledge/reviews/DEFECT-taskcache-cross-reader-section-starvation-2026-07-08.md`): `TasksClient.get_async` serves a cached TASK entry with **no check that the stored entry covers the requested projection**. The hit path (`src/autom8_asana/clients/tasks.py:207-235`) returns `cached_entry.data` at :216 guarded only by a warn-only `custom_fields` canary (:225-230). The TASK cache key is opt_fields-blind (FR-CLIENT-002, tasks.py:187); `STANDARD_TASK_OPT_FIELDS` (`models/business/fields.py:232-256`) deliberately excludes `memberships.section.*` (:268-270). So a first reader whose hydration union lacks a field family **starves every later reader** that needs it: the C-1-guard-first read order poisoned the ACTIVE-section preflight (`memberships` carried `section=None`) and false-HALTed the floodgates batch. Fail-closed, zero client harm — but it would false-HALT every batch, and the class can starve ANY cross-reader pair. The #212 miss-path union fix (tasks.py:244-271) covers only the FIRST reader's projection; cross-reader starvation stands.

Companion defect F-2: documented env knobs `ASANA_CACHE_ENABLED` / `ASANA_CACHE_PROVIDER` (config.py:651-652) never bind on the default `AsanaClient()` path — the default constructs plain `CacheConfig()` (config.py:855, client.py:121, :140-143); `CacheConfig.from_env()` (config.py:781-816) is never called. The only working disable is explicit `AsanaClient(cache_provider=NullCacheProvider())` (`_defaults/cache.py:25`).

Current workaround: the entity resolver's callers and floodgates drivers pin `NullCacheProvider()` (pin contract documented at `office_resolution.py:32-38`). Verified nuance raising urgency: the floodgates batch driver constructs a **plain `AsanaClient()`** (`floodgates/batch.py:276`) — it was never pinned on main and is exposed to the class TODAY.

## Decision

**Adopt metadata-persisted projection coverage (PHE).** Persist the union of opt_fields strings hydrated at miss-time as entry metadata (`opt_fields_used` — reusing the key `UnifiedTaskStore.put/put_batch` already writes via `create_completeness_metadata`: `unified.py:412/:474`, `completeness.py:302`), and gate every hit on a pure string-set subset check: **serve only if resolved-requested ⊆ stored-projection; else treat as miss and re-hydrate at the union (requested ∪ STANDARD ∪ stored-projection), REPLACE the entry, reset TTL.** Absent-or-empty metadata = coverage-UNKNOWN = miss-once-and-heal.

Also decided in the same train:
- **F-2: BIND, don't delete** — one line: `config.py:855` `default_factory=CacheConfig` → `default_factory=CacheConfig.from_env`. `ASANA_CACHE_ENABLED=false` becomes the zero-code-mutation operator kill-switch, live BEFORE ITEM-6 widens exposure.
- **Warmer coherence is in-scope MUST**: `autom8_adapter.py:292-300` and `:382-389` construct bare `CacheEntry` TASK writes with no metadata — unfixed, every warmed entry is coverage-UNKNOWN and the warmer degrades to prefetch-without-serve.
- **SIBLING-2 (floodgates accumulating deploy): Option B — stage-INTO-deck-host** (`~/Code/a8t/deck-host`, verified: `wrangler.toml name=deck-host, pages_build_output_dir=public`; committed `config/deck-manifest.json`; `bin/verify.js`), kept as a SEPARATE spike/TDD per ITEM-7 DEFER-WATCH discipline.
- **ITEM-5 (S2S intake_resolve `task_gid` overload): ticket, not gate**, sequenced after SIBLING-1 + ITEM-6 unpin.

## Options litigated (pythia scores)

| Option | Score | Verdict |
|---|---|---|
| **metadata-projection-entry (PHE)** | **8.9** | **CHOSEN** |
| minimal-hit-guard (shape-derived introspection + reflected widening) | 7.3 | Rejected; test doctrine + operational grafts harvested |
| TASK_CACHE_SUPERSET_OPT_FIELDS (kill-at-write + provenance digest) | 7.0 | Rejected; coherence-registry test graft harvested |

**Why PHE wins** (decision rationale, condensed):
- **Closes the CLASS, not the instance** (9.5): coverage holds for ARBITRARY projections including out-of-repo callers and future field families. The only failure direction is a spurious re-fetch — never a silently-narrowed serve. UNKNOWN entries miss-once-and-heal.
- **Predicate correctness** (9.5): pure set math on persisted dotted strings. Zero platform-shape axioms; `parent=None`-vs-key-missing is structurally out of scope; identical on `raw=True` and model paths (predicate runs on metadata before the branch at tasks.py:231-235).
- **Reuse-not-remint** (9.5, VERIFIED): `UnifiedTaskStore` already writes `opt_fields_used` (unified.py:412/:474); the metadata dict round-trips serialization (entry.py:212/:343) and survives TTL-extension rewrites (`staleness_coordinator.py:253` spreads `{**entry.metadata, ...}`) and soft-invalidate (`mutation_invalidator.py:286` uses `replace()`). PHE wires an existing convention into the read path.
- **Migration** (9.0): none — schema-free metadata dict, no version bump; legacy entries drain within entity TTLs or heal on first read; rollback is symmetric.

**Why not minimal-hit-guard** (7.3): rests on the load-bearing UV-P axiom "Asana keys every requested field, null/[] when valueless" — unverified live for every custom-field family — plus two curated drift surfaces (`_CF_SUBTYPE_TO_VALUE_KEY` table, `COVERAGE_REFLECTION_VOCABULARY`). It litigates the FRAME's "data-shape introspection is FRAGILE" warning toward the fragile side. Its test doctrine (ping-pong bound, teeth arm, uncertain-fresh authority) and F-2/SIBLING-2 guardrails are harvested as grafts.

**Why not superset+digest** (7.0): structural residual — an out-of-repo consumer requesting an unregistered field is SERVED A NARROWED ENTRY with only a WARN: the telos enemy (silent-wrong-outcome) demoted to logged-wrong-outcome but still served wrong. Plus permanent 1.5-3x payload inflation on every miss (forced `notes` inclusion), fighting fields.py:268-270's deliberate section-exclusion design, and wholesale distrust of writers that already stamp correct metadata. Its coherence-registry property-test pattern is harvested.

## Fork resolutions

**(a) Coverage predicate mechanism → METADATA-PERSISTED-PROJECTION.** `covers(entry, requested) := opt_fields_used present-and-non-empty AND frozenset(resolved_requested) ⊆ frozenset(opt_fields_used)`. Absent-or-empty normalizes to UNKNOWN ⇒ miss-once-and-heal. Exact-string subset only — NO prefix-implication heuristics (stored `custom_fields` does NOT cover `custom_fields.display_value`; false-negatives cost one re-fetch, never starvation). Data-shape introspection REJECTED (unverified live-API axiom + two curated drift surfaces). STANDARD-as-global-superset REJECTED (warn-only narrowed-serve residual + unbounded payload inflation). Authority slot = the **metadata dict**, NOT `EntityCacheEntry` typed fields (entry.py:380-381) — verified that `staleness_coordinator._extend_ttl` reconstructs a base `CacheEntry` spread-preserving metadata (:253) and would silently drop typed fields; a regression test pins metadata survival.

**(b) Merge-vs-replace + TTL → FETCH-UNION-THEN-REPLACE with TTL reset.** Union = resolved-requested ∪ `STANDARD_TASK_OPT_FIELDS` ∪ stored_projection(old_entry). The stored-projection term is the anti-thrash keystone: entry projections are monotonically non-decreasing within a cache lifetime, so disjoint reader pairs converge after ONE widening fetch (pinned by the ping-pong regression test). MERGE REJECTED: splicing stored-T1 bytes with fresh-T2 bytes manufactures torn reads across `modified_at` snapshots — a NEW silent-wrong-outcome class; because the fetch union includes the stored projection, replace loses zero fields. TTL reset honest (every byte fresh); version re-derives from new `modified_at` (base.py:148-149).

**(c) Other writers — scope split by VERIFIED writer census.** Non-writers confirmed: `list_async`/`subtasks_async` write no TASK entries (pinned GREEN by `test_tasks_cache_superset_hydration.py:270-311`); search caches DataFrames, not TASK entries. IN-SCOPE MUST: (1) `autom8_adapter.py:292-300` and `:382-389` warm writes gain projection metadata (fetcher's opt_fields known at call sites); (2) `loader.py:24/95-106` `load_task_entry` gains optional `opt_fields` kwarg, default None=UNKNOWN (exported at `cache/__init__.py:110/:219`, zero internal callers — release-note the external contract); (3) harmonize unified.py's empty-list `opt_fields_used` (from `put(opt_fields=None)`, completeness.py:302 `opt_fields or []`) as UNKNOWN in the predicate. WATCH: unified-store read-side demand coherence; out-of-repo `load_task_entry` callers.

**(d) Other entity caches → SAME SPRINT, SPLITTABLE FAST-FOLLOW.** The predicate module ships generic; TASK is the gated flagship. Projects/sections/users/custom_fields share the exact opt_fields-blind hit-serve pattern (verified: projects.py:105/:119, sections.py:113/:127, users.py:102/:116, custom_fields.py:108/:122) and get the mechanical 3-line pattern (re-hydration union = requested ∪ stored; no STANDARD analogue) as a separate commit — split to an immediate fast-follow PR if review pressure demands (zero rework; predicate is shared). Relationship entry types (SUBTASKS/DEPENDENCIES/DEPENDENTS): WATCH ONLY (list-shaped whole-value entries, no proven starvation pair).

**(e) F-2 bind-vs-delete → BIND** (unanimous across all three candidates). One line at config.py:855. `from_env` reads a fresh Pydantic `CacheSettings` per construction (config.py:781-816); explicit-config precedence (client.py:121) and explicit-provider precedence (client.py:140-143, factory.py:282-287) untouched; factory chain already honors enabled/provider (factory.py:67/:72). Rationale over deletion: the rollout NEEDS a zero-code-mutation kill-switch exactly when exposure is maximal; deletion would orphan the from_env/CacheSettings/factory apparatus. Guardrails (grafted): startup INFO log of bound values; pre-merge fleet env census for pre-existing `ASANA_CACHE_*` exports (operator ratifies any found flip); changelog callout; end-to-end regression test that `AsanaClient()` honors `ASANA_CACHE_ENABLED=false`.

**(f) SIBLING-2 deploy model → OPTION B, stage-INTO-deck-host** (unanimous; separate spike/TDD per ITEM-7, NOT folded into this seam). deck-host IS the durable accumulation substrate (verified: `wrangler.toml pages_build_output_dir=public`; committed `config/deck-manifest.json`; `bin/verify.js`). Option A (accumulating root inside floodgates) re-mints that ledger in ephemeral `.sos` state (batch.py:252 default) — a fresh checkout re-orphans prior LIVE decks: the same silent-404 class re-minted. Option C (CF API additive upload) fights Pages' immutable whole-tree snapshot model and abandons the wrangler operator lever (office_runner.py:137-144), the reserved-lever boundary, and the parity harness. Ship shape (grafted): wave-shared root via the `office_runner.py:197` one-liner (drop `/play_gid` nesting; 32-hex slug dirs collision-free per host_bundle.py:68); `--deploy-base` points at deck-host/public; root-hygiene fail-closed allowlist (`_headers` + `^[0-9a-f]{32}$` dirs only); manifest-superset no-orphan predicate before the ONE surfaced wrangler command per wave; cross-repo `_headers` byte-parity vs `HEADERS_FILE_CONTENT` (host_bundle.py:56). HARD PRECONDITION: operator backfill of deck-host's STALE `public/` (verified: holds only the SUPERSEDED `od67utt5…` slug) reconciled against the LIVE deployed slug set — PV the live deployment, never a local manifest (standing scar).

**(g) ITEM-6 unpin sequencing → FIVE-STEP LADDER.** (1) Land SIBLING-1 + F-2 bind + warmer fix as one train. (2) Gate on the 2-sided canary (RED-before on the exact proven defect pair; GREEN-after; teeth arm; ping-pong bound); qa-adversary runs the live leg. (3) Unpin `NullCacheProvider` in the entity-resolver caller drivers per the office_resolution.py:32-38 pin contract (batch.py:276 was never pinned — protected at merge, before any unpin). (4) Watch: DEFER-WATCH-1 `method="phone"` rate stays 0 on well-parented offices (office_resolution.py:83-92 provenance) + the new `cache_coverage_miss` counter with `missing_fields` payload. (5) Rollback: `ASANA_CACHE_ENABLED=false` or plain revert (schema-free metadata makes rollback symmetric). ITEM-5 lands AFTER unpin.

## Consequences

**Positive**: the false-HALT class dies — the second reader always gets its fields (worst case one extra fetch, union-monotone convergent, ≤k widenings per gid per cache lifetime where k = new field-families, empirically ≤2). Silent-narrowed serves become structurally impossible for entries with known projections; UNKNOWN entries heal on first touch. The operator gains a live kill-switch. The doc-vs-behavior lie (F-2) dies in the doc's favor. The floodgates batch driver (exposed today at batch.py:276) is protected the moment the flagship merges.

**Negative / accepted costs**: +~300-700 bytes per entry (sorted opt_fields list); microsecond-scale subset check per hit (vs 20-50ms per saved HTTP call); a bounded one-time re-fetch wave over legacy metadata-less populations (at most one extra fetch per distinct gid — never worse than the current NullCacheProvider workaround); exact-string subset can false-negative on semantically-implied fields (accepted: cost is one re-fetch, observable via `cache_coverage_miss`; a CURATED implication entry is considered only if telemetry shows a hot pair); F-2 binding flips long-dormant env vars live (mitigated by census + changelog + startup log).

**Deliberate non-choices**: `EntityCacheEntry.opt_fields` typed field NOT adopted as authority (dropped by `_extend_ttl` reconstruction — test-pinned); no prefix-implication heuristics; no STANDARD inflation; relationship caches untouched; SIBLING-2 and ITEM-5 remain separate artifacts.

## Open forks (watch-registered in HANDOFF)

Curated implication table (empirical entry criterion only); sibling-clients ride-along vs fast-follow split (review-pressure call, zero rework); F-2 env census outcome (operator sovereignty); coverage-miss × staleness single-fetch interaction (needs its one explicit test); SIBLING-2 backfill procedure (separate TDD); ITEM-5 never-404-vs-loud-4xx contract (consumer ratifies); unified-store read-side demand coherence; out-of-repo `load_task_entry` writers.
