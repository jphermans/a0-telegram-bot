"""A0 (Agent Zero) API client for Telegram bot.

Handles communication with the A0 API endpoint.
"""

import aiohttp
import base64
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class A0Response:
    """Response from A0 API."""
    success: bool
    response: Optional[str] = None
    context_id: Optional[str] = None
    error: Optional[str] = None


class A0Client:
    """Client for communicating with A0 API."""
    
    def __init__(self, endpoint: str, api_key: str, timeout: int = 300):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session
    
    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def health_check(self) -> bool:
        """Check if A0 is healthy."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.endpoint}/health") as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def _encode_file_to_base64(self, file_bytes: bytes, filename: str) -> Dict[str, str]:
        """Encode file content to base64."""
        return {
            "filename": filename,
            "base64": base64.b64encode(file_bytes).decode("utf-8")
        }
    
    async def send_message(
        self,
        text: str,
        context_id: Optional[str] = None,
        attachments: Optional[List[Dict[str, str]]] = None,
        project: Optional[str] = None,
        max_retries: int = 3
    ) -> A0Response:
        """Send a message to A0 with retry logic.
        
        Args:
            text: The message text
            context_id: Optional conversation context ID
            attachments: Optional list of attachments with 'filename' and 'base64' keys
            project: Optional project name to use for the conversation
            max_retries: Maximum number of retry attempts (default: 3)
        
        Returns:
            A0Response with success status and response/error
        """
        import asyncio
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                session = await self._get_session()
                
                # Build request body
                body: Dict[str, Any] = {
                    "message": text
                }
                
                # Add context_id if provided (for continuing conversations)
                if context_id:
                    body["context_id"] = context_id
                
                # Add project if provided (for project-specific conversations)
                # Only send project on first message (no context_id)
                if project and not context_id:
                    body["project_name"] = project
                
                # Add attachments if provided (base64-encoded)
                if attachments:
                    body["attachments"] = attachments
                
                headers = {
                    "Content-Type": "application/json",
                    "X-API-KEY": self.api_key
                }
                
                logger.debug(f"Sending to A0 (attempt {attempt + 1}/{max_retries}): project={project}, context_id={context_id}")
                
                async with session.post(
                    f"{self.endpoint}/api_message",
                    json=body,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return A0Response(
                            success=True,
                            response=data.get("response"),
                            context_id=data.get("context_id")
                        )
                    elif response.status == 404:
                        # Context not found - don't retry, return immediately
                        error_text = await response.text()
                        logger.warning(f"Context not found: {context_id}")
                        return A0Response(
                            success=False,
                            error=f"Context not found (404)"
                        )
                    elif response.status == 401:
                        # Auth error - don't retry
                        return A0Response(
                            success=False,
                            error="Authentication failed - check A0_API_KEY"
                        )
                    elif response.status == 503:
                        # Service unavailable - A0 might be busy, retry with backoff
                        last_error = "A0 is busy processing, please wait..."
                        logger.warning(f"A0 busy (503), attempt {attempt + 1}/{max_retries}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(5 * (attempt + 1))  # 5s, 10s, 15s
                            continue
                    elif response.status == 504:
                        # Gateway timeout - A0 taking too long, retry
                        last_error = "A0 request timed out, retrying..."
                        logger.warning(f"A0 timeout (504), attempt {attempt + 1}/{max_retries}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(10 * (attempt + 1))  # 10s, 20s, 30s
                            continue
                    else:
                        error_text = await response.text()
                        logger.error(f"A0 API error: {response.status} - {error_text}")
                        
                        # Parse error for better message
                        error_msg = self._parse_error_message(response.status, error_text)
                        return A0Response(
                            success=False,
                            error=error_msg
                        )
                        
            except aiohttp.ClientError as e:
                last_error = f"Connection error: {str(e)}"
                logger.error(f"Failed to connect to A0 (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(3 * (attempt + 1))  # 3s, 6s, 9s
                    continue
            except asyncio.TimeoutError:
                last_error = "Request timed out - A0 may be processing"
                logger.warning(f"Timeout (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5 * (attempt + 1))
                    continue
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return A0Response(
                    success=False,
                    error=f"Unexpected error: {str(e)}"
                )
        
        # All retries exhausted
        return A0Response(
            success=False,
            error=last_error or "Request failed after multiple attempts"
        )
    
    def _parse_error_message(self, status_code: int, error_text: str) -> str:
        """Parse error response to provide user-friendly message."""
        error_messages = {
            400: "Bad request - invalid message format",
            401: "Authentication failed - check A0_API_KEY",
            403: "Access forbidden - check API permissions",
            404: "Resource not found (context may have expired)",
            408: "Request timeout - A0 is slow, try again",
            429: "Too many requests - please wait a moment",
            500: "A0 internal server error",
            502: "A0 gateway error - service may be restarting",
            503: "A0 is busy - please wait",
            504: "A0 gateway timeout - request took too long",
        }
        
        base_msg = error_messages.get(status_code, f"API error ({status_code})")
        
        # Try to extract more detail from error_text
        if "context" in error_text.lower():
            return f"{base_msg} - context issue"
        elif "timeout" in error_text.lower():
            return f"{base_msg} - processing timeout"
        elif "memory" in error_text.lower():
            return f"{base_msg} - memory issue"
        
        return base_msg
    
    async def get_context(self, context_id: str) -> Optional[Dict[str, Any]]:
        """Get context information from A0."""
        try:
            session = await self._get_session()
            headers = {
                "X-API-KEY": self.api_key
            }
            
            async with session.get(
                f"{self.endpoint}/api_context/{context_id}",
                headers=headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            logger.error(f"Failed to get context: {e}")
            return None
