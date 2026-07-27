---
type: review
status: evidence-accrued
artifact: gate-probe-evidence
slug: fl5-gate-probe-d1-d11-evidence
lane: FL-5 (arch · topology-cartographer)
program: fleet-delegation-phase2 WAVE-1
probe_ref: repos-repo .ledge/decisions/PROBE-fleet-mcp-second-leg-2026-07-20.md
d_slate_source: repos-repo .ledge/spikes/SPIKE-mcp-substrate-concepts-2026-07-17.md :257-294
evidence_anchor_sha: dfdb84a38e71496e3b3a577935aa72039f37b5df
created_at: 2026-07-24
landing_mode: AUTONOMOUS (evidence)
scope: autom8y-asana ONLY (atomic per-repo; nothing authored cross-repo)
self_grade: MODERATE (ceiling per self-ref-evidence-grade-rule; topology observation, not evaluation)
ruling_taken: NONE — COMMIT/PARK/KILL is operator-only, outside this phase
---

# FL-5 GATE-PROBE — D1-D11 in-repo evidence accrual (autom8y-asana reference leg)

> **What this is**: a topology-cartographer inventory of the autom8y-asana artifacts
> that constitute the N=1 *reference leg* for each D1-D11 promotion candidate, plus a
> full map of the report-invoke WRITE surface. Evidence accrues toward the
> mandatory-to-evaluate D1-D11 slate opened by the COMMIT ruling.
>
> **What this is NOT**: this artifact records what IS present in-repo at
> `dfdb84a3`. It does not evaluate whether any promotion SHOULD happen, does not
> trace cross-unit dependencies (dependency-analyst's remit), and **does NOT take
> the COMMIT / PARK / KILL ruling** — that ruling is the operator's, and it was in
> fact already ruled COMMIT on 2026-07-20 (see Premise Note P2 below). Nothing here
> re-opens or re-takes it.

All paths absolute-resolvable under the repo root
`/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/`. `{path}:{line}` anchors are at
commit `dfdb84a38e71496e3b3a577935aa72039f37b5df`.

---

## 0. Premise-validation notes (surfaced before the evidence)

Three premise tensions were caught during scan and are surfaced rather than
propagated silently (per premise-validation-discipline + structural-verification-receipt).

### P1 — WRITE-surface endpoint path is a shorthand; real git path differs
- **Mission-stated path**: `api/routes/workflows.py`.
- **Actual git-tracked path**: `src/autom8_asana/api/routes/workflows.py` (resolved
  via `git ls-files`; the `api/routes/workflows.py` form is the repo's *internal
  shorthand*, used the same way inside the MCP tool docstring at
  `mcp/asana_mcp/tools/workflows.py:5`). Not a defect — a naming convention. All
  receipts below use the real git path.

```
structural_verification_receipt:
  claim: "the report-invoke REST endpoint's real git-tracked path is src/autom8_asana/api/routes/workflows.py, not the bare api/routes/workflows.py shorthand"
  verification_method: git-ls-files
  verification_anchor:
    source: "git ls-files | grep routes/workflows.py"
    path_or_glob: "src/autom8_asana/api/routes/workflows.py"
    result: exists
    claim: "the invoke route module resolves under the src/ package root; the bare api/routes/ form does not exist as a tracked path"
```

### P2 — The probe is already RULED-COMMIT (ruling NOT re-taken here)
The repos-repo probe entry carries `probe_status: RULED-COMMIT`; the operator ruled
"Commit now" on **2026-07-20**, 14 days ahead of the standing `probe_due:
2026-08-03` clock (`PROBE-fleet-mcp-second-leg-2026-07-20.md:5,24-33`). The effect
is live: "the D1-D11 slate is mandatory-to-evaluate" (probe entry :30). This
evidence-prep serves that already-live mandatory-evaluation. It takes no new ruling.

### P3 — `.mcp.json` exists in-repo but is NOT a counter-example to D8
D8 claims "no `.mcp.json`/mcpServers distribution mechanism exists anywhere." An
`.mcp.json` IS present at the repo root, but it is a **hand-edited developer-local**
client config (servers: `github`, `go-semantic`, `terraform`; a hardcoded
`/Users/tomtenuta/Code/...` absolute path at `.mcp.json:15-18`) that does **not**
contain the asana-mcp sidecar. It is an instance of exactly the per-satellite
hand-edit toil D8 names — corroborating, not contradicting. Recorded precisely so
downstream does not mis-read the file's presence as "D8 satisfied."

---

## 1. Report-invoke WRITE surface (mission step 2 — the centerpiece)

Recorded as an API-surface entry with enough detail for dependency-analyst to match
consumers. This is the write-verb the MCP second leg builds upon.

| Attribute | Value | Receipt (`{path}:{line}` @ dfdb84a3) | Confidence |
|-----------|-------|--------------------------------------|-----------|
| Route | `POST /api/v1/workflows/{workflow_id}/invoke` | `src/autom8_asana/api/routes/workflows.py:250-251` | High |
| Protocol | HTTP REST (FastAPI), Bearer auth (JWT **or** PAT) | `src/autom8_asana/api/routes/workflows.py:296`; router via `pat_router` `:36` | High |
| Declared side-effect | write-verb `x-fleet-side-effects: [{type: asana_api, target: task}]` | `src/autom8_asana/api/routes/workflows.py:264-266` | High |
| Idempotency | `x-fleet-idempotency: {idempotent: false, key_source: null}` | `src/autom8_asana/api/routes/workflows.py:267` | High |
| Rate limit | `x-fleet-rate-limit: {tier: external}`; `@limiter.limit("10/minute")` | `src/autom8_asana/api/routes/workflows.py:268,271` | High |
| Request body | `WorkflowInvokeRequest{ entity_ids[1-100 numeric GID], dry_run, params }` | `src/autom8_asana/api/routes/workflows.py:48-98` | High |
| PAT resolution | `AsanaClient(token=auth_context.asana_pat)` | `src/autom8_asana/api/routes/workflows.py:357` | High |
| Audit log fields | `workflow_id, entity_ids, dry_run, request_id, caller_service, auth_mode` | `src/autom8_asana/api/routes/workflows.py:320-329` | High |
| MCP disclosure boundary | `list_report_workflows` DISCLOSES the registry, NEVER invokes (R7/§5) | `mcp/asana_mcp/tools/workflows.py:10-18,88` | High |
| MCP write path gate | RB-1 two-phase confirm-before-firing (ruling R5/R21) | `mcp/asana_mcp/tools/confirm_gate.py:1,18-27` | High |

### 1.1 Identity keystone gap (the "shared bot PAT, not a named human" observation)

The invoke write executes on the PAT resolved by `get_auth_context`. In S2S-JWT
mode that PAT is the **shared bot PAT**, and the auth context carries **no
human-identity field**:

- `AuthContext.__slots__ = ("mode", "asana_pat", "caller_service")` — three fields,
  no `acting_agent`, no `delegating_user` (`src/autom8_asana/api/dependencies.py:58`).
- S2S-JWT path: `bot_pat = get_bot_pat()` (`dependencies.py:239`) →
  `AuthContext(... asana_pat=bot_pat, caller_service=claims.service_name)`
  (`dependencies.py:265-266`). The only caller identity is the **service name**.
- A repo-wide grep for `acting_agent` / `delegating_user` in `src/` returns the
  `AuthContext` class line only — the fields are absent from the codebase at
  `dfdb84a3`.

```
structural_verification_receipt:
  claim: "the invoke write-verb's AuthContext carries no acting_agent or delegating_user field; the JWT path resolves to the shared bot PAT, so the write is not attributable to a named human at dfdb84a3"
  verification_method: file-read
  verification_anchor:
    source: "src/autom8_asana/api/dependencies.py"
    line_range: "L58"
    marker_token: "__slots__ = (\"mode\", \"asana_pat\", \"caller_service\")"
    claim: "the auth context's field set is closed at three slots with no human-identity member; the identity keystone (acting_agent + delegating_user) is un-modeled in-repo and pending a cross-repo Phase-2"
```

This matches the MCP tool's own honest posture label: "CAPABILITY-NOW /
consumption-post-KEYSTONE: disclosed verbs still run on the shared bot PAT ... until
the identity keystone (acting_agent + delegating_user) lands in a cross-repo
Phase-2" (`mcp/asana_mcp/tools/workflows.py:23-27,59-64`).

> Neutral-observation note: the presence/absence of the keystone fields is recorded
> as structural fact. Whether that state is a defect, an intended phase boundary, or
> a risk is NOT judged here (that is structure-evaluator / security remit).

---

## 2. D1-D11 evidence table (autom8y-asana reference leg @ dfdb84a3)

Coverage semantics (topology-cartographer framing — presence of the in-repo
reference-leg artifact, NOT a promotion recommendation):
- **MET** — the autom8y-asana N=1 reference-leg artifact is present with a direct receipt.
- **PARTIAL** — the in-repo leg is present but the D-item's full scope spans
  cross-repo / shared-package / fleet-level artifacts outside this atomic per-repo scan.
- **UNMET-in-repo** — the referenced artifact is absent from autom8y-asana; the
  in-repo evidence is the *absence* (which may itself corroborate the D-item's claim).

| D | One-line promotion candidate | In-repo status | Primary receipt (@ dfdb84a3) | Confidence |
|---|------------------------------|----------------|------------------------------|-----------|
| D1 | FastMCP-over-REST sidecar scaffold/template | **MET** | `mcp/asana_mcp/server.py`, `mcp/pyproject.toml`, `mcp/serve_stdio.py` | High |
| D2 | Tool-authoring convention (~8-15 workflow-grain, sidecar-over-REST, hand-from-Pydantic) | **MET** (grain=7 observed) | `mcp/asana_mcp/tools/{query,discovery,resolve,workflows,composite_write}.py` | High |
| D3 | Typed-client ext (aggregate/resolve/match) + `require_caller_subject` allowlist → autom8y-auth | **PARTIAL** (mostly cross-repo) | `src/autom8_asana/clients/name_resolver.py:48,111,164,217`; `require_caller_subject` ABSENT in-repo | Medium |
| D4 | `x-fleet-*` OpenAPI annotations (the cheaper alt to `contracts.mcp`) | **MET** | `src/autom8_asana/api/routes/workflows.py:264-269`; also `entity_write.py:188-192`, `tags.py:55-57` | High |
| D5 | Satellite-dispatch YAML → one reusable workflow (N=5 hand-copied) | **MET** (asana copy = 1 of N) | `.github/workflows/satellite-dispatch.yml:3,54` | High |
| D6 | Shared honesty/freshness mixin in `autom8y_api_schemas.meta` (gated on data's shape, E1) | **PARTIAL** (usage in-repo; target cross-repo) | `mcp/asana_mcp/tools/workflows.py:85-86`; `src/autom8_asana/cache/policies/freshness_policy.py` | Medium |
| D7 | Cross-MCP tool namespacing convention | **PARTIAL** (collision names in-repo; convention is fleet) | `mcp/asana_mcp/tools/query.py:43,56` (`query_rows`/`query_aggregate`) | Medium |
| D8 | Client-side fleet-MCP discovery/config distribution (`.mcp.json`/mcpServers) | **UNMET-in-repo** (hand-edit toil present; see P3) | `.mcp.json:1-27` (dev-local, no asana sidecar) | Medium |
| D9 | Repeatable runtime tool-ergonomics eval harness | **UNMET-in-repo** (no MCP-tool eval) | grep-zero `semantic_score`/`eval_harness` over `mcp/**.py` | Medium |
| D10 | Sidecar↔service behavioral contract test across independent deploys | **PARTIAL** (signature-freeze, not cross-deploy behavioral) | `mcp/tests/test_seam_conformance.py:1-4` (FROZEN v1 signature conformance) | Medium |
| D11 | Readiness-proxy helper extraction (only if #2 shares shape, C3) | **MET** (helper present in-repo) | `mcp/asana_mcp/tools/_common.py:19`; `mcp/asana_mcp/bridge.py:129` | High |

---

## 3. Per-D-item detail (neutral observations + receipts)

**D1 — sidecar scaffold. MET.** The `mcp/asana_mcp/` package is a complete
FastMCP-over-REST sidecar: `server.py` (create_server seam), `assembly.py`,
`bridge.py`, `context.py`, `envelopes.py`, `settings.py`, `serve_stdio.py` entry
point, and its own build manifest `mcp/pyproject.toml`. This is the N=1 template the
D1 promotion candidate references. High confidence (explicit build manifest +
module structure).

**D2 — tool-authoring convention. MET; grain observed = 7.** Registered
`@mcp.tool` count is 7 across 5 modules: `query_rows`, `query_aggregate`
(`tools/query.py:43,56`), `list_entity_types`, `describe_entity`
(`tools/discovery.py:56,67`), `resolve_entity` (`tools/resolve.py:40`),
`list_report_workflows` (`tools/workflows.py:105`), and `composite_write`
(`tools/composite_write.py`). Sidecar-over-REST is observable: tools call the REST
oracle via `get_json` (e.g. `tools/workflows.py:75` against
`_WORKFLOWS_ORACLE_PATH` at `:46`). Recorded fact: grain = 7, which is one below the
"~8-15" stated band — recorded as an observation, not scored. (`confirm_gate.py`,
`tag_resolve.py`, `_match_business_stub.py` register no `@mcp.tool` — mechanics /
stub.)

**D3 — typed-client + allowlist. PARTIAL (mostly cross-repo).** No class literally
named `AsanaQueryClient` exists in-repo (grep-zero over `src/`, `mcp/`). The
resolve-family methods exist in `src/autom8_asana/clients/name_resolver.py`
(`resolve_tag:48`, `resolve_section:111`, `resolve_project:164`,
`resolve_assignee:217`). The `require_caller_subject` allowlist named in D3 is
**absent from autom8y-asana** (grep-zero) — its promotion target is autom8y-auth,
which is out of this atomic per-repo scope. In-repo evidence is the resolver-method
leg only.

**D4 — `x-fleet-*` annotations. MET (strongest in-repo D-item).** The "cheaper
alternative" D4 recommends over a `contracts.mcp` manifest slot — carrying the tool
surface as governed `x-fleet-*` OpenAPI annotations — is already implemented across
the REST surface: the invoke route (`routes/workflows.py:264-269`), plus
`entity_write.py:188-192`, `tags.py:55-57`, `exports.py:615-648`, `webhook.py:41-42`,
and `x-fleet-envelope-exempt` across `query.py`. Visible to the existing
governance tooling D4 cites. High confidence (explicit `openapi_extra` blocks).

**D5 — satellite-dispatch YAML. MET (asana copy = 1 of N).**
`.github/workflows/satellite-dispatch.yml` is a hand-authored `repository_dispatch`
consumer (`on:` at `:3`; `uses: peter-evans/repository-dispatch` at `:54`). It is
not itself a `workflow_call` reusable — i.e. the in-repo copy is one of the N=5
hand-copies D5 names as the duplication signal; the extraction-into-one-reusable is
the (un-taken) promotion action. High confidence.

**D6 — honesty/freshness mixin. PARTIAL.** The honesty vocabulary
(`honest_empty` / `contract_complete`) is used at the MCP tool layer
(`tools/workflows.py:85-86`) and freshness policy lives in
`src/autom8_asana/cache/policies/freshness_policy.py`. The D6 promotion **target**
is a shared mixin in `autom8y_api_schemas.meta` (a cross-repo shared package), and
D6 is explicitly gated on autom8y-data's divergent shape existing to reconcile
against (SPIKE E1). In-repo = the usage leg; the shared-package target is out of scope.

**D7 — cross-MCP namespacing. PARTIAL.** asana-mcp authors the exact
collision-candidate tool names `query_rows` / `query_aggregate`
(`tools/query.py:43,56`). The namespacing *convention* is a fleet/cross-MCP concern
that only bites once a second server (data-mcp) is reachable from one client — not
in-repo-resolvable. In-repo = the collision surface (the names) only.

**D8 — client-side discovery/config distribution. UNMET-in-repo.** See Premise
Note P3. The `.mcp.json:1-27` present is a hand-edited developer-local config with
no asana sidecar entry and a hardcoded user path — the toil D8 describes, not a
distribution mechanism. Absence of the distribution mechanism corroborates D8.

**D9 — runtime tool-ergonomics eval harness. UNMET-in-repo.** Grep-zero for
`semantic_score` / `eval_harness` / `tool_selection` / `SemanticScore` over
`mcp/**.py`. No in-repo runtime tool-USE eval harness for the MCP tools; this
corroborates D9's "static-only / one-shot" characterization. (Absence-evidence:
qualified as grep-zero over `mcp/**.py` at `dfdb84a3`, not a universal-absence proof.)

**D10 — sidecar↔service behavioral contract test. PARTIAL.**
`mcp/tests/test_seam_conformance.py` exists but its own header declares it a
"Mount-seam conformance (FROZEN v1) ... Asserts the implemented signatures match
the seam verbatim" (`:1-4`) — i.e. a **signature-freeze** conformance test, not the
cross-independent-deploy **behavioral / response-semantics** contract D10 specifies
(envelope/503/honesty semantics across independent parent-satellite rollout). The
signature seam is present; the behavioral-across-deploys contract is not.

**D11 — readiness-proxy helper. MET.** The readiness-proxy helper is present:
`ensure_ready(ctx)` in `mcp/asana_mcp/tools/_common.py:19` (gates tool availability
on the satellite `/ready`), fed by `make_readiness_probe` in
`mcp/asana_mcp/bridge.py:129` (with `readiness_fail_open` posture). This is the C3
readiness-proxy shape D11 would extract if #2 exhibits the same shape.

---

## 4. Coverage summary

- **MET (in-repo reference leg present + receipted): 5** — D1, D2, D4, D5, D11.
- **PARTIAL (in-repo leg present; full scope spans cross-repo / shared / fleet): 4**
  — D3, D6, D7, D10.
- **UNMET-in-repo (artifact absent; absence corroborates the D-item claim): 2** —
  D8, D9.

Every D-item has at least one autom8y-asana anchor (present-artifact receipt, or a
qualified absence receipt). No D-item was left un-scanned. The atomic per-repo scope
means the cross-repo legs of D3 (autom8y-auth `require_caller_subject`), D6
(`autom8y_api_schemas.meta` shared mixin + autom8y-data shape), D7 (data-mcp
co-existence), and D8 (a fleet distribution owner) are explicitly out of this scan
and flagged for whoever holds the second (autom8y-data) leg.

---

## 5. SURFACED-PLACEMENT note (FORK-β option 1)

This artifact is authored **in-repo only**, at
`autom8y-asana/.ledge/reviews/FL-gate-probe-d1-d11-evidence-2026-07-24.md`. Nothing
was authored cross-repo.

The repos-repo probe entry states "Interim evidence accrues to this entry"
(`PROBE-fleet-mcp-second-leg-2026-07-20.md:19`). Whether to place a pointer (or a
copy) of this evidence at that repos-repo entry is **SURFACED for the operator, not
taken here** (FORK-β option 1 = in-repo placement; cross-repo placement is the
operator's call). Suggested operator action, if desired: append a one-line pointer
to `repos/.ledge/decisions/PROBE-fleet-mcp-second-leg-2026-07-20.md` referencing
this file at merge SHA. This lane writes nothing into the repos-repo.

---

## 6. Ruling-not-taken statement (explicit)

The **COMMIT / PARK / KILL ruling is NOT taken in this artifact.** It is
operator-only and outside this phase. (For the record: the operator already ruled
COMMIT on 2026-07-20 per probe `:24`; this evidence-prep serves the resulting
already-live mandatory-to-evaluate slate and neither re-opens nor re-rules it.)

---

## 7. Unknowns (flagged for downstream / operator routing)

### Unknown: D2 grain sits one below the stated "~8-15" band
- **Question**: Is 7 registered tools the intended grain, or are tools pending
  registration (e.g. `composite_write` sub-verbs, `tag_resolve`)?
- **Why it matters**: D2's promotion claim is a workflow-grain convention; the N=1
  leg's actual grain calibrates the convention.
- **Evidence**: 7 `@mcp.tool` across 5 modules (`tools/*.py` @ dfdb84a3).
- **Suggested source**: MCP sidecar owner / RD lane (shared surface).

### Unknown: cross-repo legs of D3/D6/D7/D8 are unscanned by design
- **Question**: What is the state of `require_caller_subject` (autom8y-auth), the
  `autom8y_api_schemas.meta` mixin target, data-mcp tool names, and any fleet
  distribution owner?
- **Why it matters**: These are the *second* legs that convert N=1 pattern-claims
  into twice-proven promotions (R11 bar).
- **Evidence**: in-repo grep-zero for `require_caller_subject`; D6/D7/D8 name
  cross-repo/shared/fleet targets explicitly.
- **Suggested source**: autom8y-data second-leg lane + autom8y-auth owner
  (out of this atomic per-repo scope).

### Unknown: D10 behavioral-across-deploys contract is absent (only signature-freeze present)
- **Question**: Is a cross-independent-deploy behavioral contract intended before #2?
- **Why it matters**: D10 guards envelope/503/honesty response semantics under
  independent parent rollout; the present test guards signatures only.
- **Evidence**: `mcp/tests/test_seam_conformance.py:1-4` (FROZEN v1 signature scope).
- **Suggested source**: MCP sidecar owner.

---

## 8. Self-grade

**MODERATE** (ceiling per `self-ref-evidence-grade-rule`; topology observation, not
evaluation). All load-bearing claims carry `{path}:{line}` receipts at `dfdb84a3`;
the keystone-gap and write-verb claims carry explicit SVR tuples. Grade does not
rise to STRONG: this is a single-rite in-repo scan of one leg (autom8y-asana) of a
two-leg (asana + data) promotion slate; the corroborating second leg and any
rite-disjoint critic concurrence are not present in this artifact.
