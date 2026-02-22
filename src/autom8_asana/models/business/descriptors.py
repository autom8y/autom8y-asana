"""Descriptors for Business Model layer.

Per TDD-HARDENING-C: Generic descriptors for navigation property consolidation.
Per TDD-PATTERNS-A: Custom field descriptors for declarative property access.
Per ADR-0075: Single ParentRef[T] and HolderRef[T] descriptor pattern.
Per ADR-0076: Auto-invalidation on parent reference change.
Per ADR-0081: Custom field descriptor pattern.
Per ADR-0082: Fields class auto-generation strategy.

These descriptors replace ~800 lines of duplicated @property implementations
across business entities with a declarative pattern.

IMPORTANT: Due to Pydantic v2 field handling, descriptors must be declared
WITHOUT type annotations to avoid being treated as model fields. The generic
type parameter provides IDE type hints through @overload.

Example (Navigation):
    class Contact(BusinessEntity):
        # PrivateAttrs for storage (with type annotations)
        _business: Business | None = PrivateAttr(default=None)
        _contact_holder: ContactHolder | None = PrivateAttr(default=None)

        # Descriptors WITHOUT type annotations (avoid Pydantic field creation)
        business = ParentRef[Business](holder_attr="_contact_holder")
        contact_holder = HolderRef[ContactHolder]()

Example (Custom Fields):
    class Business(BusinessEntity):
        # Descriptors WITHOUT type annotations (avoid Pydantic field creation)
        company_id = TextField()
        mrr = NumberField()
        vertical = EnumField()
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, ClassVar, Generic, TypeVar, overload

import arrow
from autom8y_log import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

# Module-level registry for pending field registrations (ADR-0082)
# Uses class id() as key since class may not be fully constructed during __set_name__
_pending_fields: dict[int, dict[str, str]] = {}


def _register_custom_field(
    owner: type[Any], descriptor: CustomFieldDescriptor[Any]
) -> None:
    """Register a custom field descriptor for Fields class generation.

    Called during descriptor.__set_name__() to register field for Fields generation.
    Per ADR-0082: Two-phase registration via __set_name__ + __init_subclass__.

    Args:
        owner: The class being defined.
        descriptor: The descriptor being registered.
    """
    if descriptor.field_name is None:
        return  # Should not happen, but be defensive

    owner_id = id(owner)
    if owner_id not in _pending_fields:
        _pending_fields[owner_id] = {}
    _pending_fields[owner_id][descriptor._constant_name] = descriptor.field_name



# Re-export Arrow type for use in annotations
Arrow = arrow.Arrow


class ParentRef(Generic[T]):
    """Descriptor for cached upward navigation with lazy resolution.

    Per ADR-0075: Single descriptor type handles all navigation patterns.

    Type Parameters:
        T: The type being navigated to (e.g., Business, ContactHolder)

    Args:
        holder_attr: PrivateAttr name to resolve from (e.g., "_contact_holder").
            If provided, enables lazy resolution when cached value is None.
        target_attr: Attribute on holder to resolve to (default "_business").
        auto_invalidate: If True (default), setting triggers _invalidate_refs().

    Example:
        class Contact(BusinessEntity):
            _business: Business | None = PrivateAttr(default=None)
            _contact_holder: ContactHolder | None = PrivateAttr(default=None)

            # Descriptor declaration
            business: Business | None = ParentRef[Business](
                holder_attr="_contact_holder"
            )
    """

    __slots__ = (
        "holder_attr",
        "target_attr",
        "auto_invalidate",
        "private_name",
        "public_name",
    )

    def __init__(
        self,
        holder_attr: str | None = None,
        target_attr: str = "_business",
        auto_invalidate: bool = True,
    ) -> None:
        """Initialize descriptor.

        Args:
            holder_attr: PrivateAttr name to resolve from.
            target_attr: Attribute on holder to resolve to.
            auto_invalidate: If True, setting triggers _invalidate_refs().
        """
        self.holder_attr = holder_attr
        self.target_attr = target_attr
        self.auto_invalidate = auto_invalidate
        self.private_name: str = ""
        self.public_name: str = ""

    def __set_name__(self, owner: type[Any], name: str) -> None:
        """Called when descriptor is assigned to class attribute.

        Per ADR-0075: Automatically derives private attribute name from public.

        Args:
            owner: The class that owns the descriptor.
            name: The attribute name on the owner class.
        """
        self.public_name = name
        self.private_name = f"_{name}"

    @overload
    def __get__(self, obj: None, objtype: type[Any]) -> ParentRef[T]: ...

    @overload
    def __get__(self, obj: Any, objtype: type[Any] | None) -> T | None: ...

    def __get__(
        self,
        obj: Any,
        objtype: type[Any] | None = None,
    ) -> T | None | ParentRef[T]:
        """Get cached value or lazy-resolve via holder.

        Per FR-DESC-002: Lazy resolution via holder_attr if cache is None.
        Per FR-DESC-005: Returns None (not AttributeError) when uninitialized.

        Args:
            obj: Instance to get value from, or None for class access.
            objtype: Class of the instance.

        Returns:
            Cached value, resolved value, or None if not available.
            Returns descriptor itself when accessed on class.
        """
        if obj is None:
            # Class-level access returns descriptor itself
            return self

        # Check cached value in PrivateAttr
        cached: T | None = getattr(obj, self.private_name, None)
        if cached is not None:
            return cached

        # Lazy resolution via holder if configured
        if self.holder_attr:
            holder = getattr(obj, self.holder_attr, None)
            if holder is not None:
                resolved: T | None = getattr(holder, self.target_attr, None)
                if resolved is not None:
                    # Cache the resolved value
                    setattr(obj, self.private_name, resolved)
                    return resolved

        return None

    def __set__(self, obj: Any, value: T | None) -> None:
        """Set cached value and optionally trigger invalidation.

        Per ADR-0076: Auto-invalidation on parent reference change.
        Per FR-INV-003: Setting triggers _invalidate_refs() if configured.
        Per FR-INV-004: Only triggers on write, not read.

        Args:
            obj: Instance to set value on.
            value: Value to set (or None to clear).
        """
        # Store current value to detect actual change
        old_value = getattr(obj, self.private_name, None)

        # Set the new value
        setattr(obj, self.private_name, value)

        # Auto-invalidate on actual change (not just re-assignment of same value)
        if (
            self.auto_invalidate
            and old_value is not value
            and hasattr(obj, "_invalidate_refs")
        ):
            # Don't re-invalidate the attr we just set
            logger.debug(
                "auto_invalidating_refs",
                obj_type=type(obj).__name__,
                attr=self.public_name,
            )
            obj._invalidate_refs(_exclude_attr=self.private_name)


class HolderRef(Generic[T]):
    """Descriptor for direct holder property access.

    Per ADR-0075: Simpler descriptor for holder references without lazy resolution.

    Type Parameters:
        T: The holder type (e.g., ContactHolder, UnitHolder)

    Example:
        class Contact(BusinessEntity):
            _contact_holder: ContactHolder | None = PrivateAttr(default=None)

            # Descriptor declaration
            contact_holder: ContactHolder | None = HolderRef[ContactHolder]()
    """

    __slots__ = ("private_name", "public_name")

    def __init__(self) -> None:
        """Initialize descriptor."""
        self.private_name: str = ""
        self.public_name: str = ""

    def __set_name__(self, owner: type[Any], name: str) -> None:
        """Derive private attribute name from public.

        Args:
            owner: The class that owns the descriptor.
            name: The attribute name on the owner class.
        """
        self.public_name = name
        self.private_name = f"_{name}"

    @overload
    def __get__(self, obj: None, objtype: type[Any]) -> HolderRef[T]: ...

    @overload
    def __get__(self, obj: Any, objtype: type[Any] | None) -> T | None: ...

    def __get__(
        self,
        obj: Any,
        objtype: type[Any] | None = None,
    ) -> T | None | HolderRef[T]:
        """Get holder reference from PrivateAttr.

        Per FR-DESC-004: Direct holder access without lazy resolution.

        Args:
            obj: Instance to get value from, or None for class access.
            objtype: Class of the instance.

        Returns:
            Cached holder reference or None.
            Returns descriptor itself when accessed on class.
        """
        if obj is None:
            return self
        return getattr(obj, self.private_name, None)

    def __set__(self, obj: Any, value: T | None) -> None:
        """Set holder reference.

        Per ADR-0076: Holder changes also trigger invalidation since
        they affect upward navigation.

        Args:
            obj: Instance to set value on.
            value: Holder instance to set (or None to clear).
        """
        old_value = getattr(obj, self.private_name, None)
        setattr(obj, self.private_name, value)

        # Holder change should invalidate other refs
        if old_value is not value and hasattr(obj, "_invalidate_refs"):
            logger.debug(
                "auto_invalidating_refs_holder_change",
                obj_type=type(obj).__name__,
                attr=self.public_name,
            )
            obj._invalidate_refs(_exclude_attr=self.private_name)


# =============================================================================
# Custom Field Descriptors (ADR-0081)
# =============================================================================


class CustomFieldDescriptor(Generic[T]):
    """Base descriptor for custom field properties.

    Per ADR-0081: Single generic base with type-specific subclasses.
    Per ADR-0077: Declared WITHOUT type annotations to avoid Pydantic field creation.
    Per ADR-0082: Registers with _pending_fields for Fields class generation.

    Attributes:
        field_name: Asana custom field name (derived or explicit).
        cascading: If True, field participates in cascading system (metadata only).
        public_name: Property name on model (set by __set_name__).
        _constant_name: SCREAMING_SNAKE version for Fields class (set by __set_name__).

    Example:
        class Business(BusinessEntity):
            # Descriptor WITHOUT type annotation (avoid Pydantic field creation)
            company_id = TextField()  # Derives "Company ID"
            mrr = NumberField(field_name="MRR")  # Explicit override
    """

    __slots__ = ("field_name", "cascading", "public_name", "_constant_name")

    # Known abbreviations that should remain uppercase (ADR-0082)
    ABBREVIATIONS: ClassVar[frozenset[str]] = frozenset(
        {"mrr", "ai", "url", "id", "num", "cal", "vca", "sms", "ad"}
    )

    def __init__(
        self,
        field_name: str | None = None,
        cascading: bool = False,
    ) -> None:
        """Initialize descriptor.

        Args:
            field_name: Explicit Asana field name. If None, derived from property name.
            cascading: If True, marks field for cascading system (metadata only).
        """
        self.field_name: str | None = field_name
        self.cascading = cascading
        self.public_name: str = ""
        self._constant_name: str = ""

    def __set_name__(self, owner: type[Any], name: str) -> None:
        """Called when descriptor assigned to class attribute.

        Per ADR-0082: Derives field name and registers for Fields class generation.

        Args:
            owner: The class that owns the descriptor.
            name: The attribute name on the owner class.
        """
        self.public_name = name
        self._constant_name = name.upper()

        if self.field_name is None:
            self.field_name = self._derive_field_name(name)

        # Register for Fields class generation (via __init_subclass__)
        _register_custom_field(owner, self)

    def _derive_field_name(self, name: str) -> str:
        """Derive 'Title Case' field name from snake_case property.

        Per ADR-0082: Preserves known abbreviations as uppercase.

        Examples:
            company_id -> "Company ID"
            mrr -> "MRR"
            num_ai_copies -> "Num AI Copies"

        Args:
            name: Property name in snake_case.

        Returns:
            Title Case field name with abbreviations preserved.
        """
        parts = name.split("_")
        result: list[str] = []
        for part in parts:
            if part.lower() in self.ABBREVIATIONS:
                result.append(part.upper())
            else:
                result.append(part.capitalize())
        return " ".join(result)

    @overload
    def __get__(self, obj: None, objtype: type[Any]) -> CustomFieldDescriptor[T]: ...

    @overload
    def __get__(self, obj: Any, objtype: type[Any] | None) -> T: ...

    def __get__(
        self,
        obj: Any,
        objtype: type[Any] | None = None,
    ) -> T | CustomFieldDescriptor[T]:
        """Get custom field value from model.

        Args:
            obj: Instance to get value from, or None for class access.
            objtype: Class of the instance.

        Returns:
            Transformed field value, or descriptor itself for class access.
        """
        if obj is None:
            return self
        return self._get_value(obj)

    def __set__(self, obj: Any, value: T | None) -> None:
        """Set custom field value on model.

        Args:
            obj: Instance to set value on.
            value: Value to set.
        """
        self._set_value(obj, value)

    def _get_value(self, obj: Any) -> T:
        """Get and transform value. Override in subclasses.

        Args:
            obj: Instance to get value from.

        Returns:
            Transformed field value.

        Raises:
            NotImplementedError: If not overridden in subclass.
        """
        raise NotImplementedError("Subclasses must implement _get_value")

    def _set_value(self, obj: Any, value: T | None) -> None:
        """Set value with optional transformation. Override in subclasses.

        Default implementation passes value through to CustomFieldAccessor.set().

        Args:
            obj: Instance to set value on.
            value: Value to set (may be transformed by subclass).
        """
        obj.get_custom_fields().set(self.field_name, value)


class TextField(CustomFieldDescriptor[str | None]):
    """Descriptor for text custom fields.

    Returns str | None. Coerces non-string values to string.

    Example:
        class Business(BusinessEntity):
            company_id = TextField()  # Returns str | None
    """

    def _get_value(self, obj: Any) -> str | None:
        """Get text value, coercing non-strings.

        Args:
            obj: Instance to get value from.

        Returns:
            String value, or None if not set.
        """
        value = obj.get_custom_fields().get(self.field_name)
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return str(value)


class EnumField(CustomFieldDescriptor[str | None]):
    """Descriptor for enum custom fields.

    Extracts name from dict: {"gid": "123", "name": "Value"} -> "Value"
    Handles string passthrough for already-extracted values.

    Example:
        class Business(BusinessEntity):
            vertical = EnumField()  # Returns str | None
    """

    def _get_value(self, obj: Any) -> str | None:
        """Get enum value, extracting name from dict if needed.

        Args:
            obj: Instance to get value from.

        Returns:
            Enum name string, or None if not set.
        """
        value = obj.get_custom_fields().get(self.field_name)
        if value is None:
            return None
        if isinstance(value, dict):
            name = value.get("name")
            return str(name) if name is not None else None
        if isinstance(value, str):
            return value
        return str(value)


class MultiEnumField(CustomFieldDescriptor[list[str]]):
    """Descriptor for multi-enum custom fields.

    Returns list[str], never None. Extracts names from list of dicts.

    Example:
        class Unit(BusinessEntity):
            ai_ad_types = MultiEnumField()  # Returns list[str]
    """

    def _get_value(self, obj: Any) -> list[str]:
        """Get multi-enum values, extracting names from dicts.

        Args:
            obj: Instance to get value from.

        Returns:
            List of enum name strings. Empty list if not set.
        """
        value = obj.get_custom_fields().get(self.field_name)
        if value is None:
            return []
        if not isinstance(value, list):
            return []

        result: list[str] = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, dict):
                name = item.get("name")
                if name is not None:
                    result.append(str(name))
            elif isinstance(item, str):
                result.append(item)
        return result

    def _set_value(self, obj: Any, value: list[str] | None) -> None:
        """Set multi-enum value.

        Args:
            obj: Instance to set value on.
            value: List of enum names, or None to clear.
        """
        obj.get_custom_fields().set(self.field_name, value)


class NumberField(CustomFieldDescriptor[Decimal | None]):
    """Descriptor for decimal number custom fields.

    Returns Decimal for precision. Converts to float on write for API.

    Example:
        class Business(BusinessEntity):
            mrr = NumberField(field_name="MRR")  # Returns Decimal | None
    """

    def _get_value(self, obj: Any) -> Decimal | None:
        """Get number value as Decimal.

        Args:
            obj: Instance to get value from.

        Returns:
            Decimal value, or None if not set.
        """
        value = obj.get_custom_fields().get(self.field_name)
        if value is None:
            return None
        return Decimal(str(value))

    def _set_value(self, obj: Any, value: Decimal | None) -> None:
        """Set number value, converting Decimal to float for API.

        Args:
            obj: Instance to set value on.
            value: Decimal value, or None to clear.
        """
        api_value = float(value) if value is not None else None
        obj.get_custom_fields().set(self.field_name, api_value)


class IntField(CustomFieldDescriptor[int | None]):
    """Descriptor for integer number custom fields.

    Truncates to integer on read.

    Example:
        class Unit(BusinessEntity):
            num_ai_copies = IntField()  # Returns int | None
    """

    def _get_value(self, obj: Any) -> int | None:
        """Get number value as integer.

        Args:
            obj: Instance to get value from.

        Returns:
            Integer value (truncated), or None if not set.
        """
        value = obj.get_custom_fields().get(self.field_name)
        if value is None:
            return None
        return int(value)


class PeopleField(CustomFieldDescriptor[list[dict[str, Any]]]):
    """Descriptor for people custom fields.

    Returns list of person dicts, never None. Empty list when unset.

    Each dict contains Asana user fields like:
        {"gid": "123", "name": "John Doe", "email": "john@example.com"}

    Example:
        class Business(BusinessEntity):
            rep = PeopleField()  # Returns list[dict[str, Any]]
    """

    def _get_value(self, obj: Any) -> list[dict[str, Any]]:
        """Get people value as list of dicts.

        Args:
            obj: Instance to get value from.

        Returns:
            List of person dicts. Empty list if not set.
        """
        value = obj.get_custom_fields().get(self.field_name)
        if isinstance(value, list):
            return value
        return []

    def _set_value(self, obj: Any, value: list[dict[str, Any]] | None) -> None:
        """Set people value.

        Args:
            obj: Instance to set value on.
            value: List of person dicts, or None to clear.
        """
        obj.get_custom_fields().set(self.field_name, value)


class DateField(CustomFieldDescriptor[Arrow | None]):
    """Descriptor for date custom fields.

    Per ADR-0083: Uses Arrow library for rich date handling.
    Parses ISO 8601 date strings. Converts Arrow to ISO string on write.

    Arrow provides:
    - Timezone-aware datetime handling
    - Human-readable formatting ("2 hours ago")
    - Flexible parsing of various date formats
    - Rich comparison and arithmetic operations

    Example:
        class Process(BusinessEntity):
            process_due_date = DateField()  # Returns Arrow | None

        # Reading
        due = process.process_due_date
        if due:
            print(due.format('MMMM D, YYYY'))  # "December 16, 2025"
            print(due.humanize())               # "in 2 days"

        # Writing
        process.process_due_date = arrow.now().shift(days=7)
    """

    def _get_value(self, obj: Any) -> Arrow | None:
        """Get date value as Arrow object.

        Parses ISO 8601 date/datetime strings. Returns None for invalid values.

        Args:
            obj: Instance to get value from.

        Returns:
            Arrow object, or None if not set or invalid.
        """
        value = obj.get_custom_fields().get(self.field_name)
        if value is None or value == "":
            return None
        if isinstance(value, Arrow):
            return value
        if isinstance(value, str):
            try:
                # Arrow handles ISO 8601 dates and datetimes
                return arrow.get(value)
            except (ValueError, arrow.parser.ParserError):
                logger.warning(
                    "invalid_date_value",
                    field_name=self.field_name,
                    value=repr(value),
                )
                return None
        return None

    def _set_value(self, obj: Any, value: Arrow | None) -> None:
        """Set date value, converting Arrow to ISO string.

        Args:
            obj: Instance to set value on.
            value: Arrow object, or None to clear.
        """
        if value is None:
            api_value = None
        else:
            # Serialize to ISO 8601 date format for Asana
            api_value = value.format("YYYY-MM-DD")
        obj.get_custom_fields().set(self.field_name, api_value)
