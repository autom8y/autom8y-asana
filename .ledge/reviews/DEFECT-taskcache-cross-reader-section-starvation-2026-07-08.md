---
type: review
status: proposed
---

# DEFECT — TASK-cache cross-reader section starvation (the #212 residual, DEFER-WATCH FIRED)

- Date: 2026-07-08 (Wholebody floodgates re-pilot, resume phase)
- Severity: HIGH for batch operability (false-HALTs the fleet fan-out); client_impact: NONE (fail-closed refusal — the guard direction held)
- Discovered by: n=1 re-pilot resume on PLAY 1213916452918376 — the pilot discipline catching the class AGAIN before any batch
- Status: root-caused two-sided; UNBLOCKED via the documented `NullCacheProvider()` injection; fleet fix NOT YET BUILT

## Symptom

`--phase resume` refused with `task 1213916452918376 is not in project 1209442849265632 ACTIVE
section` while live Asana showed the task IS in ACTIVE (section 1209442954085037, unmodified
since 2026-07-02). Produce had passed the identical preflight 2h earlier.

## Root cause (proven two-sided, probe `fg_resume_nullcache.py` sibling `probe_cache_order.py`)

1. The TASK cache hit path serves the stored entry with NO projection-coverage check
   (`clients/tasks.py:209-235`; the completeness canary only WARNS, and only about custom_fields).
2. `STANDARD_TASK_OPT_FIELDS` deliberately EXCLUDES `memberships.section.*`
   (`models/business/fields.py:271` — "LIST/sweep consumer, not a get()-path detection input").
3. Resume's read order is C-1-guard-first: its miss stores `union(C-1-projection ∪ STANDARD)`
   — WITHOUT section fields — and the link_on_play preflight then HITS that narrowed entry →
   memberships carry `section=None` → false "not in ACTIVE".

Two-sided receipt (same env, fresh client per side):
- side1 preflight-first: `memberships(project,section)=[('1209442849265632','1209442954085037')]` ✅
- side2 C-1-first:      `memberships(project,section)=[('1209442849265632', None)]` ❌

The #212 union fix guarantees the invariant only for the FIRST reader of a gid. The thermia
invariant ("a read at projection P returns a value satisfying P, or a miss") is violated for
every cross-reader sequence where reader-2's projection ⊄ reader-1's union. This is the
qa-adversary's "STANDARD ⊉ all callers" warning surfacing on the READ side.

## Two companion config-surface findings (same litigation)

- F-2: `ASANA_CACHE_ENABLED` / `ASANA_CACHE_PROVIDER` env knobs DO NOT BIND on the default
  `AsanaClient()` path — env vars are only read via `CacheConfig.from_env()`, but the default
  constructs plain `CacheConfig()` (`config.py:644+`, `client.py:140-143`). Documented knobs
  that silently no-op.
- F-3: the only working disable is the documented explicit injection
  `AsanaClient(cache_provider=NullCacheProvider())` (`client.py:98`, `_defaults/cache.py:25`).

## Unblock used (2026-07-08, zero code mutation)

Scratchpad driver constructs `AsanaClient(cache_provider=NullCacheProvider())` and calls the
floodgates' own `run_batch` — all in-code guards (C-1 sha, served byte-parity, markers,
personalization) enforced on LIVE data. Resume dry-run GREEN → execute GREEN → 3 kits posted
exactly-once (link 1216390179511633, template 1216390077271899, card 1216390330223397),
read-back verified (routing addr 0507ae4e…, zero foreign-tenant leak, real <table>).

## Fleet fix direction (for the substrate sprint — NOT built yet)

Primary: hit-path projection-coverage check — serve from cache ONLY IF stored keys cover the
requested projection; else treat as miss and hydrate `union(stored ∪ requested ∪ STANDARD)`.
This closes the CLASS (any field family, any read order), not the instance.
Secondary candidates (weaker, instance-shaped — rejected as primary): add memberships.section
to STANDARD (inflates every entry; whack-a-mole); reorder resume reads (fixes one caller).
Also fix F-2 (bind `CacheConfig.from_env()` on the default path, or delete the documented knobs).

## Watch

The bare-get scalar-narrowing DEFER-WATCH (appended to
`DEFECT-floodgates-optfields-blind-cache-poisoning-2026-07-07.md`) predicted this class;
this artifact is its FIRING receipt. Batch fan-out across the remaining ACTIVE offices should
either carry the NullCacheProvider driver or wait for the coverage-check fix.
