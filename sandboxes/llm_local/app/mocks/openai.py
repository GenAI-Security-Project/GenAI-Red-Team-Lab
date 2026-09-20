"""Mock OpenAI API implementation using Ollama as the backend.

This module provides a FastAPI router that mimics the OpenAI chat completions API,
routing requests to a local Ollama instance for testing purposes.
"""

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from openai import OpenAI
from pydantic import BaseModel

# Configure Ollama as the backend
os.environ["OPENAI_API_KEY"] = "foo"
os.environ["OPENAI_BASE_URL"] = os.getenv(
    "OLLAMA_BASE_URL", "http://host.containers.internal:11434/v1"
)

router = APIRouter()


def verify_api_key(authorization: Optional[str] = Header(default=None)) -> str:
    """Mock API key verification for testing purposes.

    In a real implementation, this would validate against a database or secret store.
    For testing purposes, we accept a simple mock key.

    The header is declared optional so that a request sending none gets a 401 naming
    the expected credential, instead of FastAPI's 422 about a missing required header.
    The mock key is not a secret: `make up` prints it, both clients hardcode it, and
    four READMEs list it.

    Args:
        authorization: Authorization header value (e.g., "Bearer sk-mock-key").

    Returns:
        str: The extracted API key token.

    Raises:
        HTTPException: If the header is absent, the scheme is not Bearer, or the key
            does not match.
    """
    if authorization is None:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header",
        )
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
    """

    model: str
    messages: List[Dict[str, Any]]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    stream: Optional[bool] = False


# Initialize OpenAI client with Ollama backend
client = OpenAI(
    base_url=os.getenv("OLLAMA_BASE_URL", "http://host.containers.internal:11434/v1"),
    api_key="ollama",
)


class Model(BaseModel):
    """One entry of an OpenAI-compatible model list.

    Attributes:
        id: Model name as the backend knows it (e.g. "gpt-oss:20b").
        object: Always "model", for OpenAI client compatibility.
        created: Unix timestamp; the mock has no creation time, so 0.
        owned_by: Owner string; "ollama" for this sandbox.
    """

    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "ollama"


class ModelList(BaseModel):
    """Response model for the models endpoint.

    Attributes:
        object: Always "list", for OpenAI client compatibility.
        data: The available models.
    """

    object: str = "list"
    data: List[Model]


@router.get("/v1/models")
def list_models(token: str = Depends(verify_api_key)) -> ModelList:
    """Mock OpenAI models endpoint, answered from the sandbox's own configuration.

    Clients call this route to find out whether the sandbox is up before they send
    anything. It therefore does NOT ask Ollama: a sandbox that is running but still
    pulling a model would answer 500, which is the same false negative as the 404
    this endpoint replaces, one layer down.

    The trade-off: listing from config can advertise a model that the first completion
    then fails on. POST /v1/chat/completions still surfaces backend failures as a 500,
    so the caller learns about the backend from the request it wanted to make.

    Args:
        token: Validated API key token from dependency injection.

    Returns:
        ModelList: The model this sandbox is configured to serve.
    """
    return ModelList(data=[Model(id=os.getenv("OLLAMA_MODEL", "gpt-oss:20b"))])


@router.post("/v1/chat/completions")
def chat_completions(
    request: ChatCompletionRequest, token: str = Depends(verify_api_key)
) -> Any:
    """Mock OpenAI chat completions endpoint using Ollama as the backend.

    This endpoint mimics the OpenAI API but routes requests to a local Ollama instance.
    Useful for testing LLM applications without incurring API costs.

    Args:
        request: Chat completion request with model, messages, and parameters.
        token: Validated API key token from dependency injection.

    Returns:
        Any: OpenAI-compatible chat completion response object.

    Raises:
        HTTPException: If the Ollama backend returns an error (status 500).
    """
    print(f"DEBUG: Received request with messages: {request.messages}")
    try:
        # Type ignore for messages - OpenAI client accepts dict format
        response = client.chat.completions.create(
            model=request.model,
            messages=request.messages,  # type: ignore[arg-type]
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            stream=False if request.stream is None else request.stream,
        )
        return response
    except Exception as e:
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))
