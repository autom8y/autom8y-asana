"""D6 webhook registration: minting, create, the handshake, the reconciler, cleanup.

Design of record: TDD-asana-bench-D6-shadow-receiver-20261110 r4.6, sections 2, 2a and 3;
fixtures HS-1..HS-4, OR-1, R-A5b (section 9). Custody: RULING-project-bootstrapping-
asana-webhook-hook-custody-20261110 (write-once value, key deleted last).

DARK. Nothing in production constructs these objects in this PR. :class:`Registrar` and
:class:`Reconciler` refuse to construct unless ``ASANA_HOOK_SHADOW_ENABLED`` is exactly
``"1"``, and :func:`build_shadow_registration` returns ``None`` with the flag off, before
it calls any factory. The HTTP route that calls :func:`handle_handshake` lands in A3.

Registration sequence (section 3):

1. Mint a 128-bit hex handle.
2. Put ``HOOK`` ``pending`` with ``expires_at = now + 60 s``.
3. ``POST /webhooks`` for the project, target ``{base}/{handle}``, with the filters of
   the kinds its trigger-map row names. A project with no row registers nothing
   (auth-bench A2-4); no map ships in this PR, so nothing registers.
4. ``GET /webhooks/{gid}``: confirm the target and the resource.
5. ``handshaken -> active``, and point ``PROJECT#{gid}/ACTIVE`` at the handle.

If the create's outcome is unknown, the hook becomes ``create_unknown`` and is adopted or
deleted; its stored value is deleted LAST (OR-1).

Handshake (section 3): unknown handle 404; the conditional ``pending -> handshaken`` makes
the first handshake win; then the store write; only then the echo. A store failure gives
``failed``, 500 and no echo (HS-4, A C-2). A second handshake gives 403 and
``compromised`` (HS-2). Known but not pending gives 403.
"""

from __future__ import annotations

import asyncio
import os
import re
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Final, Protocol

from autom8y_log import get_logger

from autom8_asana.trigger.hook_environment import (
    assert_shadow_startup,
    shadow_flag_on,
)
from autom8_asana.trigger.hook_registry import (
    HookRecord,
    HookRegistryConflict,
    HookRegistryError,
    HookState,
)
from autom8_asana.trigger.hook_store import HookStoreError
from autom8_asana.trigger.ports_webhooks import (
    WebhookCallFailed,
    WebhookCallOutcomeUnknown,
    WebhooksClient,
    WebhookView,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from autom8_asana.trigger.watched_projects import WatchedProject

logger = get_logger(__name__)

HANDLE_BYTES: Final[int] = 16  # 128 bits
HANDLE_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{32}$")
HOOK_ROUTE_PATH: Final[str] = "/api/v1/webhooks/asana"
# Section 3: 16 to 256 printable, non-space ASCII characters (format UNVERIFIED upstream).
HOOK_HEADER_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[\x21-\x7e]{16,256}$")
CREATE_TIMEOUT_S: Final[float] = 30.0
RECONCILE_INTERVAL_S: Final[int] = 300
LEASE_DURATION_S: Final[int] = 360


class RegistrationRefused(TypeError):
    """Construction refused: the wrong client class, or a malformed configuration."""


class ShadowRegistrationDisabled(RuntimeError):
    """Construction refused: ``ASANA_HOOK_SHADOW_ENABLED`` is not exactly ``"1"``."""


class HookRegistryPort(Protocol):
    def put_pending(self, *, handle: str, resource_gid: str, now: int) -> HookRecord: ...
    def get_hook(self, handle: str, *, consistent: bool = True) -> HookRecord | None: ...
    def mark_handshaken(self, *, handle: str, now: int) -> None: ...
    def set_webhook_gid(self, *, handle: str, webhook_gid: str) -> None: ...
    def mark_create_unknown(self, *, handle: str, now: int) -> None: ...
    def mark_failed(self, *, handle: str, now: int) -> None: ...
    def mark_compromised(self, *, handle: str, now: int) -> None: ...
    def mark_removed(self, *, handle: str, now: int) -> None: ...
    def activate(
        self,
        *,
        handle: str,
        project_gid: str,
        webhook_gid: str,
        now: int,
        from_state: HookState,
        previous_handle: str | None,
    ) -> None: ...
    def get_active_handle(self, project_gid: str, *, consistent: bool = True) -> str | None: ...
    def acquire_lease(self, *, owner: str, now: int, duration_s: int) -> bool: ...
    def release_lease(self, *, owner: str) -> None: ...


class HookStorePort(Protocol):
    def create_hook_value(
        self, *, handle: str, hook_value: str, resource_gid: str, registered_at: str
    ) -> None: ...
    def tag_webhook_gid(self, *, handle: str, webhook_gid: str) -> None: ...
    def delete_hook_value(self, *, handle: str) -> bool: ...


def mint_handle() -> str:
    """A fresh 128-bit handle, as 32 lowercase hex characters."""
    return secrets.token_hex(HANDLE_BYTES)


def _iso(now: int) -> str:
    return datetime.fromtimestamp(now, UTC).isoformat()


# ---------------------------------------------------------------------------
# Handshake
# ---------------------------------------------------------------------------


class HandshakeReason(StrEnum):
    ECHOED = "echoed"
    UNKNOWN_HANDLE = "unknown_handle"
    NOT_PENDING = "not_pending"
    EXPIRED = "expired"
    HEADER_INVALID = "header_invalid"
    SECOND_HANDSHAKE = "second_handshake"
    STORE_FAILED = "store_failed"


@dataclass(frozen=True)
class HandshakeResult:
    """What the A3 route returns. ``echo`` is set only on 200."""

    status_code: int
    reason: HandshakeReason
    echo: str | None = field(default=None, repr=False)


async def _flag_compromised(registry: HookRegistryPort, handle: str, now: int) -> None:
    try:
        await asyncio.to_thread(registry.mark_compromised, handle=handle, now=now)
    except HookRegistryError as exc:
        logger.error(
            "hook_handshake_compromise_mark_failed",
            extra={"handle": handle, "error_type": type(exc).__name__},
        )
    logger.error("hook_handshake_compromised", extra={"handle": handle})


async def handle_handshake(
    *,
    handle: str,
    hook_header: str | None,
    registry: HookRegistryPort,
    store: HookStorePort,
    now: int,
) -> HandshakeResult:
    """Answer one Asana handshake for ``handle``. Never logs the header value."""
    if not HANDLE_PATTERN.fullmatch(handle):
        return HandshakeResult(404, HandshakeReason.UNKNOWN_HANDLE)
    # Consistent read: a handshake resolves on any task, never from a snapshot (HS-3).
    record = await asyncio.to_thread(registry.get_hook, handle, consistent=True)
    if record is None:
        logger.warning("hook_handshake_refused", extra={"handle": handle, "reason": "unknown"})
        return HandshakeResult(404, HandshakeReason.UNKNOWN_HANDLE)
    if record.handshaken_at is not None or record.state in (HookState.HANDSHAKEN, HookState.ACTIVE):
        if record.state not in (HookState.COMPROMISED, HookState.REMOVED):
            await _flag_compromised(registry, handle, now)
        return HandshakeResult(403, HandshakeReason.SECOND_HANDSHAKE)
    if record.state is not HookState.PENDING:
        logger.warning("hook_handshake_refused", extra={"handle": handle, "reason": "not_pending"})
        return HandshakeResult(403, HandshakeReason.NOT_PENDING)
    if now >= record.expires_at:
        logger.warning("hook_handshake_refused", extra={"handle": handle, "reason": "expired"})
        return HandshakeResult(403, HandshakeReason.EXPIRED)
    if hook_header is None or not HOOK_HEADER_PATTERN.fullmatch(hook_header):
        logger.warning(
            "hook_handshake_refused", extra={"handle": handle, "reason": "header_invalid"}
        )
        return HandshakeResult(403, HandshakeReason.HEADER_INVALID)

    try:
        await asyncio.to_thread(registry.mark_handshaken, handle=handle, now=now)
    except HookRegistryConflict:
        # Lost the conditional move: another handshake won, or the row expired or moved.
        latest = await asyncio.to_thread(registry.get_hook, handle, consistent=True)
        if latest is not None and latest.handshaken_at is not None:
            if latest.state not in (HookState.COMPROMISED, HookState.REMOVED):
                await _flag_compromised(registry, handle, now)
            return HandshakeResult(403, HandshakeReason.SECOND_HANDSHAKE)
        return HandshakeResult(403, HandshakeReason.NOT_PENDING)

    try:
        await asyncio.to_thread(
            store.create_hook_value,
            handle=handle,
            hook_value=hook_header,
            resource_gid=record.resource_gid,
            registered_at=_iso(now),
        )
    except Exception as exc:  # noqa: BLE001
        # BROAD-CATCH: fail-closed -- ANY store failure is `failed`, 500, no echo (A C-2).
        logger.error(
            "hook_handshake_store_failed",
            extra={"handle": handle, "error_type": type(exc).__name__},
        )
        try:
            await asyncio.to_thread(registry.mark_failed, handle=handle, now=now)
        except HookRegistryError as mark_exc:
            logger.error(
                "hook_handshake_fail_mark_failed",
                extra={"handle": handle, "error_type": type(mark_exc).__name__},
            )
        return HandshakeResult(500, HandshakeReason.STORE_FAILED)

    logger.info("hook_handshake_echoed", extra={"handle": handle})
    return HandshakeResult(200, HandshakeReason.ECHOED, echo=hook_header)


# ---------------------------------------------------------------------------
# Registrar
# ---------------------------------------------------------------------------


class RegistrationStatus(StrEnum):
    NO_MAP_ROW = "no_map_row"
    ACTIVE = "active"
    ADOPTED = "adopted"
    FAILED = "failed"
    CREATE_UNKNOWN_DELETED = "create_unknown_deleted"
    CONFIRM_MISMATCH = "confirm_mismatch"
    ACTIVE_CONFLICT = "active_conflict"


@dataclass(frozen=True)
class RegistrationOutcome:
    project_gid: str
    handle: str
    status: RegistrationStatus


def _validate_base_url(base_url: str) -> str:
    if (
        not isinstance(base_url, str)
        or not base_url.startswith("https://")
        or not base_url.endswith(HOOK_ROUTE_PATH)
        or any(c in base_url for c in "?#")
        or any(c.isspace() for c in base_url)
    ):
        raise RegistrationRefused(f"target base URL must be https and end with {HOOK_ROUTE_PATH}")
    return base_url


class Registrar:
    """Registers, adopts, replaces and retires webhooks for watched projects."""

    def __init__(
        self,
        *,
        webhooks: WebhooksClient,
        registry: HookRegistryPort,
        store: HookStorePort,
        workspace_gid: str,
        target_base_url: str,
        clock: Callable[[], float] = time.time,
        environ: Mapping[str, str] | None = None,
        create_timeout_s: float = CREATE_TIMEOUT_S,
    ) -> None:
        # R-A5b: the narrow port only. A full AsanaClient (or the SDK's full-CRUD
        # webhooks client) is refused here, at construction.
        if type(webhooks) is not WebhooksClient:
            raise RegistrationRefused(
                f"registration takes trigger.ports_webhooks.WebhooksClient, not "
                f"{type(webhooks).__module__}.{type(webhooks).__qualname__}"
            )
        if not shadow_flag_on(os.environ if environ is None else environ):
            raise ShadowRegistrationDisabled("ASANA_HOOK_SHADOW_ENABLED is not exactly '1'")
        if not workspace_gid:
            raise RegistrationRefused("workspace_gid is empty")
        self._webhooks = webhooks
        self._registry = registry
        self._store = store
        self._workspace_gid = workspace_gid
        self._base_url = _validate_base_url(target_base_url)
        self._clock = clock
        self._create_timeout_s = create_timeout_s

    def _now(self) -> int:
        return int(self._clock())

    def target_for(self, handle: str) -> str:
        return f"{self._base_url}/{handle}"

    def handle_from_target(self, target: str | None) -> str | None:
        """The handle in one of our targets, or ``None`` for any other target."""
        prefix = f"{self._base_url}/"
        if not target or not target.startswith(prefix):
            return None
        tail = target[len(prefix) :]
        return tail if HANDLE_PATTERN.fullmatch(tail) else None

    # -- cleanup --------------------------------------------------------------

    async def retire(self, handle: str, webhook_gid: str | None) -> None:
        """Delete the webhook, then the stored value (LAST), then mark the row removed."""
        if webhook_gid:
            await self._webhooks.delete(webhook_gid)
        record = await asyncio.to_thread(self._registry.get_hook, handle, consistent=True)
        if record is not None and record.handshaken_at is not None:
            await asyncio.to_thread(self._store.delete_hook_value, handle=handle)
        if record is not None and record.state is not HookState.COMPROMISED:
            try:
                await asyncio.to_thread(self._registry.mark_removed, handle=handle, now=self._now())
            except HookRegistryConflict:
                logger.warning("hook_retire_mark_conflict", extra={"handle": handle})
        logger.info("hook_retired", extra={"handle": handle, "webhook_gid": webhook_gid})

    # -- create ---------------------------------------------------------------

    async def register_project(
        self, project: WatchedProject, *, replacing: str | None = None
    ) -> RegistrationOutcome:
        gid = project.project_gid
        if not project.trigger_kinds:
            # auth A2-4: no trigger-map row registers NOTHING. No row, no Asana call.
            logger.info("hook_no_map_row", extra={"project_gid": gid})
            return RegistrationOutcome(gid, "", RegistrationStatus.NO_MAP_ROW)
        handle = mint_handle()
        now = self._now()
        await asyncio.to_thread(
            self._registry.put_pending, handle=handle, resource_gid=gid, now=now
        )
        target = self.target_for(handle)
        try:
            view = await asyncio.wait_for(
                self._webhooks.create(resource_gid=gid, target=target, filters=project.filters()),
                timeout=self._create_timeout_s,
            )
        except (WebhookCallOutcomeUnknown, TimeoutError) as exc:
            logger.warning(
                "hook_create_unknown",
                extra={"handle": handle, "project_gid": gid, "error_type": type(exc).__name__},
            )
            await asyncio.to_thread(
                self._registry.mark_create_unknown, handle=handle, now=self._now()
            )
            return await self.resolve_create_unknown(project, handle, replacing=replacing)
        except WebhookCallFailed as exc:
            # Definite refusal: Asana holds no webhook for this handle.
            logger.error(
                "hook_create_refused",
                extra={"handle": handle, "project_gid": gid, "status_code": exc.status_code},
            )
            await self._fail_without_webhook(handle)
            return RegistrationOutcome(gid, handle, RegistrationStatus.FAILED)

        await asyncio.to_thread(self._registry.set_webhook_gid, handle=handle, webhook_gid=view.gid)
        return await self._confirm_and_activate(
            project, handle, view.gid, from_state=HookState.HANDSHAKEN, replacing=replacing
        )

    async def _fail_without_webhook(self, handle: str) -> None:
        record = await asyncio.to_thread(self._registry.get_hook, handle, consistent=True)
        if record is None:
            return
        if record.state is not HookState.FAILED:
            try:
                await asyncio.to_thread(self._registry.mark_failed, handle=handle, now=self._now())
            except HookRegistryConflict:
                logger.warning("hook_fail_mark_conflict", extra={"handle": handle})
            # The handshake stored a value but Asana refused the create: no webhook will
            # ever use it.
            if record.handshaken_at is not None:
                await asyncio.to_thread(self._store.delete_hook_value, handle=handle)

    def _confirms(self, view: WebhookView | None, handle: str, project_gid: str) -> bool:
        return (
            view is not None
            and view.target == self.target_for(handle)
            and view.resource_gid == project_gid
            and view.active is not False
        )

    async def _confirm_and_activate(
        self,
        project: WatchedProject,
        handle: str,
        webhook_gid: str,
        *,
        from_state: HookState,
        replacing: str | None,
    ) -> RegistrationOutcome:
        gid = project.project_gid
        view = await self._webhooks.get(webhook_gid)
        record = await asyncio.to_thread(self._registry.get_hook, handle, consistent=True)
        if (
            not self._confirms(view, handle, gid)
            or record is None
            or record.state is not from_state
            or record.handshaken_at is None
        ):
            logger.error(
                "hook_confirm_mismatch",
                extra={"handle": handle, "project_gid": gid, "webhook_gid": webhook_gid},
            )
            await self.retire(handle, webhook_gid)
            return RegistrationOutcome(gid, handle, RegistrationStatus.CONFIRM_MISMATCH)

        try:
            await asyncio.to_thread(
                self._store.tag_webhook_gid, handle=handle, webhook_gid=webhook_gid
            )
        except HookStoreError as exc:
            # The tag is metadata, never used for verification; webhook_gid is in D-1.
            logger.warning(
                "hook_tag_failed", extra={"handle": handle, "error_type": type(exc).__name__}
            )

        try:
            await asyncio.to_thread(
                self._registry.activate,
                handle=handle,
                project_gid=gid,
                webhook_gid=webhook_gid,
                now=self._now(),
                from_state=from_state,
                previous_handle=replacing,
            )
        except HookRegistryConflict:
            # Another hook holds the project's ACTIVE row (W F-6b): this one goes.
            logger.error("hook_activate_conflict", extra={"handle": handle, "project_gid": gid})
            await self.retire(handle, webhook_gid)
            return RegistrationOutcome(gid, handle, RegistrationStatus.ACTIVE_CONFLICT)

        logger.info("hook_active", extra={"handle": handle, "project_gid": gid})
        if replacing is not None and replacing != handle:
            old = await asyncio.to_thread(self._registry.get_hook, replacing, consistent=True)
            await self.retire(replacing, old.webhook_gid if old is not None else None)
        status = (
            RegistrationStatus.ADOPTED
            if from_state is HookState.CREATE_UNKNOWN
            else RegistrationStatus.ACTIVE
        )
        return RegistrationOutcome(gid, handle, status)

    async def resolve_create_unknown(
        self, project: WatchedProject, handle: str, *, replacing: str | None = None
    ) -> RegistrationOutcome:
        """Adopt or delete a ``create_unknown`` hook (OR-1). The value is deleted last."""
        gid = project.project_gid
        target = self.target_for(handle)
        views = await self._webhooks.list_for_resource(
            workspace_gid=self._workspace_gid, resource_gid=gid
        )
        matches = [v for v in views if v.target == target]
        record = await asyncio.to_thread(self._registry.get_hook, handle, consistent=True)
        active = await asyncio.to_thread(self._registry.get_active_handle, gid, consistent=True)
        can_adopt = (
            len(matches) == 1
            and record is not None
            and record.state is HookState.CREATE_UNKNOWN
            and record.handshaken_at is not None
            and active == replacing
        )
        if can_adopt:
            webhook_gid = matches[0].gid
            await asyncio.to_thread(
                self._registry.set_webhook_gid, handle=handle, webhook_gid=webhook_gid
            )
            return await self._confirm_and_activate(
                project,
                handle,
                webhook_gid,
                from_state=HookState.CREATE_UNKNOWN,
                replacing=replacing,
            )
        # Delete every webhook Asana holds for this handle, then the value, then the row.
        for view in matches[:-1]:
            await self._webhooks.delete(view.gid)
        await self.retire(handle, matches[-1].gid if matches else None)
        return RegistrationOutcome(gid, handle, RegistrationStatus.CREATE_UNKNOWN_DELETED)

    # -- reconcile ------------------------------------------------------------

    async def reconcile_project(self, project: WatchedProject) -> list[RegistrationOutcome]:
        """One pass for one project: keep exactly one healthy active hook, sweep orphans."""
        gid = project.project_gid
        if not project.trigger_kinds:
            # auth A2-4: a project with no map row gets no create, no list, no get.
            logger.info("hook_no_map_row", extra={"project_gid": gid})
            return [RegistrationOutcome(gid, "", RegistrationStatus.NO_MAP_ROW)]
        outcomes: list[RegistrationOutcome] = []
        active = await asyncio.to_thread(self._registry.get_active_handle, gid, consistent=True)
        if active is None:
            outcomes.append(await self.register_project(project))
        elif not await self._is_healthy(active, gid):
            logger.warning("hook_unhealthy", extra={"handle": active, "project_gid": gid})
            outcomes.append(await self.register_project(project, replacing=active))

        current = await asyncio.to_thread(self._registry.get_active_handle, gid, consistent=True)
        views = await self._webhooks.list_for_resource(
            workspace_gid=self._workspace_gid, resource_gid=gid
        )
        now = self._now()
        for view in views:
            handle = self.handle_from_target(view.target)
            if handle is None or handle == current:
                continue
            record = await asyncio.to_thread(self._registry.get_hook, handle, consistent=True)
            if record is None:
                # Not provably ours: never delete a webhook this service did not register.
                logger.warning(
                    "hook_unowned_webhook", extra={"project_gid": gid, "webhook_gid": view.gid}
                )
                continue
            if record.state is HookState.CREATE_UNKNOWN:
                outcomes.append(await self.resolve_create_unknown(project, handle))
                continue
            if (
                record.state in (HookState.PENDING, HookState.HANDSHAKEN)
                and now < record.expires_at
            ):
                continue  # a registration in flight
            await self.retire(handle, view.gid)
        return outcomes

    async def _is_healthy(self, handle: str, project_gid: str) -> bool:
        record = await asyncio.to_thread(self._registry.get_hook, handle, consistent=True)
        if record is None or record.state is not HookState.ACTIVE or not record.webhook_gid:
            return False
        view = await self._webhooks.get(record.webhook_gid)
        return (
            view is not None and view.active is True and self._confirms(view, handle, project_gid)
        )


# ---------------------------------------------------------------------------
# Reconciler: every five minutes, under a lease
# ---------------------------------------------------------------------------


@dataclass
class ReconcileReport:
    ran: bool
    skipped_reason: str | None = None
    outcomes: list[RegistrationOutcome] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class Reconciler:
    """Runs :meth:`Registrar.reconcile_project` for each watched project under a lease."""

    def __init__(
        self,
        *,
        registrar: Registrar,
        registry: HookRegistryPort,
        projects: Sequence[WatchedProject],
        clock: Callable[[], float] = time.time,
        environ: Mapping[str, str] | None = None,
        owner: str | None = None,
        interval_s: int = RECONCILE_INTERVAL_S,
        lease_s: int = LEASE_DURATION_S,
    ) -> None:
        if not shadow_flag_on(os.environ if environ is None else environ):
            raise ShadowRegistrationDisabled("ASANA_HOOK_SHADOW_ENABLED is not exactly '1'")
        if type(registrar) is not Registrar:
            raise RegistrationRefused("the reconciler takes a Registrar")
        self._registrar = registrar
        self._registry = registry
        self._projects = tuple(projects)
        self._clock = clock
        self._owner = owner or uuid.uuid4().hex
        self._interval_s = interval_s
        self._lease_s = lease_s

    @property
    def projects(self) -> tuple[WatchedProject, ...]:
        return self._projects

    async def run_once(self) -> ReconcileReport:
        acquired = await asyncio.to_thread(
            self._registry.acquire_lease,
            owner=self._owner,
            now=int(self._clock()),
            duration_s=self._lease_s,
        )
        if not acquired:
            return ReconcileReport(ran=False, skipped_reason="lease_held")
        report = ReconcileReport(ran=True)
        for project in self._projects:
            try:
                report.outcomes.extend(await self._registrar.reconcile_project(project))
            except (WebhookCallFailed, HookRegistryError, HookStoreError) as exc:
                # One project's failure does not stop the next; it is logged and reported.
                logger.error(
                    "hook_reconcile_project_failed",
                    extra={"project_gid": project.project_gid, "error_type": type(exc).__name__},
                )
                report.errors.append(f"{project.project_gid}: {type(exc).__name__}")
        return report

    async def run_forever(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            await self.run_once()
            try:
                await asyncio.wait_for(stop.wait(), timeout=self._interval_s)
            except TimeoutError:
                continue
        await asyncio.to_thread(self._registry.release_lease, owner=self._owner)


def build_shadow_registration(
    *,
    environ: Mapping[str, str] | None = None,
    webhooks_factory: Callable[[], WebhooksClient],
    registry_factory: Callable[[], HookRegistryPort],
    store_factory: Callable[[], HookStorePort],
    projects_factory: Callable[[], Sequence[WatchedProject]],
    workspace_gid: str,
    target_base_url: str,
    clock: Callable[[], float] = time.time,
) -> Reconciler | None:
    """The one entry point. With the shadow flag off it returns ``None`` and calls nothing.

    With the flag on, a refused marker raises (startup fails, section 2a), and only then
    are the factories called.
    """
    env = os.environ if environ is None else environ
    if assert_shadow_startup(env) is None:
        logger.info("hook_shadow_off")
        return None
    registry = registry_factory()
    registrar = Registrar(
        webhooks=webhooks_factory(),
        registry=registry,
        store=store_factory(),
        workspace_gid=workspace_gid,
        target_base_url=target_base_url,
        clock=clock,
        environ=env,
    )
    return Reconciler(
        registrar=registrar,
        registry=registry,
        projects=projects_factory(),
        clock=clock,
        environ=env,
    )
