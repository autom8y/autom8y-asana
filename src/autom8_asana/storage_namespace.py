"""StorageNamespaceContract — the single canonical registry of every autom8-s3
namespace the asana subsystem reads or writes.

This module is the SSOT (single source of truth) for the storage/config topology.
Settings prefix defaults, the Terraform ``namespaces.gen.json``, the
``DurableTaskCacheReader`` prefix pin, and the t1-t5 alignment tests ALL derive
from the registry declared here. The grandeur anchor: the wrong-prefix read
becomes STRUCTURALLY UNADDRESSABLE because no S3 prefix literal may live in
``src/`` outside this module (enforced by ``tests/arch/test_namespace_contract.py``
t3), and no IAM grant may point at an unregistered namespace (t2).

It was minted to dissolve the triple-defect saga's three masks (storage-topology
census ``.ledge/reviews/storage-topology-census-2026-06-10.md``):

* mask #1 — phantom S3 cold tier: a config field advertised a read tier wired
  nowhere. RETIRED (the ``TieredCacheProvider`` cold tier + ``s3_enabled`` flag
  are gone); the registry records the durable task cache as a WRITE-durable /
  EXPLICIT-read namespace whose blessed reader is ``DurableTaskCacheReader``.
* mask #2 — ``ASANA_CACHE_S3_PREFIX`` overload: one env fed two semantic planes.
  The registry binds ONE prefix per namespace; t3 forbids loose literals.
* mask #3 — IAM/namespace drift: grants evolved per-incident. The registry's
  ``iam_grants`` matrix is the derivation source for the generated TF JSON (t2
  enforces grant<->namespace alignment).

Behaviour-neutrality invariant (Phase-alpha): every value declared here is
BYTE-EQUAL to the corresponding live production literal (TF env blocks, Python
defaults, the cure's pinned prefix). Phase-alpha is derivation-neutral, NOT a
value-fix. Changing a runtime prefix VALUE is a separately-gated later decision.

Pure-stdlib by construction: this module imports nothing beyond ``dataclasses``
and ``enum`` so the TF generator (``scripts/gen_namespace_config.py``) can import
it without pulling the whole application stack.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

__all__ = [
    "CHECKPOINTS",
    "CHECKPOINTS_BULK",
    "CHECKPOINTS_SECTION_FAST",
    "DATAFRAMES_V2",
    "E2E_TEST_DATAFRAMES",
    "INSIGHTS_FRAMES_FOSSIL",
    "KNOWN_DRIFTS",
    "NAME_GID_MAPPINGS_FOSSIL",
    "PROJECT_FRAMES_FOSSIL",
    "REGISTRY",
    "REGISTRY_BY_NAME",
    "REGISTRY_NAMESPACE_COUNT",
    "TASK_CACHE",
    "TASK_CACHE_LEGACY_FOSSIL",
    "TASK_DATA_CACHE_V3_FOSSIL",
    "ASANA_CACHE_DATAFRAMES_FOSSIL",
    "IAMVerb",
    "IAMGrant",
    "KnownDrift",
    "Lifecycle",
    "SemanticPlane",
    "StorageNamespaceContract",
    "WriterOwner",
]


class Lifecycle(Enum):
    """The lifecycle state of a storage namespace.

    LIVE        — actively written and/or read by a current code path.
    FOSSIL      — write-orphaned; no current writer, stranded keys remain.
    QUARANTINED — held read-only pending an explicit operator disposition.
    PHANTOM      — config advertised a backend wired NOWHERE. After the O-C
                  retire there is no PHANTOM namespace; the enum member is kept
                  so t4 can assert the registry contains ZERO phantom rows.
    """

    LIVE = "live"
    FOSSIL = "fossil"
    QUARANTINED = "quarantined"
    PHANTOM = "phantom"


class IAMVerb(Enum):
    """S3 IAM actions, as they appear in a policy ``Action`` list."""

    GET = "s3:GetObject"
    PUT = "s3:PutObject"
    DELETE = "s3:DeleteObject"
    HEAD = "s3:HeadObject"
    LIST = "s3:ListBucket"


# Mutating verbs: a FOSSIL/QUARANTINED namespace must carry NONE of these in the
# registry's target-state matrix (t5). The live exception (warmer roles still
# grant PUT/DELETE on project-frames today) is recorded in KNOWN_DRIFTS, not
# fabricated away here.
_MUTATING_VERBS: frozenset[IAMVerb] = frozenset({IAMVerb.PUT, IAMVerb.DELETE})


class SemanticPlane(Enum):
    """The semantic plane a namespace serves.

    A plane is the *meaning* of the bytes at a prefix — distinct from the prefix
    string itself. Mask #2 was one env feeding two planes; the registry binds a
    plane per namespace so the overload cannot recur.
    """

    TASK_DURABLE_CACHE = "task-durable-cache"
    TASK_CACHE_LEGACY_PICKLE = "task-cache-legacy-pickle"
    TASK_EXPENSIVE_ATTRS_V3 = "task-expensive-attrs-v3"
    DATAFRAME_V2_GID_KEYED = "dataframe-v2-gid-keyed"
    DATAFRAME_V1_NAME_KEYED = "dataframe-v1-name-keyed"
    DATAFRAME_FLAT_LEGACY = "dataframe-flat-entity-gid-legacy"
    INSIGHTS_FRAMES = "insights-export-frames"
    NAME_GID_MAPPINGS = "name-gid-resolution"
    WARMER_CHECKPOINT = "warmer-checkpoint"
    E2E_TEST_FRAMES = "e2e-test-frames"


@dataclass(frozen=True)
class WriterOwner:
    """Who writes a namespace.

    ``repo`` is one of ``"autom8y-asana"``, ``"autom8"`` (the Go monolith), or the
    sentinel ``"EXTERNAL"``. ``code_anchor`` is the ``file:line`` of the writer
    construction site, or ``None`` when the writer is not located in this repo.
    ``external_name`` is a human-readable owner handle, required iff
    ``repo == "EXTERNAL"`` AND ``code_anchor is None`` (the DECLARED-UNKNOWN case);
    it is the honest tag for the WRITER-UNKNOWN discovery item (Phase-gamma gamma-0).
    """

    repo: str
    code_anchor: str | None
    external_name: str | None = None

    EXTERNAL: str = field(default="EXTERNAL", init=False, repr=False, compare=False)

    @property
    def is_attributed(self) -> bool:
        """True when the writer is pinned to a code anchor OR a named external owner.

        An UNATTRIBUTED namespace (no code anchor AND no external name) fails t1.
        This is the DECLARED-UNKNOWN guard: the registry may declare "we do not yet
        know" only by naming an external owner; it may NEVER leave a LIVE/FOSSIL
        namespace with no owner at all.
        """
        return self.code_anchor is not None or self.external_name is not None


@dataclass(frozen=True)
class IAMGrant:
    """An IAM grant: a principal ARN and the verbs it is allowed on the namespace.

    ``principal_arn`` is the role or user ARN. ``verbs`` is the TARGET-state verb
    set the contract declares for this principal on this namespace. Where live
    grants diverge from target state (e.g. fossil PUT/DELETE not yet removed), the
    divergence is recorded in ``KNOWN_DRIFTS`` — the registry records the TARGET,
    not a fabricated picture of live.
    """

    principal_arn: str
    verbs: tuple[IAMVerb, ...]


@dataclass(frozen=True)
class KnownDrift:
    """A declared divergence between the registry's TARGET state and live reality.

    Lets t5 pass HONESTLY: the registry's IAM matrix records the target (FOSSIL ->
    no PUT/DELETE) while this entry records the live exception with a remediation
    pointer, so we never lie about the live grant.
    """

    namespace_name: str
    description: str
    remediation_pointer: str


@dataclass(frozen=True)
class StorageNamespaceContract:
    """The storage contract for ONE autom8-s3 namespace.

    Every attribute is a derivation source. The prefix feeds settings defaults and
    the TF gen JSON; the IAM grants feed the TF IAM resources; the lifecycle gates
    the FOSSIL/PHANTOM alignment tests.
    """

    # --- identity ---
    name: str
    prefix: str
    # --- semantic plane ---
    semantic_plane: SemanticPlane
    # --- ownership ---
    writer_owner: WriterOwner
    reader_apis: tuple[str, ...]
    # --- config surface ---
    env_vars: tuple[str, ...]
    env_default: str | None
    # --- IAM ---
    iam_grants: tuple[IAMGrant, ...]
    # --- lifecycle ---
    lifecycle: Lifecycle
    lifecycle_note: str = ""


# ===========================================================================
# THE REGISTRY — 11 namespaces from the A1 live census (2026-06-10).
#
# Values are BYTE-EQUAL to live (Phase-alpha derivation-neutrality). The IAM
# principal ARN is the warmer-lane role; the ECS full-bucket grant is recorded as
# a note (its narrowing is the Phase-beta beta-3 target, gated on enumerating the
# receiver write surface first).
# ===========================================================================

_WARMER_ROLE_ARN = "arn:aws:iam::696318035277:role/autom8-asana-cache-warmer-lambda-role"
_MONOLITH_USER_ARN = "arn:aws:iam::696318035277:user/autom8"

_WARMER_FULL_VERBS = (IAMVerb.GET, IAMVerb.PUT, IAMVerb.DELETE, IAMVerb.HEAD)


# --- LIVE: namespace #1 — the durable per-task cache (385k keys) ----------------
TASK_CACHE = StorageNamespaceContract(
    name="TASK_CACHE",
    prefix="asana-cache",
    semantic_plane=SemanticPlane.TASK_DURABLE_CACHE,
    writer_owner=WriterOwner(
        # WRITER-UNATTRIBUTED (the gamma-0 discovery item). A1's
        # autom8_adapter.py:300 attribution is REFUTED by A2 (that path builds a
        # Redis provider, provider-agnostic set_versioned). No prod
        # S3CacheProvider construction site exists in this repo. The honest tag is
        # UNATTRIBUTED: we declare an external owner placeholder but pin NO code
        # anchor and NO fabricated provenance handle (the main.tf:1218 comment was
        # adversary-verified absent from live TF — never cited here).
        repo=WriterOwner.EXTERNAL,
        code_anchor=None,
        external_name="UNATTRIBUTED (durable-first writer; Phase-gamma gamma-0 discovery)",
    ),
    reader_apis=(
        # The #121 cure — the blessed explicit reader (DurableTaskCacheReader),
        # consumed by null_number_recovery's cold-tier fill.
        "cache/durable_task_cache.py:DurableTaskCacheReader.read_batch",
        "dataframes/builders/null_number_recovery.py:_cold_read_durable (delegates to reader)",
        # The Python default-declaration sites for the unadorned `asana-cache`
        # prefix (the env_default below). These are the canonical declaration
        # anchors t3 allowlists — the value is DEFINED here, not loosely duplicated.
        "settings.py:430",  # S3Settings.prefix default = "asana-cache"
        "cache/backends/s3.py:56",  # S3Config.prefix default = "asana-cache"
    ),
    env_vars=("ASANA_CACHE_S3_PREFIX",),
    env_default="asana-cache",
    iam_grants=(
        # The #481 grant: read-only GET on tasks/* so the cure can read the durable
        # per-task copies. (Codified live; this checkout's TF predates the Sid.)
        IAMGrant(_WARMER_ROLE_ARN, (IAMVerb.GET,)),
    ),
    lifecycle=Lifecycle.LIVE,
    lifecycle_note=(
        "WRITE-durable / EXPLICIT-read namespace. The blessed read API is "
        "DurableTaskCacheReader (raw boto3 get_object of {prefix}/tasks/{gid}/"
        "task.json + .gz fallback). There is NO S3 cold cache tier — the phantom "
        "was retired (mask #1). The ECS task role holds full-bucket autom8-s3/* "
        "today; narrowing is the Phase-beta beta-3 operator-gated target."
    ),
)

# --- LIVE: namespace #3 — top-level v2 entity-keyed dataframes (1,025 keys) ------
DATAFRAMES_V2 = StorageNamespaceContract(
    name="DATAFRAMES_V2",
    prefix="dataframes/",
    semantic_plane=SemanticPlane.DATAFRAME_V2_GID_KEYED,
    writer_owner=WriterOwner(
        repo="autom8y-asana",
        code_anchor="dataframes/storage.py:342",  # S3DataFrameStorage default prefix
        external_name=None,
    ),
    reader_apis=(
        "api/preload/legacy.py:125",
        "api/preload/progressive.py:291",
        "dataframes/section_persistence.py:1045",
        "dataframes/offline.py:49",
        "scripts/warm_cache.py:78",
        # Additional reader/metrics sites that reference the "dataframes/" prefix
        # literal — registered so t3 accounts for every site touching this plane.
        "metrics/__main__.py:780",
        "metrics/freshness.py:281",
    ),
    # Hardcoded constructor default; no live env override (the cure-by-construction).
    env_vars=(),
    env_default="dataframes/",
    iam_grants=(IAMGrant(_WARMER_ROLE_ARN, _WARMER_FULL_VERBS),),
    lifecycle=Lifecycle.LIVE,
    lifecycle_note="the coherent=561 plane; prefix is a constructor default, env-disconnected.",
)

# --- LIVE: namespace #4 — warmer checkpoints, three lanes -----------------------
# The default lane (env unset -> DEFAULT_PREFIX) and the two per-lane disjoint
# prefixes the TF sets for the bulk and section-fast warmer functions. Modeled as
# three rows (parent + two children) so the gen JSON carries each lane's env value
# byte-equal to TF, and so prefix-shadowing is an explicit parent-child relation.
CHECKPOINTS = StorageNamespaceContract(
    name="CHECKPOINTS",
    prefix="cache-warmer/checkpoints/",
    semantic_plane=SemanticPlane.WARMER_CHECKPOINT,
    writer_owner=WriterOwner(
        repo="autom8y-asana",
        code_anchor="lambda_handlers/checkpoint.py:31",  # DEFAULT_PREFIX
        external_name=None,
    ),
    reader_apis=("lambda_handlers/checkpoint.py:_default_prefix",),
    env_vars=("CACHE_WARMER_CHECKPOINT_PREFIX",),
    env_default="cache-warmer/checkpoints/",
    iam_grants=(IAMGrant(_WARMER_ROLE_ARN, _WARMER_FULL_VERBS),),
    lifecycle=Lifecycle.LIVE,
    lifecycle_note="default lane (env unset -> DEFAULT_PREFIX). Parent of the bulk/section lanes.",
)

CHECKPOINTS_BULK = StorageNamespaceContract(
    name="CHECKPOINTS_BULK",
    prefix="cache-warmer/checkpoints/bulk/",
    semantic_plane=SemanticPlane.WARMER_CHECKPOINT,
    writer_owner=WriterOwner(
        repo="autom8y-asana",
        code_anchor="lambda_handlers/checkpoint.py:39",  # CHECKPOINT_PREFIX_ENV resolver
        external_name=None,
    ),
    reader_apis=("lambda_handlers/checkpoint.py:_default_prefix",),
    env_vars=("CACHE_WARMER_CHECKPOINT_PREFIX",),
    env_default="cache-warmer/checkpoints/bulk/",  # TF bulk lane literal
    iam_grants=(IAMGrant(_WARMER_ROLE_ARN, _WARMER_FULL_VERBS),),
    lifecycle=Lifecycle.LIVE,
    lifecycle_note="bulk pre-warmer lane; disjoint per #96 so concurrent runs never collide.",
)

CHECKPOINTS_SECTION_FAST = StorageNamespaceContract(
    name="CHECKPOINTS_SECTION_FAST",
    prefix="cache-warmer/checkpoints/section-fast/",
    semantic_plane=SemanticPlane.WARMER_CHECKPOINT,
    writer_owner=WriterOwner(
        repo="autom8y-asana",
        code_anchor="lambda_handlers/checkpoint.py:39",
        external_name=None,
    ),
    reader_apis=("lambda_handlers/checkpoint.py:_default_prefix",),
    env_vars=("CACHE_WARMER_CHECKPOINT_PREFIX",),
    env_default="cache-warmer/checkpoints/section-fast/",  # TF section lane literal
    iam_grants=(IAMGrant(_WARMER_ROLE_ARN, _WARMER_FULL_VERBS),),
    lifecycle=Lifecycle.LIVE,
    lifecycle_note="section-fast warmer lane; disjoint per #96.",
)

# --- LIVE: namespace #11 — e2e test frames (root-level) -------------------------
E2E_TEST_DATAFRAMES = StorageNamespaceContract(
    name="E2E_TEST_DATAFRAMES",
    prefix="e2e-test-dataframes/",
    semantic_plane=SemanticPlane.E2E_TEST_FRAMES,
    writer_owner=WriterOwner(
        repo="autom8y-asana",
        code_anchor=None,
        external_name="e2e test harness (non-prod)",
    ),
    reader_apis=(),
    env_vars=(),
    env_default="e2e-test-dataframes/",
    iam_grants=(),
    lifecycle=Lifecycle.LIVE,
    lifecycle_note="test-scoped; not a prod namespace, no prod grant.",
)

# --- FOSSIL: namespace #2 — v1 name-keyed dataframe frames (2,243 keys) ----------
PROJECT_FRAMES_FOSSIL = StorageNamespaceContract(
    name="PROJECT_FRAMES_FOSSIL",
    prefix="asana-cache/project-frames/",
    semantic_plane=SemanticPlane.DATAFRAME_V1_NAME_KEYED,
    writer_owner=WriterOwner(
        repo=WriterOwner.EXTERNAL,
        code_anchor=None,
        external_name="autom8-monolith-v1 (last write 2025-10-02; 8mo stale)",
    ),
    reader_apis=(),  # zero readers
    # The overloaded fossil env: ASANA_CACHE_S3_PREFIX points HERE in prod TF
    # (value asana-cache/project-frames/). Recorded so the gen JSON emits the
    # fossil value byte-equal (Phase-alpha is derivation-neutral, not a value fix).
    env_vars=("ASANA_CACHE_S3_PREFIX",),
    env_default="asana-cache/project-frames/",
    # TARGET state: read-only/none. The live warmer grant still has PUT/DELETE here
    # (KNOWN_DRIFTS), removed under Phase-beta beta-2.
    iam_grants=(IAMGrant(_WARMER_ROLE_ARN, (IAMVerb.GET,)),),
    lifecycle=Lifecycle.FOSSIL,
    lifecycle_note=(
        "v1 name-keyed schema; 2,243 stranded keys; last write 2025-10-02; no "
        "reader in any repo. The env value is the OVERLOADED ASANA_CACHE_S3_PREFIX "
        "(mask #2). TARGET grant is read-only; live PUT/DELETE drift is in KNOWN_DRIFTS."
    ),
)

# --- FOSSIL: namespace #6 — legacy pickle task cache (128,583 keys) -------------
TASK_CACHE_LEGACY_FOSSIL = StorageNamespaceContract(
    name="TASK_CACHE_LEGACY_FOSSIL",
    prefix="asana-cache/task-cache/",
    semantic_plane=SemanticPlane.TASK_CACHE_LEGACY_PICKLE,
    writer_owner=WriterOwner(
        repo=WriterOwner.EXTERNAL,
        code_anchor=None,
        external_name="autom8-monolith-legacy-pickle (no repo writer; AP-7 owner TBD at gamma)",
    ),
    reader_apis=(),
    env_vars=(),
    env_default=None,
    iam_grants=(IAMGrant(_MONOLITH_USER_ARN, (IAMVerb.GET,)),),  # target read-only
    lifecycle=Lifecycle.FOSSIL,
    lifecycle_note=(
        "legacy pickle format ({prefix}tasks/<gid>/data.pkl); 128,583 keys; no repo "
        "writer; written by the autom8 IAM super-user under the full-bucket policy. "
        "AP-7: owner-TBD at Phase-gamma. Pickle deserialization surface referred to "
        "security cross-rite (TDD section 8)."
    ),
)

# --- FOSSIL: namespace #7 — v3 expensive-attr cache (342 keys) ------------------
TASK_DATA_CACHE_V3_FOSSIL = StorageNamespaceContract(
    name="TASK_DATA_CACHE_V3_FOSSIL",
    prefix="asana-cache/task-data-cache-v3/",
    semantic_plane=SemanticPlane.TASK_EXPENSIVE_ATTRS_V3,
    writer_owner=WriterOwner(
        repo=WriterOwner.EXTERNAL,
        code_anchor=None,
        external_name="autom8-monolith (no repo writer)",
    ),
    reader_apis=(),
    env_vars=(),
    env_default=None,
    iam_grants=(IAMGrant(_MONOLITH_USER_ARN, (IAMVerb.GET,)),),
    lifecycle=Lifecycle.FOSSIL,
    lifecycle_note="v3 expensive-attr pickle cache; 342 keys; no repo writer.",
)

# --- FOSSIL: namespace #8 — insights export frames (13,448 keys) ----------------
INSIGHTS_FRAMES_FOSSIL = StorageNamespaceContract(
    name="INSIGHTS_FRAMES_FOSSIL",
    prefix="asana-cache/insights-frames/",
    semantic_plane=SemanticPlane.INSIGHTS_FRAMES,
    writer_owner=WriterOwner(
        repo=WriterOwner.EXTERNAL,
        code_anchor=None,
        external_name="autom8-asana-insights-export-lambda (probable; policy uncensused per A1)",
    ),
    reader_apis=(),
    env_vars=(),
    env_default=None,
    iam_grants=(IAMGrant(_MONOLITH_USER_ARN, (IAMVerb.GET,)),),
    lifecycle=Lifecycle.FOSSIL,
    lifecycle_note=(
        "insights-export frames; 13,448 keys; LIVE-written by an external lambda but "
        "FOSSIL from this repo's perspective (no repo reader/writer). The exact "
        "writer role is uncensused (A1 EXCLUSIONS #2)."
    ),
)

# --- FOSSIL: namespace #9 — name<->gid resolution mappings (6 keys) -------------
NAME_GID_MAPPINGS_FOSSIL = StorageNamespaceContract(
    name="NAME_GID_MAPPINGS_FOSSIL",
    prefix="asana-cache/name-gid-mappings/",
    semantic_plane=SemanticPlane.NAME_GID_MAPPINGS,
    writer_owner=WriterOwner(
        repo=WriterOwner.EXTERNAL,
        code_anchor=None,
        external_name="autom8-monolith (no repo writer)",
    ),
    reader_apis=(),
    env_vars=(),
    env_default=None,
    iam_grants=(IAMGrant(_MONOLITH_USER_ARN, (IAMVerb.GET,)),),
    lifecycle=Lifecycle.FOSSIL,
    lifecycle_note="name<->gid resolution pickles; 6 keys; no repo writer.",
)

# --- FOSSIL: namespace #10 — flat entity:gid frames under asana-cache (6 keys) --
ASANA_CACHE_DATAFRAMES_FOSSIL = StorageNamespaceContract(
    name="ASANA_CACHE_DATAFRAMES_FOSSIL",
    prefix="asana-cache/dataframes/",
    semantic_plane=SemanticPlane.DATAFRAME_FLAT_LEGACY,
    writer_owner=WriterOwner(
        repo=WriterOwner.EXTERNAL,
        code_anchor=None,
        external_name="autom8-monolith-legacy (no repo writer; distinct from top-level dataframes/)",
    ),
    reader_apis=(),
    env_vars=(),
    env_default=None,
    iam_grants=(IAMGrant(_MONOLITH_USER_ARN, (IAMVerb.GET,)),),
    lifecycle=Lifecycle.FOSSIL,
    lifecycle_note=(
        "flat entity:gid frames UNDER asana-cache (distinct from the LIVE top-level "
        "dataframes/ namespace); 6 keys; low-confidence row (A1 grep-only + layout)."
    ),
)

# Note on the Redis hot tier (census #5) and the retired phantom (census #5p):
# Redis is the REAL hot store but is NOT an S3 namespace, so it has no registry
# row (it carries no S3 prefix and no S3 IAM grant — out of the S3 namespace
# matrix by construction). The phantom S3 cold tier (#5p) is RETIRED: there is no
# Lifecycle.PHANTOM row in the registry, which is precisely what t4 asserts.


REGISTRY: tuple[StorageNamespaceContract, ...] = (
    TASK_CACHE,
    DATAFRAMES_V2,
    CHECKPOINTS,
    CHECKPOINTS_BULK,
    CHECKPOINTS_SECTION_FAST,
    E2E_TEST_DATAFRAMES,
    PROJECT_FRAMES_FOSSIL,
    TASK_CACHE_LEGACY_FOSSIL,
    TASK_DATA_CACHE_V3_FOSSIL,
    INSIGHTS_FRAMES_FOSSIL,
    NAME_GID_MAPPINGS_FOSSIL,
    ASANA_CACHE_DATAFRAMES_FOSSIL,
)

# The pinned namespace COUNT. A hand-added 12th namespace without registration in
# REGISTRY (or a removal) trips t1's count assertion. (12 = 10 S3 namespaces from
# the A1 census that carry an S3 prefix + the 2 extra checkpoint lanes modeled
# faithfully per the TF; the Redis row and the retired phantom carry no S3 prefix
# and are intentionally absent.)
REGISTRY_NAMESPACE_COUNT = 12

REGISTRY_BY_NAME: dict[str, StorageNamespaceContract] = {ns.name: ns for ns in REGISTRY}


# Declared TARGET-vs-live divergences. t5 uses these to pass HONESTLY: the registry
# records the target (FOSSIL -> no mutating verbs) while these record the live
# exception with a Phase-beta remediation pointer.
KNOWN_DRIFTS: tuple[KnownDrift, ...] = (
    KnownDrift(
        namespace_name="PROJECT_FRAMES_FOSSIL",
        description=(
            "Live warmer-lane roles still grant PUT/DELETE/HEAD on "
            "asana-cache/project-frames/* (S3CacheAccess Sid) although the namespace "
            "is FOSSIL (write-orphaned, last write 2025-10-02). The registry records "
            "the TARGET grant (read-only GET); the live PUT/DELETE is the drift."
        ),
        remediation_pointer="Phase-beta beta-2 (fossil grant removal); TDD section 5 Phase-beta.",
    ),
)


# ===========================================================================
# Registry invariants — enforced at import time (cheap structural guards) AND
# by the t1-t5 alignment tests. Failing here means the registry is internally
# inconsistent (a developer error), independent of the alignment tests.
# ===========================================================================


def _validate_registry() -> None:
    """Validate the registry's internal structural invariants at import time.

    Cheap O(n) checks that catch a malformed registry edit immediately, before any
    derivation runs. The t1-t5 tests are the CI-enforced contract; this is the
    fail-fast developer guard.
    """
    # Count matches the pinned count.
    if len(REGISTRY) != REGISTRY_NAMESPACE_COUNT:
        raise ValueError(
            f"REGISTRY has {len(REGISTRY)} namespaces but REGISTRY_NAMESPACE_COUNT "
            f"is pinned at {REGISTRY_NAMESPACE_COUNT}. A namespace was added/removed "
            "without updating the pinned count (see t1)."
        )

    # Unique names and unique prefixes.
    names = [ns.name for ns in REGISTRY]
    if len(set(names)) != len(names):
        raise ValueError(f"Duplicate namespace name(s) in REGISTRY: {names}")
    prefixes = [ns.prefix for ns in REGISTRY]
    if len(set(prefixes)) != len(prefixes):
        raise ValueError(f"Duplicate prefix(es) in REGISTRY: {prefixes}")

    # No prefix shadows another unless the shadowing is an EXPLICIT parent-child
    # relation. Two such relations are declared and structurally faithful:
    #   * "cache-warmer/checkpoints/" is the parent of the bulk/ and section-fast/
    #     lanes (the default lane is the umbrella; the lanes nest beneath it).
    #   * "asana-cache" (TASK_CACHE) is the unadorned umbrella of the asana-cache/*
    #     namespace FAMILY. TASK_CACHE's effective keyspace is the DISJOINT child
    #     "asana-cache/tasks/" (its key-builder appends "/tasks/{gid}/task.json");
    #     it NEVER reads the bare root, so it does not straddle the fossil siblings
    #     (project-frames/, task-cache/, task-data-cache-v3/, insights-frames/,
    #     name-gid-mappings/, dataframes/). This umbrella relation IS mask #2 made
    #     explicit: one root prefix family, disjoint child keyspaces per namespace.
    # Any OTHER shadow is a structural ambiguity (a read of the parent prefix would
    # straddle the child namespace) and is rejected.
    allowed_parents = {
        "cache-warmer/checkpoints/",  # parent of bulk/ and section-fast/
        "asana-cache",  # umbrella of the asana-cache/* family (tasks/ + fossils)
    }
    for a in REGISTRY:
        for b in REGISTRY:
            if a is b:
                continue
            shadows = b.prefix.startswith(a.prefix) and a.prefix != b.prefix
            if shadows and a.prefix not in allowed_parents:
                raise ValueError(
                    f"Prefix shadowing: {b.name!r} ({b.prefix!r}) nests under "
                    f"{a.name!r} ({a.prefix!r}) but {a.prefix!r} is not a declared "
                    "parent. Declare the parent-child relation or disambiguate."
                )

    # FOSSIL/QUARANTINED namespaces must be documented (non-empty lifecycle_note).
    for ns in REGISTRY:
        if ns.lifecycle in (Lifecycle.FOSSIL, Lifecycle.QUARANTINED) and not ns.lifecycle_note:
            raise ValueError(
                f"{ns.name!r} is {ns.lifecycle.value} but has no lifecycle_note "
                "(FOSSIL => documented)."
            )


_validate_registry()
