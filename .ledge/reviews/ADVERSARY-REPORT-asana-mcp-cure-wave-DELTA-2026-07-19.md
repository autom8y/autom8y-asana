---
type: review
status: complete
artifact: adversary-delta
initiative: asana-mcp-v1
date: 2026-07-19
evidence_ceiling: MODERATE
reviewer: adversary-DELTA (rite-disjoint, read-only; local pytest permitted)
scope:
  diff1: b62a431b @ .knossos/worktrees/wt.rnd.asana-mcp-cure.20260719T152728.410d30 (fix/asana-mcp-sat1-entity-vocab, base 36245d18)
  diff2: d81f7eee @ autom8y-asana-wt-mcp-s2 (cherry-pick b33cc1d9 @ autom8y-asana-wt-mcp-s6 — verified content-identical)
  diff3: runbook "### Step 6.5" @ .sos/wip/asana-mcp-v1.witness-go-runbook.md:198-247
method: >
  Refutation posture. Every receipt below re-derived by my own reads/runs; nothing inherited
  from the builder. Local runs: cure worktree pytest (46 parity/discovery; 1844 api/services/query),
  main-checkout control runs, s2 (29 passed) and s6 (98 passed) sidecar suites, live introspection
  of installed fastmcp 3.4.4, and in-process vocabulary dumps on both trees. No live REST touched,
  no writes outside this file, no git mutations.
---

# ADVERSARY-DELTA — asana-mcp-v1 cure wave (2026-07-19)

Coverage note: the wave register is G1-G6; the three diffs presented map to G1+G2+G3 (DIFF 1),
G4 (DIFF 2), G6 (DIFF 3). No artifact covering G5 was presented to this review; the register
document itself is not in the repo files I could locate. Not graded — recorded for the ledger.

---

## DIFF 1 — satellite entity-vocabulary cure (b62a431b)

### D1-F1 — severity: MATERIAL — undisclosed blast radius: the cache-warm path flips from skip-FAILURE to 9 full pipeline-project builds per warm cycle

**Claim attacked:** "get_resolvable_entities ... flipped to descriptor-driven enumeration;
process_* become queryable AND aggregatable" — implicitly, that the behavioral delta is confined
to the query surface.

**What I found:** `get_resolvable_entities` feeds three consumers beyond the query routes, and one
of them changes production behavior materially:

1. **CacheWarmer (API-side and Lambda).** `cache/dataframe/warmer.py:381` fetches the build
   strategy via `_get_strategy_instance` (`warmer.py:491-505`) → `services/resolver.py:get_strategy`
   → `is_entity_resolvable` (resolver.py:732, 406-415). The warm list is
   `cascade_warm_order()` (`lambda_handlers/cache_warmer.py:796-807` default when the event carries
   no `entity_types`), which I executed in both trees — it contains ALL NINE process pipelines:
   `['business','unit','asset_edit_holder','offer','contact','asset_edit','process_sales',
   'process_outreach','process_onboarding','process_implementation','process_month1',
   'process_retention','process_reactivation','process_account_error','process_expansion']`.
   Empirical differential (my own runs, both trees, discovery-less lambda-like context):
   - main: `get_resolvable_entities()` = 8 (`asset_edit, asset_edit_holder, business, contact,
     offer, project, section, unit` — byte-identical to the dossier's live `available_types`);
     `get_strategy("process_sales")` → **None** → `warmer.py:383-390` returns
     `WarmResult.FAILURE "No resolution strategy registered"` — **no Asana calls**.
   - cure: vocabulary = **17**; `get_strategy("process_sales")` → **UniversalResolutionStrategy**
     → `_warm_entity_type_async` proceeds to a **full project build** (`warmer.py:392-404`).
   Net: each unrestricted warm cycle gains up to 9 full pipeline-project builds, including the
   cascade/hierarchy hydration for office_phone/vertical (PROCESS_COLUMNS are `cascade:` sourced,
   `dataframes/schemas/process.py:17-33`) — the exact API-load class the asana-substrate-freshness
   arc just attributed a 429-storm to and cured with hierarchy-warm 429-banking (#234), whose C3
   soak (age<3600 ×2 cycles, gaps_warmed>0) is still pending. Merging this mid-soak changes the
   measured workload without an operator ruling or a commit-message disclosure. I could not verify
   whether the deployed warm event restricts `entity_types` (infra not in repo); the code default
   warms all 15.
2. **`/v1/resolve/{entity_type}`** (`api/routes/resolver.py:118,132,244-300`): process_* now pass
   `get_supported_entity_types` and proceed to strategy resolution. Read-only; process descriptors
   carry `key_columns=("office_phone","vertical")` (entity_registry.py process_* entries), so the
   DynamicIndex path is well-formed. Benign widening, but it IS new accepted input on a second route
   family the commit message does not mention.
3. **Write/matching/intake surfaces:** independently gated — `resolution/write_registry.py` is
   model-class-driven (process_* have no `model_class_path` → not writable); `api/routes/matching.py:130`
   and intake use `EntityProjectRegistry` directly. No widening there (verified by grep + read).

**Verdict:** STANDS-WITH-FLAG on the fix itself (the enumeration change is correct and the ruled
fix shape necessarily feeds the warmer); **REFUTED** as a contained-scope claim. Required before
witness re-entry: explicit operator disclosure of the warm-path delta (9 builds/cycle + hierarchy
cascade load) and its interaction with the C3 429-banking soak baseline; ideally a warm-list
ruling (allow / stagger / event-restrict) recorded in the ledger.

### D1-F2 — severity: MINOR — "seven pipeline entities" is nine; vocabulary widens by 9, not 7

**Claim attacked:** commit message and `tests/unit/services/test_entity_vocabulary_parity.py`
(`PIPELINE_ENTITIES`, 7 names) — "the seven pipeline entities".

**What I found:** `ENTITY_DESCRIPTORS` carries NINE warmable process pipelines — the seven named
plus `process_account_error` (GID `1201684018234520`, `core/project_registry.py:72`) and
`process_expansion` (GID `1201265144487557`, `core/project_registry.py:73`); descriptor block
header literally says "Pipeline Process Entities (9 projects)" (entity_registry.py:568-571 region).
Both enter the cured vocabulary (my 17-entity dump) and both are advertised by introspection
(`query/introspection.py:list_entities` enumerates `registry.warmable_entities()` — all 15).
The parity SUBSET assertion (`test_entity_vocabulary_parity.py:78-88`) therefore honestly covers
all nine — the guard is stronger than its own naming — but the commit message's "seven" and the
named-set docstring under-describe the widening. Ledger correction only.

**Verdict:** STANDS (test bites for all nine via the subset side); naming/receipt imprecision to ledger.

### D1-F3 — severity: MINOR — commit test-receipt census is wrong; one deterministic non-botocore failure exists (pre-existing, verified on main)

**Claim attacked:** "Local: 7821 passed; 1 pre-existing env failure (botocore[crt] login provider)
fails identically without this change."

**What I found:** my run of the affected suites in the cure worktree:
`tests/unit/services/test_query_service.py::TestEntityServiceValidateAdversarial::
test_project_gid_none_raises_service_not_configured` **FAILS** (DID NOT RAISE
ServiceNotConfiguredError), deterministically, in isolation and in suite (1 failed, 1843 passed).
I re-ran the identical test on the main checkout: **fails identically** — pre-existing, NOT a
regression of b62a431b. Root cause of the pre-existing failure: the test's
`mock_entity_registry.require.return_value = MagicMock()` makes `descriptor.body_parameterized`
truthy, so the A1 branch guard `if project_gid is None and not descriptor.body_parameterized`
(`services/entity_service.py:114`) never raises — the adversarial test has been silently vacuous
since the A1 receiver-surface change. Two ledger items: (a) the commit's failure census names only
botocore; (b) a broken adversarial test on main deserves its own fix.

**Verdict:** STANDS (no regression); receipt inaccuracy + pre-existing vacuous test to ledger.

### D1-F4 — severity: — (attack log; claims that survived)

- **Cache lifecycle (attack b): STANDS.** Invalidation is unchanged (`SchemaRegistry.on_reset(_clear_resolvable_cache)`
  resolver.py:748; `EntityProjectRegistry.reset` resolver.py:219-228). The NEW dependency,
  EntityRegistry, is frozen at module load (`EntityDescriptor` frozen dataclass, entity_registry.py:96-100;
  no register/mutation method — built once from the module tuple). Post-cure every admitted entity is
  admitted on STATIC facts (descriptor schema key + static GID, or body_parameterized), so
  dynamic discovery registrations can no longer change the set at all — strictly LESS stale-able
  than before. Note: the hot query path bypasses the cache entirely —
  `EntityService.get_queryable_entities` (entity_service.py:145) passes an explicit
  `project_registry`, which sets `using_singletons=False` (resolver.py:333) → no cache read/write.
  Only `/v1/resolve` uses the cached set.
- **Startup/circularity (attack c): STANDS.** The diff changes only function INTERNALS; both
  `get_registry()` and `schema_registry.list_task_types()` were already called by the pre-cure body
  (old line ~344/347); no new module-level imports. My bare-interpreter run exercised the full
  `_ensure_initialized` auto-wire from a cold process without lifespan — clean (schemas registered,
  only pre-existing drift-gate warnings).
- **Parity test honesty (attack d): STANDS with one flag.** The live rows/aggregate handlers gate
  entity_type through EXACTLY ONE path: `api/routes/query.py:382` / `:588` →
  `EntityService.validate_entity_type` (entity_service.py:99-101) → `get_resolvable_entities`.
  Path params are plain `str` (no enum), the static GET routes are registered before the
  parametrized ones (query.py:114), `resolve_section_index` returns None for a None section
  (services/query_service.py:179-180) — nothing else filters entity_type. Teeth are two-sided at
  the service level (unknown rejected WITH the full cured vocabulary,
  test_entity_vocabulary_parity.py:112-125) and the route-level 404 shape is already pinned by
  `tests/unit/api/test_routes_query_aggregate.py:125-142` (tc_ra002). FLAG: no route-level POSITIVE
  test drives `POST /v1/query/process_sales/rows|aggregate` through the HTTP surface; acceptance
  is proven at the service seam plus my read of the single-path handlers.
- **Aggregate / SAT-2 (attack e): STANDS-WITH-FLAG.** `AggregateRequest` still has no
  `project_gid` and `extra="forbid"` (query/models.py:184-210) — the 422 for body overrides
  remains; process_* do not need it: descriptors carry static GIDs, `validate_entity_type`
  resolves `ctx.project_gid` EntityRegistry-first (resolver.py:181-190), and the aggregate
  body-param guard `if ctx.project_gid is None` (query.py:595) passes. process_* have
  `body_parameterized=False` (descriptor default). Engine path is well-formed:
  `get_schema(to_pascal_case("process_sales"))="ProcessSales"` is registered (parity test
  :90-98 proves non-fallback resolution), `group_by section/is_completed` exist via BASE_COLUMNS
  (schemas/base.py:56,84). FLAG: "aggregatable" at runtime additionally requires a warm (or
  on-demand-buildable) process frame — `EntityQueryService.get_dataframe` raises
  CacheNotWarmError → honest 503 otherwise (services/query_service.py:621-629; query.py:623-631).
  First-call latency/503 on cold pipelines is expected until D1-F1's warm question is ruled.
- **Dynamic-entity regression (attack f): REFUTED as a risk — no such entity exists.** The only
  dynamic registration surface is `EntityProjectRegistry.register` via workspace discovery
  (`services/discovery.py:152-260`), whose universe is `ENTITY_MODEL_MAP + ["project","section"]` —
  every one descriptor-backed. No production caller of `SchemaRegistry.register` exists (grep:
  only metric/automation/hierarchy registries match). Old-loop admission REQUIRED a registered
  schema whose `.name` matched, and schemas register exclusively from descriptors
  (`_ensure_initialized`, dataframes/models/registry.py:282-318). Empirical: cure vocabulary (17)
  is a strict superset of main's (8). `unit_holder` (dynamic-registered, no schema) was outside
  the vocabulary before and after — correct both times.

---

## DIFF 2 — sidecar error passthrough (d81f7eee / s6 b33cc1d9)

### D2-F1 — severity: MINOR — no length bound on interpolated upstream content

**Claim attacked:** safe passthrough of satellite code/message/details.

**What I found:** `_upstream_suffix` (mcp/asana_mcp/errors.py:110-142) interpolates
`err.message` verbatim and joins the FULL `available_types` list with no cap (`:127-129`,
`str(a)` on arbitrary JSON members); only `validation_errors` is capped (3, `:134`).
In practice bounded: available_types is the satellite's `sorted(get_resolvable_entities())`
(17 post-cure), messages are satellite-authored (fleet-internal, S2S-authed). Prompt-injection
assessment, honestly graded: the only caller-influenced echo is the satellite reflecting the
request's own entity_type ("Unknown entity type: {caller string}") back to the SAME agent that
sent it — no new cross-principal channel; marginal amplification only. Defense-in-depth cap
(e.g. suffix truncation ~2KB) recommended, not required.

**Verdict:** STANDS-WITH-FLAG (add a cap at production reimplementation; ledger).

### D2-F2 — severity: MINOR — the auth-branch prose fence is one-sided

**Claim attacked:** "scope fence" — curated C3 text cannot be displaced.

**What I found:** the fence test (`test_errors_passthrough.py:test_warming_message_stays_curated`)
proves the WARMING side is pure. The auth branch now appends arbitrary upstream prose AFTER
"This is NOT a cache-warming condition." (errors.py:165-174). A satellite 401 whose message
itself said "cache warming" would yield contradictory prose in one error. `kind` classification
stays disjoint (status-gated branches), so the C3 machine invariant holds; this is prose-level
only, and satellite 401 messages are controlled. Ledger: consider asserting the auth suffix never
matches the warming lexicon, mirroring the existing disjointness test.

**Verdict:** STANDS-WITH-FLAG.

### D2-F3 — severity: — (attack log; claims that survived)

- **C3 invariant (attack h): STANDS.** 503 is the FIRST branch (errors.py:154-164), carries no
  `_upstream_suffix` call; the generic-4xx branch is `400 <= status < 500` (excludes 503); the
  server fallback (:203) also has no suffix. Each branch constructs exactly one message — no
  double-append path exists. A 503 body carrying details/message cannot leak (verified by branch
  structure + the fence test). `tests/test_errors_c3.py` present and green in both suites.
- **response.json() ×3 (attack i): STANDS.** `ctx.http` is a plain `httpx.AsyncClient`
  (context.py:25); tools call `await ctx.http.get/post` (tools/_common.py:41,56) which fully read
  the body (no `.stream()` anywhere), then `map_http_error(resp)` — `Response.json()` re-parses
  the loaded `.content` on each call; empty/non-JSON bodies raise and are caught to None
  (errors.py:62-64, 96-99). Triple-parse is a negligible inefficiency, not a hazard.
- **Test claims: STANDS.** s2 suite: 29 passed (my run). s6 unified: 98 passed (my run).
  Cherry-pick b33cc1d9 on s6 is byte-identical to d81f7eee for both `mcp/asana_mcp/errors.py`
  and `mcp/tests/test_errors_passthrough.py` (diff-verified). The 404 fixture shape matches the
  live satellite envelope (`raise_service_error` puts `available_types` inside `error.details`,
  api/errors.py:136-177 + services/errors.py:99-104; dossier live probe concurs).
- (ledger, pre-existing) `_WARMING_CODES` (errors.py:18) is defined but unreferenced — dead
  constant predating this diff.

---

## DIFF 3 — runbook Step 6.5 write-chain pre-smoke (G6)

### D3-F1 — severity: BLOCKING — the smoke as written fails deterministically at the push leg (false-red halts the witness)

**Claim attacked:** "an all-or-nothing result envelope with all three steps committed" from the
given invocation; "Any failure here is a witness-blocking finding ... do NOT proceed to Step 7
with a red smoke."

**What I found:** the runbook's `call_tool` passes ONLY `task_gid` + `tag_gid`
(runbook :224-231). The tool builds `save_fields={}` (composite_write.py:289-301), so step 2
sends `PUT /api/v1/tasks/{gid}` with body `{}` (composite_write.py:203-206). The satellite
accepts the empty model (`UpdateTaskRequest` all-optional, api/models.py:272-320) but the service
REFUSES it: `if not kwargs: raise InvalidParameterError("At least one field must be provided for
update")` (`services/task_service.py:273-274`) → HTTP 400 (`SERVICE_ERROR_MAP` services/errors.py:370)
→ step `push` FAILED → `refused_incomplete` with `add_tag` already committed. The composite's own
suite never exercises an empty save (`mcp/tests/test_composite_write_s3.py:148,165` pass
`{"notes": ...}`), so nothing caught it. Result: a healthy chain smokes RED, the operator halts
per the runbook's own instruction, and the pre-witness gate defeats itself. One-line fix: include
a save field in the smoke args (e.g. `"notes": "mcp write-chain smoke 2026-07-19"`) or teach the
tool to skip an empty push with an explicit receipt.

**Verdict:** REFUTED-THE-FIX.

### D3-F2 — severity: MINOR — the Rule-fire EXPECT contradicts the no-re-fire C2 outcome

**Claim attacked:** "Expect: ... the sandbox Rule firing again in the UI (consistent with your
§3.3 C2 record)."

**What I found:** Step 6's disposition is mechanical: no-re-fire → UV-P#4 DISCHARGED (runbook
Step 6). If C2 recorded no-re-fire — the discharge outcome the program wants — then the smoke's
`mark_complete` (true→true re-PUT, no completion transition) fires NO Rule, and an operator
reading "Expect ... the Rule firing again" sees an absent expected observable on a green smoke.
The parenthetical is rescueable but the sentence asserts a fire. Reword to: "Rule behavior must
match the §3.3 record — if C2 recorded no-re-fire, expect NO new fire."

**Verdict:** STANDS-WITH-FLAG (drafting ambiguity; witness-operator confusion risk).

### D3-F3 — severity: — (attack log; claims that survived)

- **fastmcp API (attack j): STANDS.** Installed fastmcp in the s6 venv is 3.4.4;
  `fastmcp.client.client.CallToolResult` is a dataclass with fields
  `content, structured_content, meta, data, is_error` (verified via `inspect.getsource` in that
  venv). The runbook's `getattr(res, "structured_content", None)` with a `res.content` block-text
  fallback is correct for this version; `call_tool(name, args)` signature matches
  (`raise_on_error=True` default makes a tool failure raise loudly — acceptable for a smoke).
  `build_instrumented_server` exists (mcp/asana_mcp/assembly.py:37) and the tool name
  `asana_complete_tagged_task` is bound (composite_write.py:269,306).
- **Ordering (attack k, remainder): STANDS.** C2's evidence windows are captured and recorded in
  §3.3 during Step 6; a later smoke cannot retroactively pollute them, and the C2 probe refuses
  to run under the write flag (runbook cites c2_sandbox_reput_probe.py:137), so sequencing is
  self-enforcing. `mark_complete` on the already-complete task converges: the route is a plain
  partial-update forward (api/routes/tasks.py:246-301, `completed` at :294); true→true is
  state-idempotent. `add_tag` re-run is a documented no-op 200 (tasks.py:524-556). The runbook's
  `composite_write.py:19` citation for the first leg matches the module docstring's verb table.
- **Flag hygiene (attack l): STANDS.** The flag travels only as a per-process env prefix
  (`env ASANA_MCP_ENABLE_WRITE_SURFACE=true`); `write_surface_enabled` reads
  `os.environ`/settings at register time (composite_write.py:82-96), settings are pure env reads
  (mcp/asana_mcp/settings.py:39-47), no dotenv/file persistence anywhere in the package, and the
  server object lives and dies inside the subprocess. The staging invariant ("flag never flipped
  anywhere persistent") holds; the shell flag statement is accurate.

---

## Gate summary

| ID | Severity | Verdict |
|---|---|---|
| D1-F1 | MATERIAL | REFUTED (contained-scope claim); fix itself STANDS-WITH-FLAG |
| D1-F2 | MINOR | STANDS (naming imprecision to ledger) |
| D1-F3 | MINOR | STANDS (receipt census wrong; failure pre-existing on main) |
| D2-F1 | MINOR | STANDS-WITH-FLAG |
| D2-F2 | MINOR | STANDS-WITH-FLAG |
| D3-F1 | BLOCKING | REFUTED-THE-FIX |
| D3-F2 | MINOR | STANDS-WITH-FLAG |

Remediation path: D3-F1 is a one-line runbook (or tool) fix + re-verify; D1-F1 requires an
operator-visible disclosure/ruling on the 9-pipeline warm-path delta against the C3 429-banking
soak before witness re-entry; minors to ledger.

GATE VERDICT: BLOCKED(D3-F1)
