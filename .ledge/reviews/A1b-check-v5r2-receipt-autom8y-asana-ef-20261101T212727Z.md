---
type: review
status: closed
kit: 3ab0393191b9
profile: a8867c41c39b
card: 1390e7e851f1
clerk_start_row: 19766
---

# A1b-check v5r2 receipt: two card-63 terms not met (format, pytest)

- Stamped 2026-11-01T21:27:27Z (date -u). Run 21:26:39Z to 21:27:02Z, once, on the clerk heavy START row 19766. Kit byte-equal to the sealed copy. Exit 0 (the kit gates passed; the results below fail two pass terms). No network, no commit.
- Venue: fresh sparse job-tmp clone, detached at 0e6775f058fe. Census SET; direnv hook defined, not wired. The tree prefix 082efb1721ef is not all digits, so it is not split.

## Every printed line

```
head=0e6775f058fe
tree_W=082efb1721ef tree_src=082efb1721ef
env_census=0
ruff_check rc=0 errors=0
ruff_format rc=1 would_reformat=1
ruff_script(excluded-by-config, forced) rc=1 errors=49 base=49
mypy rc=0 errors=0
under_W=yes marker_lines=1
pytest rc=1 summary=ModuleNotFoundError No module named autom8y_calendly
guard_full rc=0 asana_violations=0
guard_strict rc=0 lenient_advisories=0
ids_bare12=0 ids_outside_hex=0 files=8
env_census_after=0
```

## Against the card-63 pass rule

| Term | Result |
|---|---|
| census 0 before and after; tree assert | **met** (0, 0; trees equal) |
| under_W=yes, marker_lines=1 | **met** |
| ruff_check 0 | **met** |
| ruff_format 0 | **NOT met**: 1 file would be reformatted |
| mypy 0 | **met** (the src files and the new test are clean) |
| pytest rc 0 | **NOT met**: rc 1, collection fails on `ModuleNotFoundError: autom8y_calendly` (the broken local venv already carded; not the code) |
| guard full / strict | **met** (0 asana violations, rc 0; strict rc 0, 0 advisories) |
| forced scripts/ ruff vs base 49 | **met** (49 = base) |
| digit scan 0 outside hex | **met** (bare12 0, outside_hex 0, 8 files) |

## The format finding (one read after the run, disclosed)

After the kit ended, the seat ran one `ruff format --diff` (no write, cache outside W, no network; outside the sandbox) on the three files to name the hunk. The only change ruff wants is in the new test file: the `test_newtype_wrap_is_identity_at_runtime` signature that edit-2 wrapped onto three lines fits on one line (under the repo limit), so ruff joins it. Cure: an edit-3 that joins that one signature, nothing else.

## The pytest finding

The local venv's editable `.pth` points at a removed worktree, so `autom8y_calendly` cannot import and collection fails before any test runs. Rebuilding the venv needs the CodeArtifact token (Tom's credential floor, carded). The bench's A1 PR condition allows pytest RUN in CI when the local venv stays broken.

## edit-2 patch

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
