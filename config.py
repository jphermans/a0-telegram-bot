"""Configuration management for A0 Telegram bot.

Loads configuration from environment variables with sensible defaults.
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Telegram Configuration
    telegram_bot_token: str = Field(default="", description="Telegram bot token from @BotFather")
    telegram_allowed_users: str = Field(default="", description="Comma-separated list of allowed Telegram user IDs")
    
    # A0 Configuration
    a0_endpoint: str = Field(default="http://agent-zero:80", description="A0 API endpoint URL")
    a0_api_key: str = Field(default="", description="A0 API key for authentication")
    a0_timeout: int = Field(default=300, description="Timeout in seconds for A0 API requests")
    
    # Project Configuration
    telegram_projects: str = Field(default="", description="Comma-separated list of available project names")
    telegram_default_project: str = Field(default="", description="Default project to use if none selected")
    
    # Shared Volume Configuration
    shared_volume_path: str = Field(default="/shared", description="Path to shared volume for file attachments")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)")
    
    # Attachment limits
    max_attachment_size: int = Field(default=20 * 1024 * 1024, description="Maximum attachment size in bytes (default 20MB)")
    
    @property
    def allowed_users(self) -> List[int]:
        """Parse allowed users from comma-separated string."""
        if not self.telegram_allowed_users:
            return []
        return [int(u.strip()) for u in self.telegram_allowed_users.split(",") if u.strip().isdigit()]
    
    @property
    def projects(self) -> List[str]:
        """Parse available projects from comma-separated string."""
        if not self.telegram_projects:
            return []
        return [p.strip() for p in self.telegram_projects.split(",") if p.strip()]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
_settings: Optional[Settings] = None


def get_config() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_config() -> Settings:
    """Reload configuration from environment."""
    global _settings
    _settings = Settings()
    return _settings
