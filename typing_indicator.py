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
                # Add timeout to prevent hanging
                await asyncio.wait_for(self._task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception as e:
                logger.warning(f"Error stopping typing indicator: {e}")
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




class LongOperationFeedback:
    """Shows periodic 'still working...' messages for long operations.
    
    Usage:
        feedback = LongOperationFeedback(update)
        await feedback.start()
        try:
            response = await long_api_call()
        finally:
            await feedback.stop(final_message=response)
    """
    
    # Show feedback after this many seconds
    FEEDBACK_DELAY = 15  # First message after 15 seconds
    FEEDBACK_INTERVAL = 20  # Then every 20 seconds
    
    # Feedback messages to cycle through
    FEEDBACK_MESSAGES = [
        "⏳ *Still working...*",
        "⏳ *Processing your request...*",
        "⏳ *A0 is thinking...*",
        "⏳ *Almost there...*",
    ]
    
    def __init__(self, update, feedback_delay: int = None, feedback_interval: int = None):
        self.update = update
        self.feedback_delay = feedback_delay or self.FEEDBACK_DELAY
        self.feedback_interval = feedback_interval or self.FEEDBACK_INTERVAL
        self._task = None
        self._running = False
        self._message_count = 0
        self._last_message_id = None
    
    async def _send_feedback_periodically(self):
        """Send feedback messages periodically."""
        import asyncio
        
        try:
            # Wait initial delay before first message
            await asyncio.sleep(self.feedback_delay)
            
            while self._running:
                # Get next feedback message
                msg = self.FEEDBACK_MESSAGES[self._message_count % len(self.FEEDBACK_MESSAGES)]
                self._message_count += 1
                
                try:
                    # Delete previous feedback message if exists
                    if self._last_message_id:
                        try:
                            await self.update.message.chat.delete_message(self._last_message_id)
                        except:
                            pass  # Message might already be gone
                    
                    # Send new feedback message
                    sent = await self.update.message.reply_text(
                        msg,
                        parse_mode="Markdown"
                    )
                    self._last_message_id = sent.message_id
                    logger.debug(f"Sent feedback message: {msg}")
                    
                except Exception as e:
                    logger.warning(f"Failed to send feedback: {e}")
                
                await asyncio.sleep(self.feedback_interval)
                
        except asyncio.CancelledError:
            logger.debug("Feedback task cancelled")
        except Exception as e:
            logger.error(f"Feedback task error: {e}")
    
    async def start(self):
        """Start the feedback loop."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._send_feedback_periodically())
        logger.debug("Started long operation feedback")
    
    async def stop(self, final_message: str = None):
        """Stop feedback and optionally send final message.
        
        Args:
            final_message: Optional final message to send (deletes feedback)
        """
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                # Add timeout to prevent hanging
                await asyncio.wait_for(self._task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception as e:
                logger.warning(f"Error stopping feedback: {e}")
            self._task = None
        
        # Delete last feedback message
        if self._last_message_id:
            try:
                await asyncio.wait_for(
                    self.update.message.chat.delete_message(self._last_message_id),
                    timeout=5.0
                )
            except:
                pass
            self._last_message_id = None
        
        logger.debug("Stopped long operation feedback")


def get_typing_indicator(update: Update, action: str = "typing") -> TypingIndicator:
    """Factory function to create a typing indicator.
    
    Args:
        update: Telegram update object
        action: Chat action type
    
    Returns:
        TypingIndicator instance
    """
    return TypingIndicator(update, action)