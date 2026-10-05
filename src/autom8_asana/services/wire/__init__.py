"""Wire (HTTP request/response) models shared by ``services/`` and ``api/routes/``.

Moved below the API layer so services can build and return them without a
services-to-api layer inversion (rule autom8y.asana-no-lower-imports-api).
Pure leaves: pydantic + autom8y_api_schemas only; must never depend on the
api package.
"""
