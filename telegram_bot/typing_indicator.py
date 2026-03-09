"""Continuous typing indicator for Telegram.

Telegram chat actions expire after 5 seconds, so we need to
periodically resend them to show continuous activity.
"""

import asyncio
import logging
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes

from .logging_config import get_logger

logger = get_logger(__name__)


class TypingIndicator:
    """Manages continuous typing indicators for Telegram chats.
    
    Usage:
        indicator = TypingIndicator(update, action="typing")
        await indicator.start()
        try:
            # Do work...
            response = await some_api_call()
        finally:
            await indicator.stop()
    """
    
    # Telegram chat actions expire after 5 seconds
    ACTION_INTERVAL = 4.5  # Send slightly before expiration
    
    # Available actions with their visual indicators
    ACTIONS = {
        "typing": "✍️ Typing...",
        "upload_photo": "📷 Uploading photo...",
        "upload_video": "🎬 Uploading video...",
        "upload_audio": "🎵 Uploading audio...",
        "upload_document": "📎 Uploading document...",
        "choose_sticker": "😀 Choosing sticker...",
        "find_location": "📍 Finding location...",
        "record_video": "🎬 Recording video...",
        "record_voice": "🎤 Recording voice...",
    }
    
    def __init__(self, update: Update, action: str = "typing"):
        """Initialize the typing indicator.
        
        Args:
            update: Telegram update object
            action: Chat action type (typing, upload_document, etc.)
        """
        self.update = update
        self.action = action
        self._task: Optional[asyncio.Task] = None
        self._running = False
    
    async def _send_action_periodically(self):
        """Send chat action at regular intervals."""
        try:
            while self._running:
                try:
                    await self.update.message.chat.send_action(self.action)
                    logger.debug(f"Sent chat action: {self.action}")
                except Exception as e:
                    logger.warning(f"Failed to send chat action: {e}")
                    # Continue trying even if one fails
                
                await asyncio.sleep(self.ACTION_INTERVAL)
        except asyncio.CancelledError:
            logger.debug("Typing indicator cancelled")
        except Exception as e:
            logger.error(f"Typing indicator error: {e}")
    
    async def start(self):
        """Start the continuous typing indicator."""
        if self._running:
            return
        
        self._running = True
        
        # Send initial action immediately
        try:
            await self.update.message.chat.send_action(self.action)
        except Exception as e:
            logger.warning(f"Failed to send initial chat action: {e}")
        
        # Start background task for periodic updates
        self._task = asyncio.create_task(self._send_action_periodically())
        logger.debug(f"Started typing indicator: {self.action}")
    
    async def stop(self):
        """Stop the continuous typing indicator."""
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        logger.debug(f"Stopped typing indicator: {self.action}")
    
    async def change_action(self, action: str):
        """Change the action type while running.
        
        Args:
            action: New action type
        """
        self.action = action
        if self._running:
            try:
                await self.update.message.chat.send_action(self.action)
            except Exception as e:
                logger.warning(f"Failed to change chat action: {e}")


class TypingContext:
    """Context manager for typing indicator.
    
    Usage:
        async with TypingContext(update, "typing"):
            response = await some_api_call()
    """
    
    def __init__(self, update: Update, action: str = "typing"):
        self.indicator = TypingIndicator(update, action)
    
    async def __aenter__(self):
        await self.indicator.start()
        return self.indicator
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.indicator.stop()
        return False  # Don't suppress exceptions


def get_typing_indicator(update: Update, action: str = "typing") -> TypingIndicator:
    """Factory function to create a typing indicator.
    
    Args:
        update: Telegram update object
        action: Chat action type
    
    Returns:
        TypingIndicator instance
    """
    return TypingIndicator(update, action)
