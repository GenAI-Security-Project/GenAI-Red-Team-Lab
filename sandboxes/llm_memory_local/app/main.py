"""FastAPI main application module.

Initializes the FastAPI application and mounts the mock OpenAI router that adds a
persistent, poisonable conversation-memory layer. Entry point for the LLM Memory Mock
API Server.
"""

from typing import Dict

from fastapi import FastAPI

from app.mocks import openai_router

app = FastAPI(
    title="LLM Memory Mock API Server",
    description=(
        "Mock API server for testing conversation memory poisoning locally. "
        "Adds persistent, scope-keyed memory on top of a local LLM chat endpoint."
    ),
    version="1.0.0",
)


@app.get("/health")
def health_check() -> Dict[str, str]:
    """Health check endpoint to verify the server is running.

    Returns:
        Dict[str, str]: Status dictionary with 'status' key set to 'ok'.
    """
    return {"status": "ok"}


# Mount mock service routers.
app.include_router(openai_router, tags=["OpenAI Mock (with memory)"])
