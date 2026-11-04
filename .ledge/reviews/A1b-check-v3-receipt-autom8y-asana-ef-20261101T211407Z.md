---
type: review
status: closed
kit: 2c2ece147078
profile: a8867c41c39b
clerk_start_row: 19735
---

# A1b-check v3 receipt: STOPPED at the env census (tool-cache artifact)

- Stamped 2026-11-01T21:14:07Z (date -u). Run at 21:13:34Z, once, on the clerk heavy START row 19735. Kit byte-equal to the sealed copy before the run. Exit 3 (STOP). No network, no commit.
- Venue: sparse job-tmp clone at 0e6775f058fe. Census SET; direnv hook defined, not wired.

## Every printed line

```
head=0e6775f058fe
env_census=2
STOP env_census_nonzero
```

## Locating the two hits (count-only, no name printed, no file opened)

```
all=2
excluding .mypy_cache=0
excluding .mypy_cache, .ruff_cache, .pytest_cache=0
.mypy_cache: present
```

Both hits are inside `.mypy_cache`, which the v2 run's mypy step wrote at 21:06Z. The census read 0 on the fresh sparse clone before v2 ran. mypy names its cache files after modules (`<module>.meta.json`, `<module>.data.json`), so a module named `env` yields two files matching `env.*`. They are tool artifacts, not env files, and no tool opened them. The gate is right to stop: the kit cannot tell the two apart by name.

**Proposed cure (v4):** remove `.mypy_cache`, `.ruff_cache` and `.pytest_cache` from the clone before the census, and point every tool cache outside it (`MYPY_CACHE_DIR`, `ruff --cache-dir` and the existing `-p no:cacheprovider`), so the census reads only the source tree.

## edit-2 patch (for the bench to read beside this receipt)

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
