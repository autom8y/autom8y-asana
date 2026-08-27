---
type: review
status: open
type_note: live-integration defect report (n=1 pilot finding)
severity: HIGH (blocks all floodgates execution; not client-facing — fail-closed)
date: 2026-07-07
initiative: client-onboarding-delivery / floodgates
found_by: n=1 pilot (Wholebody Systems) on merged main 7a60f2e1 (#208)
client_impact: NONE — Phase-1 is local, failed before any produce/deploy/post; zero client mutation
---

# DEFECT: floodgates Phase-1 guid resolution fails on opt_fields-blind TASK cache poisoning

## Symptom
`batch --phase produce --office <PLAY> --clinic <name>` fails (reproducibly, not
transient) for the first non-Sand-Lake office:
```
[failed] 1213916452918376 outcome=None — no Office Phone on PLAY task 1213916452918376:
cannot resolve the office guid. Escalate (spec §2) — never hand-type a routing address.
```
The resolver is NOT broken: called standalone,
`_resolve_office_guid(client, task_gid=1213916452918376)` returns the correct guid
`0507ae4e-b597-4994-80f4-870a90ae7ec5`, and `_read_office_phone` returns `+14049877908`.
The failure is order-and-cache dependent inside the office_runner flow.

## Root cause (confirmed)
`office_runner._run_produce` (office_runner.py:218-220):
1. `await _preflight(client, play_gid)` reads the PLAY task for NAME + ACTIVE
   membership — opt_fields that do NOT include `custom_fields`.
2. `await _resolve_office_guid(client, task_gid=play_gid)` → `_read_office_phone`
   (contact_synthesis.py:365) reads the SAME task with
   `opt_fields=["custom_fields.name","custom_fields.display_value"]`.

The tasks client TASK cache is **opt_fields-blind** — keyed on `task_gid` only
(`clients/tasks.py:208` `_cache_get(task_gid, EntryType.TASK)`; the code's OWN
comment at `tasks.py:235`: "opt_fields-blind TASK cache key"). So step-1's
custom-field-less read populates the cache; step-2 hits it and gets a task with NO
`custom_fields` → `_office_phone_from_task` → None → "no Office Phone" → abort.

Standalone the order is reversed (custom_fields read first), so the cache is warm
WITH custom_fields and the resolve succeeds — which is why the unit-test fakes
(no cache model) and the standalone probe both pass. Classic green-tests / red-live.

## Blast radius
Affects EVERY office (Sand Lake's kit was posted before this two-phase orchestrator
existed, via the standalone posters — never through this preflight-first path). A
batch run would have failed all 7 identically. The n=1 pilot caught it before any
client task was touched (Wholebody PLAY confirmed 0 automation comments post-pilot).

## Fix options (10x-dev, smallest sufficient)
1. **Force-fresh the custom_fields read** in `_read_office_phone` / `_resolve_office_guid`
   (bypass or invalidate the TASK cache for this read), OR
2. **`_preflight` hydrates a superset** (include `custom_fields.*` in its opt_fields so
   the cached task is field-complete for the later read), OR
3. **Reorder**: resolve the guid (custom_fields read) BEFORE `_preflight`, OR
4. **Fix the cache** to key on (gid, opt_fields) — broader, fleet-level; the code
   comment suggests a "full-fields hydration read" pattern already exists to consult.
Prefer (1) or (2) — local to the floodgates/onboarding surface. Add a **live-integration
test** that exercises the real cache (the unit fakes cannot catch this class).

## Reserved-lever discipline held throughout
The pilot ran only the LOCAL Phase-1 leg. No `wrangler` deploy, no Asana post, no
client SEND. Every reserved lever intact. The exec worktree was reaped.

---
## DEFER-WATCH (DELTA re-QA #212, low severity — NOT a merge blocker)
The union fix (`caller ∪ STANDARD`) closes FG-BUG + the two field-narrowing regressions.
One accepted residual: a **bare** `get(gid)` (opt_fields=None) now fetches STANDARD, which
omits top-level scalars `modified_at`/`due_on`/`completed`/`assignee`/`notes` that Asana's
default projection carried. Mitigations: mutating bare-get callers route through SaveSession
`invalidate_for_commit` (cache evicted → later reads re-fetch via BASE union). The only
surviving harmful ordering is a NON-mutating bare `get(gid)` then a same-gid freshness read
within one cache lifetime with no invalidation — narrow, plausibly-unreached.
- **Watch-trigger**: any freshness/watermark row with a null `modified_at` traced to a
  bare-get-populated cache entry; OR a new non-mutating bare-get-then-freshness flow added.
- **Reactivation**: fold the Asana-default top-level scalars into the bare-get (opt_fields=None)
  branch of the union (make bare-get fetch `ASANA_DEFAULT ∪ STANDARD`).
- **Owner**: 10x-dev. Ratified ship-with-defer per tiered-rigor done-bar (deployed +
  component-tested + defer-watch); qa-adversary GO 2026-07-07 (commit 5726cebc).
