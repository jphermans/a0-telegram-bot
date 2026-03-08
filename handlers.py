"""Telegram command and message handlers.

Handles all incoming Telegram commands and messages.
"""

import asyncio
import logging
from typing import Optional, Dict, Any

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from .auth import get_auth_manager, AuthenticatedUser
from .a0_client import get_client, A0Response
from .config import get_config
from .logging_config import get_logger, LogContext

logger = get_logger(__name__)

# Constants for message handling
MAX_MESSAGE_LENGTH = 4096  # Telegram's message limit
CONTINUATION_OVERHEAD = 30  # Space for continuation markers


def split_message(text: str) -> list[str]:
    """Split a message into chunks that respect Telegram's 4096 character limit.
    
    Tries to split at word boundaries when possible.
    
    Args:
        text: The text to split
    
    Returns:
        List of message chunks
    """
    if len(text) <= MAX_MESSAGE_LENGTH:
        return [text]
    
    chunks = []
    remaining = text
    chunk_limit = MAX_MESSAGE_LENGTH - CONTINUATION_OVERHEAD
    
    while remaining:
        if len(remaining) <= MAX_MESSAGE_LENGTH:
            chunks.append(remaining)
            break
        
        # Find a good break point
        hard_split = min(chunk_limit, len(remaining))
        search_area = remaining[:hard_split]
        
        # Prefer newline, then space
        if '\n' in search_area:
            pos = search_area.rfind('\n')
            if pos >= chunk_limit // 2:
                chunk_end = pos + 1
            else:
                chunk_end = (search_area.rfind(' ') + 1) if ' ' in search_area else hard_split
        elif ' ' in search_area:
            chunk_end = search_area.rfind(' ') + 1
        else:
            chunk_end = hard_split
        
        if chunk_end == 0:
            chunk_end = hard_split
        
        chunk = remaining[:chunk_end].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[chunk_end:].strip()
    
    # Add continuation markers if needed
    if len(chunks) > 1:
        for i, chunk in enumerate(chunks):
            if i == 0:
                chunks[i] = chunk + "\n\n(continues...)"
            elif i == len(chunks) - 1:
                chunks[i] = "(continued)\n\n" + chunk
            else:
                chunks[i] = "(continued)\n\n" + chunk + "\n\n(continues...)"
    
    return chunks


async def send_chunked_message(
    update: Update,
    text: str,
    parse_mode: Optional[str] = None,
    delay: float = 0.5
) -> list:
    """Send a message that may need to be split into chunks.
    
    Args:
        update: Telegram update
        text: Text to send
        parse_mode: Optional parse mode (HTML, Markdown, etc.)
        delay: Delay between chunks in seconds
    
    Returns:
        List of sent messages
    """
    chunks = split_message(text)
    messages = []
    
    for i, chunk in enumerate(chunks):
        if i > 0:
            await asyncio.sleep(delay)
        
        msg = await update.message.reply_text(
            chunk,
            parse_mode=parse_mode
        )
        messages.append(msg)
    
    return messages


class CommandHandlers:
    """Handles Telegram commands."""
    
    def __init__(self):
        self.auth = get_auth_manager()
        self.config = get_config()
        # Store context IDs per chat
        self._chat_contexts: Dict[int, str] = {}
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user = self.auth.authenticate(update)
        if not user:
            await update.message.reply_text(
                "⛔ Unauthorized. You are not allowed to use this bot."
            )
            return
        
        welcome_msg = (
            f"👋 Hello {user.display_name}!\n\n"
            f"I'm the Agent Zero (A0) Telegram interface. "
            f"I can help you interact with A0 remotely.\n\n"
            f"📋 Available commands:\n"
            f"/start - Show this welcome message\n"
            f"/help - Get help and usage instructions\n"
            f"/status - Check A0 connection status\n"
            f"/tasks - List scheduled tasks\n"
            f"/cancel - Cancel current operation\n"
            f"/reset - Reset conversation context\n\n"
            f"💬 You can also just send me a message and I'll forward it to A0!"
        )
        
        await update.message.reply_text(welcome_msg)
        
        logger.info(
            f"User started bot: {user.user_id}",
            extra={"user_id": user.user_id, "event": "start_command"}
        )
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        user = self.auth.authenticate(update)
        if not user:
            return
        
        help_msg = (
            "📚 **Agent Zero Telegram Help**\n\n"
            "**Commands:**\n"
            "/start - Initialize bot and show welcome\n"
            "/help - Show this help message\n"
            "/status - Check A0 connection status\n"
            "/tasks - List scheduled tasks\n"
            "/cancel - Cancel current operation\n"
            "/reset - Reset conversation context\n\n"
            "**Usage:**\n"
            "Simply send any text message to interact with A0. "
            "Your message will be forwarded to the agent and you'll receive a response.\n\n"
            "**Attachments:**\n"
            "You can send documents, photos, and other files. "
            "They will be forwarded to A0 for processing.\n\n"
            "**Tips:**\n"
            "• Be specific in your requests\n"
            "• Use /reset to start a fresh conversation\n"
            "• Long responses are automatically split into multiple messages"
        )
        
        await update.message.reply_text(help_msg, parse_mode=ParseMode.MARKDOWN)
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        user = self.auth.authenticate(update)
        if not user:
            return
        
        await update.message.reply_text("🔍 Checking A0 status...")
        
        try:
            client = await get_client()
            is_healthy = await client.health_check()
            
            if is_healthy:
                status_msg = (
                    "✅ **A0 Status**\n\n"
                    f"🟢 Connection: Healthy\n"
                    f"🌐 Endpoint: {self.config.a0_endpoint}\n"
                    f"⏱️ Timeout: {self.config.a0_timeout}s"
                )
            else:
                status_msg = (
                    "❌ **A0 Status**\n\n"
                    f"🔴 Connection: Unhealthy\n"
                    f"🌐 Endpoint: {self.config.a0_endpoint}\n"
                    f"⚠️ A0 is not responding"
                )
            
            await update.message.reply_text(status_msg, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            await update.message.reply_text(
                f"❌ Failed to check status: {str(e)}"
            )
    
    async def tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /tasks command."""
        user = self.auth.authenticate(update)
        if not user:
            return
        
        # This would query A0 for scheduled tasks
        # For now, return a placeholder
        tasks_msg = (
            "📋 **Scheduled Tasks**\n\n"
            "No scheduled tasks available.\n"
            "Tasks can be managed through the A0 web interface or API."
        )
        
        await update.message.reply_text(tasks_msg, parse_mode=ParseMode.MARKDOWN)
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /cancel command."""
        user = self.auth.authenticate(update)
        if not user:
            return
        
        # Cancel any pending operation
        chat_id = update.effective_chat.id
        
        # Clear any pending state
        if chat_id in context.chat_data:
            context.chat_data.clear()
        
        await update.message.reply_text(
            "✅ Any pending operation has been cancelled."
        )
        
        logger.info(
            f"User cancelled operation: {user.user_id}",
            extra={"user_id": user.user_id, "event": "cancel_command"}
        )
    
    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /reset command to start a new conversation."""
        user = self.auth.authenticate(update)
        if not user:
            return
        
        chat_id = update.effective_chat.id
        
        # Clear the stored context ID
        if chat_id in self._chat_contexts:
            del self._chat_contexts[chat_id]
        
        # Clear chat data
        if chat_id in context.chat_data:
            context.chat_data.clear()
        
        await update.message.reply_text(
            "🔄 Conversation context has been reset.\n"
            "Starting a fresh conversation with A0."
        )
        
        logger.info(
            f"User reset context: {user.user_id}",
            extra={"user_id": user.user_id, "event": "reset_command"}
        )


class MessageHandler:
    """Handles regular Telegram messages."""
    
    def __init__(self):
        self.auth = get_auth_manager()
        self.config = get_config()
        self.command_handlers = CommandHandlers()
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming text messages."""
        user = self.auth.authenticate(update)
        if not user:
            return
        
        message_text = update.message.text
        if not message_text:
            # Handle other message types
            await self.handle_non_text(update, context)
            return
        
        chat_id = update.effective_chat.id
        
        with LogContext(
            logger,
            "handle_message",
            user_id=user.user_id,
            chat_id=chat_id,
            message_length=len(message_text)
        ):
            # Get or create context ID for this chat
            ctx_id = self.command_handlers._chat_contexts.get(chat_id)
            
            # Send "typing" action
            await update.message.chat.send_action("typing")
            
            try:
                client = await get_client()
                response = await client.send_message(
                    text=message_text,
                    context_id=ctx_id
                )
                
                if response.success:
                    # Store the context ID for future messages
                    if response.context_id:
                        self.command_handlers._chat_contexts[chat_id] = response.context_id
                    
                    # Send the response (may be chunked)
                    if response.message:
                        await send_chunked_message(update, response.message)
                    else:
                        await update.message.reply_text(
                            "✅ Message processed, but no response content."
                        )
                else:
                    error_msg = response.error or "Unknown error occurred"
                    await update.message.reply_text(
                        f"❌ Error: {error_msg}"
                    )
                    
            except Exception as e:
                logger.error(f"Failed to process message: {e}", exc_info=True)
                await update.message.reply_text(
                    f"❌ Failed to communicate with A0: {str(e)}"
                )
    
    async def handle_non_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle non-text messages (photos, documents, etc.)."""
        user = self.auth.authenticate(update)
        if not user:
            return
        
        message = update.message
        attachment_paths = []
        caption = message.caption or ""
        
        try:
            # Download and process attachments
            if message.photo:
                # Get the largest photo
                photo = message.photo[-1]
                file = await photo.get_file()
                file_path = f"/tmp/telegram_{photo.file_id}.jpg"
                await file.download_to_drive(file_path)
                attachment_paths.append(file_path)
                logger.info(f"Downloaded photo: {file_path}")
                
            if message.document:
                document = message.document
                # Check file size
                if document.file_size and document.file_size > self.config.max_attachment_size:
                    await update.message.reply_text(
                        f"❌ File too large. Maximum size: {self.config.max_attachment_size // (1024*1024)}MB"
                    )
                    return
                
                file = await document.get_file()
                file_path = f"/tmp/telegram_{document.file_id}_{document.file_name}"
                await file.download_to_drive(file_path)
                attachment_paths.append(file_path)
                logger.info(f"Downloaded document: {file_path}")
            
            if message.voice:
                voice = message.voice
                file = await voice.get_file()
                file_path = f"/tmp/telegram_{voice.file_id}.ogg"
                await file.download_to_drive(file_path)
                attachment_paths.append(file_path)
                logger.info(f"Downloaded voice: {file_path}")
            
            if message.video:
                video = message.video
                if video.file_size and video.file_size > self.config.max_attachment_size:
                    await update.message.reply_text(
                        f"❌ Video too large. Maximum size: {self.config.max_attachment_size // (1024*1024)}MB"
                    )
                    return
                
                file = await video.get_file()
                file_path = f"/tmp/telegram_{video.file_id}_{video.file_name or 'video.mp4'}"
                await file.download_to_drive(file_path)
                attachment_paths.append(file_path)
                logger.info(f"Downloaded video: {file_path}")
            
            if not attachment_paths:
                await update.message.reply_text(
                    "❓ I don't know how to handle this type of message. "
                    "Please send text, photos, documents, voice messages, or videos."
                )
                return
            
            # Forward to A0 with attachments
            chat_id = update.effective_chat.id
            ctx_id = self.command_handlers._chat_contexts.get(chat_id)
            
            await update.message.chat.send_action("typing")
            
            client = await get_client()
            response = await client.send_message(
                text=caption or "[Attachment received]",
                context_id=ctx_id,
                attachments=attachment_paths
            )
            
            if response.success:
                if response.context_id:
                    self.command_handlers._chat_contexts[chat_id] = response.context_id
                
                if response.message:
                    await send_chunked_message(update, response.message)
                else:
                    await update.message.reply_text("✅ Attachment processed.")
            else:
                await update.message.reply_text(
                    f"❌ Error processing attachment: {response.error}"
                )
            
        except Exception as e:
            logger.error(f"Failed to handle attachment: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ Failed to process attachment: {str(e)}"
            )
        finally:
            # Clean up downloaded files
            for path in attachment_paths:
                try:
                    import os
                    os.remove(path)
                except:
                    pass


def get_handlers():
    """Get all command and message handlers."""
    commands = CommandHandlers()
    messages = MessageHandler()
    
    return {
        "start": commands.start,
        "help": commands.help,
        "status": commands.status,
        "tasks": commands.tasks,
        "cancel": commands.cancel,
        "reset": commands.reset,
        "message": messages.handle_message,
    }
