"""Authentication and authorization module for A0 Telegram bot.

Manages user authentication and tracks user sessions.
"""

import logging
from typing import Optional, Dict, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AuthenticatedUser:
    """Represents an authenticated Telegram user."""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_admin: bool = False
    context_id: Optional[str] = None  # Current A0 conversation context
    current_project: Optional[str] = None  # Current A0 project
    message_count: int = 0  # Messages in current conversation
    failed_attempts: int = 0


class AuthManager:
    """Manages user authentication and authorization."""
    
    def __init__(self, allowed_users: List[int], admin_users: Optional[List[int]] = None):
        self.allowed_users = set(allowed_users)
        self.admin_users = set(admin_users or [])
        self._users: Dict[int, AuthenticatedUser] = {}
    
    def is_allowed(self, user_id: int) -> bool:
        """Check if a user ID is allowed to access the bot."""
        return user_id in self.allowed_users
    
    def is_admin(self, user_id: int) -> bool:
        """Check if a user ID is an admin."""
        return user_id in self.admin_users
    
    def get_user(self, user_id: int) -> Optional[AuthenticatedUser]:
        """Get or create an authenticated user."""
        if user_id not in self._users:
            if not self.is_allowed(user_id):
                return None
            self._users[user_id] = AuthenticatedUser(
                user_id=user_id,
                is_admin=self.is_admin(user_id)
            )
        return self._users[user_id]
    
    def get_user_by_chat_id(self, chat_id: int) -> Optional[AuthenticatedUser]:
        """Get user by chat ID (same as user ID for private chats)."""
        return self.get_user(chat_id)
    
    def update_user_info(self, user_id: int, username: Optional[str] = None,
                         first_name: Optional[str] = None, 
                         last_name: Optional[str] = None) -> None:
        """Update user information."""
        user = self.get_user(user_id)
        if user:
            if username:
                user.username = username
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
    
    def record_failed_attempt(self, user_id: int) -> int:
        """Record a failed authentication attempt."""
        if user_id not in self._users:
            self._users[user_id] = AuthenticatedUser(user_id=user_id)
        
        self._users[user_id].failed_attempts += 1
        return self._users[user_id].failed_attempts
    
    def clear_failed_attempts(self, user_id: int) -> None:
        """Clear failed authentication attempts for a user."""
        if user_id in self._users:
            self._users[user_id].failed_attempts = 0
    
    def set_context(self, user_id: int, context_id: str) -> None:
        """Set the A0 context ID for a user."""
        user = self.get_user(user_id)
        if user:
            user.context_id = context_id
    
    def clear_context(self, user_id: int) -> None:
        """Clear the A0 context ID for a user."""
        user = self.get_user(user_id)
        if user:
            user.context_id = None
    
    def set_project(self, user_id: int, project_name: str) -> None:
        """Set the current project for a user."""
        user = self.get_user(user_id)
        if user:
            user.current_project = project_name
            # Clear context when changing project
            user.context_id = None
    
    def clear_project(self, user_id: int) -> None:
        """Clear the current project for a user."""
        user = self.get_user(user_id)
        if user:
            user.current_project = None
    
    def get_all_users(self) -> List[AuthenticatedUser]:
        """Get all authenticated users."""
        return list(self._users.values())
