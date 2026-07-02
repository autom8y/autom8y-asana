"""Necessity-rule constants for the onboarding walkthrough workflow.

Per PRD FR-2 / TDD §Data Model / ADR §4 (G-DENOM, positive enum gate):

``WALKTHROUGH_DECK_MAP`` enumerates ALL 18 live ``Calendar Provider`` enum
options (N0 live probe against Asana task ``1214919448732981``, 2026-06-27).
OPERATOR RULING (2026-07-02): the onboarding walkthrough is **UNIVERSAL** --
``email-forwarding-setup`` is the one customer-facing deck for EVERY ACTIVE
calendar-integration task, attached REGARDLESS of the Calendar Provider value
(the deck teaches the provider-agnostic appointments / email-forwarding flow;
the rep gates the send -- no per-provider discrimination yet). Per-provider
differentiation is DEFERRED (D-2), so the map is now DERIVED from a single named
default (``WALKTHROUGH_DECK_DEFAULT``) plus a sparse per-provider OVERRIDE seam
(``_PROVIDER_DECK_OVERRIDES``, EMPTY today) rather than 18 hand-assigned values
-- "universal" is stated ONCE and cannot drift. An override of ``None``
EXPLICITLY EXCLUDES a provider (no-op skip by construction); the internal
``ghl-calendar-setup`` deck is UNREACHABLE here (the default is customer,
overrides is empty, and the audience lock re-checks at build- and run-time).

``WALKTHROUGH_TRIGGER_VALUES`` is **derived** from the map (a provider triggers
a walkthrough iff it maps to a real deck). Deriving it guarantees the positive
gate and the deck lookup can never disagree.

The two producer deck templates that exist today are
``templates/email-forwarding-setup`` (audience: customer) and
``templates/ghl-calendar-setup`` (audience: internal); the map values are the
template *folder* names (the producer invoker prepends ``templates/``). Every
template dir is audience-classified by an owned manifest in
``deck_manifests/`` (completeness-enforced by test), and the workflow's 2b
AUDIENCE gate (the deck-audience lock) refuses any non-customer deck at the
attach seam -- DEFAULT-DENY: absence of a manifest IS denial.
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

# --- The universal deck (operator ruling 2026-07-02) ---
# The one customer-facing walkthrough deck for ACTIVE calendar-integration. Any
# resolvable provider with no explicit override resolves HERE (provider-agnostic:
# the deck teaches the same appointments / email-forwarding flow for everyone).
# MUST be classified audience=customer in deck_manifests/ -- enforced at build
# time (map-purity test) AND re-read at the 2b runtime gate. NEVER the internal
# ``ghl-calendar-setup`` deck.
WALKTHROUGH_DECK_DEFAULT: str = "email-forwarding-setup"

# --- Per-provider OVERRIDE seam (future D-2 differentiation; EMPTY today) ---
# Overrides RELATIVE to WALKTHROUGH_DECK_DEFAULT. The ruling is universal, so this
# is empty; a later D-2 differentiation edits ONLY this dict. Semantics:
#   * provider ABSENT here  -> resolves to WALKTHROUGH_DECK_DEFAULT (universal);
#   * provider -> "<deck>"   -> an ALTERNATE customer deck (still audience-gated);
#   * provider -> None       -> EXPLICITLY EXCLUDED (no-op skip, provider_unmapped).
# A non-customer deck placed here is rejected LOUDLY by the map-purity validator
# (assert_map_customer_only) at build time and by the 2b gate at runtime, so no
# override can ever reach the internal ``ghl-calendar-setup`` deck.
_PROVIDER_DECK_OVERRIDES: dict[str, str | None] = {}

# --- The necessity rule (G-DENOM): the closed enum of live Calendar Providers ---
# All 18 options from the N0 probe. This is the positive gate: only a KNOWN live
# provider value proceeds (a wholly-unknown value skips as provider_not_triggering).
# Ordered so the derived map materializes deterministically (stable diffs).
_ALL_PROVIDERS: tuple[str, ...] = (
    "Acuity",
    "Calendly",
    "ChiroHD",
    "ChiroTouch Cloud",
    "Elation",
    "Genesis",
    "GHL",
    "Google",
    "JaneApp",
    "PromptEMR",
    "ReviewWave",
    "SKED",
    "SimplePractice",
    "TrackStat",
    "Unify",
    "EHR → GCal",
    "Practice Better",
    "Outlook",
)

# The necessity rule, MATERIALIZED: every live provider -> its deck, DERIVED from
# the universal default + the (empty) override seam. Universal today: every
# provider maps to email-forwarding-setup. Any mapped (non-None) deck MUST be
# audience=customer (map-purity test) and is re-checked at runtime (2b gate).
WALKTHROUGH_DECK_MAP: dict[str, str | None] = {
    provider: _PROVIDER_DECK_OVERRIDES.get(provider, WALKTHROUGH_DECK_DEFAULT)
    for provider in _ALL_PROVIDERS
}

# Trigger set = providers with a non-None deck. Derived, so the two constants
# cannot drift (a provider is a trigger iff it maps to a real deck). Universal
# today: every provider triggers (no override excludes one yet).
WALKTHROUGH_TRIGGER_VALUES: frozenset[str] = frozenset(
    provider for provider, deck in WALKTHROUGH_DECK_MAP.items() if deck is not None
)
