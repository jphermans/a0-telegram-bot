"""Main Telegram bot application.

Initializes and runs the Telegram bot with all handlers.
Includes command menu registration and project support.
"""

import asyncio
import logging
import signal
import sys

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.request import HTTPXRequest

from .config import get_config
from .handlers import get_handlers
from .logging_config import get_logger, setup_logging
from .a0_client import close_client

logger = get_logger(__name__)


# Bot command definitions for Telegram UI menu
BOT_COMMANDS = [
    ("start", "🚀 Start the bot and show welcome message"),
    ("help", "📚 Show help and usage instructions"),
    ("status", "🔍 Check A0 connection status"),
    ("reset", "🔄 Reset conversation context"),
    ("projects", "📁 List available projects"),
    ("project", "📂 Select a project: /project <name>"),
    ("newchat", "💬 Start a new chat in current project"),
    ("tasks", "📋 Show scheduled tasks"),
    ("cancel", "❌ Cancel any pending operation"),
]


class TelegramBot:
    """Telegram bot for A0 integration."""
    
    def __init__(self):
        self.config = get_config()
        self.application: Application = None
        self._shutdown_event = asyncio.Event()
        
    async def post_init(self, application: Application) -> None:
        """Post-initialization hook to set bot commands."""
        try:
            # Set bot commands for the Telegram UI menu
            await application.bot.set_my_commands(BOT_COMMANDS)
            logger.info(f"Set {len(BOT_COMMANDS)} bot commands in Telegram menu")
        except Exception as e:
            logger.error(f"Failed to set bot commands: {e}")
    
    def setup_handlers(self) -> None:
        """Set up all command and message handlers."""
        handlers = get_handlers()
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", handlers["start"]))
        self.application.add_handler(CommandHandler("help", handlers["help"]))
        self.application.add_handler(CommandHandler("status", handlers["status"]))
        self.application.add_handler(CommandHandler("reset", handlers["reset"]))
        self.application.add_handler(CommandHandler("projects", handlers["projects"]))
        self.application.add_handler(CommandHandler("project", handlers["project"]))
        self.application.add_handler(CommandHandler("newchat", handlers["newchat"]))
        self.application.add_handler(CommandHandler("tasks", handlers["tasks"]))
        self.application.add_handler(CommandHandler("cancel", handlers["cancel"]))
        
        # Message handler for text and other content
        self.application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handlers["message"]))
        
        logger.info("All handlers registered")
    
    def setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self._shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run(self) -> None:
        """Run the bot."""
        setup_logging(self.config.log_level)
        
        logger.info("Starting A0 Telegram Bot...")
        logger.info(f"A0 Endpoint: {self.config.a0_endpoint}")
        logger.info(f"Allowed users: {self.config.allowed_users}")
        logger.info(f"Available projects: {self.config.projects}")
        
        if not self.config.telegram_bot_token:
            logger.error("TELEGRAM_BOT_TOKEN is not set!")
            sys.exit(1)
        
        # Configure request with larger timeout for file uploads
        request = HTTPXRequest(
            connect_timeout=30.0,
            read_timeout=60.0,
            write_timeout=60.0,
            pool_timeout=30.0
        )
        
        # Create application
        self.application = Application.builder()
        self.application = self.application.token(self.config.telegram_bot_token)
        self.application = self.application.request(request)
        self.application = self.application.post_init(self.post_init)
        self.application = self.application.build()
        
        # Set up handlers
        self.setup_handlers()
        
        # Set up signal handlers
        self.setup_signal_handlers()
        
        # Run the bot
        logger.info("Bot starting - polling for updates...")
        
        async with self.application:
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            
            # Wait for shutdown signal
            await self._shutdown_event.wait()
            
            # Graceful shutdown
            logger.info("Shutting down bot...")
            await self.application.updater.stop()
            await self.application.stop()
            await close_client()
            logger.info("Bot shutdown complete")


def main():
    """Main entry point."""
    bot = TelegramBot()
    asyncio.run(bot.run())


if __name__ == "__main__":
    main()
