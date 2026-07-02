"""Selection constants for the onboarding walkthrough workflow.

**Provider-agnostic selection** (operator rulings, 2026-07-02). The
``Calendar Provider`` custom field on the Calendar-Integrations project
(``1209442849265632``) is a LIVE, operator-editable Asana field. Encoding its
options as a closed in-code enum was a recurring drift class: the field grew a
19th option, ``Direct``, that the stale 18-entry enum did not have, so the
selection gate silently dropped ``Direct`` (Sand Lake Dental) and would drop
ANY option added tomorrow (the 19-vs-18 drift). The fix removes the closed-enum
SELECTION GATE entirely: the provider value is now METADATA, not a gate.

Two rulings drive this:

* The **universal-deck ruling** -- ``email-forwarding-setup`` (audience:
  customer) is THE customer walkthrough deck for every ACTIVE calendar
  integration; the rep gates the send. There is no per-provider deck
  discrimination yet, so selection is provider-agnostic by default.
* The **Direct ruling** -- ``Direct`` is the **custom-integration class**
  (external direct-booking) which REQUIRES EmailNotificationForwarding so
  contente receives appointment data back; it MUST onboard, exactly like the
  **calendar-integration API-provider class** (Acuity/Calendly/GHL/...). BOTH
  classes onboard via ``email-forwarding-setup``.

So the deck is resolved provider-agnostically as
``WALKTHROUGH_DECK_OVERRIDES.get(provider, WALKTHROUGH_DECK_DEFAULT)``: ANY
present provider value (``Direct``, an API provider, or a value added tomorrow)
maps to the universal default customer deck. The REAL positive gates live
elsewhere -- ACTIVE-section membership (the enumeration), resolvable identity
(W1 GFR by-GUID, fail-closed), and the deck-audience lock (#191, the 2b runtime
gate). The denominator is now **ACTIVE ∩ resolvable**, NOT "provider ∈ closed
enum".

The producer deck templates that exist today are
``templates/email-forwarding-setup`` (audience: customer) and
``templates/ghl-calendar-setup`` (audience: internal, NEVER customer-facing);
the deck values here are template *folder* names (the producer invoker prepends
``templates/``). Every template dir is audience-classified by an owned manifest
in ``deck_manifests/`` (completeness-enforced by test), and the workflow's 2b
AUDIENCE gate refuses any non-customer deck at the attach seam -- DEFAULT-DENY:
absence of a manifest IS denial. ``WALKTHROUGH_DECK_DEFAULT`` MUST stay a
customer-classified deck (pinned by test) so the universal default can never
silently become an internal deck.
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

# --- Provider-agnostic deck selection (rulings 2026-07-02) ---
# The UNIVERSAL customer walkthrough deck. ANY present provider value resolves
# here unless an explicit override says otherwise. MUST be audience=customer
# (pinned by test + re-checked at runtime by the 2b deck-audience lock), so the
# universal default can never silently become an internal deck.
WALKTHROUGH_DECK_DEFAULT = "email-forwarding-setup"

# The D-2 discrimination seam (EMPTY today -- provider-agnostic by default).
# ``provider -> alternate customer deck`` remaps a specific provider to a
# DIFFERENT customer deck; ``provider -> None`` is an EXPLICIT exclusion (that
# provider SKIPS instead of onboarding). Resolution is
# ``WALKTHROUGH_DECK_OVERRIDES.get(provider, WALKTHROUGH_DECK_DEFAULT)``: an
# absent key falls to the universal default, a present key wins (deck or None).
# Every non-None override MUST be audience=customer (map-purity test + 2b gate).
# The code no longer GATES on any closed provider enum -- the live Asana field
# is the source of truth; adding a provider option needs NO code change here.
WALKTHROUGH_DECK_OVERRIDES: dict[str, str | None] = {}

# The currently-KNOWN Calendar-Provider options on the live Asana field (census
# 2026-07-02: 19 enabled options). This list is DOCUMENTATION ONLY -- the code
# does NOT gate on it, MUST NOT gate on it, and does not need updating when the
# operator adds an option. It exists to name the two onboarding classes; both
# onboard via ``WALKTHROUGH_DECK_DEFAULT``:
#   * calendar-integration API providers -- Acuity, Calendly, ChiroHD,
#     ChiroTouch Cloud, Elation, Genesis, GHL, Google, JaneApp, PromptEMR,
#     ReviewWave, SKED, SimplePractice, TrackStat, Unify, EHR → GCal,
#     Practice Better, Outlook;
#   * custom / direct-integration -- Direct (external direct-booking; the 19th
#     option the stale 18-entry enum was MISSING, the drift this fix kills).
# Selection is provider-agnostic: this list is deliberately NOT wired to any
# runtime branch (drift-proof by construction).
