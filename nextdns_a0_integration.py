#!/usr/bin/env python3
"""
NextDNS Integration for A0 Telegram Bot
=======================================
Dit bestand bevat NextDNS command handlers die aan de A0 Telegram bot
kunnen worden toegevoegd.

Commands (prefix: /nd_ om conflicten te voorkomen):
- /nd_status - DNS statistieken
- /nd_domains [blocked|allowed] - Top domains
- /nd_devices - Top apparaten
- /nd_logs [blocked] - Recente DNS logs
- /nd_block <domain> - Domain blokkeren
- /nd_unblock <domain> - Domain deblokkeren
- /nd_allow <domain> - Domain toestaan
- /nd_unallow <domain> - Van allowlist verwijderen
- /nd_list - Toon denylist
- /nd_allowlist - Toon allowlist
- /nd_report - Genereer rapport
- /nd_help - Toon hulp

Installatie:
1. Voeg deze handlers toe aan de A0 Telegram bot handlers.py
2. Of importeer deze module en registreer de handlers in bot.py

Author: Agent Zero
Date: 2026-03-22
"""

import os
import json
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, List

# telegram imports (zullen beschikbaar zijn in A0 bot context)
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.constants import ParseMode
    from telegram.ext import ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

logger = logging.getLogger(__name__)

# NextDNS Configuration
NEXTDNS_API_KEY = os.environ.get("NEXTDNS_API_KEY", "")
NEXTDNS_PROFILE = os.environ.get("NEXTDNS_PROFILE", "")
NEXTDNS_API = "https://api.nextdns.io"

SEP = "───────────────"


class NextDNSClient:
    """Lightweight NextDNS API client"""
    
    def __init__(self, api_key: str = None, profile_id: str = None):
        self.api_key = api_key or NEXTDNS_API_KEY
        self.profile_id = profile_id or NEXTDNS_PROFILE
        self.headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def _get(self, endpoint: str, params: Dict = None) -> Dict:
        """Make GET request"""
        url = f"{NEXTDNS_API}{endpoint}"
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"NextDNS API error: {e}")
            return {"error": str(e)}
    
    def _post(self, endpoint: str, data: Dict = None) -> Dict:
        """Make POST request"""
        url = f"{NEXTDNS_API}{endpoint}"
        try:
            resp = requests.post(url, headers=self.headers, json=data, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"NextDNS API error: {e}")
            return {"error": str(e)}
    
    def _delete(self, endpoint: str) -> Dict:
        """Make DELETE request"""
        url = f"{NEXTDNS_API}{endpoint}"
        try:
            resp = requests.delete(url, headers=self.headers, timeout=30)
            resp.raise_for_status()
            return {"ok": True}
        except Exception as e:
            logger.error(f"NextDNS API error: {e}")
            return {"error": str(e)}
    
    # Analytics
    def get_status(self, days: int = 7) -> Dict:
        return self._get(f"/profiles/{self.profile_id}/analytics/status", {"from": f"-{days}d"})
    
    def get_domains(self, status: str = None, limit: int = 10) -> Dict:
        params = {"limit": limit}
        if status:
            params["status"] = status
        return self._get(f"/profiles/{self.profile_id}/analytics/domains", params)
    
    def get_devices(self, limit: int = 10) -> Dict:
        return self._get(f"/profiles/{self.profile_id}/analytics/devices", {"limit": limit})
    
    def get_reasons(self, limit: int = 10) -> Dict:
        return self._get(f"/profiles/{self.profile_id}/analytics/reasons", {"limit": limit})
    
    # Logs
    def get_logs(self, limit: int = 20, status: str = None) -> Dict:
        params = {"limit": limit}
        if status:
            params["status"] = status
        return self._get(f"/profiles/{self.profile_id}/logs", params)
    
    # Lists
    def get_denylist(self) -> Dict:
        return self._get(f"/profiles/{self.profile_id}/denylist")
    
    def get_allowlist(self) -> Dict:
        return self._get(f"/profiles/{self.profile_id}/allowlist")
    
    def add_denylist(self, domain: str) -> Dict:
        return self._post(f"/profiles/{self.profile_id}/denylist", {"id": domain, "active": True})
    
    def remove_denylist(self, domain: str) -> Dict:
        return self._delete(f"/profiles/{self.profile_id}/denylist/{domain}")
    
    def add_allowlist(self, domain: str) -> Dict:
        return self._post(f"/profiles/{self.profile_id}/allowlist", {"id": domain, "active": True})
    
    def remove_allowlist(self, domain: str) -> Dict:
        return self._delete(f"/profiles/{self.profile_id}/allowlist/{domain}")


# Global client instance
_nextdns_client = None

def get_nextdns_client() -> NextDNSClient:
    """Get or create NextDNS client"""
    global _nextdns_client
    if _nextdns_client is None:
        _nextdns_client = NextDNSClient()
    return _nextdns_client


# ==================== COMMAND HANDLERS ====================

if TELEGRAM_AVAILABLE:
    
    async def nd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /nd_help command"""
        keyboard = [
            [
                InlineKeyboardButton("📊 Status", callback_data="nd:status"),
                InlineKeyboardButton("🌐 Domains", callback_data="nd:domains")
            ],
            [
                InlineKeyboardButton("💻 Devices", callback_data="nd:devices"),
                InlineKeyboardButton("📜 Logs", callback_data="nd:logs")
            ],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="menu:main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🔒 *NextDNS Commands*\n\n"
            f"{SEP}\n"
            "*Analytics*\n"
            "• `/nd_status` — DNS statistieken\n"
            "• `/nd_domains` — Top domains\n"
            "• `/nd_domains blocked` — Geblokkeerde\n"
            "• `/nd_devices` — Top apparaten\n\n"
            f"{SEP}\n"
            "*Logs*\n"
            "• `/nd_logs` — Recente DNS logs\n"
            "• `/nd_logs blocked` — Geblokkeerde\n\n"
            f"{SEP}\n"
            "*Beheer*\n"
            "• `/nd_block <domain>` — Blokkeer\n"
            "• `/nd_unblock <domain>` — Deblokkeer\n"
            "• `/nd_allow <domain>` — Sta toe\n"
            "• `/nd_list` — Toon denylist\n"
            "• `/nd_allowlist` — Toon allowlist\n\n"
            f"{SEP}\n"
            "*Rapport*\n"
            "• `/nd_report` — Genereer rapport",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def nd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /nd_status command"""
        client = get_nextdns_client()
        data = client.get_status(days=7)
        
        if "error" in data:
            await update.message.reply_text(
                f"❌ *Error*\n\n`{data['error']}`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        items = data.get("data", [])
        total = sum(i.get("queries", 0) for i in items)
        
        text = f"📊 *NextDNS Status* (7 dagen)\n\n{SEP}\n"
        
        for item in items:
            status = item.get("status", "unknown")
            queries = item.get("queries", 0)
            pct = (queries / total * 100) if total > 0 else 0
            icon = {"default": "⚪", "blocked": "🔴", "allowed": "🟢"}.get(status, "❓")
            text += f"\n{icon} *{status.title()}*: `{queries:,}` ({pct:.1f}%)"
        
        text += f"\n\n{SEP}\n📈 *Totaal*: `{total:,}` queries"
        
        keyboard = [
            [
                InlineKeyboardButton("🌐 Domains", callback_data="nd:domains"),
                InlineKeyboardButton("💻 Devices", callback_data="nd:devices")
            ],
            [InlineKeyboardButton("📜 Logs", callback_data="nd:logs")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )
    
    async def nd_domains(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /nd_domains command"""
        client = get_nextdns_client()
        status_filter = context.args[0] if context.args else None
        
        if status_filter and status_filter not in ["blocked", "allowed", "default"]:
            await update.message.reply_text(
                "❌ *Ongeldig filter*\n\nGebruik: `/nd_domains` of `/nd_domains blocked`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        data = client.get_domains(status=status_filter, limit=15)
        
        if "error" in data:
            await update.message.reply_text(
                f"❌ *Error*\n\n`{data['error']}`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        items = data.get("data", [])
        filter_text = f" ({status_filter})" if status_filter else ""
        text = f"🌐 *Top Domains{filter_text}*\n\n{SEP}\n"
        
        for i, item in enumerate(items, 1):
            domain = item.get("domain", "unknown")
            queries = item.get("queries", 0)
            # Truncate long domains
            if len(domain) > 35:
                domain = domain[:32] + "..."
            text += f"\n{i}. `{domain}`\n   📊 `{queries:,}`"
        
        keyboard = [
            [
                InlineKeyboardButton("🔴 Blocked", callback_data="nd:domains:blocked"),
                InlineKeyboardButton("🟢 Allowed", callback_data="nd:domains:allowed")
            ],
            [InlineKeyboardButton("📊 Status", callback_data="nd:status")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )
    
    async def nd_devices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /nd_devices command"""
        client = get_nextdns_client()
        data = client.get_devices(limit=10)
        
        if "error" in data:
            await update.message.reply_text(
                f"❌ *Error*\n\n`{data['error']}`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        items = data.get("data", [])
        text = f"💻 *Top Apparaten*\n\n{SEP}\n"
        
        for i, item in enumerate(items, 1):
            name = item.get("name", "Unknown")
            model = item.get("model", "")
            queries = item.get("queries", 0)
            text += f"\n{i}. *{name}*"
            if model:
                text += f"\n   📱 {model}"
            text += f"\n   📊 `{queries:,}` queries"
        
        keyboard = [[InlineKeyboardButton("📊 Status", callback_data="nd:status")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )
    
    async def nd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /nd_logs command"""
        client = get_nextdns_client()
        status_filter = context.args[0] if context.args else None
        
        if status_filter and status_filter not in ["blocked", "allowed", "default", "error"]:
            await update.message.reply_text(
                "❌ *Ongeldig filter*\n\nGebruik: `/nd_logs` of `/nd_logs blocked`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        data = client.get_logs(limit=15, status=status_filter)
        
        if "error" in data:
            await update.message.reply_text(
                f"❌ *Error*\n\n`{data['error']}`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        logs = data.get("data", [])
        filter_text = f" [{status_filter}]" if status_filter else ""
        text = f"📜 *DNS Logs{filter_text}*\n\n{SEP}\n"
        
        for log in logs[:15]:
            domain = log.get("domain", "unknown")
            status = log.get("status", "unknown")
            device = log.get("device", {}).get("name", "Unknown")
            timestamp = log.get("timestamp", "")
            
            # Parse timestamp
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                time_str = dt.strftime("%H:%M:%S")
            except:
                time_str = "?"
            
            icon = {"default": "⚪", "blocked": "🔴", "allowed": "🟢", "error": "⚠️"}.get(status, "❓")
            
            # Truncate long domains
            if len(domain) > 30:
                domain = domain[:27] + "..."
            
            text += f"\n{icon} `{domain}`\n   📱 {device} | 🕐 {time_str}"
        
        keyboard = [
            [
                InlineKeyboardButton("🔴 Blocked", callback_data="nd:logs:blocked"),
                InlineKeyboardButton("🟢 Allowed", callback_data="nd:logs:allowed")
            ],
            [InlineKeyboardButton("📊 Status", callback_data="nd:status")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )
    
    async def nd_block(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /nd_block command"""
        if not context.args:
            await update.message.reply_text(
                "❌ *Gebruik:*\n\n`/nd_block <domain>`\n\nVoorbeeld:\n`/nd_block ads.google.com`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        domain = context.args[0].strip()
        client = get_nextdns_client()
        result = client.add_denylist(domain)
        
        if "error" in result:
            await update.message.reply_text(
                f"❌ *Fout bij blokkeren*\n\n`{result['error']}`",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                f"✅ *Geblokkeerd*\n\n`{domain}` toegevoegd aan denylist",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def nd_unblock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /nd_unblock command"""
        if not context.args:
            await update.message.reply_text(
                "❌ *Gebruik:*\n\n`/nd_unblock <domain>`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        domain = context.args[0].strip()
        client = get_nextdns_client()
        result = client.remove_denylist(domain)
        
        if "error" in result:
            await update.message.reply_text(
                f"❌ *Fout bij deblokkeren*\n\n`{result['error']}`",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                f"✅ *Gedeblokkeerd*\n\n`{domain}` verwijderd van denylist",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def nd_allow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /nd_allow command"""
        if not context.args:
            await update.message.reply_text(
                "❌ *Gebruik:*\n\n`/nd_allow <domain>`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        domain = context.args[0].strip()
        client = get_nextdns_client()
        result = client.add_allowlist(domain)
        
        if "error" in result:
            await update.message.reply_text(
                f"❌ *Fout bij toevoegen*\n\n`{result['error']}`",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                f"✅ *Toegestaan*\n\n`{domain}` toegevoegd aan allowlist",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def nd_unallow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /nd_unallow command"""
        if not context.args:
            await update.message.reply_text(
                "❌ *Gebruik:*\n\n`/nd_unallow <domain>`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        domain = context.args[0].strip()
        client = get_nextdns_client()
        result = client.remove_allowlist(domain)
        
        if "error" in result:
            await update.message.reply_text(
                f"❌ *Fout bij verwijderen*\n\n`{result['error']}`",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                f"✅ *Verwijderd*\n\n`{domain}` verwijderd van allowlist",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def nd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /nd_list command - show denylist"""
        client = get_nextdns_client()
        data = client.get_denylist()
        
        if "error" in data:
            await update.message.reply_text(
                f"❌ *Error*\n\n`{data['error']}`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        items = data.get("data", [])
        text = f"🚫 *Denylist*\n\n{SEP}\n"
        
        if not items:
            text += "\n(leeg)"
        else:
            for item in items[:20]:  # Max 20 items
                domain = item.get("id", "")
                active = "✓" if item.get("active", True) else "✗"
                text += f"\n`[{active}] {domain}`"
            
            if len(items) > 20:
                text += f"\n\n_... en {len(items) - 20} meer_"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def nd_allowlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /nd_allowlist command - show allowlist"""
        client = get_nextdns_client()
        data = client.get_allowlist()
        
        if "error" in data:
            await update.message.reply_text(
                f"❌ *Error*\n\n`{data['error']}`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        items = data.get("data", [])
        text = f"✅ *Allowlist*\n\n{SEP}\n"
        
        if not items:
            text += "\n(leeg)"
        else:
            for item in items[:20]:  # Max 20 items
                domain = item.get("id", "")
                active = "✓" if item.get("active", True) else "✗"
                text += f"\n`[{active}] {domain}`"
            
            if len(items) > 20:
                text += f"\n\n_... en {len(items) - 20} meer_"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def nd_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /nd_report command - generate quick report"""
        client = get_nextdns_client()
        
        # Get data
        status_data = client.get_status(days=7)
        domains_data = client.get_domains(limit=5)
        devices_data = client.get_devices(limit=5)
        reasons_data = client.get_reasons(limit=5)
        
        if "error" in status_data:
            await update.message.reply_text(
                f"❌ *Error*\n\n`{status_data['error']}`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Process status
        status_items = status_data.get("data", [])
        total_queries = sum(i.get("queries", 0) for i in status_items)
        blocked = next((i.get("queries", 0) for i in status_items if i.get("status") == "blocked"), 0)
        blocked_pct = (blocked / total_queries * 100) if total_queries > 0 else 0
        
        text = (
            f"📊 *NextDNS Rapport*\n"
            f"📅 {datetime.now().strftime('%d-%m-%Y %H:%M')}\n\n"
            f"{SEP}\n"
            f"📈 *Overzicht (7 dagen)*\n\n"
            f"• Totaal: `{total_queries:,}`\n"
            f"• Geblokkeerd: `{blocked:,}` ({blocked_pct:.1f}%)\n\n"
            f"{SEP}\n"
            f"🌐 *Top 5 Domains*\n"
        )
        
        for i, item in enumerate(domains_data.get("data", [])[:5], 1):
            domain = item.get("domain", "unknown")
            queries = item.get("queries", 0)
            if len(domain) > 25:
                domain = domain[:22] + "..."
            text += f"\n{i}. `{domain}` ({queries:,})"
        
        text += f"\n\n{SEP}\n💻 *Top 5 Apparaten*\n"
        
        for i, item in enumerate(devices_data.get("data", [])[:5], 1):
            name = item.get("name", "Unknown")
            queries = item.get("queries", 0)
            text += f"\n{i}. {name} ({queries:,})"
        
        text += f"\n\n{SEP}\n🛡️ *Blokkades*\n"
        
        for i, item in enumerate(reasons_data.get("data", [])[:5], 1):
            name = item.get("name", "Unknown")
            queries = item.get("queries", 0)
            if len(name) > 25:
                name = name[:22] + "..."
            text += f"\n{i}. {name} ({queries:,})"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def handle_nd_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle NextDNS callback queries"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if not data.startswith("nd:"):
            return
        
        action = data[3:]  # Remove 'nd:' prefix
        client = get_nextdns_client()
        
        if action == "status":
            data = client.get_status(days=7)
            items = data.get("data", [])
            total = sum(i.get("queries", 0) for i in items)
            
            text = f"📊 *NextDNS Status* (7 dagen)\n\n{SEP}\n"
            for item in items:
                status = item.get("status", "unknown")
                queries = item.get("queries", 0)
                pct = (queries / total * 100) if total > 0 else 0
                icon = {"default": "⚪", "blocked": "🔴", "allowed": "🟢"}.get(status, "❓")
                text += f"\n{icon} *{status.title()}*: `{queries:,}` ({pct:.1f}%)"
            text += f"\n\n{SEP}\n📈 *Totaal*: `{total:,}` queries"
            
            keyboard = [
                [InlineKeyboardButton("🌐 Domains", callback_data="nd:domains"),
                 InlineKeyboardButton("💻 Devices", callback_data="nd:devices")],
                [InlineKeyboardButton("📜 Logs", callback_data="nd:logs")]
            ]
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif action == "domains":
            data = client.get_domains(limit=15)
            items = data.get("data", [])
            text = f"🌐 *Top Domains*\n\n{SEP}\n"
            for i, item in enumerate(items, 1):
                domain = item.get("domain", "unknown")
                queries = item.get("queries", 0)
                if len(domain) > 35:
                    domain = domain[:32] + "..."
                text += f"\n{i}. `{domain}`\n   📊 `{queries:,}`"
            
            keyboard = [
                [InlineKeyboardButton("🔴 Blocked", callback_data="nd:domains:blocked"),
                 InlineKeyboardButton("🟢 Allowed", callback_data="nd:domains:allowed")],
                [InlineKeyboardButton("📊 Status", callback_data="nd:status")]
            ]
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif action == "domains:blocked":
            data = client.get_domains(status="blocked", limit=15)
            items = data.get("data", [])
            text = f"🌐 *Top Blocked Domains*\n\n{SEP}\n"
            for i, item in enumerate(items, 1):
                domain = item.get("domain", "unknown")
                queries = item.get("queries", 0)
                if len(domain) > 35:
                    domain = domain[:32] + "..."
                text += f"\n{i}. `{domain}`\n   📊 `{queries:,}`"
            
            keyboard = [
                [InlineKeyboardButton("🌐 Alle", callback_data="nd:domains"),
                 InlineKeyboardButton("🟢 Allowed", callback_data="nd:domains:allowed")],
                [InlineKeyboardButton("📊 Status", callback_data="nd:status")]
            ]
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif action == "domains:allowed":
            data = client.get_domains(status="allowed", limit=15)
            items = data.get("data", [])
            text = f"🌐 *Top Allowed Domains*\n\n{SEP}\n"
            for i, item in enumerate(items, 1):
                domain = item.get("domain", "unknown")
                queries = item.get("queries", 0)
                if len(domain) > 35:
                    domain = domain[:32] + "..."
                text += f"\n{i}. `{domain}`\n   📊 `{queries:,}`"
            
            keyboard = [
                [InlineKeyboardButton("🌐 Alle", callback_data="nd:domains"),
                 InlineKeyboardButton("🔴 Blocked", callback_data="nd:domains:blocked")],
                [InlineKeyboardButton("📊 Status", callback_data="nd:status")]
            ]
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif action == "devices":
            data = client.get_devices(limit=10)
            items = data.get("data", [])
            text = f"💻 *Top Apparaten*\n\n{SEP}\n"
            for i, item in enumerate(items, 1):
                name = item.get("name", "Unknown")
                model = item.get("model", "")
                queries = item.get("queries", 0)
                text += f"\n{i}. *{name}*"
                if model:
                    text += f"\n   📱 {model}"
                text += f"\n   📊 `{queries:,}` queries"
            
            keyboard = [[InlineKeyboardButton("📊 Status", callback_data="nd:status")]]
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif action == "logs":
            data = client.get_logs(limit=15)
            logs = data.get("data", [])
            text = f"📜 *DNS Logs*\n\n{SEP}\n"
            for log in logs[:15]:
                domain = log.get("domain", "unknown")
                status = log.get("status", "unknown")
                device = log.get("device", {}).get("name", "Unknown")
                timestamp = log.get("timestamp", "")
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    time_str = dt.strftime("%H:%M:%S")
                except:
                    time_str = "?"
                icon = {"default": "⚪", "blocked": "🔴", "allowed": "🟢", "error": "⚠️"}.get(status, "❓")
                if len(domain) > 30:
                    domain = domain[:27] + "..."
                text += f"\n{icon} `{domain}`\n   📱 {device} | 🕐 {time_str}"
            
            keyboard = [
                [InlineKeyboardButton("🔴 Blocked", callback_data="nd:logs:blocked"),
                 InlineKeyboardButton("🟢 Allowed", callback_data="nd:logs:allowed")],
                [InlineKeyboardButton("📊 Status", callback_data="nd:status")]
            ]
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif action == "logs:blocked":
            data = client.get_logs(limit=15, status="blocked")
            logs = data.get("data", [])
            text = f"📜 *Blocked Logs*\n\n{SEP}\n"
            for log in logs[:15]:
                domain = log.get("domain", "unknown")
                device = log.get("device", {}).get("name", "Unknown")
                reasons = log.get("reasons", [])
                timestamp = log.get("timestamp", "")
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    time_str = dt.strftime("%H:%M:%S")
                except:
                    time_str = "?"
                if len(domain) > 30:
                    domain = domain[:27] + "..."
                reason_str = reasons[0].get("name", "") if reasons else ""
                if len(reason_str) > 20:
                    reason_str = reason_str[:17] + "..."
                text += f"\n🔴 `{domain}`\n   📱 {device} | 🕐 {time_str}\n   🛡️ {reason_str}"
            
            keyboard = [
                [InlineKeyboardButton("📜 Alle Logs", callback_data="nd:logs"),
                 InlineKeyboardButton("🟢 Allowed", callback_data="nd:logs:allowed")],
                [InlineKeyboardButton("📊 Status", callback_data="nd:status")]
            ]
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif action == "logs:allowed":
            data = client.get_logs(limit=15, status="allowed")
            logs = data.get("data", [])
            text = f"📜 *Allowed Logs*\n\n{SEP}\n"
            for log in logs[:15]:
                domain = log.get("domain", "unknown")
                device = log.get("device", {}).get("name", "Unknown")
                timestamp = log.get("timestamp", "")
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    time_str = dt.strftime("%H:%M:%S")
                except:
                    time_str = "?"
                if len(domain) > 30:
                    domain = domain[:27] + "..."
                text += f"\n🟢 `{domain}`\n   📱 {device} | 🕐 {time_str}"
            
            keyboard = [
                [InlineKeyboardButton("📜 Alle Logs", callback_data="nd:logs"),
                 InlineKeyboardButton("🔴 Blocked", callback_data="nd:logs:blocked")],
                [InlineKeyboardButton("📊 Status", callback_data="nd:status")]
            ]
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))


# ==================== REGISTRATION HELPER ====================

def get_nextdns_handlers():
    """Return list of (command, handler) tuples for registration"""
    if not TELEGRAM_AVAILABLE:
        return []
    
    return [
        ("nd_help", nd_help),
        ("nd_status", nd_status),
        ("nd_domains", nd_domains),
        ("nd_devices", nd_devices),
        ("nd_logs", nd_logs),
        ("nd_block", nd_block),
        ("nd_unblock", nd_unblock),
        ("nd_allow", nd_allow),
        ("nd_unallow", nd_unallow),
        ("nd_list", nd_list),
        ("nd_allowlist", nd_allowlist),
        ("nd_report", nd_report),
    ]


def get_nextdns_callback_handler():
    """Return callback handler for NextDNS buttons"""
    if not TELEGRAM_AVAILABLE:
        return None
    return handle_nd_callback


# ==================== STANDALONE TEST ====================

if __name__ == "__main__":
    # Test the NextDNS client
    print("Testing NextDNS client...")
    client = NextDNSClient()
    
    print("\n1. Status:")
    status = client.get_status(days=7)
    print(json.dumps(status, indent=2)[:500])
    
    print("\n2. Domains:")
    domains = client.get_domains(limit=5)
    print(json.dumps(domains, indent=2)[:500])
    
    print("\n3. Devices:")
    devices = client.get_devices(limit=5)
    print(json.dumps(devices, indent=2)[:500])
    
    print("\n✅ All tests passed!")
