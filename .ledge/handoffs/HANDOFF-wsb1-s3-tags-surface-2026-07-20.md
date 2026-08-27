---
type: handoff
handoff_type: implementation
status: draft
initiative: asana-mcp-postfelt-hardening
sprint: sprint-3
workstream: WS-B1 (tag-addressability — SATELLITE half)
from: 10x-dev / principal-engineer
to:
  - 10x-dev / principal-engineer (sprint-4 / WS-B2 — the sidecar CONSUMES this route)
  - hygiene / audit-lead (rite-disjoint critic per shape §6; hygiene-11-check-rubric)
created: 2026-07-20
repo: autom8y-asana
branch: feat/asana-mcp-postfelt-wsb1-tags
pr: 246
commits:
  - 90b23f5b  # feat(api): add GET /api/v1/tags read surface
  - 5c53a29e  # docs(api): regenerate OpenAPI spec for tags route
source_anchor: origin/main 793e670b (fresh; includes #238-#241 + #245)
self_grade: MODERATE  # self-assessment caps MODERATE; STRONG needs the rite-disjoint hygiene/audit-lead critic + eunomia PT-09
---

# HANDOFF — WS-B1 satellite tags read surface (TAG-1, SATELLITE half)

## 1. What this closes (TAG-1)

The composite write tool requires a `tag_gid`, but humans and agents think in tag
NAMES, and nothing in the stack could resolve a name: the satellite exposed no
tags read/resolution surface (the only tag-touching route was the composite's own
`POST /api/v1/tasks/{gid}/tags` leg), and the query engine's `tags` field carries
names without gids (digest §10 TAG-1, :219-234). This sprint delivers the SATELLITE
half — a read surface with a name→gid resolution primitive. The sidecar's dual-key
tool schema is sprint-4's job, downstream of this route.

Scope held: `src/` only (no `mcp/` — sprint-4's tree); no write verbs; write-flag
discipline untouched; single-composite W-2 shape not reopened (TAG-2 stays deferred).

## 2. Endpoint contract (for sprint-4 / the sidecar to consume)

```
GET /api/v1/tags
  auth:   Bearer (PAT or S2S-JWT) — dual-mode via get_auth_context DI
  query:
    name    optional  Exact tag name to resolve to its GID(s). Case-sensitive,
                      byte-for-byte. Empty/omitted => unfiltered listing.
    limit   optional  1..100, default 100. Applies to the unfiltered listing only.
    offset  optional  Opaque pagination cursor from a prior unfiltered response.

  200 OK  envelope: {"data": [ TagResource, ... ], "meta": {"request_id", "pagination"}}
      TagResource: { gid, name, color, permalink_url, resource_type }
      - name GIVEN  -> data is the COMPLETE exact-match set (scans all pages);
                       meta.pagination.has_more=false, next_offset=null.
                       MISS => data == []  (this is how the caller detects "no such tag").
                       Asana tag names are NOT unique -> data may contain >1 tag.
      - name ABSENT -> data is ONE page; meta.pagination carries has_more + next_offset
                       (follow next_offset via ?offset= for the next page).

  503 Service Unavailable  -> the Asana workspace GID is not configured on the service
      (SERVICE_NOT_CONFIGURED). Fail-closed.
```

**Sidecar guidance (sprint-4):** resolve `tag_name` by calling `GET /api/v1/tags?name=<name>`.
On `len(data)==1` use `data[0].gid`; on `len(data)>1` disambiguate (duplicate names);
on `len(data)==0` surface a not-found (the full unfiltered listing can supply
suggestions/`permalink_url`). Caching is the sidecar's responsibility — this route
is a stateless passthrough by design. Case-folding / fuzzy matching, if wanted, is
the sidecar's layer, not this primitive (the read surface is deterministic-exact).

## 3. Receipts — per-item `{path}:{line}` (landed on branch `feat/asana-mcp-postfelt-wsb1-tags`)

| Item | Anchor |
|---|---|
| Route `GET /api/v1/tags` (pat_router) | `src/autom8_asana/api/routes/tags.py:41` |
| Route handler `list_tags` | `src/autom8_asana/api/routes/tags.py:60` |
| Idempotency annotation (`idempotent: True`, `side-effects: []`) | `src/autom8_asana/api/routes/tags.py:55` |
| Service `TagService.list_tags` (dual mode) | `src/autom8_asana/services/tag_service.py:82` |
| Name→gid resolution primitive (all-page exact scan) | `src/autom8_asana/services/tag_service.py:144` |
| Fail-closed 503 when workspace unconfigured | `src/autom8_asana/services/tag_service.py:116` |
| Result type `TagListResult` | `src/autom8_asana/services/tag_service.py:58` |
| DI factory `get_tag_service` + `TagServiceDep` | `src/autom8_asana/api/dependencies.py:454`, `:489` |
| SCAR-WS8 JWT exclusion `/api/v1/tags/*` | `src/autom8_asana/api/main.py:438` |
| RouterMount wiring | `src/autom8_asana/api/main.py:463` |
| OpenAPI classification (_PAT_TAGS / scope def / scope rule) | `src/autom8_asana/api/main.py:111`, `:160`, `:179` |
| OpenAPI spec regenerated (additive-only, +165 lines) | `docs/api-reference/openapi.json` (commit `5c53a29e`) |

## 4. SCAR-WS8 discharge (load-bearing)

A new PAT route tree absent from the JWT middleware `exclude_paths` is rejected with a
silent 401 before `pat_router` DI fires. `/api/v1/tags/*` was added to the exclude list
in the same commit as the route (`src/autom8_asana/api/main.py:438`), with a dedicated
regression test at `tests/unit/api/test_tags_auth_exclusion.py:45` AND the family-level
co-exclusion invariant extended at `tests/unit/api/test_exports_auth_exclusion.py`
(`expected_pat_route_trees` now includes `/api/v1/tags/*`). App-build probe confirmed
`/api/v1/tags/*` present in the live `JWTAuthMiddleware.exclude_paths`.

## 5. Test receipts

Local (`.venv` python, `PYTHONPATH=<wt>/src`):

- Service layer — 13 tests, `tests/unit/services/test_tag_service.py`: two-sided name
  hit/miss, case-sensitivity guard, duplicate-name set, multi-page cursor scan,
  unfiltered pagination/offset, empty-`name`=unfiltered, unconfigured-workspace raise.
- Route — 7 tests, `tests/unit/api/test_routes_tags.py`: list, pagination, offset,
  name-filter hit, name-filter miss (200+empty), idempotency annotation, 503.
- Auth exclusion — 1 test, `tests/unit/api/test_tags_auth_exclusion.py` (+ family invariant).
- Combined new + `test_custom_openapi.py` + both auth-exclusion suites: **51 passed**.
- `ruff format` + `ruff check`: clean on all changed files. `mypy --strict`: clean on all
  changed source files.

## 6. CI receipts

- PR: https://github.com/autom8y/autom8y-asana/pull/246 (MERGEABLE, OPEN)
- CI run (all gates): https://github.com/autom8y/autom8y-asana/actions/runs/29741958167
- Green gates include: Test shards 1-4/4, Lint & Type Check, OpenAPI Spec Drift,
  Semantic Score, Spectral, CodeQL (python), Fleet Schema Governance, Aegis, Fuzz.
- Roll-up: 24 pass, 2 skipping (Convention Check + Integration Tests skip on PRs by design), 0 fail.

## 7. Design choices (documented for the critic)

1. **Exact, case-sensitive name match** — the read surface is a deterministic resolution
   primitive; case-folding/fuzzy is the sidecar's UX concern. Two-sided test proves an
   off-case query misses.
2. **Name MISS => HTTP 200 + empty list** (NOT 404) — a filtered collection with zero
   results is an empty collection, not a missing resource; matches sibling list-route
   semantics; gives the caller an unambiguous `len(data)==0` signal.
3. **All exact matches returned** — Asana tag names are not unique; surfacing all
   candidates keeps resolution honest (caller disambiguates).
4. **Thin passthrough, no cache** — caching lives in the sidecar (frame shape (a)).
   The service uses `client._http.get_paginated("/workspaces/{gid}/tags")` — the same
   endpoint the SDK `TagsClient` uses — mirroring `TaskService`/`workspaces.py`.
5. **Fail-closed 503** when `client.default_workspace_gid` is unset.

## 8. Open flags / boundaries

- **Limb (b) is NOT claimed here.** This sprint delivers the route only; the e2e
  "one composite invocation addressed by tag NAME" (predicate limb b) is sprint-4's
  exit (PT-06). This handoff's exit is PT-05 (the resolution surface exists), pending
  the rite-disjoint hygiene/audit-lead critic.
- **Merge is operator/dispatcher-reserved** (PT-05 → dispatcher merges after the
  rite-disjoint critic's CONCUR). This session did NOT merge.
- **Pre-existing local test note (NOT a regression):**
  `tests/unit/services/test_query_service.py::TestEntityServiceValidateAdversarial::test_project_gid_none_raises_service_not_configured`
  fails in the LOCAL editable-install environment but PASSES in CI (all 4 shards green;
  the file is byte-identical to origin/main per `git diff origin/main`, and this sprint
  touches nothing in `entity_service`/`query_service`). It is outside this change surface.
- **Sidecar `tag_gid | tag_name` dual-key schema, TAG-2 defer-watch registration, and
  case-folding UX** are sprint-4 / sprint-5 concerns, not this route's.

## 9. Self-grade

**MODERATE** (self-assessment ceiling). STRONG requires the rite-disjoint hygiene/
audit-lead critique (per-sprint) + eunomia PT-09 attestation (initiative, receipts-only).
