"""A0 API Client for communicating with Agent Zero.

Handles HTTP communication with the A0 REST API.
Files are sent as base64-encoded attachments as expected by the A0 API.
"""

import asyncio
import base64
import json
import logging
import os
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path

import aiohttp

from .config import get_config
from .logging_config import get_logger, LogContext

logger = get_logger(__name__)


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
        
        if self._api_key:
            logger.info(f"A0 API key loaded (length: {len(self._api_key)} chars)")
        else:
            logger.warning("A0 API key is NOT set - authentication will fail!")
    
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
    
    def _encode_file_to_base64(self, file_path: str) -> Optional[Dict[str, str]]:
        """Read a file and encode it as base64 for the A0 API.
        
        A0 expects attachments in format: {"filename": "name.pdf", "base64": "...content..."}
        
        Args:
            file_path: Path to the file to encode
            
        Returns:
            Dictionary with filename and base64 content, or None if failed
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"File not found: {file_path}")
                return None
            
            # Read file content
            with open(path, "rb") as f:
                file_content = f.read()
            
            # Encode as base64
            base64_content = base64.b64encode(file_content).decode('utf-8')
            
            logger.info(f"Encoded file {path.name} ({len(file_content)} bytes) to base64")
            
            return {
                "filename": path.name,
                "base64": base64_content
            }
            
        except Exception as e:
            logger.error(f"Failed to encode file {file_path}: {e}")
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
        
        # Process attachments - encode as base64 for A0 API
        encoded_attachments = []
        if attachments:
            for file_path in attachments:
                encoded = self._encode_file_to_base64(file_path)
                if encoded:
                    encoded_attachments.append(encoded)
            
            if encoded_attachments:
                logger.info(f"Prepared {len(encoded_attachments)} attachment(s) for A0")
        
        # Build payload
        payload: Dict[str, Any] = {
            "message": text,
        }
        
        if context_id:
            payload["context_id"] = context_id
        
        # Add attachments in the format A0 expects: [{"filename": "...", "base64": "..."}]
        if encoded_attachments:
            payload["attachments"] = encoded_attachments
        
        with LogContext(logger, "send_message", text_length=len(text), context_id=context_id, attachments=len(encoded_attachments)):
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
