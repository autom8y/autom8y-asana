"""BR-3 UNIT-VERTICAL-CARRY: two-sided discriminating proofs (DIC/SUB-1).

The bug (BR-3): a freshly-created unit was a bare subtask of ``unit_holder`` and
was never a member of the Business Units project, so it carried none of the
project's custom fields. The old ``_write_vertical_custom_field`` read the fresh
task's ``custom_fields`` (empty) and silently no-op'd -> the unit's ``vertical``
column (unit.py:64 -> ``cf:Vertical``) stayed null. ``vertical`` is one of the
unit entity's two index key columns, so the unit was unresolvable on its 2nd key
and ``POST /v1/resolve/unit`` returned NOT_FOUND.

The fix (Option A): add the unit to the Business Units project pinned to the
Onboarding section BEFORE writing the Vertical CF, and resolve the CF gid +
enum-option gid from the PROJECT DEFINITION (race-free), never the fresh task.

These proofs are two-sided against the REALIZED write (transport seam + readback
oracle from #330) and against the section-registry / classifier that drive the
downstream consumers (L2 index, L3 resolve, account-status ledger). The three
LIVE legs (L1 readback on a real task, L2 appears-in-index, L3 resolves) are
UV-P and owed to SUB-3 -- see the module ``UV-P`` note below.

[UV-P: L1/L2/L3 live three-leg acceptance against real Asana (create a chiropractic
unit -> readback cf:Vertical==Chiropractic, appears in /unit index, resolves via
POST /v1/resolve/unit active_only=True; two-sided: a unit created WITHOUT the
project-add FAILS readback+resolve) | METHOD: SUB-3 GATE-2 live certification with
ASANA_BOT_PAT against the canary tenant | REASON: no live Asana creds at the build
seat; the in-harness half (transport-seam body + strict-subset readback oracle +
section/classifier structural link) is proven here]
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import polars as pl
from tests._shared.cf_write_readback import (
    apply_write_body,
    captured_put_body,
    read_custom_field,
    real_tasks_client,
)

# Circular-import ordering guard (scar): importing IntakeCreateService cold
# fails -- api.routes.__init__ pulls intake_create, which imports back out of
# the partially-initialized service module. Driving the route package FIRST
# resolves the cycle from the side that succeeds. Without this the whole file
# ERRORs at collection under single-file / pytest-split selection while passing
# in a full run that imported the API earlier.
import autom8_asana.api.routes  # noqa: F401, E402  -- import-order guard
from autom8_asana.core.project_registry import UNIT_PROJECT
from autom8_asana.lambda_handlers.traffic_offer_divergence_tripwire import (
    CANARY_SENTINEL_PHONE,
)
from autom8_asana.reconciliation.section_registry import (
    _RECEIPT_NAME_TO_GID,
    EXCLUDED_SECTION_GIDS,
    UNIT_SECTION_GIDS,
)
from autom8_asana.services.gid_push import extract_status_from_dataframe
from autom8_asana.services.intake_create_service import (
    ONBOARDING_SECTION_NAME,
    IntakeCreateService,
)

# A REAL enum vertical (A'-3): "chiropractic" is one of the field's ~56-61
# live options. NEVER "synthetic-canary" -- that is absent from the option set
# and would score a false RED on the enum match.
_REAL_VERTICAL = "chiropractic"
_UNIT_GID = "1207000000000001"


def _project_settings_client(
    tasks: object,
    *,
    field_name: str = "Vertical",
    options: list[dict] | None = None,
) -> object:
    """A minimal AsanaClient shim: real ``tasks`` + a project-definition stub.

    The Vertical field + enum options are served from
    ``custom_fields.get_settings_for_project_async`` (the PROJECT DEFINITION,
    O6), so the fresh task is never consulted for resolution.
    """
    from types import SimpleNamespace

    if options is None:
        options = [
            {"gid": "enum_dental", "name": "Dental"},
            {"gid": "enum_chiropractic", "name": "Chiropractic"},
            {"gid": "enum_medical", "name": "Medical"},
        ]
    collector = MagicMock()
    collector.collect = AsyncMock(
        return_value=[
            {"custom_field": {"gid": "cf_vertical", "name": field_name, "enum_options": options}},
        ]
    )
    custom_fields = MagicMock()
    custom_fields.get_settings_for_project_async = MagicMock(return_value=collector)
    return SimpleNamespace(tasks=tasks, custom_fields=custom_fields, projects=MagicMock())


# ---------------------------------------------------------------------------
# L1 (in-harness half): the REALIZED Vertical write reads back == the option
# ---------------------------------------------------------------------------


class TestVerticalWriteReadbackRealized:
    """The real write body, applied to a project-member task, reads back right.

    Uses the #330 transport-seam harness + strict-subset readback oracle: the
    production ``TasksClient.update_async`` marshaling runs for real (only
    ``_http.put`` mocked), and the captured body is read back through the
    PRODUCTION resolver extractor. The receipt is the value that comes back out,
    never the HTTP status (Asana 200s on the broken body too).
    """

    async def test_realized_write_reads_back_as_the_real_vertical(self) -> None:
        """(+) leg: the body _write_vertical_custom_field emits, applied to a
        unit that carries the inherited Vertical CF, reads back == Chiropractic.
        """
        tasks, mock_http = real_tasks_client()
        service = IntakeCreateService(_project_settings_client(tasks))

        await service._write_vertical_custom_field(_UNIT_GID, _REAL_VERTICAL)

        body = captured_put_body(mock_http)

        # The unit AS IT EXISTS after project membership: it carries the
        # inherited Vertical enum field (with its options). This is the read
        # doc the resolver would fetch.
        member_task = {
            "gid": _UNIT_GID,
            "custom_fields": [
                {
                    "gid": "cf_vertical",
                    "name": "Vertical",
                    "enum_options": [
                        {"gid": "enum_dental", "name": "Dental"},
                        {"gid": "enum_chiropractic", "name": "Chiropractic"},
                        {"gid": "enum_medical", "name": "Medical"},
                    ],
                },
            ],
        }
        applied = apply_write_body(member_task, body)
        assert read_custom_field(applied, "Vertical") == "Chiropractic"

    async def test_broken_bodies_read_back_none(self) -> None:
        """(-) leg: the two CLASS-DEFECT-CF-WRITE shapes read back None.

        The strict-subset oracle applies nothing for the ``data=`` double-nest
        or the nested ``{"gid": opt}`` enum read-shape, so a defective write
        can never manufacture a false GREEN. This is what makes the (+) leg
        above non-vacuous.
        """
        member_task = {
            "gid": _UNIT_GID,
            "custom_fields": [
                {
                    "gid": "cf_vertical",
                    "name": "Vertical",
                    "enum_options": [{"gid": "enum_chiropractic", "name": "Chiropractic"}],
                },
            ],
        }
        # GATE-1 double-nest: {"data": {"data": {...}}}
        double_nest = {"data": {"data": {"custom_fields": {"cf_vertical": "enum_chiropractic"}}}}
        # F-1 nested enum READ shape written back: {gid: {"gid": opt}}
        nested_enum = {"data": {"custom_fields": {"cf_vertical": {"gid": "enum_chiropractic"}}}}

        assert read_custom_field(apply_write_body(member_task, double_nest), "Vertical") is None
        assert read_custom_field(apply_write_body(member_task, nested_enum), "Vertical") is None


# ---------------------------------------------------------------------------
# L2 / L3 structural link: Onboarding is PROCESSED, Templates is EXCLUDED
# ---------------------------------------------------------------------------


class TestSectionPlacementDrivesResolvability:
    """The section a unit lands in is what makes L2/L3 pass or silently fail.

    The unit index (L2) and ``/v1/resolve/unit`` (L3) are built by the DENYLIST
    reconciliation processor, which EXCLUDES the Templates section. A unit
    pinned to Onboarding is processed (resolvable); a section-less add falls
    into Templates and is silently dropped -- the exact silent-green (L1 passes,
    L3 NOT_FOUND) that placement exists to prevent.
    """

    def test_onboarding_is_processed_templates_is_excluded(self) -> None:
        onboarding = _RECEIPT_NAME_TO_GID[ONBOARDING_SECTION_NAME]
        templates = _RECEIPT_NAME_TO_GID["Templates"]

        # (+) Onboarding: in the processed unit set, NOT excluded -> resolvable.
        assert onboarding in UNIT_SECTION_GIDS
        assert onboarding not in EXCLUDED_SECTION_GIDS

        # (-) Templates: excluded, NOT processed -> the silent-green sink.
        assert templates in EXCLUDED_SECTION_GIDS
        assert templates not in UNIT_SECTION_GIDS


# ---------------------------------------------------------------------------
# account_status exclusion: the canary unit never enters the ledger
# ---------------------------------------------------------------------------


class TestCanarySentinelAccountStatusExclusion:
    """Two-sided: the canary sentinel phone is dropped at the row->entry funnel.

    BR-3 adds the canary unit to the Business Units project, whose pipeline_type
    is "unit" -- so, absent the exclusion, the synthetic unit would emit a row
    into the business-of-record account-status ledger. The exclusion (mirroring
    the R7 tripwire, #326) drops it. Uses the REAL unit classifier (Onboarding
    -> activating) so the drop is provably the phone-match, not some other
    filter.
    """

    @staticmethod
    def _row(phone: str) -> pl.DataFrame:
        # Identical active-section row; ONLY the phone differs between arms.
        return pl.DataFrame(
            {
                "office_phone": [phone],
                "vertical": [_REAL_VERTICAL],
                "section": [ONBOARDING_SECTION_NAME],
            }
        )

    def test_real_phone_emits_an_entry(self) -> None:
        """(+) control: an identical row with a REAL phone emits one entry.

        Proves the row is genuinely classifiable/active -- so a drop of the
        sentinel arm can only be the exclusion, never a background filter.
        """
        result = extract_status_from_dataframe(self._row("+15551239876"), UNIT_PROJECT, "unit")
        assert len(result) == 1
        assert result[0]["phone"] == "+15551239876"
        assert result[0]["account_activity"] == "activating"

    def test_sentinel_phone_is_excluded(self) -> None:
        """(-) leg: the SAME row with the canary sentinel phone emits nothing."""
        result = extract_status_from_dataframe(
            self._row(CANARY_SENTINEL_PHONE), UNIT_PROJECT, "unit"
        )
        assert result == []

    def test_mixed_frame_keeps_only_the_real_row(self) -> None:
        """A frame with both rows emits ONLY the real one -- no synthetic leak."""
        df = pl.DataFrame(
            {
                "office_phone": [CANARY_SENTINEL_PHONE, "+15551239876"],
                "vertical": [_REAL_VERTICAL, _REAL_VERTICAL],
                "section": [ONBOARDING_SECTION_NAME, ONBOARDING_SECTION_NAME],
            }
        )
        result = extract_status_from_dataframe(df, UNIT_PROJECT, "unit")
        phones = {e["phone"] for e in result}
        assert phones == {"+15551239876"}
        assert CANARY_SENTINEL_PHONE not in phones
