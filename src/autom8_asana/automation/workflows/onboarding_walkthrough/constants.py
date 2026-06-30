"""Necessity-rule constants for the onboarding walkthrough workflow.

Per PRD FR-2 / TDD §Data Model / ADR §4 (G-DENOM, positive enum gate):

``WALKTHROUGH_DECK_MAP`` enumerates ALL 18 live ``Calendar Provider`` enum
options (N0 live probe against Asana task ``1214919448732981``, 2026-06-27).
The value->deck assignment is **PRODUCT-INPUT / PROBE-GATED** and is NOT
fabricated here: only ``GHL -> ghl-calendar-setup`` is semantically
unambiguous. The other 17 providers are explicit ``None`` placeholders -- a
provider mapped to ``None`` (or absent from the map) takes the no-op skip path
by construction.

``WALKTHROUGH_TRIGGER_VALUES`` is **derived** from the map (a provider triggers
a walkthrough iff it maps to a real deck). Deriving it guarantees the positive
gate and the deck lookup can never disagree.

The two producer deck templates that exist today are
``templates/email-forwarding-setup`` and ``templates/ghl-calendar-setup``; the
map values are the template *folder* names (the producer invoker prepends
``templates/``).
"""

from __future__ import annotations

# --- Feature flag (MC-2 #725 broad-rollout block: OPT-IN, defaults OFF) ---
# Unlike the opt-OUT sibling bridges, OnboardingWalkthroughWorkflow.validate_async
# OVERRIDES the base to require EXPLICIT enable (=true/1/yes/on). Unset/blank =>
# DISABLED, so dispatch-wiring can never make it fire by default before the pilot.
WALKTHROUGH_ENABLED_ENV_VAR = "AUTOM8_WALKTHROUGH_ENABLED"

# --- Producer location (CONFIG, never hardcoded to a worktree path) ---
# The Node >=22 producer directory (the sole freezer). In Lambda/ECS this is a
# bundled, writable path with a writable ``export/`` subdir (ADR-WALK-B2).
WALKTHROUGH_PRODUCER_DIR_ENV_VAR = "AUTOM8_WALKTHROUGH_PRODUCER_DIR"

# --- Onboarding project (N0 live probe 2026-06-27; PROBE-SOURCED, not invented) ---
# Asana project "Onboarding" GID. Sourced from the live probe, not fabricated.
# Overridable via constructor for test/non-prod targeting.
ONBOARDING_PROJECT_GID = "1201319387632570"

# --- Calendar-Integrations project (W3 batch-sweep enumeration target) ---
# The batch sweep enumerates the ACTIVE section of the Calendar-Integrations
# project. PROBE-SOURCED (R-1 census 2026-06-30): the project GID and its ACTIVE
# section (resolved BY NAME -- gid 1209442954085037 at probe time) were confirmed
# live; the GHL pilot task anchors a Business root at path_len=1. This GID lives
# in core/project_registry.py's _CONSUMER_WARM_SET_TIER_3_LIGHT (a cache-warming
# target) DELIBERATELY SEPARATE from the domain _REGISTRY, so it is referenced
# here as a named workflow-local constant rather than promoted into _REGISTRY:
# the enumeration needs only the GID string plus section-by-name resolution and
# never a registry-domain promotion (promoting would widen get_project_gid /
# all_entity_project_gids / parity -- project_registry.py:207-220). GFR's W1
# anchor walks parent chains structurally and never consults project_registry.
# Constructor-overridable on the workflow (two-way door with ONBOARDING_PROJECT_GID).
CALENDAR_INTEGRATIONS_PROJECT_GID = "1209442849265632"

# --- ACTIVE section name (W3; resolved BY NAME, never a hardcoded section GID) ---
# The active-set definition for THIS Calendar-Integrations sweep is the section
# literally named "ACTIVE", resolved via resolve_section_gids. This is NOT the
# Offers OFFER_CLASSIFIER (an Offers-domain activity classifier bound to the Offer
# project): importing it here would drag an Offers denominator into a
# Calendar-Integrations sweep (G-DENOM hygiene). A literal frozenset keeps the
# active-set definition local and explicit.
ACTIVE_SECTION_NAMES: frozenset[str] = frozenset({"ACTIVE"})

# --- Attachment naming (ADR-WALK-B1: unique-per-run, not a fixed name) ---
# A fixed ``walkthrough.html`` would be excluded from its own deletion by the
# AttachmentReplacementMixin (it excludes by name) and accumulate duplicates.
ATTACHMENT_GLOB = "walkthrough_*.html"

# --- W2 prior-harvest size cap (F5: bounded byte-harvest) ---
# The W2 idempotency check downloads each prior ``walkthrough_*.html`` to harvest
# its embedded routing-address guid. A walkthrough deck is a single-file inlined
# HTML -- tens to low-hundreds of KB, well under a megabyte even with inlined
# images. This cap (8 MiB, generous headroom) bounds that harvest: a prior larger
# than this is NOT a deck this workflow minted (a corrupt/foreign/oversized
# attachment that merely matches the glob), so it is skipped with a logged reason
# rather than pulled fully into memory. The cap is enforced BOTH up front (against
# the attachment's reported ``size``) AND mid-stream (a hard wall during download,
# in case ``size`` is absent or under-reports), so one oversized prior can never
# exhaust memory or abort the whole task's idempotency check.
MAX_PRIOR_DECK_BYTES = 8 * 1024 * 1024

# --- The necessity rule (G-DENOM) ---
# All 18 live Calendar Provider options. Deck assignment is PRODUCT-INPUT /
# PROBE-GATED (D-2) except GHL. Do NOT guess the 17 placeholders to a deck.
WALKTHROUGH_DECK_MAP: dict[str, str | None] = {
    "Acuity": None,  # PROBE-GATED / PRODUCT-INPUT
    "Calendly": None,  # PROBE-GATED / PRODUCT-INPUT
    "ChiroHD": None,  # PROBE-GATED / PRODUCT-INPUT
    "ChiroTouch Cloud": None,  # PROBE-GATED / PRODUCT-INPUT
    "Elation": None,  # PROBE-GATED / PRODUCT-INPUT
    "Genesis": None,  # PROBE-GATED / PRODUCT-INPUT
    "GHL": "ghl-calendar-setup",  # CANDIDATE -- unambiguous; product-confirm before live send
    "Google": None,  # PROBE-GATED / PRODUCT-INPUT
    "JaneApp": None,  # PROBE-GATED / PRODUCT-INPUT (pilot task value D-5; deck UNDETERMINED D-2)
    "PromptEMR": None,  # PROBE-GATED / PRODUCT-INPUT
    "ReviewWave": None,  # PROBE-GATED / PRODUCT-INPUT
    "SKED": None,  # PROBE-GATED / PRODUCT-INPUT
    "SimplePractice": None,  # PROBE-GATED / PRODUCT-INPUT
    "TrackStat": None,  # PROBE-GATED / PRODUCT-INPUT
    "Unify": None,  # PROBE-GATED / PRODUCT-INPUT
    "EHR → GCal": None,  # PROBE-GATED / PRODUCT-INPUT
    "Practice Better": None,  # PROBE-GATED / PRODUCT-INPUT
    "Outlook": None,  # PROBE-GATED / PRODUCT-INPUT
}

# Trigger set = providers with a non-None deck. Derived, so the two constants
# cannot drift (a provider is a trigger iff it maps to a real deck).
WALKTHROUGH_TRIGGER_VALUES: frozenset[str] = frozenset(
    provider for provider, deck in WALKTHROUGH_DECK_MAP.items() if deck is not None
)
