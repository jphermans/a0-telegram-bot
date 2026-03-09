"""Telegram Bot for Agent Zero.

A Python-based Telegram interface that allows full bidirectional communication
with Agent Zero (A0) framework.

Usage:
    from telegram_bot import Config, get_config
    
    config = get_config()
    
Or run directly:
    python -m telegram_bot.bot
"""

from .config import Config, get_config
from .auth import AuthManager, AuthenticatedUser, get_auth_manager
from .a0_client import A0Client, A0Response, get_client, close_client
from .bot import TelegramBot
from .handlers import CommandHandlers, MessageHandler, get_handlers
from .logging_config import setup_logging, get_logger, LogContext

__version__ = "1.3.0"
__author__ = "Agent Zero Team"

__all__ = [
    # Configuration
    "Config",
    "get_config",
    
    # Authentication
    "AuthManager",
    "AuthenticatedUser",
    "get_auth_manager",
    
    # A0 Client
    "A0Client",
    "A0Response",
    "get_client",
    "close_client",
    
    # Bot
    "TelegramBot",
    
    # Handlers
    "CommandHandlers",
    "MessageHandler",
    "get_handlers",
    
    # Logging
    "setup_logging",
    "get_logger",
    "LogContext",
]
