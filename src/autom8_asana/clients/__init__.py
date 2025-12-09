"""Resource client implementations.

Per TDD-0003: Tier 1 resource clients for autom8 parity.
Per TDD-0004: Tier 2 resource clients (Webhooks, Teams, Attachments, Tags, Goals, Portfolios, Stories).
"""

from autom8_asana.clients.attachments import AttachmentsClient
from autom8_asana.clients.base import BaseClient
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

__all__ = [
    # Base
    "BaseClient",
    # Tier 1 clients
    "CustomFieldsClient",
    "ProjectsClient",
    "SectionsClient",
    "TasksClient",
    "UsersClient",
    "WorkspacesClient",
    # Tier 2 clients
    "AttachmentsClient",
    "GoalsClient",
    "PortfoliosClient",
    "StoriesClient",
    "TagsClient",
    "TeamsClient",
    "WebhooksClient",
]
