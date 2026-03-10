"""Telegram bot command and message handlers.

Handles all incoming messages and commands from Telegram users.
"""

import logging
from typing import Optional, Dict, Any
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from .auth import AuthManager, AuthenticatedUser
from .a0_client import A0Client, A0Response
from .typing_indicator import TypingIndicator
from .project_discovery import get_project_discovery, Project

logger = logging.getLogger(__name__)


class CommandHandlers:
    """Handles Telegram bot commands."""
    
    def __init__(self, auth_manager: AuthManager, a0_client: A0Client):
        self.auth_manager = auth_manager
        self.a0_client = a0_client
        self._project_discovery = get_project_discovery()
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user = update.effective_user
        
        if not self.auth_manager.is_allowed(user.id):
            logger.warning(f"Unauthorized access attempt from user {user.id} (@{user.username})")
            await update.message.reply_text(
                "⛔ *Access Denied*\\n\\n"
                "You are not authorized to use this bot.\\n"
                "Please contact the administrator.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        auth_user = self.auth_manager.get_user(user.id)
        
        # Get current project info
        current_project = auth_user.current_project if auth_user else None
        project_info = ""
        if current_project:
            project = self._project_discovery.get_project_by_name(current_project)
            if project:
                project_info = f"\\n📁 *Project:* `{project.name}` ({project.title})"
        
        await update.message.reply_text(
            f"👋 *Welcome to A0 Telegram Bot!*\\n\\n"
            f"I'm your interface to Agent Zero.\\n{project_info}\\n\\n"
            "*Available Commands:*\\n"
            "• /help - Show usage instructions\\n"
            "• /status - Check A0 connection\\n"
            "• /projects - List available projects\\n"
            "• /project <name> - Select a project\\n"
            "• /newchat - Start new conversation\\n"
            "• /reset - Reset conversation context\\n"
            "• /cancel - Cancel pending operation\\n\\n"
            "Just send me a message to talk to A0! 🚀",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        user = update.effective_user
        
        if not self.auth_manager.is_allowed(user.id):
            return
        
        await update.message.reply_text(
            "📚 *A0 Telegram Bot Help*\\n\\n"
            "*What is this?*\\n"
            "This bot connects you to Agent Zero (A0), an AI assistant framework.\\n\\n"
            "*How to use:*\\n"
            "1. Send any message to chat with A0\\n"
            "2. Send documents/images for analysis\\n"
            "3. Use commands to manage your session\\n\\n"
            "*Commands:*\\n"
            "• /start - Initialize the bot\\n"
            "• /help - Show this help\\n"
            "• /status - Check A0 status and current context\\n"
            "• /projects - List all available A0 projects\\n"
            "• /project <name> - Switch to a project\\n"
            "• /newchat - Start a fresh conversation\\n"
            "• /reset - Reset the current context\\n"
            "• /cancel - Cancel any pending operation\\n\\n"
            "*Projects:*\\n"
            "Projects are discovered automatically from `/a0/usr/projects/`.\\n"
            "Select a project to work within its context.\\n\\n"
            "*Attachments:*\\n"
            "Send documents, images, or other files and A0 will analyze them.\\n\\n"
            "*Tips:*\\n"
            "• Type `/` to see the command menu\\n"
            "• Long messages are supported\\n"
            "• Use /reset if the conversation gets stuck",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        user = update.effective_user
        
        if not self.auth_manager.is_allowed(user.id):
            return
        
        auth_user = self.auth_manager.get_user(user.id)
        
        # Check A0 connection
        a0_status = "🔴 Disconnected"
        try:
            is_healthy = await self.a0_client.health_check()
            if is_healthy:
                a0_status = "🟢 Connected"
        except Exception as e:
            logger.error(f"Health check failed: {e}")
        
        # Get context info
        context_id = auth_user.context_id if auth_user else None
        context_info = f"`{context_id[:8]}...`" if context_id else "None"
        
        # Get project info
        current_project = auth_user.current_project if auth_user else None
        project_info = "None"
        if current_project:
            project = self._project_discovery.get_project_by_name(current_project)
            if project:
                project_info = f"`{project.name}` ({project.title})"
            else:
                project_info = f"`{current_project}`"
        
        await update.message.reply_text(
            f"🔍 *A0 Telegram Bot Status*\\n\\n"
            f"*A0 Connection:* {a0_status}\\n"
            f"*Context ID:* {context_info}\\n"
            f"*Current Project:* {project_info}\\n"
            f"*User:* {user.first_name} (@{user.username})\\n"
            f"*User ID:* `{user.id}`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def projects(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /projects command - list available projects dynamically."""
        user = update.effective_user
        
        if not self.auth_manager.is_allowed(user.id):
            return
        
        auth_user = self.auth_manager.get_user(user.id)
        current_project = auth_user.current_project if auth_user else None
        
        # Refresh project list
        projects = self._project_discovery.get_projects(refresh=True)
        
        if not projects:
            await update.message.reply_text(
                "📁 *No Projects Found*\\n\\n"
                "No A0 projects were found in `/a0/usr/projects/`.\\n\\n"
                "To create a project, use the A0 Web UI or create a folder with `.a0proj/project.json`.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Format project list
        lines = ["📁 *Available Projects*\\n"]
        
        for project in projects:
            marker = "✅ " if project.name == current_project else "• "
            title = project.title or project.name
            
            if project.description:
                desc_preview = project.description[:50] + "..." if len(project.description) > 50 else project.description
                lines.append(f"{marker}`{project.name}` - *{title}*\\n   _{desc_preview}_\\n")
            else:
                lines.append(f"{marker}`{project.name}` - *{title}*\\n")
        
        lines.append("\\n💡 Use `/project <name>` to select a project.")
        
        await update.message.reply_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def project(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /project command - select a project."""
        user = update.effective_user
        
        if not self.auth_manager.is_allowed(user.id):
            return
        
        # Get project name from command args
        if not context.args or len(context.args) == 0:
            await update.message.reply_text(
                "⚠️ *Usage:* `/project <name>`\\n\\n"
                "Use `/projects` to see available projects.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        project_name = context.args[0].strip()
        
        # Find project
        project = self._project_discovery.get_project_by_name(project_name)
        
        if not project:
            # List available projects
            available = ", ".join(f"`{p.name}`" for p in self._project_discovery.get_projects())
            await update.message.reply_text(
                f"❌ *Project not found:* `{project_name}`\\n\\n"
                f"Available projects: {available}",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Set project for user
        auth_user = self.auth_manager.get_user(user.id)
        if auth_user:
            auth_user.current_project = project.name
            # Clear context when changing project
            auth_user.context_id = None
        
        await update.message.reply_text(
            f"✅ *Project selected:* `{project.name}`\\n"
            f"*Title:* {project.title}\\n\\n"
            f"🔄 Previous conversation context cleared.\\n"
            f"Your next message will start a new chat in this project.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def newchat(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /newchat command - start a new conversation."""
        user = update.effective_user
        
        if not self.auth_manager.is_allowed(user.id):
            return
        
        auth_user = self.auth_manager.get_user(user.id)
        
        # Clear context
        if auth_user:
            auth_user.context_id = None
        
        current_project = auth_user.current_project if auth_user else None
        project_info = ""
        if current_project:
            project = self._project_discovery.get_project_by_name(current_project)
            if project:
                project_info = f"\\n📁 *Project:* `{project.name}` ({project.title})"
        
        await update.message.reply_text(
            f"🔄 *Starting a new conversation*{project_info}\\n\\n"
            "Your next message will start fresh!",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /reset command - reset conversation context."""
        user = update.effective_user
        
        if not self.auth_manager.is_allowed(user.id):
            return
        
        auth_user = self.auth_manager.get_user(user.id)
        
        # Clear context
        if auth_user:
            auth_user.context_id = None
        
        await update.message.reply_text(
            "🔄 *Context Reset*\\n\\n"
            "Conversation context has been cleared.\\n"
            "Your next message will start a new conversation.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /cancel command."""
        user = update.effective_user
        
        if not self.auth_manager.is_allowed(user.id):
            return
        
        # Cancel any pending operation
        await update.message.reply_text(
            "❌ *Cancelled*\\n\\n"
            "Any pending operation has been cancelled.",
            parse_mode=ParseMode.MARKDOWN
        )


class MessageHandler:
    """Handles regular messages sent to the bot."""
    
    def __init__(self, auth_manager: AuthManager, a0_client: A0Client):
        self.auth_manager = auth_manager
        self.a0_client = a0_client
        self.command_handlers: Dict[int, str] = {}  # chat_id -> context_id
        self._project_discovery = get_project_discovery()
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming messages."""
        user = update.effective_user
        message = update.message
        
        # Check authorization
        if not self.auth_manager.is_allowed(user.id):
            logger.warning(f"Unauthorized access attempt from user {user.id} (@{user.username}), attempt #1, message: {message.text[:20] if message.text else 'media'}...")
            await message.reply_text(
                "⛔ *Access Denied*\\n\\n"
                "You are not authorized to use this bot.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        auth_user = self.auth_manager.get_user(user.id)
        chat_id = message.chat_id
        
        # Get current context
        ctx_id = auth_user.context_id if auth_user else None
        current_project = auth_user.current_project if auth_user else None
        
        # Prepare message content
        message_text = message.text or message.caption or ""
        
        # Handle attachments
        attachments = []
        typing_action = "typing"
        
        if message.document:
            typing_action = "upload_document"
            file_data = await self._process_document(message.document)
            if file_data:
                attachments.append(file_data)
        
        if message.photo:
            typing_action = "upload_photo"
            photo = message.photo[-1]  # Get largest photo
            file_data = await self._process_photo(photo)
            if file_data:
                attachments.append(file_data)
        
        if message.video:
            typing_action = "upload_video"
            file_data = await self._process_video(message.video)
            if file_data:
                attachments.append(file_data)
        
        if message.voice:
            typing_action = "record_voice"
            file_data = await self._process_voice(message.voice)
            if file_data:
                attachments.append(file_data)
        
        # Start typing indicator
        typing_indicator = TypingIndicator(chat_id, context.bot, typing_action)
        await typing_indicator.start()
        
        try:
            # Send message to A0
            response = await self.a0_client.send_message(
                text=message_text,
                context_id=ctx_id,
                attachments=attachments if attachments else None,
                project=current_project
            )
            
            if response.success:
                # Store context ID
                if auth_user and response.context_id:
                    auth_user.context_id = response.context_id
                
                # Check for context not found error
                if self._is_context_not_found_error(response.response or ""):
                    logger.warning(f"Context {ctx_id} not found, creating new context")
                    if auth_user:
                        auth_user.context_id = None
                    
                    # Retry without context
                    response = await self.a0_client.send_message(
                        text=message_text,
                        context_id=None,
                        attachments=attachments if attachments else None,
                        project=current_project
                    )
                    
                    if response.success and auth_user and response.context_id:
                        auth_user.context_id = response.context_id
                        await message.reply_text(
                            "🔄 _Previous conversation context was lost (A0 may have restarted). "
                            "Starting a fresh conversation._",
                            parse_mode=ParseMode.MARKDOWN
                        )
                    else:
                        await message.reply_text(
                            f"❌ *Error*\\n\\n{response.error or 'Unknown error'}",
                            parse_mode=ParseMode.MARKDOWN
                        )
                        return
                
                # Send response
                await message.reply_text(
                    response.response or "No response from A0.",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await message.reply_text(
                    f"❌ *Error*\\n\\n{response.error or 'Unknown error'}",
                    parse_mode=ParseMode.MARKDOWN
                )
        finally:
            await typing_indicator.stop()
    
    def _is_context_not_found_error(self, error_str: str) -> bool:
        """Check if error is 'Context not found' error."""
        return "context not found" in error_str.lower() or "404" in error_str
    
    async def _process_document(self, document) -> Optional[Dict[str, Any]]:
        """Process a document attachment."""
        try:
            file = await document.get_file()
            file_bytes = await file.download_as_bytearray()
            
            import base64
            return {
                "filename": document.file_name or "document",
                "base64": base64.b64encode(bytes(file_bytes)).decode("utf-8")
            }
        except Exception as e:
            logger.error(f"Failed to process document: {e}")
            return None
    
    async def _process_photo(self, photo) -> Optional[Dict[str, Any]]:
        """Process a photo attachment."""
        try:
            file = await photo.get_file()
            file_bytes = await file.download_as_bytearray()
            
            import base64
            return {
                "filename": "photo.jpg",
                "base64": base64.b64encode(bytes(file_bytes)).decode("utf-8")
            }
        except Exception as e:
            logger.error(f"Failed to process photo: {e}")
            return None
    
    async def _process_video(self, video) -> Optional[Dict[str, Any]]:
        """Process a video attachment."""
        try:
            file = await video.get_file()
            file_bytes = await file.download_as_bytearray()
            
            import base64
            return {
                "filename": video.file_name or "video.mp4",
                "base64": base64.b64encode(bytes(file_bytes)).decode("utf-8")
            }
        except Exception as e:
            logger.error(f"Failed to process video: {e}")
            return None
    
    async def _process_voice(self, voice) -> Optional[Dict[str, Any]]:
        """Process a voice attachment."""
        try:
            file = await voice.get_file()
            file_bytes = await file.download_as_bytearray()
            
            import base64
            return {
                "filename": "voice.ogg",
                "base64": base64.b64encode(bytes(file_bytes)).decode("utf-8")
            }
        except Exception as e:
            logger.error(f"Failed to process voice: {e}")
            return None
    
    def clear_context_id(self, chat_id: int) -> None:
        """Clear context ID for a chat."""
        auth_user = self.auth_manager.get_user_by_chat_id(chat_id)
        if auth_user:
            auth_user.context_id = None
