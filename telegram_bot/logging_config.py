"""Structured logging configuration for Telegram bot.

Provides centralized logging setup with structured output support.
"""

import logging
import sys
from datetime import datetime
from typing import Optional
from pythonjsonlogger import jsonlogger

from .config import get_config


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""
    
    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        log_record['service'] = 'telegram-bot'
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id
        if hasattr(record, 'chat_id'):
            log_record['chat_id'] = record.chat_id
        if hasattr(record, 'message_id'):
            log_record['message_id'] = record.message_id
        if hasattr(record, 'duration_ms'):
            log_record['duration_ms'] = record.duration_ms


def setup_logging(json_output: bool = False) -> logging.Logger:
    """Set up logging configuration.
    
    Args:
        json_output: If True, output JSON-formatted logs (for production/Docker)
    
    Returns:
        Configured logger instance
    """
    config = get_config()
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    
    if json_output:
        # JSON formatter for production/Docker
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s',
            rename_fields={'levelname': 'level', 'name': 'logger'}
        )
    else:
        # Human-readable formatter for development
        formatter = logging.Formatter(
            config.log_format,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('telegram.ext').setLevel(logging.INFO)
    
    return logging.getLogger('telegram_bot')


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.
    
    Args:
        name: Module name (usually __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LogContext:
    """Context manager for timing operations."""
    
    def __init__(self, logger: logging.Logger, operation: str, **extra):
        self.logger = logger
        self.operation = operation
        self.extra = extra
        self.start_time: Optional[float] = None
    
    def __enter__(self):
        self.start_time = datetime.utcnow().timestamp()
        self.logger.debug(f"Starting {self.operation}", extra=self.extra)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = int((datetime.utcnow().timestamp() - self.start_time) * 1000)
        extra = {**self.extra, 'duration_ms': duration_ms}
        
        if exc_type:
            self.logger.error(
                f"Failed {self.operation}: {exc_val}",
                extra=extra,
                exc_info=True
            )
        else:
            self.logger.debug(f"Completed {self.operation}", extra=extra)
        
        return False  # Don't suppress exceptions
