"""Configuration management for A0 Telegram bot.

Loads configuration from environment variables with sensible defaults.
"""

import os
from typing import List, Optional


class Config:
    """Application settings loaded from environment variables."""
    
    def __init__(self):
        # Telegram Configuration
        self.telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_allowed_users: str = os.getenv("TELEGRAM_ALLOWED_USERS", "")
        self.telegram_userid: str = os.getenv("TELEGRAM_USERID", "")
        
        # A0 Configuration
        self.a0_endpoint: str = os.getenv("A0_ENDPOINT", "http://agent-zero:80")
        self.a0_api_key: str = os.getenv("A0_API_KEY", "")
        self.a0_timeout: int = int(os.getenv("A0_TIMEOUT", "300"))
        
        # Project Configuration
        self.telegram_projects: str = os.getenv("TELEGRAM_PROJECTS", "")
        self.telegram_default_project: str = os.getenv("TELEGRAM_DEFAULT_PROJECT", "")
        
        # Shared Volume Configuration
        self.shared_volume_path: str = os.getenv("SHARED_VOLUME_PATH", "/shared")
        
        # Logging
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        
        # Attachment limits
        self.max_attachment_size: int = 20 * 1024 * 1024  # 20MB
    
    def _is_secret_placeholder(self, value: str) -> bool:
        """Check if a value is a secret placeholder like §§secret(...)"""
        return value.strip().startswith("§§secret(")
    
    def _parse_user_ids(self, value: str) -> List[int]:
        """Parse comma-separated user IDs, skipping non-numeric values."""
        if not value or self._is_secret_placeholder(value):
            return []
        return [int(u.strip()) for u in value.split(",") if u.strip().isdigit()]
    
    @property
    def allowed_users(self) -> List[int]:
        """Parse allowed users from comma-separated string.
        
        Checks TELEGRAM_USERID first (the actual variable in user's .env),
        then falls back to TELEGRAM_ALLOWED_USERS.
        Skips secret placeholders like §§secret(...)
        """
        # First try TELEGRAM_USERID (primary variable in user's .env)
        if self.telegram_userid and not self._is_secret_placeholder(self.telegram_userid):
            return self._parse_user_ids(self.telegram_userid)
        # Fall back to TELEGRAM_ALLOWED_USERS
        if self.telegram_allowed_users and not self._is_secret_placeholder(self.telegram_allowed_users):
            return self._parse_user_ids(self.telegram_allowed_users)
        return []
    
    @property
    def projects(self) -> List[str]:
        """Parse available projects from comma-separated string."""
        if self.telegram_projects:
            return [p.strip() for p in self.telegram_projects.split(",") if p.strip()]
        return []


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config
