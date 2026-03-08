"""A0 API Client for communicating with Agent Zero.

Handles HTTP communication with the A0 REST API.
Uses shared volume for file attachments.
"""

import asyncio
import json
import logging
import mimetypes
import os
import shutil
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

import aiohttp

from .config import get_config
from .logging_config import get_logger, LogContext

logger = get_logger(__name__)

# Shared volume path for file exchange between containers
SHARED_VOLUME_PATH = os.getenv("SHARED_VOLUME_PATH", "/shared")


@dataclass
class A0Response:
    """Response from A0 API."""
    success: bool
    message: Optional[str] = None
    context_id: Optional[str] = None
    error: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "A0Response":
        """Create response from API response dict."""
        return cls(
            success="response" in data and data.get("response") is not None,
            message=data.get("response"),
            context_id=data.get("context_id"),
            error=data.get("error"),
            raw_response=data
        )


class A0Client:
    """Async client for A0 API communication."""
    
    def __init__(self, endpoint: Optional[str] = None, api_key: Optional[str] = None):
        self._config = get_config()
        self._endpoint = endpoint or self._config.a0_endpoint
        self._api_key = api_key or self._config.a0_api_key
        self._session: Optional[aiohttp.ClientSession] = None
        self._timeout = aiohttp.ClientTimeout(total=self._config.a0_timeout)
        
        # Ensure shared volume exists
        self._ensure_shared_volume()
        
        if self._api_key:
            logger.info(f"A0 API key loaded (length: {len(self._api_key)} chars)")
        else:
            logger.warning("A0 API key is NOT set - authentication will fail!")
    
    def _ensure_shared_volume(self):
        """Ensure the shared volume directory exists."""
        try:
            shared_path = Path(SHARED_VOLUME_PATH)
            shared_path.mkdir(parents=True, exist_ok=True)
            # Create telegram subfolder
            telegram_path = shared_path / "telegram_uploads"
            telegram_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Shared volume ready: {SHARED_VOLUME_PATH}")
        except Exception as e:
            logger.warning(f"Could not create shared volume: {e}")
    
    async def __aenter__(self) -> "A0Client":
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
    
    async def connect(self) -> None:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
            logger.info(f"A0 client connected to {self._endpoint}")
    
    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("A0 client session closed")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {"Accept": "application/json"}
        if self._api_key:
            headers["X-API-KEY"] = self._api_key
        return headers
    
    def _get_url(self, path: str) -> str:
        base = self._endpoint.rstrip("/")
        return f"{base}{path}"
    
    async def health_check(self) -> bool:
        try:
            await self.connect()
            async with self._session.get(
                self._get_url("/"),
                headers=self._get_headers()
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.warning(f"A0 health check failed: {e}")
            return False
    
    def _copy_to_shared_volume(self, file_path: str) -> Optional[str]:
        """Copy file to shared volume and return the path A0 can access.
        
        Returns:
            Path that A0 can use to access the file, or None if failed
        """
        try:
            source = Path(file_path)
            if not source.exists():
                logger.error(f"Source file not found: {file_path}")
                return None
            
            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_name = f"{timestamp}_{source.name}"
            
            # Copy to shared volume
            shared_path = Path(SHARED_VOLUME_PATH) / "telegram_uploads" / unique_name
            shutil.copy2(str(source), str(shared_path))
            
            logger.info(f"Copied file to shared volume: {shared_path}")
            
            # Return the path A0 should use (also via shared volume)
            # A0 will access it at /a0/usr/workdir/shared/telegram_uploads/<filename>
            return f"/a0/usr/workdir/shared/telegram_uploads/{unique_name}"
            
        except Exception as e:
            logger.error(f"Failed to copy file to shared volume: {e}")
            return None
    
    async def send_message(
        self,
        text: str,
        context_id: Optional[str] = None,
        attachments: Optional[List[str]] = None
    ) -> A0Response:
        """Send a message to A0 and get response.
        
        Args:
            text: Message text to send
            context_id: Optional conversation context ID
            attachments: Optional list of file paths to attach
        
        Returns:
            A0Response with the result
        """
        await self.connect()
        
        # Process attachments if any
        attachment_paths = []
        if attachments:
            for file_path in attachments:
                shared_path = self._copy_to_shared_volume(file_path)
                if shared_path:
                    attachment_paths.append(shared_path)
            
            if attachment_paths:
                logger.info(f"Attachments prepared for A0: {attachment_paths}")
        
        # Build payload
        payload: Dict[str, Any] = {
            "message": text,
        }
        
        if context_id:
            payload["context_id"] = context_id
        
        # Add attachments to payload - A0 expects them in this format
        if attachment_paths:
            payload["attachments"] = attachment_paths
        
        with LogContext(logger, "send_message", text_length=len(text), context_id=context_id, attachments=len(attachment_paths)):
            try:
                async with self._session.post(
                    self._get_url("/api_message"),
                    json=payload,
                    headers=self._get_headers()
                ) as response:
                    response_text = await response.text()
                    
                    if response.status == 200:
                        data = json.loads(response_text) if response_text.strip() else {}
                        result = A0Response.from_dict(data)
                        logger.info(f"A0 response received", extra={"context_id": result.context_id})
                        return result
                    else:
                        error_msg = f"A0 API error: {response.status} - {response_text[:200]}"
                        logger.error(error_msg)
                        return A0Response(success=False, error=error_msg)
                        
            except aiohttp.ClientError as e:
                error_msg = f"A0 connection error: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return A0Response(success=False, error=error_msg)
            except json.JSONDecodeError as e:
                error_msg = f"A0 response parse error: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return A0Response(success=False, error=error_msg)
            except Exception as e:
                error_msg = f"A0 unexpected error: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return A0Response(success=False, error=error_msg)
    
    async def reset_chat(self, context_id: str) -> bool:
        await self.connect()
        try:
            async with self._session.post(
                self._get_url("/api_reset_chat"),
                json={"context_id": context_id},
                headers=self._get_headers()
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Failed to reset chat: {e}")
            return False
    
    async def terminate_chat(self, context_id: str) -> bool:
        await self.connect()
        try:
            async with self._session.post(
                self._get_url("/api_terminate_chat"),
                json={"context_id": context_id},
                headers=self._get_headers()
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Failed to terminate chat: {e}")
            return False


# Singleton client instance
_client: Optional[A0Client] = None


async def get_client() -> A0Client:
    global _client
    if _client is None:
        _client = A0Client()
        await _client.connect()
    return _client


async def close_client() -> None:
    global _client
    if _client:
        await _client.close()
        _client = None
