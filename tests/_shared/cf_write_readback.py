"""Transport-seam harness + READBACK oracle for Asana custom-field writes.

Why this module exists
----------------------
The CLASS-DEFECT-CF-WRITE family (GATE-1 double-nest, DIC/F-1 enum read-shape)
is invisible to HTTP status: Asana answers **200 OK for both the broken and the
correct body** and silently writes nothing on the broken one. An assertion on
the status code -- or on a wholesale-mocked ``tasks.update_async`` -- therefore
proves nothing. Two things are needed and both live here:

1. :func:`real_tasks_client` -- mock ONE LAYER LOWER than the client. The only
   stubbed seam is ``self._http.put``; the REAL ``TasksClient.update_async``
   runs its own ``json={"data": kwargs}`` marshaling, so the captured request
   body is byte-for-byte what Asana would receive.

2. :func:`apply_write_body` + :func:`read_custom_field` -- a READBACK of the
   written field. The captured body is applied to a task-read document and the
   value is read back through the PRODUCTION extractor
   (``intake_resolve_service._extract_custom_field``). The receipt is the value
   that comes back out, never the HTTP status.

Live-readback scope
-------------------
This is the in-harness half of the readback receipt. The live half -- writing to
a real Asana task and re-fetching it -- is NOT runnable from the build seat and
is owed to SUB-3's GATE-2 certification.

Error orientation (LOAD-BEARING, not an implementation note)
------------------------------------------------------------
:func:`apply_write_body` is a STRICT SUBSET of Asana's write semantics, never a
faithful simulator. It recognizes exactly one body shape -- a flat
``{"data": {"custom_fields": {gid: scalar}}}`` envelope against fields already
present on the task -- and treats **every** unrecognized shape as contributing
NO write. Its error direction is therefore monotonically "the field stays
unwritten", which can only ever FAIL the cured arm (loudly) and can never
manufacture a false GREEN for a broken body. A more permissive oracle would
launder the exact defect class this module exists to catch.

The two arms are non-vacuous only as a PAIR: the cured arm proves the oracle
does apply a correct body (it is not a no-op that trivially returns ``None``),
and the broken arm proves a defective body is not applied. Neither alone
discriminates.
"""

from __future__ import annotations

import copy
from typing import Any
from unittest.mock import AsyncMock, MagicMock

__all__ = [
    "apply_write_body",
    "captured_put_body",
    "read_custom_field",
    "real_tasks_client",
]

# A schema-valid Task payload: the real ``update()`` runs
# ``Task.model_validate(result)`` on whatever ``_http.put`` returns.
_PUT_RESPONSE: dict[str, Any] = {"gid": "1217301971794137"}


def real_tasks_client() -> tuple[Any, AsyncMock]:
    """Build a REAL ``TasksClient`` whose ONLY mocked seam is ``self._http.put``.

    ``BaseClient.__init__`` just stores its arguments (no validation), so the
    config/auth collaborators can be bare mocks. Instance attributes shadow the
    ``@async_method`` descriptors, so callers may stub ``tasks.get_async``
    directly while leaving ``update_async`` REAL -- which is the whole point:
    the body-build is production code under test, not a mock's echo.

    Returns:
        ``(tasks_client, mock_http)``. Assert against
        ``mock_http.put.await_args`` for the verbatim outbound body.
    """
    from autom8_asana.clients.tasks import TasksClient

    mock_http = MagicMock()
    mock_http.put = AsyncMock(return_value=dict(_PUT_RESPONSE))
    tasks = TasksClient(http=mock_http, config=MagicMock(), auth_provider=MagicMock())
    return tasks, mock_http


def captured_put_body(mock_http: AsyncMock) -> dict[str, Any]:
    """Return the verbatim JSON body of the single awaited ``_http.put`` call."""
    body = mock_http.put.await_args.kwargs["json"]
    assert isinstance(body, dict), f"expected a JSON object body, got {type(body)!r}"
    return body


def apply_write_body(task: dict[str, Any], body: Any) -> dict[str, Any]:
    """Apply an Asana ``PUT /tasks/{gid}`` request body to a task-read document.

    STRICT SUBSET of Asana's write semantics -- see the module docstring's
    "Error orientation" section, which is the load-bearing property. Anything
    not explicitly recognized below applies NOTHING, so a wrong oracle can only
    under-write.

    Recognized (and ONLY this):
      * a top-level ``{"data": {...}}`` envelope whose payload is the flat task
        field map -- an inner ``data`` key is the double-nest defect and is
        refused outright;
      * a ``custom_fields`` map of ``{field_gid: scalar}`` against fields ALREADY
        present on ``task``;
      * for an enum field, a PLAIN option-gid string that matches one of the
        field's ``enum_options`` -- the nested ``{"gid": opt}`` read shape is a
        non-scalar and applies nothing.

    Args:
        task: A task-read document (``get_async`` shape) with ``custom_fields``.
        body: The captured ``_http.put`` JSON body.

    Returns:
        A deep copy of ``task`` with any recognized writes applied.
    """
    applied: dict[str, Any] = copy.deepcopy(task)

    if not isinstance(body, dict):
        return applied
    envelope = body.get("data")
    if not isinstance(envelope, dict):
        return applied
    if "data" in envelope:
        # Double-nested body: ``{"data": {"data": {...}}}``. Asana answers 200 and
        # ignores the inner envelope entirely. Apply nothing -- deliberately.
        return applied

    fields = envelope.get("custom_fields")
    if not isinstance(fields, dict):
        return applied

    by_gid: dict[str, dict[str, Any]] = {
        cf["gid"]: cf
        for cf in applied.get("custom_fields", [])
        if isinstance(cf, dict) and cf.get("gid")
    }

    for cf_gid, value in fields.items():
        target = by_gid.get(cf_gid)
        if target is None:
            # Unknown field gid: not writable on this task. Apply nothing.
            continue

        options = target.get("enum_options") or []
        if options:
            if not isinstance(value, str):
                # Nested read shape ({"gid": opt}) or any non-scalar. Apply nothing.
                continue
            match = next(
                (o for o in options if isinstance(o, dict) and o.get("gid") == value),
                None,
            )
            if match is None:
                # Not one of this field's options. Apply nothing.
                continue
            target["enum_value"] = {"gid": match.get("gid"), "name": match.get("name")}
            target["display_value"] = match.get("name")
            continue

        if isinstance(value, (dict, list)):
            # Non-scalar into a scalar field. Apply nothing.
            continue
        if value is None:
            target["text_value"] = None
            target["display_value"] = None
            continue
        target["text_value"] = str(value)
        target["display_value"] = str(value)

    return applied


def read_custom_field(task: dict[str, Any], field_name: str) -> str | None:
    """Read a custom field back by NAME through the PRODUCTION extractor.

    Delegates to ``intake_resolve_service._extract_custom_field`` -- the same
    function the resolver uses against live Asana reads. Never re-implement the
    read here: a local re-implementation would only assert that the test agrees
    with itself.

    Args:
        task: A task-read document, typically the output of
            :func:`apply_write_body`.
        field_name: The custom field's display name (case/space insensitive).

    Returns:
        The field's readable value, or ``None`` when it is unwritten.
    """
    # ``intake_resolve_service`` cannot be imported COLD: ``api.routes.__init__``
    # pulls ``intake_create``, which imports ``is_valid_e164`` back out of this
    # very module -> ImportError on a partially-initialized module. Importing the
    # route package FIRST drives the cycle from the side that resolves. Without
    # this the helper is an ORDER-DEPENDENT flake -- green in a full-file run
    # that happened to import the API earlier, red under pytest-split sharding.
    import autom8_asana.api.routes  # noqa: F401  -- circular-import ordering guard
    from autom8_asana.services.intake_resolve_service import _extract_custom_field

    return _extract_custom_field(task.get("custom_fields", []), field_name)
