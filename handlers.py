"""Telegram bot command and message handlers."""

import logging
from typing import Optional, Dict, Any, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CallbackQueryHandler

from .auth import AuthManager, AuthenticatedUser
from .a0_client import A0Client, A0Response
from .typing_indicator import TypingIndicator
from .project_discovery import get_project_discovery, Project

logger = logging.getLogger(__name__)

SEP = "───────────────"

# Callback data prefixes
CALLBACK_PROJECT = "proj:"
CALLBACK_NEWCHAT = "newchat"
CALLBACK_RESET = "reset"
CALLBACK_STATUS = "status"
CALLBACK_MENU = "menu"
CALLBACK_MEMORY = "mem:"
CALLBACK_MEMORY_SEARCH = "mem_search:"
CALLBACK_MEMORY_LIST = "mem_list:"
CALLBACK_MEMORY_DELETE = "mem_del:"
CALLBACK_MEMORY_SUBDIR = "mem_subdir:"


class CommandHandlers:
    def __init__(self, auth_manager: AuthManager, a0_client: A0Client):
        self.auth_manager = auth_manager
        self.a0_client = a0_client
        self._project_discovery = get_project_discovery()
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not self.auth_manager.is_allowed(user.id):
            await update.message.reply_text("⛔ *Access Denied*", parse_mode=ParseMode.MARKDOWN)
            return
        auth_user = self.auth_manager.get_user(user.id)
        current_project = auth_user.current_project if auth_user else None
        project_info = f"\n📁 Project: `{current_project}`" if current_project else ""
        keyboard = [
            [InlineKeyboardButton("📁 Projects", callback_data=CALLBACK_MENU+"projects"), InlineKeyboardButton("📊 Status", callback_data=CALLBACK_STATUS)],
            [InlineKeyboardButton("🧠 Memory", callback_data=CALLBACK_MEMORY+"menu"), InlineKeyboardButton("🔄 New Chat", callback_data=CALLBACK_NEWCHAT)],
            [InlineKeyboardButton("❓ Help", callback_data=CALLBACK_MENU+"help")]
        ]
        await update.message.reply_text(f"👋 *Welcome to A0 Telegram Bot!*{project_info}\n\n💡 Use buttons or send a message!", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.auth_manager.is_allowed(update.effective_user.id): return
        keyboard = [[InlineKeyboardButton("🧠 Memory", callback_data=CALLBACK_MEMORY+"menu")], [InlineKeyboardButton("🏠 Menu", callback_data=CALLBACK_MENU+"main")]]
        await update.message.reply_text("📚 *Help*\n\n*Conversation*\n• /newchat — Fresh conversation\n• /reset — Reset context\n\n*Projects*\n• /projects — List projects\n• /project <name> — Select\n\n*Memory*\n• /memory — Memory menu\n• /memory search <q> — Search\n• /memory list — List all\n\n*System*\n• /status — Connection\n• /menu — Main menu", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not self.auth_manager.is_allowed(user.id): return
        auth_user = self.auth_manager.get_user(user.id)
        a0_status = "🟢 Connected" if await self.a0_client.health_check() else "🔴 Disconnected"
        ctx = f"`{auth_user.context_id[:8]}...`" if auth_user and auth_user.context_id else "None"
        proj = f"`{auth_user.current_project}`" if auth_user and auth_user.current_project else "None"
        keyboard = [[InlineKeyboardButton("🧠 Memory", callback_data=CALLBACK_MEMORY+"menu")], [InlineKeyboardButton("🔄 New Chat", callback_data=CALLBACK_NEWCHAT)]]
        await update.message.reply_text(f"🔍 *Status*\n\nA0: {a0_status}\nContext: {ctx}\nProject: {proj}", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def projects(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.auth_manager.is_allowed(update.effective_user.id): return
        auth_user = self.auth_manager.get_user(update.effective_user.id)
        current = auth_user.current_project if auth_user else None
        projects = self._project_discovery.get_projects(refresh=True)
        if not projects:
            await update.message.reply_text("📁 No projects", parse_mode=ParseMode.MARKDOWN)
            return
        keyboard = []
        for p in projects:
            prefix = "✅ " if p.name == current else "📁 "
            keyboard.append([InlineKeyboardButton(f"{prefix}{p.title[:25]}", callback_data=f"{CALLBACK_PROJECT}{p.name}")])
        keyboard.append([InlineKeyboardButton("❌ Close", callback_data=CALLBACK_MENU+"close")])
        await update.message.reply_text(f"📁 *Projects*\n\nCurrent: `{current or 'None'}`", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def project(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.auth_manager.is_allowed(update.effective_user.id): return
        if not context.args:
            await self.projects(update, context)
            return
        name = context.args[0].strip()
        proj = self._project_discovery.get_project_by_name(name)
        if not proj:
            await update.message.reply_text(f"❌ Project `{name}` not found", parse_mode=ParseMode.MARKDOWN)
            return
        auth_user = self.auth_manager.get_user(update.effective_user.id)
        if auth_user:
            auth_user.current_project = proj.name
            auth_user.context_id = None
        await update.message.reply_text(f"✅ *Selected:* `{proj.name}`\n📝 {proj.title}\n\n🔄 Context cleared.", parse_mode=ParseMode.MARKDOWN)
    
    async def menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.auth_manager.is_allowed(update.effective_user.id): return
        auth_user = self.auth_manager.get_user(update.effective_user.id)
        proj = f"`{auth_user.current_project}`" if auth_user and auth_user.current_project else "None"
        keyboard = [
            [InlineKeyboardButton("📁 Projects", callback_data=CALLBACK_MENU+"projects"), InlineKeyboardButton("📊 Status", callback_data=CALLBACK_STATUS)],
            [InlineKeyboardButton("🧠 Memory", callback_data=CALLBACK_MEMORY+"menu"), InlineKeyboardButton("🔄 New Chat", callback_data=CALLBACK_NEWCHAT)],
            [InlineKeyboardButton("❓ Help", callback_data=CALLBACK_MENU+"help"), InlineKeyboardButton("❌ Close", callback_data=CALLBACK_MENU+"close")]
        ]
        await update.message.reply_text(f"🎛️ *Main Menu*\n\n📁 Project: {proj}", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def memory(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.auth_manager.is_allowed(update.effective_user.id): return
        if context.args:
            subcmd = context.args[0].lower()
            if subcmd == "search" and len(context.args) > 1:
                await self._search_memories(update.message, " ".join(context.args[1:]))
                return
            elif subcmd == "list":
                await self._list_memories(update.message)
                return
        await self._show_memory_menu(update.message)
    
    async def _show_memory_menu(self, message) -> None:
        keyboard = [
            [InlineKeyboardButton("🔍 Search", callback_data=CALLBACK_MEMORY+"search"), InlineKeyboardButton("📋 List All", callback_data=CALLBACK_MEMORY_LIST+"default")],
            [InlineKeyboardButton("📂 Areas", callback_data=CALLBACK_MEMORY+"areas"), InlineKeyboardButton("📁 Subdirs", callback_data=CALLBACK_MEMORY_SUBDIR+"list")],
            [InlineKeyboardButton("🏠 Menu", callback_data=CALLBACK_MENU+"main"), InlineKeyboardButton("❌ Close", callback_data=CALLBACK_MENU+"close")]
        ]
        await message.reply_text("🧠 *Memory Management*\n\n🔍 Search — Find memories\n📋 List All — Recent memories\n📂 Areas — Filter by area\n📁 Subdirs — Select subdirectory", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _search_memories(self, message, query: str, subdir: str = "default") -> None:
        result = await self.a0_client.search_memories(query=query, memory_subdir=subdir, limit=8)
        if not result.get("success"):
            await message.reply_text(f"❌ *Error*\n\n{result.get('error', 'Unknown')}", parse_mode=ParseMode.MARKDOWN)
            return
        memories = result.get("memories", [])
        if not memories:
            await message.reply_text(f"🔍 *Search: `{query}`*\n\nNo results found.", parse_mode=ParseMode.MARKDOWN)
            return
        text = f"🔍 *Search: `{query}`*\nFound: {len(memories)}\n{SEP}\n\n"
        keyboard = []
        for i, m in enumerate(memories[:5]):
            text += f"*[{i+1}]* `{m.get('area','?')}` ({m.get('timestamp','')[:10]})\n{m.get('content_full','')[:80]}...\n\n"
            keyboard.append([InlineKeyboardButton(f"🗑️ #{i+1}", callback_data=f"{CALLBACK_MEMORY_DELETE}{m.get('id')}")])
        keyboard.append([InlineKeyboardButton("🔙 Memory Menu", callback_data=CALLBACK_MEMORY+"menu")])
        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _list_memories(self, message, subdir: str = "default", area: str = "") -> None:
        result = await self.a0_client.search_memories(query="", memory_subdir=subdir, area=area, limit=10)
        if not result.get("success"):
            await message.reply_text(f"❌ *Error*\n\n{result.get('error', 'Unknown')}", parse_mode=ParseMode.MARKDOWN)
            return
        memories = result.get("memories", [])
        total = result.get("total_count", 0)
        if not memories:
            await message.reply_text(f"📋 *Memory List*\n\nNo memories found.", parse_mode=ParseMode.MARKDOWN)
            return
        area_info = f" • Area: `{area}`" if area else ""
        text = f"📋 *Memories*\nSubdir: `{subdir}`{area_info}\nShowing: {len(memories)}/{total}\n{SEP}\n\n"
        keyboard = []
        for i, m in enumerate(memories[:6]):
            text += f"*[{i+1}]* `{m.get('area','?')}` ({m.get('timestamp','')[:10]})\n{m.get('content_full','')[:60]}...\n\n"
            keyboard.append([InlineKeyboardButton(f"🗑️ #{i+1}", callback_data=f"{CALLBACK_MEMORY_DELETE}{m.get('id')}")])
        keyboard.append([InlineKeyboardButton("🔙 Memory Menu", callback_data=CALLBACK_MEMORY+"menu")])
        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def newchat(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.auth_manager.is_allowed(update.effective_user.id): return
        auth_user = self.auth_manager.get_user(update.effective_user.id)
        if auth_user: auth_user.context_id = None
        proj = f" in `{auth_user.current_project}`" if auth_user and auth_user.current_project else ""
        await update.message.reply_text(f"🔄 *New Chat*{proj}\nNext message starts fresh!", parse_mode=ParseMode.MARKDOWN)
    
    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.auth_manager.is_allowed(update.effective_user.id): return
        auth_user = self.auth_manager.get_user(update.effective_user.id)
        if auth_user: auth_user.context_id = None
        await update.message.reply_text("🔄 *Reset*\nContext cleared.", parse_mode=ParseMode.MARKDOWN)
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.auth_manager.is_allowed(update.effective_user.id): return
        await update.message.reply_text("❌ Cancelled", parse_mode=ParseMode.MARKDOWN)
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not self.auth_manager.is_allowed(query.from_user.id):
            await query.answer("⛔ Not authorized", show_alert=True)
            return
        await query.answer()
        data = query.data
        try:
            if data.startswith(CALLBACK_MEMORY):
                await self._handle_memory_callback(query, data)
                return
            if data.startswith(CALLBACK_MEMORY_LIST):
                parts = data[len(CALLBACK_MEMORY_LIST):].split(":")
                await self._list_memories_callback(query, parts[0] if parts else "default", parts[1] if len(parts) > 1 else "")
                return
            if data.startswith(CALLBACK_MEMORY_DELETE):
                await self._delete_memory_callback(query, data[len(CALLBACK_MEMORY_DELETE):])
                return
            if data.startswith(CALLBACK_MEMORY_SUBDIR):
                await self._handle_subdir_callback(query, data)
                return
            if data.startswith(CALLBACK_PROJECT):
                name = data[len(CALLBACK_PROJECT):]
                proj = self._project_discovery.get_project_by_name(name)
                if proj:
                    auth_user = self.auth_manager.get_user(query.from_user.id)
                    if auth_user:
                        auth_user.current_project = proj.name
                        auth_user.context_id = None
                    await query.edit_message_text(f"✅ *Selected:* `{proj.name}`\n📝 {proj.title}", parse_mode=ParseMode.MARKDOWN)
                return
            if data == CALLBACK_NEWCHAT:
                auth_user = self.auth_manager.get_user(query.from_user.id)
                if auth_user: auth_user.context_id = None
                await query.edit_message_text("🔄 *New Chat*\nNext message starts fresh!", parse_mode=ParseMode.MARKDOWN)
                return
            if data == CALLBACK_RESET:
                auth_user = self.auth_manager.get_user(query.from_user.id)
                if auth_user: auth_user.context_id = None
                await query.edit_message_text("🔄 *Reset*\nContext cleared.", parse_mode=ParseMode.MARKDOWN)
                return
            if data == CALLBACK_STATUS:
                auth_user = self.auth_manager.get_user(query.from_user.id)
                status = "🟢 Connected" if await self.a0_client.health_check() else "🔴 Disconnected"
                ctx = f"`{auth_user.context_id[:8]}...`" if auth_user and auth_user.context_id else "None"
                proj = f"`{auth_user.current_project}`" if auth_user and auth_user.current_project else "None"
                await query.edit_message_text(f"🔍 *Status*\n\nA0: {status}\nContext: {ctx}\nProject: {proj}", parse_mode=ParseMode.MARKDOWN)
                return
            if data.startswith(CALLBACK_MENU):
                action = data[len(CALLBACK_MENU):]
                if action == "projects":
                    await self.projects(update, context)
                elif action == "main":
                    await self.menu(update, context)
                elif action == "help":
                    await self.help(update, context)
                elif action == "close":
                    await query.delete_message()
        except Exception as e:
            logger.error(f"Callback error: {e}")
    
    async def _handle_memory_callback(self, query, data: str) -> None:
        action = data[len(CALLBACK_MEMORY):]
        if action == "menu":
            await self._show_memory_menu(query)
        elif action == "search":
            await query.edit_message_text("🔍 *Search Memories*\n\nUse: `/memory search <query>`\n\nExample:\n`/memory search python`", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=CALLBACK_MEMORY+"menu")]]))
        elif action == "areas":
            keyboard = [
                [InlineKeyboardButton("📋 main", callback_data=CALLBACK_MEMORY_LIST+"default:main"), InlineKeyboardButton("👤 user", callback_data=CALLBACK_MEMORY_LIST+"default:user")],
                [InlineKeyboardButton("📁 knowledge", callback_data=CALLBACK_MEMORY_LIST+"default:knowledge"), InlineKeyboardButton("💬 conv", callback_data=CALLBACK_MEMORY_LIST+"default:conversations")],
                [InlineKeyboardButton("📋 All", callback_data=CALLBACK_MEMORY_LIST+"default:"), InlineKeyboardButton("🔙 Back", callback_data=CALLBACK_MEMORY+"menu")]
            ]
            await query.edit_message_text("📂 *Filter by Area*", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _handle_subdir_callback(self, query, data: str) -> None:
        if data == CALLBACK_MEMORY_SUBDIR + "list":
            result = await self.a0_client.get_memory_subdirs()
            subdirs = result.get("subdirs", ["default"])
            keyboard = [[InlineKeyboardButton(f"📁 {s}", callback_data=f"{CALLBACK_MEMORY_LIST}{s}:")] for s in subdirs]
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=CALLBACK_MEMORY+"menu")])
            await query.edit_message_text("📁 *Memory Subdirectories*", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _list_memories_callback(self, query, subdir: str, area: str) -> None:
        result = await self.a0_client.search_memories(query="", memory_subdir=subdir, area=area, limit=8)
        if not result.get("success"):
            await query.edit_message_text(f"❌ Error: {result.get('error', 'Unknown')}", parse_mode=ParseMode.MARKDOWN)
            return
        memories = result.get("memories", [])
        if not memories:
            await query.edit_message_text("📋 No memories found.", parse_mode=ParseMode.MARKDOWN)
            return
        area_info = f" • `{area}`" if area else ""
        text = f"📋 *Memories*\n`{subdir}`{area_info} • {len(memories)} items\n{SEP}\n\n"
        keyboard = []
        for i, m in enumerate(memories[:5]):
            text += f"*[{i+1}]* `{m.get('area','?')}`\n{m.get('content_full','')[:60]}...\n\n"
            keyboard.append([InlineKeyboardButton(f"🗑️ #{i+1}", callback_data=f"{CALLBACK_MEMORY_DELETE}{m.get('id')}")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=CALLBACK_MEMORY+"menu")])
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _delete_memory_callback(self, query, memory_id: str) -> None:
        result = await self.a0_client.delete_memory(memory_id)
        if result.get("success"):
            await query.answer("✅ Deleted", show_alert=False)
            keyboard = [[InlineKeyboardButton("📋 List", callback_data=CALLBACK_MEMORY_LIST+"default:"), InlineKeyboardButton("🔙 Menu", callback_data=CALLBACK_MEMORY+"menu")]]
            await query.edit_message_text(f"✅ *Memory Deleted*\n\n`{memory_id[:16]}...`", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.answer(f"❌ Failed: {result.get('error', 'Unknown')}", show_alert=True)


class BotMessageHandler:
    def __init__(self, auth_manager: AuthManager, a0_client: A0Client):
        self.auth_manager = auth_manager
        self.a0_client = a0_client
        self._project_discovery = get_project_discovery()
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        message = update.message
        if not self.auth_manager.is_allowed(user.id):
            await message.reply_text("⛔ Access Denied", parse_mode=ParseMode.MARKDOWN)
            return
        auth_user = self.auth_manager.get_user(user.id)
        ctx_id = auth_user.context_id if auth_user else None
        proj = auth_user.current_project if auth_user else None
        text = message.text or message.caption or ""
        attachments = []
        action = "typing"
        if message.document:
            action = "upload_document"
            d = await self._process_doc(message.document)
            if d: attachments.append(d)
        if message.photo:
            action = "upload_photo"
            d = await self._process_photo(message.photo[-1])
            if d: attachments.append(d)
        indicator = TypingIndicator(update, action)
        await indicator.start()
        try:
            resp = await self.a0_client.send_message(text=text, context_id=ctx_id, attachments=attachments or None, project=proj)
            if resp.success:
                if auth_user and resp.context_id:
                    auth_user.context_id = resp.context_id
                if "context not found" in (resp.response or "").lower():
                    if auth_user: auth_user.context_id = None
                    resp = await self.a0_client.send_message(text=text, context_id=None, attachments=attachments or None, project=proj)
                    if resp.success and auth_user and resp.context_id:
                        auth_user.context_id = resp.context_id
                await message.reply_text(resp.response or "No response.", parse_mode=ParseMode.MARKDOWN)
            else:
                await message.reply_text(f"❌ Error: {resp.error or 'Unknown'}", parse_mode=ParseMode.MARKDOWN)
        finally:
            await indicator.stop()
    
    async def _process_doc(self, doc):
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
    
    def clear_context_id(self, chat_id: int) -> None:
        u = self.auth_manager.get_user_by_chat_id(chat_id)
        if u: u.context_id = None
