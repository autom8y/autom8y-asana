"""DD-5: instrument_app() wiring proof for the asana satellite.

Sprint-A0 hop-1 wires ``instrument_app(app, InstrumentationConfig(
service_name="asana"))`` into ``create_app()`` (api/main.py) so the satellite
emits the fleet-standard ``autom8y_http_*`` metrics under the EXPLICIT
``service="asana"`` label. Without the explicit service_name the label would
default to the implicit ``autom8y-service`` and the per-service SLI would be
unselectable; without the call the metric would never emit at all.

This test proves the wire ACTUALLY emits (not merely that the call exists):

1. Build a real app via ``create_app()`` (proves the ``[fastapi]`` extra of
   autom8y-telemetry resolves -- a missing extra surfaces as
   ``ModuleNotFoundError`` at import/instrument time).
2. Drive a real, non-excluded route through an in-process ``TestClient``
   (``/openapi.json`` -- a dependency-free 200 route that the MetricsMiddleware
   records; ``/health`` and ``/metrics`` are the only paths the middleware
   skips).
3. Scrape ``GET /metrics`` (the endpoint instrument_app mounts) and parse the
   Prometheus text exposition, asserting:
   * ``autom8y_http_request_duration_seconds_count{service="asana"} > 0`` -- the
     metric emitted under the load-bearing explicit service label.
   * a ``route_class`` label is present on the emitted series -- proves the
     autom8y-telemetry>=0.8.0 route-class label is wired (denominator-scoped
     SLI selection).

The metric registry is process-global (prometheus default REGISTRY), so the
count assertion uses ``> 0`` rather than an exact value: other tests in the
same worker may also have driven requests. The route-class label presence is
asserted structurally on the asana-service series.
"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from collections.abc import Iterator

from autom8_asana.api.main import create_app
from autom8_asana.services.resolver import EntityProjectRegistry

# The fleet-standard duration histogram exposes its observation count as
# ``<name>_count`` in the Prometheus text exposition.
_COUNT_METRIC = "autom8y_http_request_duration_seconds_count"

# A non-excluded, dependency-free route. The MetricsMiddleware records every
# path except the always-excluded {/health, /metrics}; /openapi.json is mounted
# by FastAPI and returns 200 without any auth or business-layer dependency.
_NON_EXCLUDED_ROUTE = "/openapi.json"


@pytest.fixture
def instrumented_app() -> Iterator[FastAPI]:
    """Build a real create_app() instance with entity discovery mocked.

    Mirrors tests/unit/api/conftest.py: enable the auth dev-mode bypass and
    short-circuit the network-bound entity discovery so the app boots in a
    hermetic unit-test context. The act of calling create_app() exercises the
    instrument_app() wire (and the autom8y-telemetry[fastapi] import) -- a
    missing extra would raise ModuleNotFoundError here.
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

        # No ModuleNotFoundError here proves autom8y-telemetry[fastapi] resolved.
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


def _parse_count_samples(metrics_text: str) -> list[tuple[dict[str, str], float]]:
    """Parse ``autom8y_http_request_duration_seconds_count`` samples.

    Returns a list of (labels-dict, value) tuples for every count series in the
    Prometheus text exposition. Comment (# HELP/# TYPE) lines are ignored.
    """
    samples: list[tuple[dict[str, str], float]] = []
    line_re = re.compile(rf"^{re.escape(_COUNT_METRIC)}\{{(?P<labels>[^}}]*)\}}\s+(?P<value>\S+)$")
    label_re = re.compile(r'(\w+)="((?:[^"\\]|\\.)*)"')
    for line in metrics_text.splitlines():
        if line.startswith("#") or not line.startswith(_COUNT_METRIC):
            continue
        match = line_re.match(line)
        if match is None:
            continue
        labels = {k: v for k, v in label_re.findall(match.group("labels"))}
        samples.append((labels, float(match.group("value"))))
    return samples


def test_create_app_boots_without_module_not_found(instrumented_app: FastAPI) -> None:
    """create_app() boots cleanly -- autom8y-telemetry[fastapi] is present.

    A missing [fastapi] extra would surface as ModuleNotFoundError when
    instrument_app imports the FastAPI instrumentation; reaching this assertion
    proves the extra resolved.
    """
    assert isinstance(instrumented_app, FastAPI)
    # instrument_app mounts the /metrics route; its presence is a structural
    # proof the wire ran during create_app().
    mounted_paths = {route.path for route in instrumented_app.routes}  # type: ignore[attr-defined]
    assert "/metrics" in mounted_paths


def test_metrics_emit_under_asana_service_label(instrumented_app: FastAPI) -> None:
    """A real request emits the duration count under service="asana" + route_class.

    DD-5: drive a non-excluded route, scrape /metrics, and assert the
    fleet-standard duration metric emitted under the EXPLICIT asana service
    label with a route_class label present.
    """
    with TestClient(instrumented_app) as client:
        # (a) Hit a real, non-excluded route so the MetricsMiddleware records.
        driven = client.get(_NON_EXCLUDED_ROUTE)
        assert driven.status_code == 200, (
            f"{_NON_EXCLUDED_ROUTE} should return 200 so the metric records a "
            f"clean signal; got {driven.status_code}"
        )

        # (b) Scrape the /metrics endpoint instrument_app mounted.
        scrape = client.get("/metrics")
        assert scrape.status_code == 200, "instrument_app must mount a 200 /metrics endpoint"

    samples = _parse_count_samples(scrape.text)
    asana_samples = [
        (labels, value) for labels, value in samples if labels.get("service") == "asana"
    ]

    # The metric emitted under the load-bearing explicit service="asana" label.
    assert asana_samples, (
        "Expected at least one "
        f'{_COUNT_METRIC}{{service="asana"}} series after driving '
        f"{_NON_EXCLUDED_ROUTE}; got services="
        f"{sorted({labels.get('service') for labels, _ in samples})}"
    )

    # The count is strictly positive -- the wire ACTUALLY emitted, it did not
    # merely register a zero-valued series.
    total_asana_count = sum(value for _, value in asana_samples)
    assert total_asana_count > 0, (
        f"{_COUNT_METRIC}{{service=asana}} must be > 0 after a real request; "
        f"observed {total_asana_count}"
    )

    # The route_class label (autom8y-telemetry>=0.8.0) is present on the emitted
    # asana series -- proves denominator-scoped SLI selection is wired.
    assert any("route_class" in labels for labels, _ in asana_samples), (
        "Expected a route_class label on the asana duration-count series "
        "(autom8y-telemetry>=0.8.0 route_class wiring); labels seen: "
        f"{[sorted(labels) for labels, _ in asana_samples]}"
    )
