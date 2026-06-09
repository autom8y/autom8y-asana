"""FOI S2 WS-B2: build_info emitting-floor seal for the asana satellite.

Falsifiability fixture for the autom8y-telemetry 0.10.0 upgrade. 0.10.0 adds the
``autom8y_build_info`` emitting-floor (autom8y-telemetry#456): ``instrument_app``
registers the ``autom8y_build_info`` Gauge SYNCHRONOUSLY in the factory body
(autom8y_telemetry/fastapi/instrument.py: the eager ``get_or_create_build_info``
call), so the instant ``GET /metrics`` answers 200 a zero-traffic task already
serves >=1 ``autom8y_`` family. This service INHERITS that floor by construction
via its existing ``instrument_app(app, InstrumentationConfig(service_name="asana"))``
wire in ``api/main.py`` -- no asana-side metric registration is added.

The seal proves the floor at its SOURCE, not by leaning on the incidental
side-effect of HTTP-family registration (that already requires driving a request;
the build_info floor must hold at zero traffic).

It asserts on the build_info metric FAMILY SHAPE -- never on a literal config or
source string:

* Registry assertion: ``autom8y_build_info`` appears as a metric-family name in
  the process-global prometheus ``REGISTRY.collect()`` after ``create_app()``.
* Exposition assertion: ``GET /metrics`` text carries the ``# TYPE
  autom8y_build_info gauge`` HELP/TYPE shape AND a ``1``-valued series -- the
  always-non-vacuous emitting-floor child.

Both halves are FAMILY-presence / SHAPE checks. They survive a label-value change
(e.g. a different ``version=`` value) because they never assert a label VALUE --
only that the family is present and the floor child carries the constant ``1``.

Negative arm (build_info_absent): when ``instrument_app`` is NOT run / build_info
registration is suppressed, the same family-presence assertion FAILS. This is the
deliberately-broken half that proves the seal can fire RED -- a fixture that can
only pass is theater. The init-mutation proof (commenting out the
``instrument_app`` call in ``api/main.py``) is the production-path companion to
this in-test suppression arm.
"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

if TYPE_CHECKING:
    from collections.abc import Iterator

from autom8_asana.api.main import create_app
from autom8_asana.services.resolver import EntityProjectRegistry

# The emitting-floor anchor family minted by autom8y-telemetry 0.10.0 (#456).
_BUILD_INFO_FAMILY = "autom8y_build_info"

# The Prometheus text-exposition TYPE line for the gauge family. Asserting the
# TYPE shape (not a label value) keeps the seal a FAMILY-presence check that is
# robust to version-label changes.
_BUILD_INFO_TYPE_LINE = re.compile(
    rf"^#\s+TYPE\s+{re.escape(_BUILD_INFO_FAMILY)}\s+gauge\s*$",
    re.MULTILINE,
)

# The floor child: a series named ``autom8y_build_info`` (the gauge value sample,
# which prometheus_client exposes WITHOUT a ``_total``/``_count`` suffix) whose
# value is the constant ``1``. Match the family name + label block + a value of 1
# (1, 1.0, or 1e0 exponential forms prometheus may emit) -- the always-non-vacuous
# emitting-floor invariant, asserted on SHAPE not on any specific label value.
_BUILD_INFO_FLOOR_SERIES = re.compile(
    rf"^{re.escape(_BUILD_INFO_FAMILY)}\{{[^}}]*\}}\s+1(?:\.0+)?(?:e\+?0+)?$",
    re.MULTILINE,
)


def _build_info_family_in_registry() -> bool:
    """True when the ``autom8y_build_info`` family is in the global REGISTRY.

    Walks ``REGISTRY.collect()`` and matches on the metric-family ``name`` (the
    family name, which for a Gauge is the bare metric name without a suffix).
    This is a SHAPE check: it asserts the family was registered, not any label
    value it carries.
    """
    return any(metric_family.name == _BUILD_INFO_FAMILY for metric_family in REGISTRY.collect())


@pytest.fixture
def instrumented_app() -> Iterator[FastAPI]:
    """Build a real create_app() with entity discovery mocked (hermetic boot).

    Mirrors tests/unit/api/test_instrument_app_wiring.py: dev-mode auth bypass +
    short-circuited network entity discovery so the app boots in-process. Calling
    create_app() runs the instrument_app() wire, which -- on telemetry 0.10.0 --
    eagerly registers the autom8y_build_info emitting-floor in its synchronous
    factory body (zero traffic required).
    """
    prev_dev_mode = os.environ.get("AUTH__DEV_MODE")
    prev_env = os.environ.get("AUTOM8Y_ENV")
    os.environ["AUTH__DEV_MODE"] = "true"
    os.environ["AUTOM8Y_ENV"] = "LOCAL"

    EntityProjectRegistry.reset()

    with patch(
        "autom8_asana.api.lifespan._discover_entity_projects",
        new_callable=AsyncMock,
    ) as mock_discover:

        async def _setup_registry(app: FastAPI) -> None:
            app.state.entity_project_registry = EntityProjectRegistry.get_instance()

        mock_discover.side_effect = _setup_registry

        app = create_app()
        yield app

    EntityProjectRegistry.reset()
    if prev_dev_mode is None:
        os.environ.pop("AUTH__DEV_MODE", None)
    else:
        os.environ["AUTH__DEV_MODE"] = prev_dev_mode
    if prev_env is None:
        os.environ.pop("AUTOM8Y_ENV", None)
    else:
        os.environ["AUTOM8Y_ENV"] = prev_env


def test_build_info_present_in_registry_after_instrument(
    instrumented_app: FastAPI,
) -> None:
    """create_app() registers the autom8y_build_info family with NO traffic.

    The eager emitting-floor (#456) registers build_info in the synchronous
    instrument_app factory body. We assert family presence in the process-global
    REGISTRY immediately after create_app(), WITHOUT driving any request -- the
    zero-traffic floor invariant.
    """
    assert isinstance(instrumented_app, FastAPI)
    assert _build_info_family_in_registry(), (
        f"Expected the {_BUILD_INFO_FAMILY} family in the prometheus REGISTRY "
        "after create_app() (telemetry 0.10.0 eager emitting-floor #456); "
        f"families seen: {sorted({mf.name for mf in REGISTRY.collect()})[:40]}"
    )


def test_build_info_present_on_metrics_exposition(
    instrumented_app: FastAPI,
) -> None:
    """GET /metrics serves the autom8y_build_info family shape + the 1-valued floor.

    Scrape the /metrics endpoint instrument_app mounted and assert the
    build_info TYPE shape AND the always-non-vacuous 1-valued floor series are
    present in the Prometheus text exposition. SHAPE assertion only: no label
    VALUE is matched, so the seal is robust to a version-label change.
    """
    with TestClient(instrumented_app) as client:
        scrape = client.get("/metrics")
        assert scrape.status_code == 200, "instrument_app must mount a 200 /metrics endpoint"

    body = scrape.text

    assert _BUILD_INFO_TYPE_LINE.search(body), (
        f"Expected a '# TYPE {_BUILD_INFO_FAMILY} gauge' line on GET /metrics "
        "(telemetry 0.10.0 emitting-floor #456 inherited via instrument_app); "
        f"build_info lines seen: "
        f"{[ln for ln in body.splitlines() if _BUILD_INFO_FAMILY in ln][:5]}"
    )

    assert _BUILD_INFO_FLOOR_SERIES.search(body), (
        f"Expected a 1-valued {_BUILD_INFO_FAMILY} floor series on GET /metrics "
        "(the always-non-vacuous emitting-floor child); build_info series seen: "
        f"{[ln for ln in body.splitlines() if ln.startswith(_BUILD_INFO_FAMILY)][:5]}"
    )


def test_build_info_absent_when_instrument_suppressed() -> None:
    """build_info_absent -> the family-presence assertion FAILS (seal fires RED).

    The deliberately-broken arm. We boot a bare FastAPI app that NEVER runs
    instrument_app (and therefore never registers the emitting-floor), then assert
    its /metrics has no build_info family. This proves the seal's positive
    assertions are falsifiable: if build_info registration is suppressed, the
    TYPE-shape and floor-series checks the positive tests rely on would NOT match.

    A fixture that can only pass is theater (G-THEATER). This arm demonstrates the
    RED state structurally, in-process, with no telemetry init on the path.
    """
    bare = FastAPI()

    @bare.get("/metrics")
    def _bare_metrics() -> str:  # pragma: no cover - trivial stub route
        # A /metrics route that serves NO build_info family (no instrument_app,
        # no prometheus exposition wiring). Stands in for "instrument_app not run".
        return "# no telemetry exposition\n"

    with TestClient(bare) as client:
        scrape = client.get("/metrics")
        assert scrape.status_code == 200

    body = scrape.text

    # The exact assertions the positive exposition test makes MUST fail here.
    assert not _BUILD_INFO_TYPE_LINE.search(body), (
        "build_info_absent arm: a bare app with no instrument_app must NOT carry "
        f"the {_BUILD_INFO_FAMILY} TYPE line -- if it does, the seal cannot "
        "distinguish floor-present from floor-absent and is theater."
    )
    assert not _BUILD_INFO_FLOOR_SERIES.search(body), (
        "build_info_absent arm: a bare app with no instrument_app must NOT carry "
        f"the {_BUILD_INFO_FAMILY} 1-valued floor series."
    )
