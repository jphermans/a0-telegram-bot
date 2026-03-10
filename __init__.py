"""A0 Telegram Bot Package.

A Telegram bot interface for Agent Zero (A0).
"""

from .config import Config, get_config
from .auth import AuthManager, AuthenticatedUser
from .a0_client import A0Client, A0Response
from .handlers import CommandHandlers, BotMessageHandler
from .typing_indicator import TypingIndicator
from .project_discovery import ProjectDiscovery, Project, get_project_discovery

__all__ = [
    "Config",
    "get_config",
    "AuthManager",
    "AuthenticatedUser",
    "A0Client",
    "A0Response",
    "CommandHandlers",
    "BotMessageHandler",
    "TypingIndicator",
    "ProjectDiscovery",
    "Project",
    "get_project_discovery",
]

__version__ = "1.4.0"
