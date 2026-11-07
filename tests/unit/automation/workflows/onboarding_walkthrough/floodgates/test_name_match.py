"""D9 clinic-name predicate: two-sided cases plus a planted control (FORK-S1 rule).

``assert_clinic_name_confirmed`` passes only when the PLAY title's clinic part (T), the
parent Business name (B) and ``--clinic`` (C) agree under ``canon`` (NFC, zero-width
dropped, whitespace collapsed). Every visible difference refuses.

The planted control rebuilds the module with the equality test swapped for a prefix or a
token-Jaccard rule. Under those weaker rules the near-miss and the location-suffix cases
PASS, so the refusals below come from the real predicate and not from the fixtures.

Synthetic names only: this repository is public.
"""

from __future__ import annotations

import inspect
import types
import unicodedata
from unittest.mock import patch

import pytest

from autom8_asana.automation.workflows.onboarding_walkthrough.floodgates import (
    name_match,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.floodgates.name_match import (
    ClinicNameMismatch,
    assert_clinic_name_confirmed,
    canon,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.office_resolution import (
    BusinessResolution,
)

PLAY_GID = "1200000000000007"
BUSINESS_GID = "1200000000000042"
NAME = "Harbor Light Chiropractic"


def _title(clinic_part: str) -> str:
    return f"PLAY: Custom Calendar Integration — {clinic_part}"


def _resolution(
    business_name: str | None,
    *,
    method: str = "hierarchy",
    business_gid: str | None = BUSINESS_GID,
) -> BusinessResolution:
    return BusinessResolution(
        business_gid=business_gid,
        company_id="00000000-0000-4000-8000-000000000000",
        method=method,  # type: ignore[arg-type]
        ancestor_depth=1,
        business_name=business_name,
    )


def _confirm(module: types.ModuleType, *, title: str | None, business: str | None, clinic: str):
    return module.assert_clinic_name_confirmed(
        play_gid=PLAY_GID, title=title, resolution=_resolution(business), clinic_arg=clinic
    )


# ------------------------------------------------------------------------------- canon


class TestCanon:
    def test_folds_only_invisible_differences(self) -> None:
        nfd = unicodedata.normalize("NFD", "Café Harbor Light")
        assert nfd != "Café Harbor Light"  # the fixture really is NFD
        assert canon(nfd) == "Café Harbor Light"
        assert canon(" Harbor\u200b Light  Chiropractic\ufeff ") == NAME
        assert canon(None) == ""

    def test_keeps_visible_differences(self) -> None:
        assert canon("Harbor Light chiropractic") != canon(NAME)  # case is visible
        assert canon("Ｈarbor Light Chiropractic") != canon(NAME)  # full-width (no NFKC)


# ------------------------------------------------------------------------------- PASS


class TestPass:
    def test_identical_names_pass_and_return_the_business_name(self) -> None:
        assert _confirm(name_match, title=_title(NAME), business=NAME, clinic=NAME) == NAME

    def test_invisible_differences_pass_and_return_canonical_business(self) -> None:
        """B has a double space, a zero-width character and NFD; T and C are plain NFC."""
        clinic = "Café Harbor Light Chiropractic"
        business = unicodedata.normalize("NFD", "Café Harbor  Light Chiropractic\u200b")
        assert business != clinic
        result = _confirm(name_match, title=_title(clinic), business=business, clinic=clinic)
        assert result == clinic
        assert unicodedata.is_normalized("NFC", result)


# ------------------------------------------------------------------------------- REFUSE

REFUSE_CASES = {
    # (title clinic part, business name, --clinic)
    "centre_vs_center": (
        "Harbor Light Family Wellness Centre",
        "Harbor Light Family Wellness Center",
        "Harbor Light Family Wellness Centre",
    ),
    "holder_suffix": (NAME, f"{NAME} PLAYS/REQUESTS ✅", NAME),
    "case_only": (NAME, "Harbor Light chiropractic", NAME),
    "clinic_arg_differs": (NAME, NAME, "Harbor Light"),
    "location_suffix": (NAME, f"{NAME} — Downtown", NAME),
    "empty_business": (NAME, "", NAME),
    "missing_business_name": (NAME, None, NAME),
}


class TestRefuse:
    @pytest.mark.parametrize("case", sorted(REFUSE_CASES))
    def test_visible_difference_refuses(self, case: str) -> None:
        title_part, business, clinic = REFUSE_CASES[case]
        with pytest.raises(ClinicNameMismatch, match="D9") as excinfo:
            _confirm(name_match, title=_title(title_part), business=business, clinic=clinic)
        message = str(excinfo.value)
        assert PLAY_GID in message
        assert BUSINESS_GID in message
        assert f"business={ascii(business)}" in message
        assert f"--clinic={ascii(clinic)}" in message
        assert "ask the operator" in message

    def test_title_none_refuses(self) -> None:
        with pytest.raises(ClinicNameMismatch, match="D9"):
            _confirm(name_match, title=None, business=NAME, clinic=NAME)

    def test_title_without_clinic_part_refuses(self) -> None:
        with pytest.raises(ClinicNameMismatch, match="D9"):
            _confirm(
                name_match, title="PLAY: Custom Calendar Integration", business=NAME, clinic=NAME
            )

    @pytest.mark.parametrize(
        ("method", "business_gid"), [("phone", BUSINESS_GID), ("hierarchy", None)]
    )
    def test_no_business_parent_refuses(self, method: str, business_gid: str | None) -> None:
        """A phone match is not a parent; a walk with no Business match has no parent."""
        with pytest.raises(ClinicNameMismatch, match="no Business parent") as excinfo:
            assert_clinic_name_confirmed(
                play_gid=PLAY_GID,
                title=_title(NAME),
                resolution=_resolution(NAME, method=method, business_gid=business_gid),
                clinic_arg=NAME,
            )
        assert "D9" in str(excinfo.value)
        assert "ask the operator" in str(excinfo.value)

    def test_message_escapes_invisible_characters(self) -> None:
        """ascii() makes a zero-width character visible in the refusal text."""
        business = f"{NAME}\u200b — Downtown"
        with pytest.raises(ClinicNameMismatch) as excinfo:
            _confirm(name_match, title=_title(NAME), business=business, clinic=NAME)
        assert "\\u200b" in str(excinfo.value)

    def test_log_event_carries_gids_never_names(self) -> None:
        with (
            patch.object(name_match, "logger") as logger,
            pytest.raises(ClinicNameMismatch),
        ):
            _confirm(name_match, title=_title(NAME), business=f"{NAME} — Downtown", clinic=NAME)
        logger.warning.assert_called_once()
        kwargs = logger.warning.call_args.kwargs
        assert kwargs["play_gid"] == PLAY_GID
        assert kwargs["business_gid"] == BUSINESS_GID
        assert not any("Harbor" in str(v) for v in kwargs.values())

    def test_is_a_runtime_error(self) -> None:
        """The batch records RuntimeError subclasses as failed and exits non-zero."""
        assert issubclass(ClinicNameMismatch, RuntimeError)


# ------------------------------------------------------------------------------- planted control

_REAL_RULE = "if not ct or not cb or ct != cb or cc != cb:"


def _mutant(rule: str) -> types.ModuleType:
    """Rebuild ``name_match`` from its own source with the comparison line swapped."""
    source = inspect.getsource(name_match)
    assert source.count(_REAL_RULE) == 1, "the D9 comparison moved; update the planted control"
    module = types.ModuleType("name_match_planted_control")
    module.__dict__["_jaccard"] = _jaccard
    exec(compile(source.replace(_REAL_RULE, rule), module.__name__, "exec"), module.__dict__)  # noqa: S102 -- test-only mutant of the module under test
    return module


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(a.lower().split()), set(b.lower().split())
    return len(sa & sb) / len(sa | sb) if sa | sb else 0.0


PREFIX_RULE = "if not ct or not cb or not (cb.startswith(ct) and cb.startswith(cc)):"
JACCARD_RULE = "if not ct or not cb or _jaccard(ct, cb) < 0.6 or _jaccard(cc, cb) < 0.6:"


class TestPlantedControl:
    @pytest.mark.parametrize(
        ("rule", "lets_through"),
        [
            (PREFIX_RULE, ("location_suffix", "holder_suffix")),
            (JACCARD_RULE, ("centre_vs_center", "location_suffix")),
        ],
        ids=["prefix", "jaccard"],
    )
    def test_weaker_rule_lets_the_refused_cases_through(
        self, rule: str, lets_through: tuple[str, ...]
    ) -> None:
        mutant = _mutant(rule)
        # Sanity: the mutant still accepts the identical case (it is a working rule).
        assert _confirm(mutant, title=_title(NAME), business=NAME, clinic=NAME) == NAME
        for case in lets_through:
            title_part, business, clinic = REFUSE_CASES[case]
            # The weaker rule PASSES the case ...
            _confirm(mutant, title=_title(title_part), business=business, clinic=clinic)
            # ... and the real predicate refuses the very same inputs.
            with pytest.raises(ClinicNameMismatch, match="D9"):
                _confirm(name_match, title=_title(title_part), business=business, clinic=clinic)
