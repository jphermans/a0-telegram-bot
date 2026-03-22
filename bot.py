"""Main Telegram bot application."""

import logging
from telegram import BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from telegram import Update

from .config import get_config
from .auth import AuthManager
from .a0_client import A0Client
from .handlers import CommandHandlers, BotMessageHandler
from .logging_config import setup_logging
from .nextdns_a0_integration import get_nextdns_handlers, get_nextdns_callback_handler

logger = logging.getLogger(__name__)


# Bot commands to register
BOT_COMMANDS = [
    BotCommand("start", "Start the bot"),
    BotCommand("help", "Show help and usage"),
    BotCommand("status", "Check A0 connection status"),
    BotCommand("ping", "Quick connectivity test"),
    BotCommand("info", "Show session info (context, messages)"),
    BotCommand("version", "Show bot version info"),
    BotCommand("projects", "List available projects"),
    BotCommand("project", "Select a project"),
    BotCommand("newchat", "Start new conversation"),
    BotCommand("reset", "Reset conversation context"),
    BotCommand("menu", "Show interactive menu"),
    BotCommand("clear", "Clear chat history"),
    BotCommand("cancel", "Cancel pending operation"),
    # NextDNS commands
    BotCommand("nd_help", "NextDNS help"),
    BotCommand("nd_status", "NextDNS status"),
    BotCommand("nd_domains", "NextDNS top domains"),
    BotCommand("nd_devices", "NextDNS top devices"),
    BotCommand("nd_logs", "NextDNS DNS logs"),
    BotCommand("nd_block", "Block a domain"),
    BotCommand("nd_allow", "Allow a domain"),
    BotCommand("nd_list", "Show denylist"),
    BotCommand("nd_report", "NextDNS report"),
]




async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error handler for the bot."""
    logger.error(f"Exception while handling update: {context.error}")
    
    # Try to notify user if possible
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ *An error occurred*\n\n"
                "Something went wrong processing your request.\n"
                "Please try again or use /start to reset.",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")


def create_bot() -> Application:
    """Create and configure the Telegram bot application."""
    config = get_config()
    
    # Debug: Log configuration (partial values for security)
    logger.info(f"Config loaded:")
    logger.info(f"  A0_ENDPOINT: {config.a0_endpoint}")
    logger.info(f"  A0_API_KEY: {config.a0_api_key[:8] + '...' if config.a0_api_key and len(config.a0_api_key) > 8 else 'NOT SET or TOO SHORT'}")
    logger.info(f"  A0_TIMEOUT: {config.a0_timeout}")
    logger.info(f"  Allowed users count: {len(config.allowed_users)}")
    
    # Validate configuration
    if not config.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is required")
    if not config.a0_api_key:
        raise ValueError("A0_API_KEY is required")
    
    # Create auth manager
    auth_manager = AuthManager(config.allowed_users)
    
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
    message_handler = BotMessageHandler(auth_manager, a0_client)
    
    # Register command handlers
    application.add_handler(CommandHandler("start", command_handlers.start))
    application.add_handler(CommandHandler("help", command_handlers.help))
    application.add_handler(CommandHandler("status", command_handlers.status))
    application.add_handler(CommandHandler("ping", command_handlers.ping))
    application.add_handler(CommandHandler("info", command_handlers.info))
    application.add_handler(CommandHandler("version", command_handlers.version))
    application.add_handler(CommandHandler("clear", command_handlers.clear))
    application.add_handler(CommandHandler("projects", command_handlers.projects))
    application.add_handler(CommandHandler("project", command_handlers.project))
    application.add_handler(CommandHandler("newchat", command_handlers.newchat))
    application.add_handler(CommandHandler("reset", command_handlers.reset))
    application.add_handler(CommandHandler("menu", command_handlers.menu))
    application.add_handler(CommandHandler("cancel", command_handlers.cancel))
    
    # Register callback query handler for inline keyboards (bound to instance)
    application.add_handler(CallbackQueryHandler(command_handlers.handle_callback))
    
    # Register message handler for text and media
    
    # Register NextDNS handlers
    for cmd, handler in get_nextdns_handlers():
        application.add_handler(CommandHandler(cmd, handler))
    
    # Register NextDNS callback handler
    nd_callback = get_nextdns_callback_handler()
    if nd_callback:
        application.add_handler(CallbackQueryHandler(nd_callback, pattern="^nd:"))
    # Register message handler
    application.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO | filters.Document.ALL | filters.VIDEO | filters.VOICE,
        message_handler.handle_message
    ))
    
    # Set bot commands
    # Register global error handler
    application.add_error_handler(error_handler)
    
    application.post_init = _post_init
    
    return application


async def _post_init(application: Application) -> None:
    """Post-initialization hook to set bot commands."""
    await application.bot.set_my_commands(BOT_COMMANDS)


def run_bot() -> None:
    """Run the Telegram bot with auto-reconnection."""
    import asyncio
    import time as time_module
    
    setup_logging()
    
    logger.info("Starting A0 Telegram Bot...")
    
    max_retries = 10
    retry_delay = 5  # seconds between retries
    
    for attempt in range(max_retries):
        try:
            application = create_bot()
            
            logger.info(f"Bot configured, starting polling... (attempt {attempt + 1}/{max_retries})")
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,  # Don't process old messages on restart
                close_loop=False  # Allow reconnection
            )
            break  # Exit if successful
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
        except Exception as e:
            logger.error(f"Bot error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time_module.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)  # Exponential backoff, max 60s
            else:
                logger.error("Max retries reached, exiting")
                raise


if __name__ == "__main__":
    run_bot()
