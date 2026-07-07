"""Runtime tenant-binding assertion (T7) -- the runtime analogue of the byte-exact oracle.

The onboarding-walkthrough resolve->freeze path (``workflow.process_entity``)
resolves a single canonical routing address from the office phone (B1, the sole
address source) and hands it to the Node producer to freeze into the deck. The
producer already fail-closes on *absence* (``producer.freeze_walkthrough_deck``
raises ``ProducerFreezeError`` when the resolved address is not a substring of
the frozen bytes). That is a **presence** check only.

This module adds the missing **exclusivity** half: it harvests *every* canonical
routing address embedded in the frozen bytes and asserts the harvested set is
EXACTLY ``{gated_address}`` -- the resolved address is present AND nothing else
is. A frozen deck that carries the resolved address *plus* a stale/hardcoded
second-tenant address (a producer-side injection drift, or a template that
embeds a literal foreign routing address) passes the producer's substring
presence check yet leaks a wrong tenant into the artifact the client receives.
Set-equality is the runtime analogue of the byte-exact harvest oracle used in
the deck tests: presence + exclusivity in one predicate.

This is the producer-side complement to the resolve-side guard. The wrong-tenant
RESOLVE is prevented upstream in autom8y-data: the office_phone -> guid hop runs
through ``BusinessRepository._single_business_or_raise`` (a colliding phone
fail-closes with ``OfficePhoneCollisionError`` -> HTTP 409 / DATA-CONFLICT-002 ->
``DataServiceUnavailableError`` at the workflow boundary, so no wrong-tenant
address is ever minted). This module ensures the frozen *artifact* matches the
address that resolve produced -- no producer-side drift between resolve and
freeze.

Siting (why a dedicated module, not ``producer.py``): the producer module is
contractually forbidden from reimplementing the canonical-address form in Python
(it does a raw-substring presence check precisely to avoid owning a Python
``CANONICAL_ADDR_RE``). This oracle is a *verifier*, not the freezer, so the
canonical-address pattern lives here -- mirroring the harvest oracle the deck
tests already use -- keeping the producer regex-free.

Deck-template precondition (NOTE, pre-flip verification): a deck template MUST
NOT embed a literal ``{uuid}@appointments.contenteapp.com`` string other than the
injection slot the producer replaces (the injection placeholder must itself be
non-canonical). A template that hardcodes an example canonical routing address
would make every frozen deck carry a second address and this assertion would
(correctly) refuse it. The walkthrough ships opt-in / OFF-by-default
(``AUTOM8_WALKTHROUGH_ENABLED``); verify the live templates carry no static
canonical routing address before enabling the pilot.
"""

from __future__ import annotations

import re

from autom8y_core.helpers.routing import format_routing_address

# The canonical routing-address form: a 36-char UUID (32 hex + 4 hyphens) at the
# ``@appointments.contenteapp.com`` routing domain. Mirrors the harvest oracle in
# tests/unit/automation/workflows/test_onboarding_walkthrough.py. The negative
# lookbehind ensures we harvest a *complete* address, not a hex suffix of a longer
# run (which would be non-canonical anyway).
#
# Case-INSENSITIVE (``re.IGNORECASE``): the canonical form is lowercase, enforced
# UPSTREAM by the producer's ``CANONICAL_ADDR_RE`` and the DB's lowercase v4 guids.
# This module is the producer-side VERIFIER, not the minter -- it must FAIL-CLOSED on a
# non-canonical case-variant, never fail-OPEN by failing to SEE it. A lowercase-only
# class would let an uppercase-hex foreign address embedded in a deck template (the
# pre-flip manual-NOTE hazard documented above) slip past ``findall`` invisibly; matching
# case-insensitively HARVESTS the variant so the exclusivity set-equality below (which
# normalizes to lowercase) catches it. Harvest wider, then bind exactly -- never the
# reverse. This does not weaken the canonical contract: the producer still mints
# lowercase-only; the verifier merely refuses to be blind to a variant.
CANONICAL_ROUTING_ADDR_RE = re.compile(
    r"(?<![0-9a-f-])[0-9a-f-]{36}@appointments\.contenteapp\.com",
    re.IGNORECASE,
)


class TenantBindingError(RuntimeError):
    """Raised when a frozen deck's embedded routing address(es) do not bind
    EXACTLY to the single resolved tenant address.

    Covers both arms of the byte-exact oracle:
      * the resolved address is absent from the frozen bytes (presence), and
      * the frozen bytes carry any OTHER canonical routing address (exclusivity).

    A tenant-binding violation is NOT transient: re-running resolve+freeze on a
    template that embeds a foreign address, or a producer that drifts, will
    reproduce it. Callers MUST fail closed (refuse to attach) rather than retry.
    """


def harvest_routing_addresses(frozen: bytes) -> set[str]:
    """Harvest the distinct set of canonical routing addresses in the frozen bytes.

    Decodes defensively (``errors="replace"`` -- an invalid byte becomes U+FFFD,
    which is not in the address character class and so acts as a separator, never
    bridging two hex runs into a spurious match). Returns the DISTINCT set, so a
    legitimate deck that renders the same resolved address in several places
    (mailto link, display text, hidden field) collapses to a single element.

    Args:
        frozen: the frozen deck bytes returned by the Node producer.

    Returns:
        The set of distinct canonical routing-address strings present.
    """
    text = frozen.decode("utf-8", errors="replace")
    return set(CANONICAL_ROUTING_ADDR_RE.findall(text))


def _mask_addr(addr: str) -> str:
    """Mask a routing address to its first 8 hex chars + domain (forensic breadcrumb).

    Enough to identify the implicated tenant against the DB during an incident,
    without spilling a full (wrong-)tenant routing address into logs/errors.
    """
    local, _, domain = addr.partition("@")
    return f"{local[:8]}…@{domain}" if domain else f"{addr[:8]}…"


def assert_exclusive_tenant_binding(*, frozen: bytes, gated_address: str) -> None:
    """Assert the frozen deck binds to EXACTLY the resolved routing address.

    The runtime analogue of the byte-exact oracle: the set of canonical routing
    addresses harvested from ``frozen`` MUST equal ``{gated_address}`` -- presence
    (the resolved address is in the deck) AND exclusivity (no other routing
    address is). Fail-closed: raise ``TenantBindingError`` on any mismatch.

    Args:
        frozen: the frozen deck bytes (post-producer-freeze).
        gated_address: the single canonical address resolved by B1 (the producer
            already guarantees this is canonical and present as a substring; this
            oracle re-affirms presence and adds exclusivity, self-contained).

    Raises:
        TenantBindingError: if the resolved address is absent, or any foreign
            canonical routing address is present, in the frozen bytes.
    """
    # Case-fold the comparison at the guard boundary: canonical routing addresses are
    # lowercase by construction (producer ``CANONICAL_ADDR_RE`` + DB v4 guids). Normalizing
    # BOTH the harvested set AND the gated address to lowercase means a case-variant FOREIGN
    # address (now harvested via ``re.IGNORECASE``) is caught as a distinct member
    # (set != {gated} -> RED), WHILE a case-variant of the RESOLVED address collapses onto
    # it and does NOT false-RED. This never weakens the canonical contract -- the producer
    # still mints lowercase-only -- it only ensures a non-canonical variant fails CLOSED
    # here instead of riding along silently. The masked breadcrumb is likewise normalized,
    # which is correct: the DB stores lowercase guids, so the lowercased prefix is the form
    # an operator matches against during an incident.
    gated_norm = gated_address.lower()
    harvested = {addr.lower() for addr in harvest_routing_addresses(frozen)}
    if harvested == {gated_norm}:
        return

    resolved_present = gated_norm in harvested
    foreign = sorted(harvested - {gated_norm})
    raise TenantBindingError(
        "frozen deck tenant-binding violation: expected exactly the resolved "
        f"routing address; resolved_present={resolved_present}, "
        f"distinct_addresses={len(harvested)}, "
        f"foreign={[_mask_addr(a) for a in foreign]}"
    )


class TemplateTenantMismatch(RuntimeError):
    """Raised when a composed carrier-email text carries a routing address that is NOT
    this office's own (a foreign-tenant leak), or when the office guid is malformed so
    an own address cannot even be computed (fail-closed on a bad anchor).

    The v3 carrier analogue of :class:`TenantBindingError`, applied to the
    email-composition surface rather than the frozen deck bytes. NOT transient: a
    foreign address / bad guid reproduces on re-run. Callers MUST fail closed (refuse
    to post/send), never retry.
    """


class TaskOfficeMismatch(TemplateTenantMismatch):
    """Raised when an explicitly-supplied ``office_guid`` does not equal the guid resolved
    from the TASK it is being posted onto -- a ``(office_guid, task_gid)`` pairing that
    binds one office's routing address to ANOTHER office's PLAY (the cross-tenant leak).

    The task-ownership analogue of :class:`TemplateTenantMismatch`: where the parent guards
    the composed-text-vs-guid consistency, this guards the guid-vs-task ownership. It is a
    :class:`TemplateTenantMismatch` subclass so a caller catching the tenant-mismatch family
    (and the CLI's fail-closed handler) already covers it. NOT transient: a mis-paired
    ``(guid, task)`` reproduces on re-run. Callers MUST fail closed (refuse to post), never
    retry -- in a batch loop this is a real client told to forward bookings into a foreign
    tenant's inbox.
    """


def assert_template_tenant_match(*, composed_text: str, office_guid: str) -> None:
    """Assert every routing address in ``composed_text`` is THIS office's own.

    The carrier-email analogue of :func:`assert_exclusive_tenant_binding` MINUS the
    presence half. The v3 template SHOULD carry the office's own routing address, but a
    valid re-send MAY omit it -- so this is a SUBSET (no-foreign) predicate, not
    set-equality. Harvest every ``{uuid}@appointments.contenteapp.com`` via
    :data:`CANONICAL_ROUTING_ADDR_RE`; refuse fail-closed if any harvested address is
    not ``format_routing_address(office_guid)`` -- the leak-by-containment crown-jewel.

    Predicate: ``harvested - {own} == set()``. Presence of ``own`` is permitted
    (expected); absence of any address is permitted (a valid re-send); presence of any
    address != ``own`` is REFUSED.

    Why SUBSET, not EQUALITY (the deliberate difference from the deck guard):
    :func:`assert_exclusive_tenant_binding` requires ``harvested == {gated}`` --
    presence AND exclusivity -- because the deck's whole purpose is to carry exactly
    that address (a deck missing it is a broken product). The template email only SHOULD
    carry it, so this guard keeps only the exclusivity/leak half; presence is a checklist
    SHOULD (spec §5), not a guard MUST.

    Args:
        composed_text: the fully composed carrier-email text (post-compose).
        office_guid: this office's guid (its Company ID). MUST be a canonical lowercase
            UUID v4 -- ``format_routing_address`` raises ``ValueError`` on a malformed
            guid, which this guard wraps as a fail-closed :class:`TemplateTenantMismatch`
            (a bad anchor can never yield a tenant-matched send).

    Raises:
        TemplateTenantMismatch: on any foreign routing address (the leak arm), OR a
            malformed office guid (the bad-anchor arm; the wrapped ``ValueError`` is
            preserved as ``__cause__``).
    """
    try:
        own = format_routing_address(office_guid)
    except ValueError as exc:
        # Bad-anchor arm: cannot compute this office's own address, so no send can be
        # tenant-matched. Fail closed -- never fall open on a malformed guid.
        raise TemplateTenantMismatch(
            f"cannot compute own routing address: malformed office guid ({exc})"
        ) from exc

    # Case-fold at the guard boundary (mirrors ``assert_exclusive_tenant_binding``): a
    # case-variant FOREIGN address (harvested via ``re.IGNORECASE``) is caught as a
    # distinct member, while a case-variant of OWN collapses onto it and does not false-RED.
    own_norm = own.lower()
    harvested = {addr.lower() for addr in CANONICAL_ROUTING_ADDR_RE.findall(composed_text)}
    foreign = sorted(harvested - {own_norm})
    if foreign:
        raise TemplateTenantMismatch(
            "carrier-email tenant-binding violation: composed text carries a foreign "
            f"routing address; foreign={[_mask_addr(a) for a in foreign]}"
        )
