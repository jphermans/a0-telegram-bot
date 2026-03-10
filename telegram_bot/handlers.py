"""Telegram bot command and message handlers."""

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
                "⛔ *Access Denied*\n\nYou are not authorized.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        await update.message.reply_text(
            "👋 *Welcome to A0 Telegram Bot!*\n\n"
            "I'm your interface to Agent Zero.\n\n"
            "*Commands:*\n"
            "• /help — Show usage\n"
            "• /status — Check connection\n"
            "• /projects — List projects\n"
            "• /project <name> — Select project\n"
            "• /newchat — Start fresh\n"
            "• /reset — Reset context\n\n"
            "💡 Send me a message to talk to A0!",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        user = update.effective_user
        
        if not self.auth_manager.is_allowed(user.id):
            return
        
        await update.message.reply_text(
            "📚 *A0 Telegram Bot Help*\n\n"
            "*Conversation*\n"
            "  /newchat — Start fresh\n"
            "  /reset — Reset context\n\n"
            "*Projects*\n"
            "  /projects — List projects\n"
            "  /project <name> — Select\n\n"
            "*System*\n"
            "  /status — Check connection\n"
            "  /cancel — Cancel\n\n"
            "Send documents/images for analysis.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        try:
            user = update.effective_user
            logger.info(f"Status command from user {user.id}")
            
            if not self.auth_manager.is_allowed(user.id):
                logger.warning(f"Unauthorized status check from {user.id}")
                await update.message.reply_text("⛔ Not authorized", parse_mode=ParseMode.MARKDOWN)
                return
            
            auth_user = self.auth_manager.get_user(user.id)
            
            a0_status = "🔴 Disconnected"
            try:
                is_healthy = await self.a0_client.health_check()
                if is_healthy:
                    a0_status = "🟢 Connected"
            except Exception as e:
                logger.error(f"Health check failed: {e}")
            
            context_id = auth_user.context_id if auth_user else None
            ctx_info = f"`{context_id[:8]}...`" if context_id else "None"
            
            current_project = auth_user.current_project if auth_user else None
            proj_info = f"`{current_project}`" if current_project else "None"
            
            await update.message.reply_text(
                f"🔍 *Status*\n\n"
                f"A0: {a0_status}\n"
                f"Context: {ctx_info}\n"
                f"Project: {proj_info}\n"
                f"User: {user.first_name}",
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info("Status response sent")
        except Exception as e:
            logger.error(f"Error in status handler: {e}")
            try:
                await update.message.reply_text(f"❌ Error: {e}")
            except:
                pass
    
    async def projects(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /projects command."""
        user = update.effective_user
        
        if not self.auth_manager.is_allowed(user.id):
            return
        
        auth_user = self.auth_manager.get_user(user.id)
        current = auth_user.current_project if auth_user else None
        
        projects = self._project_discovery.get_projects(refresh=True)
        
        if not projects:
            await update.message.reply_text(
                "📁 No projects found",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        lines = ["📁 *Projects*"]
        for p in projects:
            mark = "✅" if p.name == current else "📁"
            lines.append(f"{mark} `{p.name}` - {p.title}")
        lines.append("\n💡 Use `/project <name>` to select")
        
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    
    async def project(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /project command."""
        user = update.effective_user
        
        if not self.auth_manager.is_allowed(user.id):
            return
        
        if not context.args:
            await update.message.reply_text(
                "⚠️ Usage: `/project <name>`\nUse `/projects` to list",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        name = context.args[0].strip()
        proj = self._project_discovery.get_project_by_name(name)
        
        if not proj:
            await update.message.reply_text(
                f"❌ Project `{name}` not found",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        auth_user = self.auth_manager.get_user(user.id)
        if auth_user:
            auth_user.current_project = proj.name
            auth_user.context_id = None
        
        await update.message.reply_text(
            f"✅ Selected: `{proj.name}`\n{proj.title}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def newchat(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /newchat command."""
        user = update.effective_user
        
        if not self.auth_manager.is_allowed(user.id):
            return
        
        auth_user = self.auth_manager.get_user(user.id)
        if auth_user:
            auth_user.context_id = None
        
        await update.message.reply_text(
            "🔄 *New Chat*\nNext message starts fresh!",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /reset command."""
        user = update.effective_user
        
        if not self.auth_manager.is_allowed(user.id):
            return
        
        auth_user = self.auth_manager.get_user(user.id)
        if auth_user:
            auth_user.context_id = None
        
        await update.message.reply_text(
            "🔄 *Reset*\nContext cleared.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /cancel command."""
        user = update.effective_user
        
        if not self.auth_manager.is_allowed(user.id):
            return
        
        await update.message.reply_text("❌ Cancelled", parse_mode=ParseMode.MARKDOWN)


class BotMessageHandler:
    """Handles regular messages."""
    
    def __init__(self, auth_manager: AuthManager, a0_client: A0Client):
        self.auth_manager = auth_manager
        self.a0_client = a0_client
        self._project_discovery = get_project_discovery()
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming messages."""
        user = update.effective_user
        message = update.message
        
        if not self.auth_manager.is_allowed(user.id):
            await message.reply_text("⛔ Access Denied", parse_mode=ParseMode.MARKDOWN)
            return
        
        auth_user = self.auth_manager.get_user(user.id)
        chat_id = message.chat_id
        
        ctx_id = auth_user.context_id if auth_user else None
        proj = auth_user.current_project if auth_user else None
        
        text = message.text or message.caption or ""
        attachments = []
        action = "typing"
        
        if message.document:
            action = "upload_document"
            d = await self._process_document(message.document)
            if d: attachments.append(d)
        if message.photo:
            action = "upload_photo"
            d = await self._process_photo(message.photo[-1])
            if d: attachments.append(d)
        if message.video:
            action = "upload_video"
            d = await self._process_video(message.video)
            if d: attachments.append(d)
        if message.voice:
            action = "record_voice"
            d = await self._process_voice(message.voice)
            if d: attachments.append(d)
        
        indicator = TypingIndicator(chat_id, context.bot, action)
        await indicator.start()
        
        try:
            resp = await self.a0_client.send_message(
                text=text, context_id=ctx_id,
                attachments=attachments or None, project=proj
            )
            
            if resp.success:
                if auth_user and resp.context_id:
                    auth_user.context_id = resp.context_id
                
                if self._is_context_error(resp.response or ""):
                    if auth_user: auth_user.context_id = None
                    resp = await self.a0_client.send_message(
                        text=text, context_id=None,
                        attachments=attachments or None, project=proj
                    )
                    if resp.success and auth_user and resp.context_id:
                        auth_user.context_id = resp.context_id
                        await message.reply_text("🔄 Context lost. Fresh start.", parse_mode=ParseMode.MARKDOWN)
                
                await message.reply_text(resp.response or "No response.", parse_mode=ParseMode.MARKDOWN)
            else:
                await message.reply_text(f"❌ Error: {resp.error or 'Unknown'}", parse_mode=ParseMode.MARKDOWN)
        finally:
            await indicator.stop()
    
    def _is_context_error(self, s: str) -> bool:
        return "context not found" in s.lower() or "404" in s
    
    async def _process_document(self, doc):
        try:
            f = await doc.get_file()
            b = await f.download_as_bytearray()
            import base64
            return {"filename": doc.file_name or "doc", "base64": base64.b64encode(bytes(b)).decode()}
        except: return None
    
    async def _process_photo(self, photo):
        try:
            f = await photo.get_file()
            b = await f.download_as_bytearray()
            import base64
            return {"filename": "photo.jpg", "base64": base64.b64encode(bytes(b)).decode()}
        except: return None
    
    async def _process_video(self, video):
        try:
            f = await video.get_file()
            b = await f.download_as_bytearray()
            import base64
            return {"filename": video.file_name or "video.mp4", "base64": base64.b64encode(bytes(b)).decode()}
        except: return None
    
    async def _process_voice(self, voice):
        try:
            f = await voice.get_file()
            b = await f.download_as_bytearray()
            import base64
            return {"filename": "voice.ogg", "base64": base64.b64encode(bytes(b)).decode()}
        except: return None
    
    def clear_context_id(self, chat_id: int) -> None:
        u = self.auth_manager.get_user_by_chat_id(chat_id)
        if u: u.context_id = None
