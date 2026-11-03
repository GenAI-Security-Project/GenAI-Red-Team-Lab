"""OpenAI-compatible agent API with an approval gateway in front of MCP."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastapi import Depends, FastAPI

from app.live import build_gateway
from app.mocks.openai import ChatCompletionRequest, verify_api_key


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.gateway = build_gateway()
    yield
    for connection in app.state.gateway.connections.values():
        await connection.close()


app = FastAPI(
    title="Agentic MCP Rug Pull Sandbox",
    description="Agent loop with a configurable MCP tool-approval gateway",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/tool/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest, token: str = Depends(verify_api_key)
) -> Any:
    return await app.state.gateway.chat(
        request.messages, request.model, request.temperature or 0.0
    )


@app.get("/admin/tools")
async def admin_tools(token: str = Depends(verify_api_key)) -> Any:
    """Tools as a user reviewing approvals would see them."""
    return {"tools": await app.state.gateway.admin_tools()}


@app.post("/admin/reconnect")
async def admin_reconnect(token: str = Depends(verify_api_key)) -> Dict[str, str]:
    await app.state.gateway.reconnect()
    return {"status": "reconnected"}


@app.post("/admin/reset")
async def admin_reset(token: str = Depends(verify_api_key)) -> Dict[str, str]:
    await app.state.gateway.reconnect()
    app.state.gateway.reset()
    return {"status": "reset"}
