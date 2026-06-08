"""Unit tests for the S7-GATE-FIDELITY Project-arm content-binding.

These tests pin the load-bearing assertion of the deploy-gate canary: a 2xx
carrying an empty/wrong frame on the PROJECT arm MUST fail the gate (defeat the
HTTP-2xx body-blind liveness-masquerade), while a genuinely-empty honest-complete
project (zero rows + meta.honest_empty=True) is an ATTESTED valid result.

The canary lives under scripts/canary/ (not an importable package), so the module
is loaded by file path via importlib. Only the pure classification/gate functions
are exercised — no network, no auth, no event loop.

Scope discipline: the SECTION arm is column-contract-EXEMPT and has NO content
criterion (cleared on the disaggregated honest-EMF/cause signal + the PQ-5
section_gid guard-or-seed decision, NOT column content). These tests therefore
assert ONLY the Project-arm binding and that the Section arm carries no content
gate.
"""

from __future__ import annotations

import base64
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any

import pytest

# --- Load the canary module by path (scripts/canary is not a package) ---------
_REPO_ROOT = Path(__file__).resolve().parents[3]
_CANARY_PATH = _REPO_ROOT / "scripts" / "canary" / "receiver_bulk_fanout_deploy_gate.py"
_CANARY_MOD_NAME = "_canary_deploy_gate_under_test"


def _load_canary() -> Any:
    spec = importlib.util.spec_from_file_location(_CANARY_MOD_NAME, _CANARY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Register BEFORE exec: the @dataclass decorator resolves field annotations
    # (e.g. Counter[str] under `from __future__ import annotations`) via
    # sys.modules[cls.__module__]; an unregistered module makes that lookup
    # return None and the decorator raises AttributeError.
    sys.modules[_CANARY_MOD_NAME] = module
    spec.loader.exec_module(module)
    return module


canary = _load_canary()


# --- Body envelope builders (canonical double-envelope, models.py:430) --------


def _envelope(rows: list[dict[str, Any]], meta: dict[str, Any]) -> dict[str, Any]:
    return {"data": {"data": rows, "meta": meta}}


def _full_row(**overrides: Any) -> dict[str, Any]:
    row = {"gid": "111", "office_phone": "555-0100", "vertical": "dental"}
    row.update(overrides)
    return row


# --- The contract columns are exactly the consumer's authoritative set --------


def test_contract_columns_match_consumer_attestation_set():
    # Mirrors autom8/apis/asana_api/satellite/getdf_signals.py:77 _CONTRACT_COLUMNS.
    assert canary.PROJECT_CONTRACT_COLUMNS == ("office_phone", "vertical", "gid")


# --- Happy path: a real frame with the full contract is OK --------------------


def test_full_contract_frame_is_ok():
    body = _envelope([_full_row(), _full_row(gid="222")], {"honest_empty": False})
    cls, reason = canary._classify_project_content(body)
    assert cls == "ok"
    assert reason == ""


# --- The masquerade: 2xx empty WITHOUT honest_empty attestation = violation ---


def test_empty_frame_without_honest_empty_is_violation():
    body = _envelope([], {"honest_empty": False})
    cls, reason = canary._classify_project_content(body)
    assert cls == "violation"
    assert reason == "empty_frame_without_honest_empty"


def test_empty_frame_missing_meta_flag_is_violation():
    # honest_empty absent entirely (not just False) — still the masquerade.
    body = _envelope([], {})
    cls, reason = canary._classify_project_content(body)
    assert cls == "violation"
    assert reason == "empty_frame_without_honest_empty"


# --- Attested empty is a VALID result, not a violation ------------------------


def test_attested_honest_empty_is_valid():
    body = _envelope([], {"honest_empty": True})
    cls, reason = canary._classify_project_content(body)
    assert cls == "honest_empty"
    assert reason == ""


# --- Wrong frame: a 2xx whose rows miss a contract column = violation ----------


@pytest.mark.parametrize(
    ("missing_col", "row"),
    [
        ("office_phone", {"gid": "1", "vertical": "dental"}),
        ("vertical", {"gid": "1", "office_phone": "555-0100"}),
        ("gid", {"office_phone": "555-0100", "vertical": "dental"}),
    ],
)
def test_missing_contract_column_is_violation(missing_col: str, row: dict[str, Any]):
    body = _envelope([row], {"honest_empty": False})
    cls, reason = canary._classify_project_content(body)
    assert cls == "violation"
    assert missing_col in reason
    assert reason.startswith("missing_columns[")


def test_one_bad_row_among_good_rows_is_violation():
    # A single row missing the contract breaks the downstream join.
    body = _envelope([_full_row(), {"gid": "2", "vertical": "dental"}], {"honest_empty": False})
    cls, reason = canary._classify_project_content(body)
    assert cls == "violation"
    assert "office_phone" in reason


# --- Malformed envelopes are violations, never silently OK ---------------------


@pytest.mark.parametrize(
    "body",
    [
        None,
        {},
        {"data": "not-a-dict"},
        {"data": {"data": "not-a-list", "meta": {}}},
        {"data": {"data": [], "meta": "not-a-dict"}},
        {"data": {"data": ["not-an-object"], "meta": {"honest_empty": False}}},
    ],
)
def test_malformed_bodies_are_violations(body: Any):
    cls, _reason = canary._classify_project_content(body)
    assert cls == "violation"


# --- Gate integration: a Project content violation FAILS the gate --------------


def _arm(name: str, **kw: Any) -> Any:
    return canary.ArmResults(arm=name, **kw)


def test_gate_fails_on_project_content_violation_even_when_status_green():
    # Both arms 100% HTTP success and zero 429 — but the Project arm carried a
    # content violation. The gate MUST still FAIL (defeat the masquerade).
    project = _arm(
        "project",
        total_calls=100,
        successes=100,
        content_ok=99,
        content_violations=1,
        content_violation_reasons=canary.Counter({"empty_frame_without_honest_empty": 1}),
    )
    section = _arm("section", total_calls=100, successes=100)
    passed, failures = canary._evaluate_gate(project, section, 0.99)
    assert passed is False
    assert any("content_violations" in f for f in failures)


def test_gate_passes_with_clean_content_and_status():
    project = _arm(
        "project",
        total_calls=100,
        successes=100,
        content_ok=100,
    )
    section = _arm("section", total_calls=100, successes=100)
    passed, failures = canary._evaluate_gate(project, section, 0.99)
    assert passed is True
    assert failures == []


def test_gate_passes_with_attested_honest_empty_project_content():
    # An all-honest-empty Project window is content-clean (zero violations).
    project = _arm(
        "project",
        total_calls=50,
        successes=50,
        content_honest_empty=50,
    )
    section = _arm("section", total_calls=50, successes=50)
    passed, failures = canary._evaluate_gate(project, section, 0.99)
    assert passed is True
    assert failures == []


# --- Token provider: self-refresh defense (the 2026-06-08 stale-token fix) -----
#
# The probe runs longer than the SA JWT TTL (~4-5 min observed vs the 10-min
# default window). The original code minted ONE token and reused it; past TTL
# every call 401'd and the 4xx-excluding success_rate masked it as a green gate.
# These tests pin the exp-aware refresh so that regression cannot return silently.


def _fake_jwt(exp: float | None) -> str:
    """A syntactically-valid JWT (header.payload.sig) carrying an optional exp.

    Signature is a placeholder — _jwt_exp READS the claim, it does not verify.
    """
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none"}).encode()).rstrip(b"=").decode()
    payload_obj: dict[str, Any] = {} if exp is None else {"exp": exp}
    payload = base64.urlsafe_b64encode(json.dumps(payload_obj).encode()).rstrip(b"=").decode()
    return f"{header}.{payload}.sig"


def test_jwt_exp_decodes_exp():
    assert canary._jwt_exp(_fake_jwt(1_900_000_000)) == 1_900_000_000.0


def test_jwt_exp_opaque_or_no_exp_returns_none():
    assert canary._jwt_exp("not-a-jwt") is None
    assert canary._jwt_exp(_fake_jwt(None)) is None


def test_token_provider_static_never_remints():
    calls = {"n": 0}

    def mint() -> str:
        calls["n"] += 1
        return "operator-supplied-token"

    p = canary._TokenProvider(mint, static=True)
    assert p.get() == "operator-supplied-token"
    assert p.get() == "operator-supplied-token"
    assert calls["n"] == 1  # minted once; a static (env) token is never refreshed


def test_token_provider_caches_until_near_expiry():
    calls = {"n": 0}

    def mint() -> str:
        calls["n"] += 1
        return _fake_jwt(time.time() + 3600)  # 1h out — far beyond the skew

    p = canary._TokenProvider(mint)
    p.get()
    p.get()
    p.get()
    assert calls["n"] == 1  # valid token is reused, not re-minted every call


def test_token_provider_refreshes_before_expiry():
    calls = {"n": 0}

    def mint() -> str:
        calls["n"] += 1
        # exp sits INSIDE the refresh-skew window, so every get() must re-mint.
        return _fake_jwt(time.time() + canary._TOKEN_REFRESH_SKEW_S - 1)

    p = canary._TokenProvider(mint)
    p.get()
    p.get()
    assert calls["n"] == 2  # stale-token defense: re-minted before reuse


def test_section_arm_has_no_content_criterion():
    # The Section arm is column-contract-EXEMPT: even with content_violations set
    # (which the Section arm never populates in practice), the gate does NOT read
    # the section's content counters. Proven by a Section arm that is HTTP-green
    # and a Project arm that is content-clean: gate passes regardless of any
    # section content fields.
    project = _arm("project", total_calls=10, successes=10, content_ok=10)
    section = _arm(
        "section",
        total_calls=10,
        successes=10,
        # Deliberately set — must be IGNORED by the gate for the section arm.
        content_violations=5,
        content_violation_reasons=canary.Counter({"missing_columns[office_phone]": 5}),
    )
    passed, failures = canary._evaluate_gate(project, section, 0.99)
    assert passed is True
    assert failures == []
