"""Mock OpenAI API implementation using Ollama as the backend.

This module provides a FastAPI router that mimics the OpenAI chat completions API,
routing requests to a local Ollama instance for testing purposes.
"""

import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from openai import OpenAI
from pydantic import BaseModel

from app import memory

# Configure Ollama as the backend
os.environ["OPENAI_API_KEY"] = "foo"
os.environ["OPENAI_BASE_URL"] = os.getenv(
    "OLLAMA_BASE_URL", "http://host.containers.internal:11434/v1"
)

router = APIRouter()
memory.init_db()


def verify_api_key(authorization: str = Header(...)) -> str:
    """Mock API key verification for testing purposes.

    In a real implementation, this would validate against a database or secret store.
    For testing purposes, we accept a simple mock key.

    Args:
        authorization: Authorization header value (e.g., "Bearer sk-mock-key").

    Returns:
        str: The extracted API key token.

    Raises:
        HTTPException: If authentication scheme is invalid or API key doesn't match.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    token = authorization.split(" ")[1]
    if token != "sk-mock-key":
        raise HTTPException(status_code=401, detail="Invalid API key")
    return token


class ChatCompletionRequest(BaseModel):
    """Request model for chat completions endpoint.

    Attributes:
        model: Name of the model to use (e.g., "gpt-oss:20b").
        messages: List of message dictionaries with 'role' and 'content' keys.
        temperature: Sampling temperature between 0 and 2. Defaults to 0.7.
        max_tokens: Maximum number of tokens to generate. Defaults to None.
        top_p: Nucleus sampling parameter. Defaults to None.
        stream: Whether to stream responses. Defaults to False.
        session_id: Optional conversation/session identifier used to scope
            (or, deliberately, fail to scope) persistent memory. If omitted,
            a new random session_id is generated per request.
    """

    model: str
    messages: List[Dict[str, Any]]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    stream: Optional[bool] = False
    session_id: Optional[str] = None


# Initialize OpenAI client with Ollama backend
client = OpenAI(
    base_url=os.getenv("OLLAMA_BASE_URL", "http://host.containers.internal:11434/v1"),
    api_key="ollama",
)


@router.post("/v1/chat/completions")
def chat_completions(
    request: ChatCompletionRequest, token: str = Depends(verify_api_key)
) -> Any:
    """Mock OpenAI chat completions endpoint, backed by Ollama and by
    persistent (and intentionally unscoped) memory.

    Before forwarding to Ollama, this endpoint prepends two things to the
    conversation: (1) every long-term fact ever stored, from any session
    (memory.build_memory_context()), and (2) this session's own recent
    history (memory.get_recent_history()). After the reply comes back,
    both the user's message and the assistant's reply are logged, and the
    user's message is scanned for a "remember that" trigger phrase that
    would promote it to long-term memory.

    Args:
        request: Chat completion request with model, messages, and parameters.
        token: Validated API key token from dependency injection.

    Returns:
        Any: OpenAI-compatible chat completion response object.

    Raises:
        HTTPException: If the Ollama backend returns an error (status 500).
    """
    session_id = request.session_id or str(uuid.uuid4())
    memory_context = memory.build_memory_context()
    history = memory.get_recent_history(session_id)
    composed_messages = []
    if memory_context:
        composed_messages.append({"role": "system", "content": memory_context})

    for role, content in history:
        composed_messages.append({"role": role, "content": content})
    composed_messages.extend(request.messages)

    for msg in request.messages:
        if msg["role"] == "user":
            memory.log_message(session_id, "user", msg["content"])
            memory.extract_and_store_facts(session_id, msg["content"])

    print(f"DEBUG: Received request with messages: {request.messages}")
    try:
        # Type ignore for messages - OpenAI client accepts dict format
        response = client.chat.completions.create(
            model=request.model,
            messages=composed_messages,  # type: ignore[arg-type]
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            stream=False if request.stream is None else request.stream,
        )
        assistant_reply = response.choices[0].message.content  # type: ignore[union-attr]
        memory.log_message(session_id, "assistant", assistant_reply)
        return response
    except Exception as e:
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/memory/facts")
def get_facts(token: str = Depends(verify_api_key)) -> Any:
    """
    Debug endpoint: list every long-term fact currently stored, regardless of session
    """
    fact_stored_check = memory.get_all_facts()
    return {"facts": fact_stored_check}


@router.post("/v1/memory/reset")
def reset_memory(token: str = Depends(verify_api_key)) -> Any:
    """Debug endpoint: wipe both memory tables (conversation_log and
    long_term_memory) for a clean-slate demo.
    """
    memory.reset_all()
    return {"status": "reset"}
