---
type: review
status: proposed
---

# BUILD — ECS 1390/60s fair-share self-cap (in-path wiring)

> S5 ECS-1390-SELFCAP · satellite `autom8y-asana` · grade **MODERATE** (lighter rigor,
> STAGED PR, UNFLIPPED). Branch `feat/ecs-1390-fair-share-selfcap` off origin/main
> `b3da9d8c`. The node-8 flip-to-enforcement stays **operator-sovereign** — this build
> ships the mechanism byte-identical-INERT behind the existing
> `ASANA_BUDGET_ALLOCATOR_ENABLED` knob; it never activates.

## 1. What was wired (file:line)

The gap (verified by S4): the ECS/`FAIR_SHARE` GET path had NO in-path `gate.admit()`.
`1390` existed only as a config constant + advisory-only overage telemetry
(`budget_allocator.py:423` `observe_admission`); `_floor_paced` returns the fetch
unchanged off the warmer lane. This build adds the in-path cap, mirroring the warmer
floor gate (`dataframes/builders/hierarchy_warmer.py::_floor_paced`).

**Reused machinery (unchanged):** the 1390/60s config
(`src/autom8_asana/config.py:859` `fair_share_max_requests=1390`;
`src/autom8_asana/settings.py:610`) and the `WarmerFloorGate` token-bucket primitive
(`budget_allocator.py`). No parallel surface invented.

**New — `src/autom8_asana/transport/budget_allocator.py`:**
- `:347` — `_fair_share_gate_instance` + `_fair_share_gate_lock`: the MEMOIZED
  process-singleton gate slot (built lazily; never constructed while INERT).
- `:407` — `fair_share_floor()`: pure config read → `PublishedFloor(1390, 60)`
  (C-11-decoupled, symmetric with `published_floor()`).
- `:421` — `fair_share_gate()`: returns the ONE shared 1390/60s gate per process
  (PC-1 unification / PC-4 sizing). Memoization is load-bearing — a fresh gate per
  GET would reset the bucket and never cap a concurrent burst.

**New — `src/autom8_asana/transport/asana_http.py`:**
- `:589` — `_resolve_fair_share_gate(method)`: returns the shared gate iff
  `method == GET` AND NOT `running_in_warmer_lane()` AND `allocator.enabled`; else
  `None` (byte-identical no-op). Fail-OPEN on any fault (PC-3 / C-4).
- `:625` — `_fair_share_admit(method)`: `await gate.admit()` (`:640`) BEFORE the
  outbound GET, then `observe_admission(Lane.FAIR_SHARE)` (AC-2 denominator).
- `:652` — `_note_fair_share_failopen(error)`: emits `budget_lane_failopen`,
  mirrors `HierarchyWarmer._note_floor_failopen`.
- `:696` — the in-path call: `await self._fair_share_admit(method)` in `_request`,
  placed AFTER the circuit-breaker check (an open breaker never burns a token) and
  BEFORE the semaphore/rate-limiter loop.

**Reversibility / INERT guarantee:** `enabled=False` (default) → `_resolve_fair_share_gate`
returns `None` → `_fair_share_admit` early-returns → the ECS GET path is byte-identical
to the pre-allocator baseline. The knob binds per-process-fresh via
`get_budget_allocator()` → `BudgetAllocatorConfig.from_env()` (ITEM-D dead-knob
discipline preserved). Rollback = flip the knob false; no persistent state.

## 2. Two-sided discriminating test (discriminating-canary doctrine; NO G-THEATER)

New: `tests/unit/transport/test_budget_allocator_fair_share_cap.py` (11 tests, all in
silico — ZERO live Asana calls, ZERO real sleeps; F-b honored). Mirrors
`test_budget_allocator_warmer_floor.py` + `test_canary_f1a_budget_allocator.py`.

The RED-before is a deliberately-OVER-budget INPUT the live cap correctly sheds — NOT a
defect injected into a working surface. Empirically demonstrated:

```
BROKEN INPUT  (1400-burst) @ 1390-cap   -> admitted=1391  (RED: excess SHED, 9 rejected)
BROKEN INPUT  (1400-burst) @ 2000-loose -> admitted=1400  (teeth: capped<1400 FAILS here)
REAL INPUT    (1000-demand) @ 1390-cap  -> admitted=1000  (GREEN: all pass)
```

- **CORRECTLY CAPPED (broken input):** a 1400-GET burst inside one 60s window admits
  ~1390; the excess is shed past the window — the ECS service stops starving the shared
  1500/60s Asana budget. (`test_over_budget_burst_is_capped_and_real_demand_passes`)
- **GREEN (real input):** a 1000-GET (≤1390) demand passes in full within the window.
- **TEETH:** a deliberately-loose 2000/60s cap admits the SAME 1400-burst in full —
  proving the shed is attributable to the 1390 value, not the harness
  (`test_cap_value_has_teeth_loose_cap_admits_the_same_burst`).
- **Seam (mirror canary pair-c), two-sided byte-identity:** armed + ECS-lane + GET
  resolves the shared gate (GREEN); disabled / warmer-lane / POST-PUT-DELETE resolve
  `None` (byte-identical RED). Fail-open returns `None` + tripwire.

**Results:** new suite `11 passed`; transport dir `187 passed`; full unit suite
`14853 passed, 13 skipped, 3 xfailed`. ruff check + format clean; mypy strict clean on
both changed source modules. The ONLY 2 full-suite failures
(`test_cache_warmer.py::test_missing_bot_pat` / `test_missing_workspace_gid`) reproduce
IDENTICALLY on baseline `b3da9d8c` with my edits stashed — a pre-existing local
`botocore[crt]` dependency gap, NOT a regression from this build.

## 3. DEVIATION flagged for human review — killswitch invariant updated

`tests/unit/transport/test_budget_allocator_killswitch.py:79` previously asserted the
allocator is STRUCTURALLY ABSENT from `asana_http.py` (byte-identity by absence). An
in-path cap on the transport GET path necessarily references the allocator there, so
that half of the invariant is superseded by the directed design. I did NOT silently
weaken it — I replaced it with a STRONGER, more specific guarantee:
- the per-resource `clients/**` modules remain STRUCTURALLY allocator-free (unchanged);
- `asana_http.py` may reference the allocator ONLY function-locally (no module-level
  import), asserted by AST; and
- `_resolve_fair_share_gate` is proven enabled-guarded (early-return when disabled) by a
  new AST test (`test_ast_fair_share_resolve_is_enabled_guarded`), symmetric with the
  existing `_attach_to_budget_allocator` guard proof.

This mirrors the warmer floor gate, whose byte-identity is ALSO runtime-guard-based
(`_floor_paced` returns the SAME closure object when inert), not structural absence.
**Reviewer action:** confirm the runtime-guard byte-identity contract is acceptable for
the transport GET path (it matches the already-shipped warmer-lane precedent).

## 4. What clause (c) STILL owes (NOT discharged here)

This cap is **read-side (GET) only**. Explicitly out of scope and undischarged:

- **Write-side three-writer arbitration.** The legacy monolith `asana_handler`
  write-storm is NOT arbitrated by this cap — `_fair_share_admit` no-ops on
  POST/PUT/DELETE (`asana_http.py:589` `if method.upper() != "GET": return None`). The
  three-writer contention on the shared budget remains unmediated on the write path.
- **AC-5 near-zero cap sizing from live measurement.** The near-zero workflow-Lambda
  soft-caps remain config defaults sized from window-artifact zeros, NOT from live CWLI
  measurement (F-b forbids live probes at this altitude). Only the W-A/W-B windows are
  addressed by the static 1390; telemetry-driven near-zero sizing is owed to
  node-9/operator (matches the pre-existing AC-5 DEFER in `budget_allocator.py`).

Both remain honest gaps for a subsequent leg; neither is a precondition for the ECS
GET-path self-cap shipped here.

## 5. Fence attestation

- STAGED PR only — NOT merged.
- `ASANA_BUDGET_ALLOCATOR_ENABLED` NOT flipped; NO ECS activation.
- Mechanism is byte-identical-INERT until the operator flips the knob (node-8 flip is
  operator-sovereign).
- Built in a blessed worktree off origin/main; local diverged `d544b094` never read for
  code state, never committed on.
