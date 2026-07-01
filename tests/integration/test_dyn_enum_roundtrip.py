"""LIVE cross-repo round-trip harness for the dyn-enum-contract (AUTHORED; INERT).

The realization predicate made executable (telos :62-66 / ADR §10): a NEW or
renamed Asana enum_option round-trips into ``autom8y-data.verticals`` via
additive-upsert with existing ids + FK children intact within one sync cycle,
AND an empty/truncated read is hard-REFUSED (never applied). This is spec-as-test:
the assertion structure IS the acceptance target. NO consumer is built here.

This harness is DELIBERATELY INERT in sprint-1/3 CI (two-layer):
  1. ``@pytest.mark.integration`` keeps it out of the default ``tests/unit`` run.
  2. ``_requires_live_consumer`` SKIPS (never fails/errors) unless the env trio is
     set, and ``live_consumer_or_skip`` SKIPS on a pre-deploy 404. The consumer
     endpoint ``POST /api/v1/vocabularies/sync`` does not exist yet.

CON-007 preserved: sprint-3 exit is 207 gfr GREEN; this file contributes 0
collected failures. The review-rite (PT-07-live / signal-sifter, which HAS Bash)
runs it LIVE post-deploy; it goes GREEN when the consumer ships, or finds a real
gap.

[UNATTESTED -- DEFER-POST-HANDOFF: dyn-enum-contract/PT-07-live-roundtrip] -- the
harness is AUTHORED; its GREEN is the rite-disjoint review-rite's to attest LIVE
against the deployed consumer (STRONG belongs to the critic, not this station).

The EXACT live-run command (for the operator / review-rite)::

    cd /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-dynenum
    AUTOM8Y_DATA_URL=https://<deployed-consumer-host> \
    AUTOM8Y_DATA_API_KEY=<s2s-jwt> \
    DYN_ENUM_LIVE_ROUNDTRIP=1 \
    ./.venv/bin/python -m pytest tests/integration/test_dyn_enum_roundtrip.py \
        -m integration -v --timeout=60

Run against a STAGING consumer where possible. Against prod, the FK-inert,
idempotent, no-cleanup-needed marker key ``__dyn_enum_canary__`` is the discipline:
the no-delete invariant (autom8y-data ``services/vertical.py:9``) means a test
insert CANNOT be cleaned up, so a stable namespaced key that no FK child references
is used throughout (re-running upserts the same key -- no accumulation, no orphan).
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import pytest

from autom8_asana.contracts.vocabulary_sync import (
    VocabularyOption,
    VocabularySyncRequest,
    VocabularySyncResponse,
)
from autom8_asana.services.gid_push import (
    VOCAB_SYNC_ENABLED_ENV_VAR,
    push_vocabulary_to_data_service,
)

# ---------------------------------------------------------------------------
# Environment & skip guard (mirror test_schema_contract.py:46-54 + a mutation
# opt-in + an endpoint-existence probe)
# ---------------------------------------------------------------------------

_DATA_URL = os.environ.get("AUTOM8Y_DATA_URL", "").rstrip("/")  # consumer base URL
_DATA_API_KEY = os.environ.get("AUTOM8Y_DATA_API_KEY", "")  # S2S JWT bearer
_MUTATE_OK = os.environ.get("DYN_ENUM_LIVE_ROUNDTRIP") == "1"  # destructive opt-in

_requires_live_consumer = pytest.mark.skipif(
    not (_DATA_URL and _DATA_API_KEY and _MUTATE_OK),
    reason=(
        "dyn-enum LIVE round-trip: set AUTOM8Y_DATA_URL + AUTOM8Y_DATA_API_KEY + "
        "DYN_ENUM_LIVE_ROUNDTRIP=1 (the consumer /api/v1/vocabularies/sync must be "
        "deployed; this test mutates verticals additively)."
    ),
)

# Both marks apply to every test in this module: integration (out of the default
# unit run) + the env-trio skip (never a failure/error absent the live consumer).
pytestmark = [pytest.mark.integration, _requires_live_consumer]

# ---------------------------------------------------------------------------
# Contract-locked + consumer-side paths
# ---------------------------------------------------------------------------

# ADR-locked (Lock-1, CON-001): the generic plural sync path -- NEVER /verticals/sync.
_SYNC_PATH = "/api/v1/vocabularies/sync"

# Consumer read-back path for the id-stability / no-delete assertions. The exact
# route is a CONSUMER-side detail (sprint-2); confirmed at live-run against the
# deployed consumer. [UNATTESTED -- DEFER-POST-HANDOFF: verticals-list-path]
_VERTICALS_LIST_PATH = "/api/v1/verticals"

# The stable, namespaced, FK-inert idempotent canary key. No FK child references
# it; re-running upserts the same key (no accumulation, no orphan, no cleanup).
_CANARY_KEY = "__dyn_enum_canary__"
_CANARY_NEWKEY = "__dyn_enum_canary_v2__"

_TIMEOUT = 30.0


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_DATA_API_KEY}"}


def _post_sync(payload: dict[str, Any]) -> httpx.Response:
    """POST a (possibly hand-crafted / truncated) request directly to the consumer."""
    return httpx.post(
        f"{_DATA_URL}{_SYNC_PATH}", headers=_headers(), json=payload, timeout=_TIMEOUT
    )


def _sync_options(options: list[VocabularyOption]) -> VocabularySyncResponse:
    """POST a well-formed VocabularySyncRequest and parse the typed response."""
    request = VocabularySyncRequest(field_key="vertical", options=options)
    resp = _post_sync(request.model_dump(mode="json"))
    resp.raise_for_status()
    return VocabularySyncResponse.model_validate(resp.json())


def _get_verticals_key_to_id() -> dict[str, int]:
    """Read the consumer verticals as a ``{vertical_key: vertical_id}`` snapshot.

    The id-stability substrate: if every PRE key maps to the SAME id post-sync, the
    additive-upsert preserved ids (INT FK children on ``verticals.id`` still
    resolve) and retained keys (the STRING FK ``offers.category`` -> ``verticals.key``
    still resolves). This is the FK-safety proof observable via the verticals read.
    """
    resp = httpx.get(f"{_DATA_URL}{_VERTICALS_LIST_PATH}", headers=_headers(), timeout=_TIMEOUT)
    resp.raise_for_status()
    body = resp.json()
    rows = body["verticals"] if isinstance(body, dict) else body
    return {row["key"]: row["id"] for row in rows}


def _options_from_snapshot(key_to_id: dict[str, int]) -> list[VocabularyOption]:
    """Reconstruct the existing option-SET (NAME-keyed) from a verticals snapshot."""
    return [VocabularyOption(vertical_key=key, name=key) for key in key_to_id]


# ---------------------------------------------------------------------------
# Session fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def live_consumer_or_skip() -> str:
    """Endpoint-existence probe: SKIP (not fail) if the sync endpoint is absent.

    Pre-deploy the consumer returns 404 for POST /api/v1/vocabularies/sync; the
    harness skips rather than erroring so it is inert until the consumer ships.
    """
    try:
        probe = _post_sync({"field_key": "vertical", "options": []})
    except httpx.HTTPError as exc:  # network unreachable, DNS, TLS -- inert, not RED
        pytest.skip(f"consumer {_SYNC_PATH} unreachable ({exc!r}) -- run post-deploy")
    if probe.status_code == 404:
        pytest.skip(f"consumer {_SYNC_PATH} not deployed (404) -- run post-deploy")
    return _DATA_URL


@pytest.fixture(scope="session")
def pre_snapshot(live_consumer_or_skip: str) -> dict[str, int]:
    """PRE capture: the verticals ``{key: id}`` snapshot for the intact-check."""
    return _get_verticals_key_to_id()


# ---------------------------------------------------------------------------
# The round-trip legs (the realization predicate, per TDD §S3-3)
# ---------------------------------------------------------------------------


class TestDynEnumRoundtrip:
    """POS-NEW / POS-RENAME-SAMEKEY / POS-RENAME-NEWKEY / NEG-empty / NEG-truncated
    / IDEMPOTENCE -- the full realization predicate asserted end-to-end."""

    def test_pos_new_additive_upsert_preserves_ids(self, pre_snapshot: dict[str, int]) -> None:
        """POS-NEW: the full existing SET + __dyn_enum_canary__ -> inserted>=1,
        refused==[]; every PRE (key->id) unchanged (no id churn -- additive); the
        new canary key present. The positive round-trip leg."""
        options = _options_from_snapshot(pre_snapshot) + [
            VocabularyOption(vertical_key=_CANARY_KEY, name=_CANARY_KEY)
        ]
        response = _sync_options(options)

        assert response.refused == [], f"unexpected refusals: {response.refused}"
        assert response.inserted >= 1  # at least the new canary key

        post = _get_verticals_key_to_id()
        # Every PRE key->id is UNCHANGED (additive-upsert never churns ids).
        for key, pre_id in pre_snapshot.items():
            assert post.get(key) == pre_id, f"id churned for {key!r}: {pre_id} -> {post.get(key)}"
        # The new canary key is present.
        assert _CANARY_KEY in post

    def test_pos_rename_samekey_updates_name_id_stable(self, pre_snapshot: dict[str, int]) -> None:
        """POS-RENAME-SAMEKEY (name refresh): a display-name re-cased/whitespaced so
        normalize() yields the SAME key -> updated>=1; that row's id STABLE (same
        key -> same row); FK children on it intact. The UPDATE-name leg."""
        # Ensure the canary exists, then re-push it (same key, refreshed display).
        _sync_options([VocabularyOption(vertical_key=_CANARY_KEY, name=_CANARY_KEY)])
        before = _get_verticals_key_to_id()
        canary_id_before = before[_CANARY_KEY]

        response = _sync_options(
            [VocabularyOption(vertical_key=_CANARY_KEY, name=f"{_CANARY_KEY} (refreshed)")]
        )
        assert response.refused == []
        assert response.updated >= 1  # same key -> UPDATE, not INSERT

        after = _get_verticals_key_to_id()
        assert after[_CANARY_KEY] == canary_id_before  # id STABLE across name refresh

    def test_pos_rename_newkey_retains_old_key_no_delete(
        self, pre_snapshot: dict[str, int]
    ) -> None:
        """POS-RENAME-NEWKEY (true rename): an existing option renamed to a NEW
        normalized key -> inserted>=1 (new key); the OLD key+id RETAINED (no
        delete); FK children on the OLD key still resolve. Proves no-delete/FK-safe
        under rename."""
        # Seed the OLD canary key, capture its id.
        _sync_options([VocabularyOption(vertical_key=_CANARY_KEY, name=_CANARY_KEY)])
        old_id = _get_verticals_key_to_id()[_CANARY_KEY]

        # "Rename" to a NEW key (additive -- the OLD key is NOT deleted).
        response = _sync_options(
            [VocabularyOption(vertical_key=_CANARY_NEWKEY, name=_CANARY_NEWKEY)]
        )
        assert response.refused == []
        assert response.inserted >= 1  # the new key is inserted

        after = _get_verticals_key_to_id()
        assert after.get(_CANARY_KEY) == old_id  # OLD key + id RETAINED (no delete)
        assert _CANARY_NEWKEY in after  # NEW key present alongside the old

    async def test_neg_empty_producer_refuses_nothing_reaches_consumer(
        self, pre_snapshot: dict[str, int], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """NEG-empty (producer): None/[] fed to the producer -> producer REFUSES
        (VocabSyncRefused{empty}); NOTHING reaches the consumer; verticals UNCHANGED
        vs PRE. Defense-in-depth (already unit-proven sprint-1), asserted live."""
        monkeypatch.setenv(VOCAB_SYNC_ENABLED_ENV_VAR, "true")
        result = await push_vocabulary_to_data_service(
            None, data_service_url=_DATA_URL, auth_token=_DATA_API_KEY
        )
        assert result is False  # producer refused BEFORE any transport

        post = _get_verticals_key_to_id()
        for key, pre_id in pre_snapshot.items():
            assert post.get(key) == pre_id  # verticals UNCHANGED -- nothing applied

    def test_neg_truncated_consumer_refuses_coverage(self, pre_snapshot: dict[str, int]) -> None:
        """NEG-truncated (consumer teeth): a grossly-truncated request POSTed
        DIRECTLY to the consumer (bypass the producer) -> the consumer's own FR-004
        3-edge coverage refuse fires (4xx OR all-refused); verticals UNCHANGED. The
        authoritative refuse lives where the FK data lives (sprint-1 D-2 boundary)."""
        # A single-option set when the real population is ~40: if applied additively
        # this is benign, but a set that OMITS FK-referenced keys must trip the
        # consumer's referential-coverage hard-refuse (ADR §8 FR-004).
        truncated = {
            "field_key": "vertical",
            "options": [{"vertical_key": _CANARY_KEY, "name": _CANARY_KEY}],
        }
        resp = _post_sync(truncated)

        refused_coverage = False
        if resp.status_code >= 400:
            refused_coverage = True  # hard 4xx coverage refuse
        elif resp.status_code == 200:
            body = VocabularySyncResponse.model_validate(resp.json())
            # A coverage refuse surfaces as refused rows for the omitted referenced
            # keys (never a silent apply that would orphan FK children).
            refused_coverage = bool(body.refused)
        assert refused_coverage, (
            "consumer did NOT refuse a coverage-truncated set -- FR-004 3-edge "
            f"referential-coverage teeth absent (status={resp.status_code})"
        )

        post = _get_verticals_key_to_id()
        for key, pre_id in pre_snapshot.items():
            assert post.get(key) == pre_id  # verticals UNCHANGED under a refused set

    def test_idempotence_second_run_is_noop(self, pre_snapshot: dict[str, int]) -> None:
        """IDEMPOTENCE (NFR-002): re-run POS-NEW's healthy SET -> 2nd run
        inserted==0, refused==[], ids identical. The no-op-suppressing upsert."""
        options = _options_from_snapshot(pre_snapshot) + [
            VocabularyOption(vertical_key=_CANARY_KEY, name=_CANARY_KEY)
        ]
        _sync_options(options)  # 1st run (converge)
        before = _get_verticals_key_to_id()

        second = _sync_options(options)  # 2nd run (must be a no-op)
        assert second.inserted == 0  # nothing new to insert
        assert second.refused == []

        after = _get_verticals_key_to_id()
        assert after == before  # ids identical -- no churn on the idempotent re-run
