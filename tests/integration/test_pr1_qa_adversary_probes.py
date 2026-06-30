"""PR1 QA-adversary probes -- adversarial pressure on the per-task safety core (W1 + W2).

Adopted from the N4 QA-adversary suite and HARDENED. The per-task safety core PASSED
adversarial review (no wrong-tenant attach in any probe); these probes are kept as
PERMANENT regression coverage, and the four that originally FLAGGED a robustness gap
(F1, F2, F3, F4) now assert the FIXED behavior:

  * attack1 / attack4 / attack5 -- GREEN safety invariants (no-tautology W1, batch
    zero-leak, W1/T7 independence). attack1/attack4 run the REAL GFR engine + guard
    (UNMOCKED) over a mocked substrate; the asana attach + SDK resolve are mocked.
  * attack2a / attack3a / attack3b / attack6a(programming-bug) -- GREEN robustness
    invariants (non-compounding dedupe, legacy/uppercase/whitespace recognition,
    precise non-GfrError propagation).
  * attack2b -> F1: a foreign-tenant survivor is REAPED on the already-attached path.
  * attack3c -> F2: a mixed-case single deck is ONE prior (no self-deleting dedupe).
  * attack6a(guard-violation) -> F3: GuardViolationError / AmbiguousCardinalityError
    carry DISTINCT, LOUD reasons (not masked as anchor_unresolved).
  * attack6c -> F4: an unwired query_engine is surfaced LOUDLY at validate_async.

Everything routes through the REAL ``process_entity`` / ``execute_async`` /
``validate_async``. The two production-mutating boundaries (Asana attach, SDK resolve)
are mocked; the GFR engine + guard run unmocked where the probe targets tenant isolation.
"""

from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest
import structlog

from autom8_asana.automation.workflows.onboarding_walkthrough import constants, identity_guard
from autom8_asana.automation.workflows.onboarding_walkthrough import producer as producer_module
from autom8_asana.automation.workflows.onboarding_walkthrough.workflow import (
    OnboardingWalkthroughWorkflow,
)
from autom8_asana.core.types import EntityType
from tests.unit.resolution.gfr.conftest import make_hydration_result, make_rows_response

pytestmark = [pytest.mark.xdist_group("gfr_resolver")]

WF_MOD = "autom8_asana.automation.workflows.onboarding_walkthrough.workflow"
_HYDRATE = "autom8_asana.resolution.gfr.entry.hydrate_from_gid_async"
DOMAIN = "@appointments.contenteapp.com"

# Tenants. G_A is the honest target; G_X is a DIFFERENT (wrong) tenant; G_C is a third
# tenant used as a phone-collision victim's TRUE owner in the batch probe.
G_A = "d167d635-1468-4ad5-9f88-8d44c8a4d1a9"
G_X = "11111111-2222-4333-8444-555555555555"
G_C = "ffffffff-eeee-4ddd-8ccc-bbbbaaaa0000"
BIZ_A = "biz-a-gid"
BIZ_C = "biz-c-gid"
PHONE_A = "+15550000001"
SHARED_PHONE = "+15551112222"  # the collision surface


# --------------------------------------------------------------------------- #
# Helpers (mirrors of the unit-suite doubles, self-contained for the probes).
# --------------------------------------------------------------------------- #
def addr(guid: str) -> str:
    """The canonical routing address embedding ``guid``."""
    return f"{guid}{DOMAIN}"


def deck(*addrs: str) -> bytes:
    """A minimal frozen-deck stand-in embedding each routing address (mailto + text)."""
    parts = ["<html><body>"]
    for a in addrs:
        parts.append(f'<a href="mailto:{a}">Forward to {a}</a>')
    parts.append("</body></html>")
    return "".join(parts).encode("utf-8")


def first_addr(raw: bytes) -> str | None:
    """Harvest the first embedded routing-address guid from deck bytes (independent oracle)."""
    m = re.search(
        r"([0-9a-fA-F-]{36})@appointments\.contenteapp\.com", raw.decode("utf-8", "replace")
    )
    return m.group(1).lower() if m else None


def entity(gid: str, *, phone: str, provider: str = "GHL") -> dict[str, Any]:
    return {"gid": gid, "calendar_provider": provider, "office_phone": phone, "name": gid}


def freeze_echoing_resolved() -> AsyncMock:
    """A freeze double that echoes the RESOLVED address into the deck bytes.

    So an (unguarded) attach lands a deck carrying exactly the resolved tenant's guid --
    the SAFETY oracle then reads that guid off the captured upload.
    """

    async def _freeze(
        *, producer_dir: Any, deck_template: Any, gated_address: str, **_kw: Any
    ) -> bytes:
        return deck(gated_address)

    return AsyncMock(side_effect=_freeze)


def echo_anchor(resolved_addr: str) -> AsyncMock:
    """A Source-B anchor that ECHOES Source A (W1 passes transparently)."""

    async def _a(*, task_gid: str, client: Any, query_engine: Any, verifier: Any) -> str:
        return resolved_addr.split("@", 1)[0].lower()

    return AsyncMock(side_effect=_a)


def raising_anchor(exc: Exception) -> AsyncMock:
    """A Source-B anchor that RAISES (GFR cannot independently anchor)."""

    async def _a(*, task_gid: str, client: Any, query_engine: Any, verifier: Any) -> str:
        raise exc

    return AsyncMock(side_effect=_a)


class FakeAttachments:
    """Stateful in-memory attachments client (the faithful double-run substrate).

    ``store`` maps task_gid -> list of attachment objects (SimpleNamespace with
    gid/name/created_at/size/_bytes). ``upload_async`` appends (harvesting size+bytes),
    ``delete_async`` removes by gid (first ``delete_raises`` calls raise -- the
    soft-fail residue arm), ``list_for_task_async`` snapshots the store, and
    ``download_async`` streams an attachment's bytes into the destination buffer.
    """

    def __init__(
        self,
        initial: dict[str, list[Any]] | None = None,
        *,
        delete_raises: int = 0,
    ) -> None:
        self.store: dict[str, list[Any]] = {k: list(v) for k, v in (initial or {}).items()}
        self.delete_raises = delete_raises
        self._delete_calls = 0
        self._upn = 0
        self.uploads: list[dict[str, Any]] = []
        self.upload_async = AsyncMock(side_effect=self._upload)
        self.delete_async = AsyncMock(side_effect=self._delete)
        self.list_for_task_async = MagicMock(side_effect=self._list)
        self.download_async = AsyncMock(side_effect=self._download)

    async def _upload(
        self, *, parent: str, file: Any, name: str, content_type: str | None = None
    ) -> MagicMock:
        raw = file.getvalue()
        self._upn += 1
        self.uploads.append({"parent": parent, "name": name, "bytes": raw})
        self.store.setdefault(parent, []).append(
            SimpleNamespace(
                gid=f"up-{self._upn}",
                name=name,
                created_at=f"2026-06-30T00:00:{self._upn:02d}Z",
                size=len(raw),
                _bytes=raw,
            )
        )
        return MagicMock()

    async def _delete(self, att_gid: str) -> None:
        self._delete_calls += 1
        if self._delete_calls <= self.delete_raises:
            raise RuntimeError(f"simulated delete failure #{self._delete_calls}")
        for atts in self.store.values():
            atts[:] = [a for a in atts if a.gid != att_gid]

    def _list(self, task_gid: str, **_kwargs: Any) -> Any:
        return _AsyncIter(list(self.store.get(task_gid, [])))

    async def _download(self, att_gid: str, *, destination: Any) -> None:
        for atts in self.store.values():
            for a in atts:
                if a.gid == att_gid:
                    destination.write(a._bytes)
                    return
        destination.write(b"")

    def listed_guids(self, task_gid: str) -> set[str]:
        out: set[str] = set()
        for a in self.store.get(task_gid, []):
            for m in re.findall(
                r"([0-9a-fA-F-]{36})@appointments", a._bytes.decode("utf-8", "replace")
            ):
                out.add(m.lower())
        return out


class _AsyncIter:
    def __init__(self, items: list[Any]) -> None:
        self._items = items
        self._i = 0

    def __aiter__(self) -> _AsyncIter:
        return self

    async def __anext__(self) -> Any:
        if self._i >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._i]
        self._i += 1
        return item


def _att(gid: str, name: str, raw: bytes, *, created_at: str = "2020Z") -> SimpleNamespace:
    return SimpleNamespace(gid=gid, name=name, created_at=created_at, size=len(raw), _bytes=raw)


def make_wf(
    *,
    anchor: Any,
    atts: FakeAttachments,
    resolver_map: dict[str, str | None] | None = None,
    resolved: str | None = None,
    query_engine: Any = "default",
) -> OnboardingWalkthroughWorkflow:
    """Build the REAL workflow over the FakeAttachments + a phone->address resolver."""
    resolver = MagicMock()
    if resolver_map is not None:

        async def _resolve(*, office_phone: str) -> str | None:
            return resolver_map.get(office_phone)

        resolver.resolve_routing_address_by_phone_async = AsyncMock(side_effect=_resolve)
    else:
        resolver.resolve_routing_address_by_phone_async = AsyncMock(return_value=resolved)

    asana = MagicMock()
    asana.tasks = MagicMock()
    asana.tasks.get_async = AsyncMock()
    qe = MagicMock() if query_engine == "default" else query_engine
    return OnboardingWalkthroughWorkflow(
        asana_client=asana,
        resolver=resolver,
        attachments_client=atts,
        producer_dir="/tmp/_no_producer_probe",
        query_engine=qe,
        company_id_anchor=anchor,
    )


def _real_gfr_substrate(frame: pl.DataFrame, gid_to_biz: dict[str, str]) -> tuple[Any, Any]:
    """Build a (query_engine, hydrate_side_effect) pair driving the REAL GFR engine+guard.

    ``execute_rows`` serves the gid-exact Business row from ``frame``; the hydrate
    side-effect anchors each entry gid to its business per ``gid_to_biz`` (offer
    path_len=3). One stable patch for the whole batch -> concurrency-safe.
    """

    async def _exec(entity_type: Any, project_gid: Any, _client: Any, request: Any) -> Any:
        target = request.where.value
        return make_rows_response(rows=frame.filter(pl.col("gid") == target).to_dicts())

    qe = AsyncMock()
    qe.execute_rows = _exec

    async def _hydrate(*args: Any, **kwargs: Any) -> Any:
        # The GFR entry calls ``hydrate_from_gid_async(client, gid, hydrate_full=False)``
        # -- the entry gid is the SECOND positional (or the ``gid`` kwarg).
        gid = kwargs.get("gid")
        if gid is None:
            gid = args[1] if len(args) > 1 else args[0]
        return make_hydration_result(
            business_gid=gid_to_biz[gid], entry_type=EntityType.OFFER, path_len=3
        )

    return qe, _hydrate


def _capture_logs() -> Any:
    proxy = __import__(WF_MOD, fromlist=["logger"]).logger
    if "bind" in getattr(proxy, "__dict__", {}):
        del proxy.__dict__["bind"]
    return structlog.testing.capture_logs()


# =========================================================================== #
# attack1 -- W1 catches a phone-collision wrong-tenant resolve (no tautology leak).
# REAL GFR engine + guard, UNMOCKED.
# =========================================================================== #
async def test_attack1_phone_collision_wrong_tenant_no_tautology_leak() -> None:
    # task_A's office_phone resolves (SDK) to tenant X's address (a phone collision),
    # but the parent-chain gid-exact anchor for task_A is G_A. The two are INDEPENDENT
    # (Source A = phone -> G_X; Source B = gid-exact -> G_A), so W1 catches the mismatch
    # and fail-closes. NO wrong-tenant deck is frozen or attached.
    atts = FakeAttachments()
    frame = pl.DataFrame([{"gid": BIZ_A, "office_phone": SHARED_PHONE, "company_id": G_A}])
    qe, hydrate = _real_gfr_substrate(frame, {"task_A": BIZ_A})
    wf = make_wf(
        anchor=identity_guard.anchor_company_id,
        atts=atts,
        resolver_map={SHARED_PHONE: addr(G_X)},  # phone collision -> WRONG tenant X
        query_engine=qe,
    )
    freeze = freeze_echoing_resolved()
    with (
        patch(_HYDRATE, AsyncMock(side_effect=hydrate)),
        patch.object(producer_module, "freeze_walkthrough_deck", freeze),
    ):
        out = await wf.process_entity(entity("task_A", phone=SHARED_PHONE), {})
    assert out.status == "skipped"
    assert out.reason == "guid_anchor_mismatch"
    assert atts.uploads == []  # ZERO upload -- no wrong-tenant deck lands
    freeze.assert_not_awaited()  # guard precedes FREEZE
    print(f"[A1] phone-collision -> {out.reason}; uploads={len(atts.uploads)} (no tautology leak)")


# =========================================================================== #
# attack2a -- same-guid residue is NON-COMPOUNDING over N runs.
# =========================================================================== #
async def test_attack2a_same_guid_residue_non_compounding_over_n_runs() -> None:
    atts = FakeAttachments()
    wf = make_wf(anchor=echo_anchor(addr(G_A)), atts=atts, resolver_map={PHONE_A: addr(G_A)})
    statuses = []
    with patch.object(producer_module, "freeze_walkthrough_deck", freeze_echoing_resolved()):
        for _ in range(4):
            r = await wf.process_entity(entity("task_1", phone=PHONE_A), {})
            statuses.append(r.status)
    # Run-1 mints exactly one; runs 2-4 skip (already_attached). Never compounding.
    assert len(atts.uploads) == 1
    assert statuses[1:] == ["skipped", "skipped", "skipped"]
    assert atts.listed_guids("task_1") == {G_A.lower()}
    print(
        f"[A2a] 4 runs: uploads={len(atts.uploads)} surviving_guids={sorted(atts.listed_guids('task_1'))}"
    )


# =========================================================================== #
# attack2b -> F1: a foreign-tenant survivor IS reaped on the already-attached path.
# =========================================================================== #
async def test_attack2b_foreign_guid_survivor_is_reaped() -> None:
    # Tenant X's deck sits on task_1. The honest resolve is G_A. Run-1 mints A's deck
    # and tries to reap X via delete-old but it SOFT-FAILS (delete_raises=1) -> X
    # survives. Run-2: A is already_attached and F1 REAPS the foreign X deck. FIXED:
    # the wrong-tenant residue does NOT persist.
    foreign = _att("foreign", "walkthrough_task_1_20200101.html", deck(addr(G_X)))
    atts = FakeAttachments({"task_1": [foreign]}, delete_raises=1)
    wf = make_wf(anchor=echo_anchor(addr(G_A)), atts=atts, resolver_map={PHONE_A: addr(G_A)})
    statuses = []
    with patch.object(producer_module, "freeze_walkthrough_deck", freeze_echoing_resolved()):
        for _ in range(2):
            r = await wf.process_entity(entity("task_1", phone=PHONE_A), {})
            statuses.append(r.status)
    survivors = atts.listed_guids("task_1")
    assert len(atts.uploads) == 1  # one mint, no re-mint
    # F1 (FIXED): the foreign wrong-tenant guid is GONE; only the honest tenant remains.
    assert G_X.lower() not in survivors, "foreign wrong-tenant deck must be reaped (F1)"
    assert G_A.lower() in survivors
    print(
        f"[A2b] runs={statuses} uploads={len(atts.uploads)} surviving_guids={sorted(survivors)} (F1 reaped foreign)"
    )


# =========================================================================== #
# attack3a -- an UPPERCASE legacy deck is recognized (case-insensitive harvest) -> skip.
# =========================================================================== #
async def test_attack3a_uppercase_legacy_deck_recognized_skip() -> None:
    legacy = _att("legacy", "walkthrough_task_1_2018.html", deck(addr(G_A).upper()))
    atts = FakeAttachments({"task_1": [legacy]})
    wf = make_wf(anchor=echo_anchor(addr(G_A)), atts=atts, resolver_map={PHONE_A: addr(G_A)})
    freeze = freeze_echoing_resolved()
    with patch.object(producer_module, "freeze_walkthrough_deck", freeze):
        r = await wf.process_entity(entity("task_1", phone=PHONE_A), {})
    assert r.status == "skipped"
    assert r.reason == "already_attached"
    assert atts.uploads == []
    freeze.assert_not_awaited()
    print(f"[A3a] uppercase legacy -> {r.reason} uploads=0")


# =========================================================================== #
# attack3b -- whitespace-padded / multi-rendered target address is recognized -> skip.
# =========================================================================== #
async def test_attack3b_whitespace_padded_and_multi_address_recognized() -> None:
    raw = b"  \n\t" + deck(addr(G_A), addr(G_A)) + b"\n   "  # padding + repeated rendering
    legacy = _att("legacy", "walkthrough_task_1_2019.html", raw)
    atts = FakeAttachments({"task_1": [legacy]})
    wf = make_wf(anchor=echo_anchor(addr(G_A)), atts=atts, resolver_map={PHONE_A: addr(G_A)})
    with patch.object(producer_module, "freeze_walkthrough_deck", freeze_echoing_resolved()):
        r = await wf.process_entity(entity("task_1", phone=PHONE_A), {})
    assert r.status == "skipped"
    assert r.reason == "already_attached"
    assert atts.uploads == []
    print(f"[A3b] whitespace/multi-rendered -> {r.reason} uploads=0")


# =========================================================================== #
# attack3c -> F2: a mixed-case single deck is ONE prior (no self-deleting dedupe).
# =========================================================================== #
async def test_attack3c_mixed_case_same_guid_single_deck_does_not_self_delete() -> None:
    # The legacy deck's BYTES carry the SAME guid in lower AND upper case. Pre-F2 this
    # counted as 2 priors -> dedupe-down deleted the only real deck. FIXED: ONE prior ->
    # already_attached, deletes=0, the deck survives.
    mixed = deck(addr(G_A), addr(G_A).upper())
    legacy = _att("legacy", "walkthrough_task_1_2018.html", mixed)
    atts = FakeAttachments({"task_1": [legacy]})
    wf = make_wf(anchor=echo_anchor(addr(G_A)), atts=atts, resolver_map={PHONE_A: addr(G_A)})
    with patch.object(producer_module, "freeze_walkthrough_deck", freeze_echoing_resolved()):
        r = await wf.process_entity(entity("task_1", phone=PHONE_A), {})
    after = atts.listed_guids("task_1")
    assert r.status == "skipped"
    assert r.reason == "already_attached"  # NOT already_attached_deduped
    assert atts.delete_async.await_count == 0  # deletes=0: not self-deleted
    assert len(atts.uploads) == 0
    assert after == {G_A.lower()}  # the deck survives
    print(
        f"[A3c] mixed-case single deck -> {r.reason} deletes={atts.delete_async.await_count} remaining={sorted(after)} (F2 fixed)"
    )


# =========================================================================== #
# attack4 -- BATCH zero-leak through execute_async. REAL GFR engine + guard.
# =========================================================================== #
async def test_attack4_batch_zero_leak_through_execute_async() -> None:
    # Two tasks: an honest one (phone -> own addr, anchor matches -> attach) and a
    # phone-collision attacker (phone -> tenant X's addr, anchor -> its TRUE owner G_C
    # -> mismatch -> skip). Through the REAL execute_async fan-out, ZERO wrong-tenant
    # deck is attached: every uploaded deck carries the task's own true tenant guid.
    atts = FakeAttachments()
    frame = pl.DataFrame(
        [
            {"gid": BIZ_A, "office_phone": PHONE_A, "company_id": G_A},
            {"gid": BIZ_C, "office_phone": SHARED_PHONE, "company_id": G_C},
        ]
    )
    qe, hydrate = _real_gfr_substrate(frame, {"task_ok": BIZ_A, "task_collide": BIZ_C})
    wf = make_wf(
        anchor=identity_guard.anchor_company_id,
        atts=atts,
        resolver_map={PHONE_A: addr(G_A), SHARED_PHONE: addr(G_X)},  # collide -> WRONG X
        query_engine=qe,
    )
    entities = [
        entity("task_ok", phone=PHONE_A),
        entity("task_collide", phone=SHARED_PHONE),
    ]
    with (
        patch(_HYDRATE, AsyncMock(side_effect=hydrate)),
        patch.object(producer_module, "freeze_walkthrough_deck", freeze_echoing_resolved()),
    ):
        result = await wf.execute_async(entities, {})

    uploaded_guids = {first_addr(u["bytes"]) for u in atts.uploads}
    assert G_X.lower() not in uploaded_guids, "wrong-tenant deck must NEVER be attached"
    assert uploaded_guids == {G_A.lower()}  # only the honest tenant's deck landed
    assert result.succeeded == 1
    assert result.skipped == 1
    print(
        f"[A4] batch: succeeded={result.succeeded} skipped={result.skipped} uploaded_guids={sorted(g for g in uploaded_guids if g)} (zero leak)"
    )


# =========================================================================== #
# attack5 -- T7 bites AFTER W1 passes: the gates are independent.
# =========================================================================== #
async def test_attack5_t7_bites_after_w1_passes_gates_independent() -> None:
    # W1 passes (the anchor echoes Source A), but the FROZEN artifact is contaminated
    # with a foreign address -> T7 (tenant-binding exclusivity) fail-closes. Proves W1
    # and T7 are independent gates: passing one does not bypass the other.
    atts = FakeAttachments()
    wf = make_wf(anchor=echo_anchor(addr(G_A)), atts=atts, resolver_map={PHONE_A: addr(G_A)})

    async def _contaminated(**_kw: Any) -> bytes:
        return deck(addr(G_A), addr(G_X))  # resolved tenant + a FOREIGN address

    with patch.object(
        producer_module, "freeze_walkthrough_deck", AsyncMock(side_effect=_contaminated)
    ):
        out = await wf.process_entity(entity("task_1", phone=PHONE_A), {})
    assert out.status == "failed"
    assert out.error is not None
    assert out.error.error_type == "tenant_binding_violation"
    assert atts.uploads == []  # T7 fail-closed -> no attach
    print(f"[A5] W1 passed but T7 caught contamination -> {out.error.error_type}; uploads=0")


# =========================================================================== #
# attack6a (programming-bug) -- a non-GfrError is NOT swallowed as anchor_unresolved.
# =========================================================================== #
async def test_attack6a_programming_bug_not_swallowed_as_anchor_unresolved() -> None:
    # A genuine programming bug in the anchor (a KeyError, NOT a GfrError) must NOT be
    # masked as a benign skip. process_entity's catch is GfrError-only, so it propagates;
    # through execute_async the per-entity boundary surfaces it as FAILED (unexpected_error),
    # never skipped(anchor_unresolved).
    atts = FakeAttachments()

    def _buggy() -> AsyncMock:
        async def _a(*, task_gid: str, client: Any, query_engine: Any, verifier: Any) -> str:
            raise KeyError("a real bug in the anchor, not a GFR failure")

        return AsyncMock(side_effect=_a)

    wf = make_wf(anchor=_buggy(), atts=atts, resolver_map={PHONE_A: addr(G_A)})
    with patch.object(producer_module, "freeze_walkthrough_deck", freeze_echoing_resolved()):
        # Directly: it propagates (not swallowed).
        with pytest.raises(KeyError):
            await wf.process_entity(entity("task_1", phone=PHONE_A), {})
        # Through the batch boundary: FAILED, not a benign skip.
        result = await wf.execute_async([entity("task_1", phone=PHONE_A)], {})
    assert result.failed == 1
    assert result.skipped == 0
    assert atts.uploads == []
    print(f"[A6a-bug] non-GfrError -> failed={result.failed} skipped={result.skipped} (not masked)")


# =========================================================================== #
# attack6a (guard-violation) -> F3: structural/integrity signals get DISTINCT reasons.
# =========================================================================== #
@pytest.mark.parametrize(
    ("exc_factory", "expected_reason"),
    [
        (lambda: _guard_violation(), "guard_violation"),
        (lambda: _ambiguous(), "ambiguous_anchor"),
    ],
)
async def test_attack6a_guard_violation_distinct_loud_reason(
    exc_factory: Any, expected_reason: str
) -> None:
    from autom8_asana.resolution.gfr.errors import GfrError

    exc = exc_factory()
    assert isinstance(exc, GfrError)
    atts = FakeAttachments()
    wf = make_wf(anchor=raising_anchor(exc), atts=atts, resolver_map={PHONE_A: addr(G_A)})
    with patch.object(producer_module, "freeze_walkthrough_deck", freeze_echoing_resolved()):
        with _capture_logs() as captured:
            r = await wf.process_entity(entity("task_1", phone=PHONE_A), {})
    assert r.status == "skipped"
    # F3 (FIXED): a distinct, LOUD reason -- NOT masked into anchor_unresolved.
    assert r.reason == expected_reason
    entry = next(e for e in captured if e["event"] == "onboarding_walkthrough_skipped")
    assert entry["reason"] == expected_reason
    assert entry["log_level"] == "error"
    assert atts.uploads == []
    print(
        f"[A6a-flag] {type(exc).__name__} -> reason={r.reason!r} level={entry['log_level']!r} (F3 distinct)"
    )


def _guard_violation() -> Exception:
    from autom8_asana.resolution.gfr.errors import GuardViolationError

    return GuardViolationError("the PHI-leak trap was reintroduced")


def _ambiguous() -> Exception:
    from autom8_asana.resolution.gfr.errors import AmbiguousCardinalityError

    return AmbiguousCardinalityError(row_count=2)


# =========================================================================== #
# attack6c -> F4: an unwired query_engine sweep is INERT, but now LOUDLY surfaced.
# =========================================================================== #
async def test_attack6c_unwired_query_engine_inert_but_loudly_surfaced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Per-task, an unwired guard fail-closes every entity (anchor_unresolved) -> the
    # sweep attaches nothing. That inert behavior is REAL (and safe). The FIX (F4): it
    # is no longer SILENT -- validate_async surfaces the unwired state LOUDLY at
    # pre-flight, so a dark deploy is detectable.
    atts = FakeAttachments()
    wf = make_wf(
        anchor=identity_guard.anchor_company_id,
        atts=atts,
        resolver_map={PHONE_A: addr(G_A)},
        query_engine=None,
    )
    assert wf._query_engine is None

    entities = [entity(f"t{i}", phone=PHONE_A) for i in range(3)]
    with patch.object(producer_module, "freeze_walkthrough_deck", freeze_echoing_resolved()):
        result = await wf.execute_async(entities, {})
    # The inert behavior is real: 3/3 skipped, zero uploads.
    assert result.succeeded == 0
    assert result.skipped == 3
    assert atts.uploads == []

    # F4 (FIXED): validate_async makes the unwired deploy LOUD + DETECTABLE.
    monkeypatch.setenv(constants.WALKTHROUGH_ENABLED_ENV_VAR, "true")
    with _capture_logs() as captured:
        problems = await wf.validate_async()
    assert problems, "unwired-but-enabled deploy MUST fail pre-flight (not silently dark)"
    assert any("INERT" in p for p in problems)
    inert = [e for e in captured if e["event"] == "onboarding_walkthrough_guard_inert"]
    assert len(inert) == 1 and inert[0]["log_level"] == "error"
    print(
        f"[A6c] inert sweep: skipped={result.skipped} uploads=0; validate problems={len(problems)} level={inert[0]['log_level']!r} (F4 loud)"
    )
