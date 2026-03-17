import asyncio
"""Telegram bot command and message handlers."""

import logging
import time
from collections import defaultdict
from typing import Optional, Dict, Any, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CallbackQueryHandler

from .auth import AuthManager, AuthenticatedUser
from .a0_client import A0Client, A0Response
from .typing_indicator import TypingIndicator, LongOperationFeedback
from .project_discovery import get_project_discovery, Project

logger = logging.getLogger(__name__)

# Shorter separator for mobile compatibility
SEP = "───────────────"

# Bot statistics
BOT_START_TIME = None  # Set on first message
TOTAL_MESSAGES_PROCESSED = 0
ACTIVE_USERS = set()
USER_LAST_ACTIVITY = {}  # user_id -> timestamp
WELCOME_BACK_THRESHOLD = 300  # 5 minutes in seconds

# Rate limiting configuration
RATE_LIMIT_MESSAGES = 5  # Max messages per minute
RATE_LIMIT_WINDOW = 60   # Window in seconds

# Simple rate limiter using defaultdict
_user_message_times: Dict[int, List[float]] = defaultdict(list)


def _check_rate_limit(user_id: int) -> tuple:
    """Check if user is within rate limit. Returns (allowed, wait_seconds)."""
    now = time.time()
    times = _user_message_times[user_id]
    
    # Remove old entries outside the window
    times[:] = [t for t in times if now - t < RATE_LIMIT_WINDOW]
    
    if len(times) >= RATE_LIMIT_MESSAGES:
        # User is rate limited - calculate wait time
        oldest = min(times)
        wait_seconds = int(RATE_LIMIT_WINDOW - (now - oldest)) + 1
        return False, max(1, wait_seconds)
    
    # Record this message
    times.append(now)
    return True, 0

# Callback data prefixes
CALLBACK_PROJECT = "proj:"
CALLBACK_NEWCHAT = "newchat"
CALLBACK_RESET = "reset"
CALLBACK_STATUS = "status"
CALLBACK_MENU = "menu"
CALLBACK_NO_PROJECT = "noproject"  # Clear project selection (use normal workdir)
CALLBACK_RETRY = "retry:"  # Retry last message on error


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
                "⛔ *Access Denied*\n\n"
                "You are not authorized to use this bot.\n"
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
                project_info = f"\n📁 Project: `{project.name}`"
        
        # Create inline keyboard for quick actions
        keyboard = [
            [
                InlineKeyboardButton("📁 Projects", callback_data=CALLBACK_MENU + "projects"),
                InlineKeyboardButton("📊 Status", callback_data=CALLBACK_STATUS)
            ],
            [
                InlineKeyboardButton("🔄 New Chat", callback_data=CALLBACK_NEWCHAT),
                InlineKeyboardButton("❓ Help", callback_data=CALLBACK_MENU + "help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"👋 *Welcome to A0 Telegram Bot!*\n\n"
            f"I'm your interface to Agent Zero.{project_info}\n\n"
            "💡 Use the buttons below or send me a message!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        user = update.effective_user
        
        if not self.auth_manager.is_allowed(user.id):
            return
        
        await self._send_help_message(update.message, context)
    
    async def _send_help_message(self, message, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send help message."""
        keyboard = [
            [InlineKeyboardButton("📁 Projects", callback_data=CALLBACK_MENU + "projects")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data=CALLBACK_MENU + "main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(
            "📚 *A0 Telegram Bot Help*\n\n"
            f"{SEP}\n"
            "*What is this?*\n"
            "This bot connects you to Agent Zero (A0), an AI assistant framework.\n\n"
            f"{SEP}\n"
            "*Conversation*\n"
            "• `/newchat` — Start a fresh conversation\n"
            "• `/reset` — Reset conversation context\n"
            "• `/info` — Show session details\n\n"
            f"{SEP}\n"
            "*Projects*\n"
            "• `/projects` — List available projects\n"
            "• `/project <name>` — Select a project\n\n"
            f"{SEP}\n"
            "*System*\n"
            "• `/status` — Check connection\n"
            "• `/version` — Show bot version\n"
            "• `/menu` — Show interactive menu\n\n"
            "📎 Send documents/images for analysis.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
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
            
            # Create keyboard for quick actions
            keyboard = [
                [
                    InlineKeyboardButton("🔄 New Chat", callback_data=CALLBACK_NEWCHAT),
                    InlineKeyboardButton("📁 Projects", callback_data=CALLBACK_MENU + "projects")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"🔍 *Status*\n\n"
                f"A0: {a0_status}\n"
                f"Context: {ctx_info}\n"
                f"Project: {proj_info}\n"
                f"User: {user.first_name}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            logger.info("Status response sent")
        except Exception as e:
            logger.error(f"Error in status handler: {e}")
            try:
                await update.message.reply_text(f"❌ Error: {e}")
            except:
                pass
    

    async def info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /info command - show detailed session info."""
        user = update.effective_user
        
        if not self.auth_manager.is_allowed(user.id):
            return
        
        auth_user = self.auth_manager.get_user(user.id)
        
        # Gather info
        context_id = auth_user.context_id if auth_user else None
        ctx_display = f"`{context_id[:12]}...`" if context_id else "None"
        ctx_short = context_id[:8] if context_id and len(context_id) >= 8 else "N/A"
        
        current_project = auth_user.current_project if auth_user else None
        proj_display = f"`{current_project}`" if current_project else "None (workdir)"
        
        msg_count = auth_user.message_count if auth_user else 0
        
        # Build info message
        info_text = (
            f"📊 *Session Info*\n\n"
            f"{SEP}\n"
            f"👤 *User:* {user.first_name}\n"
            f"🆔 *User ID:* `{user.id}`\n"
            f"{SEP}\n"
            f"💬 *Context:* {ctx_display}\n"
            f"📝 *Messages:* {msg_count}\n"
            f"{SEP}\n"
            f"📁 *Project:* {proj_display}"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 New Chat", callback_data=CALLBACK_NEWCHAT),
                InlineKeyboardButton("📁 Projects", callback_data=CALLBACK_MENU + "projects")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            info_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )


    async def version(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /version command - show bot version info."""
        user = update.effective_user
        
        if not self.auth_manager.is_allowed(user.id):
            return
        
        import subprocess
        from datetime import datetime
        
        # Get git info
        try:
            commit = subprocess.check_output(
                ['git', 'rev-parse', '--short', 'HEAD'],
                cwd='/app',
                stderr=subprocess.DEVNULL
            ).decode().strip()
        except:
            commit = "unknown"
        
        try:
            commit_date = subprocess.check_output(
                ['git', 'log', '-1', '--format=%ci', 'HEAD'],
                cwd='/app',
                stderr=subprocess.DEVNULL
            ).decode().strip()
        except:
            commit_date = "unknown"
        
        version_text = (
            f"🤖 *A0 Telegram Bot*\n\n"
            f"📝 *Version:* 1.4.2\n"
            f"🔧 *Commit:* `{commit}`\n"
            f"📅 *Updated:* {commit_date}\n"
            f"🐍 *Python:* 3.11+"
        )
        
        await update.message.reply_text(
            version_text,
            parse_mode=ParseMode.MARKDOWN
        )

    async def projects(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /projects command - shows inline keyboard with project buttons."""
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
        
        # Create inline keyboard with project buttons
        keyboard = []
        for p in projects:
            # Mark current project with ✅
            prefix = "✅ " if p.name == current else "📁 "
            button_text = f"{prefix}{p.title[:20]}"
            if len(p.title) > 20:
                button_text += "..."
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"{CALLBACK_PROJECT}{p.name}")])
        
        # Add "No Project" option to use normal workdir
        keyboard.append([InlineKeyboardButton("📂 Normal Workdir (no project)", callback_data=CALLBACK_NO_PROJECT)])
        
        # Add navigation buttons
        keyboard.append([
            InlineKeyboardButton("🔄 Refresh", callback_data=CALLBACK_MENU + "projects"),
            InlineKeyboardButton("❌ Close", callback_data=CALLBACK_MENU + "close")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        current_info = f"\n\n*Current:* `{current}`" if current else "\n\n*Current:* None"
        
        await update.message.reply_text(
            f"📁 *Available Projects*{current_info}\n\n"
            "Tap a button to select a project:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def project(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /project command."""
        user = update.effective_user
        
        if not self.auth_manager.is_allowed(user.id):
            return
        
        if not context.args:
            # Show project selection keyboard
            await self.projects(update, context)
            return
        
        name = context.args[0].strip()
        await self._select_project_message(update.message, name)
    
    async def _select_project_message(self, message, name: str) -> None:
        """Select a project by name and send message."""
        proj = self._project_discovery.get_project_by_name(name)
        
        if not proj:
            await message.reply_text(
                f"❌ Project `{name}` not found",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Create keyboard for next actions
        keyboard = [
            [
                InlineKeyboardButton("💬 Start Chat", callback_data=CALLBACK_NEWCHAT),
                InlineKeyboardButton("📁 Other Project", callback_data=CALLBACK_MENU + "projects")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(
            f"✅ *Selected:* `{proj.name}`\n"
            f"📝 {proj.title}\n\n"
            f"🔄 Context cleared. Next message starts fresh in this project.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /menu command - shows interactive main menu."""
        user = update.effective_user
        
        if not self.auth_manager.is_allowed(user.id):
            return
        
        auth_user = self.auth_manager.get_user(user.id)
        current_project = auth_user.current_project if auth_user else None
        
        # Build status info
        project_display = f"`{current_project}`" if current_project else "None"
        
        keyboard = [
            [
                InlineKeyboardButton("📁 Projects", callback_data=CALLBACK_MENU + "projects"),
                InlineKeyboardButton("📊 Status", callback_data=CALLBACK_STATUS)
            ],
            [
                InlineKeyboardButton("🔄 New Chat", callback_data=CALLBACK_NEWCHAT),
                InlineKeyboardButton("♻️ Reset", callback_data=CALLBACK_RESET)
            ],
            [
                InlineKeyboardButton("📊 Info", callback_data=CALLBACK_MENU + "info"),
                InlineKeyboardButton("🔧 Version", callback_data=CALLBACK_MENU + "version")
            ],
            [
                InlineKeyboardButton("❓ Help", callback_data=CALLBACK_MENU + "help"),
                InlineKeyboardButton("❌ Close", callback_data=CALLBACK_MENU + "close")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🎛️ *Main Menu*\n\n"
            f"📁 *Current Project:* {project_display}\n\n"
            "Select an action:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def newchat(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /newchat command."""
        user = update.effective_user
        
        if not self.auth_manager.is_allowed(user.id):
            return
        
        auth_user = self.auth_manager.get_user(user.id)
        project_name = auth_user.current_project if auth_user else None
        
        if auth_user:
            auth_user.context_id = None
        
        proj_info = f" in `{project_name}`" if project_name else ""
        
        keyboard = [[InlineKeyboardButton("💬 Send Message", callback_data=CALLBACK_MENU + "close")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🔄 *New Chat*{proj_info}\n"
            f"Next message starts fresh!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
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
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle inline keyboard button callbacks."""
        query = update.callback_query
        user = query.from_user
        
        if not self.auth_manager.is_allowed(user.id):
            await query.answer("⛔ Not authorized", show_alert=True)
            return
        
        await query.answer()  # Acknowledge the callback
        
        data = query.data
        
        try:
            # Project selection
            if data.startswith(CALLBACK_PROJECT):
                project_name = data[len(CALLBACK_PROJECT):]
                proj = self._project_discovery.get_project_by_name(project_name)
                
                if not proj:
                    await query.edit_message_text(
                        f"❌ Project `{project_name}` not found",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
                
                auth_user = self.auth_manager.get_user(user.id)
                if auth_user:
                    auth_user.current_project = proj.name
                    auth_user.context_id = None
                
                # Update the message
                keyboard = [
                    [
                        InlineKeyboardButton("💬 Start Chat", callback_data=CALLBACK_NEWCHAT),
                        InlineKeyboardButton("📁 Other Project", callback_data=CALLBACK_MENU + "projects")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"✅ *Selected:* `{proj.name}`\n"
                    f"📝 {proj.title}\n\n"
                    f"🔄 Context cleared. Send a message to start!",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            

            # No project - use normal workdir
            elif data == CALLBACK_NO_PROJECT:
                auth_user = self.auth_manager.get_user(user.id)
                if auth_user:
                    auth_user.current_project = None
                    auth_user.context_id = None
                    auth_user.message_count = 0  # Reset message count
                
                await query.edit_message_text(
                    "📂 *Normal Workdir Selected*\n\n"
                    "🔄 Context cleared. Using default workdir.\n"
                    "Send a message to start!",
                    parse_mode=ParseMode.MARKDOWN
                )
            

            # Retry last message on error
            elif data.startswith(CALLBACK_RETRY):
                await query.answer("Retrying...")
                await query.edit_message_text(
                    "🔄 *Retrying your last message...*",
                    parse_mode=ParseMode.MARKDOWN
                )
                # Note: Full retry would require storing last message per user
                # For now, just prompt user to resend
                await query.edit_message_text(
                    "📝 *Please resend your last message.*\n\n"
                    "The bot doesn\'t store message history for privacy.",
                    parse_mode=ParseMode.MARKDOWN
                )
            # New chat
            elif data == CALLBACK_NEWCHAT:
                auth_user = self.auth_manager.get_user(user.id)
                project_name = auth_user.current_project if auth_user else None
                
                if auth_user:
                    auth_user.context_id = None
                    auth_user.message_count = 0  # Reset message count
                
                proj_info = f" in `{project_name}`" if project_name else ""
                
                await query.edit_message_text(
                    f"🔄 *New Chat*{proj_info}\n"
                    f"Next message starts fresh!",
                    parse_mode=ParseMode.MARKDOWN
                )
            
            # Reset
            elif data == CALLBACK_RESET:
                auth_user = self.auth_manager.get_user(user.id)
                if auth_user:
                    auth_user.context_id = None
                    auth_user.message_count = 0  # Reset message count
                
                await query.edit_message_text(
                    "🔄 *Reset*\nContext cleared.",
                    parse_mode=ParseMode.MARKDOWN
                )
            
            # Status
            elif data == CALLBACK_STATUS:
                auth_user = self.auth_manager.get_user(user.id)
                
                a0_status = "🔴 Disconnected"
                try:
                    is_healthy = await self.a0_client.health_check()
                    if is_healthy:
                        a0_status = "🟢 Connected"
                except:
                    pass
                
                context_id = auth_user.context_id if auth_user else None
                ctx_info = f"`{context_id[:8]}...`" if context_id else "None"
                current_project = auth_user.current_project if auth_user else None
                proj_info = f"`{current_project}`" if current_project else "None"
                
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 New Chat", callback_data=CALLBACK_NEWCHAT),
                        InlineKeyboardButton("📁 Projects", callback_data=CALLBACK_MENU + "projects")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"🔍 *Status*\n\n"
                    f"A0: {a0_status}\n"
                    f"Context: {ctx_info}\n"
                    f"Project: {proj_info}",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            
            # Menu actions
            elif data.startswith(CALLBACK_MENU):
                action = data[len(CALLBACK_MENU):]
                
                if action == "projects":
                    # Show projects menu
                    auth_user = self.auth_manager.get_user(user.id)
                    current = auth_user.current_project if auth_user else None
                    projects = self._project_discovery.get_projects(refresh=True)
                    
                    if not projects:
                        await query.edit_message_text(
                            "📁 No projects found",
                            parse_mode=ParseMode.MARKDOWN
                        )
                        return
                    
                    keyboard = []
                    for p in projects:
                        prefix = "✅ " if p.name == current else "📁 "
                        button_text = f"{prefix}{p.title[:20]}"
                        if len(p.title) > 20:
                            button_text += "..."
                        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"{CALLBACK_PROJECT}{p.name}")])
                    
                    # Add "No Project" option
                    keyboard.append([InlineKeyboardButton("📂 Normal Workdir (no project)", callback_data=CALLBACK_NO_PROJECT)])
                    
                    keyboard.append([
                        InlineKeyboardButton("🏠 Main Menu", callback_data=CALLBACK_MENU + "main"),
                        InlineKeyboardButton("❌ Close", callback_data=CALLBACK_MENU + "close")
                    ])
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    current_info = f"\n\n*Current:* `{current}`" if current else "\n\n*Current:* None"
                    
                    await query.edit_message_text(
                        f"📁 *Available Projects*{current_info}\n\n"
                        "Tap a button to select:",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                
                elif action == "main":
                    # Show main menu
                    auth_user = self.auth_manager.get_user(user.id)
                    current_project = auth_user.current_project if auth_user else None
                    project_display = f"`{current_project}`" if current_project else "None"
                    
                    keyboard = [
                        [
                            InlineKeyboardButton("📁 Projects", callback_data=CALLBACK_MENU + "projects"),
                            InlineKeyboardButton("📊 Status", callback_data=CALLBACK_STATUS)
                        ],
                        [
                            InlineKeyboardButton("🔄 New Chat", callback_data=CALLBACK_NEWCHAT),
                            InlineKeyboardButton("♻️ Reset", callback_data=CALLBACK_RESET)
                        ],
                        [
                            InlineKeyboardButton("❓ Help", callback_data=CALLBACK_MENU + "help"),
                            InlineKeyboardButton("❌ Close", callback_data=CALLBACK_MENU + "close")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        f"🎛️ *Main Menu*\n\n"
                        f"📁 *Current Project:* {project_display}\n\n"
                        "Select an action:",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                
                elif action == "info":
                    auth_user = self.auth_manager.get_user(user.id)
                    context_id = auth_user.context_id if auth_user else None
                    ctx_display = f"`{context_id[:12]}...`" if context_id else "None"
                    current_project = auth_user.current_project if auth_user else None
                    proj_display = f"`{current_project}`" if current_project else "None (workdir)"
                    msg_count = auth_user.message_count if auth_user else 0
                    
                    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data=CALLBACK_MENU + "main")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        f"📊 *Session Info*\n\n"
                        f"{SEP}\n"
                        f"💬 *Context:* {ctx_display}\n"
                        f"📝 *Messages:* {msg_count}\n"
                        f"{SEP}\n"
                        f"📁 *Project:* {proj_display}",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                
                elif action == "version":
                    import subprocess
                    try:
                        commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd='/app', stderr=subprocess.DEVNULL).decode().strip()
                    except:
                        commit = "unknown"
                    try:
                        commit_date = subprocess.check_output(['git', 'log', '-1', '--format=%ci', 'HEAD'], cwd='/app', stderr=subprocess.DEVNULL).decode().strip()
                    except:
                        commit_date = "unknown"
                    
                    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data=CALLBACK_MENU + "main")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        f"🤖 *A0 Telegram Bot*\n\n"
                        f"📝 *Version:* 1.4.2\n"
                        f"🔧 *Commit:* `{commit}`\n"
                        f"📅 *Updated:* {commit_date}\n"
                        f"🐍 *Python:* 3.11+",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                
                elif action == "help":
                    keyboard = [
                        [InlineKeyboardButton("📁 Projects", callback_data=CALLBACK_MENU + "projects")],
                        [InlineKeyboardButton("🏠 Main Menu", callback_data=CALLBACK_MENU + "main")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        "📚 *A0 Telegram Bot Help*\n\n"
                        f"{SEP}\n"
                        "*Conversation*\n"
                        "• `/newchat` — Start a fresh conversation\n"
                        "• `/reset` — Reset context\n\n"
                        f"{SEP}\n"
                        "*Projects*\n"
                        "• `/projects` — List projects\n"
                        "• `/project <name>` — Select project\n\n"
                        f"{SEP}\n"
                        "*System*\n"
                        "• `/status` — Check connection\n"
                        "• `/menu` — Show menu\n\n"
                        "📎 Send documents/images for analysis.",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                
                elif action == "close":
                    await query.delete_message()
        
        except Exception as e:
            logger.error(f"Callback error: {e}")
            try:
                await query.edit_message_text(
                    f"❌ Error: {str(e)}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass


class BotMessageHandler:
    """Handles regular messages."""
    
    def __init__(self, auth_manager: AuthManager, a0_client: A0Client):
        self.auth_manager = auth_manager
        self.a0_client = a0_client
        self._project_discovery = get_project_discovery()
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming messages."""
        global BOT_START_TIME, TOTAL_MESSAGES_PROCESSED, ACTIVE_USERS
        
        # Initialize bot start time on first message
        if BOT_START_TIME is None:
            import time
            BOT_START_TIME = time.time()
        
        user = update.effective_user
        message = update.message
        
        # Track statistics
        ACTIVE_USERS.add(user.id)
        
        if not self.auth_manager.is_allowed(user.id):
            await message.reply_text("⛔ Access Denied", parse_mode=ParseMode.MARKDOWN)
            return
        
        # Rate limiting check
        allowed, wait_seconds = _check_rate_limit(user.id)
        if not allowed:
            await message.reply_text(
                f"⏳ *Rate Limited*\n\n"
                f"Please wait `{wait_seconds}` seconds before sending another message.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        auth_user = self.auth_manager.get_user(user.id)
        chat_id = message.chat_id
        
        ctx_id = auth_user.context_id if auth_user else None
        proj = auth_user.current_project if auth_user else None
        
        logger.info(f"Handling message: context_id={ctx_id}, project={proj}")
        
        text = message.text or message.caption or ""
        
        # Warn if message is too long (Telegram limit is 4096, warn at 4000)
        MAX_MESSAGE_LENGTH = 4000
        if len(text) > MAX_MESSAGE_LENGTH:
            await message.reply_text(
                f"⚠️ *Long Message Warning*\n\n"
                f"Your message is `{len(text)}` characters.\n"
                f"Messages over 4000 chars may be truncated.\n\n"
                f"Consider splitting into smaller messages.",
                parse_mode=ParseMode.MARKDOWN
            )
            # Continue processing anyway, just warn
        
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
        
        indicator = TypingIndicator(update, action)
        feedback = LongOperationFeedback(update)
        await indicator.start()
        await feedback.start()
        
        try:
            resp = await self.a0_client.send_message(
                text=text, context_id=ctx_id,
                attachments=attachments or None, project=proj
            )
            
            if resp.success:
                if auth_user and resp.context_id:
                    auth_user.context_id = resp.context_id
                # Increment message count for this conversation
                if auth_user:
                    auth_user.message_count += 1
                # Increment global message counter
                TOTAL_MESSAGES_PROCESSED += 1
                
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
                # Error with retry button
                keyboard = [[InlineKeyboardButton("🔄 Retry", callback_data=f"{CALLBACK_RETRY}{ctx_id or 'none'}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await message.reply_text(
                    f"❌ *Error*\n\n{resp.error or 'Unknown'}",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
        finally:
            await indicator.stop()
            await feedback.stop()
    
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
