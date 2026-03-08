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


def get_user_friendly_error(error: Exception, context: str = "") -> str:
    """Convert technical errors to user-friendly messages.
    
    Args:
        error: The exception that occurred
        context: Context about what operation was happening
    
    Returns:
        User-friendly error message
    """
    error_str = str(error).lower()
    error_type = type(error).__name__
    
    # Connection errors
    if any(x in error_str for x in ["connection", "connect", "network", "timeout", "timed out"]):
        return (
            "⚠️ **Connection Issue**\n\n"
            "I couldn't reach Agent Zero. This might be because:\n"
            "• A0 is starting up or restarting\n"
            "• Network connectivity issue\n"
            "• A0 is processing a heavy task\n\n"
            "Please try again in a moment. If the problem persists, check the A0 status with /status"
        )
    
    # Authentication errors
    if any(x in error_str for x in ["401", "unauthorized", "authentication", "api key"]):
        return (
            "🔐 **Authentication Error**\n\n"
            "The A0 API key may be missing or invalid.\n"
            "Please contact the administrator to verify the API configuration."
        )
    
    # Rate limiting
    if any(x in error_str for x in ["429", "rate limit", "too many"]):
        return (
            "⏳ **Rate Limited**\n\n"
            "Too many requests. Please wait a moment before trying again."
        )
    
    # Server errors
    if any(x in error_str for x in ["500", "502", "503", "504", "server error", "internal error"]):
        return (
            "🔧 **Server Error**\n\n"
            "Agent Zero encountered an internal error.\n"
            "Please try again. If this persists, the A0 service may need attention."
        )
    
    # File/attachment errors
    if any(x in error_str for x in ["file", "attachment", "upload", "too large"]):
        return (
            "📎 **File Error**\n\n"
            f"There was an issue with your file.\n"
            "Please check the file size (max 20MB) and format."
        )
    
    # JSON parsing errors
    if "json" in error_str or "parse" in error_str:
        return (
            "⚠️ **Response Error**\n\n"
            "Received an unexpected response from Agent Zero.\n"
            "Please try again or use /reset to start a fresh conversation."
        )
    
    # Generic fallback with helpful suggestions
    return (
        f"⚠️ **Something went wrong**\n\n"
        f"An unexpected error occurred{f' during {context}' if context else ''}.\n"
        f"Please try again. If the problem persists:\n"
        f"• Use /reset to start fresh\n"
        f"• Use /status to check A0 connection\n\n"
        f"_Error type: {error_type}_"
    )


def split_message(text: str) -> list[str]:
    """Split a message into chunks that respect Telegram's 4096 character limit.
    
    Tries to split at word boundaries when possible.
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
        
        hard_split = min(chunk_limit, len(remaining))
        search_area = remaining[:hard_split]
        
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
    """Send a message that may need to be split into chunks."""
    chunks = split_message(text)
    messages = []
    
    for i, chunk in enumerate(chunks):
        if i > 0:
            await asyncio.sleep(delay)
        msg = await update.message.reply_text(chunk, parse_mode=parse_mode)
        messages.append(msg)
    
    return messages


class CommandHandlers:
    """Handles Telegram commands."""
    
    def __init__(self):
        self.auth = get_auth_manager()
        self.config = get_config()
        self._chat_contexts: Dict[int, str] = {}
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user = self.auth.authenticate(update)
        if not user:
            await update.message.reply_text("⛔ Unauthorized. You are not allowed to use this bot.")
            return
        
        welcome_msg = (
            f"👋 Hello {user.display_name}!\n\n"
            f"I'm the Agent Zero (A0) Telegram interface.\n\n"
            f"📋 **Commands:**\n"
            f"/start - Show welcome\n"
            f"/help - Get help\n"
            f"/status - Check connection\n"
            f"/reset - Reset conversation\n\n"
            f"💬 Send me a message or file and I'll forward it to A0!"
        )
        await update.message.reply_text(welcome_msg, parse_mode=ParseMode.MARKDOWN)
        
        logger.info(f"User started bot: {user.user_id}")
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        user = self.auth.authenticate(update)
        if not user:
            return
        
        help_msg = (
            "📚 **Agent Zero Telegram Help**\n\n"
            "**Commands:**\n"
            "/start - Initialize bot\n"
            "/help - Show this help\n"
            "/status - Check A0 connection\n"
            "/reset - Reset conversation\n\n"
            "**Usage:**\n"
            "Send text or files to interact with A0.\n\n"
            "**Tips:**\n"
            "• Use /reset if responses seem off\n"
            "• Use /status to check connection\n"
            "• Long responses are split automatically"
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
                    f"🌐 Endpoint: {self.config.a0_endpoint}"
                )
            else:
                status_msg = (
                    "❌ **A0 Status**\n\n"
                    f"🔴 Connection: Unhealthy\n"
                    f"⚠️ A0 is not responding"
                )
            await update.message.reply_text(status_msg, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            error_msg = get_user_friendly_error(e, "status check")
            await update.message.reply_text(error_msg, parse_mode=ParseMode.MARKDOWN)
    
    async def tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /tasks command."""
        user = self.auth.authenticate(update)
        if not user:
            return
        
        tasks_msg = (
            "📋 **Scheduled Tasks**\n\n"
            "No scheduled tasks available.\n"
            "Tasks can be managed through the A0 web interface."
        )
        await update.message.reply_text(tasks_msg, parse_mode=ParseMode.MARKDOWN)
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /cancel command."""
        user = self.auth.authenticate(update)
        if not user:
            return
        
        chat_id = update.effective_chat.id
        if chat_id in context.chat_data:
            context.chat_data.clear()
        
        await update.message.reply_text("✅ Any pending operation has been cancelled.")
        logger.info(f"User cancelled operation: {user.user_id}")
    
    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /reset command."""
        user = self.auth.authenticate(update)
        if not user:
            return
        
        chat_id = update.effective_chat.id
        
        if chat_id in self._chat_contexts:
            del self._chat_contexts[chat_id]
        if chat_id in context.chat_data:
            context.chat_data.clear()
        
        await update.message.reply_text(
            "🔄 Conversation reset.\n"
            "Starting fresh with A0."
        )
        logger.info(f"User reset context: {user.user_id}")


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
            await self.handle_non_text(update, context)
            return
        
        chat_id = update.effective_chat.id
        ctx_id = self.command_handlers._chat_contexts.get(chat_id)
        
        await update.message.chat.send_action("typing")
        
        try:
            client = await get_client()
            response = await client.send_message(text=message_text, context_id=ctx_id)
            
            if response.success:
                if response.context_id:
                    self.command_handlers._chat_contexts[chat_id] = response.context_id
                
                if response.message:
                    await send_chunked_message(update, response.message)
                else:
                    await update.message.reply_text("✅ Message processed.")
            else:
                error_msg = response.error or "Unknown error"
                await update.message.reply_text(
                    f"⚠️ **Error**\n\n{error_msg}",
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Failed to process message: {e}", exc_info=True)
            error_msg = get_user_friendly_error(e, "message processing")
            await update.message.reply_text(error_msg, parse_mode=ParseMode.MARKDOWN)
    
    async def handle_non_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle non-text messages (photos, documents, etc.)."""
        user = self.auth.authenticate(update)
        if not user:
            return
        
        message = update.message
        attachment_paths = []
        caption = message.caption or ""
        
        try:
            if message.photo:
                photo = message.photo[-1]
                file = await photo.get_file()
                file_path = f"/tmp/telegram_{photo.file_id}.jpg"
                await file.download_to_drive(file_path)
                attachment_paths.append(file_path)
                logger.info(f"Downloaded photo: {file_path}")
                
            if message.document:
                document = message.document
                if document.file_size and document.file_size > self.config.max_attachment_size:
                    await update.message.reply_text(
                        f"❌ File too large. Max: {self.config.max_attachment_size // (1024*1024)}MB"
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
                        f"❌ Video too large. Max: {self.config.max_attachment_size // (1024*1024)}MB"
                    )
                    return
                file = await video.get_file()
                file_path = f"/tmp/telegram_{video.file_id}_{video.file_name or 'video.mp4'}"
                await file.download_to_drive(file_path)
                attachment_paths.append(file_path)
                logger.info(f"Downloaded video: {file_path}")
            
            if not attachment_paths:
                await update.message.reply_text(
                    "❓ I can't handle this message type.\n"
                    "Please send text, photos, documents, voice, or videos."
                )
                return
            
            chat_id = update.effective_chat.id
            ctx_id = self.command_handlers._chat_contexts.get(chat_id)
            
            await update.message.chat.send_action("upload_document")
            
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
                error_msg = response.error or "Unknown error"
                await update.message.reply_text(
                    f"⚠️ **Error**\n\n{error_msg}",
                    parse_mode=ParseMode.MARKDOWN
                )
            
        except Exception as e:
            logger.error(f"Failed to handle attachment: {e}", exc_info=True)
            error_msg = get_user_friendly_error(e, "attachment processing")
            await update.message.reply_text(error_msg, parse_mode=ParseMode.MARKDOWN)
        finally:
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
