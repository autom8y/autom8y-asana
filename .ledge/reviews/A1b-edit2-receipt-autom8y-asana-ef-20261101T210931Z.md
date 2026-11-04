---
type: review
status: closed
clerk_start_row: 19718
---

# A1b-edit-2 receipt: test-signature annotations committed

- Stamped 2026-11-01T21:09:31Z (date -u). Committed 21:09:16Z on the clerk START row 19718.
- Venue: sparse job-tmp clone, branch fix/r03-phone-field-annotations, base 3b17c1989e04. New commit **0e6775f058fe**. Not pushed. No attribution.
- Hooks check: `core.hooksPath` is unset and the clone has no non-sample hooks in .git/hooks (a fresh `git clone` does not copy hooks), so no hook ran. Disclosed: "hooks on" held as "nothing disabled", but no hook was present to run.
- Census SET; hook (direnv) defined, not wired.

## diff --stat

```
 tests/unit/enrollment/test_r03_phone_field_contract.py | 13 ++++++++++---
 1 file changed, 10 insertions(+), 3 deletions(-)
```

## Patch

```diff
diff --git a/tests/unit/enrollment/test_r03_phone_field_contract.py b/tests/unit/enrollment/test_r03_phone_field_contract.py
index e41f7332..009d0709 100644
--- a/tests/unit/enrollment/test_r03_phone_field_contract.py
+++ b/tests/unit/enrollment/test_r03_phone_field_contract.py
@@ -8,6 +8,8 @@ is identity at runtime.
 
 from __future__ import annotations
 
+from typing import TYPE_CHECKING, Any
+
 import pytest
 from autom8y_api_schemas import (
     LeadPhone,
@@ -17,22 +19,27 @@ from autom8y_api_schemas import (
 )
 from pydantic import TypeAdapter, ValidationError
 
+if TYPE_CHECKING:
+    from collections.abc import Callable
+
 VALID = "+15555550100"  # obviously fake E.164
 
 
 class TestPhoneFieldContract:
     @pytest.mark.parametrize("field", [OfficePhoneField, LeadPhoneField])
-    def test_valid_e164_passes(self, field) -> None:
+    def test_valid_e164_passes(self, field: Any) -> None:
         assert TypeAdapter(field).validate_python(VALID) == VALID
 
     @pytest.mark.parametrize("field", [OfficePhoneField, LeadPhoneField])
     @pytest.mark.parametrize("bad", ["555-0100", "not-a-phone"])
-    def test_malformed_refused(self, field, bad: str) -> None:
+    def test_malformed_refused(self, field: Any, bad: str) -> None:
         with pytest.raises(ValidationError):
             TypeAdapter(field).validate_python(bad)
 
     @pytest.mark.parametrize("wrap", [OfficePhone, LeadPhone])
-    def test_newtype_wrap_is_identity_at_runtime(self, wrap) -> None:
+    def test_newtype_wrap_is_identity_at_runtime(
+        self, wrap: Callable[[str], str]
+    ) -> None:
         wrapped = wrap(VALID)
         assert wrapped == VALID
         assert isinstance(wrapped, str)
```
