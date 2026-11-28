"""OpenAI-compatible agent API for the customer-record sandbox."""

from typing import Dict

from fastapi import FastAPI

from app.mocks import openai_router, openai_tool_router

app = FastAPI(
    title="Agentic Customer Record Sandbox",
    description="Local agent loop for MCP customer-record security testing",
    version="1.0.0",
)


@app.get("/health")
def health_check() -> Dict[str, str]:
    """Health check endpoint to verify the server is running.

    Returns:
        Dict[str, str]: Status dictionary with 'status' key set to 'ok'.
    """
    return {"status": "ok"}


app.include_router(openai_router, tags=["OpenAI Mock"])
app.include_router(openai_tool_router, tags=["OpenAI Tool Mock"])
