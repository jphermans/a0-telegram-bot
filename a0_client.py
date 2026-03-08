"""A0 API Client for communicating with Agent Zero.

Handles HTTP communication with the A0 REST API.
Supports both JSON and multipart/form-data for file attachments.
"""

import asyncio
import base64
import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from typing import Optional, List, AsyncIterator, Any, Dict, IO, Union
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

        # Debug: Log if API key is present (without revealing it)
        if self._api_key:
            logger.info(f"A0 API key loaded (length: {len(self._api_key)} chars)")
        else:
            logger.warning("A0 API key is NOT set - authentication will fail!")

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
            )
            logger.info(f"A0 client connected to {self._endpoint}")

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("A0 client session closed")

    def _get_headers(self, include_content_type: bool = True) -> Dict[str, str]:
        """Get request headers."""
        headers = {
            "Accept": "application/json",
        }
        if self._api_key:
            headers["X-API-KEY"] = self._api_key
        return headers

    def _get_url(self, path: str) -> str:
        """Get full URL for API path."""
        base = self._endpoint.rstrip("/")
        return f"{base}{path}"

    async def health_check(self) -> bool:
        """Check if A0 API is healthy."""
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

    def _get_mime_type(self, file_path: str) -> str:
        """Get MIME type for a file."""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "application/octet-stream"

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

        # If no attachments, use simple JSON
        if not attachments:
            return await self._send_json(text, context_id)

        # With attachments, use multipart/form-data
        return await self._send_multipart(text, context_id, attachments)

    async def _send_json(
        self,
        text: str,
        context_id: Optional[str] = None
    ) -> A0Response:
        """Send a simple JSON message (no attachments)."""
        payload: Dict[str, Any] = {
            "message": text,
            "text": text,
        }
        if context_id:
            payload["context_id"] = context_id

        with LogContext(logger, "send_message", text_length=len(text), context_id=context_id):
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

    async def _send_multipart(
        self,
        text: str,
        context_id: Optional[str],
        attachments: List[str]
    ) -> A0Response:
        """Send a message with file attachments using multipart/form-data."""
        from aiohttp import FormData

        form = FormData()
        form.add_field("message", text)
        form.add_field("text", text)

        if context_id:
            form.add_field("context_id", context_id)

        # Add each attachment
        for i, file_path in enumerate(attachments):
            try:
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    logger.warning(f"Attachment file not found: {file_path}")
                    continue

                # Get file info
                file_name = file_path_obj.name
                mime_type = self._get_mime_type(str(file_path_obj))
                file_size = file_path_obj.stat().st_size

                # Check file size limit
                max_size = self._config.max_attachment_size
                if file_size > max_size:
                    logger.warning(
                        f"File too large: {file_name} ({file_size} > {max_size})"
                    )
                    continue

                # Add file to form
                with open(file_path, "rb") as f:
                    file_content = f.read()

                form.add_field(
                    f"attachments",
                    file_content,
                    filename=file_name,
                    content_type=mime_type
                )

                logger.info(
                    f"Added attachment: {file_name} ({file_size} bytes, {mime_type})"
                )

            except Exception as e:
                logger.error(f"Failed to add attachment {file_path}: {e}")
                continue

        with LogContext(
            logger,
            "send_multipart",
            text_length=len(text),
            context_id=context_id,
            attachment_count=len(attachments)
        ):
            try:
                async with self._session.post(
                    self._get_url("/api_message"),
                    data=form,
                    headers=self._get_headers(include_content_type=False)
                ) as response:
                    response_text = await response.text()

                    if response.status == 200:
                        data = json.loads(response_text) if response_text.strip() else {}
                        result = A0Response.from_dict(data)
                        logger.info(
                            f"A0 multipart response received",
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
                json={"context_id": context_id},
                headers=self._get_headers()
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
