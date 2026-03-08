"""Telegram Bot for Agent Zero.

A Python-based Telegram interface that allows full bidirectional communication
with Agent Zero (A0) framework.

Usage:
    from telegram_bot import TelegramBot, Config
    
    config = Config.from_env()
    bot = TelegramBot(config)
    await bot.start()

Or run directly:
    python -m telegram_bot.bot
"""

from .config import Config, get_config, clear_config_cache
from .auth import AuthManager, AuthenticatedUser, get_auth_manager
from .a0_client import A0Client, A0Response, get_client, close_client
from .bot import TelegramBot, setup_signal_handlers
from .handlers import CommandHandlers, MessageHandler, get_handlers
from .logging_config import setup_logging, get_logger, LogContext

__version__ = "1.0.0"
__author__ = "Agent Zero Team"

__all__ = [
    # Configuration
    "Config",
    "get_config",
    "clear_config_cache",
    
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
    "setup_signal_handlers",
    
    # Handlers
    "CommandHandlers",
    "MessageHandler",
    "get_handlers",
    
    # Logging
    "setup_logging",
    "get_logger",
    "LogContext",
]
