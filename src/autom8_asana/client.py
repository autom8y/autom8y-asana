"""Main AsanaClient facade."""

from __future__ import annotations

import asyncio
import os
import threading
from typing import TYPE_CHECKING, Any

from autom8_asana._defaults.auth import EnvAuthProvider
from autom8_asana._defaults.log import DefaultLogProvider
from autom8_asana.cache.factory import create_cache_provider
from autom8_asana._defaults.observability import NullObservabilityHook
from autom8_asana.batch.client import BatchClient
from autom8_asana.persistence import SaveSession
from autom8_asana.clients.attachments import AttachmentsClient
from autom8_asana.clients.custom_fields import CustomFieldsClient
from autom8_asana.clients.goals import GoalsClient
from autom8_asana.clients.portfolios import PortfoliosClient
from autom8_asana.clients.projects import ProjectsClient
from autom8_asana.clients.sections import SectionsClient
from autom8_asana.clients.stories import StoriesClient
from autom8_asana.clients.tags import TagsClient
from autom8_asana.clients.tasks import TasksClient
from autom8_asana.clients.teams import TeamsClient
from autom8_asana.clients.users import UsersClient
from autom8_asana.clients.webhooks import WebhooksClient
from autom8_asana.clients.workspaces import WorkspacesClient
from autom8_asana.config import AsanaConfig
from autom8_asana.exceptions import AuthenticationError, ConfigurationError
from autom8_asana.transport.http import AsyncHTTPClient

if TYPE_CHECKING:
    from autom8_asana.automation.engine import AutomationEngine
    from autom8_asana.protocols.auth import AuthProvider
    from autom8_asana.protocols.cache import CacheProvider
    from autom8_asana.protocols.log import LogProvider
    from autom8_asana.protocols.observability import ObservabilityHook


class AsanaClient:
    """Main entry point for the autom8_asana SDK.

    Provides access to all Asana API resources through typed clients.

    Example (standalone with env var):
        # Set ASANA_PAT environment variable
        client = AsanaClient()
        task = client.tasks.get("task_gid")

    Example (with explicit token):
        client = AsanaClient(token="your_pat_here")
        task = await client.tasks.get_async("task_gid")

    Example (with custom providers - autom8 integration):
        client = AsanaClient(
            auth_provider=MyAuthProvider(),
            cache_provider=MyCacheProvider(),
            log_provider=MyLogProvider(),
        )

    Usage as context manager (recommended for cleanup):
        async with AsanaClient(token="...") as client:
            task = await client.tasks.get_async("task_gid")
    """

    def __init__(
        self,
        token: str | None = None,
        *,
        workspace_gid: str | None = None,
        auth_provider: AuthProvider | None = None,
        cache_provider: CacheProvider | None = None,
        log_provider: LogProvider | None = None,
        config: AsanaConfig | None = None,
        observability_hook: ObservabilityHook | None = None,
    ) -> None:
        """Initialize AsanaClient.

        Args:
            token: Asana Personal Access Token (convenience parameter)
            workspace_gid: Workspace GID (optional). Resolution order:
                          1. Explicit parameter (if provided)
                          2. ASANA_WORKSPACE_GID environment variable
                          3. Auto-detection (if exactly one workspace exists)
            auth_provider: Custom auth provider (overrides token)
            cache_provider: Custom cache provider. If None, uses environment-aware
                auto-selection based on config.cache settings. Pass
                NullCacheProvider() explicitly to disable all caching.
                Per TDD-CACHE-INTEGRATION: FR-CLIENT-006, NFR-COMPAT-004.
            log_provider: Custom log provider (default: DefaultLogProvider)
            config: SDK configuration (default: AsanaConfig())
            observability_hook: Custom observability hook for metrics/tracing
                (default: NullObservabilityHook). Per TDD-HARDENING-A/FR-OBS-011.

        Raises:
            ConfigurationError: If workspace_gid not provided and:
                               - 0 workspaces available (token invalid?)
                               - >1 workspaces available (ambiguous, must specify)

        Example:
            >>> # Simple: auto-detect if only one workspace
            >>> client = AsanaClient(token="...")

            >>> # From environment variable
            >>> # export ASANA_WORKSPACE_GID=1234567890123456
            >>> client = AsanaClient(token="...")

            >>> # Explicit: specify workspace (overrides env var)
            >>> client = AsanaClient(token="...", workspace_gid="1234567890123456")
        """
        self._config = config or AsanaConfig()

        # Resolve auth provider
        resolved_auth_provider: AuthProvider
        if auth_provider is not None:
            resolved_auth_provider = auth_provider
        elif token is not None:
            # Create simple token-based provider
            resolved_auth_provider = _TokenAuthProvider(token, self._config.token_key)
        else:
            # Try environment variables
            resolved_auth_provider = EnvAuthProvider()

        self._auth_provider: AuthProvider = resolved_auth_provider

        # Resolve other providers
        # Per TDD-CACHE-INTEGRATION: Use factory for environment-aware selection
        # FR-CLIENT-006: Explicit provider takes precedence
        # NFR-COMPAT-004: NullCacheProvider explicit still works
        self._cache_provider: CacheProvider = create_cache_provider(
            config=self._config.cache,
            explicit_provider=cache_provider,
        )
        self._log_provider: LogProvider = log_provider or DefaultLogProvider()
        self._observability_hook: ObservabilityHook = (
            observability_hook or NullObservabilityHook()
        )

        # Create HTTP client
        self._http = AsyncHTTPClient(
            config=self._config,
            auth_provider=self._auth_provider,
            logger=self._log_provider,
        )

        # Resolve workspace_gid: parameter > env var > auto-detect
        if workspace_gid is None:
            # Check environment variable
            env_workspace = os.environ.get("ASANA_WORKSPACE_GID")
            if env_workspace and env_workspace.strip():
                workspace_gid = env_workspace.strip()
            elif token is not None:
                # Auto-detect only if token was explicitly provided
                workspace_gid = self._auto_detect_workspace(
                    self._auth_provider, self._config.token_key
                )

        self.default_workspace_gid = workspace_gid

        # Lazy-initialized resource clients with lock to prevent race conditions
        # Using threading.Lock since property accessors are synchronous

        # Tier 1 clients
        self._tasks: TasksClient | None = None
        self._tasks_lock = threading.Lock()
        self._projects: ProjectsClient | None = None
        self._projects_lock = threading.Lock()
        self._sections: SectionsClient | None = None
        self._sections_lock = threading.Lock()
        self._custom_fields: CustomFieldsClient | None = None
        self._custom_fields_lock = threading.Lock()
        self._users: UsersClient | None = None
        self._users_lock = threading.Lock()
        self._workspaces: WorkspacesClient | None = None
        self._workspaces_lock = threading.Lock()

        # Tier 2 clients
        self._webhooks: WebhooksClient | None = None
        self._webhooks_lock = threading.Lock()
        self._teams: TeamsClient | None = None
        self._teams_lock = threading.Lock()
        self._attachments: AttachmentsClient | None = None
        self._attachments_lock = threading.Lock()
        self._tags: TagsClient | None = None
        self._tags_lock = threading.Lock()
        self._goals: GoalsClient | None = None
        self._goals_lock = threading.Lock()
        self._portfolios: PortfoliosClient | None = None
        self._portfolios_lock = threading.Lock()
        self._stories: StoriesClient | None = None
        self._stories_lock = threading.Lock()

        # Specialized clients
        self._batch: BatchClient | None = None
        self._batch_lock = threading.Lock()

        # Automation engine (TDD-AUTOMATION-LAYER)
        from autom8_asana.automation.engine import AutomationEngine

        self._automation: AutomationEngine | None = None
        if self._config.automation.enabled:
            self._automation = AutomationEngine(self._config.automation)

    @property
    def automation(self) -> "AutomationEngine | None":
        """Access automation engine for rule registration.

        Per TDD-AUTOMATION-LAYER: Provides access to AutomationEngine.

        Returns:
            AutomationEngine if automation is enabled, None otherwise.

        Example:
            if client.automation:
                client.automation.register(PipelineConversionRule())
                client.automation.register(MyCustomRule())
        """
        return self._automation

    @property
    def observability(self) -> "ObservabilityHook":
        """Observability hook for metrics and tracing.

        Per TDD-HARDENING-A/FR-OBS-011: Exposes the configured observability hook.
        Returns NullObservabilityHook if none was configured.

        Returns:
            The configured ObservabilityHook implementation.
        """
        return self._observability_hook

    @property
    def tasks(self) -> TasksClient:
        """Tasks API client.

        Thread-safe lazy initialization using double-checked locking.
        """
        # Fast path: client already exists
        if self._tasks is not None:
            return self._tasks

        # Slow path: acquire lock and create client
        with self._tasks_lock:
            # Double-check after acquiring lock
            if self._tasks is None:
                self._tasks = TasksClient(
                    http=self._http,
                    config=self._config,
                    auth_provider=self._auth_provider,
                    cache_provider=self._cache_provider,
                    log_provider=self._log_provider,
                    client=self,
                )
        return self._tasks

    @property
    def projects(self) -> ProjectsClient:
        """Projects API client.

        Thread-safe lazy initialization using double-checked locking.
        """
        if self._projects is not None:
            return self._projects

        with self._projects_lock:
            if self._projects is None:
                self._projects = ProjectsClient(
                    http=self._http,
                    config=self._config,
                    auth_provider=self._auth_provider,
                    cache_provider=self._cache_provider,
                    log_provider=self._log_provider,
                )
        return self._projects

    @property
    def sections(self) -> SectionsClient:
        """Sections API client.

        Thread-safe lazy initialization using double-checked locking.
        """
        if self._sections is not None:
            return self._sections

        with self._sections_lock:
            if self._sections is None:
                self._sections = SectionsClient(
                    http=self._http,
                    config=self._config,
                    auth_provider=self._auth_provider,
                    cache_provider=self._cache_provider,
                    log_provider=self._log_provider,
                )
        return self._sections

    @property
    def custom_fields(self) -> CustomFieldsClient:
        """Custom Fields API client.

        Thread-safe lazy initialization using double-checked locking.
        """
        if self._custom_fields is not None:
            return self._custom_fields

        with self._custom_fields_lock:
            if self._custom_fields is None:
                self._custom_fields = CustomFieldsClient(
                    http=self._http,
                    config=self._config,
                    auth_provider=self._auth_provider,
                    cache_provider=self._cache_provider,
                    log_provider=self._log_provider,
                )
        return self._custom_fields

    @property
    def users(self) -> UsersClient:
        """Users API client.

        Thread-safe lazy initialization using double-checked locking.
        """
        if self._users is not None:
            return self._users

        with self._users_lock:
            if self._users is None:
                self._users = UsersClient(
                    http=self._http,
                    config=self._config,
                    auth_provider=self._auth_provider,
                    cache_provider=self._cache_provider,
                    log_provider=self._log_provider,
                )
        return self._users

    @property
    def workspaces(self) -> WorkspacesClient:
        """Workspaces API client.

        Thread-safe lazy initialization using double-checked locking.
        """
        if self._workspaces is not None:
            return self._workspaces

        with self._workspaces_lock:
            if self._workspaces is None:
                self._workspaces = WorkspacesClient(
                    http=self._http,
                    config=self._config,
                    auth_provider=self._auth_provider,
                    cache_provider=self._cache_provider,
                    log_provider=self._log_provider,
                )
        return self._workspaces

    # --- Tier 2 Clients ---

    @property
    def webhooks(self) -> WebhooksClient:
        """Webhooks API client.

        Thread-safe lazy initialization using double-checked locking.
        """
        if self._webhooks is not None:
            return self._webhooks

        with self._webhooks_lock:
            if self._webhooks is None:
                self._webhooks = WebhooksClient(
                    http=self._http,
                    config=self._config,
                    auth_provider=self._auth_provider,
                    cache_provider=self._cache_provider,
                    log_provider=self._log_provider,
                )
        return self._webhooks

    @property
    def teams(self) -> TeamsClient:
        """Teams API client.

        Thread-safe lazy initialization using double-checked locking.
        """
        if self._teams is not None:
            return self._teams

        with self._teams_lock:
            if self._teams is None:
                self._teams = TeamsClient(
                    http=self._http,
                    config=self._config,
                    auth_provider=self._auth_provider,
                    cache_provider=self._cache_provider,
                    log_provider=self._log_provider,
                )
        return self._teams

    @property
    def attachments(self) -> AttachmentsClient:
        """Attachments API client.

        Thread-safe lazy initialization using double-checked locking.
        """
        if self._attachments is not None:
            return self._attachments

        with self._attachments_lock:
            if self._attachments is None:
                self._attachments = AttachmentsClient(
                    http=self._http,
                    config=self._config,
                    auth_provider=self._auth_provider,
                    cache_provider=self._cache_provider,
                    log_provider=self._log_provider,
                )
        return self._attachments

    @property
    def tags(self) -> TagsClient:
        """Tags API client.

        Thread-safe lazy initialization using double-checked locking.
        """
        if self._tags is not None:
            return self._tags

        with self._tags_lock:
            if self._tags is None:
                self._tags = TagsClient(
                    http=self._http,
                    config=self._config,
                    auth_provider=self._auth_provider,
                    cache_provider=self._cache_provider,
                    log_provider=self._log_provider,
                )
        return self._tags

    @property
    def goals(self) -> GoalsClient:
        """Goals API client.

        Thread-safe lazy initialization using double-checked locking.
        """
        if self._goals is not None:
            return self._goals

        with self._goals_lock:
            if self._goals is None:
                self._goals = GoalsClient(
                    http=self._http,
                    config=self._config,
                    auth_provider=self._auth_provider,
                    cache_provider=self._cache_provider,
                    log_provider=self._log_provider,
                )
        return self._goals

    @property
    def portfolios(self) -> PortfoliosClient:
        """Portfolios API client.

        Thread-safe lazy initialization using double-checked locking.
        """
        if self._portfolios is not None:
            return self._portfolios

        with self._portfolios_lock:
            if self._portfolios is None:
                self._portfolios = PortfoliosClient(
                    http=self._http,
                    config=self._config,
                    auth_provider=self._auth_provider,
                    cache_provider=self._cache_provider,
                    log_provider=self._log_provider,
                )
        return self._portfolios

    @property
    def stories(self) -> StoriesClient:
        """Stories API client.

        Thread-safe lazy initialization using double-checked locking.
        """
        if self._stories is not None:
            return self._stories

        with self._stories_lock:
            if self._stories is None:
                self._stories = StoriesClient(
                    http=self._http,
                    config=self._config,
                    auth_provider=self._auth_provider,
                    cache_provider=self._cache_provider,
                    log_provider=self._log_provider,
                )
        return self._stories

    # --- Specialized Clients ---

    @property
    def batch(self) -> BatchClient:
        """Batch API client for bulk operations.

        Thread-safe lazy initialization using double-checked locking.

        Enables efficient bulk operations by batching multiple requests
        into single API calls. Automatically handles:
        - Chunking requests into groups of 10 (Asana's limit)
        - Sequential chunk execution for rate limit compliance
        - Partial failure handling (one failure doesn't fail the batch)

        Example:
            from autom8_asana.batch import BatchRequest

            requests = [
                BatchRequest("/tasks", "POST", data={"name": "Task 1", "projects": ["123"]}),
                BatchRequest("/tasks", "POST", data={"name": "Task 2", "projects": ["123"]}),
            ]
            results = await client.batch.execute_async(requests)

            # Or use convenience methods:
            results = await client.batch.create_tasks_async([
                {"name": "Task 1", "projects": ["123"]},
                {"name": "Task 2", "projects": ["123"]},
            ])
        """
        if self._batch is not None:
            return self._batch

        with self._batch_lock:
            if self._batch is None:
                self._batch = BatchClient(
                    http=self._http,
                    config=self._config,
                    auth_provider=self._auth_provider,
                    cache_provider=self._cache_provider,
                    log_provider=self._log_provider,
                )
        return self._batch

    # --- Auto-detection ---

    @staticmethod
    def _auto_detect_workspace(
        auth_provider: AuthProvider,
        token_key: str,
    ) -> str | None:
        """Auto-detect workspace GID if exactly one exists.

        Makes a synchronous HTTP call to /users/me endpoint to fetch workspaces.

        Args:
            auth_provider: Authentication provider
            token_key: Token secret key (from config.token_key)

        Returns:
            Workspace GID if exactly one found, or None if auto-detection fails/unavailable

        Raises:
            ConfigurationError: If >1 workspaces found (ambiguous choice)
        """
        import httpx

        # Get token from auth provider using the specified key
        try:
            token = auth_provider.get_secret(token_key)
        except KeyError:
            raise ConfigurationError(
                f"Cannot auto-detect workspace: auth provider does not have '{token_key}' secret"
            )

        # Create temporary synchronous HTTP client
        with httpx.Client(
            headers={"Authorization": f"Bearer {token}"},
            base_url="https://app.asana.com/api/1.0",
        ) as client:
            try:
                response = client.get(
                    "/users/me",
                    params={"opt_fields": "workspaces.gid,workspaces.name"},
                    timeout=10.0,
                )
                response.raise_for_status()
                data: dict[str, Any] = response.json()["data"]
                workspaces: list[dict[str, Any]] = data.get("workspaces", [])

                if len(workspaces) == 0:
                    raise ConfigurationError(
                        "No workspaces found. Token may be invalid or have no workspace access."
                    )
                elif len(workspaces) == 1:
                    gid: str = workspaces[0]["gid"]
                    return gid
                else:
                    workspace_names = [w["name"] for w in workspaces]
                    raise ConfigurationError(
                        f"Multiple workspaces found: {', '.join(workspace_names)}. "
                        f"Please specify workspace_gid explicitly: "
                        f"AsanaClient(token=..., workspace_gid='your_gid')"
                    )
            except httpx.HTTPError:
                # If the token is invalid or the API is unreachable, we can't auto-detect
                # This is expected for test tokens, so we return None to indicate no auto-detection
                # The client will continue without a workspace_gid
                return None

    # --- Save Session Factory ---

    def save_session(
        self,
        batch_size: int = 10,
        max_concurrent: int = 15,
    ) -> SaveSession:
        """Create a SaveSession for batched operations.

        Returns a context manager that enables deferred, batched saves
        with automatic dependency ordering and partial failure handling.

        Example (async):
            async with client.save_session() as session:
                session.track(task)
                task.name = "Updated"
                result = await session.commit_async()

        Example (sync):
            with client.save_session() as session:
                session.track(task)
                task.name = "Updated"
                result = session.commit()

        Args:
            batch_size: Maximum operations per batch (default: 10, Asana limit).
            max_concurrent: Maximum concurrent batch requests (default: 15).

        Returns:
            SaveSession instance (context manager).
        """
        return SaveSession(
            client=self,
            batch_size=batch_size,
            max_concurrent=max_concurrent,
        )

    async def close(self) -> None:
        """Close client and release resources.

        Call this when done with the client, or use as context manager.
        """
        await self._http.close()

    async def aclose(self) -> None:
        """Async close - alias for close() for naming consistency with httpx."""
        await self.close()

    async def __aenter__(self) -> AsanaClient:
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit - closes client."""
        await self.close()

    def __enter__(self) -> AsanaClient:
        """Sync context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Sync context manager exit - closes client.

        Raises:
            ConfigurationError: If called from an async context, where
                resources cannot be properly cleaned up. Use `async with`
                instead.
        """
        try:
            asyncio.get_running_loop()
            # If there's a running loop, we can't use asyncio.run()
            # Fail fast per ADR-0002 - don't silently leak resources
            raise ConfigurationError(
                "Cannot use sync context manager in async context. "
                "Use 'async with AsanaClient(...) as client:' instead."
            )
        except RuntimeError:
            # No running loop - safe to run close
            asyncio.run(self.close())


class _TokenAuthProvider:
    """Simple auth provider that returns a fixed token."""

    def __init__(self, token: str, expected_key: str) -> None:
        """Initialize with a token.

        Args:
            token: The authentication token (must be non-empty)
            expected_key: The key this provider responds to

        Raises:
            AuthenticationError: If token is empty or whitespace-only
        """
        if not token.strip():
            raise AuthenticationError(
                "Token cannot be empty or whitespace-only. "
                "Provide a valid authentication token."
            )
        self._token = token
        self._expected_key = expected_key

    def get_secret(self, key: str) -> str:
        """Retrieve a secret by key.

        Args:
            key: The secret key to retrieve

        Returns:
            The secret value if key matches expected_key

        Raises:
            KeyError: If key doesn't match expected_key
        """
        if key == self._expected_key:
            return self._token
        raise KeyError(f"Unknown secret key: {key}")
