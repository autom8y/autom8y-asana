---
type: spec
subtype: tdd
title: Storage Namespace Contract (SNC)
initiative: storage-namespace-contract
status: draft
rung: design-only  # NOT built / NOT live / NOT verified-realized
date: 2026-06-10
author: arch remediation-planner (A4)
head: 8f9051b1 (origin/main autom8y-asana) / 49972967 (autom8y TF)
evidence_grade: MODERATE  # self-ref ceiling; upstream A1/A2/A3 carry HIGH confidence on specific findings
upstream:
  - .ledge/reviews/storage-topology-census-2026-06-10.md            # A1
  - .ledge/reviews/storage-config-consumer-graph-2026-06-10.md      # A2
  - .ledge/reviews/storage-config-antipattern-assessment-2026-06-10.md  # A3
derivation_model: .ledge/specs/TDD-field-provenance-population-contract-2026-06-09.md  # §3-§4 template
n_applied_throughline: integration-boundary-fidelity N_applied 1→2 (this contract IS the four-layer discipline at config altitude)
companion_adr: .ledge/decisions/ADR-storage-namespace-contract-2026-06-10.md
---

# TDD — Storage Namespace Contract

> **Construct**: for every S3 namespace in the autom8-s3 bucket that any code
> in the autom8y-asana platform reads or writes, the namespace's *storage
> contract* — its canonical prefix, its semantic plane, its writer-owner
> (repo + code path or EXTERNAL + name), its reader APIs, its env-var binding (if
> any), its IAM principals + allowed verbs, and its lifecycle state
> (LIVE / FOSSIL / QUARANTINED) — must be **declared once, derived everywhere, and
> verified by a generated test suite.** Today those attributes are split across
> TF literals, Python defaults, env vars, and hand-pinned constants, producing
> the three-mask defect. The SNC makes the contract EXPLICIT · ENFORCED ·
> GENERATED-VERIFIED · OBSERVED.
>
> **Rung (G-RUNG)**: This is a design. It is not built, not live, not
> verified-realized. The only live receipts are diagnostic (A1/A2/A3 census).
> Architecture exits at designed/adversary-PASSED; the contract is NOT real until
> a misconfigured consumer cannot pass CI.
>
> **CR-3 safety invariant**: NO change in any phase may perturb the live
> coherent=561 plane (dataframes/ namespace, S3DataFrameStorage default) or the
> warm cadence (checkpoint namespaces). Every phase is independently revertible.

---

## 1. System Context

### 1.1 The namespace denominator (A1 territory)

11 live S3 prefixes under autom8-s3 touching the asana subsystem (A1 live
census, 2026-06-10):

| # | Namespace prefix | Live keys | Lifecycle | Owner |
|---|---|---|---|---|
| 1 | `asana-cache/tasks/` | 384,992 | LIVE | ECS receiver (durable-first write) |
| 2 | `asana-cache/project-frames/` | 2,243 | FOSSIL | EXTERNAL:monolith-v1 (last write 2025-10-02) |
| 3 | `dataframes/` | 1,025 | LIVE | autom8y-asana S3DataFrameStorage |
| 4 | `cache-warmer/checkpoints/` | ~3 | LIVE | autom8y-asana CheckpointManager |
| 5 | Redis (not S3) | n/a | LIVE | RedisCacheProvider |
| 5p | (phantom S3 cold tier) | 0 | PHANTOM | — wired nowhere — |
| 6 | `asana-cache/task-cache/` | 128,583 | FOSSIL | EXTERNAL:monolith-legacy-pickle |
| 7 | `asana-cache/task-data-cache-v3/` | 342 | FOSSIL | EXTERNAL:monolith |
| 8 | `asana-cache/insights-frames/` | 13,448 | LIVE | EXTERNAL:insights-export-lambda |
| 9 | `asana-cache/name-gid-mappings/` | 6 | FOSSIL | EXTERNAL:monolith |
| 10 | `asana-cache/dataframes/` | 6 | FOSSIL | EXTERNAL:monolith-legacy |

### 1.2 The three-mask defect (A1/A3 synthesis)

The triple-defect saga was ONE architecture defect wearing three masks. All
three are the same root: **the storage prefix and the principal grant are not
derived from a single canonical namespace registry.**

| Mask | Anti-pattern (A3) | Root |
|---|---|---|
| #1 phantom tier | AP-2 — config advertises an S3 read tier that is never wired | No liveness contract between config tier and backend |
| #2 prefix overload | AP-1 + AP-4 — `ASANA_CACHE_S3_PREFIX` feeds two semantic planes; writer unknown | No per-namespace prefix binding; env overloaded |
| #3 IAM drift | AP-3 — grants evolve per-incident, not from a namespace map | No derivation path from namespace registry to IAM grant |

### 1.3 The WRITER-UNKNOWN (load-bearing open item)

A2 §5 + A3 §Unknowns: the live writer of the 384,992 `asana-cache/tasks/` keys
cannot be pinned from the autom8y-asana repo. The A1 attribution
("monolith writer at autom8_adapter.py:300") is REFUTED (A2: that module builds
a Redis provider). TF `main.tf:1218` comment attributes it to "the ECS receiver
under its full-bucket grant." No prod `S3CacheProvider(` construction site
exists in src/scripts (A2 P3 grep-negative, HIGH confidence).

**Roadmap treatment**: the WRITER-UNKNOWN is Phase-γ's first discovery task,
NOT a resolved fact. Phase-α and Phase-β can proceed because they operate on
the consumer side (split, contract, retire phantom) and the LIVE read path (the
#121 cure) already pins `"asana-cache"` as a constant. The writer must surface
before Phase-γ can codify the owner declaration.

---

## 2. Option Enumeration

Per option-enumeration-discipline: each option carries reversibility, CR-3
safety, blast radius (A2 counts), falsifiable prediction with expiry, and
RED-fixture design.

### O-A — Env split only

**Mechanism**: rename `ASANA_CACHE_S3_PREFIX` to two purpose-scoped vars:
`ASANA_TASK_CACHE_S3_PREFIX` (task-cache plane, default `"asana-cache"`) and
`ASANA_DATAFRAME_S3_PREFIX` (dataframe plane, default `"dataframes/"`). Back-compat
defaults mean no behavior changes on day-1.

**Blast radius (A2 §2 O-A)**: ~9 edge sites, ~5 files (4 AS + 1 TF).

**What it fixes**: AP-1 (prefix overload eliminated at the env layer). The
`_DURABLE_TASK_CACHE_PREFIX` pin in `null_number_recovery.py:148` can be retired
and derived from the task-cache var.

**What it does NOT fix**: AP-2 (phantom tier survives), AP-3 (IAM grants still
hand-authored), AP-4 (writer-unknown persists), AP-5 (fossil grants survive),
AP-6 (scattered literals survive — split adds two new ones), AP-7 (orphan keys
unclaimed).

**Reversibility**: HIGH. TF env rename with back-compat default is a rollback-safe
deploy. A single `git revert` on the settings change restores the previous state.

**CR-3 safety**: HIGH. Back-compat defaults guarantee no prefix value changes on
any live plane; the `dataframes/` plane is already env-disconnected (D1–D8
hardcoded defaults), so the split does not touch its behavior.

**Falsifiable prediction**: within 30 days of merge, `git grep "ASANA_CACHE_S3_PREFIX"
origin/main -- src/ terraform/` returns ZERO hits.
**Expiry**: 2026-07-10.

**RED-fixture**: set `ASANA_TASK_CACHE_S3_PREFIX="asana-cache/WRONG/"` in a test
env; assert the task-cache key-builder produces `asana-cache/WRONG/tasks/{gid}/task.json`
(current behaviour — the split makes the wrong value VISIBLE and testable, not
hidden behind an overloaded env that reaches nothing live).

**Leverage**: impact=MEDIUM (fixes one mask; latent only), effort=LOW. Leverage
score ~2. Mid-tier — quick win on the env surface but incomplete contraction.

---

### O-B — StorageNamespaceContract SSOT

**Mechanism**: introduce a `storage_namespace.py` registry module (one frozen
dataclass per namespace: prefix · semantic-plane · writer-owner · reader-APIs ·
env-var (if any) · IAM-principals+verbs · lifecycle). Derive: settings defaults,
TF env blocks + IAM policy resources, the cure's pinned constant, AND a generated
alignment test suite.

**Registry dataclass schema** (the template, mirroring FPC §3):

```python
from dataclasses import dataclass
from enum import Enum

class Lifecycle(Enum):
    LIVE        = "live"
    FOSSIL      = "fossil"
    QUARANTINED = "quarantined"
    PHANTOM     = "phantom"     # config present, no wired backend

class IAMVerb(Enum):
    GET    = "s3:GetObject"
    PUT    = "s3:PutObject"
    DELETE = "s3:DeleteObject"
    HEAD   = "s3:HeadObject"
    LIST   = "s3:ListBucket"

@dataclass(frozen=True)
class WriterOwner:
    repo: str                    # "autom8y-asana" | "autom8y/a8" | "EXTERNAL"
    code_anchor: str | None      # file:line OR None if EXTERNAL+unlocated
    external_name: str | None    # human name when repo="EXTERNAL"

@dataclass(frozen=True)
class IAMGrant:
    principal_arn: str           # role ARN or user ARN
    verbs: tuple[IAMVerb, ...]

@dataclass(frozen=True)
class StorageNamespaceContract:
    # --- identity ---
    name: str                    # e.g. "TASK_CACHE"
    prefix: str                  # literal S3 prefix, e.g. "asana-cache/tasks/"
    # --- semantic plane ---
    semantic_plane: str          # e.g. "task-durable-cache" | "dataframe-v2" | ...
    # --- ownership ---
    writer_owner: WriterOwner
    reader_apis: tuple[str, ...]  # file:line of reader construction sites
    # --- config surface ---
    env_var: str | None          # e.g. "ASANA_TASK_CACHE_S3_PREFIX" or None if hardcoded
    env_default: str | None      # back-compat default value
    # --- IAM ---
    iam_grants: tuple[IAMGrant, ...]
    # --- lifecycle ---
    lifecycle: Lifecycle
    lifecycle_note: str = ""     # e.g. "v1 name-keyed schema; last write 2025-10-02"
```

**Worked instances** (anchored to A1/A2/A3 evidence):

```python
TASK_CACHE = StorageNamespaceContract(
    name="TASK_CACHE",
    prefix="asana-cache/tasks/",
    semantic_plane="task-durable-cache",
    writer_owner=WriterOwner(
        repo="EXTERNAL",                     # WRITER-UNKNOWN: ECS receiver durable-first
        code_anchor=None,                    # UV-P: not yet located — Phase-γ discovery task
        external_name="ECS-receiver-durable-first (main.tf:1218 comment)",
    ),
    reader_apis=(
        "dataframes/builders/null_number_recovery.py:495",  # the #121 cure reader
    ),
    env_var="ASANA_TASK_CACHE_S3_PREFIX",   # post-O-A split name
    env_default="asana-cache",
    iam_grants=(
        IAMGrant(
            "arn:aws:iam::696318035277:role/autom8-asana-cache-warmer-lambda-role",
            (IAMVerb.GET,),   # S3DurableTaskCacheRead Sid — read-only
        ),
        # ECS task role holds full-bucket; narrowing is Phase-β target
    ),
    lifecycle=Lifecycle.LIVE,
)

DATAFRAME_V2 = StorageNamespaceContract(
    name="DATAFRAME_V2",
    prefix="dataframes/",
    semantic_plane="dataframe-v2-gid-keyed",
    writer_owner=WriterOwner(
        repo="autom8y-asana",
        code_anchor="dataframes/storage.py:342",   # S3DataFrameStorage default prefix
        external_name=None,
    ),
    reader_apis=(
        "api/preload/legacy.py:130",
        "api/preload/progressive.py:298",
        "dataframes/section_persistence.py:1050",
        "scripts/warm_cache.py:82",
        "dataframes/offline.py:83",
    ),
    env_var=None,   # hardcoded default; no env override in use
    env_default="dataframes/",
    iam_grants=(
        IAMGrant(
            "arn:aws:iam::696318035277:role/autom8-asana-cache-warmer-lambda-role",
            (IAMVerb.GET, IAMVerb.PUT, IAMVerb.DELETE, IAMVerb.HEAD),
        ),
    ),
    lifecycle=Lifecycle.LIVE,
)

CHECKPOINTS = StorageNamespaceContract(
    name="CHECKPOINTS",
    prefix="cache-warmer/checkpoints/",
    semantic_plane="warmer-checkpoint",
    writer_owner=WriterOwner(
        repo="autom8y-asana",
        code_anchor="lambda_handlers/checkpoint.py:31",
        external_name=None,
    ),
    reader_apis=("lambda_handlers/checkpoint.py:50",),
    env_var="CACHE_WARMER_CHECKPOINT_PREFIX",
    env_default="cache-warmer/checkpoints/",
    iam_grants=(
        IAMGrant(
            "arn:aws:iam::696318035277:role/autom8-asana-cache-warmer-lambda-role",
            (IAMVerb.GET, IAMVerb.PUT, IAMVerb.DELETE, IAMVerb.HEAD),
        ),
    ),
    lifecycle=Lifecycle.LIVE,
    lifecycle_note="per-lane disjoint by design (#96); accepted trade-off per A3",
)

PROJECT_FRAMES_FOSSIL = StorageNamespaceContract(
    name="PROJECT_FRAMES_FOSSIL",
    prefix="asana-cache/project-frames/",
    semantic_plane="dataframe-v1-name-keyed-FOSSIL",
    writer_owner=WriterOwner(
        repo="EXTERNAL",
        code_anchor=None,
        external_name="autom8-monolith-v1 (last write 2025-10-02; 8mo stale)",
    ),
    reader_apis=(),   # zero readers
    env_var="ASANA_CACHE_S3_PREFIX",   # the overloaded fossil env; retire post-split
    env_default=None,
    iam_grants=(
        # These grants MUST be removed under Phase-β (AP-5 cure)
        IAMGrant(
            "arn:aws:iam::696318035277:role/autom8-asana-cache-warmer-lambda-role",
            (IAMVerb.GET, IAMVerb.PUT, IAMVerb.DELETE, IAMVerb.HEAD),
        ),
    ),
    lifecycle=Lifecycle.FOSSIL,
    lifecycle_note="v1 name-keyed schema; 2,243 stranded keys; last write 2025-10-02; "
                   "no reader in any repo; AP-5: fossil retains PUT/DELETE grants — remove",
)
```

**The derivation model** (mirroring FPC §4 G-PROPAGATE):

```
              ┌─────────────────────────────┐
              │  StorageNamespaceContract   │  ← THE SINGLE WRITE POINT
              │  (prefix, lifecycle, ...)   │
              └──────────────┬──────────────┘
   ┌──────────┬──────────────┼──────────────┬──────────────┬───────────────┐
   ▼          ▼              ▼              ▼              ▼               ▼
settings   TF env        TF IAM         cure pin      t1: owner     t2: IAM
defaults   blocks        resources      (derived,     completeness  alignment
(derived)  (generated    (generated     not hand-     test          test
           .json)        .json)         pinned)       (t1..t5)      (t1..t5)
```

| derived artifact | derivation rule | seals |
|---|---|---|
| `settings.py` prefix defaults | `S3Settings.task_cache_prefix = TASK_CACHE.env_default` etc. | AP-1, AP-6 |
| `_DURABLE_TASK_CACHE_PREFIX` | `= TASK_CACHE.prefix` (derived from registry, not pinned literal) | AP-1, AP-6 |
| TF env blocks | `namespaces.gen.json` → `jsondecode(file("namespaces.gen.json"))` TF local | AP-1, AP-3 |
| TF IAM `Resource` ARNs | generated from `iam_grants` per namespace lifecycle (FOSSIL → GET-only; LIVE → declared verbs) | AP-3, AP-5 |
| alignment test t1 | every LIVE/FOSSIL registry namespace has `writer_owner.code_anchor` non-None OR is `EXTERNAL+name` declared — kills AP-4/AP-7 | AP-4, AP-7 |
| alignment test t2 | every IAM grant `Resource` prefix ∈ registry namespace prefixes with matching verbs and principal — kills AP-3 | AP-3 |
| alignment test t3 | no Python literal / settings field declares a prefix string outside the registry — kills AP-1/AP-6 | AP-1, AP-6 |
| alignment test t4 | no config field advertises a backend tier with `lifecycle=PHANTOM` — kills AP-2 | AP-2 |
| alignment test t5 | FOSSIL/QUARANTINED namespaces have no PUT/DELETE grants — kills AP-5 | AP-5 |

**The TF↔Python derivation edge (the hard part — designed explicitly)**:

TF cannot import Python at plan-time. The mechanism is:

1. `src/autom8_asana/storage_namespace.py` declares the registry (pure frozen
   dataclasses, no imports beyond stdlib).
2. A generator script `scripts/gen_namespace_config.py` imports the registry
   and emits `terraform/services/asana/namespaces.gen.json` — a JSON object with
   two keys: `"env_blocks"` (prefix env vars by lane) and `"iam_resources"` (ARN
   lists per policy Sid).
3. TF reads: `locals { ns = jsondecode(file("${path.module}/../../../src/autom8_asana/namespaces.gen.json")) }` —
   prefix env values and IAM Resource ARNs derive from the generated file.
4. A CI diff-test (`tests/arch/test_namespace_gen.py`) runs the generator and
   asserts `git diff --exit-code terraform/services/asana/namespaces.gen.json`.
   If the registry changes without regenerating, CI fails.

This mechanism makes the TF derivation **detection-grade (CI-enforced), not
prevention-grade** at the TF-plan boundary. The distinction is honest: TF can
drift from the registry during the `terraform plan` step if the .gen.json is
stale between CI runs. The diff-test is the enforcement channel; a pre-commit
hook running the generator closes the remaining window.

**[UV-P: the diff-test CI enforcement is detection-grade between CI runs; a pre-commit hook regenerating namespaces.gen.json on registry edits closes the window to near-zero | METHOD: bash-probe (pre-commit hook verifying gen invocation on `storage_namespace.py` changes) | REASON: the pre-commit hook is a Phase-α deliverable, not yet present; the diff-test alone is the initial enforcement channel]**

**Blast radius (A2 §2 O-B extended)**: ~14 edge sites, ~8 files (6 AS + 1 TF + 1
test) — the full contraction surface.

**Reversibility**: MEDIUM. The registry module is additive; settings/TF changes
have back-compat defaults. Reverting the TF derivation means restoring literal
env values — a TF revert, not a data operation. Alignment tests can be
`xfail`-gated during rollback.

**CR-3 safety**: HIGH provided derivation defaults exactly match current live
values. The generator MUST emit `"dataframes/"` for DATAFRAME_V2 and `"asana-cache"`
for TASK_CACHE — verified by the diff-test on day-1.

**Falsifiable prediction**: within 60 days of Phase-α merge, `git grep -n '"asana-cache"'
origin/main -- src/autom8_asana/ | grep -v "storage_namespace.py" | grep -v test`
returns ZERO hits. **Expiry**: 2026-08-10.

**RED-fixture**: mutate `TASK_CACHE.prefix = "asana-cache/WRONG/"` in the registry;
assert t3 fires RED (a literal `"asana-cache"` now exists in
`null_number_recovery.py:148` that disagrees with the registry).

**Leverage**: impact=HIGH (kills all 7 anti-patterns), effort=MEDIUM. Leverage
score ~3. Strategic investment — highest contraction value.

---

### O-C — O-B + phantom-RETIRE (Option-2 resolution)

**Mechanism**: O-B plus an explicit decision on the phantom S3 cold tier (AP-2).
Two sub-options:

**(i) Wire S3 as a first-class read tier**: add a real `TieredConfig(s3_enabled=True)`
production construction path. Cost: the fleet cache-topology change deferred
from the cure saga; re-couples the ECS receiver to the overloaded `S3Settings.prefix`
that O-A/O-B is trying to disentangle; requires the `S3CacheProvider` prod
construction site that currently does not exist. The existing #121 cure already
reads `asana-cache/tasks/` directly via raw boto3 — adding a tiered abstraction
layer above it buys nothing and re-introduces the coupling the cure escaped.

**(ii) RETIRE the phantom**: delete `s3_enabled`, `ASANA_CACHE_S3_ENABLED`
docstring, and the `tiered.py` cold-path gates; declare `asana-cache/tasks/` a
WRITE-ONLY-durable + explicit-read namespace (which is what production actually
is); promote `DurableTaskCacheReader` as the blessed read API wrapping the
raw boto3 `get_object` the #121 cure already uses.

**Evidence for (ii)**:
- The cure WORKS. `null_number_recovery.py:495` raw boto3 GET is live,
  coherent=561 confirmed (THROUGHLINE node fired 2026-06-10 13:07Z).
- A tiered read tier would re-couple to `S3Settings.prefix` — the exact config
  surface this contract is quarantining (A2 §0, P2/P3).
- `factory.py:209/219`: "S3 cold tier is Phase 3" — the decision is already
  deferred by design. The registry simply makes the deferral EXPLICIT via
  `lifecycle=PHANTOM → remove` rather than leaving false docstrings.
- O-B's t4 alignment test makes a phantom tier a CI failure. Retiring it is
  strictly simpler than making it live.

**The `DurableTaskCacheReader` API** (small wrapper, the "blessed pattern" that
replaces the phantom):

```python
class DurableTaskCacheReader:
    """Explicit read API for the TASK_CACHE namespace.

    This is NOT a tiered cache tier. The asana-cache/tasks/ namespace is
    WRITE-ONLY-durable (written by the ECS receiver durable-first path) with
    EXPLICIT read via this class. There is no S3 cold tier in the cache
    provider stack — see StorageNamespaceContract.TASK_CACHE.lifecycle_note.
    """
    def __init__(self, s3_client, prefix: str = TASK_CACHE.prefix, bucket: str = ...):
        self._prefix = prefix   # derived from registry, not env
        ...
    async def get_task(self, gid: str) -> dict | None:
        key = f"{self._prefix}tasks/{gid}/task.json"
        ...  # boto3 get_object, same pattern as null_number_recovery.py:495
```

This formalizes what the #121 cure already does as an ad-hoc pattern and gives
it a named, registerable owner in the namespace registry.

**Blast radius**: same as O-B + ~3 additional sites (`tiered.py` field deletions,
docstring removal, `docs/guides/cache-system.md:140` stale doc update).

**Reversibility**: HIGH for the phantom-retire sub-component (the cold-path code
is dead; deleting dead gates has no runtime effect and is trivially revertible).
MEDIUM overall (same as O-B for the registry work).

**CR-3 safety**: HIGH. Deleting dead cold-path gates changes nothing at runtime.
The `DurableTaskCacheReader` wrapper is additive; the existing
`null_number_recovery.py:495` pattern continues to work unchanged during
transition.

**Falsifiable prediction**: within 60 days of Phase-α merge, `git grep "s3_enabled"
origin/main -- src/` returns ZERO hits. **Expiry**: 2026-08-10.

**RED-fixture**: before retire — construct `TieredConfig()` in a test and assert
`s3_enabled == False` AND `self._cold is None` (proves the tier was never live);
the test turns GREEN on the retire commit (field gone → test replaced by
`DurableTaskCacheReader` unit test).

**Leverage**: impact=HIGH (kills all 7 APs including AP-2 cleanly), effort=MEDIUM.
Leverage score ~3.5. Slightly higher than O-B alone because phantom-retire costs
near-zero (dead code deletion) while closing AP-2 permanently.

---

### O-D — Status-quo + lint

**Mechanism**: add grep-lint forbidding `get_settings().s3.prefix` as a live read
and forbidding new `S3DataFrameStorage(prefix=...)` overrides. Leave all four
fossil TF env sites and the phantom flag.

**Blast radius**: ~1 CI rule.

**What it fixes**: AP-1 is detection-grade only (next caller is discouraged, not
blocked). Fixes nothing structural.

**Leverage**: impact=LOW (zero contraction; wrong-prefix read remains addressable
by any caller that ignores the lint), effort=LOW. Leverage score ~0.5. Long-term
transformation category — lowest leverage, accepted only as a temporary gate
while O-C phases in.

---

## 3. Option Comparison Table

| Dimension | O-A (env split) | O-B (SSOT registry) | O-C (O-B + retire phantom) | O-D (lint only) |
|---|---|---|---|---|
| APs cured | AP-1 partial | AP-1..AP-7 all | AP-1..AP-7 all + AP-2 clean retire | AP-1 detection only |
| Blast radius | ~9 sites / 5 files | ~14 sites / 8 files | ~17 sites / ~10 files | ~1 CI rule |
| Leverage score | ~2 | ~3 | ~3.5 | ~0.5 |
| CR-3 safety | HIGH | HIGH | HIGH | HIGH |
| Reversibility | HIGH | MEDIUM | MEDIUM | HIGH |
| TF↔Python | no cross-repo | diff-test+gen (detection-grade) | diff-test+gen (detection-grade) | none |
| Phantom retired | NO | NO (t4 test catches it) | YES | NO |
| Writer-unknown | unresolved | registry forces declaration | registry forces declaration | unresolved |
| "Structurally unaddressable" | NO — lint-grade only | YES — t1..t5 CI tests | YES | NO |

---

## 4. Recommendation: O-C with phantom-RETIRE (ii)

**Recommendation**: O-C with phantom-RETIRE sub-option (ii).

**Argument**:

1. **O-A alone fails the grandeur anchor.** Splitting the env removes the overload
   (AP-1) but leaves AP-2 through AP-7 structurally re-triggerable. The
   wrong-prefix read remains addressable — a new caller can construct
   `S3CacheProvider(prefix=get_settings().task_cache_prefix)` and land in the
   task-cache namespace from the ECS receiver, which still holds a full-bucket
   grant. The grandeur anchor requires STRUCTURAL UNADDRESSABILITY; O-A delivers
   discoverability.

2. **O-B/O-C are the only options that make the wrong-prefix read structurally
   unaddressable.** Test t3 makes a prefix literal outside the registry a CI
   failure. Test t2 makes a grant pointing at an unregistered prefix a CI failure.
   Together they close both directions of the drift class.

3. **Phantom-RETIRE (ii) is correct.** The cure works (#121, coherent=561). Wiring
   option (i) would re-couple to `S3Settings.prefix` — the exact surface we are
   contracting. The `DurableTaskCacheReader` wrapper costs ~20 LOC and formalizes
   what production already does. The false docstring in `tiered.py:49` is an
   active misleader; deleting it is strictly better than making the phantom
   discoverable via a registry entry.

4. **The effort delta between O-B and O-C is negligible.** The phantom-retire is
   dead-code deletion (~3 sites) plus a small wrapper class. The diff test and
   registry module are the bulk of the work in both options.

5. **O-D is appropriate only as a temporary gate during Phase-α build.** It should
   be added as an interim lint rule before the registry lands, then retired once
   t3 is live.

**Operator decision points** (escalated — human judgment required):

- **IAM tightening of ECS full-bucket** (Phase-β): the ECS task role currently holds
  `autom8-s3/*` (full-bucket). Narrowing to the declared namespace set is the
  intended Phase-β change. Before scoping, ENUMERATE what the ECS receiver writes:
  from A1/A2 evidence the receiver writes `asana-cache/tasks/` (durable-first)
  and reads `dataframes/` (preload). It may also write `dataframes/` (the warmer
  lane calls `S3DataFrameStorage.put_async` but those paths also run as Lambda).
  The operator must verify the ECS receiver's WRITE surface before narrowing — an
  incomplete scope breaks writes silently. This enumeration is a Phase-β
  pre-condition, not a Phase-α deliverable.

- **Fossil namespace retention vs deletion**: `asana-cache/project-frames/` (2,243
  keys) and `asana-cache/task-cache/` (128,583 pickle keys) are write-orphaned.
  The contract quarantines them (no new writes possible); physical deletion is a
  separate operator decision requiring confirmation that no emergency rollback
  path reads them. The registry's `lifecycle=FOSSIL` state is the correct holding
  state; object deletion is out of scope for this contract.

---

## 5. Phased Roadmap

### Phase-α — 10x-dev build

**Scope**: registry module + alignment tests + phantom-retire + `DurableTaskCacheReader`
API. PYTHON ONLY — no TF changes. This phase is CR-3-safe because no env value
changes; the registry's defaults match current live values exactly.

**Deliverables**:

1. `src/autom8_asana/storage_namespace.py` — `StorageNamespaceContract` registry
   with all 11 namespace rows (4 LIVE, 6 FOSSIL/PHANTOM, 1 Redis non-S3).
   WRITER-UNKNOWN declared explicitly in TASK_CACHE as `external_name=
   "ECS-receiver-durable-first (main.tf:1218 comment)"` with `code_anchor=None`.
2. `scripts/gen_namespace_config.py` — generator emitting `namespaces.gen.json`
   to the TF services/asana path.
3. `terraform/services/asana/namespaces.gen.json` — generated file, checked in,
   initially matching the current TF literal values exactly (diff is zero on day-1).
4. `src/autom8_asana/cache/durable_task_cache.py` — `DurableTaskCacheReader`
   wrapping the raw boto3 pattern from `null_number_recovery.py:495`, deriving
   prefix from `TASK_CACHE.prefix`.
5. `null_number_recovery.py:148` — `_DURABLE_TASK_CACHE_PREFIX` now derived:
   `from autom8_asana.storage_namespace import TASK_CACHE; _DURABLE_TASK_CACHE_PREFIX = TASK_CACHE.prefix`
6. `cache/providers/tiered.py` — delete `s3_enabled` field and cold-path gates
   (`tiered.py:57, :120, :126, :168, :211, :264, :302, :364, :430, :492`).
   Factory comment `factory.py:209` updated to "S3 cold tier permanently deferred
   — see StorageNamespaceContract.PHANTOM in storage_namespace.py."
7. `docs/guides/cache-system.md:140` — remove stale `s3_enabled=True` reference.
8. `tests/arch/test_namespace_contract.py` — alignment test suite implementing
   t1..t5 (see §2 derivation model). G-THEATER mandate: each test proven by a
   RED fixture (see §5.1 below).
9. `tests/arch/test_namespace_gen.py` — diff-test asserting `namespaces.gen.json`
   regenerates to identical content (proves the gen script is idempotent and
   CI-verifiable).
10. Interim lint rule (as a pre-cursor, can land first): `ruff` or a `grep`-based
    pre-commit hook blocking new occurrences of `get_settings().s3.prefix` in
    production code paths.

**Reversibility**: HIGH. All changes are additive (new module, new tests) or dead-code
deletion (tiered.py phantom gates). The only non-additive change is `null_number_recovery.py:148`
— trivially revertible (replace the import with the literal string).

**CR-3 safety**: HIGH. The `_DURABLE_TASK_CACHE_PREFIX` value is `"asana-cache"`
before and after derivation. The `dataframes/` plane is untouched. The tiered
cold-path deletion affects no production path (confirmed dead by A2 §1E HIGH).

**Falsifiable prediction**: CI passes with all t1..t5 GREEN and the diff-test GREEN
within 5 days of Phase-α land. Prediction expires 2026-08-15.

**RED-fixture design** (G-THEATER per FPC §4.1 mandate):

- t1 RED: add a LIVE namespace row with `writer_owner.code_anchor=None` and
  `writer_owner.external_name=None` → t1 fires `AssertionError: namespace LIVE_ORPHAN
  has no writer owner declared`.
- t2 RED: add an IAM grant row pointing at `"autom8-s3/UNREGISTERED/*"` (not in
  the registry) → t2 fires `AssertionError: IAM grant Resource prefix not in
  namespace registry`.
- t3 RED: introduce `prefix_str = "asana-cache"` in a non-registry Python file
  → t3 grep-lint fires.
- t4 RED: add a `StorageNamespaceContract(..., lifecycle=Lifecycle.PHANTOM)` and
  assert a config field references it → t4 fires.
- t5 RED: add a PUT grant on `PROJECT_FRAMES_FOSSIL` → t5 fires
  `AssertionError: FOSSIL namespace PROJECT_FRAMES_FOSSIL has PUT grant`.

---

### Phase-β — sre: TF derivation + IAM tightening

**Scope**: wire TF to read `namespaces.gen.json`; narrow ECS full-bucket grant;
remove fossil PUT/DELETE grants from warmer roles. Each sub-change is
**operator-gated** (each TF apply is a separate PR + deploy gate).

**Pre-conditions** (must be met before Phase-β opens):

1. Phase-α merged and CI GREEN (all t1..t5 passing).
2. ECS receiver WRITE surface enumerated — operator confirms the exact set of
   namespaces the ECS task role must PUT to (required before IAM narrowing to
   avoid a silent write-breaking deploy).
3. `namespaces.gen.json` diff-test GREEN (proves the file is stable).

**Deliverables**:

1. **TF locals derivation** (β-1, low risk): refactor `main.tf` prefix env values
   and IAM `Resource` ARN lists to derive from `namespaces.gen.json` via
   `jsondecode(file(...))`. Behavior is IDENTICAL on day-1 (the .gen.json matches
   the current literals). This is the structural change that makes future
   namespace additions derive from the registry rather than requiring manual TF edits.

2. **Fossil grant removal** (β-2, medium risk, operator-gated): remove
   `PUT`/`DELETE` grants on `asana-cache/project-frames/` from all three warmer
   role policies. The fossil is write-orphaned (A2 §4 HIGH); removing PUT/DELETE
   cannot break any live path. The `GET` grant may be retained temporarily as a
   read-safety net pending fossil deletion decision.

3. **ECS grant narrowing** (β-3, HIGH risk, operator-gated separately):
   narrow `autom8y-asana-service-task-s3` from `autom8-s3/*` to the declared
   namespace set. This is the highest-risk change because the ECS receiver's full
   write surface must be verified before scoping (see Operator Decision Points in
   §4). A staged narrowing — first restrict to known namespaces + retain a
   temporary overly-broad catch-all, then tighten in a follow-on PR — is the
   safer approach.

**Reversibility**: MEDIUM. Each β sub-change is an independent TF PR. β-1
is pure refactor (rollback = restore literals, no IAM effect). β-2 and β-3 are
IAM changes — a rollback on β-3 requires a TF apply to restore the old policy,
which is fast but requires a deploy cycle.

**CR-3 safety**: HIGH for β-1 (no IAM effect). MEDIUM for β-2/β-3 (IAM changes
can silently break writes if the surface is under-enumerated; the pre-condition
of ECS write-surface enumeration mitigates this).

**Falsifiable prediction**: after β-1 land, `terraform plan` produces zero diff on
the next registry-only change (no human edits to TF env literals needed). Expires
2026-09-01.

**RED-fixture**: a TF test (or a `tflint` custom rule via the gen'd JSON schema)
that asserts every IAM `Resource` ARN in the three warmer policies is present in
`namespaces.gen.json` — fails when a new namespace is added to the registry but
the TF apply has not yet re-derived.

---

### Phase-γ — cross-repo: writer-unknown resolution + SEAM-2 rider

**Scope**: pin the WRITER-UNKNOWN for `asana-cache/tasks/`; SEAM-2 rider if the
SEAM-2 monolith consumers need namespace registry awareness.

**First deliverable — discovery task** (γ-0, research only):

Locate the exact code path that writes `asana-cache/tasks/{gid}/task.json` in
the ECS receiver. The A2 §5 Unknown attributes it to "the ECS receiver
durable-first path" (TF `main.tf:1218` comment) but no prod `S3CacheProvider(`
construction site was found. Candidate greps:

```
git grep -n "task.json\|asana-cache/tasks\|tasks/{" origin/main -- src/
git grep -n "durable\|durable_first\|durable_write" origin/main -- src/
```

If the writer is in the ECS receiver Python path (autom8y-asana), the registry
`TASK_CACHE.writer_owner.code_anchor` can be pinned. If it is in the autom8
Go monolith (`/Users/tomtenuta/Code/a8`), A2 §3 proves the Go tree has zero
`asana-cache/tasks` hits — the writer must be the Python ECS receiver path.

**Pre-condition for γ-0**: NO Phase-γ work proceeds until the writer identity is
confirmed. If the writer is the ECS receiver Python path, the registry update is
a low-risk code-anchor addition. If it is an external system not in this repo,
the `EXTERNAL` declaration is confirmed and the registry note updated.

**γ-1 — registry update**: once the writer is confirmed, update
`TASK_CACHE.writer_owner.code_anchor` from `None` to the confirmed file:line.
This makes t1 pass without the `EXTERNAL+external_name` exception.

**γ-2 — SEAM-2 rider**: the SEAM-2 monolith consumers (offer/unit frame reads)
are mediated by the ECS receiver HTTP API, not by direct S3 access (A2 §3,
HIGH confidence). No SEAM-2 change is needed for the namespace contract itself.
If SEAM-2 introduces a direct S3 reader in a sibling repo, that reader must
declare itself in `reader_apis` for the relevant namespace. The contract enforces
this via t1/t3.

**Reversibility**: HIGH (registry annotation; no runtime change).

**CR-3 safety**: HIGH (no runtime change; writer-discovery is read-only research).

**Falsifiable prediction**: after γ-0 completes, `TASK_CACHE.writer_owner.code_anchor`
is non-None in `storage_namespace.py`. Expires 30 days after Phase-β close.

---

## 6. N_applied 1→2 Registration: integration-boundary-fidelity

**Claim**: this StorageNamespaceContract IS the integration-boundary-fidelity
four-layer discipline applied at config altitude. This is the N=2 instance.

**Layer mapping argument**:

| Throughline Layer | Config-altitude application in the SNC |
|---|---|
| Layer 1 — Population-mechanism fidelity | The namespace registry declares the WRITER-OWNER for each namespace. A consumer test must use the REAL write path (the production `DurableTaskCacheReader` or `S3DataFrameStorage`), not a stand-in that pre-populates a different prefix. t1 enforces writer declaration; the alignment tests use real construction paths. |
| Layer 2 — Key-construction + config-pollution fidelity | AP-1's cure: the registry eliminates the overloaded env. t3 asserts no prefix literal exists outside the registry. The key `{TASK_CACHE.prefix}/tasks/{gid}/task.json` is the exact-key analog at config altitude — ONE declared constant, no overload. |
| Layer 3 — Deserialization-shape fidelity | At config altitude, this is the IAM grant shape: the grant resource ARN must match the namespace prefix EXACTLY (t2). A grant that points at `project-frames/` while the writer uses `tasks/` is the config analog of an envelope mismatch. |
| Layer 4 — Runtime-principal-permission fidelity | AP-3's cure: IAM grants are derived from the registry (Phase-β). A namespace whose writer does not have a grant is a Layer-4 failure at config altitude. The #481 reactive grant was a Layer-4 failure — the test suite could not catch it because no IAM assertion existed. t2 is the IAM-assertion analog for the config layer. |

**N=1 instance** (already registered): autom8y-asana null_number_recovery
hot-store heal path (#119→#120→#121→#481), fired 2026-06-10 13:07Z.

**N=2 instance (this registration)**: autom8y-asana storage namespace contract
design — applying the four-layer discipline to the configuration boundary
(env vars, S3 prefixes, IAM grants) rather than the object-cache boundary.
The saga's three masks ARE the four-layer failures at config altitude: mask #1
= Layer-1 (phantom population mechanism), mask #2 = Layer-2 (config-pollution
key divergence), mask #3 = Layer-4 (runtime principal grant drift).

**Evidence grade**: `[MODERATE, self-ref-capped]`. The N=2 registration is
self-referential (the same arch rite that designed the contract is registering
the N=2 instance). MODERATE ceiling holds per `self-ref-evidence-grade-rule`.
Promotion to MODERATE-external gated on a SECOND satellite independently
applying the four-layer discipline.

**[UV-P: this N=2 registration counts toward the throughline's MODERATE-external
gate only if a rite-disjoint attester (eunomia) confirms the layer mapping is not
circular | METHOD: file-read (THROUGHLINE-integration-boundary-fidelity-2026-06-10.md §7
Promotion Gate) | REASON: the §7 gate requires the second anchor to be a DISTINCT
incident at a DISTINCT satellite; this is the same satellite (autom8y-asana) at a
different altitude (config vs object-cache). Whether "different altitude" satisfies
"distinct incident" is a Pythia-custodianship question, not an arch-rite question.
Deferred to eunomia.]**

---

## 7. Unknowns Registry (consolidated from A1/A2/A3)

### Unknown: Live `asana-cache/tasks/` writer identity (AP-4 root)
- **Question**: which exact code path writes the 384,992 live `asana-cache/tasks/{gid}/task.json` keys — a receiver durable-first path whose construction site A2 could not locate, or some other path?
- **Why it matters**: Phase-γ γ-0 cannot close until the writer is pinned. If the writer reads a different prefix, the #121 cure's `"asana-cache"` pin may be a coincidental match, not a verified contract.
- **Evidence**: A2 P3 grep-negative (no prod `S3CacheProvider(`); TF `main.tf:1218` comment attributes to ECS receiver; A2 §3 confirms Go monolith zero hits.
- **Suggested source**: grep `asana-cache/tasks\|task.json` across `src/` and `api/routes/`; check receiver request-handler for a `durable_write` / `s3.put_object` call.

### Unknown: TF↔Python derivation (O-B/O-C feasibility assertion)
- **Question**: does the diff-test + gen mechanism provide sufficient CI enforcement, or is a pre-commit hook required to prevent a "CI passes on stale .gen.json" window?
- **Why it matters**: the "structurally unaddressable" claim for AP-3 requires the gen file to be always-current. The diff-test enforces this post-PR; the pre-commit hook enforces it pre-commit.
- **Evidence**: A2 §5 + O-B note; this TDD §2 O-B design.
- **Suggested source**: platform-engineer (Phase-β pre-conditions); the pre-commit hook is a Phase-α deliverable.

### Unknown: ECS receiver WRITE surface (Phase-β pre-condition)
- **Question**: does the ECS task role need PUT access to any namespaces beyond `asana-cache/tasks/` and `dataframes/`? Are there receiver writes to `cache-warmer/checkpoints/` or any other namespace not yet enumerated?
- **Why it matters**: narrowing the ECS grant without knowing the full write surface silently breaks production writes. This is the highest-risk unknown for Phase-β.
- **Evidence**: A1 IAM column — ECS holds full-bucket `autom8-s3/*`; only `asana-cache/tasks/` write was attributed. A1 A2 consensus is that warmer lanes (not ECS) write `dataframes/` and `checkpoints/`.
- **Suggested source**: grep for `s3.put_object\|S3CacheProvider\|S3DataFrameStorage` in the ECS receiver code path (routes/, api/); confirm via CloudTrail or S3 access logs.

### Unknown: `S3Settings.prefix` cross-repo importers
- **Question**: does any sibling python service import `autom8_asana.settings` and read `.s3.prefix` live?
- **Why it matters**: a hidden live reader inverts AP-1's "zero live readers" premise and reclassifies it CRITICAL.
- **Evidence**: A2 §5; A3 §Unknowns; in-repo only reader is the dead cold tier.
- **Suggested source**: `grep -r "s3.prefix\|s3_settings.prefix" repos/` across sibling checkouts.

---

## 8. Scope and Limitations

This contract covers:
- S3 namespace × env × IAM × Python config surface under autom8y-asana + autom8y TF.
- The phantom tier decision and its recommended disposal.
- The derivation model for t1..t5 alignment tests.

This contract does NOT cover:
- **Physical object deletion**: lifecycle=FOSSIL classification is the
  correct holding state; actual `aws s3 rm` of the 130k+ fossil keys is a
  separate operator decision requiring emergency-rollback verification.
- **Non-asana S3 namespaces** (`asset-packages/`, `openai-cache/`, `slack-cache/`,
  `sql-cache/`, `stripe-cache/`, `zipcode-cache/`) — sibling subsystems,
  out of scope per A1 EXCLUSIONS.
- **Redis internal topology** (ElastiCache cluster, TTLs, key schema) — not S3;
  out of scope.
- **CloudTrail / S3 access log analysis** — the IAM tightening pre-condition
  (ECS write surface) should be verified via access logs; this is an sre-rite
  operational concern.
- **Security audit of the pickle deserialization surfaces** (`asana-cache/task-cache/`
  and `asana-cache/task-data-cache-v3/` — FOSSIL pickle namespaces with
  `autom8` super-user as writer): A3 cross-rite observation; see cross-rite
  referrals in companion ADR.
- **monolith repo (`autom8/a8`) code changes**: the contract declares EXTERNAL
  writer ownership for monolith-written namespaces but does not prescribe
  changes to the Go monolith.

---

*Artifact: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/TDD-storage-namespace-contract-2026-06-10.md`*
*Read-only target repos; no src modified. Design-only — rung exits at designed.*
