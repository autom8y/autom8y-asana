# Design Pattern Opportunities Analysis

> Comprehensive architectural review identifying high-impact opportunities to leverage Python design patterns for improved efficiency, accuracy, and maintainability.

**Date**: 2025-12-16
**Scope**: `autom8_asana` SDK codebase
**Inspired By**: Navigation Descriptor Pattern success (Initiative C - ~800 lines eliminated)

---

## Executive Summary

This analysis identifies **5 high-impact pattern opportunities** that could collectively eliminate **2,000+ lines of duplicated code** while improving type safety, reducing bugs, and making the codebase more Pythonic.

### Top 5 Opportunities (Priority Order)

| # | Pattern | Impact | Lines Saved | Complexity |
|---|---------|--------|-------------|------------|
| 1 | **Async/Sync Method Generator** | Eliminates massive client method duplication | ~1,200 lines | Medium |
| 2 | **Custom Field Property Descriptor** | Unifies field accessor boilerplate | ~400 lines | Low |
| 3 | **Holder Factory with `__init_subclass__`** | Consolidates holder creation logic | ~300 lines | Medium |
| 4 | **Result Monad for Error Handling** | Eliminates is_retryable duplication | ~150 lines | Low |
| 5 | **CRUD Client Metaclass** | Auto-generates standard CRUD methods | ~500 lines | High |

**Total Estimated Savings**: ~2,550 lines of code

---

## Pattern Opportunity Catalog

### Opportunity 1: Async/Sync Method Generator Decorator

**Current State: Massive Duplication**

Every client method requires 3-4 implementations:
1. Async implementation with `@overload` for `raw=True/False`
2. Sync wrapper calling `_method_sync`
3. Internal `_method_sync` decorated with `@sync_wrapper`

Example from `SectionsClient.get`:

```python
# Current: 48 lines for ONE method

@overload
async def get_async(
    self, section_gid: str, *, raw: Literal[False] = ..., opt_fields: list[str] | None = ...,
) -> Section: ...

@overload
async def get_async(
    self, section_gid: str, *, raw: Literal[True], opt_fields: list[str] | None = ...,
) -> dict[str, Any]: ...

@error_handler
async def get_async(
    self, section_gid: str, *, raw: bool = False, opt_fields: list[str] | None = None,
) -> Section | dict[str, Any]:
    params = self._build_opt_fields(opt_fields)
    data = await self._http.get(f"/sections/{section_gid}", params=params)
    if raw:
        return data
    return Section.model_validate(data)

@overload
def get(
    self, section_gid: str, *, raw: Literal[False] = ..., opt_fields: list[str] | None = ...,
) -> Section: ...

@overload
def get(
    self, section_gid: str, *, raw: Literal[True], opt_fields: list[str] | None = ...,
) -> dict[str, Any]: ...

def get(
    self, section_gid: str, *, raw: bool = False, opt_fields: list[str] | None = None,
) -> Section | dict[str, Any]:
    return self._get_sync(section_gid, raw=raw, opt_fields=opt_fields)

@sync_wrapper("get_async")
async def _get_sync(
    self, section_gid: str, *, raw: bool = False, opt_fields: list[str] | None = None,
) -> Section | dict[str, Any]:
    if raw:
        return await self.get_async(section_gid, raw=True, opt_fields=opt_fields)
    return await self.get_async(section_gid, raw=False, opt_fields=opt_fields)
```

**Proposed Pattern: Method Generator Decorator**

```python
# After: 12 lines for the same functionality

from autom8_asana.patterns import async_method, ModelType

class SectionsClient(BaseClient):

    @async_method(
        model=Section,
        endpoint="/sections/{section_gid}",
        http_method="GET",
    )
    async def get(
        self,
        section_gid: str,
        *,
        opt_fields: list[str] | None = None,
    ) -> Section:
        """Get a section by GID."""
        ...
```

**Implementation Approach**:

```python
# src/autom8_asana/patterns/method_generator.py

from __future__ import annotations
import functools
import inspect
from typing import Any, Callable, TypeVar, Generic, Literal, overload, get_type_hints

T = TypeVar("T")

class async_method(Generic[T]):
    """Decorator that generates async/sync method pairs with raw overloads.

    Generates:
    - method_async() with @overload for raw=True/False
    - method() sync wrapper
    - Proper type hints for IDE support

    Example:
        @async_method(model=Section, endpoint="/sections/{gid}", http_method="GET")
        async def get(self, gid: str) -> Section: ...

        # Generates: get_async(), get(), with full type overloads
    """

    def __init__(
        self,
        *,
        model: type[T],
        endpoint: str,
        http_method: Literal["GET", "POST", "PUT", "DELETE"],
        error_handler: bool = True,
    ):
        self.model = model
        self.endpoint = endpoint
        self.http_method = http_method
        self.error_handler = error_handler

    def __call__(self, func: Callable[..., T]) -> AsyncSyncMethodPair[T]:
        """Transform decorated method into async/sync pair."""
        return AsyncSyncMethodPair(
            func=func,
            model=self.model,
            endpoint=self.endpoint,
            http_method=self.http_method,
            error_handler=self.error_handler,
        )


class AsyncSyncMethodPair(Generic[T]):
    """Descriptor that provides both async and sync method access."""

    def __init__(
        self,
        func: Callable[..., T],
        model: type[T],
        endpoint: str,
        http_method: str,
        error_handler: bool,
    ):
        self.func = func
        self.model = model
        self.endpoint = endpoint
        self.http_method = http_method
        self.error_handler = error_handler
        self.name = func.__name__

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name
        self.async_name = f"{name}_async"

    def __get__(self, obj: Any, objtype: type | None = None) -> SyncMethodWrapper[T]:
        if obj is None:
            return self  # type: ignore
        return SyncMethodWrapper(self, obj)


class SyncMethodWrapper(Generic[T]):
    """Provides sync method that wraps async implementation."""

    def __init__(self, pair: AsyncSyncMethodPair[T], instance: Any):
        self.pair = pair
        self.instance = instance

    @overload
    def __call__(self, *args: Any, raw: Literal[False] = ..., **kwargs: Any) -> T: ...

    @overload
    def __call__(self, *args: Any, raw: Literal[True], **kwargs: Any) -> dict[str, Any]: ...

    def __call__(self, *args: Any, raw: bool = False, **kwargs: Any) -> T | dict[str, Any]:
        """Execute sync version of the method."""
        from autom8_asana.transport.sync import run_sync
        return run_sync(self.async_impl(*args, raw=raw, **kwargs))

    async def async_impl(
        self, *args: Any, raw: bool = False, **kwargs: Any
    ) -> T | dict[str, Any]:
        """Execute async implementation."""
        # Build endpoint with path parameters
        sig = inspect.signature(self.pair.func)
        bound = sig.bind(self.instance, *args, **kwargs)
        bound.apply_defaults()

        endpoint = self.pair.endpoint.format(**bound.arguments)

        # Execute HTTP call
        http = self.instance._http
        match self.pair.http_method:
            case "GET":
                data = await http.get(endpoint, params=kwargs.get("params", {}))
            case "POST":
                data = await http.post(endpoint, json=kwargs.get("json", {}))
            case "PUT":
                data = await http.put(endpoint, json=kwargs.get("json", {}))
            case "DELETE":
                await http.delete(endpoint)
                return None  # type: ignore

        if raw:
            return data
        return self.pair.model.model_validate(data)
```

**Expected Benefits**:
- **Lines Saved**: ~1,200 lines across all clients (Tasks, Sections, Tags, Projects)
- **Bugs Prevented**: Eliminates copy-paste errors in method signatures
- **Type Safety**: Single source of truth for type hints
- **Maintainability**: Change method generation once, affects all clients

**Implementation Complexity**: Medium
- Requires careful handling of `@overload` generation
- Must preserve IDE autocomplete (may need `.pyi` stubs)
- Testing decorator behavior across all method types

---

### Opportunity 2: Custom Field Property Descriptor

**Current State: Repetitive Property Boilerplate**

Every business model has 15-20 custom field properties with identical patterns:

```python
# Current: Business model has 19 fields, each with ~10 lines of boilerplate

class Business(BusinessEntity):

    class Fields:
        COMPANY_ID = "Company ID"
        OFFICE_PHONE = "Office Phone"
        # ... 17 more constants

    def _get_text_field(self, field_name: str) -> str | None:
        value = self.get_custom_fields().get(field_name)
        if value is None or isinstance(value, str):
            return value
        return str(value)

    def _get_enum_field(self, field_name: str) -> str | None:
        value = self.get_custom_fields().get(field_name)
        if isinstance(value, dict):
            name = value.get("name")
            return str(name) if name is not None else None
        # ... more handling

    @property
    def company_id(self) -> str | None:
        return self._get_text_field(self.Fields.COMPANY_ID)

    @company_id.setter
    def company_id(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.COMPANY_ID, value)

    @property
    def office_phone(self) -> str | None:
        return self._get_text_field(self.Fields.OFFICE_PHONE)

    @office_phone.setter
    def office_phone(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.OFFICE_PHONE, value)

    # ... 17 more property pairs
```

**Proposed Pattern: Custom Field Descriptor**

```python
# After: 2 lines per field

from autom8_asana.patterns import TextField, EnumField, NumberField, PeopleField

class Business(BusinessEntity):

    # Text fields - 1 line each!
    company_id = TextField("Company ID")
    office_phone = TextField("Office Phone")
    facebook_page_id = TextField("Facebook Page ID")
    google_cal_id = TextField("Google Cal ID")
    owner_name = TextField("Owner Name")
    stripe_id = TextField("Stripe ID")
    # ... etc

    # Enum fields
    vertical = EnumField("Vertical")
    booking_type = EnumField("Booking Type")
    vca_status = EnumField("VCA Status")

    # Number fields
    num_reviews = NumberField("Num Reviews")

    # People fields
    rep = PeopleField("Rep")
```

**Implementation**:

```python
# src/autom8_asana/patterns/custom_field_descriptors.py

from __future__ import annotations
from typing import Any, Generic, TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.models.base import AsanaResource

T = TypeVar("T")


class CustomFieldDescriptor(Generic[T]):
    """Base descriptor for custom field access.

    Works with Pydantic models by accessing get_custom_fields() method.
    Supports IDE autocomplete and type checking.
    """

    def __init__(self, field_name: str, *, doc: str | None = None):
        self.field_name = field_name
        self.__doc__ = doc or f"Custom field: {field_name}"

    def __set_name__(self, owner: type, name: str) -> None:
        self.attr_name = name

        # Auto-generate Fields class constant if not exists
        if not hasattr(owner, "Fields"):
            owner.Fields = type("Fields", (), {})
        setattr(owner.Fields, name.upper(), self.field_name)

    def _get_accessor(self, obj: AsanaResource) -> Any:
        """Get the custom field accessor from the model."""
        return obj.get_custom_fields()

    def __get__(self, obj: AsanaResource | None, objtype: type | None = None) -> T | None:
        if obj is None:
            return self  # type: ignore
        return self._convert_get(self._get_accessor(obj).get(self.field_name))

    def __set__(self, obj: AsanaResource, value: T | None) -> None:
        self._get_accessor(obj).set(self.field_name, self._convert_set(value))

    def _convert_get(self, value: Any) -> T | None:
        """Override to convert API value to Python type."""
        return value

    def _convert_set(self, value: T | None) -> Any:
        """Override to convert Python value to API format."""
        return value


class TextField(CustomFieldDescriptor[str]):
    """Descriptor for text custom fields."""

    def _convert_get(self, value: Any) -> str | None:
        if value is None:
            return None
        return str(value)


class EnumField(CustomFieldDescriptor[str]):
    """Descriptor for enum custom fields.

    Handles Asana's enum format: {"gid": "...", "name": "Value"}
    """

    def _convert_get(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, dict):
            name = value.get("name")
            return str(name) if name is not None else None
        return str(value)

    def _convert_set(self, value: str | None) -> str | None:
        # Asana API accepts enum name directly for setting
        return value


class NumberField(CustomFieldDescriptor[int | float]):
    """Descriptor for number custom fields."""

    def __init__(
        self,
        field_name: str,
        *,
        as_int: bool = True,
        doc: str | None = None,
    ):
        super().__init__(field_name, doc=doc)
        self.as_int = as_int

    def _convert_get(self, value: Any) -> int | float | None:
        if value is None:
            return None
        return int(value) if self.as_int else float(value)


class PeopleField(CustomFieldDescriptor[list[dict[str, Any]]]):
    """Descriptor for people/user custom fields.

    Returns list of user dicts: [{"gid": "...", "name": "..."}]
    """

    def _convert_get(self, value: Any) -> list[dict[str, Any]]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return []


class DateField(CustomFieldDescriptor[str]):
    """Descriptor for date custom fields.

    Returns ISO date string (YYYY-MM-DD).
    Can be extended to return datetime objects.
    """

    def _convert_get(self, value: Any) -> str | None:
        if value is None:
            return None
        # Asana returns {"date": "YYYY-MM-DD"} or just "YYYY-MM-DD"
        if isinstance(value, dict):
            return value.get("date")
        return str(value)
```

**Pydantic Compatibility Note**:

Per ADR-0077 (Pydantic Descriptor Compatibility), descriptors declared WITHOUT type annotations avoid Pydantic treating them as model fields:

```python
class Business(BusinessEntity):
    # CORRECT: No type annotation, Pydantic ignores
    company_id = TextField("Company ID")

    # WRONG: Type annotation causes Pydantic to treat as field
    company_id: str = TextField("Company ID")  # Don't do this!
```

**Expected Benefits**:
- **Lines Saved**: ~400 lines across Business, Contact, Unit, Offer, Process models
- **Type Safety**: Descriptors return proper types, IDE knows `company_id` is `str | None`
- **Consistency**: All custom fields behave identically
- **Auto-documentation**: `Fields` class generated automatically

**Implementation Complexity**: Low
- Descriptors are simple, well-understood Python pattern
- Already proven with Navigation Descriptors
- No metaclass magic needed

---

### Opportunity 3: Holder Factory with `__init_subclass__`

**Current State: Copy-Paste Holder Implementations**

Each holder class has near-identical structure with only child type differing:

```python
# Current: DNAHolder, ReconciliationHolder, VideographyHolder, AssetEditHolder
# are all virtually identical

class DNAHolder(Task, HolderMixin[Task]):
    CHILD_TYPE: ClassVar[type[Task]] = Task  # Will be DNA at runtime
    PARENT_REF_NAME: ClassVar[str] = "_dna_holder"
    CHILDREN_ATTR: ClassVar[str] = "_children"

    _children: list[Any] = PrivateAttr(default_factory=list)
    _business: Business | None = PrivateAttr(default=None)

    @property
    def children(self) -> list[Any]:
        return self._children

    @property
    def business(self) -> Business | None:
        return self._business

    def _populate_children(self, subtasks: list[Task]) -> None:
        from autom8_asana.models.business.dna import DNA as DNAClass
        self.__class__.CHILD_TYPE = DNAClass
        sorted_tasks = sorted(subtasks, key=lambda t: (t.created_at or "", t.name or ""))
        self._children = []
        for task in sorted_tasks:
            child = DNAClass.model_validate(task.model_dump())
            child._dna_holder = self
            child._business = self._business
            self._children.append(child)

# ReconciliationHolder is EXACTLY THE SAME except:
# - PARENT_REF_NAME = "_reconciliation_holder"
# - Imports Reconciliation instead of DNA
# - Sets child._reconciliation_holder instead of child._dna_holder
```

**Proposed Pattern: Holder Factory with `__init_subclass__`**

```python
# After: 3 lines per holder!

class DNAHolder(HolderBase, child_type="DNA", parent_ref="_dna_holder"):
    """Holder for DNA children."""
    pass


class ReconciliationHolder(HolderBase, child_type="Reconciliation", parent_ref="_reconciliation_holder"):
    """Holder for Reconciliation children."""

    @property
    def reconciliations(self) -> list[Any]:
        """Alias for children with semantic name."""
        return self.children
```

**Implementation**:

```python
# src/autom8_asana/models/business/holder_base.py

from __future__ import annotations
from typing import Any, ClassVar, TYPE_CHECKING
from pydantic import PrivateAttr
from autom8_asana.models.task import Task

if TYPE_CHECKING:
    from autom8_asana.models.business.business import Business


class HolderBase(Task):
    """Base class for holder tasks using __init_subclass__ pattern.

    Automatically configures holder behavior based on class parameters.

    Usage:
        class DNAHolder(HolderBase, child_type="DNA", parent_ref="_dna_holder"):
            pass

    This generates:
    - CHILD_TYPE, PARENT_REF_NAME, CHILDREN_ATTR class vars
    - _children PrivateAttr
    - _business PrivateAttr
    - children property
    - business property
    - _populate_children method
    """

    # These will be set by __init_subclass__
    CHILD_TYPE: ClassVar[type[Task]]
    PARENT_REF_NAME: ClassVar[str]
    CHILDREN_ATTR: ClassVar[str] = "_children"
    _CHILD_MODULE: ClassVar[str]  # e.g., "autom8_asana.models.business.dna"
    _CHILD_CLASS_NAME: ClassVar[str]  # e.g., "DNA"

    # Storage
    _children: list[Any] = PrivateAttr(default_factory=list)
    _business: Business | None = PrivateAttr(default=None)

    def __init_subclass__(
        cls,
        *,
        child_type: str | None = None,
        parent_ref: str | None = None,
        children_attr: str = "_children",
        **kwargs: Any,
    ) -> None:
        """Configure holder subclass automatically.

        Args:
            child_type: Name of child class (e.g., "DNA", "Reconciliation")
            parent_ref: Name of parent reference attribute (e.g., "_dna_holder")
            children_attr: Name of children storage attribute
        """
        super().__init_subclass__(**kwargs)

        if child_type is not None:
            cls._CHILD_CLASS_NAME = child_type
            # Infer module from class name pattern
            module_name = child_type.lower()
            cls._CHILD_MODULE = f"autom8_asana.models.business.{module_name}"
            cls.PARENT_REF_NAME = parent_ref or f"_{module_name}_holder"
            cls.CHILDREN_ATTR = children_attr

            # Initially set CHILD_TYPE to Task (will be resolved at runtime)
            cls.CHILD_TYPE = Task

    @property
    def children(self) -> list[Any]:
        """All child entities.

        Returns:
            List of typed child entities.
        """
        return getattr(self, self.CHILDREN_ATTR)

    @property
    def business(self) -> Business | None:
        """Navigate to parent Business.

        Returns:
            Business entity or None if not populated.
        """
        return self._business

    def _populate_children(self, subtasks: list[Task]) -> None:
        """Populate children from fetched subtasks.

        Dynamically imports child class to avoid circular imports,
        converts Task instances to typed children, and sets bidirectional refs.

        Args:
            subtasks: List of Task subtasks from API.
        """
        import importlib

        # Dynamically import child class
        module = importlib.import_module(self._CHILD_MODULE)
        child_class = getattr(module, self._CHILD_CLASS_NAME)

        # Update CHILD_TYPE for this instance
        self.__class__.CHILD_TYPE = child_class

        # Sort and convert
        sorted_tasks = sorted(
            subtasks,
            key=lambda t: (t.created_at or "", t.name or ""),
        )

        children = []
        for task in sorted_tasks:
            child = child_class.model_validate(task.model_dump())
            # Set bidirectional reference
            setattr(child, self.PARENT_REF_NAME, self)
            child._business = self._business
            children.append(child)

        setattr(self, self.CHILDREN_ATTR, children)
```

**Expected Benefits**:
- **Lines Saved**: ~300 lines across 4 stub holders + potential future holders
- **Consistency**: All holders behave identically
- **Extensibility**: New holders require only 3 lines
- **Bug Prevention**: No chance of forgetting to set a reference

**Implementation Complexity**: Medium
- `__init_subclass__` is less common but well-documented
- Dynamic imports require careful module path handling
- Testing needs to cover class creation edge cases

---

### Opportunity 4: Result Monad for Error Classification

**Current State: Duplicated is_retryable Logic**

`SaveError` and `ActionResult` have nearly identical error classification code:

```python
# SaveError.is_retryable - 30 lines
@property
def is_retryable(self) -> bool:
    if isinstance(self.error, (TimeoutError, ConnectionError, OSError)):
        return True
    status_code = self._extract_status_code()
    if status_code is None:
        return False
    if status_code == 429:
        return True
    if 500 <= status_code < 600:
        return True
    return False

@property
def recovery_hint(self) -> str:
    if isinstance(self.error, TimeoutError):
        return "Request timed out. Retry with exponential backoff."
    # ... 40 more lines of identical logic

# ActionResult.is_retryable - EXACT SAME 30 lines!
@property
def is_retryable(self) -> bool:
    if self.success or self.error is None:
        return False
    if isinstance(self.error, (TimeoutError, ConnectionError, OSError)):
        return True
    # ... identical logic

@property
def recovery_hint(self) -> str:
    # ... same 40 lines again
```

**Proposed Pattern: ErrorClassification Protocol + Mixin**

```python
# After: Shared behavior, single source of truth

from autom8_asana.patterns import RetryableErrorMixin

@dataclass
class SaveError(RetryableErrorMixin):
    """Error information for a failed operation."""
    entity: AsanaResource
    operation: OperationType
    error: Exception
    payload: dict[str, Any]

    def _get_error(self) -> Exception | None:
        return self.error


@dataclass
class ActionResult(RetryableErrorMixin):
    """Result of an action operation."""
    action: ActionOperation
    success: bool
    error: Exception | None = None
    response_data: dict[str, Any] | None = None

    def _get_error(self) -> Exception | None:
        return None if self.success else self.error
```

**Implementation**:

```python
# src/autom8_asana/patterns/error_classification.py

from __future__ import annotations
from abc import abstractmethod
from typing import Protocol, runtime_checkable


@runtime_checkable
class HasError(Protocol):
    """Protocol for types that may contain an error."""

    @abstractmethod
    def _get_error(self) -> Exception | None:
        """Return the error if present, None otherwise."""
        ...


class RetryableErrorMixin:
    """Mixin providing error classification and recovery hints.

    Classes using this mixin must implement _get_error().

    Provides:
    - is_retryable: Whether the error can be retried
    - recovery_hint: Human-readable recovery guidance
    - retry_after_seconds: Delay before retry (for rate limits)
    """

    @abstractmethod
    def _get_error(self) -> Exception | None:
        """Return the error if present."""
        ...

    @property
    def is_retryable(self) -> bool:
        """Determine if this error is potentially retryable.

        Classification:
        - Network errors (Timeout, Connection, OS): Retryable
        - 429 Rate Limit: Retryable
        - 5xx Server Errors: Retryable
        - 4xx Client Errors: Not retryable
        """
        error = self._get_error()
        if error is None:
            return False

        # Network errors
        if isinstance(error, (TimeoutError, ConnectionError, OSError)):
            return True

        status_code = self._extract_status_code(error)
        if status_code is None:
            return False

        return status_code == 429 or 500 <= status_code < 600

    @property
    def recovery_hint(self) -> str:
        """Provide guidance for recovering from this error."""
        error = self._get_error()
        if error is None:
            return ""

        # Network error hints
        network_hints = {
            TimeoutError: "Request timed out. Retry with exponential backoff.",
            ConnectionError: "Connection failed. Check network connectivity and retry.",
            OSError: "Network error. Check connectivity and retry.",
        }
        for error_type, hint in network_hints.items():
            if isinstance(error, error_type):
                return hint

        # HTTP status hints
        status_code = self._extract_status_code(error)
        if status_code is None:
            return "Unknown error. Inspect the error attribute for details."

        status_hints = {
            400: "Bad request. Check payload format and required fields.",
            401: "Authentication failed. Verify API credentials.",
            403: "Permission denied. Check access permissions.",
            404: "Resource not found. Verify the GID exists.",
            409: "Conflict detected. Resource may have been modified.",
            429: "Rate limit exceeded. Wait for retry_after_seconds and retry.",
            500: "Server error. Retry with exponential backoff.",
            502: "Bad gateway. Retry with exponential backoff.",
            503: "Service unavailable. Retry with exponential backoff.",
            504: "Gateway timeout. Retry with exponential backoff.",
        }

        if status_code in status_hints:
            return status_hints[status_code]

        if 400 <= status_code < 500:
            return f"Client error ({status_code}). Check request parameters."
        if 500 <= status_code < 600:
            return f"Server error ({status_code}). Retry with exponential backoff."

        return f"HTTP {status_code}. Inspect the error attribute for details."

    @property
    def retry_after_seconds(self) -> int | None:
        """Get recommended wait time before retry."""
        error = self._get_error()
        if error is None:
            return None
        return getattr(error, 'retry_after', None)

    @staticmethod
    def _extract_status_code(error: Exception) -> int | None:
        """Extract HTTP status code from error."""
        from autom8_asana.exceptions import AsanaError

        if isinstance(error, AsanaError):
            return error.status_code

        status = getattr(error, 'status_code', None)
        return status if isinstance(status, int) else None
```

**Expected Benefits**:
- **Lines Saved**: ~150 lines (eliminating duplication)
- **Single Source of Truth**: Update error hints once, affects all result types
- **Testability**: Test error classification once
- **Extensibility**: New result types get retry logic for free

**Implementation Complexity**: Low
- Standard mixin pattern, no magic
- Clear protocol for implementers
- Easy to test in isolation

---

### Opportunity 5: CRUD Client Metaclass

**Current State: Every Client Repeats CRUD Pattern**

`TasksClient`, `SectionsClient`, `TagsClient`, `ProjectsClient` all have:
- `get_async` / `get` pair
- `create_async` / `create` pair
- `update_async` / `update` pair
- `delete_async` / `delete` pair
- List methods with pagination

The structure is identical; only endpoints and models differ.

**Proposed Pattern: CRUD Metaclass / Base with Registration**

```python
# After: Configuration-driven client definition

from autom8_asana.patterns import CRUDClient, crud_endpoint

class SectionsClient(CRUDClient[Section]):
    """Client for Asana Section operations."""

    model = Section
    resource_name = "sections"

    # Standard CRUD auto-generated: get, create, update, delete

    # Custom endpoints declared explicitly
    @crud_endpoint(method="POST", path="/sections/{section_gid}/addTask")
    async def add_task(
        self,
        section_gid: str,
        *,
        task: str,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> None:
        """Add a task to a section."""
        ...
```

**Implementation Sketch**:

```python
# src/autom8_asana/patterns/crud_client.py

from __future__ import annotations
from typing import Generic, TypeVar, ClassVar, Any

T = TypeVar("T")


class CRUDClientMeta(type):
    """Metaclass that generates CRUD methods for client classes.

    Inspects class for `model` and `resource_name` attributes,
    then generates get/create/update/delete method pairs.
    """

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> type:
        cls = super().__new__(mcs, name, bases, namespace)

        # Skip base class
        if name == "CRUDClient":
            return cls

        # Get configuration
        model = getattr(cls, "model", None)
        resource_name = getattr(cls, "resource_name", None)

        if model is None or resource_name is None:
            return cls

        # Generate CRUD methods
        mcs._add_get_methods(cls, model, resource_name)
        mcs._add_create_methods(cls, model, resource_name)
        mcs._add_update_methods(cls, model, resource_name)
        mcs._add_delete_methods(cls, model, resource_name)
        mcs._add_list_method(cls, model, resource_name)

        return cls

    @staticmethod
    def _add_get_methods(cls: type, model: type, resource_name: str) -> None:
        """Generate get_async and get methods."""

        async def get_async(
            self,
            gid: str,
            *,
            raw: bool = False,
            opt_fields: list[str] | None = None,
        ):
            params = self._build_opt_fields(opt_fields)
            data = await self._http.get(f"/{resource_name}/{gid}", params=params)
            if raw:
                return data
            return model.model_validate(data)

        def get(self, gid: str, *, raw: bool = False, opt_fields: list[str] | None = None):
            return self._run_sync(get_async, self, gid, raw=raw, opt_fields=opt_fields)

        get_async.__doc__ = f"Get a {resource_name[:-1]} by GID."
        get.__doc__ = f"Get a {resource_name[:-1]} by GID (sync)."

        setattr(cls, "get_async", get_async)
        setattr(cls, "get", get)

    # Similar for create, update, delete, list...


class CRUDClient(Generic[T], metaclass=CRUDClientMeta):
    """Base class for CRUD-enabled clients.

    Subclasses should define:
    - model: The Pydantic model class for this resource
    - resource_name: The API resource path (e.g., "sections", "tasks")

    Standard CRUD methods are auto-generated:
    - get_async / get
    - create_async / create
    - update_async / update
    - delete_async / delete
    - list_async (returns PageIterator)
    """

    model: ClassVar[type[T]]
    resource_name: ClassVar[str]
```

**Expected Benefits**:
- **Lines Saved**: ~500+ lines across all CRUD clients
- **Consistency**: All clients behave identically
- **Extensibility**: New resource clients require minimal code
- **Type Safety**: Generic typing preserved

**Implementation Complexity**: High
- Metaclasses are powerful but complex
- Must handle `@overload` for IDE support
- Testing metaclass behavior is tricky
- May need runtime type generation

**Recommendation**: Consider implementing Opportunity 1 (decorator approach) first, as it's simpler and provides similar benefits.

---

## Additional Opportunities (Lower Priority)

### Opportunity 6: Context Manager for SaveSession

**Current Pattern**:
```python
session = SaveSession(client)
session.track(task)
try:
    result = await session.commit()
except Exception:
    # Manual cleanup
    raise
```

**Proposed Pattern**:
```python
async with SaveSession(client) as session:
    session.track(task)
    result = await session.commit()
    # Auto-cleanup on exception
```

**Implementation Complexity**: Low
**Lines Saved**: ~50 (error handling boilerplate)

---

### Opportunity 7: Flyweight for Custom Field Metadata

**Problem**: Each `CustomFieldAccessor` instance stores field metadata that could be shared.

**Proposed**: Flyweight pattern with class-level metadata cache.

**Implementation Complexity**: Medium
**Memory Saved**: ~40% reduction in custom field overhead

---

### Opportunity 8: Chain of Responsibility for API Response Processing

**Problem**: Response processing (unwrap data, validate, model convert) is scattered.

**Proposed**: Pipeline pattern for composable response processors.

**Implementation Complexity**: Medium
**Benefit**: Easier to add new processing steps (logging, metrics, caching)

---

## Prioritized Implementation Roadmap

### Phase 1: Quick Wins (1-2 days each)

1. **Custom Field Property Descriptor** (Opportunity 2)
   - Lowest risk, highest familiarity (similar to Navigation Descriptors)
   - Immediate 400+ line reduction
   - Can be done incrementally per model

2. **Result Monad / Error Mixin** (Opportunity 4)
   - Simple mixin, no magic
   - Fixes obvious duplication
   - Easy to test

### Phase 2: Medium Lift (3-5 days each)

3. **Holder Factory with `__init_subclass__`** (Opportunity 3)
   - Moderate complexity
   - Prepares for future holder types
   - Reduces holder boilerplate by 80%

4. **Async/Sync Method Generator** (Opportunity 1)
   - Highest impact (1200+ lines)
   - Requires careful IDE compatibility testing
   - May need `.pyi` stub generation

### Phase 3: Major Refactor (1+ week)

5. **CRUD Client Metaclass** (Opportunity 5)
   - Highest complexity
   - Greatest long-term benefit
   - Consider after patterns 1-4 are stable

---

## Risks and Considerations

### Technical Risks

| Risk | Mitigation |
|------|------------|
| **IDE Support Degradation** | Generate `.pyi` stubs; test with VSCode, PyCharm |
| **Runtime Performance** | Profile descriptor `__get__` calls; consider caching |
| **Debugging Difficulty** | Add clear `__repr__` to all descriptors; comprehensive logging |
| **Pydantic Compatibility** | Follow ADR-0077 patterns; avoid type annotations on descriptors |

### Process Risks

| Risk | Mitigation |
|------|------------|
| **Migration Complexity** | Implement incrementally; maintain backward compatibility |
| **Test Coverage Gaps** | Write pattern tests first; ensure 100% coverage |
| **Documentation Lag** | Update docs with each pattern; create pattern guide |

### When NOT to Use These Patterns

1. **One-off methods**: If a method is unique, don't force it into a pattern
2. **Simple cases**: Don't add abstraction for 2-3 similar lines
3. **Unclear requirements**: Wait until pattern is proven before abstracting
4. **External constraints**: If Asana API changes frequently, flexibility > abstraction

---

## Success Metrics

### Quantitative

| Metric | Target | Measurement |
|--------|--------|-------------|
| Lines of Code Reduced | 2,000+ | `wc -l` before/after |
| Test Coverage | >95% | `pytest --cov` |
| Type Check Pass | 100% | `mypy --strict` |
| Cyclomatic Complexity | <10 per method | `radon cc` |

### Qualitative

- New developers can understand patterns in <30 minutes
- Adding new resource type requires <50 lines
- IDE autocomplete works for all generated methods
- Error messages remain clear and actionable

---

## Conclusion

The Navigation Descriptor Pattern proved that well-designed Python patterns can dramatically reduce code while improving safety. This analysis identifies five additional opportunities with similar potential.

**Recommended Next Steps**:

1. Start with **Custom Field Property Descriptor** (Opportunity 2) - low risk, proven pattern
2. Follow with **Error Classification Mixin** (Opportunity 4) - quick win
3. Then tackle **Async/Sync Generator** (Opportunity 1) for maximum impact

Each pattern should be implemented as a standalone initiative with its own PRD, TDD, and test plan following the established 10x workflow.

---

*Document generated by Architect agent as part of design pattern analysis.*
