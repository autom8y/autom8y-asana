"""Tasks client - returns typed Task models by default.

Phase 3.2: Updated to return Pydantic Task models.
Use raw=True for backward-compatible dict returns.
Per TDD-0002: list_async() returns PageIterator[Task] for automatic pagination.
Per ADR-0059: P1 operations and TTL resolution extracted for SRP compliance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, overload

from autom8y_log import get_logger

from autom8_asana.clients.base import BaseClient
from autom8_asana.models import PageIterator, Task
from autom8_asana.models.business import STANDARD_TASK_OPT_FIELDS
from autom8_asana.observability import error_handler
from autom8_asana.patterns import async_method

logger = get_logger(__name__)

# Minimum fields always merged into an explicitly-narrowed task fetch, so a
# narrow-first get_async caches an object rich enough for every LATER reader of the
# same gid. The TASK cache key is opt_fields-blind (FR-CLIENT-002): the field-shape
# of the FIRST fetch of a gid is what every subsequent cache-hit reader receives.
#
#   - parent.gid: cascade / upward hierarchy traversal (GFR no-identity-path).
#     Instance #1 of the narrow-cache-poisoning class (already cured).
#   - memberships.project.gid / memberships.project.name: entity-type + ProcessType
#     detection. tier-1 typing reads memberships[0].project.gid
#     (models/business/detection/tier1.py::_extract_project_gid); ProcessType
#     detection reads memberships[0].project.name (models/business/hydration.py,
#     ADR-0094). Instance #2: without these, a narrow-first fetch cached a
#     membership-less object, starving detection to entity-type-undetectable for
#     every later reader of that gid within the process.
#
# Authored INDEPENDENTLY of DETECTION_MEMBERSHIP_OPT_FIELDS (the detection denominator
# in models/business/fields.py) -- the fetch>=detector coherence property test asserts
# that denominator is a subset of this supply set, so the two cannot silently drift.
_MINIMUM_OPT_FIELDS: frozenset[str] = frozenset(
    {
        "parent.gid",
        "memberships.project.gid",
        "memberships.project.name",
    }
)

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.clients.task_operations import TaskOperations
    from autom8_asana.clients.task_ttl import TaskTTLResolver


class TasksClient(BaseClient):
    """Client for Asana Task operations.

    Returns typed Task models by default. Use raw=True for dict returns.

    P1 Direct Methods (P1):
        - add_tag_async() / add_tag()
        - remove_tag_async() / remove_tag()
        - move_to_section_async() / move_to_section()
        - set_assignee_async() / set_assignee()
        - add_to_project_async() / add_to_project()
        - remove_from_project_async() / remove_from_project()

    Per ADR-0059: P1 operations are delegated to TaskOperations.
    Per ADR-0059: TTL resolution is delegated to TaskTTLResolver.
    """

    def __init__(
        self,
        http: Any,
        config: Any,
        auth_provider: Any,
        cache_provider: Any | None = None,
        log_provider: Any | None = None,
        client: AsanaClient | None = None,
    ) -> None:
        """Initialize TasksClient.

        Args:
            http: HTTP client
            config: SDK configuration
            auth_provider: Authentication provider
            cache_provider: Optional cache provider
            log_provider: Optional log provider
            client: Full AsanaClient instance (for SaveSession support)
        """
        super().__init__(
            http=http,
            config=config,
            auth_provider=auth_provider,
            cache_provider=cache_provider,
            log_provider=log_provider,
        )
        self._client = client
        # Lazy initialization to avoid circular imports (per ADR-0059)
        self._operations: TaskOperations | None = None
        self._ttl_resolver: TaskTTLResolver | None = None

    # --- Lazy Properties for Extracted Components (per ADR-0059) ---

    @property
    def operations(self) -> TaskOperations:
        """Access task operations helper (lazy-loaded).

        Returns:
            TaskOperations instance for P1 convenience methods.
        """
        if self._operations is None:
            from autom8_asana.clients.task_operations import TaskOperations

            self._operations = TaskOperations(self)
        return self._operations

    @property
    def ttl_resolver(self) -> TaskTTLResolver:
        """Access TTL resolver (lazy-loaded).

        Returns:
            TaskTTLResolver instance for cache TTL resolution.
        """
        if self._ttl_resolver is None:
            from autom8_asana.clients.task_ttl import TaskTTLResolver

            self._ttl_resolver = TaskTTLResolver(self._config)
        return self._ttl_resolver

    @overload  # type: ignore[no-overload-impl]
    async def get_async(
        self,
        task_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Task:
        """Get a task by GID, returning a Task model."""
        ...

    @overload
    async def get_async(
        self,
        task_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Get a task by GID, returning a raw dict."""
        ...

    @overload
    def get(
        self,
        task_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Task:
        """Get a task by GID (sync), returning a Task model."""
        ...

    @overload
    def get(
        self,
        task_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Get a task by GID (sync), returning a raw dict."""
        ...

    @async_method  # type: ignore[arg-type, operator, misc]
    @error_handler
    async def get(
        self,
        task_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Task | dict[str, Any]:
        """Get a task by GID with cache support.

        Per FR-CLIENT-001: Checks cache before HTTP request.
        Per FR-CLIENT-002: Uses task GID as cache key with EntryType.TASK.
        Per FR-CLIENT-004: Respects TTL expiration.
        Per FR-CLIENT-007: raw=True returns cached dict directly.

        Args:
            task_gid: Task GID
            raw: If True, return raw dict instead of Task model
            opt_fields: Optional fields to include

        Returns:
            Task model by default, or dict if raw=True

        Raises:
            ValidationError: If task_gid is invalid.
        """
        from autom8_asana.cache.models.coverage import stored_projection
        from autom8_asana.cache.models.entry import EntryType
        from autom8_asana.persistence.validation import validate_gid

        validate_gid(task_gid, "task_gid")

        # PHE (ADR-taskcache-projection-coverage-2026-07-08): resolve the
        # requested projection BEFORE the lookup so the hit is gated on
        # coverage. The predicate runs on entry METADATA before the raw/model
        # branch, so raw=True and model paths are identical by construction.
        resolved_opt_fields = self._resolve_opt_fields(opt_fields)

        # FR-CLIENT-001: Check cache first -- serve ONLY a projection-covering
        # entry. A non-covering entry is a coverage-miss (logged loud) and is
        # exposed as existing_entry for the re-hydration union below.
        cached_entry, existing_entry = self._cache_get_covering(
            task_gid, EntryType.TASK, resolved_opt_fields
        )

        if cached_entry is not None:
            # Per NFR-OBS-001: Log cache hit at DEBUG level
            logger.debug(
                "Cache hit for task",
                extra={"task_gid": task_gid},
            )
            data = cached_entry.data
            # Completeness canary, DEMOTED to cross-writer telemetry (PHE): the
            # coverage predicate now gates hits on stored projection metadata,
            # so this fires only for metadata-less writers whose entries slipped
            # through the empty-request serve path. It is a SIGNAL to
            # investigate, not a proof of regression. O(1) on the passing path.
            if "custom_fields" not in data:
                logger.warning(
                    "TASK cache hit missing custom_fields "
                    "(metadata-less cross-writer -- entry predates PHE stamping)",
                    extra={"task_gid": task_gid, "cached_keys": sorted(data.keys())},
                )
            # Requested-prefix loud canary on TRUSTED hits (defense-in-depth,
            # warn-only -- can never cost a false miss): after the predicate
            # passes, a requested family whose top-level prefix is absent as a
            # key in served data MAY indicate a LYING writer (metadata stamping
            # fields it did not fetch). AXIOM PARTIALLY FALSIFIED LIVE
            # (qa-adversary G9, 2026-07-08): Asana OMITS the key entirely for
            # unset omitted-unless-set fields (opt_fields=["external"] returns
            # NO "external" key, while null-valued start_on IS returned as
            # key:null). So a missing prefix here is AMBIGUOUS -- lying writer
            # OR legitimately-unset omitted field -- which is why this stays
            # warn-only and MUST NOT be promoted to a miss/refusal without a
            # per-family always-materializes allowlist (rejected absent
            # telemetry; see ADR fork open-forks).
            missing_prefixes = {f.split(".", 1)[0] for f in resolved_opt_fields} - set(data.keys())
            if missing_prefixes:
                logger.warning(
                    "TASK cache trusted hit missing requested top-level families "
                    "(writer stamped fields it did not fetch?)",
                    extra={
                        "task_gid": task_gid,
                        "missing_prefixes": sorted(missing_prefixes),
                    },
                )
            if raw:
                return data
            task = Task.model_validate(data)
            task._client = self._client
            return task

        # Per NFR-OBS-001: Log cache miss at DEBUG level
        opt_fields_count = len(opt_fields) if opt_fields else 0
        logger.debug(
            "Cache miss for task",
            extra={"task_gid": task_gid, "opt_fields_count": opt_fields_count},
        )

        # Cache miss: fetch a TRUE SUPERSET of BOTH the caller's projection AND the
        # cache-coherence standard set. The TASK cache key is opt_fields-blind
        # (FR-CLIENT-002): the field-shape of the FIRST fetch of a gid is what every
        # subsequent cache-hit reader receives.
        #
        # Option B (thermia-ruled, HANDOFF-thermia-to-10xdev-taskcache-fix-2026-07-07)
        # as corrected under QA #212 NO-GO: hydrate the miss with
        #   caller-projection  UNION  STANDARD_TASK_OPT_FIELDS
        # NOT STANDARD alone. STANDARD is NOT a superset of every caller's request --
        # it drops modified_at/due_on/completed/tags/assignee/notes/etc. that
        # BASE_OPT_FIELDS (freshness/hierarchy_warmer/progressive watermarks) and
        # field_write_service._TASK_OPT_FIELDS (_refetch_updated echo) require. Fetching
        # STANDARD alone would satisfy the FG-BUG (custom_fields present) but regress
        # those callers to None on a guaranteed-miss refetch. The UNION satisfies the
        # thermodynamicist's invariant literally ("a cache read at projection P returns
        # a value satisfying P, or a miss -- never a silently-narrowed task") for EVERY
        # P, AND keeps FG-BUG closed (STANDARD subset of union => custom_fields.* always
        # present). _resolve_opt_fields restores the caller-projection + parent.gid /
        # memberships cascade minimum that origin/main's miss path carried; for a bare
        # get (opt_fields=None) it returns STANDARD, so the union collapses to STANDARD.
        #
        # PHE (fork b): on a COVERAGE-miss the union additionally carries the
        # stored projection of the non-covering entry -- the anti-thrash
        # keystone. Entry projections are monotonically non-decreasing within a
        # cache lifetime, so disjoint reader pairs converge after ONE widening
        # fetch (pinned by the ping-pong regression test). FETCH-UNION-THEN-
        # REPLACE: merge is REJECTED (splicing two modified_at snapshots
        # manufactures torn reads); because the fetch union includes the stored
        # projection, replace loses zero fields. TTL resets honestly (every
        # byte is fresh).
        stored = (
            stored_projection(existing_entry) if existing_entry is not None else None
        ) or frozenset()
        superset_opt_fields = sorted(
            set(resolved_opt_fields) | set(STANDARD_TASK_OPT_FIELDS) | stored
        )
        params = self._build_opt_fields(superset_opt_fields)
        data = await self._http.get(f"/tasks/{task_gid}", params=params)

        # Store in cache with entity-type TTL (delegates to TaskTTLResolver);
        # stamp the projection actually fetched (PHE metadata authority).
        ttl = self._resolve_entity_ttl(data)
        self._cache_set(task_gid, data, EntryType.TASK, ttl=ttl, opt_fields=superset_opt_fields)

        if raw:
            return data
        task = Task.model_validate(data)
        task._client = self._client  # Store client reference for save/refresh
        return task

    def _resolve_entity_ttl(self, data: dict[str, Any]) -> int:
        """Resolve TTL based on entity type detection.

        Delegates to TaskTTLResolver per ADR-0059.

        Args:
            data: Task data dict from API.

        Returns:
            TTL in seconds.
        """
        return self.ttl_resolver.resolve(data)

    def _resolve_opt_fields(
        self,
        opt_fields: list[str] | None,
        *,
        include_standard: bool = True,
    ) -> list[str]:
        """Resolve opt_fields ensuring minimum fields are always included.

        Per TDD-sdk-cascade-resolution Section 3.1: Ensures parent.gid is always
        included in API requests to support cascade resolution.

        Args:
            opt_fields: User-provided opt_fields, or None for defaults.
            include_standard: If True and opt_fields is None, use STANDARD_TASK_OPT_FIELDS.
                            If False and opt_fields is None, use only _MINIMUM_OPT_FIELDS.

        Returns:
            List of opt_fields with _MINIMUM_OPT_FIELDS merged in.

        Behavior:
            - opt_fields=None, include_standard=True: Returns STANDARD_TASK_OPT_FIELDS
            - opt_fields=None, include_standard=False: Returns list(_MINIMUM_OPT_FIELDS)
            - opt_fields provided: Merges with _MINIMUM_OPT_FIELDS
        """
        if opt_fields is None:
            if include_standard:
                # Use full standard fields which already include parent.gid
                return list(STANDARD_TASK_OPT_FIELDS)
            else:
                # Minimal mode: just the minimum required fields
                return list(_MINIMUM_OPT_FIELDS)

        # Merge user-provided fields with minimum required fields
        merged = set(opt_fields) | _MINIMUM_OPT_FIELDS
        return list(merged)

    @overload  # type: ignore[no-overload-impl]
    async def create_async(
        self,
        *,
        name: str,
        raw: Literal[False] = ...,
        workspace: str | None = ...,
        projects: list[str] | None = ...,
        parent: str | None = ...,
        notes: str | None = ...,
        **kwargs: Any,
    ) -> Task:
        """Create a new task, returning a Task model."""
        ...

    @overload
    async def create_async(
        self,
        *,
        name: str,
        raw: Literal[True],
        workspace: str | None = ...,
        projects: list[str] | None = ...,
        parent: str | None = ...,
        notes: str | None = ...,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a new task, returning a raw dict."""
        ...

    @overload
    def create(
        self,
        *,
        name: str,
        raw: Literal[False] = ...,
        workspace: str | None = ...,
        projects: list[str] | None = ...,
        parent: str | None = ...,
        notes: str | None = ...,
        **kwargs: Any,
    ) -> Task:
        """Create a new task (sync), returning a Task model."""
        ...

    @overload
    def create(
        self,
        *,
        name: str,
        raw: Literal[True],
        workspace: str | None = ...,
        projects: list[str] | None = ...,
        parent: str | None = ...,
        notes: str | None = ...,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a new task (sync), returning a raw dict."""
        ...

    @async_method  # type: ignore[arg-type, operator, misc]
    @error_handler
    async def create(
        self,
        *,
        name: str,
        raw: bool = False,
        workspace: str | None = None,
        projects: list[str] | None = None,
        parent: str | None = None,
        notes: str | None = None,
        **kwargs: Any,
    ) -> Task | dict[str, Any]:
        """Create a new task.

        Args:
            name: Task name (required)
            raw: If True, return raw dict instead of Task model
            workspace: Workspace GID (required if no projects/parent)
            projects: List of project GIDs to add task to
            parent: Parent task GID (for subtasks)
            notes: Task description
            **kwargs: Additional task fields

        Returns:
            Task model by default, or dict if raw=True
        """

        data: dict[str, Any] = {"name": name}

        if workspace:
            data["workspace"] = workspace
        if projects:
            data["projects"] = projects
        if parent:
            data["parent"] = parent
        if notes:
            data["notes"] = notes

        data.update(kwargs)

        result = await self._http.post("/tasks", json={"data": data})
        if raw:
            return result
        task = Task.model_validate(result)
        task._client = self._client  # Store client reference for save/refresh
        return task

    @overload  # type: ignore[no-overload-impl]
    async def update_async(
        self,
        task_gid: str,
        *,
        raw: Literal[False] = ...,
        **kwargs: Any,
    ) -> Task:
        """Update a task, returning a Task model."""
        ...

    @overload
    async def update_async(
        self,
        task_gid: str,
        *,
        raw: Literal[True],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update a task, returning a raw dict."""
        ...

    @overload
    def update(
        self,
        task_gid: str,
        *,
        raw: Literal[False] = ...,
        **kwargs: Any,
    ) -> Task:
        """Update a task (sync), returning a Task model."""
        ...

    @overload
    def update(
        self,
        task_gid: str,
        *,
        raw: Literal[True],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update a task (sync), returning a raw dict."""
        ...

    @async_method  # type: ignore[arg-type, operator, misc]
    @error_handler
    async def update(
        self,
        task_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> Task | dict[str, Any]:
        """Update a task.

        Args:
            task_gid: Task GID
            raw: If True, return raw dict instead of Task model
            **kwargs: Fields to update

        Returns:
            Task model by default, or dict if raw=True
        """
        result = await self._http.put(f"/tasks/{task_gid}", json={"data": kwargs})
        if raw:
            return result
        task = Task.model_validate(result)
        task._client = self._client  # Store client reference for save/refresh
        return task

    @async_method  # type: ignore[arg-type]
    @error_handler
    async def delete(self, task_gid: str) -> None:
        """Delete a task.

        Args:
            task_gid: Task GID
        """
        await self._http.delete(f"/tasks/{task_gid}")

    def list_async(
        self,
        *,
        project: str | None = None,
        section: str | None = None,
        assignee: str | None = None,
        workspace: str | None = None,
        completed_since: str | None = None,
        modified_since: str | None = None,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Task]:
        """List tasks with automatic pagination.

        Returns a PageIterator that lazily fetches pages as you iterate.

        Args:
            project: Filter by project GID
            section: Filter by section GID
            assignee: Filter by assignee GID (use "me" for current user)
            workspace: Filter by workspace GID (required if no project/section)
            completed_since: ISO 8601 datetime; include completed tasks modified since
            modified_since: ISO 8601 datetime; only tasks modified since
            opt_fields: Fields to include in response
            limit: Number of items per page (default 100, max 100)

        Returns:
            PageIterator[Task] - async iterator over Task objects

        Example:
            # Iterate all tasks
            async for task in client.tasks.list_async(project="123"):
                print(task.name)

            # Get first 10
            tasks = await client.tasks.list_async(project="123").take(10)

            # Collect all
            all_tasks = await client.tasks.list_async(project="123").collect()
        """
        self._log_operation("list_async")

        # Resolve opt_fields to ensure parent.gid is always included
        # Per TDD-sdk-cascade-resolution: This is critical for cascade resolution
        resolved_opt_fields = self._resolve_opt_fields(opt_fields)

        async def fetch_page(offset: str | None) -> tuple[list[Task], str | None]:
            """Fetch a single page of tasks."""
            params = self._build_opt_fields(resolved_opt_fields)
            if project:
                params["project"] = project
            if section:
                params["section"] = section
            if assignee:
                params["assignee"] = assignee
            if workspace:
                params["workspace"] = workspace
            if completed_since:
                params["completed_since"] = completed_since
            if modified_since:
                params["modified_since"] = modified_since
            params["limit"] = min(limit, 100)  # Asana max is 100
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated("/tasks", params=params)
            tasks = [Task.model_validate(t) for t in data]
            return tasks, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))

    # Default fields needed for entity type detection and field cascading
    # Per PRD-CACHE-PERF-HYDRATION FR-CACHE-001, FR-CACHE-002:
    # Use STANDARD_TASK_OPT_FIELDS to ensure parent.gid and people_value are present.
    # This enables upward traversal and Owner cascading from cached tasks.
    # Per ADR-0101: Include project.name for ProcessType detection via project name matching.
    # Per TDD-HYDRATION: Include custom_fields for field cascading (Vertical, Products, etc.)
    _DETECTION_FIELDS: list[str] = list(STANDARD_TASK_OPT_FIELDS)

    def subtasks_async(
        self,
        task_gid: str,
        *,
        opt_fields: list[str] | None = None,
        include_detection_fields: bool = False,
        limit: int = 100,
    ) -> PageIterator[Task]:
        """List subtasks of a task with automatic pagination.

        Returns a PageIterator that lazily fetches pages as you iterate.

        Per ADR-0057: Provides async iteration over subtasks of a parent task.

        Args:
            task_gid: GID of the parent task
            opt_fields: Fields to include in response
            include_detection_fields: If True, automatically include fields needed
                for entity type detection and field cascading:
                - Detection: memberships.project.gid, memberships.project.name, name
                - Custom fields: custom_fields with all subfields for cascading
                This is useful when hydrating holders to enable detection-based
                identification, ProcessType detection via project name matching,
                and access to cascading fields (Vertical, Products, etc.).
                Default is False to maintain backward compatibility.
            limit: Number of items per page (default 100, max 100)

        Returns:
            PageIterator[Task] - async iterator over Task objects

        Example:
            # Iterate all subtasks
            async for subtask in client.tasks.subtasks_async("parent_gid"):
                print(subtask.name)

            # Collect all subtasks
            all_subtasks = await client.tasks.subtasks_async("parent_gid").collect()

            # With detection fields for holder identification
            subtasks = await client.tasks.subtasks_async(
                "parent_gid", include_detection_fields=True
            ).collect()
        """
        self._log_operation("subtasks_async")

        # Merge detection fields if requested, then resolve to ensure minimum fields
        effective_opt_fields = opt_fields
        if include_detection_fields:
            detection_fields = set(self._DETECTION_FIELDS)
            if opt_fields:
                # Merge, avoiding duplicates
                effective_opt_fields = list(set(opt_fields) | detection_fields)
            else:
                effective_opt_fields = list(detection_fields)

        # Resolve opt_fields to ensure parent.gid is always included
        # Per TDD-sdk-cascade-resolution: This is critical for cascade resolution
        resolved_opt_fields = self._resolve_opt_fields(effective_opt_fields)

        async def fetch_page(offset: str | None) -> tuple[list[Task], str | None]:
            """Fetch a single page of subtasks."""
            params = self._build_opt_fields(resolved_opt_fields)
            params["limit"] = min(limit, 100)
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                f"/tasks/{task_gid}/subtasks",
                params=params,
            )
            tasks = [Task.model_validate(t) for t in data]
            return tasks, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))

    def dependents_async(
        self,
        task_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Task]:
        """List dependent tasks (tasks that depend on this task) with automatic pagination.

        Returns a PageIterator that lazily fetches pages as you iterate.

        Per FR-PREREQ-003: Follows subtasks_async() pattern for fetching dependents.

        A dependent task is one that depends on this task to be completed first
        (i.e., this task is a blocker/dependency of the returned tasks).
        Note: Asana limits combined dependents+dependencies to 30 per task.

        Args:
            task_gid: GID of the task to get dependents for.
            opt_fields: Fields to include in response.
            limit: Number of items per page (default 100, max 100).

        Returns:
            PageIterator[Task] - async iterator over Task objects.

        Example:
            # Iterate all dependents
            async for dependent in client.tasks.dependents_async("task_gid"):
                print(f"Task {dependent.name} depends on this task")

            # Collect all dependents
            all_dependents = await client.tasks.dependents_async("task_gid").collect()
        """
        from autom8_asana.persistence.validation import validate_gid

        validate_gid(task_gid, "task_gid")
        self._log_operation("dependents_async")

        # Resolve opt_fields to ensure parent.gid is always included
        # Per TDD-sdk-cascade-resolution: This is critical for cascade resolution
        resolved_opt_fields = self._resolve_opt_fields(opt_fields)

        async def fetch_page(offset: str | None) -> tuple[list[Task], str | None]:
            """Fetch a single page of dependents."""
            params = self._build_opt_fields(resolved_opt_fields)
            params["limit"] = min(limit, 100)
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                f"/tasks/{task_gid}/dependents",
                params=params,
            )
            tasks = [Task.model_validate(t) for t in data]
            return tasks, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))

    # --- P1 Direct Methods: Delegated to TaskOperations (per ADR-0059) ---
    # Per TDD-SDKUX Section 2C: Direct methods that wrap SaveSession internally
    # and return updated Task objects without requiring explicit session management.

    async def add_tag_async(self, task_gid: str, tag_gid: str, *, refresh: bool = False) -> Task:
        """Add tag to task without explicit SaveSession.

        Delegates to TaskOperations.add_tag_async per ADR-0059.

        Args:
            task_gid: Target task GID
            tag_gid: Tag GID to add
            refresh: If True, fetch fresh task state after commit. Default False.

        Returns:
            Task object (refreshed if refresh=True, otherwise pre-commit state)
        """
        return await self.operations.add_tag_async(task_gid, tag_gid, refresh=refresh)  # type: ignore[attr-defined, no-any-return]

    def add_tag(self, task_gid: str, tag_gid: str, *, refresh: bool = False) -> Task:
        """Add tag to task without explicit SaveSession (sync).

        Delegates to TaskOperations.add_tag per ADR-0059.
        """
        return self.operations.add_tag(task_gid, tag_gid, refresh=refresh)  # type: ignore[no-any-return]

    async def remove_tag_async(self, task_gid: str, tag_gid: str, *, refresh: bool = False) -> Task:
        """Remove tag from task without explicit SaveSession.

        Delegates to TaskOperations.remove_tag_async per ADR-0059.
        """
        return await self.operations.remove_tag_async(  # type: ignore[attr-defined, no-any-return]
            task_gid, tag_gid, refresh=refresh
        )

    def remove_tag(self, task_gid: str, tag_gid: str, *, refresh: bool = False) -> Task:
        """Remove tag from task without explicit SaveSession (sync).

        Delegates to TaskOperations.remove_tag per ADR-0059.
        """
        return self.operations.remove_tag(task_gid, tag_gid, refresh=refresh)  # type: ignore[no-any-return]

    async def move_to_section_async(
        self,
        task_gid: str,
        section_gid: str,
        project_gid: str,
        *,
        refresh: bool = False,
    ) -> Task:
        """Move task to section within project without explicit SaveSession.

        Delegates to TaskOperations.move_to_section_async per ADR-0059.
        """
        return await self.operations.move_to_section_async(  # type: ignore[attr-defined, no-any-return]
            task_gid, section_gid, project_gid, refresh=refresh
        )

    def move_to_section(
        self,
        task_gid: str,
        section_gid: str,
        project_gid: str,
        *,
        refresh: bool = False,
    ) -> Task:
        """Move task to section within project without explicit SaveSession (sync).

        Delegates to TaskOperations.move_to_section per ADR-0059.
        """
        return self.operations.move_to_section(  # type: ignore[no-any-return]
            task_gid, section_gid, project_gid, refresh=refresh
        )

    async def set_assignee_async(self, task_gid: str, assignee_gid: str) -> Task:
        """Set task assignee without explicit SaveSession.

        Delegates to TaskOperations.set_assignee_async per ADR-0059.
        """
        return await self.operations.set_assignee_async(task_gid, assignee_gid)  # type: ignore[attr-defined, no-any-return]

    def set_assignee(self, task_gid: str, assignee_gid: str) -> Task:
        """Set task assignee without explicit SaveSession (sync).

        Delegates to TaskOperations.set_assignee per ADR-0059.
        """
        return self.operations.set_assignee(task_gid, assignee_gid)  # type: ignore[no-any-return]

    async def add_to_project_async(
        self,
        task_gid: str,
        project_gid: str,
        section_gid: str | None = None,
        *,
        refresh: bool = False,
    ) -> Task:
        """Add task to project without explicit SaveSession.

        Delegates to TaskOperations.add_to_project_async per ADR-0059.
        """
        return await self.operations.add_to_project_async(  # type: ignore[attr-defined, no-any-return]
            task_gid, project_gid, section_gid, refresh=refresh
        )

    def add_to_project(
        self,
        task_gid: str,
        project_gid: str,
        section_gid: str | None = None,
        *,
        refresh: bool = False,
    ) -> Task:
        """Add task to project without explicit SaveSession (sync).

        Delegates to TaskOperations.add_to_project per ADR-0059.
        """
        return self.operations.add_to_project(  # type: ignore[no-any-return]
            task_gid, project_gid, section_gid, refresh=refresh
        )

    async def remove_from_project_async(
        self, task_gid: str, project_gid: str, *, refresh: bool = False
    ) -> Task:
        """Remove task from project without explicit SaveSession.

        Delegates to TaskOperations.remove_from_project_async per ADR-0059.
        """
        return await self.operations.remove_from_project_async(  # type: ignore[attr-defined, no-any-return]
            task_gid, project_gid, refresh=refresh
        )

    def remove_from_project(
        self, task_gid: str, project_gid: str, *, refresh: bool = False
    ) -> Task:
        """Remove task from project without explicit SaveSession (sync).

        Delegates to TaskOperations.remove_from_project per ADR-0059.
        """
        return self.operations.remove_from_project(  # type: ignore[no-any-return]
            task_gid, project_gid, refresh=refresh
        )

    # --- Task Duplication ---
    # Per TDD-PIPELINE-AUTOMATION-ENHANCEMENT: Wraps Asana's duplicate endpoint

    @overload  # type: ignore[no-overload-impl]
    async def duplicate_async(
        self,
        task_gid: str,
        *,
        name: str,
        include: list[str] | None = ...,
        raw: Literal[False] = ...,
    ) -> Task:
        """Duplicate a task, returning a Task model."""
        ...

    @overload
    async def duplicate_async(
        self,
        task_gid: str,
        *,
        name: str,
        include: list[str] | None = ...,
        raw: Literal[True],
    ) -> dict[str, Any]:
        """Duplicate a task, returning a raw dict."""
        ...

    @overload
    def duplicate(
        self,
        task_gid: str,
        *,
        name: str,
        include: list[str] | None = ...,
        raw: Literal[False] = ...,
    ) -> Task:
        """Duplicate a task (sync), returning a Task model."""
        ...

    @overload
    def duplicate(
        self,
        task_gid: str,
        *,
        name: str,
        include: list[str] | None = ...,
        raw: Literal[True],
    ) -> dict[str, Any]:
        """Duplicate a task (sync), returning a raw dict."""
        ...

    @async_method  # type: ignore[arg-type, operator, misc]
    @error_handler
    async def duplicate(
        self,
        task_gid: str,
        *,
        name: str,
        include: list[str] | None = None,
        raw: bool = False,
    ) -> Task | dict[str, Any]:
        """Duplicate a task with optional attribute copying.

        Per FR-DUP-001: Wraps Asana's POST /tasks/{task_gid}/duplicate.

        Args:
            task_gid: GID of the task to duplicate.
            name: Name for the new task (required by Asana API).
            include: List of attributes to copy. Valid values:
                - "subtasks": Copy all subtasks
                - "notes": Copy task description
                - "assignee": Copy assignee
                - "attachments": Copy attachments
                - "dates": Copy due dates
                - "dependencies": Copy dependencies
                - "collaborators": Copy followers
                - "tags": Copy tags
            raw: If True, return raw dict instead of Task model.

        Returns:
            Task model (or dict if raw=True) representing the new task.
            The new_task.gid is immediately available.
            Note: Subtasks are created asynchronously by Asana.

        Raises:
            ValidationError: If task_gid is invalid.
            NotFoundError: If source task doesn't exist.
        """
        from autom8_asana.persistence.validation import validate_gid

        validate_gid(task_gid, "task_gid")

        # Build request payload
        data: dict[str, Any] = {"name": name}
        if include:
            data["include"] = include

        # Call Asana duplicate endpoint
        result = await self._http.post(
            f"/tasks/{task_gid}/duplicate",
            json={"data": data},
        )

        # Asana returns a job object with new_task embedded
        # Extract the new_task from the job response
        new_task_data: dict[str, Any] = result.get("new_task", result)

        if raw:
            return new_task_data
        task = Task.model_validate(new_task_data)
        task._client = self._client
        return task
