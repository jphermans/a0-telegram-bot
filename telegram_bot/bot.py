"""Main Telegram bot application.

Entry point for the Telegram bot that interfaces with Agent Zero.
"""

import asyncio
import logging
import signal
import sys
from typing import Optional, NoReturn

from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.error import TelegramError, NetworkError, Conflict

from .config import get_config, Config
from .logging_config import setup_logging, get_logger, LogContext
from .handlers import get_handlers
from .auth import get_auth_manager
from .a0_client import get_client, close_client

logger = get_logger(__name__)


class TelegramBot:
    """Telegram bot that interfaces with Agent Zero."""
    
    def __init__(self, config: Optional[Config] = None):
        self._config = config or get_config()
        self._application: Optional[Application] = None
        self._running = False
        self._shutdown_event = asyncio.Event()
    
    def _setup_handlers(self) -> None:
        """Set up all command and message handlers."""
        handlers = get_handlers()
        
        # Command handlers
        self._application.add_handler(
            CommandHandler("start", handlers["start"])
        )
        self._application.add_handler(
            CommandHandler("help", handlers["help"])
        )
        self._application.add_handler(
            CommandHandler("status", handlers["status"])
        )
        self._application.add_handler(
            CommandHandler("tasks", handlers["tasks"])
        )
        self._application.add_handler(
            CommandHandler("cancel", handlers["cancel"])
        )
        self._application.add_handler(
            CommandHandler("reset", handlers["reset"])
        )
        
        # Message handler for text and other content
        self._application.add_handler(
            MessageHandler(filters.ALL & ~filters.COMMAND, handlers["message"])
        )
        
        logger.info("All handlers registered")
    
    def _setup_error_handler(self) -> None:
        """Set up global error handler."""
        async def error_handler(update, context) -> None:
            """Handle errors in the bot."""
            error = context.error
            
            if isinstance(error, Conflict):
                logger.error(
                    f"Bot conflict error (multiple instances?): {error}"
                )
                # Wait and retry
                await asyncio.sleep(5)
                return
            
            if isinstance(error, NetworkError):
                logger.error(f"Network error: {error}")
                return
            
            if isinstance(error, TelegramError):
                logger.error(f"Telegram error: {error}")
                return
            
            # Log unexpected errors
            logger.error(
                f"Unexpected error handling update {update}: {error}",
                exc_info=context.error
            )
            
            # Try to notify user if possible
            if update and update.effective_message:
                try:
                    await update.effective_message.reply_text(
                        "❌ An unexpected error occurred. Please try again."
                    )
                except:
                    pass
        
        self._application.add_error_handler(error_handler)
    
    async def initialize(self) -> None:
        """Initialize the bot."""
        with LogContext(logger, "initialize"):
            # Validate configuration
            warnings = self._config.validate()
            for warning in warnings:
                logger.warning(warning)
            
            # Log configuration info
            logger.info(
                f"Initializing bot with config: "
                f"endpoint={self._config.a0_endpoint}, "
                f"allowed_users={len(self._config.telegram_allowed_users)}"
            )
            
            # Create application
            self._application = (
                Application.builder()
                .token(self._config.telegram_bot_token)
                .read_timeout(self._config.poll_timeout)
                .write_timeout(self._config.poll_timeout)
                .connect_timeout(self._config.poll_timeout)
                .pool_timeout(self._config.poll_timeout)
                .build()
            )
            
            # Set up handlers
            self._setup_handlers()
            self._setup_error_handler()
            
            # Initialize A0 client
            client = await get_client()
            
            # Check A0 health
            is_healthy = await client.health_check()
            if is_healthy:
                logger.info("A0 health check passed")
            else:
                logger.warning(
                    "A0 health check failed - bot will continue but may not respond correctly"
                )
            
            logger.info("Bot initialization complete")
    
    async def start(self) -> None:
        """Start the bot with long polling."""
        if self._running:
            logger.warning("Bot is already running")
            return
        
        await self.initialize()
        self._running = True
        
        logger.info("Starting Telegram bot with long polling...")
        
        # Start polling
        await self._application.initialize()
        await self._application.start()
        
        # Start polling in the background
        await self._application.updater.start_polling(
            poll_interval=self._config.poll_interval,
            timeout=self._config.poll_timeout,
            drop_pending_updates=True,  # Don't process old messages on restart
            allowed_updates=["message", "edited_message", "callback_query"]
        )
        
        logger.info("Bot started successfully - waiting for messages...")
        
        # Wait for shutdown signal
        await self._shutdown_event.wait()
        
        # Graceful shutdown
        await self.stop()
    
    async def stop(self) -> None:
        """Stop the bot gracefully."""
        if not self._running:
            return
        
        logger.info("Stopping Telegram bot...")
        self._running = False
        
        try:
            # Stop updater
            if self._application.updater.running:
                await self._application.updater.stop()
            
            # Stop application
            await self._application.stop()
            await self._application.shutdown()
            
            # Close A0 client
            await close_client()
            
            logger.info("Bot stopped successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def request_shutdown(self) -> None:
        """Request a graceful shutdown."""
        logger.info("Shutdown requested")
        self._shutdown_event.set()
    
    async def run_forever(self) -> NoReturn:
        """Run the bot with automatic reconnection."""
        retry_count = 0
        max_retries = self._config.max_retries
        retry_delay = self._config.retry_delay
        
        while True:
            try:
                retry_count = 0  # Reset on successful start
                await self.start()
                
            except (NetworkError, TelegramError) as e:
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error(
                        f"Max retries ({max_retries}) exceeded. Exiting."
                    )
                    sys.exit(1)
                
                wait_time = retry_delay * (2 ** min(retry_count - 1, 5))  # Exponential backoff
                logger.error(
                    f"Bot error: {e}. Retrying in {wait_time}s "
                    f"(attempt {retry_count}/{max_retries})"
                )
                await asyncio.sleep(wait_time)
                
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                self.request_shutdown()
                break
                
            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                retry_count += 1
                if retry_count >= max_retries:
                    sys.exit(1)
                await asyncio.sleep(retry_delay)


def setup_signal_handlers(bot: TelegramBot) -> None:
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        bot.request_shutdown()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main() -> None:
    """Main entry point."""
    # Set up logging (use JSON output if configured)
    import os
    json_output = os.getenv("JSON_LOGS", "false").lower() == "true"
    setup_logging(json_output=json_output)
    
    logger.info("Starting Agent Zero Telegram Bot")
    
    # Create and run bot
    bot = TelegramBot()
    setup_signal_handlers(bot)
    
    await bot.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
