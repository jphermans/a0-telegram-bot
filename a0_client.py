"""A0 API Client for communicating with Agent Zero.

Handles HTTP communication with the A0 REST API.
"""

import asyncio
import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from typing import Optional, List, AsyncIterator, Any, Dict
from pathlib import Path

import aiohttp
from aiohttp import FormData, MultipartWriter

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
    
    async def __aenter__(self) -> "A0Client":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
    
    async def connect(self) -> None:
        """Initialize the HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self._timeout,
                headers=self._get_headers()
            )
            logger.info(f"A0 client connected to {self._endpoint}")
    
    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("A0 client session closed")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        return headers
    
    def _get_url(self, path: str) -> str:
        """Get full URL for API path."""
        base = self._endpoint.rstrip("/")
        return f"{base}{path}"
    
    async def health_check(self) -> bool:
        """Check if A0 API is healthy."""
        try:
            await self.connect()
            async with self._session.get(self._get_url("/")) as response:
                return response.status == 200
        except Exception as e:
            logger.warning(f"A0 health check failed: {e}")
            return False
    
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
        
        # Build JSON payload (matching nicolasleao/agent-zero-telegram format)
        payload: Dict[str, Any] = {
            "message": text,
            "text": text,
            "attachments": attachments or [],
        }
        if context_id:
            payload["context_id"] = context_id
        
        with LogContext(logger, "send_message", text_length=len(text), context_id=context_id):
            try:
                async with self._session.post(
                    self._get_url("/api_message"),
                    json=payload
                ) as response:
                    response_text = await response.text()
                    
                    if response.status == 200:
                        data = json.loads(response_text) if response_text.strip() else {}
                        result = A0Response.from_dict(data)
                        logger.info(
                            f"A0 response received",
                            extra={"context_id": result.context_id}
                        )
                        return result
                    else:
                        error_msg = f"A0 API error: {response.status} - {response_text[:200]}"
                        logger.error(error_msg)
                        return A0Response(
                            success=False,
                            error=error_msg
                        )
                        
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
        """Reset a chat's history in Agent Zero."""
        await self.connect()
        
        try:
            async with self._session.post(
                self._get_url("/api_reset_chat"),
                json={"context_id": context_id}
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Failed to reset chat: {e}")
            return False
    
    async def terminate_chat(self, context_id: str) -> bool:
        """Terminate a chat in Agent Zero."""
        await self.connect()
        
        try:
            async with self._session.post(
                self._get_url("/api_terminate_chat"),
                json={"context_id": context_id}
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Failed to terminate chat: {e}")
            return False


# Singleton client instance
_client: Optional[A0Client] = None


async def get_client() -> A0Client:
    """Get or create the A0 client singleton."""
    global _client
    if _client is None:
        _client = A0Client()
        await _client.connect()
    return _client


async def close_client() -> None:
    """Close the A0 client singleton."""
    global _client
    if _client:
        await _client.close()
        _client = None
