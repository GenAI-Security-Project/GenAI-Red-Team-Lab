"""Request model and mock API-key check shared with the other MCP sandboxes."""

from typing import Any, Dict, List, Optional

from fastapi import Header, HTTPException
from pydantic import BaseModel

MOCK_API_KEY = "sk-mock-key"


def verify_api_key(authorization: str = Header(...)) -> str:
    """Accept only ``Bearer sk-mock-key``; this is a lab, not an auth scheme."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    token = authorization.split(" ", 1)[1]
    if token != MOCK_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return token


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Dict[str, Any]]
    temperature: Optional[float] = 0.0
