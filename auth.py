"""User authentication for Telegram bot.

Handles user authorization, validation, and security logging.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Set, FrozenSet
from telegram import Update
from telegram.ext import ContextTypes

from .config import get_config
from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class AuthenticatedUser:
    """Represents an authenticated Telegram user."""
    user_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    is_admin: bool = False
    
    @property
    def display_name(self) -> str:
        """Get a human-readable display name."""
        if self.username:
            return f"@{self.username}"
        parts = [self.first_name, self.last_name]
        return " ".join(filter(None, parts)) or f"User {self.user_id}"


class AuthManager:
    """Manages user authentication and authorization."""
    
    def __init__(self):
        self._config = get_config()
        self._allowed_users: FrozenSet[int] = frozenset(self._config.telegram_allowed_users)
        # Optional: admin users (subset of allowed users)
        admin_ids_str = getattr(self._config, 'telegram_admin_users', '')
        if isinstance(admin_ids_str, str) and admin_ids_str:
            self._admin_users = frozenset(
                int(uid.strip()) for uid in admin_ids_str.split(',') if uid.strip()
            )
        else:
            self._admin_users = frozenset()
        
        # Track failed auth attempts for rate limiting
        self._failed_attempts: dict[int, int] = {}
    
    def is_allowed(self, user_id: int) -> bool:
        """Check if a user ID is allowed to interact with the bot."""
        return user_id in self._allowed_users
    
    def is_admin(self, user_id: int) -> bool:
        """Check if a user ID has admin privileges."""
        return user_id in self._admin_users
    
    def authenticate(self, update: Update) -> Optional[AuthenticatedUser]:
        """Authenticate a user from a Telegram update.
        
        Args:
            update: Telegram update object
        
        Returns:
            AuthenticatedUser if authenticated, None otherwise
        """
        user = update.effective_user
        if not user:
            logger.warning("Received update without user information")
            return None
        
        user_id = user.id
        
        if not self.is_allowed(user_id):
            self._log_unauthorized_access(user_id, user.username, update)
            return None
        
        # Log successful authentication
        logger.info(
            f"User authenticated: {user_id} (@{user.username})",
            extra={
                'user_id': user_id,
                'username': user.username,
                'event': 'auth_success'
            }
        )
        
        return AuthenticatedUser(
            user_id=user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            is_admin=self.is_admin(user_id)
        )
    
    def _log_unauthorized_access(self, user_id: int, username: Optional[str], update: Update) -> None:
        """Log unauthorized access attempts."""
        # Track failed attempts
        self._failed_attempts[user_id] = self._failed_attempts.get(user_id, 0) + 1
        attempts = self._failed_attempts[user_id]
        
        # Get chat info for logging
        chat_id = update.effective_chat.id if update.effective_chat else None
        message_text = update.message.text if update.message else None
        
        logger.warning(
            f"Unauthorized access attempt from user {user_id} (@{username}), "
            f"attempt #{attempts}, message: {message_text[:50] if message_text else 'N/A'}...",
            extra={
                'user_id': user_id,
                'username': username,
                'chat_id': chat_id,
                'event': 'unauthorized_access',
                'attempt_count': attempts
            }
        )
    
    def require_auth(self):
        """Decorator for handlers that require authentication.
        
        Usage:
            @auth_manager.require_auth()
            async def my_handler(update, context):
                # Handler code here - only runs if authenticated
                pass
        """
        def decorator(func):
            async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
                user = self.authenticate(update)
                if not user:
                    if update.message:
                        await update.message.reply_text(
                            "⛔ Unauthorized. You are not allowed to use this bot."
                        )
                    return None
                
                # Store authenticated user in context for later use
                context.user_data['authenticated_user'] = user
                
                return await func(update, context)
            
            wrapper.__name__ = func.__name__
            return wrapper
        return decorator
    
    def get_allowed_user_count(self) -> int:
        """Get the number of allowed users."""
        return len(self._allowed_users)


# Global auth manager instance
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """Get the global auth manager instance."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


def reset_auth_manager() -> None:
    """Reset the auth manager (mainly for testing)."""
    global _auth_manager
    _auth_manager = None
