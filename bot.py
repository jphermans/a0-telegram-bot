"""Main Telegram bot module.

Creates and runs the Telegram bot with all handlers.
"""

import asyncio
import logging
import os
from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from .config import get_config
from .auth import AuthManager
from .a0_client import A0Client
from .handlers import CommandHandlers, MessageHandler
from .logging_config import setup_logging

logger = logging.getLogger(__name__)


# Bot commands to register
BOT_COMMANDS = [
    BotCommand("start", "🚀 Start the bot"),
    BotCommand("help", "📚 Show help and usage"),
    BotCommand("status", "🔍 Check A0 connection status"),
    BotCommand("projects", "📁 List available projects"),
    BotCommand("project", "📂 Select a project"),
    BotCommand("newchat", "💬 Start new conversation"),
    BotCommand("reset", "🔄 Reset conversation context"),
    BotCommand("cancel", "❌ Cancel pending operation"),
]


def create_bot() -> Application:
    """Create and configure the Telegram bot application."""
    config = get_config()
    
    # Validate configuration
    if not config.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is required")
    
    if not config.allowed_users:
        logger.warning("No TELEGRAM_ALLOWED_USERS or TELEGRAM_USERID configured - bot will reject all users!")
    
    # Create auth manager
    auth_manager = AuthManager(
        allowed_users=config.allowed_users,
        admin_users=[]  # Add admin users if needed
    )
    
    # Create A0 client
    a0_client = A0Client(
        endpoint=config.a0_endpoint,
        api_key=config.a0_api_key,
        timeout=config.a0_timeout
    )
    
    # Create bot application
    application = Application.builder().token(config.telegram_bot_token).build()
    
    # Create handlers
    command_handlers = CommandHandlers(auth_manager, a0_client)
    message_handler = MessageHandler(auth_manager, a0_client)
    
    # Register command handlers
    application.add_handler(CommandHandler("start", command_handlers.start))
    application.add_handler(CommandHandler("help", command_handlers.help))
    application.add_handler(CommandHandler("status", command_handlers.status))
    application.add_handler(CommandHandler("projects", command_handlers.projects))
    application.add_handler(CommandHandler("project", command_handlers.project))
    application.add_handler(CommandHandler("newchat", command_handlers.newchat))
    application.add_handler(CommandHandler("reset", command_handlers.reset))
    application.add_handler(CommandHandler("cancel", command_handlers.cancel))
    
    # Register message handler for all other messages
    application.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO | filters.Document.ALL | filters.VIDEO | filters.VOICE,
        message_handler.handle_message
    ))
    
    logger.info("Bot created with handlers registered")
    
    return application


async def set_bot_commands(application: Application) -> None:
    """Set the bot command menu."""
    try:
        await application.bot.set_my_commands(BOT_COMMANDS)
        logger.info("Bot commands registered successfully")
    except Exception as e:
        logger.warning(f"Failed to register bot commands: {e}")


def run_bot() -> None:
    """Run the Telegram bot."""
    # Setup logging
    config = get_config()
    setup_logging(config.log_level)
    
    logger.info("Starting A0 Telegram Bot...")
    
    # Create bot
    application = create_bot()
    
    # Set commands on startup
    application.post_init = set_bot_commands
    
    # Run bot
    application.run_polling(
        allowed_updates=['message'],
        drop_pending_updates=True
    )


if __name__ == "__main__":
    run_bot()
