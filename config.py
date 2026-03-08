"""Configuration management for Telegram bot.

Handles environment variables, defaults, and runtime configuration.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional
from functools import lru_cache


@dataclass(frozen=True)
class Config:
    """Immutable configuration loaded from environment variables."""
    
    # Telegram configuration
    telegram_bot_token: str
    telegram_allowed_users: List[int]
    
    # A0 API configuration
    a0_endpoint: str
    a0_api_key: Optional[str]
    a0_timeout: int  # seconds
    
    # Bot behavior
    poll_timeout: int  # seconds
    poll_interval: float  # seconds
    max_retries: int
    retry_delay: float  # seconds
    
    # Logging
    log_level: str
    log_format: str
    
    # Features
    enable_attachments: bool
    max_attachment_size: int  # bytes
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        
        # Required: Telegram bot token
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        
        # Parse allowed users from comma-separated string
        allowed_users_str = os.getenv("TELEGRAM_ALLOWED_USERS", "")
        if not allowed_users_str:
            raise ValueError("TELEGRAM_ALLOWED_USERS environment variable is required")
        
        allowed_users = [
            int(user_id.strip())
            for user_id in allowed_users_str.split(",")
            if user_id.strip()
        ]
        
        if not allowed_users:
            raise ValueError("At least one allowed user ID must be specified")
        
        return cls(
            telegram_bot_token=bot_token,
            telegram_allowed_users=allowed_users,
            a0_endpoint=os.getenv("A0_ENDPOINT", "http://localhost:8000"),
            a0_api_key=os.getenv("A0_API_KEY"),
            a0_timeout=int(os.getenv("A0_TIMEOUT", "120")),
            poll_timeout=int(os.getenv("TELEGRAM_POLL_TIMEOUT", "30")),
            poll_interval=float(os.getenv("TELEGRAM_POLL_INTERVAL", "1.0")),
            max_retries=int(os.getenv("MAX_RETRIES", "5")),
            retry_delay=float(os.getenv("RETRY_DELAY", "5.0")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_format=os.getenv(
                "LOG_FORMAT",
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ),
            enable_attachments=os.getenv("ENABLE_ATTACHMENTS", "true").lower() == "true",
            max_attachment_size=int(os.getenv("MAX_ATTACHMENT_SIZE", str(20 * 1024 * 1024))),  # 20MB
        )
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of warnings."""
        warnings = []
        
        if len(self.telegram_allowed_users) == 0:
            warnings.append("No allowed users configured - bot will reject all messages")
        
        if not self.a0_endpoint.startswith(("http://", "https://")):
            warnings.append(f"A0 endpoint should start with http:// or https://")
        
        if self.a0_timeout < 30:
            warnings.append("A0 timeout is very short, may cause timeouts for long responses")
        
        return warnings


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Get cached configuration instance."""
    return Config.from_env()


def clear_config_cache() -> None:
    """Clear the configuration cache (mainly for testing)."""
    get_config.cache_clear()
