---
type: spec
decision_subtype: tdd
id: TDD-OBW-REMEDIATION
artifact_id: TDD-onboarding-walkthrough-remediation-2026-07-01
schema_version: "1.0"
status: draft
date: "2026-07-01"
rite: 10x-dev
station: N2 (architect)
initiative: "First-Attach Remediation — onboarding-walkthrough attach failure (fleet-wide observability swallow + autom8_data fault naming)"
upstream: ".ledge/specs/PRD-onboarding-walkthrough-remediation-2026-07-01.md"
verification_tree: "origin/main @ caade0033759d6deb284133a58b63416d5d81543"
worktree_live: "cb4b42017b71f582e7bd09945e96730e6f81ec33 (off-branch, dirty)"
deciders: [architect (10x-dev)]
consulted: [principal-engineer (downstream implementer), qa-adversary (broken-fixture RED proof)]
evidence_grade: MODERATE
evidence_grade_rationale: >
  Self-authored design within 10x-dev; caps at MODERATE per self-ref-evidence-grade-rule.
  All exception-class + premise claims are executable/file-read receipts (§0). The
  fault-NAMING (R1 vs R2) is POST-DEPLOY and is NOT claimed here (G-RUNG).
related:
  - ADR-onboarding-walkthrough-observability-taxonomy-2026-07-01
---

# TDD: Onboarding-Walkthrough First-Attach Remediation — Swallow-Close + Fault-Naming Taxonomy

> Terminal rung of THIS arc = **swallow-closed** (FR-1 logger + FR-2 excepts widened + broken-fixture two-sided RED→GREEN + PR surfaced). `fault-named` and `realized` are POST-DEPLOY (operator re-invoke), carried by the N5 HANDOFF. This design never claims to name the fault pre-deploy.

## §0 Verification Receipts (G-PROVE — no claim without a receipt)

**Grounding.** All source anchors below are on files with **zero diff between origin/main `caade003` and worktree `cb4b4201`** (`git diff caade003 -- <files> --stat` = empty for every source/test file; only `justfile` drifted, re-anchored below). Design grounds cleanly on origin/main.

### R-1 — OQ-1 RESOLVED: the autom8y_core data-service exception taxonomy (executable receipt)

`autom8y-core 4.9.0` installed at `.venv/lib/python3.12/site-packages/autom8y_core/`. Runtime probe (`​.venv/bin/python -c ...`):

```
autom8y_core.__version__ = 4.9.0
MRO DataServiceUnavailableError: DataServiceUnavailableError -> DataServiceError -> TransportError -> Exception -> BaseException
DSU subclass of DataServiceError : True
DSV subclass of DataServiceError : True
DataServiceError subclass Transport: True
InvalidServiceKeyError <: DataServiceError : False
InvalidServiceKeyError <: TokenAcquisitionError: True
=> DataServiceError and TokenAcquisitionError are SIBLINGS under TransportError: True
```

Hierarchy (from `autom8y_core/errors.py`, file-read):

```
TransportError                                   errors.py:129   (== Exception subclass)
├── TokenAcquisitionError                        errors.py:150   ── AUTH / S2S family (R2)
│   ├── InvalidServiceKeyError  (http 401)       errors.py:166   ── R2: bad/expired/revoked S2S key
│   ├── ServiceUnavailableError (http 503)       errors.py:177
│   ├── RetryExhaustedError                      errors.py:184
│   └── RateLimitedError        (http 429)       errors.py:202
└── DataServiceError            (http 500)       errors.py:239   ── DATA family base (R1-leaning)
    ├── BusinessNotFoundError   (http 404)       errors.py:246
    ├── GidLookupError          (http 503)       errors.py:262
    ├── DataServiceUnavailableError (http 503)   errors.py:368   ── transient infra (timeout/5xx/circuit) — R2-transient candidate
    ├── DataServiceValidationError  (http 400)   errors.py:485   ── 4xx data-shape (incl. INVALID_BUSINESS_GUID_FORMAT) — R1 candidate
    └── (DataIntake* / DataMessage* / DataPayment* / Scheduling* siblings)
```

**Decisive fact:** `DataServiceError` (data family) and `TokenAcquisitionError` (auth family) are **SIBLINGS** under `TransportError` — `InvalidServiceKeyError` is NOT a `DataServiceError`. This is the linchpin of the R1/R2 taxonomy (§4, §6).

**Exact classes each call can raise** (file-read of `autom8y_core/clients/data_service.py`):

| Call | Raises | Receipt |
|------|--------|---------|
| `resolve_routing_address_by_phone_async` (data_service.py:438) | `ValueError` | composes `format_routing_address(business.guid)` (L482) which **raises `ValueError`** on a non-canonical stored GUID — `routing.py:105-108` (`if not _is_canonical_uuid_v4(guid): raise ValueError(...)`) |
| `resolve_routing_address_by_phone_async` | `DataServiceUnavailableError` | via `get_business_by_phone_async` on timeout/transport/non-200-non-404 — data_service.py:377,383,397 |
| `resolve_routing_address_by_phone_async` | `DataServiceError` (base) | via `get_business_by_phone_async` malformed body — data_service.py:406 |
| `get_business_by_guid_async` (data_service.py:631) | `DataServiceUnavailableError` | `_fetch_business_envelope` timeout/transport/5xx — data_service.py:736,741,770 |
| `get_business_by_guid_async` | `DataServiceValidationError` | `_fetch_business_envelope` 4xx (INVALID_BUSINESS_GUID_FORMAT) — data_service.py:763 |
| `get_business_by_guid_async` | `DataServiceError` (base) | `_fetch_business_envelope` malformed body — data_service.py:778 |
| both (via `BaseClient` token path) | `InvalidServiceKeyError` / `TokenAcquisitionError` | token acquisition (S2S) precedes the HTTP call and is NOT caught by the `except httpx.*` clauses — propagates as an **auth-family** escape (R2) |

> Note — neither call raises a bare `ValueError` from the *anchor* by-guid path (`get_business_by_guid_async` catches pydantic `ValueError` and re-raises as `DataServiceError`, data_service.py:778). The only bare-`ValueError` raise-site is `format_routing_address` in the **resolve** leg. Ladders are sized to the verified raise-sites — **no dead except legs** (anti-strawman).

### R-2 — Pythia premise (a) CONFIRMED: `extract_address_guid` cannot raise

`identity_guard.py:68` (file-read): `return gated_address.split("@", 1)[0].lower()`. Pure string ops on a `str`; no raise-site. A non-canonical local-part becomes a lowercased string that fails the gid-exact compare (`workflow.py:545`) → `guid_anchor_mismatch` **SKIP** (`workflow.py:557`), never a failure. ⇒ the dispatch's "R1 = GUID→`ValueError`" hypothesis does **not** ground *in-tree via the identity guard*. (It DOES ground SDK-side via `format_routing_address` on the *stored business GUID* — a different GUID, R-1 above — which is exactly why FR-2 `resolve_invalid_input` is load-bearing, not dead.)

### R-3 — Pythia premise (b) CONFIRMED: `just invoke` is LOCAL, not the deployed Lambda

`justfile:311-312` (origin/main; :306-307 on worktree): `invoke workflow_id *args: uv run python scripts/invoke_workflow.py {{workflow_id}} {{args}}`. `scripts/invoke_workflow.py:1-6`: "Developer CLI for invoking workflows directly ... local testing. Constructs a workflow, calls enumerate_async + execute_async". `grep -rn "aws lambda invoke" justfile scripts/` = **empty**. ⇒ local invoke runs in-process against the current tree; it does NOT exercise the deployed image and cannot produce the CloudWatch line that names the fault. AC-3d is inherently **post-deploy** (operator).

### R-4 — The swallow CONFIRMED + the anchor-escape CONFIRMED

- `bridge_base.py:220-237` (file-read): `_run_one` wraps `process_entity` in `try/except (Exception) as exc` (L222-226) returning `BridgeOutcome(status="failed", error=WorkflowItemError(error_type="unexpected_error", message=str(exc), recoverable=True))` (L227-237). **No `logger.` call in the block.** `asyncio.gather` at L239. Module logger present: `from autom8y_log import get_logger; logger = get_logger(__name__)` (L19,44).
- `engine.py` (GFR `resolve_async` spine): `grep -n "try:\|except"` = **empty** — the engine has NO broad catch. The only raises in the by-guid path are `UnresolvedError`/`AmbiguousCardinalityError`/`GuardViolationError` (engine.py:151,158,195,212 — all `GfrError`-family). A `DataService*`/auth exception from `truth_source.py:68` (`record = await verifier.get_business_by_guid_async(company_id)`, UNWRAPPED) propagates **raw** through `anchor_company_id` → escapes all three GFR excepts (`workflow.py:497,512,525`, disjoint hierarchies) → hits the terminal swallow. **PRD Anchor C confirmed with code evidence.**
- House log idiom = **structlog** via `autom8y_log`. `structlog.processors.format_exc_info` IS in the configured chain (`autom8y_log/backends/structlog_backend.py:109`) ⇒ `exc_info=exc` renders a full traceback into the `exception` field, config-independent. Existing precedent: `logger.error("onboarding_walkthrough_resolve_unavailable", task_gid=gid, office_phone=masked, error=str(exc))` (workflow.py:445). Masking helpers present: `mask_phone_number` (imported workflow.py:54), `identity_guard.mask_guid` (identity_guard.py:140).

---

## §1 Problem & Scope

On 2026-07-01 the onboarding-walkthrough workflow processed exactly one task (Neu Life, GHL, `1213653428400851`) and failed fast (0.51s, `failed:1`) with **no per-task log** — un-diagnosable, because the shared bridge runner's terminal broad-catch swallows the escaping exception without logging (R-4). This TDD closes that swallow **in the shared runner** (fleet-wide) and widens the resolve/anchor excepts so KNOWN autom8_data faults become NAMED `failed` reasons — with **no bandaid and no bridge rewrite**, preserving per-entity isolation and every INV-1..6.

**In scope (code, this arc):** structured error log in `bridge_base.py:222-237`; widened resolve ladder `workflow.py:440-460`; widened anchor ladder `workflow.py:490-538`; unit tests `test_bridge_base.py` (AC-1), `test_onboarding_walkthrough.py` (AC-2); specification of the post-deploy receipt + R1/R2 tree (§6, N5 HANDOFF).

**RESERVED (operator, past the rung):** image rebuild/redeploy; re-enable; the live production re-invoke; any attach/mint/send; the R2 sre/platform fix; deck-map/selection changes.

## §2 System Context

`bridge_base.BridgeWorkflowAction` is the SHARED runner for ALL asana bridge workflows (`insights_export`, `conversation_audit`, `payment_reconciliation`, `onboarding_walkthrough`). The FR-1 fix lands here → fleet blast radius **by construction** (G-PROPAGATE); it benefits every sibling. FR-2 lands in the onboarding-walkthrough `workflow.py` legs only (the resolve/anchor ladders are workflow-specific policy).

```
execute_async (bridge_base.py:197)
  └─ _run_one (L220)  ── per-entity isolation boundary (semaphore + asyncio.gather L239)
       └─ try: process_entity(entity)              [onboarding_walkthrough.workflow.process_entity]
       │     ├─ RESOLVE (workflow.py:440)  ── SDK phone leg → may raise ValueError / DataService* / auth
       │     │     └─ [FR-2] widened resolve ladder → NAMED failed BridgeOutcome (returns; never reaches terminal)
       │     └─ ANCHOR  (workflow.py:490)  ── GFR by-guid (truth_source.py:68) → may raise DataService* / auth
       │           └─ [FR-2] widened anchor ladder → NAMED failed BridgeOutcome (returns; never reaches terminal)
       └─ except Exception as exc:  ── TERMINAL last-resort net (residual/unanticipated + auth-family R2)
             └─ [FR-1] logger.error("bridge_entity_failed", ...) BEFORE the failed return   ← the swallow-close
```

**Dependency direction (DIP, preserved):** the low-level resolution substrate (`truth_source.py`, `engine.py`) does NOT decide per-entity disposition — it raises typed exceptions and lets the high-level workflow policy (the `workflow.py` ladders) own the `failed`/`skipped` semantics. FR-2 widens the ladder at the **workflow boundary**, NOT at `truth_source.py:68` (see ADR D4 — wrapping truth_source would force a lossy `bool`/`GfrError` conversion that re-buries the fault).

## §3 FR-1 — The Swallow-Close (bridge_base.py:222-237)

Insert one structured **ERROR** log immediately BEFORE the `failed` return, inside the existing broad-catch. The catch is **not narrowed** (INV-3 held); this is purely additive observability.

```python
async def _run_one(entity: dict[str, Any]) -> BridgeOutcome:
    async with semaphore:
        try:
            return await self.process_entity(entity, params)
        except Exception as exc:  # noqa: BLE001  # BROAD-CATCH: boundary -- per-entity isolation
            item_id = entity.get("gid", "unknown")
            logger.error(
                "bridge_entity_failed",
                workflow_id=self.workflow_id,   # fleet-shared runner → name WHICH workflow faulted
                task_gid=item_id,
                error_type=type(exc).__name__,  # the escaping class → names R1 vs R2 in the live log
                message=str(exc),
                exc_info=exc,                    # structlog format_exc_info → full traceback in `exception` field
            )
            return BridgeOutcome(
                gid=item_id,
                status="failed",
                reason=None,
                error=WorkflowItemError(
                    item_id=item_id,
                    error_type="unexpected_error",  # contract-stable (see ADR D5 — FR-6/OQ-4 DEFERRED)
                    message=str(exc),
                    recoverable=True,
                ),
            )
```

**Placement:** BEFORE the return. **Isolation (INV-3, NFR-1):** still returns the per-entity `failed` BridgeOutcome; `asyncio.gather` (L239) unaffected; one task's fault never aborts the sweep. **Level:** ERROR (mirrors the resolve-leg precedent, workflow.py:445). **Event name:** `bridge_entity_failed` — fleet-altitude (NOT `onboarding_walkthrough_*`), correct for the shared runner. **`workflow_id`** is added so a fleet-shared line self-identifies the faulting workflow.

**OQ-5 — traceback FULL, not truncated (decided; see ADR D2).** Via `exc_info=exc` + the configured `format_exc_info` processor (R-4). Rationale: (1) this block fires only on the *failure* path — a healthy sweep (e.g. `insights_export succeeded:67/failed:0`) emits ZERO of these lines; volume scales with faults (already near-zero by SLO), not throughput. (2) The entire remediation exists to make a single invisible failure diagnosable; a truncated traceback could elide the SDK frame (`format_routing_address` / `_fetch_business_envelope`) that discriminates R1 vs R2 — re-opening the gap we are closing. (3) `format_exc_info` renders frames + the exception string, NOT local-variable values, so a full traceback does not dump locals (NFR-3, §5). Bounded exception: a future workflow that legitimately fails thousands of entities/sweep is a per-sink sampling concern, NOT a reason to blind the shared runner.

## §4 FR-2 — Except-Widening Taxonomy (workflow.py resolve L440-460 + anchor L490-538)

**Import addition** (workflow.py:35): add `DataServiceError, DataServiceValidationError` alongside the existing `DataServiceUnavailableError`.

**Design rule (the linchpin):** widened legs catch the **DataServiceError family (data, R1-leaning) by name** and deliberately do **NOT** catch `TransportError`/`TokenAcquisitionError` (auth). An auth-family escape (`InvalidServiceKeyError`, R-1) is NOT a `DataServiceError` (R-1 receipt) → it falls through the named data legs to the now-logged terminal net, where its true class name (`InvalidServiceKeyError`) surfaces as an unambiguous **R2** signal. Catching the `TransportError` grand-base instead would collapse R1 and R2 into one net and destroy the discrimination — rejected (ADR D3).

### Resolve ladder (B, workflow.py:440-460) — final order

| # | Except (subclass-before-base) | Disposition | `error_type` | `recoverable` | Log event | Verified raise-site |
|---|-------------------------------|-------------|--------------|---------------|-----------|---------------------|
| 1 | `DataServiceUnavailableError` (existing L444) | `failed` | `resolve_unavailable` | `True` | `onboarding_walkthrough_resolve_unavailable` | data_service.py:377/383/397 |
| 2 | `DataServiceError` (NEW, base) | `failed` | `resolve_data_error` | `True` | `onboarding_walkthrough_resolve_data_error` | malformed body data_service.py:406 |
| 3 | `ValueError` (NEW) | `failed` | `resolve_invalid_input` | `False` | `onboarding_walkthrough_resolve_invalid` | `format_routing_address` routing.py:105 |

(No `DataServiceValidationError` leg in the resolve ladder — the phone leg has no 4xx raise-site, R-1. No dead legs.)

### Anchor ladder (C, workflow.py:490-538) — final order

| # | Except (GFR family FIRST, unchanged; then DataService subclass-before-base) | Disposition | `error_type`/reason | Log event | Verified raise-site |
|---|------------------------------------------------------------------------------|-------------|--------------------|-----------|---------------------|
| 1 | `GuardViolationError` (existing L497) | `skipped` | `guard_violation` (ERROR) | unchanged | engine.py:212 |
| 2 | `AmbiguousCardinalityError` (existing L512) | `skipped` | `ambiguous_anchor` (ERROR) | unchanged | engine.py:195 |
| 3 | `GfrError` (existing L525, base of GFR family) | `skipped` | `anchor_unresolved` (WARNING) | unchanged | engine.py:151/158 |
| 4 | `DataServiceUnavailableError` (NEW) | `failed` | `anchor_unavailable` (`True`) | `onboarding_walkthrough_anchor_unavailable` | data_service.py:736/741/770 |
| 5 | `DataServiceValidationError` (NEW) | `failed` | `anchor_invalid` (`False`) | `onboarding_walkthrough_anchor_invalid` | 4xx data_service.py:763 |
| 6 | `DataServiceError` (NEW, base) | `failed` | `anchor_data_error` (`True`) | `onboarding_walkthrough_anchor_data_error` | malformed body data_service.py:778 |

**Ordering correctness:** GFR family (1-3) and DataService family (4-6) are disjoint hierarchies (R-4), so inter-family order is free; the GFR subclass-before-base order is PRESERVED (AC-2c regression guard). Within DataService: subclasses (4,5) precede base (6). Auth family is caught by NEITHER family → terminal net (R2).

**Isolation + fail-closed (INV-1,2,3):** every widened leg returns a per-entity `failed` BridgeOutcome BEFORE FREEZE (no producer subprocess, no attach). The guard/compare logic (workflow.py:545-557) is untouched (INV-2). Symmetry with the resolve leg: the anchor DataService* path is `failed` (not `skipped`), so a real data/infra fault is alarmed and never mistaken for the benign no-identity-path `skip` (GfrError → `anchor_unresolved`, unchanged).

**NFR-4 (exactly-one-log):** a named leg logs at its own site AND returns → the fault never reaches the terminal net → no double-log. The terminal net logs ONLY residual/unanticipated escapes (incl. auth-family R2).

## §5 NFR-3 — PII discipline

- Named resolve legs log `office_phone=masked` (`mask_phone_number`, in scope at workflow.py:437); this is unchanged from the existing DSU leg.
- Named anchor legs log `task_gid=gid, error=str(exc)`; `DataServiceUnavailableError.__str__` renders `method=/error_category=/status_code=/retry_after=` (errors.py:475-482) — structurally PII-free (no phone/guid).
- Terminal net: `exc_info=exc` traceback renders frames + exception string, NOT locals → no phone/guid spilled from a local. `format_routing_address`'s `ValueError` message caps at 80 chars and `repr`s (routing.py:99-108).
- **Residual (bounded):** an UNANTICIPATED exception whose `str(exc)` embeds a raw phone/guid would pass through the terminal `message`. The mitigation is structural: FR-2 pulls the KNOWN phone/guid-bearing faults (resolve/anchor) into masked NAMED legs ahead of the terminal net; the net is only for classes we cannot field-mask by construction. A free-text guid/phone scrubber in the shared processor chain is a wider change — noted as a deferrable COULD, out of this arc's MUST scope.

## §6 FR-3 acceptance & the post-deploy receipt (SPECIFIED, not executed)

Local green unit suite is NOT acceptance (arc scar: local-green ≠ runtime-correct; R-3 proves `just invoke` is the exact local trap). The functional receipt is: the **deployed** Lambda re-invoked for `1213653428400851`, whose CloudWatch log now carries the FR-1 line naming the fault. Because the deployed image must carry the fix for that line to exist, AC-3d is inherently **post-deploy** and operator-executed. This arc terminates at swallow-closed + PR-surfaced.

## §7 Test Design

### AC-1 — `tests/unit/automation/workflows/test_bridge_base.py` (extend `_TestBridge` L29-49; capture via `structlog.testing.capture_logs()`)

| pytest node id | Asserts | RED-before / GREEN-after |
|----------------|---------|--------------------------|
| `TestBroadCatchObservability::test_broken_entity_logs_structured_error` | `_BrokenBridge.process_entity` raises `ValueError("boom")`; `execute_async([{"gid":"neu-life-fixture"}], {})` → `failed==1` **AND exactly one** `bridge_entity_failed` log with `task_gid=="neu-life-fixture"`, `error_type=="ValueError"`, an `exception` (traceback) field | **RED** on pre-fix (0 logs — reproduces 2026-07-01); **GREEN** on fixed (1 structured log) |
| `TestBroadCatchObservability::test_clean_entity_emits_no_error_log` | default `_TestBridge` (returns `succeeded`) → `succeeded==1` AND **zero** `bridge_entity_failed` logs | two-sided teeth (log fires ONLY on fault) |
| `TestBroadCatchObservability::test_skipped_entity_emits_no_error_log` | a `_SkipBridge` returning `skipped` → `skipped==1` AND **zero** `bridge_entity_failed` logs | two-sided teeth |

This is discriminating-canary **MODE 2** (genuine-gap production fix): the broken *input* (an entity whose `process_entity` raises) is fed to the REAL shared runner whose guard-absence (no logger) is genuine — NOT a defect injected into working code. The clean/skip inputs prove the log does not false-fire (two-sided).

### AC-2 — `tests/unit/automation/workflows/test_onboarding_walkthrough.py` (extend the DSU stub L558-569; factories `_make_resolver`, `_make_workflow`, `_entity`)

| pytest node id | Setup | Asserts |
|----------------|-------|---------|
| `test_resolve_valueerror_named_failed` (AC-2a) | `_make_resolver(raises=ValueError("bad guid"))` | `failed`, `error_type=="resolve_invalid_input"`, upload not called, and terminal `unexpected_error` did NOT fire (proves B widened) |
| `test_resolve_malformed_named_failed` (AC-2a sib) | `_make_resolver(raises=DataServiceError("malformed"))` | `failed`, `error_type=="resolve_data_error"` |
| `test_anchor_unavailable_named_failed` (AC-2b) | inject `company_id_anchor` (seam, workflow.py:116) with `side_effect=DataServiceUnavailableError(method="get_business_by_guid")` | `failed`, `error_type=="anchor_unavailable"`, not terminal |
| `test_anchor_invalid_named_failed` (AC-2b sib) | anchor `side_effect=DataServiceValidationError(method="get_business_by_guid", status_code=400)` | `failed`, `error_type=="anchor_invalid"` |
| `test_anchor_auth_reaches_terminal_named_R2` (AC-2b teeth) | anchor `side_effect=InvalidServiceKeyError()` | reaches terminal net → outcome `failed`/`unexpected_error`; the log line `error_type=="InvalidServiceKeyError"` (proves auth-family deliberately falls through data legs → R2 self-identifies) |
| `test_gfr_family_dispositions_unchanged` (AC-2c) | anchor raises each of `GuardViolationError`/`AmbiguousCardinalityError`/`GfrError`; plus `guid_anchor_mismatch` path | `skipped` with `guard_violation`/`ambiguous_anchor`/`anchor_unresolved`/`guid_anchor_mismatch` — UNCHANGED (regression guard on ladder ordering) |

(`_make_workflow` may need a one-line extension to pass `company_id_anchor` through — a test-file-local change, in scope.)

## §8 R1/R2 Post-Deploy Decision Tree (N5 HANDOFF artifact — NOT executed here)

Operator re-invokes the deployed Lambda for `1213653428400851`; read the now-emitted `error_type` (+ `message`/`error_category`/`status_code` in the traceback):

```
error_type (live log)
├── resolve_invalid_input | ValueError            → R1 (Neu-Life stored GUID non-canonical via format_routing_address)
├── resolve_data_error | anchor_data_error         → R1 (malformed data-service body, localized to Neu Life)
├── anchor_invalid | DataServiceValidationError    → R1 (4xx / INVALID_BUSINESS_GUID_FORMAT — data-shape)
│        ⇒ ALL R1 branches: FR-5 SHOULD — fix the Neu-Life data fault to root. Stay denom=1.
├── resolve_unavailable | anchor_unavailable | DataServiceUnavailableError   → AMBIGUOUS; disambiguate by message:
│        ├── error_category ∈ {SERVER_ERROR(5xx), TIMEOUT, TRANSPORT, CIRCUIT_OPEN}, isolated to Neu-Life & clears on retry → transient (re-invoke)
│        ├── error_category fleet-wide / persistent 5xx → R2-infra → ESCALATE sre/platform
│        └── status_code ∈ {401,403} → R2-auth
└── InvalidServiceKeyError | TokenAcquisitionError | ServiceUnavailableError | RetryExhaustedError | RateLimitedError
         (surfaces at the LOGGED terminal net — auth-family is NOT a DataServiceError, R-1)
         → R2 S2S-auth. CONTRADICTS P6 (insights_export succeeded:67 / 0 auth / 3d).
         → G-HALT the re-attach; ESCALATE sre/platform; re-examine P6.
```

P6 favors R1. The taxonomy makes the common cases self-discriminating on `error_type` alone; only the transient-`Unavailable` class needs `message`/`error_category`/`status_code`.

## §9 Invariants & Reversibility

| INV | Preserved by |
|-----|--------------|
| INV-1 customer-clean (fail-closed before FREEZE) | every widened leg returns `failed`/`skipped` before step 5; no producer subprocess |
| INV-2 fail-closed identity guard unchanged | anchor ladder widened for observability/naming only; guard/compare workflow.py:545-557 untouched |
| INV-3 per-entity isolation | terminal broad-catch retained (not narrowed); `asyncio.gather` L239 unchanged |
| INV-4 denominator = 1 | positive-necessity gate workflow.py:405-425 + `WALKTHROUGH_DECK_MAP` untouched (G-DENOM) |
| INV-5 #725 OPEN ⇒ broad rollout BLOCKED | no enable/rollout in scope |
| INV-6 never emails | leg list workflow.py:1-23 unchanged |

**Reversibility (all two-way doors):** FR-1 is additive (one log call; revert = delete). FR-2 adds except legs + named `error_type` strings (revert = remove legs; the fault reverts to the now-logged terminal net). No schema, API contract, or infra change; `WorkflowItemError.error_type="unexpected_error"` terminal contract UNCHANGED (ADR D5). No one-way doors ⇒ no stakeholder sign-off gate.

## §10 Risks

| Risk | Mitigation |
|------|------------|
| A widened `error_type` string is consumed by an unknown downstream matcher | new strings are ADDITIVE named values; the terminal `unexpected_error` contract is unchanged (ADR D5); FR-6 enrichment DEFERRED |
| `str(exc)` free-text PII on an unanticipated class at the terminal net | FR-2 pulls known phone/guid faults into masked named legs ahead of the net; traceback renders no locals (§5) |
| A DataService sibling not enumerated (e.g. `BusinessNotFoundError` in a future anchor path) | caught by the `DataServiceError` base leg (6) → `anchor_data_error` (named, not swallowed) — base leg is the safety net within the data family |
| Test log-capture idiom mismatch | `structlog.testing.capture_logs()` (suite already imports `structlog`); config-independent |
