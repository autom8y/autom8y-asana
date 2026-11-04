# A1 record: R-03 phone-field annotations (autom8y-asana)

- Stamp (UTC): 20261101T130328Z
- Base: d912fa0d3e59
- Branch: fix/r03-phone-field-annotations (job-tmp clone, local only; not pushed)
- Commit: 60383a040fce

## Diff stat

```
 scripts/certification/landing_receipt.py                | 4 +++-
 src/autom8_asana/automation/workflows/leads_consumer.py | 4 +++-
 src/autom8_asana/enrollment/intent_projection.py        | 3 ++-
 3 files changed, 8 insertions(+), 3 deletions(-)
```

## Full diff

```diff
(one unchanged context line below had a home path; redacted as <home>)
diff --git a/scripts/certification/landing_receipt.py b/scripts/certification/landing_receipt.py
index 2774d03b..c397587c 100644
--- a/scripts/certification/landing_receipt.py
+++ b/scripts/certification/landing_receipt.py
@@ -44,6 +44,8 @@ from datetime import UTC, datetime, timedelta
 from pathlib import Path
 from typing import Any, Iterable, Sequence
 
+from autom8y_api_schemas import E164PhoneField
+
 HERE = Path(__file__).resolve().parent
 DEFAULT_PREDICATE = HERE / "predicate.toml"
 DEFAULT_ENV = Path("<home>/Code/a8/autom8/.env")
@@ -340,7 +342,7 @@ class Booking:
     appt_id: int
     created: datetime
     appt_office_phone: str | None
-    contact_phone: str | None
+    contact_phone: E164PhoneField | None
     start_raw: str | None
     start_dt: datetime | None
     start_dialect: str
diff --git a/src/autom8_asana/automation/workflows/leads_consumer.py b/src/autom8_asana/automation/workflows/leads_consumer.py
index 7bb8983b..3695c50d 100644
--- a/src/autom8_asana/automation/workflows/leads_consumer.py
+++ b/src/autom8_asana/automation/workflows/leads_consumer.py
@@ -54,6 +54,8 @@ from autom8_asana.errors import (
 from autom8_asana.resolution.context import ResolutionContext
 
 if TYPE_CHECKING:
+    from autom8y_api_schemas import OfficePhoneField
+
     from autom8_asana.clients.data.client import DataServiceClient
     from autom8_asana.core.scope import EntityScope
     from autom8_asana.protocols.auth import AuthProvider
@@ -73,7 +75,7 @@ class _ResolvedBusiness:
     """Resolved Business fields needed for the per-business leads read."""
 
     gid: str
-    office_phone: str | None
+    office_phone: OfficePhoneField | None
     vertical: str | None
     company_id: str | None
     name: str | None
diff --git a/src/autom8_asana/enrollment/intent_projection.py b/src/autom8_asana/enrollment/intent_projection.py
index 800d195b..a00b5bee 100644
--- a/src/autom8_asana/enrollment/intent_projection.py
+++ b/src/autom8_asana/enrollment/intent_projection.py
@@ -159,6 +159,7 @@ if TYPE_CHECKING:
     from collections.abc import Iterable, Sequence
 
     import polars as pl
+    from autom8y_api_schemas import OfficePhoneField
 
 # ==============================================================================
 # Frame identity (project gids + S3 key layout)
@@ -449,7 +450,7 @@ class EnrollmentIntent(NamedTuple):
     (R-12).
     """
 
-    office_phone: str
+    office_phone: OfficePhoneField
     intent_enabled: bool
     intent_raw: str | None
     intent_source: str
```

## Checks (counts only; loopback-only sandbox; existing virtualenv)

- a) ruff check, 2 src files: 0 errors. ruff format --check, 3 files: 2 already formatted, 1 would reformat (scripts/certification/landing_receipt.py, already unformatted at base).
  - scripts/ is in the repo's ruff extend-exclude. Run on the explicit path (bypassing the exclude): 50 errors vs 49 at base; the +1 is TC002 on the new E164PhoneField import. Not fixed (no TYPE_CHECKING block in the script; out of annotation-only scope).
  - In the two src files the new import sits inside the existing TYPE_CHECKING block, which is where ruff TC002 requires it (valid because of `from __future__ import annotations`).
- b) mypy (module form, 2 src files, repo config; the venv mypy launcher has a stale interpreter path): 2 errors, FAIL. Base: 0 errors on the same 2 files.
  - leads_consumer.py:295 arg-type: passes str | None where OfficePhone | None is expected.
  - intent_projection.py:728 arg-type: passes str where OfficePhone is expected.
  - Cure needs a construction-site change (wrapping or cast), which is beyond annotation-only; escalated, not fixed forward.
- c) pytest: NOT RUN. Startup fails with ModuleNotFoundError: autom8y_calendly (the venv .pth points at a worktree path that no longer exists). Not worked around. Target test files identified: 4 (tests/unit/enrollment/test_intent_projection.py, tests/unit/automation/workflows/test_leads_consumer.py, tests/unit/canary/test_grain_bridge_canary.py, tests/unit/lambda_handlers/test_enrollment_intent_bridge.py). No test covers landing_receipt.
- d) R-03 guard (api-schemas 6c6078bfcd11 copy): default mode 0 violations, rc 0; --strict-only 0 violations, rc 0.
