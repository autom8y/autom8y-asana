"""F-9 durable observation semantics -- the two-sided proof suite (W-F lane).

THE DEFECT (F-9, ratified: CERT-sarm-1601-RECERT-43aa30da-2026-08-13 §5;
PACKET-D5-sitting-2026-08-13 §3.4):
    The pre-cure resolve producer ALWAYS stamped ``has_unit`` /
    ``has_contact_holder`` explicitly onto the wire (``bool = False`` model
    defaults + unconditional constructor kwargs + swallowed subtask faults).
    The wire therefore never omitted them, so ordinary production index lag
    (a business task indexed before its sub-entities -> empty subtask
    listing) rendered as an ASSERTED ``has_unit: false``. The consuming W5-3
    first-create tripwire (calendly-intake ``tripwire/probe.py``) correctly
    reads an asserted false as a positive written(True) != read(False)
    contradiction -> MISMATCH -> unattended revert of the client-facing
    subscription at ``mode: live``. Its consumer-side F-3 cure
    (``read_field``/``model_fields_set``) is blind here BY DESIGN: it can
    only downgrade a field the wire OMITS.

THE CURE (this suite proves it two-sided, per the ratified semantics
"tri-state / exclude_unset / 5xx-on-subtask-fault"):
    * tri-state -- ``bool | None = None``: UNOBSERVED is representable.
    * exclude-unset -- an unobserved field never reaches the wire (model
      serializer, scoped to the two fields).
    * 5xx-on-subtask-fault -- a faulted listing is an instrument fault,
      never data: 503, never an asserted false.

TWO-SIDED DISCIPLINE (discriminating-canary doctrine):
    * BITES on the defect: a genuinely malformed first-create (a non-empty
      listing observed WITHOUT the holder the create response asserted)
      still puts an asserted ``false`` on the wire -- the tripwire keeps
      its teeth (test_genuinely_malformed_first_create_keeps_its_teeth).
    * QUIET on the healthy path: a merely index-lagged first-create (empty
      listing) is OMITTED from the wire and resolves to ABSENT/UNOBSERVED
      at the real consumer model -- it can never fabricate a MISMATCH
      (test_index_lagged_* / test_lag_wire_reads_unobserved_*).

SOLE DISCRIMINATOR (S5): key-presence on the wire, surfaced to the consumer
as ``model_fields_set`` membership -- the exact predicate the probe's
``read_field`` reads (probe.py:159-164). The cheap signals are proven blind
in test_cheap_signal_getattr_is_blind_fields_set_discriminates: HTTP 200,
``found=true`` and ``getattr(resp, "has_unit") == False`` are IDENTICAL for
"asserted absent" and "unobserved" -- only fields_set discriminates.

RED-BEFORE / GREEN-AFTER: this suite was executed against the pre-cure code
path (origin/main 844bbde5) and the lag + fault legs FAILED there (the wire
carried ``has_unit: false`` on an empty listing; the fault path returned
200-with-false). Receipts in the S-09 disposition artifact.

Authored under seat-materialization: general-purpose agent preloaded
verbatim with integrity-architect.md + pipeline-steward.md (dre unseated in
dispatcher; pythia Option-5 2026-08-18).
"""

from __future__ import annotations

# The REAL consumer model: the SDK class AsanaIntakeClient.resolve_business_async
# parses the wire into, and the exact object the W5-3 probe's read_field()
# inspects. Parsing the realized wire bytes through it is the cross-seam leg
# of this proof -- not a stand-in model.
from autom8y_core.models.asana_service import (
    BusinessResolveResponse as ConsumerBusinessResolveResponse,
)

# Re-export the fixtures the tests below consume (pytest resolves them by
# name from the imported module's fixture registry only if conftest-visible;
# importing them explicitly keeps this module self-sufficient).
from tests.unit.api.routes.test_intake_resolve import (  # noqa: F401
    AUTH_HEADER,
    BUSINESS_GID,
    BUSINESS_MEMBERSHIPS,
    _make_mock_asana_client,
    _reset_singletons,
    _resolve_patches,
    app,
    client,
)

_TASK_DATA = {
    "gid": BUSINESS_GID,
    "name": "Test Dental",
    "custom_fields": [],
    "memberships": BUSINESS_MEMBERSHIPS,
}


def _post_resolve(client, mock_asana):
    patches = _resolve_patches(mock_client=mock_asana, index_gid=BUSINESS_GID)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
        return client.post(
            "/v1/resolve/business",
            json={"office_phone": "+15551234567"},
            headers=AUTH_HEADER,
        )


class TestF9IndexLagIsUnobserved:
    """The QUIET side: lag must not be representable as an assertion."""

    def test_index_lagged_first_create_is_unobserved_on_the_wire(self, client) -> None:
        """EMPTY subtask listing (the index-lag shape: parent indexed before
        its sub-entities) -> the wire OMITS has_unit/has_contact_holder.

        RED on the pre-cure path: the wire carried ``"has_unit": false`` --
        the exact fuel of the F-9 unattended production revert.
        """
        mock_asana = _make_mock_asana_client(task_data=_TASK_DATA, subtasks=[])
        resp = _post_resolve(client, mock_asana)

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["found"] is True
        assert data["task_gid"] == BUSINESS_GID
        # The realized wire: key-ABSENCE, not key-with-false.
        assert "has_unit" not in data
        assert "has_contact_holder" not in data

    def test_lag_wire_reads_unobserved_at_the_real_consumer(self, client) -> None:
        """Cross-seam leg: parse the realized lag wire through the REAL
        consumer SDK model. The probe's read_field() predicate is
        ``name not in model_fields_set`` (probe.py:159-164) -> ABSENT ->
        UNOBSERVED -> an unobserved leg cannot revert production."""
        mock_asana = _make_mock_asana_client(task_data=_TASK_DATA, subtasks=[])
        resp = _post_resolve(client, mock_asana)

        parsed = ConsumerBusinessResolveResponse.model_validate(resp.json()["data"])
        assert "has_unit" not in parsed.model_fields_set
        assert "has_contact_holder" not in parsed.model_fields_set

    def test_cheap_signal_getattr_is_blind_fields_set_discriminates(self, client) -> None:
        """S5 sole-discriminator proof. The cheap signals -- HTTP 200,
        found=true, and getattr(parsed, "has_unit") -- are IDENTICAL between
        an index-lagged create (unobserved) and a genuinely unit-less create
        (asserted false). Only fields_set membership separates them. getattr
        is literally the blind instrument that armed F-3/F-9."""
        lag_resp = _post_resolve(client, _make_mock_asana_client(task_data=_TASK_DATA, subtasks=[]))
        asserted_resp = _post_resolve(
            client,
            _make_mock_asana_client(
                task_data=_TASK_DATA,
                subtasks=[{"gid": "sub_ch", "name": "contact_holder"}],
            ),
        )

        lag = ConsumerBusinessResolveResponse.model_validate(lag_resp.json()["data"])
        asserted = ConsumerBusinessResolveResponse.model_validate(asserted_resp.json()["data"])

        # Cheap signals: blind (identical on both arms).
        assert lag_resp.status_code == asserted_resp.status_code == 200
        assert lag.found is asserted.found is True
        assert lag.has_unit is False  # schema default -- NOT an assertion
        assert asserted.has_unit is False  # asserted false -- indistinguishable here
        # The sole discriminator: fields_set membership.
        assert "has_unit" not in lag.model_fields_set
        assert "has_unit" in asserted.model_fields_set


class TestF9TeethArePreserved:
    """The BITE side: a genuinely malformed first-create must still trip."""

    def test_genuinely_malformed_first_create_keeps_its_teeth(self, client) -> None:
        """A NON-EMPTY listing observed WITHOUT a unit_holder is a REAL
        observation of absence: the wire must carry an asserted
        ``has_unit: false`` so the probe's written(True) != read(False)
        contradiction still fires on a create whose unit write was lost."""
        mock_asana = _make_mock_asana_client(
            task_data=_TASK_DATA,
            subtasks=[{"gid": "sub_ch", "name": "contact_holder"}],
        )
        resp = _post_resolve(client, mock_asana)

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["has_unit"] is False  # asserted, on the wire
        assert data["has_contact_holder"] is True

        parsed = ConsumerBusinessResolveResponse.model_validate(data)
        assert "has_unit" in parsed.model_fields_set  # the probe CAN contradict

    def test_healthy_first_create_asserts_both_true(self, client) -> None:
        """Healthy path stays healthy: both holders observed -> both asserted
        true on the wire; probe reads MATCH."""
        mock_asana = _make_mock_asana_client(
            task_data=_TASK_DATA,
            subtasks=[
                {"gid": "sub_u", "name": "unit_holder"},
                {"gid": "sub_ch", "name": "contact_holder"},
            ],
        )
        resp = _post_resolve(client, mock_asana)

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["has_unit"] is True
        assert data["has_contact_holder"] is True


class TestF9SubtaskFaultFailsClosed:
    """5xx-on-subtask-fault: an instrument fault is never data."""

    def test_subtask_fault_is_503_never_a_false_assertion(self, client) -> None:
        """A faulted subtask listing -> 503 SUBTASK_OBSERVATION_FAILED.

        RED on the pre-cure path: the fault was swallowed with a warning and
        the response carried 200 + ``has_unit: false`` -- a fabricated
        positive contradiction handed to the first-create tripwire.
        """
        mock_asana = _make_mock_asana_client(
            task_data=_TASK_DATA,
            raise_on_subtasks=RuntimeError("asana subtasks listing exploded"),
        )
        resp = _post_resolve(client, mock_asana)

        assert resp.status_code == 503
        assert "SUBTASK_OBSERVATION_FAILED" in resp.text
        # And emphatically NOT a 200 with fabricated sub-entity state.
        assert "has_unit" not in resp.text
