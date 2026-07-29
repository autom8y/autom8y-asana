---
type: review
artifact_id: FEASIBILITY-substrate-v2-seams-s1
title: "Substrate-v2 — feasibility read + hardened frozen-seam build contracts (S1 Phase-2)"
created_at: "2026-07-28T00:00:00Z"
author: principal-engineer
rite: 10x-dev
initiative: substrate-v2-epoch
sprint: S1
phase: "Phase-2 (parallel to arch-adversary; feasibility + seam-hardening, NOT build)"
status: proposed
prod_touch: NONE
evidence_grade: MODERATE
evidence_grade_rationale: >
  Self-authored feasibility read within the 10x-dev corridor; caps at MODERATE per
  self-ref-evidence-grade-rule. Grounding claims are file-read/bash-probe verified
  at HEAD b9438e83 this session (§0 ledger). STRONG is the rite-disjoint arch-adversary
  concurrence (running in parallel) + eunomia attestation at epoch exit.
consumes:
  - .ledge/specs/TDD-substrate-v2.md
  - .ledge/decisions/ADR-substrate-v2-fork-register.md
  - .ledge/specs/RC-acceptance-predicates-substrate-v2.md
feeds:
  - phase-3-reconciliation (architect TDD finalize + DP-2/DP-3 packets)
  - PT-01 seams-frozen gate (Potnia)
  - S2-S7 dark build (the 5 seam contracts are the build target)
related_artifacts:
  - CHARTER-substrate-v2-epoch-2026-07-27
  - DEFECT-seam1-entity-blind-prober-plane-split-2026-07-27
---

# Feasibility + hardened frozen-seam build contracts — Substrate-v2 (S1 Phase-2)

> **Role.** Principal-engineer, running in PARALLEL with the arch-adversary. Charge:
> (1) is the whole design buildable-as-drawn — any hard infeasibility that co-triggers
> an architect re-enter? (2) harden the 5 frozen seams into contracts precise enough that
> five independent builders cannot diverge. (3) make refuse-loud unbypassable across ALL
> consumer paths including the cross-process MCP boundary. Fence: this one file. prod_touch NONE.

## 0. Bottom line + grounding ledger

**Bottom line: the whole design is BUILDABLE-AS-DRAWN. NO hard infeasibility is found — nothing
in Python's type system or runtime makes a module or seam impossible-as-drawn.** The architect's
honest floor for "impossible-by-construction" (deleted capability + mypy-strict + construction
guard) is *reachable* for both operator-named pressure tests (RC-C typed key, RC-E no-write
reader) — I confirmed the substrate exists (§2). Seven items are **BUILDABLE-WITH-CAVEAT**: each
is a build-contract precision the seam must freeze so S2-S7 don't diverge, not a design defect.
One load-bearing **cross-service collision** (a ratified `stale-served-on-200` ADR vs RC-B's
refuse-past-SLA) is real, grounded in shipped code, and routes to the **existing DP-3 door** — it
is not a new fork (§4). Legibility check **PASSES**: 6 modules / 5 seams / 2 pure-core types / one
inward arrow is small enough for one engineer to hold; the only two places where "small" hides
real complexity are named (digest canonicalization, observe completeness).

**Grounding ledger (SVR — file-read/bash-probe at HEAD `b9438e83`, this session):**

| # | Claim (load-bearing for a verdict) | Method | Receipt | Status |
|---|-----------------------------------|--------|---------|--------|
| G1 | `EntityType` is a real closed `Enum` — RC-C can bind a typed key to it | file-read | `core/types.py:13` `class EntityType(Enum)`; members BUSINESS…OFFER…`UNKNOWN = "unknown"` at :69 | VERIFIED |
| G2 | mypy `strict = true` is repo-wide; all `ignore_errors` removed — the RC-C/RC-E "mypy tooth" needs zero config, `substrate/` inherits it | file-read | `pyproject.toml:144` `strict = true`; :205 "All ignore_errors overrides removed — mypy strict enforced on all modules" | VERIFIED |
| G3 | runtime floor is 3.12 — the drawn `type ServedNumber = Provable \| Refused` (PEP 695 alias stmt) is valid syntax; no infeasibility | file-read | `pyproject.toml:10` `requires-python = ">=3.12"`; :143 `python_version = "3.12"` | VERIFIED |
| G4 | `frozen=True` + `__post_init__` is idiomatic here; `ArtifactId`/`FreshnessProof` are consistent-with-conventions | bash-probe | `frozen=True` at `core/entity_registry.py:95` (`slots=True`), `core/retry.py:84/103/120`, `core/connections.py:39` | VERIFIED |
| G5 | v1's plane-blind hole is live: every `StorageBackend` key-builder takes `entity_type: str \| None = None`; `legacy_fallback_enabled: bool = True` | file-read | `dataframes/storage.py` signatures at :91/:117/:128/:405/:414; `legacy_fallback_enabled: bool = True` at :352 | VERIFIED |
| G6 | The paced-fetch primitive (RC-E-4) EXISTS — the rebuilder delegates, does not re-implement | bash-probe | `transport/budget_allocator.py`, `transport/adaptive_semaphore.py`, `clients/data/_endpoints/_pacer.py`, `core/concurrency.py`, `core/retry.py` all present | VERIFIED |
| G7 | A rebuild coalescer EXISTS (RK7 single-flight is grounded) | bash-probe | `settings.py:223/:265` `df_coalescer_max_wait` + "503 CACHE_BUILD_IN_PROGRESS" coalesced-wait knob | VERIFIED |
| G8 | The CloudWatch EMF emit primitive (RC-F) EXISTS — observe reuses it | file-read | `metrics/cloudwatch_emit.py:120` `emit_freshness_probe_metrics` → `:217` `cw_client.put_metric_data` | VERIFIED |
| G9 | The HTTP refuse envelope EXISTS — `Refused` maps onto it; loud-refuse-over-HTTP is already shipped | file-read | `api/errors.py:92` `raise_api_error(request_id, status_code, code, message, details, headers)` → `HTTPException(ErrorResponse)`; query route `:504` `raise_api_error(…, 503, "CACHE_NOT_WARMED", …)`, `:492` "NEVER a 500, NEVER a silent empty-200" | VERIFIED |
| G10 | The cross-process consumer ALREADY raises on every non-2xx — a non-2xx `Refused` is unbypassable across the wire | file-read | `mcp/asana_mcp/tools/_common.py:63-64` `if resp.status_code != 200: raise map_http_error(resp)`; `mcp/asana_mcp/errors.py:145` classifies 503/401/429/404/4xx | VERIFIED |
| G11 | **COLLISION**: a ratified ADR serves STALE data on a **200** with a `stale_served=true` flag (SWR/LKG) — the exact "confidence-labelled stale number" RC-B forbids | file-read | `query/models.py:249` + `:428` "ADR-serve-stale-within-bound (2026-06-03) … served stale-within-bound (APPROACHING_STALE+SWR or STALE+LKG)"; `stale_served: bool` fields at :253/:436 | VERIFIED |
| G12 | A consumer passes a bare `str` entity to the read path today — a real str→EntityType coercion boundary the guard must close | file-read | `api/routes/matching.py:145` `cache.get_async(project_gid, "business")`; `api/routes/query.py:336` `entity_type: str` (URL param) | VERIFIED |
| G13 | Raw `load_dataframe` importers are all v1 write/warm/preload paths (deleted at S11), NOT consumer read paths — the serving chokepoint privacy boundary is cleanly separable | bash-probe | direct importers: `cache/dataframe/tiers/progressive.py`, `dataframes/{storage,section_persistence,builders/progressive}.py`, `api/preload/{progressive,legacy}.py` — none are query/matching/offline serve | VERIFIED |

---

## 1. Feasibility verdict — per module and per seam

| Unit | RC | Verdict | Basis |
|------|----|---------|-------|
| `substrate.identity` (`ArtifactId`) | RC-C | **BUILDABLE-WITH-CAVEAT** | `EntityType` real enum (G1) + frozen-dc idiom (G4). Caveat C1: `EntityType.UNKNOWN` is typed-world plane-blindness — the type is necessary, not sufficient; guard must reject it (§2, §3-Seam-2). |
| `substrate.freshness` (`FreshnessProof`, `is_provable`) | RC-B | **BUILDABLE-WITH-CAVEAT** | Frozen dc + pure fn, trivially feasible. Caveat C2: `content_digest` reproducibility (RK2) — the canonicalization MUST be frozen at the seam, not emergent per builder (§3-Seam-1). Highest 5-builder-divergence risk in the design. |
| `substrate.store` (`ArtifactStore`) | RC-A, RC-E | **BUILDABLE** | S3 single-object-PUT atomicity for the tiny `current.json` pointer is genuine; large immutable `v{N}/frame` is written before the flip, so its multipart non-atomicity is irrelevant. Contract hardening only (§3-Seam-2). |
| `substrate.rebuild` (`Rebuilder`) | RC-E | **BUILDABLE** | Stage-validate-swap standard; paced primitive (G6) and coalescer (G7) both exist to delegate to. Capability-typed reader is honest-floor (RK3), reachable (§2). |
| `substrate.serve` (`SubstrateReader`, `ServedNumber`) | RC-C(serve), P2 | **BUILDABLE-WITH-CAVEAT** | In-process sum-type gate feasible (`type` stmt valid on 3.12, G3). Caveat C3: exhaustiveness is honest-floor (Python won't force it at runtime) — needs `assert_never`, which is **net-new** to this codebase (grep: zero uses). Caveat C4: cross-process boundary + the G11 collision (§4). |
| `substrate.observe` (`ProvabilityEvaluator`) | RC-F | **BUILDABLE-WITH-CAVEAT** | EMF emit exists (G8), scheduled evaluator standard. Caveat C5: a partial run that emits a heartbeat but silently skips the broken artifact still reads green — the seam must add a **completeness** metric, not just a heartbeat (§3-Seam-5). This is the ADR's own F6 adversary target, unresolved in the draft. |
| Seam 1 FRESHNESS | RC-B | **BUILDABLE-WITH-CAVEAT** | C2 (digest canonicalization freeze). |
| Seam 2 STORAGE+KEYS | RC-A/E | **BUILDABLE-WITH-CAVEAT** | C1 (UNKNOWN guard) + `read_current` raises-not-`(None,None)` is a hard v1 break to name. |
| Seam 3 REBUILD | RC-E | **BUILDABLE** | Reader/Rebuilder type-separation is the frozen invariant; both delegates exist. |
| Seam 4 SERVING | RC-C/P2 | **BUILDABLE-WITH-CAVEAT** | C3 (assert_never) + C4 (cross-process, §4). |
| Seam 5 OBSERVABILITY | RC-F | **BUILDABLE-WITH-CAVEAT** | C5 (completeness ≠ heartbeat). |

**No unit is INFEASIBLE-AS-DRAWN.** See §5 for the hard-infeasibility check that co-triggers a re-enter — it fires NEGATIVE.

---

## 2. The two operator-named pressure tests (is the honest floor reachable?)

The architect conceded "impossible-by-construction" in Python = deleted capability + mypy-strict +
construction guard, not compile-absolute. Pressure test: is that floor actually reachable?

**RC-C — typed `entity_type` key. REACHABLE, with one named hole to close.**
- Tooth 1 (deleted None branch): buildable — `ArtifactId.entity_type: EntityType` with no default. `EntityType` is a real enum (G1). A writer with `grep -c entity_type == 0` cannot construct an `ArtifactId` — there is no entity-agnostic constructor to fall through to, unlike v1's `str | None = None` (G5).
- Tooth 2 (mypy-strict): **zero-config reachable** — `strict = true` is already repo-wide and `substrate/` inherits it (G2). Passing a bare `str` or `None` where `EntityType` is required is a mypy error today.
- Tooth 3 (construction guard): buildable — `__post_init__` is idiomatic (G4).
- **HOLE (Caveat C1):** the typed key does NOT prevent `ArtifactId(gid, EntityType.UNKNOWN)`. `UNKNOWN` (and arguably the structural `PROJECT`/`SECTION` members) is the typed-world equivalent of v1's plane-blind `None`. mypy is satisfied by any `EntityType`; only the runtime guard closes it. **The guard's content must be frozen at the seam**: reject `UNKNOWN` and any non-servable member. There is also a live str→EntityType coercion boundary (G12: `matching.py` passes `"business"`, the MCP route takes `entity_type: str`) — that boundary must coerce-or-refuse (unknown string → `Refused`/reject, never silent-legacy). This is a precise hardening, **not** an infeasibility.

**RC-E — reader has no write method. REACHABLE at the stated floor.**
- The construction is two DISTINCT types: `SubstrateReader` (has `read`, no `put`) and `Rebuilder` (writes staging only, no serve-read). A consumer typed against `SubstrateReader` cannot call `.put()` — mypy: "no attribute". At runtime, if the concrete reader object simply has no write method, the P4 counterexample (a "read-only recompute" that persists) is unconstructable through the reader.
- Honest-floor is exactly as the ADR states: deleted method + mypy-strict + type-separation. Python cannot make it compile-absolute (a caller with the concrete `Rebuilder` in hand could still write) — but the *serve* capability handed to consumers has no write surface. **Reachable.** The one net-new-to-this-repo pattern is `assert_never`-based exhaustiveness on `ServedNumber` (Caveat C3) — standard `typing`, zero grep hits today, so name it in the contract.

**Verdict: both floors reachable. Neither is a hard infeasibility. No re-enter triggered by feasibility.**

---

## 3. The five hardened frozen-seam interface contracts (the S2-S7 build target)

Each contract = the architect's drawn signature (kept) + the **hardening delta** a builder needs so
five builders converge. The signature vocabulary is frozen; a DP ruling changes a *shape*, not these
contracts. Deltas are marked **[H-n]**.

### Seam 1 — FRESHNESS (`substrate.freshness`, pure core) — RC-B

```python
@dataclass(frozen=True, slots=True)
class FreshnessProof:
    built_from_live_at: datetime   # tz-aware UTC; advanced ONLY by a content-bearing rebuild
    content_digest: str            # sha256 hex over the CANONICAL form below — never GIDs, never parquet bytes
    sla_seconds: int               # freshness contract for this (project, entity) class; sourced from the entity registry

class Provability(Enum):          # CLOSED — no builder adds a member
    PROVABLE = "provable"
    STALE = "stale"
    CORRUPT = "corrupt"

def is_provable(proof: FreshnessProof, served_bytes_digest: str, now: datetime) -> Provability:
    """PROVABLE iff (now - built_from_live_at) <= sla_seconds AND served_bytes_digest == content_digest.
    Else STALE (age) or CORRUPT (digest mismatch). Pure; deterministic in its 3 args; no I/O, no now()."""
```

- **[H1] Digest canonicalization is FROZEN in this module, not emergent (closes RK2/C2 — the top divergence risk).** Pin all five: (a) **column set** = the declared value-columns resolved from the entity registry (NOT an ad-hoc per-builder list; UV-P at S2 confirms the offer set mrr/offer_id/cost/weekly_ad_spend against prod); (b) **row order** = ascending sort on a declared `row_key`; (c) **serialization** = a parquet-INDEPENDENT canonical encoding (e.g. UTF-8 JSON of sorted-key records) — explicitly NOT `df.write_parquet()` bytes (they embed non-deterministic compression/metadata); (d) **null** = one pinned sentinel; (e) **float** = one pinned format (fixed precision, not `repr`). Ship a `canonical_digest(df) -> str` helper in this module; every producer/consumer of a digest calls it. Freeze with a same-bytes-twice reproducibility test at S2 before the digest domain locks.
- **[H2] tz invariant:** `__post_init__` rejects naive `built_from_live_at`; `is_provable` rejects naive `now`. Monotonic decay only holds in UTC. (The repo already raises on naive watermarks in `save_dataframe` — carry that discipline.)
- **[H3]** `Provability` is a CLOSED enum shared verbatim with Seam 5 (RC-F depends on ONE predicate). `is_provable` is the SOLE freshness definition — no parallel staleness check anywhere.
- **Frozen invariant:** only a content-bearing rebuild constructs a new `FreshnessProof`; no probe mutates one; `is_provable` is consumed identically by serving (Seam 4) and observability (Seam 5).

### Seam 2 — STORAGE+KEYS (`substrate.identity` + `substrate.store`, core type + infra) — RC-A/RC-E

```python
@dataclass(frozen=True, slots=True)
class ArtifactId:
    project_gid: str
    entity_type: EntityType        # REQUIRED — no default, no None
    def __post_init__(self) -> None:
        # [H4] guard content is FROZEN: non-empty project_gid; entity_type is a SERVABLE member.
        if not self.project_gid: raise ValueError("empty project_gid")
        if self.entity_type in _NON_SERVABLE:  # {UNKNOWN, …} — closes the typed-world plane-blind hole (C1)
            raise ValueError(f"non-servable entity_type: {self.entity_type}")

def artifact_key(aid: ArtifactId) -> str:      # pure; the ONLY key-builder; no None branch, no legacy segment
    return f"dataframes-v2/{aid.project_gid}/{aid.entity_type.value}"

class ArtifactStore(Protocol):
    async def read_current(self, aid: ArtifactId) -> tuple[bytes, FreshnessProof]: ...
    async def stage_version(self, aid: ArtifactId, frame_bytes: bytes, proof: FreshnessProof) -> VersionId: ...
    async def swap_pointer(self, aid: ArtifactId, to: VersionId) -> None: ...
    async def list_versions(self, aid: ArtifactId) -> list[VersionId]: ...
    async def gc_versions(self, aid: ArtifactId, keep_after: datetime) -> int: ...
```

- **[H4] guard closes C1** (above): the servable-set is data-driven from the registry; `_NON_SERVABLE` at minimum contains `EntityType.UNKNOWN`. The str→EntityType coercion for HTTP/CLI boundaries (G12) lives in the Seam-4 adapters and MUST refuse an unknown string, never coerce to legacy.
- **[H5] `read_current` postcondition is a HARD v1 break — name it loudly:** resolves `current.json` → named immutable version in ONE logical read and returns `(bytes, proof)`, or **raises `ArtifactMissing`** on an absent pointer OR absent named object. It does **not** return `(None, None)` (contrast v1 `load_dataframe -> (None, None)`, G5). An absent authority is loud (RC-A backstop). Every S2-S7 builder must code against raise-not-None.
- **[H6] `swap_pointer` is the ONLY writer of `current.json`**, a single-object PUT, and carries a **version-monotonicity check** (reject a swap to a version older than current unless invoked through an explicit rollback capability). This is the RK7 concurrency tooth (two rebuilders racing the pointer → last-writer-wins with monotonicity, not silent clobber).
- **[H7] `stage_version` NEVER touches `current.json`** and never overwrites a pointed-to version (immutability). `gc_versions` never deletes current or current-1 and only reaps age > SLA+grace (RK4 reader-holding-GC'd-version).
- **[H8] the store is POLICY-FREE** — it returns bytes+proof and does not apply the SLA/refuse gate (that is Seam 4; this is the F5-3 rejection made structural, and it preserves the rebuilder + parity-harness raw-read need).
- **Frozen invariant:** `entity_type` required and typed; exactly one key-builder with no legacy path; `stage_version` never mutates the live pointer; `swap_pointer` is the sole, atomic, monotonic mutation of `current.json`; reads resolve current → named immutable version or raise.

### Seam 3 — REBUILD (`substrate.rebuild`, infra) — RC-E

```python
class RebuildOutcome(Enum):  # CLOSED
    SWAPPED = "swapped"; STAGED_REJECTED = "staged_rejected"; FETCH_REFUSED = "fetch_refused"

class Rebuilder(Protocol):
    async def rebuild(self, aid: ArtifactId, fetch: PacedAsanaFetcher,
                      validate: AcceptancePredicates) -> RebuildResult: ...
    # steps, ORDERED, swap LAST: fetch(paced) -> digest+proof -> stage_version -> validate(staged) -> swap|discard
```

- **[H9] capability separation is THE frozen invariant** (makes RC-E structural): `Rebuilder` and `SubstrateReader` are DISTINCT types; `Rebuilder` exposes no serve-read, `SubstrateReader` exposes no write. They are never the same object. The P4/RC-E-2 counterexample becomes a passing test because the serve capability has no `put`.
- **[H10] swap is LAST and conditional:** validate runs on the STAGED bytes; `swap_pointer` fires ONLY on PASS; on FAIL discard staging, live pointer untouched (partial ≠ corrupt, RC-E-1). A builder must never swap-then-validate.
- **[H11] paced-fetch delegation is MANDATORY:** all live Asana I/O routes the injected `PacedAsanaFetcher` (G6 — the AIMD/budget/semaphore primitive exists); the rebuilder constructs no direct `AsanaClient`, has no un-paced path (RC-E-4).
- **[H12] single-flight per ArtifactId (RK7):** one in-flight rebuild per `aid`, coalescing concurrent requests via the existing coalescer (G7).
- **[H13] minimum validation set** `AcceptancePredicates` runs pre-swap: population floor + digest self-consistency (staged bytes hash to the new proof) + proof well-formedness. Freeze the floor so a builder can't swap an unvalidated version.
- **Frozen invariant:** writes are staging-only until one atomic, monotonic swap after validation; all live fetches route the paced primitive; a failed rebuild cannot corrupt the live artifact.

### Seam 4 — SERVING (`substrate.serve`, core policy + thin per-consumer adapters) — RC-C(serve)/P2

```python
@dataclass(frozen=True, slots=True)
class Provable:  frame: bytes; proof: FreshnessProof
@dataclass(frozen=True, slots=True)
class Refused:   reason: RefuseReason; detail: RefusePayload   # RefuseReason CLOSED: {STALE, CORRUPT, MISSING, DIVERGENT}

type ServedNumber = Provable | Refused      # PEP 695 alias — valid on 3.12 (G3)

class SubstrateReader(Protocol):
    async def read(self, aid: ArtifactId) -> ServedNumber: ...
    # postcondition: read_current -> is_provable(proof, canonical_digest(bytes), now) -> Provable | Refused; NEVER a bare value
```

- **[H14] sum-member payloads are FROZEN** so the CLI, HTTP, and MCP adapters serialize identical fields. `RefuseReason` is a CLOSED enum {STALE, CORRUPT, MISSING, DIVERGENT}. `RefusePayload` carries the RC-A-2 explanation schema (which artifact, absolute age, magnitude, per-section delta — the acceptance doc's OQ-1 observable). Freeze the payload; the wire *format* is DP-3, the *fields* are the seam.
- **[H15] exhaustiveness tooth (C3, net-new pattern):** every `ServedNumber` consumer matches both arms with `typing.assert_never` in the default; a bare attribute access on `ServedNumber` is a mypy error. Zero `assert_never` uses exist today — the contract mandates it as the RC-C-serving honest floor. Python does not force runtime exhaustiveness, so this + mypy-strict is the "bare value unobtainable" floor.
- **[H16] the gate lives INSIDE `read`** — not in the store (H8), not in the caller. `read` resolves `store.read_current`, computes `canonical_digest` (Seam-1 [H1]) of the served bytes, applies `is_provable`, and returns `Refused(STALE|CORRUPT)` on failure — never `Provable` for an unprovable number.
- **[H17] raw-read privacy is enforceable and bounded (G13):** `store.read_current` / any `load_dataframe` are module-private to `substrate.{serve,rebuild}`; an import-layer mypy/lint tooth forbids importing them elsewhere. The blast radius is known — today's raw `load_dataframe` importers are all v1 write/warm/preload paths that delete at S11, none are consumer serve paths. The rebuilder + parity harness reach raw bytes via a DISTINCT non-serving capability.
- **[H18] adapters are THIN:** per-consumer adapters (CLI, service route, MCP route, matching, force-warm) translate `ServedNumber` to their surface and contain NO freshness logic. (§4 specifies each.)
- **Frozen invariant:** exactly one public read path; it returns `Provable | Refused`; a bare value is unobtainable without handling `Refused`; raw bytes are reachable only by rebuilder + parity harness via a distinct non-serving capability.

### Seam 5 — OBSERVABILITY (`substrate.observe`, infra) — RC-F

```python
class ProvabilityEvaluator(Protocol):
    async def evaluate_all(self, expected: Set[ArtifactId], now: datetime) -> EvaluationRun: ...
    # per-aid: read_current + is_provable -> emit provable=1/0; ArtifactMissing -> provable=0 (never silence)
    # run-level: emit heartbeat(run_count) AND evaluated_count; caller/alarm compares evaluated_count vs len(expected)
```

- **[H19] shared-predicate invariant:** `evaluate_all` imports and calls the SAME `is_provable` + `Provability` (Seam-1 [H3]) that Seam-4 serving calls. No parallel staleness re-implementation — this is the mechanical basis of "cannot read green while serving refuses."
- **[H20] completeness ≠ heartbeat (closes C5 — the ADR's own unresolved F6 adversary target):** the heartbeat (`run_count`) proves the evaluator RAN; it does NOT prove it COVERED every artifact. A partial run that emits a heartbeat but skips the broken artifact reads green. Freeze a **completeness** signal: `evaluate_all` takes the EXPECTED warmed set (sourced from the warm-target registry) and emits `evaluated_count`; `evaluated_count < len(expected)` is itself a firing condition. Absence-of-emission for a skipped artifact must not read as absence-of-problem.
- **[H21] absence = alarm:** `ArtifactMissing` emits `provable=0`, never silence (RC-F absence-fires).
- **[H22] query-independence:** `evaluate_all` is scheduled (EventBridge→Lambda or warmer post-step) and is NEVER called from `read`. Freeze: no serve path invokes the evaluator.
- **[H23] emission reuses `cloudwatch_emit` EMF/`put_metric_data`** (G8). The terraform alarm-provisioning limb is the EXISTING Door #4 — out of this seam's CODE scope; the seam owns the emission contract only.
- **Frozen invariant:** provability is evaluated on a schedule independent of serve and warm; it consumes the identical `is_provable`; absence of proof fires; incompleteness fires; the evaluator's own silence fires (heartbeat + CloudWatch native no-data).

---

## 4. The consumer-exhaustive serving-seam CROSS-PROCESS refuse contract (RK5 / DP-3)

The mission's "loudly refused" is the load-bearing word, and refuse-loud has two altitudes with
**different enforcement mechanics**. This is where the design is hardest and where I add the most.

### 4a. In-process: refuse-loud is a TYPE property (RC-C-3, new-consumer test)

A new (6th) consumer that wants a number has exactly one path, and three teeth block every bypass:
1. It must import `SubstrateReader` — the only exported serve symbol. Raw `read_current`/`load_dataframe` are module-private with an import-layer tooth ([H17], bounded by G13).
2. It must build an `ArtifactId` — cannot be plane-blind (Seam-2 [H4] guard; no `str | None` path exists).
3. It must handle `ServedNumber` — `assert_never` + mypy-strict make a bare value unobtainable ([H15]).

There is no plane-blind API and no gate-blind API to forget. RC-C-3 ("a brand-new consumer cannot
compile a plane-blind call") passes by construction, not by a maintained call-site inventory — which
is precisely the layer v1's `test_seam1_callsite_inventory.py` missed (the persistence-wrapper
surface CP-6).

### 4b. Cross-process (MCP/delegated-fleet): bytes over HTTP are not an in-process exception

The honest boundary (architect's RK5, correctly named): across the wire, `Refused` is just bytes — a
remote caller CAN ignore an envelope it chooses to. So "Refused" must be a TRANSPORT signal the
consumer cannot read as success. **This is buildable on rails that already ship** (G9, G10):

- **Server side:** the MCP route's adapter maps `Refused` → `raise_api_error(request_id, <non-2xx>, code, message, details=<RefusePayload>)` (G9). The **FROZEN invariant is: every `Refused` is a non-2xx with a machine-readable `code`; NO `Refused` is a 200.** The specific reason→status *table* is a DP-3 payload; the non-2xx *class* is the seam.
- **Consumer side (already unbypassable, G10):** the MCP island's `post_json`/`get_json` do `if resp.status_code != 200: raise map_http_error(resp)`. A non-2xx `Refused` is RAISED as `McpToolError` in the remote process — it CANNOT be treated as an empty-200. This is the grounding that makes cross-process refuse-loud real rather than aspirational.

### 4c. The load-bearing COLLISION the DP-3 packet MUST carry (G11)

A ratified `ADR-serve-stale-within-bound (2026-06-03)` serves STALE data on a **200** with
`stale_served=true` (SWR + LKG), surfaced as an honesty flag (`query/models.py:249/:428`, and the MCP
island lifts it to the tool top-level via `shape_execution_result`). **That 200-with-a-flag IS the
"confidence-labelled stale number" RC-B and the acceptance doc explicitly forbid** (RC-acceptance
:105 "never a confidence-labelled stale number"). Substrate-v2's serving seam RETIRES the
stale-served-200 path: STALE becomes a non-2xx `Refused`. That is a behavioral change to live
consumers who today rely on SWR/LKG *availability* — i.e. it IS the DP-3 one-way door (cross-service
consumer contract). Two concrete sub-decisions the DP-3 packet must rule on (I do NOT pre-answer them
— door):
- **Status partition + SLI accounting (grounded subtlety):** the query route's receiver SLI counts 5xx as `server_error` but **does NOT count 4xx** ("4xx are NOT counted (client error, not receiver health)", route body). So STALE→**409** would HIDE substrate-staleness from the receiver health metric (re-creating a query-gated blind spot), while STALE→**503-class** makes the SLI and RC-F both see unprovability as a health signal. **My recommendation to the DP-3 packet: STALE/CORRUPT/DIVERGENT map to a 5xx-class refuse, not 4xx** — so substrate-unprovability is visible to receiver health, consistent with RC-F. (Recommendation, not ruling.)
- **Consumer-side reason surfacing:** `map_http_error` today has no branch meaning "stale, needs rebuild, not-your-fault, don't hot-retry" (503→retryable-warming, 409→generic-client). The envelope already carries a distinct `code` (G9); the DP-3 packet should extend the consumer's `shape_execution_result`/`map_http_error` to surface `refused: {reason}` as a distinct top-level signal (replacing `stale_served`), so the remote LLM reads a refusal, not a warming-retry. Net-work on BOTH sides of the boundary — buildable, named.

### 4d. Consumer-path exhaustive map (every CP-1..6 + force-warm forced through the chokepoint)

| Path (acceptance CP + anchor) | Today (grounded) | v2 adapter — how Refused is made unbypassable |
|---|---|---|
| CP-1 offline/CLI (`metrics/__main__.py`→`offline`) | `PlaneDivergenceError` caught only here (P5) | adapter maps `Refused` → non-zero `DATA-INTEGRITY` exit (RC-acceptance :104); generalizes the existing one-path guard to ALL reasons via `SubstrateReader` |
| CP-2 force-warm recheck (`from_s3_resolved`, `__main__.py:476/:883`) | mtime-based "fresh" (P7); comment admits "stale legacy reading" | recheck resolves via `is_provable` ([H16]), NOT mtime; a non-provable recheck refuses |
| CP-3/4 MCP `query_rows`/`query_aggregate` (`api/routes/query.py:334/:573`) | `entity_type: str` URL param; 503 refuse exists but 200-stale-served also exists (G11) | route adapter: str→EntityType coerce-or-refuse ([H4]); `Refused`→`raise_api_error` non-2xx (§4b); retire the 200-stale path (§4c) |
| CP-5 shared `DataFrameCache.get_async` (`:242`; matching passes `"business"`, G12) | plane-blind cache key possible | `SubstrateReader` wraps the memory→S3 tier; the cache key is derived from `ArtifactId` ([H4]), never a bare str |
| CP-6 persistence-wrapper surface (the layer v1's inventory MISSED) | `write/read_section_async` default to legacy on omit | subtracted with v1; no `entity_type: str \| None` surface exists in `substrate/` |
| matching (`api/routes/matching.py:145`) | `cache.get_async(project_gid, "business")` bare str | same as CP-3/5: routed through `SubstrateReader`, `ArtifactId(gid, EntityType.BUSINESS)` |

---

## 5. Hard-infeasibility check — the co-equal re-enter trigger (fires NEGATIVE)

The charge: a hard infeasibility (a Python/type/runtime constraint making a construction
impossible-as-drawn) is a co-equal trigger with adversary dissent for a bounded architect re-enter.
**I find NONE.** I pressure-tested the candidates and cleared each:

| Candidate hard-infeasibility | Cleared because |
|---|---|
| RC-C typed key can't be enforced in dynamic Python | `EntityType` enum (G1) + repo-wide mypy-strict (G2) + frozen-dc guard (G4) make the stated 3-tooth floor reachable; the only gap (`UNKNOWN`) is closed by guard content [H4], not a language limit. |
| RC-E "reader has no write method" is aspirational | type-separation ([H9]) + deleted method + mypy-strict is a real floor; the serve capability handed to consumers has no write surface. Honest-floor, reachable. |
| `type ServedNumber = …` (PEP 695) not available | `requires-python = ">=3.12"` (G3) — valid syntax at the runtime floor. |
| Cross-process `Refused` can't survive the wire (RK5) | non-2xx envelope (G9) + consumer raises on every non-200 (G10) — unbypassable on rails that already ship. |
| Digest non-reproducible (RK2) | not an infeasibility — a canonicalization the seam FREEZES ([H1]) + a same-bytes-twice test at S2. |

**Feasibility does NOT co-trigger a re-enter.** The adversary's dissent (parallel track) is the other
potential trigger; this file speaks only to feasibility.

### What I route UP to the architect/operator (NOT re-enter triggers — "know before you freeze")

1. **The G11 collision** (§4c): the serving seam's `Refused(STALE)` retires the ratified
   `ADR-serve-stale-within-bound` 200-stale path. This is a DP-3 payload (existing door, no new fork),
   but the architect should freeze the seam knowing STALE→non-2xx is a live-consumer contract change
   with an SLI-accounting consequence and a recommended 5xx-class mapping.
2. **Observe completeness (C5 / [H20])**: the draft's F6 leaves the "partial run emits a heartbeat but
   skips the broken artifact" hole open (its own adversary target). The seam must carry a completeness
   metric, not just a heartbeat. Folded into the Seam-5 contract; flagged so it isn't lost.
3. **Digest canonicalization (C2 / [H1])** and **`read_current` raises-not-`(None,None)` (H5)** are the
   two build-contract details most likely to cause 5-builder divergence if left emergent. Freeze them
   explicitly in the finalized TDD §4.

---

## 6. Legibility check (hold the whole design — one engineer?)

**PASS.** 6 modules, 5 seams, 2 pure-core types (`ArtifactId`, `FreshnessProof`), one inward
dependency arrow, one read choke-point, one freshness predicate consumed by both serving and
observability. That is holdable. The design's "small" is honest EXCEPT at two loci where real
complexity hides and must be frozen so it doesn't silently bloat: **digest canonicalization** ([H1])
and **observe completeness** ([H20]). Both are named above. No gold-plating added (P7): I did not
design forks, did not pre-answer DP-2/DP-3 (I hardened invariants and routed the collision to the
existing door), and did not expand the module count.

---

## Attestation

| Artifact | Absolute path | Verified |
|----------|---------------|----------|
| This feasibility + seam-hardening review | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/reviews/FEASIBILITY-substrate-v2-seams-s1.md` | YES (Read-back) |
| Consumed — TDD | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/specs/TDD-substrate-v2.md` | read fresh |
| Consumed — fork register ADR | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/decisions/ADR-substrate-v2-fork-register.md` | read fresh |
| Consumed — RC acceptance predicates | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/specs/RC-acceptance-predicates-substrate-v2.md` | read fresh |

**Verdict:** whole design BUILDABLE-AS-DRAWN; 7 BUILDABLE-WITH-CAVEAT hardenings folded into the 5
seam contracts; 0 INFEASIBLE-AS-DRAWN; NO feasibility-triggered architect re-enter. Evidence grade
MODERATE (self-authored corridor; grounding receipts §0 verified at HEAD `b9438e83`; STRONG is the
rite-disjoint arch-adversary concurrence + eunomia at epoch exit). `prod_touch: NONE`.

*Authored by principal-engineer (10x-dev), S1 Phase-2, parallel to arch-adversary. Hand back to
Potnia/architect for Phase-3 reconciliation (finalize TDD §4 with [H1]-[H23]; carry the G11 collision
into the DP-3 packet).*
