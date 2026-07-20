# asana_mcp — FastMCP sidecar POC (asana-mcp-v1, sprint-2 read-surface)

> **REFERENCE / THROWAWAY POSTURE.** This is a proof-of-concept, NOT production
> code, and NOT to be promoted before the charter §4 probe rules COMMIT
> (constraint 8 / V-4). It exists to make **felt-gate limb (a)** demonstrable: an
> agent, *from schemas alone*, answers a real business question via
> `list_entity_types → describe_entity → query_rows → query_aggregate`.
> The felt VERDICT is the operator's alone; this code only *enables the witness*.

Grounding: charter `DECISION-fleet-mcp-program-alignment-2026-07-17.md` (GOVERNS),
shape `asana-mcp-v1.shape.md` §2 sprint-2, spike `SPIKE-asana-mcp-exposure.md`
(tools 1-6, POC criteria :210-215), mount-seam `asana-mcp-v1.mount-seam.md` (FROZEN).

## What it is

A **FastMCP 3.4.4 sidecar** that speaks HTTP to the `autom8y-asana` REST **S2S**
surface and exposes the 5 read tools as MCP tools:

| # | Tool | Backing endpoint | Tier (C1) |
|---|------|------------------|-----------|
| 1 | `list_entity_types` | `GET /v1/query/entities` | thin discovery |
| 2 | `describe_entity` | `GET /v1/query/{t}/fields` + `/relations` (+ `/sections`) | thin discovery |
| 3 | `query_rows` | `POST /v1/query/{t}/rows` | rich native |
| 4 | `query_aggregate` | `POST /v1/query/{t}/aggregate` | rich native |
| 5 | `resolve_entity` | `POST /v1/resolve/{t}` | rich native |

Tool 6 (`match_business`) is **surface-not-POC** (shape §0) — stub-noted only, not
built (`tools/_match_business_stub.py`).

## The load-bearing fence (constraint 5)

The MCP process **NEVER imports `autom8_asana`** (the domain SDK) and makes **ZERO
direct Asana calls**. Auth **joins** the fleet bridge `autom8y_core.TokenManager`
(SVR-8) — zero new auth-minting code. Proven by `tests/test_import_safety.py` (AST
scan + clean-subprocess: importing `asana_mcp` pulls neither `autom8_asana` nor
even `autom8y_core` — the bridge import is lazy).

## Run the tests

```bash
# any interpreter with httpx + pydantic + pytest + pytest-asyncio (fastmcp optional)
python -m pytest mcp/tests -q
```
Tests use `httpx.MockTransport` with envelope shapes transcribed from
`query/models.py` — they NEVER hit live Asana and do NOT require fastmcp (the pure
handlers are fastmcp-free). Result: **23 passed** with fastmcp present; **22 passed
+ 1 skipped** without.

## Deliberate shortcuts (production gaps — read before promoting)

1. **Live S2S path is wired but unexercised in tests.** `bridge._default_token_provider`
   builds the real `TokenManager.from_env()`; tests inject a fake token + fake
   transport. A live smoke against a real satellite `/ready` + S2S JWT is NOT run
   here (directive: do not hit live Asana). *Production*: an integration test
   against a staging satellite.
2. **Readiness probe is per-call, uncached.** Every tool call hits `/ready` first
   (proves the gate). *Production*: cache readiness with a short TTL to avoid a
   round-trip per tool call.
3. **Readiness posture is fail-CLOSED by default (`Settings.readiness_fail_open`).**
   The full C9 fail-open/fail-closed declaration is **sprint-4's** (C3/C9).
4. **Schema-drift guard is a content-hash canary, not a semantic differ.**
   `tests/test_schema_canary.py` pins the sha256 of `query/models.py` and checks
   mirrored-field tokens (A7 semantic-lite). The **A7 semantic-score static gate**
   is the production upgrade. If the canary trips, re-review `schemas.py` against
   the native `RowsRequest`/`AggregateRequest` and re-pin.
5. **`where`/`having` predicates are typed `list | dict`, not the native recursive
   `PredicateNode` union.** The full grammar lives in the field *description* (LLM
   schema-grounding) — a documented ergonomic curation. Server-side `extra="forbid"`
   still enforces strictness on the real request.
6. **`server.sidecar_context` attribute** is a throwaway convenience so sprint-3
   (write tools) and sprint-6 (assembly) can reach the ctx while honoring the
   frozen `create_server(settings) -> FastMCP` signature. *Production*: thread ctx
   through an explicit assembly container. (Downstream may also rebuild via
   `build_context(settings)`.)
7. **No observability, no rate-cap, no budget partition.** All of that is
   **sprint-4's** (`instrument(mcp, settings)` hook point left uncalled; the
   `ASANA_MCP_BUDGET_*` extension point is marked in `settings.py`). Adding it here
   would be prototype gold-plating.
8. **No auth beyond the S2S bearer.** Route curation is the Phase-1 security
   boundary (constraint 6); scopes are documentation-only in asana. External OAuth
   (V-2) is explicitly out of scope.

## What didn't work / findings (saves future effort)

- **FastMCP 3.4.x has no `get_tools()`.** The tool-listing API is
  `await mcp.list_tools()` (returns `list[Tool]`, each with `.name` and
  `.parameters` JSON schema). `get_tool` is singular. Wire s6 assembly against
  `list_tools()`.
- **`@mcp.tool(name=..., description=...)` works** in 3.4.4; a single Pydantic-model
  parameter (`args: RowsArgs`) lands as a nested object in the tool `inputSchema`
  (`properties: {entity_type, args}`) — the hand-authored schema *is* the tool
  contract (C2/R6 satisfied).
- **The honest error messages cross-reference the other class** ("this is NOT an
  auth failure" / "NOT a cache-warming condition"). That disambiguation is a
  FEATURE — so the C3 tests assert the structured `kind`, not message substrings.

## Feasibility vs targets

| Dimension | Target | POC result |
|-----------|--------|------------|
| Limb-(a) chain works from schemas alone | required | ✅ 5 tools, list→describe→rows→aggregate proven against faked HTTP + real FastMCP |
| Constraint 5 (no domain SDK / zero Asana calls) | hard fence | ✅ AST + subprocess proof; `autom8y_core` not even pulled at import |
| Honesty passthrough (stale_served/honest_empty/contract_complete) | visible to LLM | ✅ lifted top-level; not fabricated where absent |
| Cold-frame 503 → retryable, never auth-shaped (C3) | invariant | ✅ disjoint classes asserted |
| FastMCP pin (R5/UV-P-1) | protocol 2025-11-25 + FastMCP minor | ✅ re-probed live: FastMCP 3.4.4 pinned `>=3.4.4,<3.5.0` |
| Schema-drift guard (R6/A5) | pin-and-canary | ✅ content-hash canary (A7 semantic gate deferred) |

## Demo script (capabilities AND limitations)

1. **Show the fence.** `python -m pytest mcp/tests/test_import_safety.py -q` →
   the sidecar cannot import the domain SDK. *(Limitation shown: it is a POC — the
   live TokenManager path is not exercised here.)*
2. **Show limb (a) end-to-end.** `python -m pytest mcp/tests/test_discovery_tools.py
   mcp/tests/test_query_tools.py -q` → discovery → rows → aggregate, with honesty
   flags surfaced. *(Limitation: faked HTTP, not a live satellite.)*
3. **Show the honest failure modes.** `python -m pytest mcp/tests/test_errors_c3.py
   mcp/tests/test_readiness_gate.py -q` → a warming satellite yields a retryable
   "cache warming" refusal, never "auth failed".
4. **Show the real server.** With fastmcp installed, `create_server()` →
   `await mcp.list_tools()` returns exactly the 5 read tools. *(Limitation:
   match_business is intentionally absent; observability/rate-cap are sprint-4.)*

## Handoff to downstream sprints

- **sprint-3 (write-surface):** add write-tool modules exposing `register(mcp, ctx)`;
  wire against `server.sidecar_context`. Build only — EXPOSURE is gated by GATE-BW.
- **sprint-4 (observability):** implement `instrument(mcp, settings) -> FastMCP`
  (idempotent); own the `ASANA_MCP_BUDGET_*` vars + rate cap; finalize the C9
  readiness posture; contract-test the honesty passthrough (already true here).
- **sprint-6 (felt-gate harness):** assemble `create_server() → register(...) →
  instrument(...)`; stage the operator witness for limb (a). Do NOT speak the verdict.

## Constraint discovered (FLAG for the seam owner / sprint-4)

Running the repo's `ruff` over this POC surfaces **TID251**: raw `httpx` is banned
in `autom8y-asana` — the convention is `autom8y_http.Autom8yHttpClient`
(`docs/guides/sdk-only-imports-migration.md`), and `autom8y-http[otel]` is already
a satellite dependency providing **W3C traceparent auto-propagation on outbound
httpx calls**.

This POC uses raw `httpx.AsyncClient` **because the FROZEN mount-seam mandates that
exact type** (`SidecarContext.http: httpx.AsyncClient`). So the POC is
seam-conformant — but there is a real **seam-vs-repo-convention tension**:

- sprint-4 needs traceparent across the sidecar→REST hop (C4/C5). `autom8y_http`
  provides exactly that.
- If production adopts `autom8y_http.Autom8yHttpClient`, the seam's
  `SidecarContext.http` **type changes**.

**Recommendation (not a silent patch):** the mount-seam owner (Potnia) and
sprint-4 should evaluate re-typing `SidecarContext.http` to
`autom8y_http.Autom8yHttpClient` for the production build. This POC deliberately
holds the frozen seam and flags the divergence rather than patching it.
