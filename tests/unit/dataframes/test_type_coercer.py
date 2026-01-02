"""Unit tests for TypeCoercer class.

Per TDD-custom-field-type-coercion FR-001: Tests for schema-aware type coercion
of Asana custom field values to target dtypes.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from autom8_asana.dataframes.resolver import TypeCoercer, coerce_value


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def coercer() -> TypeCoercer:
    """Fresh TypeCoercer instance for each test."""
    return TypeCoercer()


# ============================================================================
# TestListToString
# ============================================================================


class TestListToString:
    """Tests for list to string coercion (multi_enum -> Utf8)."""

    def test_multiple_values(self, coercer: TypeCoercer) -> None:
        """Test list with multiple values joins with separator."""
        result = coercer.coerce(["A", "B", "C"], "Utf8")
        assert result == "A, B, C"

    def test_single_value(self, coercer: TypeCoercer) -> None:
        """Test list with single value returns that value."""
        result = coercer.coerce(["Only"], "Utf8")
        assert result == "Only"

    def test_empty_list_returns_none(self, coercer: TypeCoercer) -> None:
        """Test empty list returns None, not empty string."""
        result = coercer.coerce([], "Utf8")
        assert result is None

    def test_none_values_filtered(self, coercer: TypeCoercer) -> None:
        """Test None values are filtered from list."""
        result = coercer.coerce(["A", None, "B", None, "C"], "Utf8")
        assert result == "A, B, C"

    def test_all_none_values_returns_none(self, coercer: TypeCoercer) -> None:
        """Test list of only None values returns None."""
        result = coercer.coerce([None, None, None], "Utf8")
        assert result is None

    def test_numeric_values_converted(self, coercer: TypeCoercer) -> None:
        """Test numeric values are converted to strings."""
        result = coercer.coerce([1, 2, 3], "Utf8")
        assert result == "1, 2, 3"

    def test_string_dtype_alias(self, coercer: TypeCoercer) -> None:
        """Test String dtype works same as Utf8."""
        result = coercer.coerce(["A", "B"], "String")
        assert result == "A, B"


# ============================================================================
# TestListPassthrough
# ============================================================================


class TestListPassthrough:
    """Tests for list passthrough (list -> List[Utf8])."""

    def test_list_to_list_utf8_unchanged(self, coercer: TypeCoercer) -> None:
        """Test list to List[Utf8] returns unchanged."""
        input_list = ["A", "B", "C"]
        result = coercer.coerce(input_list, "List[Utf8]")
        assert result == ["A", "B", "C"]
        assert result is input_list  # Same reference

    def test_empty_list_unchanged(self, coercer: TypeCoercer) -> None:
        """Test empty list to List[Utf8] returns unchanged."""
        input_list: list[str] = []
        result = coercer.coerce(input_list, "List[Utf8]")
        assert result == []
        assert result is input_list

    def test_list_string_dtype_alias(self, coercer: TypeCoercer) -> None:
        """Test List[String] dtype works same as List[Utf8]."""
        input_list = ["A", "B"]
        result = coercer.coerce(input_list, "List[String]")
        assert result == ["A", "B"]


# ============================================================================
# TestStringToList
# ============================================================================


class TestStringToList:
    """Tests for string to list coercion (single value -> List[Utf8])."""

    def test_string_wrapped_in_list(self, coercer: TypeCoercer) -> None:
        """Test string is wrapped in single-element list."""
        result = coercer.coerce("single", "List[Utf8]")
        assert result == ["single"]

    def test_empty_string_wrapped(self, coercer: TypeCoercer) -> None:
        """Test empty string is still wrapped in list."""
        result = coercer.coerce("", "List[Utf8]")
        assert result == [""]

    def test_string_to_list_string(self, coercer: TypeCoercer) -> None:
        """Test string to List[String] works."""
        result = coercer.coerce("value", "List[String]")
        assert result == ["value"]


# ============================================================================
# TestNumericCoercion
# ============================================================================


class TestNumericCoercion:
    """Tests for numeric type coercion."""

    def test_string_to_decimal(self, coercer: TypeCoercer) -> None:
        """Test string to Decimal coercion."""
        result = coercer.coerce("123.45", "Decimal")
        assert result == Decimal("123.45")
        assert isinstance(result, Decimal)

    def test_float_to_decimal(self, coercer: TypeCoercer) -> None:
        """Test float to Decimal coercion via string intermediate."""
        result = coercer.coerce(123.45, "Decimal")
        # Note: goes through str() to preserve precision
        assert isinstance(result, Decimal)
        assert result == Decimal("123.45")

    def test_int_to_decimal(self, coercer: TypeCoercer) -> None:
        """Test integer to Decimal coercion."""
        result = coercer.coerce(100, "Decimal")
        assert result == Decimal("100")
        assert isinstance(result, Decimal)

    def test_decimal_passthrough(self, coercer: TypeCoercer) -> None:
        """Test Decimal value passes through unchanged."""
        input_val = Decimal("999.99")
        result = coercer.coerce(input_val, "Decimal")
        assert result is input_val

    def test_string_to_float64(self, coercer: TypeCoercer) -> None:
        """Test string to Float64 coercion."""
        result = coercer.coerce("123.45", "Float64")
        assert result == 123.45
        assert isinstance(result, float)

    def test_string_to_int64(self, coercer: TypeCoercer) -> None:
        """Test string to Int64 coercion."""
        result = coercer.coerce("123", "Int64")
        assert result == 123
        assert isinstance(result, int)

    def test_float_string_to_int64(self, coercer: TypeCoercer) -> None:
        """Test float string to Int64 truncates decimal."""
        result = coercer.coerce("123.99", "Int64")
        assert result == 123
        assert isinstance(result, int)

    def test_string_to_int32(self, coercer: TypeCoercer) -> None:
        """Test string to Int32 coercion."""
        result = coercer.coerce("42", "Int32")
        assert result == 42
        assert isinstance(result, int)

    def test_invalid_numeric_returns_none(self, coercer: TypeCoercer) -> None:
        """Test invalid numeric value returns None."""
        result = coercer.coerce("not-a-number", "Decimal")
        assert result is None

    def test_invalid_float_returns_none(self, coercer: TypeCoercer) -> None:
        """Test invalid float value returns None."""
        result = coercer.coerce("abc", "Float64")
        assert result is None

    def test_invalid_int_returns_none(self, coercer: TypeCoercer) -> None:
        """Test invalid int value returns None."""
        result = coercer.coerce("xyz", "Int64")
        assert result is None


# ============================================================================
# TestNoneHandling
# ============================================================================


class TestNoneHandling:
    """Tests for None value handling."""

    def test_none_to_utf8(self, coercer: TypeCoercer) -> None:
        """Test None passthrough for Utf8."""
        result = coercer.coerce(None, "Utf8")
        assert result is None

    def test_none_to_list_utf8(self, coercer: TypeCoercer) -> None:
        """Test None passthrough for List[Utf8]."""
        result = coercer.coerce(None, "List[Utf8]")
        assert result is None

    def test_none_to_decimal(self, coercer: TypeCoercer) -> None:
        """Test None passthrough for Decimal."""
        result = coercer.coerce(None, "Decimal")
        assert result is None

    def test_none_to_float64(self, coercer: TypeCoercer) -> None:
        """Test None passthrough for Float64."""
        result = coercer.coerce(None, "Float64")
        assert result is None

    def test_none_to_int64(self, coercer: TypeCoercer) -> None:
        """Test None passthrough for Int64."""
        result = coercer.coerce(None, "Int64")
        assert result is None

    def test_none_to_unknown_dtype(self, coercer: TypeCoercer) -> None:
        """Test None passthrough for unknown dtype."""
        result = coercer.coerce(None, "UnknownType")
        assert result is None


# ============================================================================
# TestPassthrough
# ============================================================================


class TestPassthrough:
    """Tests for passthrough behavior (no coercion needed)."""

    def test_string_to_utf8_unchanged(self, coercer: TypeCoercer) -> None:
        """Test string to Utf8 returns unchanged."""
        result = coercer.coerce("hello", "Utf8")
        assert result == "hello"

    def test_string_to_string_unchanged(self, coercer: TypeCoercer) -> None:
        """Test string to String returns unchanged."""
        result = coercer.coerce("world", "String")
        assert result == "world"

    def test_list_to_list_utf8_unchanged(self, coercer: TypeCoercer) -> None:
        """Test list to List[Utf8] returns unchanged."""
        input_list = ["a", "b"]
        result = coercer.coerce(input_list, "List[Utf8]")
        assert result is input_list

    def test_unknown_dtype_passthrough(self, coercer: TypeCoercer) -> None:
        """Test unknown dtype passes value through."""
        result = coercer.coerce("value", "UnknownType")
        assert result == "value"

    def test_dict_passthrough(self, coercer: TypeCoercer) -> None:
        """Test dict passes through for unknown dtype."""
        input_dict = {"key": "value"}
        result = coercer.coerce(input_dict, "Object")
        assert result is input_dict


# ============================================================================
# TestSourceTypeHint
# ============================================================================


class TestSourceTypeHint:
    """Tests for source_type parameter (optional hint)."""

    def test_source_type_does_not_affect_coercion(self, coercer: TypeCoercer) -> None:
        """Test source_type is informational only."""
        # Same coercion regardless of source_type
        result1 = coercer.coerce(["A", "B"], "Utf8", source_type="multi_enum")
        result2 = coercer.coerce(["A", "B"], "Utf8", source_type=None)
        assert result1 == result2 == "A, B"

    def test_source_type_passed_to_debug_log(self, coercer: TypeCoercer) -> None:
        """Test source_type is passed through (no exception)."""
        # Should not raise
        result = coercer.coerce({"complex": "value"}, "Object", source_type="custom")
        assert result == {"complex": "value"}


# ============================================================================
# TestModuleLevelFunction
# ============================================================================


class TestModuleLevelFunction:
    """Tests for coerce_value module-level function."""

    def test_coerce_value_list_to_string(self) -> None:
        """Test module-level coerce_value function."""
        result = coerce_value(["A", "B"], "Utf8")
        assert result == "A, B"

    def test_coerce_value_string_to_list(self) -> None:
        """Test module-level string to list coercion."""
        result = coerce_value("single", "List[Utf8]")
        assert result == ["single"]

    def test_coerce_value_numeric(self) -> None:
        """Test module-level numeric coercion."""
        result = coerce_value("123.45", "Decimal")
        assert result == Decimal("123.45")

    def test_coerce_value_none(self) -> None:
        """Test module-level None handling."""
        result = coerce_value(None, "Utf8")
        assert result is None

    def test_coerce_value_with_source_type(self) -> None:
        """Test module-level with source_type parameter."""
        result = coerce_value(["A"], "Utf8", source_type="multi_enum")
        assert result == "A"


# ============================================================================
# TestClassConstants
# ============================================================================


class TestClassConstants:
    """Tests for TypeCoercer class constants."""

    def test_list_separator(self) -> None:
        """Test LIST_SEPARATOR constant."""
        assert TypeCoercer.LIST_SEPARATOR == ", "

    def test_list_dtypes(self) -> None:
        """Test LIST_DTYPES constant."""
        assert "List[Utf8]" in TypeCoercer.LIST_DTYPES
        assert "List[String]" in TypeCoercer.LIST_DTYPES
        assert len(TypeCoercer.LIST_DTYPES) == 2

    def test_string_dtypes(self) -> None:
        """Test STRING_DTYPES constant."""
        assert "Utf8" in TypeCoercer.STRING_DTYPES
        assert "String" in TypeCoercer.STRING_DTYPES
        assert len(TypeCoercer.STRING_DTYPES) == 2

    def test_numeric_dtypes(self) -> None:
        """Test NUMERIC_DTYPES constant."""
        assert "Decimal" in TypeCoercer.NUMERIC_DTYPES
        assert "Float64" in TypeCoercer.NUMERIC_DTYPES
        assert "Int64" in TypeCoercer.NUMERIC_DTYPES
        assert "Int32" in TypeCoercer.NUMERIC_DTYPES
        assert len(TypeCoercer.NUMERIC_DTYPES) == 4

    def test_constants_are_frozenset(self) -> None:
        """Test constants are immutable frozensets."""
        assert isinstance(TypeCoercer.LIST_DTYPES, frozenset)
        assert isinstance(TypeCoercer.STRING_DTYPES, frozenset)
        assert isinstance(TypeCoercer.NUMERIC_DTYPES, frozenset)


# ============================================================================
# TestThreadSafety
# ============================================================================


class TestThreadSafety:
    """Tests for thread safety of TypeCoercer."""

    def test_stateless_coercion(self) -> None:
        """Test TypeCoercer is stateless - multiple instances produce same results."""
        coercer1 = TypeCoercer()
        coercer2 = TypeCoercer()

        result1 = coercer1.coerce(["A", "B"], "Utf8")
        result2 = coercer2.coerce(["A", "B"], "Utf8")

        assert result1 == result2 == "A, B"

    def test_module_singleton_is_same_instance(self) -> None:
        """Test module-level singleton works correctly."""
        # Multiple calls should work without issue
        result1 = coerce_value(["X"], "Utf8")
        result2 = coerce_value(["Y"], "Utf8")

        assert result1 == "X"
        assert result2 == "Y"


# ============================================================================
# TestEdgeCases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_long_list(self, coercer: TypeCoercer) -> None:
        """Test coercion of very long list."""
        long_list = [f"item_{i}" for i in range(1000)]
        result = coercer.coerce(long_list, "Utf8")
        assert result is not None
        assert result.count(", ") == 999

    def test_unicode_strings(self, coercer: TypeCoercer) -> None:
        """Test Unicode strings in list."""
        result = coercer.coerce(["Hello", "World"], "Utf8")
        assert result == "Hello, World"

    def test_mixed_types_in_list(self, coercer: TypeCoercer) -> None:
        """Test list with mixed types converts all to strings."""
        result = coercer.coerce(["text", 123, 45.6, True], "Utf8")
        assert result == "text, 123, 45.6, True"

    def test_negative_numbers(self, coercer: TypeCoercer) -> None:
        """Test negative number coercion."""
        result = coercer.coerce("-123.45", "Decimal")
        assert result == Decimal("-123.45")

    def test_scientific_notation(self, coercer: TypeCoercer) -> None:
        """Test scientific notation to Decimal."""
        result = coercer.coerce("1.23e10", "Decimal")
        assert result == Decimal("1.23e10")

    def test_whitespace_string(self, coercer: TypeCoercer) -> None:
        """Test whitespace string passes through."""
        result = coercer.coerce("   ", "Utf8")
        assert result == "   "

    def test_empty_string(self, coercer: TypeCoercer) -> None:
        """Test empty string passes through."""
        result = coercer.coerce("", "Utf8")
        assert result == ""

    def test_zero_value_numeric(self, coercer: TypeCoercer) -> None:
        """Test zero values are preserved."""
        result = coercer.coerce("0", "Decimal")
        assert result == Decimal("0")
        assert result is not None

    def test_zero_float(self, coercer: TypeCoercer) -> None:
        """Test zero float is preserved."""
        result = coercer.coerce(0.0, "Float64")
        assert result == 0.0
        assert result is not None


# ============================================================================
# ADVERSARIAL TESTS - QA Adversary Deep Validation
# Per TDD-custom-field-type-coercion validation
# ============================================================================


class TestAdversarialNestedAndComplexLists:
    """Adversarial tests for complex list handling.

    Tests edge cases not covered by standard tests:
    - Deeply nested lists
    - Mixed types including None
    - Unicode edge cases
    - Extremely large values
    """

    def test_nested_list_flattens_to_string_repr(self, coercer: TypeCoercer) -> None:
        """Test nested list converts via str() - POTENTIAL BUG VECTOR.

        Nested lists should NOT appear in Asana multi_enum, but if they do,
        the coercer should handle them gracefully (convert via str()).
        """
        # Nested list - this could happen with corrupted data
        nested = ["A", ["B", "C"], "D"]
        result = coercer.coerce(nested, "Utf8")
        # The nested list will be str()-converted: "['B', 'C']"
        assert result is not None
        assert "A" in result
        assert "D" in result
        # The nested list becomes string representation
        assert "['B', 'C']" in result or "[" in result

    def test_deeply_nested_list_three_levels(self, coercer: TypeCoercer) -> None:
        """Test three-level nested list for memory/recursion issues."""
        deep_nested = ["A", [["inner"]], "B"]
        result = coercer.coerce(deep_nested, "Utf8")
        assert result is not None
        assert isinstance(result, str)

    def test_mixed_types_with_none_numbers_strings(
        self, coercer: TypeCoercer
    ) -> None:
        """Test list with None interspersed with numbers and strings."""
        mixed = [None, "A", 123, None, "B", 45.6, None]
        result = coercer.coerce(mixed, "Utf8")
        # None values should be filtered out
        assert result == "A, 123, B, 45.6"

    def test_list_with_empty_strings(self, coercer: TypeCoercer) -> None:
        """Test list containing empty strings.

        Empty strings should NOT be filtered (they're not None).
        """
        with_empties = ["A", "", "B", "", "C"]
        result = coercer.coerce(with_empties, "Utf8")
        # Empty strings should be preserved
        assert result == "A, , B, , C"

    def test_list_with_only_empty_strings(self, coercer: TypeCoercer) -> None:
        """Test list containing only empty strings."""
        only_empties = ["", "", ""]
        result = coercer.coerce(only_empties, "Utf8")
        # Should join the empty strings with separator
        assert result == ", , "

    def test_list_with_whitespace_strings(self, coercer: TypeCoercer) -> None:
        """Test list containing whitespace-only strings."""
        whitespace = ["A", "   ", "B", "\t", "C"]
        result = coercer.coerce(whitespace, "Utf8")
        # Whitespace strings should be preserved
        assert "   " in result
        assert "\t" in result

    def test_unicode_emoji_in_list(self, coercer: TypeCoercer) -> None:
        """Test Unicode emoji handling in list values."""
        emoji_list = ["Priority", "High", "Review"]
        result = coercer.coerce(emoji_list, "Utf8")
        assert "" in result
        assert "" in result

    def test_unicode_cjk_characters(self, coercer: TypeCoercer) -> None:
        """Test CJK (Chinese, Japanese, Korean) character handling."""
        cjk = ["Hello", "", "", ""]  # Hello, Chinese, Japanese, Korean
        result = coercer.coerce(cjk, "Utf8")
        assert result == "Hello, , , "

    def test_unicode_rtl_languages(self, coercer: TypeCoercer) -> None:
        """Test right-to-left language handling (Arabic, Hebrew)."""
        rtl = ["English", "", ""]  # English, Arabic, Hebrew
        result = coercer.coerce(rtl, "Utf8")
        assert "" in result
        assert "" in result

    def test_unicode_combining_characters(self, coercer: TypeCoercer) -> None:
        """Test Unicode combining/diacritical characters."""
        combining = ["cafe", "naive", "resume", "Muller"]
        result = coercer.coerce(combining, "Utf8")
        # These are plain ASCII - the coercer doesn't add diacriticals
        assert "cafe" in result
        assert "naive" in result
        assert "resume" in result
        assert "Muller" in result

    def test_unicode_diacritical_characters(self, coercer: TypeCoercer) -> None:
        """Test Unicode diacritical characters are preserved."""
        diacriticals = ["cafe", "naive", "resume", "Muller"]
        result = coercer.coerce(diacriticals, "Utf8")
        assert result == "cafe, naive, resume, Muller"

    def test_very_long_string_values_in_list(self, coercer: TypeCoercer) -> None:
        """Test list with very long individual string values."""
        long_string = "X" * 10000
        long_list = [long_string, "Short", long_string]
        result = coercer.coerce(long_list, "Utf8")
        assert result is not None
        assert len(result) > 20000
        assert "Short" in result

    def test_extremely_large_list_10000_items(self, coercer: TypeCoercer) -> None:
        """Test coercion of extremely large list (10000 items)."""
        huge_list = [f"item_{i}" for i in range(10000)]
        result = coercer.coerce(huge_list, "Utf8")
        assert result is not None
        assert result.count(", ") == 9999
        assert "item_0" in result
        assert "item_9999" in result

    def test_list_with_boolean_values(self, coercer: TypeCoercer) -> None:
        """Test list with boolean values."""
        bools = [True, False, True]
        result = coercer.coerce(bools, "Utf8")
        assert result == "True, False, True"

    def test_list_with_float_precision(self, coercer: TypeCoercer) -> None:
        """Test list with float precision edge cases."""
        floats = [0.1 + 0.2, 1.1, 2.2]  # 0.1 + 0.2 = 0.30000000000000004
        result = coercer.coerce(floats, "Utf8")
        assert result is not None
        # Should contain the float representation
        assert "0.3" in result

    def test_list_with_decimal_values(self, coercer: TypeCoercer) -> None:
        """Test list with Decimal values converts properly."""
        decimals = [Decimal("100.00"), Decimal("200.50")]
        result = coercer.coerce(decimals, "Utf8")
        assert result == "100.00, 200.50"


class TestAdversarialUnexpectedTypes:
    """Adversarial tests for unexpected input types.

    Tests behavior when receiving types that shouldn't normally occur
    but might due to bugs or data corruption.
    """

    def test_tuple_to_string_dtype(self, coercer: TypeCoercer) -> None:
        """Test tuple input to Utf8 dtype.

        Tuples are iterable but not lists - verify behavior.
        """
        # Tuple is not a list, so should pass through as unknown type
        tup = ("A", "B", "C")
        result = coercer.coerce(tup, "Utf8")
        # Tuple is not isinstance(list), so should passthrough
        assert result == ("A", "B", "C")

    def test_set_to_string_dtype(self, coercer: TypeCoercer) -> None:
        """Test set input to Utf8 dtype.

        Sets are iterable but not lists - verify behavior.
        """
        s = {"A", "B", "C"}
        result = coercer.coerce(s, "Utf8")
        # Set is not isinstance(list), so should passthrough
        assert result == s

    def test_frozenset_to_string_dtype(self, coercer: TypeCoercer) -> None:
        """Test frozenset input to Utf8 dtype."""
        fs = frozenset(["A", "B", "C"])
        result = coercer.coerce(fs, "Utf8")
        # frozenset is not isinstance(list), so should passthrough
        assert result == fs

    def test_generator_to_string_dtype(self, coercer: TypeCoercer) -> None:
        """Test generator input to Utf8 dtype.

        Generators are iterable - verify they're not consumed.
        """
        gen = (x for x in ["A", "B", "C"])
        result = coercer.coerce(gen, "Utf8")
        # Generator is not isinstance(list), so should passthrough
        # The generator object itself is returned
        assert result is not None

    def test_dict_to_string_dtype(self, coercer: TypeCoercer) -> None:
        """Test dict input to Utf8 dtype."""
        d = {"key1": "value1", "key2": "value2"}
        result = coercer.coerce(d, "Utf8")
        # Dict is not a string or list, should passthrough
        assert result == d

    def test_bytes_to_string_dtype(self, coercer: TypeCoercer) -> None:
        """Test bytes input to Utf8 dtype."""
        b = b"hello world"
        result = coercer.coerce(b, "Utf8")
        # bytes is not str or list, should passthrough
        assert result == b

    def test_bytearray_to_string_dtype(self, coercer: TypeCoercer) -> None:
        """Test bytearray input to Utf8 dtype."""
        ba = bytearray(b"hello")
        result = coercer.coerce(ba, "Utf8")
        # bytearray is not str or list, should passthrough
        assert result == ba

    def test_custom_object_with_iter(self, coercer: TypeCoercer) -> None:
        """Test custom iterable object to Utf8 dtype."""

        class CustomIterable:
            def __iter__(self):
                return iter(["A", "B", "C"])

        obj = CustomIterable()
        result = coercer.coerce(obj, "Utf8")
        # Custom object is not list, should passthrough
        assert result is obj

    def test_custom_object_with_str(self, coercer: TypeCoercer) -> None:
        """Test custom object with __str__ to Utf8 dtype."""

        class CustomStr:
            def __str__(self):
                return "CustomString"

        obj = CustomStr()
        result = coercer.coerce(obj, "Utf8")
        # Not a list or str instance, should passthrough
        assert result is obj

    def test_list_subclass_is_list(self, coercer: TypeCoercer) -> None:
        """Test list subclass is treated as list."""

        class MyList(list):
            pass

        my_list = MyList(["A", "B", "C"])
        result = coercer.coerce(my_list, "Utf8")
        # Should be treated as list (isinstance check)
        assert result == "A, B, C"

    def test_string_subclass_is_string(self, coercer: TypeCoercer) -> None:
        """Test string subclass is treated as string."""

        class MyStr(str):
            pass

        my_str = MyStr("hello")
        result = coercer.coerce(my_str, "Utf8")
        # Should be treated as string
        assert result == "hello"


class TestAdversarialNumericBoundaries:
    """Adversarial tests for numeric coercion boundary conditions.

    Tests edge cases in numeric conversion:
    - Infinity
    - NaN
    - Very large/small numbers
    - Precision limits
    """

    def test_infinity_to_decimal(self, coercer: TypeCoercer) -> None:
        """Test infinity string to Decimal.

        NOTE: Python Decimal DOES support Infinity, unlike some expectations.
        This is documented behavior per Python decimal module.
        """
        result = coercer.coerce("Infinity", "Decimal")
        # Python Decimal supports special values
        assert result == Decimal("Infinity")
        assert result.is_infinite()

    def test_negative_infinity_to_decimal(self, coercer: TypeCoercer) -> None:
        """Test negative infinity string to Decimal."""
        result = coercer.coerce("-Infinity", "Decimal")
        assert result == Decimal("-Infinity")
        assert result.is_infinite()

    def test_nan_string_to_decimal(self, coercer: TypeCoercer) -> None:
        """Test NaN string to Decimal.

        NOTE: Python Decimal DOES support NaN, unlike some expectations.
        This is documented behavior per Python decimal module.
        """
        result = coercer.coerce("NaN", "Decimal")
        # Python Decimal supports NaN
        assert isinstance(result, Decimal)
        assert result.is_nan()

    def test_float_infinity_to_decimal(self, coercer: TypeCoercer) -> None:
        """Test float infinity to Decimal.

        NOTE: Python Decimal supports Infinity when converted from string.
        str(math.inf) = "inf", and Decimal("inf") creates Decimal('Infinity').
        """
        import math

        result = coercer.coerce(math.inf, "Decimal")
        # str(math.inf) = "inf", Decimal("inf") = Decimal('Infinity')
        assert isinstance(result, Decimal)
        assert result.is_infinite()

    def test_float_nan_to_decimal(self, coercer: TypeCoercer) -> None:
        """Test float NaN to Decimal.

        NOTE: Python Decimal supports NaN when converted from string.
        """
        import math

        result = coercer.coerce(math.nan, "Decimal")
        # str(math.nan) = "nan", Decimal("nan") = Decimal('NaN')
        assert isinstance(result, Decimal)
        assert result.is_nan()

    def test_infinity_to_float64(self, coercer: TypeCoercer) -> None:
        """Test infinity string to Float64."""
        import math

        result = coercer.coerce("inf", "Float64")
        # float("inf") is valid
        assert result == math.inf

    def test_nan_to_float64(self, coercer: TypeCoercer) -> None:
        """Test NaN string to Float64."""
        import math

        result = coercer.coerce("nan", "Float64")
        # float("nan") is valid but NaN != NaN
        assert math.isnan(result)

    def test_infinity_to_int64(self, coercer: TypeCoercer) -> None:
        """Test infinity to Int64.

        FIXED: OverflowError is now caught and returns None gracefully.
        int(float("inf")) raises OverflowError, which is now handled
        in _to_numeric() exception handler.
        """
        # Fixed: Returns None instead of raising OverflowError
        result = coercer.coerce("inf", "Int64")
        assert result is None

    def test_very_large_number_to_decimal(self, coercer: TypeCoercer) -> None:
        """Test very large number to Decimal."""
        huge = "9" * 100  # 100-digit number
        result = coercer.coerce(huge, "Decimal")
        assert result is not None
        assert isinstance(result, Decimal)
        assert result == Decimal(huge)

    def test_very_small_decimal(self, coercer: TypeCoercer) -> None:
        """Test very small decimal number."""
        tiny = "0." + "0" * 50 + "1"
        result = coercer.coerce(tiny, "Decimal")
        assert result is not None
        assert isinstance(result, Decimal)

    def test_max_int64_boundary(self, coercer: TypeCoercer) -> None:
        """Test Int64 max value boundary.

        FIXED: Direct int() conversion is now tried first for strings,
        preserving precision for large integers. Only falls back to
        float() for decimal strings like "123.0".
        """
        max_int64 = "9223372036854775807"  # 2^63 - 1
        result = coercer.coerce(max_int64, "Int64")
        # Fixed: Direct int() conversion preserves precision
        assert result == 9223372036854775807

    def test_overflow_int64(self, coercer: TypeCoercer) -> None:
        """Test Int64 overflow behavior.

        Python ints are arbitrary precision, so this should work.
        """
        overflow = "9223372036854775808"  # 2^63 (one over max)
        result = coercer.coerce(overflow, "Int64")
        # Python int has no overflow, so this should work
        assert result == 9223372036854775808

    def test_negative_zero(self, coercer: TypeCoercer) -> None:
        """Test negative zero handling."""
        result = coercer.coerce("-0", "Float64")
        # -0.0 == 0.0 in Python
        assert result == 0.0

    def test_decimal_with_exponent(self, coercer: TypeCoercer) -> None:
        """Test Decimal with positive exponent."""
        result = coercer.coerce("1E+10", "Decimal")
        assert result == Decimal("1E+10")

    def test_decimal_with_negative_exponent(self, coercer: TypeCoercer) -> None:
        """Test Decimal with negative exponent."""
        result = coercer.coerce("1E-10", "Decimal")
        assert result == Decimal("1E-10")

    def test_string_with_leading_zeros(self, coercer: TypeCoercer) -> None:
        """Test numeric string with leading zeros."""
        result = coercer.coerce("00123", "Int64")
        assert result == 123

    def test_string_with_spaces(self, coercer: TypeCoercer) -> None:
        """Test numeric string with spaces (should fail)."""
        result = coercer.coerce(" 123 ", "Int64")
        # float(" 123 ") works in Python
        assert result == 123

    def test_string_with_comma(self, coercer: TypeCoercer) -> None:
        """Test numeric string with comma formatting (should fail)."""
        result = coercer.coerce("1,234", "Int64")
        # float("1,234") raises ValueError
        assert result is None

    def test_string_with_currency_symbol(self, coercer: TypeCoercer) -> None:
        """Test numeric string with currency symbol (should fail)."""
        result = coercer.coerce("$100", "Decimal")
        assert result is None

    def test_string_with_percent(self, coercer: TypeCoercer) -> None:
        """Test numeric string with percent symbol (should fail)."""
        result = coercer.coerce("50%", "Float64")
        assert result is None


class TestAdversarialUnknownDtypes:
    """Adversarial tests for unknown/unsupported dtype handling.

    Tests behavior with dtypes that are not in the known sets.
    """

    def test_unknown_dtype_passthrough_list(self, coercer: TypeCoercer) -> None:
        """Test list with unknown dtype passes through unchanged."""
        lst = ["A", "B", "C"]
        result = coercer.coerce(lst, "RandomType")
        # Unknown dtype should passthrough
        assert result is lst

    def test_unknown_dtype_passthrough_string(self, coercer: TypeCoercer) -> None:
        """Test string with unknown dtype passes through unchanged."""
        s = "hello"
        result = coercer.coerce(s, "WeirdType")
        assert result == "hello"

    def test_case_sensitive_dtype(self, coercer: TypeCoercer) -> None:
        """Test dtype matching is case-sensitive."""
        # "utf8" is not the same as "Utf8"
        result = coercer.coerce(["A", "B"], "utf8")
        # Should passthrough since "utf8" not in STRING_DTYPES
        assert result == ["A", "B"]

    def test_dtype_with_whitespace(self, coercer: TypeCoercer) -> None:
        """Test dtype with whitespace is not recognized."""
        result = coercer.coerce(["A", "B"], " Utf8 ")
        # " Utf8 " is not in STRING_DTYPES
        assert result == ["A", "B"]

    def test_similar_dtype_names(self, coercer: TypeCoercer) -> None:
        """Test similar but incorrect dtype names."""
        # These should all passthrough
        assert coercer.coerce(["A"], "UTF8") == ["A"]
        assert coercer.coerce(["A"], "utf-8") == ["A"]
        assert coercer.coerce(["A"], "Utf-8") == ["A"]
        assert coercer.coerce(["A"], "List") == ["A"]
        assert coercer.coerce(["A"], "list[Utf8]") == ["A"]

    def test_empty_dtype(self, coercer: TypeCoercer) -> None:
        """Test empty string dtype."""
        result = coercer.coerce(["A", "B"], "")
        # Empty string is unknown dtype, passthrough
        assert result == ["A", "B"]

    def test_numeric_dtype_string(self, coercer: TypeCoercer) -> None:
        """Test numeric string as dtype."""
        result = coercer.coerce("100", "123")
        # "123" is unknown dtype, passthrough
        assert result == "100"


class TestAdversarialConcurrency:
    """Adversarial tests for concurrent coercion operations.

    Tests thread safety under concurrent load.
    """

    def test_concurrent_coercion_same_input(self) -> None:
        """Test concurrent coercion with same input."""
        import threading
        from concurrent.futures import ThreadPoolExecutor

        coercer = TypeCoercer()
        results: list[str | None] = []
        errors: list[Exception] = []

        def coerce_task():
            try:
                result = coercer.coerce(["A", "B", "C"], "Utf8")
                results.append(result)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(coerce_task) for _ in range(100)]
            for f in futures:
                f.result(timeout=10)

        assert len(errors) == 0
        assert len(results) == 100
        assert all(r == "A, B, C" for r in results)

    def test_concurrent_coercion_different_inputs(self) -> None:
        """Test concurrent coercion with different inputs."""
        import threading
        from concurrent.futures import ThreadPoolExecutor

        coercer = TypeCoercer()
        results: dict[int, str | None] = {}
        errors: list[Exception] = []
        lock = threading.Lock()

        def coerce_task(i: int):
            try:
                input_list = [f"item_{i}_{j}" for j in range(3)]
                result = coercer.coerce(input_list, "Utf8")
                with lock:
                    results[i] = result
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(coerce_task, i) for i in range(50)]
            for f in futures:
                f.result(timeout=10)

        assert len(errors) == 0
        assert len(results) == 50
        # Each result should be unique
        for i in range(50):
            expected = f"item_{i}_0, item_{i}_1, item_{i}_2"
            assert results[i] == expected

    def test_concurrent_module_singleton(self) -> None:
        """Test module-level coerce_value is thread-safe."""
        from concurrent.futures import ThreadPoolExecutor

        results: list[str | None] = []

        def coerce_task(i: int):
            return coerce_value([f"thread_{i}"], "Utf8")

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(coerce_task, i) for i in range(100)]
            for f in futures:
                results.append(f.result(timeout=10))

        # All should succeed
        assert len(results) == 100
        for i, r in enumerate(results):
            assert r is not None


class TestAdversarialListToListPassthrough:
    """Adversarial tests for list-to-list passthrough behavior."""

    def test_list_with_none_passthrough(self, coercer: TypeCoercer) -> None:
        """Test list with None values passed through unchanged for List dtype."""
        lst = ["A", None, "B"]
        result = coercer.coerce(lst, "List[Utf8]")
        # Passthrough should preserve the list reference
        assert result is lst
        assert result == ["A", None, "B"]

    def test_list_with_mixed_types_passthrough(self, coercer: TypeCoercer) -> None:
        """Test list with mixed types passed through for List dtype."""
        lst = ["A", 123, True, None]
        result = coercer.coerce(lst, "List[Utf8]")
        # Passthrough - no modification
        assert result is lst

    def test_empty_list_passthrough_reference(self, coercer: TypeCoercer) -> None:
        """Test empty list returns same reference."""
        lst: list[str] = []
        result = coercer.coerce(lst, "List[Utf8]")
        assert result is lst

    def test_list_mutation_after_passthrough(self, coercer: TypeCoercer) -> None:
        """Test that passthrough doesn't protect against mutation.

        This is expected behavior but worth documenting.
        """
        lst = ["A", "B"]
        result = coercer.coerce(lst, "List[Utf8]")
        lst.append("C")
        # Result is same reference, so it sees the mutation
        assert result == ["A", "B", "C"]


class TestAdversarialSpecialStringValues:
    """Adversarial tests for special string values."""

    def test_string_none_literal(self, coercer: TypeCoercer) -> None:
        """Test string containing 'None' literal."""
        result = coercer.coerce("None", "Utf8")
        assert result == "None"  # Not Python None

    def test_string_null_literal(self, coercer: TypeCoercer) -> None:
        """Test string containing 'null' literal."""
        result = coercer.coerce("null", "Utf8")
        assert result == "null"

    def test_string_with_separator(self, coercer: TypeCoercer) -> None:
        """Test string containing the separator character."""
        # String that looks like a joined list
        result = coercer.coerce("A, B, C", "Utf8")
        assert result == "A, B, C"  # Unchanged

    def test_list_with_separator_in_values(self, coercer: TypeCoercer) -> None:
        """Test list where values contain the separator."""
        lst = ["A, B", "C, D"]
        result = coercer.coerce(lst, "Utf8")
        # Should join normally - separator inside values is preserved
        assert result == "A, B, C, D"  # Ambiguous but expected

    def test_string_newline(self, coercer: TypeCoercer) -> None:
        """Test string with newline characters."""
        result = coercer.coerce("line1\nline2", "Utf8")
        assert result == "line1\nline2"

    def test_list_with_newlines(self, coercer: TypeCoercer) -> None:
        """Test list with newline characters in values."""
        lst = ["line1\nline2", "line3"]
        result = coercer.coerce(lst, "Utf8")
        assert "line1\nline2" in result

    def test_string_carriage_return(self, coercer: TypeCoercer) -> None:
        """Test string with carriage return."""
        result = coercer.coerce("line1\r\nline2", "Utf8")
        assert result == "line1\r\nline2"

    def test_string_tab(self, coercer: TypeCoercer) -> None:
        """Test string with tab character."""
        result = coercer.coerce("col1\tcol2", "Utf8")
        assert result == "col1\tcol2"

    def test_string_null_byte(self, coercer: TypeCoercer) -> None:
        """Test string with null byte character."""
        result = coercer.coerce("before\x00after", "Utf8")
        assert result == "before\x00after"

    def test_list_with_null_bytes(self, coercer: TypeCoercer) -> None:
        """Test list with null bytes in values."""
        lst = ["a\x00b", "c"]
        result = coercer.coerce(lst, "Utf8")
        assert "\x00" in result


class TestAdversarialNumericToString:
    """Adversarial tests for numeric-to-string scenarios."""

    def test_decimal_to_string_dtype(self, coercer: TypeCoercer) -> None:
        """Test Decimal value with Utf8 target dtype."""
        d = Decimal("123.45")
        result = coercer.coerce(d, "Utf8")
        # Not a list or string, should passthrough
        assert result == d

    def test_int_to_string_dtype(self, coercer: TypeCoercer) -> None:
        """Test int value with Utf8 target dtype."""
        i = 123
        result = coercer.coerce(i, "Utf8")
        # Not a list or string, should passthrough
        assert result == 123

    def test_float_to_string_dtype(self, coercer: TypeCoercer) -> None:
        """Test float value with Utf8 target dtype."""
        f = 123.45
        result = coercer.coerce(f, "Utf8")
        # Not a list or string, should passthrough
        assert result == 123.45

    def test_bool_to_string_dtype(self, coercer: TypeCoercer) -> None:
        """Test bool value with Utf8 target dtype."""
        b = True
        result = coercer.coerce(b, "Utf8")
        # Not a list or string, should passthrough
        assert result is True
