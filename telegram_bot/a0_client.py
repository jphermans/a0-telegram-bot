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
        project: Optional[str] = None
    ) -> A0Response:
        """Send a message to A0.
        
        Args:
            text: The message text
            context_id: Optional conversation context ID
            attachments: Optional list of attachments with 'filename' and 'base64' keys
            project: Optional project name to use for the conversation
        
        Returns:
            A0Response with success status and response/error
        """
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
                body["project"] = project
            
            # Add attachments if provided (base64-encoded)
            if attachments:
                body["attachments"] = attachments
            
            headers = {
                "Content-Type": "application/json",
                "X-API-KEY": self.api_key
            }
            
            logger.debug(f"Sending to A0: project={project}, context_id={context_id}, has_attachments={bool(attachments)}")
            
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
                else:
                    error_text = await response.text()
                    logger.error(f"A0 API error: {response.status} - {error_text}")
                    return A0Response(
                        success=False,
                        error=f"API error: {response.status} - {error_text}"
                    )
        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to A0: {e}")
            return A0Response(
                success=False,
                error=f"Connection error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return A0Response(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )
    
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
