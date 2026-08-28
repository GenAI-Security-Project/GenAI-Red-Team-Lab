"""Mock OpenAI chat API with persistent, poisonable conversation memory.

This mock mirrors ``sandboxes/llm_local`` but adds a long-term memory layer around the
chat endpoint:

1. Before the model is called, every memory stored for the request's scope is loaded
   and injected as a leading system message (the injection sink).
2. After the model responds, the latest user message is scanned for memory directives
   ("remember that ...") and any match is written back to the store (the write path).

Because memory is keyed by scope and not by conversation, a directive planted in one
session is injected into every later session that shares the scope. That is the
Conversation Memory Poisoning behaviour this sandbox exists to demonstrate.
"""

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from openai import OpenAI
from pydantic import BaseModel

from app.memory.store import (
    DEFAULT_SCOPE,
    MemoryStore,
    build_memory_preamble,
)

# Configure Ollama as the backend, matching the llm_local mock.
os.environ["OPENAI_API_KEY"] = "foo"
os.environ["OPENAI_BASE_URL"] = os.getenv(
    "OLLAMA_BASE_URL", "http://host.containers.internal:11434/v1"
)

router = APIRouter()

# The memory database lives under the container's mounted ``data/`` directory so
# poisoned state survives restarts, exactly like a production memory feature would.
memory_store = MemoryStore(os.getenv("MEMORY_DB_PATH", "data/memory.db"))


def verify_api_key(authorization: str = Header(...)) -> str:
    """Mock API key verification for testing purposes.

    Args:
        authorization: Authorization header value (e.g., "Bearer sk-mock-key").

    Returns:
        str: The extracted API key token.

    Raises:
        HTTPException: If the scheme is invalid or the API key does not match.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    token = authorization.split(" ")[1]
    if token != "sk-mock-key":
        raise HTTPException(status_code=401, detail="Invalid API key")
    return token


class ChatCompletionRequest(BaseModel):
    """Request model for the chat completions endpoint.

    Attributes:
        model: Name of the model to use (e.g., "gpt-oss:20b").
        messages: List of message dictionaries with 'role' and 'content' keys.
        temperature: Sampling temperature between 0 and 2. Defaults to 0.7.
        max_tokens: Maximum number of tokens to generate. Defaults to None.
        top_p: Nucleus sampling parameter. Defaults to None.
        stream: Whether to stream responses. Defaults to False.
    """

    model: str
    messages: List[Dict[str, Any]]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    stream: Optional[bool] = False


# Initialize the OpenAI client pointed at the Ollama backend.
client = OpenAI(
    base_url=os.getenv("OLLAMA_BASE_URL", "http://host.containers.internal:11434/v1"),
    api_key="ollama",
)


def _latest_user_content(messages: List[Dict[str, Any]]) -> str:
    """Return the text of the most recent user message, or an empty string."""
    for message in reversed(messages):
        if message.get("role") == "user":
            content = message.get("content", "")
            return content if isinstance(content, str) else ""
    return ""


@router.post("/v1/chat/completions")
def chat_completions(
    request: ChatCompletionRequest,
    token: str = Depends(verify_api_key),
    x_memory_scope: Optional[str] = Header(default=None),
) -> Any:
    """Chat completion with memory recall on the way in and memory writes on the way out.

    Args:
        request: Chat completion request with model, messages, and parameters.
        token: Validated API key token from dependency injection.
        x_memory_scope: Optional memory scope header. Sessions that share a scope share
            memory; when absent, the default scope is used.

    Returns:
        Any: OpenAI-compatible chat completion response object.

    Raises:
        HTTPException: If the Ollama backend returns an error (status 500).
    """
    scope = x_memory_scope or DEFAULT_SCOPE

    # 1) Recall: inject everything remembered for this scope as leading system context.
    remembered = memory_store.get_memories(scope)
    preamble = build_memory_preamble(remembered)
    messages: List[Dict[str, Any]] = list(request.messages)
    if preamble:
        messages = [{"role": "system", "content": preamble}] + messages

    print(f"DEBUG: scope={scope} injected_memories={len(remembered)}")
    try:
        response = client.chat.completions.create(
            model=request.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            stream=False if request.stream is None else request.stream,
        )
    except Exception as e:
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # 2) Write: persist any memory directives found in the latest user message.
    stored = memory_store.remember_from_message(scope, _latest_user_content(messages))
    if stored:
        print(f"DEBUG: stored {len(stored)} memory directive(s) into scope={scope}")

    return response


@router.get("/memory")
def list_memory(
    scope: str = DEFAULT_SCOPE, token: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """Inspect the memories persisted for a scope (used to verify poisoning)."""
    return {"scope": scope, "memories": memory_store.get_memories(scope)}


@router.delete("/memory")
def reset_memory(
    scope: Optional[str] = None, token: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """Clear stored memory for a scope, or all scopes when none is given."""
    removed = memory_store.clear(scope)
    return {"cleared": removed, "scope": scope if scope is not None else "ALL"}
