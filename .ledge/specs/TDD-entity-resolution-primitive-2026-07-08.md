---
type: spec
status: proposed
---

# TDD — Entity-resolution primitive: hierarchy-first office-guid / task->business resolver

- Date: 2026-07-08
- ADR: `.ledge/decisions/ADR-entity-resolution-primitive-2026-07-08.md`
- Repo: autom8y-asana (read origin/main via the intact worktree; NEVER the stale local main)
- Self-assessment ceiling: **MODERATE** (`self-ref-evidence-grade-rule`). STRONG requires an
  independent build + 2-sided QA receipt.

Every platform-behavior claim below carries a `file:line` SVR. `parent.gid` = the Asana task
`parent` nested `gid`.

---

## 1. Design summary

Replace the lossy `office_phone -> workspace /tasks/search` bridge that BOTH walkthrough posters
share with an **authoritative ancestor walk**: PLAY -> follow `parent.gid` upward -> the FIRST
ancestor that is a `BUSINESS_PROJECT` member -> read its `Company ID` custom field. Phone survives
only as a labeled fallback + optional shadow crosscheck.

**Store-independence is the primary architecture** (the load-bearing constraint): the walkthrough
runs plain `AsanaClient()` with NO `UnifiedTaskStore` (SVR `contact_synthesis.py:591`,
`template_comment.py:432`, `floodgates/batch.py:276`), and `HierarchyIndex.get_ancestor_chain`
returns `[]` for an unregistered gid (SVR `hierarchy.py:175`). So the resolver **self-warms**: it
fetches each node live via `tasks.get_async` and registers it into a **fresh local
`HierarchyIndex()`** — the SAME SDK primitive `HierarchyIndex` wraps (SVR `hierarchy.py:87-90`) — so
cycle-detection and the depth bound come free (reuse, not re-mint of traversal).

---

## 2. New module + signatures

### 2.1 `src/autom8_asana/automation/workflows/onboarding_walkthrough/office_resolution.py` (NEW)

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

from autom8_asana.client import AsanaClient
from autom8_asana.cache.policies.hierarchy import HierarchyIndex   # SVR hierarchy.py:57
from autom8_asana.core.entity_registry import get_registry          # SVR entity_registry.py:1203
from autom8_asana.core.project_registry import BUSINESS_PROJECT     # SVR project_registry.py:21
from autom8_asana.core.types import EntityType

# Projection carrying BOTH the walk edge AND the Company ID reader input in one fetch.
_WALK_OPT_FIELDS = ["gid", "name", "parent.gid", "projects.gid",
                    "custom_fields.name", "custom_fields.display_value"]


@dataclass(frozen=True)
class BusinessResolution:
    business_gid: str | None
    company_id: str | None                        # the office guid (cf "Company ID")
    method: Literal["hierarchy", "phone"]         # provenance — observable fleet signal
    ancestor_depth: int | None                    # hops walked (0 = self was BUSINESS)
    candidates: tuple[str, ...] = ()              # ambiguity set for a LOUD refusal


class BusinessResolutionAmbiguous(RuntimeError): ...          # >1 BUSINESS ancestor / >1 phone match
class BusinessResolutionMissingNoBusiness(RuntimeError): ...  # walk found no BUSINESS ancestor
class BusinessResolutionDepthExhausted(RuntimeError): ...     # FORK-3 distinct code
class DivergentOfficeResolution(RuntimeError): ...            # crosscheck tripwire


async def resolve_business_gid(
    asana_client: AsanaClient,
    *,
    task_gid: str,
    project_gid: str = BUSINESS_PROJECT,   # FORK-1 seam; BUSINESS-only ships, general LATER
    max_depth: int = 5,
    phone_crosscheck: bool = False,
) -> BusinessResolution:
    """Authoritative walk: task -> first ancestor in `project_gid` -> that node.

    Self-warms a fresh local HierarchyIndex from live parent.gid reads (store-optional
    by construction). Returns method="hierarchy" on success. On no-business-ancestor,
    the CALLER decides fallback-vs-refuse (this fn does not silently phone-fallback).
    Raises BusinessResolutionAmbiguous if >1 ancestor in project_gid is found in the
    walked chain (FORK-3 assert-at-most-one). Raises BusinessResolutionDepthExhausted
    if max_depth is reached with a non-null parent still pending (distinct from
    BusinessResolutionMissingNoBusiness = chain ended, no member).
    """


async def resolve_office_guid(
    asana_client: AsanaClient,
    *,
    task_gid: str,
    **kw,
) -> str | None:
    """resolve_business_gid then read Company ID off the resolved Business node
    via the existing _company_id_from_task reader (SVR template_comment.py:217)."""
```

**Walk body (spec):**
1. `idx = HierarchyIndex()`; `cur = task_gid`; `depth = 0`; `matches: list[tuple[str, dict]] = []`.
2. Loop while `cur` and `depth <= max_depth`:
   - `node = await asana_client.tasks.get_async(cur, opt_fields=_WALK_OPT_FIELDS)`; coerce to a `{"gid","parent","projects","custom_fields"}` dict.
   - `idx.register(node_dict)` (SVR `hierarchy.py:96`) — feeds the SDK tracker so cycle/depth guards apply.
   - `desc = _match_business(node_dict, project_gid)`: for each `projects[].gid`, `d = get_registry().get_by_gid(pgid)` (SVR `entity_registry.py:299`); a match iff `d is not None and d.primary_project_gid == project_gid` (registry-typed; `BUSINESS_PROJECT` literal is the fallback compare if the registry returns `None`).
   - if matched: append `(node.gid, node_dict)` to `matches`.
   - `parent_gid = node["parent"]["gid"] if node.get("parent") else None`; if `None` -> chain end, break; else `cur = parent_gid`, `depth += 1`.
3. `if len(matches) > 1`: raise `BusinessResolutionAmbiguous(candidates=tuple(g for g,_ in matches))`.
4. `if len(matches) == 1`: return `BusinessResolution(business_gid, company_id_from(node_dict), "hierarchy", depth_at_match, ())`.
5. `if depth > max_depth and parent_gid is not None`: raise `BusinessResolutionDepthExhausted` (FORK-3).
6. else (chain ended, no member): return `BusinessResolution(None, None, "hierarchy", None, ())` — caller falls back or refuses.

**Crosscheck (`phone_crosscheck=True`):** after a hierarchy success, also run
`_business_gid_by_phone` (via the office phone read from the task) and assert equal; on
disagreement raise `DivergentOfficeResolution` (LOUD tripwire; off by default).

### 2.2 Cache-provider pinning (FORK-2)

The walk's `tasks.get_async(opt_fields=[... projects.gid, custom_fields ...])` reads are subject to
the cross-reader projection-coverage starvation: the hit path serves a stored entry with NO
coverage check (SVR `clients/tasks.py:209-235`), and a narrow cached ancestor missing `projects.gid`
would false-negative `_match_business` and overshoot the Business
(SVR `DEFECT-taskcache-cross-reader-section-starvation-2026-07-08.md:20-37`). Until SIBLING-1's
hit-path coverage check lands fleet-wide, the resolver's callers construct
`AsanaClient(cache_provider=NullCacheProvider())` (the proven 2026-07-08 unblock,
SVR defect:47-53; `client.py:98`, `_defaults/cache.py:25`). **DEFER-WATCH**: switch to cached reads
once SIBLING-1 lands. Note: the documented `ASANA_CACHE_*` env knobs DO NOT BIND on the default
path (SVR defect F-2:40-43) — explicit injection is the only working disable.

---

## 3. Reuse ledger (integrate, do NOT re-mint)

| Reused primitive | SVR | Role in the walk |
|---|---|---|
| `HierarchyIndex()` / `register` / SDK `HierarchyTracker` | `hierarchy.py:57,87-90,96` | fresh local tracker; free cycle-detect + depth bound |
| `get_ancestor_chain` semantics (empty on unregistered) | `hierarchy.py:160-182` (`:175`) | why self-warm is mandatory, not optional |
| `BUSINESS_PROJECT = "1200653012566782"` | `project_registry.py:21` | fallback literal discriminator |
| `get_registry().get_by_gid` -> BUSINESS descriptor ROOT | `entity_registry.py:299,445-446,1203` | registry-typed discriminator (primary) |
| `_company_id_from_task` | `template_comment.py:217-229` | Company ID reader (unchanged) |
| `_business_gid_by_phone` | `contact_synthesis.py:374-414` | fallback + crosscheck only (LIFTED, not deleted) |
| `cascade_validator` walk pattern | `cascade_validator.py:102-107` | the LIVE exemplar this design lifts to identity altitude |

Literal parity verified: `contact_synthesis.py:103` `_BUSINESSES_PROJECT_GID` ==
`project_registry.py:21` `BUSINESS_PROJECT` == `entity_registry.py:446` `primary_project_gid` ==
`"1200653012566782"`.

---

## 4. Integration at each site (file:line)

### SITE 1 — `template_comment._resolve_office_guid` (`template_comment.py:232-261`)

Replace the phone-first body. Keep the LOUD `TemplateCommentRefused` semantics and the
`_company_id_from_task` reader:

```python
res = await office_resolution.resolve_business_gid(asana_client, task_gid=task_gid)
if res.business_gid is None:                     # walk found no Business ancestor
    office_phone = await _read_office_phone(asana_client, task_gid)   # fallback (SVR :239)
    if office_phone:
        pg = await _business_gid_by_phone(asana_client, office_phone) # SVR contact_synthesis:374
        # ... (phone fallback path, method="phone" logged)
    if not resolved:
        raise TemplateCommentRefused(...)        # unchanged LOUD refuse (SVR :247)
return res.company_id or _company_id_from_task(business_node)
```

The `TaskOfficeMismatch` crown-jewel verify (`template_comment.py:319-327`, supplied `office_guid`
must EQUAL task-resolved guid) is **UNCHANGED** — now compares against the hierarchy-resolved guid,
strictly stronger.

### SITE 2 — `contact_synthesis.resolve_ranked_cards` + `post_contact_card` (`contact_synthesis.py:417-459`, `465-547`)

- `resolve_ranked_cards` signature migration (FORK-5): add `task_gid: str`; retain `office_phone` as deprecation-window fallback/crosscheck. Line `:434` (`business_gid = await _business_gid_by_phone(...)`) becomes:
  ```python
  res = await office_resolution.resolve_business_gid(asana_client, task_gid=task_gid)
  business_gid = res.business_gid
  if business_gid is None and office_phone:                     # fallback
      business_gid = await _business_gid_by_phone(asana_client, office_phone)
  if not business_gid:
      return False, []                                          # unchanged no_holder (SVR :435-436)
  ```
- `post_contact_card` threads `play_gid` (already in scope, SVR `:468,499`) into `resolve_ranked_cards`; `office_phone` becomes a pure override, still read from the PLAY when the walk is used only for fallback.
- `_business_gid_by_phone` (`:374-414`) is **retained** (fallback + crosscheck; the S2S surface's only tool). Its `ContactCardBusinessAmbiguous` on >1 (`:406-410`) is preserved.

### SITE 3 (DECISION — OUT OF SCOPE for this seam) — `api/routes/intake_resolve.resolve_business` (`intake_resolve.py:69-157`)

**Explicitly deferred** (FORK-4). It is a SEPARATE process with its own store/index
(`GidLookupIndex` O(1), `services/intake_resolve_service.py:56-97`) and accepts a **phone input with
NO task-gid**, so it cannot use the ancestor walk as primary. The felt bug is the walkthrough.
Follow-up ticket: add an additive optional `task_gid` to `BusinessResolveRequest`; when present,
prefer a hierarchy walk (the store-optional signature delegates to `get_parent_chain_async` when a
store IS present, SVR `unified.py:709`), else the O(1) index. ADR-INT-001 never-404 preserved. NOT
a gate on shipping SITE 1/2.

---

## 5. Sibling-debt disposition (ranked)

| Rank | Sibling | Disposition |
|---|---|---|
| 1 | **FLAGSHIP** (this TDD) | BUILD now — closes the felt collision class |
| 2 | **SIBLING-1** cache hit-path projection-coverage (`clients/tasks.py:209-235`; defect receipt) | **CONTAINED coupling** — resolver pinned to `NullCacheProvider()`; DEFER-WATCH to switch to cached reads when the fleet-wide coverage-check lands. NOT built here. |
| 3 | **SIBLING-2** floodgates per-office Pages deploy accumulation (`host_bundle.py:109-178`, `floodgates/batch.py`) | **DEFER** — orthogonal to office resolution; single-office runs work; not load-bearing to the flagship. Watch-registered only. |

---

## 6. Two-sided test plan

All resolver reads run under `AsanaClient(cache_provider=NullCacheProvider())` (FORK-2).

### T-1 (POSITIVE, hierarchy) — a TWC-class office resolves via the walk where phone was AMBIGUOUS

- Input: PLAY `1215766139321621` (Total Wellness Center).
- Expect: `resolve_business_gid(...).business_gid == "1214127219419742"`, `method == "hierarchy"`, `ancestor_depth == 2` (PLAY -> `1214127290389479` -> `1214127219419742`, SVR spike:24-28); `company_id == "7363c7ea-66f8-487f-9f6e-c7a12a63d33f"` (spike:27).
- Contrast: the phone path on the SAME office raises `ContactCardBusinessAmbiguous` (2 matches for `+13036277995`, SVR spike:16-19). **The walk succeeds where phone fails** — this is the discriminating teeth (two-sided: the walk bites correctly, phone refuses correctly).

### T-2 (POSITIVE, fallback) — a phone-only office still resolves via the fallback

- Input: a clean single-Business office (no opportunity/lead card sharing the phone).
- Expect BOTH paths agree: `resolve_business_gid(..., phone_crosscheck=True)` returns `method="hierarchy"` with `business_gid == _business_gid_by_phone(office_phone)`; NO `DivergentOfficeResolution`. Then simulate a walk-`None` (orphan-parent fixture) -> caller falls back to phone -> resolves with `method="phone"`. Proves the fallback contract is live and the crosscheck tripwire passes on agreement.

### T-3 (NEGATIVE, B5 non-regression) — the get_gid_map failure is NOT reintroduced

- Assert (static + import): `office_resolution.py` imports NO `DataServiceClient` / `get_gid_map` / vertical-keyed export symbol. `grep -n "get_gid_map\|DataServiceClient" office_resolution.py` returns EMPTY.
- Assert (behavioral): the resolver's ONLY network dependency is `asana_client.tasks.get_async` (the same primitive the phone bridge already uses live on 8/8 ACTIVE offices). No M2M creds, no vertical key. The B5 coverage-gap failure MODE (external dataset incompleteness, SVR `contact_synthesis.py:429`) is structurally unreachable.

### T-4 (NEGATIVE, ambiguity discipline) — multi-Business ancestor refuses LOUD

- Fixture: a synthetic chain with TWO ancestors both members of `BUSINESS_PROJECT`.
- Expect: `BusinessResolutionAmbiguous` with `candidates` = both gids (never silent first-match). Mirrors `contact_synthesis.py:406-410`.
- **Pre-build spot-check (FORK-3)**: run a live query confirming no real ACTIVE PLAY has an ancestor task that is a member of >1 registered project (multi-project membership; UV-P until run).

### T-5 (NEGATIVE, refusal-code distinctness) — depth vs no-business

- Depth-exhausted fixture (chain deeper than `max_depth` with a live parent still pending) -> `BusinessResolutionDepthExhausted`.
- Orphan/mis-parented PLAY (chain ends, no BUSINESS member) -> caller sees `business_gid=None` -> after phone fallback fails -> `TemplateCommentRefused` / `no_holder`. The two are diagnosably different (FORK-3).

### T-6 (INVARIANT) — crown-jewel guard preserved

- `post_template_comment` with a mismatched supplied `office_guid` still raises `TaskOfficeMismatch` (`template_comment.py:320-326`) — now against the hierarchy-resolved guid.

---

## 7. Phased migration (each phase independently shippable + reversible)

- **Phase 0 (build + prove)**: land `office_resolution.py` + unit tests; port `scratchpad/fg_twc_hierarchy.py` (SVR spike:46-48) into a real T-1 test driving TWC. No production edit yet.
- **Phase 1 (seam swap, walkthrough)**: repoint `template_comment.py:245` and `contact_synthesis.py:434` to the walk (hierarchy PRIMARY, phone AUTOMATIC fallback). Keep `_business_gid_by_phone` in-tree. Ship behind no flag (strictly-more-correct: closes the HALTing ambiguity). Rollback = revert the two call-site lines.
- **Phase 2 (shadow crosscheck)**: run `phone_crosscheck=True` across one full batch wave; require ZERO `DivergentOfficeResolution` (proves hierarchy ⊇ phone on every ACTIVE office).
- **Phase 3 (deprecate)**: once the wave is clean, flip crosscheck off, mark `_business_gid_by_phone` deprecated-fallback; confirm no EXTERNAL caller depends on the phone-only entry (FORK-5) before any future deletion.
- **Phase 4 (SIBLING-1 lift, DEFER-WATCH)**: when the cache hit-path coverage-check lands fleet-wide, drop the `NullCacheProvider` pin so the walk runs cached (O(1)-ish per node).
- **Follow-up ticket (SITE 3, not gated)**: additive `task_gid` on the S2S `intake_resolve` surface.

No data/schema migration. No index rebuild for the walkthrough path.

---

## 8. Realization rungs

authored (this TDD) < built (`office_resolution.py` + tests) < tested (2-sided QA GREEN, T-1..T-6)
< merged (Phase 1 PR) < live (Phase 2 shadow wave, zero divergence).
