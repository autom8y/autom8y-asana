# TDD-DESIGN-PATTERNS-E: CRUD Client Base Class

| Field | Value |
|-------|-------|
| **ID** | TDD-DESIGN-PATTERNS-E |
| **Title** | CRUD Client Base Class |
| **Status** | Active |
| **PRD** | PRD-DESIGN-PATTERNS-E |
| **Created** | 2025-12-16 |

---

## 1. Overview

This document specifies the technical design for a generic CRUD client base class that reduces boilerplate in resource-specific clients while preserving full type safety.

### 1.1 Design Goals

1. **Reusable implementations** - Common CRUD logic in base class
2. **Full type safety** - mypy compliance, IDE autocomplete
3. **Minimal configuration** - Simple dataclass for resource config
4. **Composable with @async_method** - Leverages Initiative D's pattern

### 1.2 Key Insight: Why Not Metaclass?

The original meta-initiative proposed a metaclass approach. Discovery revealed:

1. **Type overloads cannot be runtime-generated** for static type checkers
2. **Create signatures vary too much** to templatize
3. **@async_method already handles 65%** of the duplication
4. **Metaclass complexity is HIGH** for marginal gain

The base class approach provides similar benefit with lower complexity and better maintainability.

---

## 2. Architecture

### 2.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     CRUDClient[T] Base                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Configuration:                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  @dataclass                                               │  │
│  │  class CRUDConfig:                                        │  │
│  │      resource_name: str        # "section"                │  │
│  │      endpoint: str             # "/sections"              │  │
│  │      model_class: type[T]      # Section                  │  │
│  │      gid_param: str           # "section_gid"             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Template Methods (use @async_method):                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  _crud_get()      -> T | dict  (template)                 │  │
│  │  _crud_update()   -> T | dict  (template)                 │  │
│  │  _crud_delete()   -> None      (template)                 │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Subclass provides:                                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  - Type overload declarations (required for mypy)         │  │
│  │  - create() implementation (varies per resource)          │  │
│  │  - Custom methods (add_task, add_members, etc.)           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Inheritance Hierarchy

```
BaseClient
    │
    ├── CRUDClient[T]           # New generic base
    │       │
    │       ├── SectionsClient(CRUDClient[Section])
    │       ├── TagsClient(CRUDClient[Tag])
    │       ├── ProjectsClient(CRUDClient[Project])
    │       └── ...
    │
    └── Non-CRUD Clients        # Remain as BaseClient subclasses
            ├── WorkspacesClient (get/list only)
            └── ...
```

---

## 3. Detailed Design

### 3.1 CRUDConfig Dataclass

```python
# src/autom8_asana/patterns/crud.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class CRUDConfig(Generic[T]):
    """Configuration for CRUD operations on a resource.

    Attributes:
        resource_name: Singular resource name (e.g., "section")
        endpoint: Base API endpoint (e.g., "/sections")
        model_class: Pydantic model class for this resource
        gid_param: Name of the GID parameter (e.g., "section_gid")
    """
    resource_name: str
    endpoint: str
    model_class: type[T]
    gid_param: str = ""  # Defaults to "{resource_name}_gid"

    def __post_init__(self) -> None:
        # Set default gid_param if not provided
        if not self.gid_param:
            object.__setattr__(self, "gid_param", f"{self.resource_name}_gid")
```

### 3.2 CRUDClient Base Class

```python
# src/autom8_asana/patterns/crud.py (continued)

from typing import Any, TYPE_CHECKING

from autom8_asana.clients.base import BaseClient
from autom8_asana.observability import error_handler
from autom8_asana.patterns.async_method import async_method

if TYPE_CHECKING:
    from autom8_asana.config import AsanaConfig
    from autom8_asana.protocols.auth import AuthProvider
    from autom8_asana.protocols.cache import CacheProvider
    from autom8_asana.protocols.log import LogProvider
    from autom8_asana.transport.http import AsyncHTTPClient


class CRUDClient(BaseClient, Generic[T]):
    """Generic base class for resource clients with CRUD operations.

    Provides template implementations for get, update, and delete.
    Subclasses must:
    - Define `_crud_config` class attribute
    - Declare type overloads for get, update methods
    - Implement create() method (signatures vary per resource)

    Example:
        class SectionsClient(CRUDClient[Section]):
            _crud_config = CRUDConfig(
                resource_name="section",
                endpoint="/sections",
                model_class=Section,
            )

            # Type overloads (required for mypy)
            @overload
            async def get_async(self, section_gid: str, *, raw: Literal[False] = ...) -> Section: ...
            @overload
            async def get_async(self, section_gid: str, *, raw: Literal[True]) -> dict: ...
            # ... sync overloads ...

            # Implementation delegates to base
            @async_method
            @error_handler
            async def get(self, section_gid: str, *, raw: bool = False,
                          opt_fields: list[str] | None = None) -> Section | dict:
                return await self._crud_get(section_gid, raw=raw, opt_fields=opt_fields)
    """

    _crud_config: CRUDConfig[T]  # Subclass must define

    async def _crud_get(
        self,
        gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> T | dict[str, Any]:
        """Template implementation for get operation.

        Args:
            gid: Resource GID
            raw: If True, return raw dict
            opt_fields: Optional fields to include

        Returns:
            Model instance or raw dict based on `raw` parameter.
        """
        config = self._crud_config
        params = self._build_opt_fields(opt_fields)
        data = await self._http.get(f"{config.endpoint}/{gid}", params=params)
        if raw:
            return data
        return config.model_class.model_validate(data)

    async def _crud_update(
        self,
        gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> T | dict[str, Any]:
        """Template implementation for update operation.

        Args:
            gid: Resource GID
            raw: If True, return raw dict
            **kwargs: Fields to update

        Returns:
            Updated model instance or raw dict.
        """
        config = self._crud_config
        result = await self._http.put(
            f"{config.endpoint}/{gid}",
            json={"data": kwargs},
        )
        if raw:
            return result
        return config.model_class.model_validate(result)

    async def _crud_delete(self, gid: str) -> None:
        """Template implementation for delete operation.

        Args:
            gid: Resource GID
        """
        config = self._crud_config
        await self._http.delete(f"{config.endpoint}/{gid}")
```

### 3.3 SectionsClient Migration Pattern

```python
# src/autom8_asana/clients/sections.py (migrated)

from __future__ import annotations

from typing import Any, Literal, overload

from autom8_asana.models import PageIterator
from autom8_asana.models.section import Section
from autom8_asana.observability import error_handler
from autom8_asana.patterns import async_method
from autom8_asana.patterns.crud import CRUDClient, CRUDConfig


class SectionsClient(CRUDClient[Section]):
    """Client for Asana Section operations.

    Uses CRUDClient base for get, update, delete operations.
    Implements create() and custom methods (add_task, insert_section).
    """

    _crud_config = CRUDConfig(
        resource_name="section",
        endpoint="/sections",
        model_class=Section,
    )

    # --- GET: Type overloads + delegation ---

    @overload
    async def get_async(
        self, section_gid: str, *, raw: Literal[False] = ..., opt_fields: list[str] | None = ...
    ) -> Section: ...

    @overload
    async def get_async(
        self, section_gid: str, *, raw: Literal[True], opt_fields: list[str] | None = ...
    ) -> dict[str, Any]: ...

    @overload
    def get(
        self, section_gid: str, *, raw: Literal[False] = ..., opt_fields: list[str] | None = ...
    ) -> Section: ...

    @overload
    def get(
        self, section_gid: str, *, raw: Literal[True], opt_fields: list[str] | None = ...
    ) -> dict[str, Any]: ...

    @async_method
    @error_handler
    async def get(
        self, section_gid: str, *, raw: bool = False, opt_fields: list[str] | None = None
    ) -> Section | dict[str, Any]:
        """Get a section by GID."""
        return await self._crud_get(section_gid, raw=raw, opt_fields=opt_fields)

    # --- UPDATE: Type overloads + delegation ---

    @overload
    async def update_async(self, section_gid: str, *, raw: Literal[False] = ..., **kwargs: Any) -> Section: ...

    @overload
    async def update_async(self, section_gid: str, *, raw: Literal[True], **kwargs: Any) -> dict[str, Any]: ...

    @overload
    def update(self, section_gid: str, *, raw: Literal[False] = ..., **kwargs: Any) -> Section: ...

    @overload
    def update(self, section_gid: str, *, raw: Literal[True], **kwargs: Any) -> dict[str, Any]: ...

    @async_method
    @error_handler
    async def update(self, section_gid: str, *, raw: bool = False, **kwargs: Any) -> Section | dict[str, Any]:
        """Update a section (rename)."""
        return await self._crud_update(section_gid, raw=raw, **kwargs)

    # --- DELETE: Simpler (no raw parameter) ---

    @async_method
    @error_handler
    async def delete(self, section_gid: str) -> None:
        """Delete a section."""
        await self._crud_delete(section_gid)

    # --- CREATE: Resource-specific (not templated) ---

    @overload
    async def create_async(
        self, *, name: str, project: str, raw: Literal[False] = ...,
        insert_before: str | None = ..., insert_after: str | None = ...
    ) -> Section: ...

    @overload
    async def create_async(
        self, *, name: str, project: str, raw: Literal[True],
        insert_before: str | None = ..., insert_after: str | None = ...
    ) -> dict[str, Any]: ...

    @overload
    def create(
        self, *, name: str, project: str, raw: Literal[False] = ...,
        insert_before: str | None = ..., insert_after: str | None = ...
    ) -> Section: ...

    @overload
    def create(
        self, *, name: str, project: str, raw: Literal[True],
        insert_before: str | None = ..., insert_after: str | None = ...
    ) -> dict[str, Any]: ...

    @async_method
    @error_handler
    async def create(
        self, *, name: str, project: str, raw: bool = False,
        insert_before: str | None = None, insert_after: str | None = None
    ) -> Section | dict[str, Any]:
        """Create a new section in a project.

        Note: Create uses /projects/{project}/sections endpoint, not /sections.
        """
        data: dict[str, Any] = {"name": name}
        if insert_before is not None:
            data["insert_before"] = insert_before
        if insert_after is not None:
            data["insert_after"] = insert_after

        result = await self._http.post(f"/projects/{project}/sections", json={"data": data})
        if raw:
            return result
        return Section.model_validate(result)

    # --- LIST: Resource-specific ---

    def list_for_project_async(
        self, project_gid: str, *, opt_fields: list[str] | None = None, limit: int = 100
    ) -> PageIterator[Section]:
        """List sections in a project with automatic pagination."""
        self._log_operation("list_for_project_async", project_gid)

        async def fetch_page(offset: str | None) -> tuple[list[Section], str | None]:
            params = self._build_opt_fields(opt_fields)
            params["limit"] = min(limit, 100)
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                f"/projects/{project_gid}/sections", params=params
            )
            sections = [Section.model_validate(s) for s in data]
            return sections, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))

    # --- CUSTOM METHODS: Resource-specific ---

    @async_method
    @error_handler
    async def add_task(
        self, section_gid: str, *, task: str,
        insert_before: str | None = None, insert_after: str | None = None
    ) -> None:
        """Add a task to a section."""
        data: dict[str, Any] = {"task": task}
        if insert_before is not None:
            data["insert_before"] = insert_before
        if insert_after is not None:
            data["insert_after"] = insert_after

        await self._http.post(f"/sections/{section_gid}/addTask", json={"data": data})

    @async_method
    @error_handler
    async def insert_section(
        self, project_gid: str, *, section: str,
        before_section: str | None = None, after_section: str | None = None
    ) -> None:
        """Reorder a section within a project."""
        data: dict[str, Any] = {"section": section}
        if before_section is not None:
            data["before_section"] = before_section
        if after_section is not None:
            data["after_section"] = after_section

        await self._http.post(f"/projects/{project_gid}/sections/insert", json={"data": data})
```

---

## 4. Line Count Analysis

### 4.1 Current SectionsClient (with @async_method)

| Component | Lines |
|-----------|-------|
| Imports | 8 |
| Class docstring | 4 |
| get (overloads + impl) | 24 |
| create (overloads + impl) | 38 |
| update (overloads + impl) | 24 |
| delete (impl) | 6 |
| list_for_project | 21 |
| add_task | 15 |
| insert_section | 16 |
| **Total** | **~156 lines** |

### 4.2 Migrated SectionsClient (with CRUDClient)

| Component | Lines |
|-----------|-------|
| Imports | 9 |
| Class docstring + config | 10 |
| get (overloads + delegation) | 18 |
| create (overloads + impl) | 32 |
| update (overloads + delegation) | 14 |
| delete (delegation) | 5 |
| list_for_project | 21 |
| add_task | 15 |
| insert_section | 16 |
| **Total** | **~140 lines** |

### 4.3 Reduction Analysis

| Metric | Value |
|--------|-------|
| Lines in current SectionsClient | ~156 |
| Lines in migrated SectionsClient | ~140 |
| Lines in CRUDClient base + CRUDConfig | ~80 |
| **Net reduction for SectionsClient** | **~16 lines (10%)** |
| **Reduction if 4 clients migrate** | ~64 lines saved, 80 lines invested = **-16 lines (net loss)** |

### 4.4 Key Finding

**The CRUDClient base class does NOT provide significant value.**

The math shows:
- Per-client savings: ~16 lines (~10%)
- Base class investment: ~80 lines
- **Break-even point: 5+ clients** migrated
- But type overloads cannot be eliminated (mypy requirement)
- So the "savings" is mostly shuffling code to a base class

---

## 5. Alternative: Protocol-Based Mixin

Instead of inheritance, consider a **protocol-based mixin** that provides helper methods without requiring class hierarchy changes:

```python
class CRUDMixin(Protocol[T]):
    """Mixin providing CRUD helper methods."""

    _http: AsyncHTTPClient
    _crud_endpoint: str
    _crud_model: type[T]

    async def _fetch_resource(self, gid: str, opt_fields: list[str] | None = None) -> dict[str, Any]:
        """Fetch raw resource data."""
        params = {"opt_fields": ",".join(opt_fields)} if opt_fields else {}
        return await self._http.get(f"{self._crud_endpoint}/{gid}", params=params)

    def _validate_resource(self, data: dict[str, Any]) -> T:
        """Validate and return model."""
        return self._crud_model.model_validate(data)
```

This provides less abstraction but more flexibility.

---

## 6. Go/No-Go Evaluation

### 6.1 Recommendation: NO-GO for Full Implementation

The discovery and analysis reveals:

| Factor | Assessment |
|--------|------------|
| Code reduction | Minimal (~10% per client) |
| Type safety preservation | High complexity (overloads still required) |
| Maintenance burden | Increases (another abstraction layer) |
| Break-even point | 5+ clients (we have ~6 total) |
| Risk vs reward | High complexity, low value |

### 6.2 Why the Original Meta-Initiative Was Over-Optimistic

The meta-initiative estimated ~500+ lines savings with a metaclass. This was based on:
1. Assuming type overloads could be eliminated (they cannot)
2. Assuming create methods could be templated (they cannot)
3. Not accounting for @async_method already solving 65% of duplication

**Reality**: @async_method from Initiative D already captured the major win. Further abstraction yields diminishing returns.

### 6.3 Alternative Recommendation

Instead of CRUDClient, recommend:
1. **Document the pattern** as a template in code conventions
2. **Use @async_method consistently** across all clients
3. **Keep clients as independent units** - easier to understand and maintain
4. **Extract truly common helpers** to BaseClient if useful

---

## 7. ADR: CRUD Client Base Class Evaluation

### Decision

**DO NOT implement CRUDClient base class** for the following reasons:

1. **@async_method already captured major value** (~65% reduction)
2. **Type overloads cannot be eliminated** - fundamental Python limitation
3. **Create methods vary too much** - cannot be templated
4. **Net benefit is negative** when accounting for base class complexity
5. **Maintenance burden increases** with another abstraction layer

### Alternatives Considered

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| Metaclass | Maximum abstraction | Type safety broken, high complexity | Rejected |
| Generic base class | Moderate abstraction | Minimal savings, overloads still needed | Rejected |
| Protocol mixin | Flexible, no hierarchy | Very limited savings | Not recommended |
| Keep current pattern | Simple, maintainable | Some duplication | **Recommended** |

### Consequences

- SectionsClient remains as-is (already uses @async_method)
- Other clients can migrate to @async_method pattern (Initiative D scope)
- No new CRUDClient abstraction introduced
- Documentation updated to reflect this decision

---

## 8. Implementation Plan

Given the NO-GO recommendation, the implementation plan is:

1. **Complete this TDD** - Document the analysis
2. **Create ADR** - Record the decision
3. **Update meta-initiative** - Mark Initiative E as "Evaluated, Not Implemented"
4. **Document learnings** - Add to code conventions

### 8.1 What We Learned

1. **Metaclasses + Python typing don't mix well** for runtime-generated methods
2. **@async_method pattern is the right level of abstraction** for this codebase
3. **Type overloads are a fundamental tax** that cannot be avoided
4. **Discovery should happen early** - the meta-initiative scope was optimistic

---

## 9. References

- [PRD-DESIGN-PATTERNS-E](../requirements/PRD-DESIGN-PATTERNS-E.md)
- [TDD-DESIGN-PATTERNS-D](TDD-DESIGN-PATTERNS-D.md) - @async_method decorator
- [PROMPT-MINUS-1-DESIGN-PATTERNS](../initiatives/PROMPT-MINUS-1-DESIGN-PATTERNS.md) - Meta-initiative
- [Mypy Metaclasses](https://mypy.readthedocs.io/en/stable/metaclasses.html)
