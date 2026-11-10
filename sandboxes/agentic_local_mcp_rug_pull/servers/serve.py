"""Serve a server core (toolbox or workspace) over MCP SSE.

Usage: ``python servers/serve.py toolbox`` or ``python servers/serve.py workspace``.

Uses the low-level MCP server so that tool definitions, including ``_meta``,
are sent exactly as written in the definitions file. Admin routes are for the
lab harness only and are reachable only on the private container network.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import mcp_types as types
import uvicorn
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.types import Message, Receive, Scope, Send

sys.path.insert(0, str(Path(__file__).resolve().parent))

from toolbox_core import Toolbox  # noqa: E402
from workspace_core import Workspace  # noqa: E402

HERE = Path(__file__).resolve().parent
STATE_DIR = Path(os.getenv("STATE_DIR", "/tmp/rug_pull_state"))


def build_core(kind: str) -> Any:
    if kind == "toolbox":
        definitions = Path(
            os.getenv("TOOLBOX_DEFINITIONS", HERE / "toolbox_default.json")
        )
        return Toolbox.from_file(definitions, STATE_DIR / "toolbox_log.jsonl")
    if kind == "workspace":
        return Workspace(
            STATE_DIR / "workspace_log.jsonl",
            os.getenv("CANARY", "RTL-CANARY-UNSET"),
        )
    raise SystemExit("usage: serve.py toolbox|workspace")


def build_app(kind: str) -> Starlette:
    core = build_core(kind)
    pending_notify: list[bool] = []
    core.on_list_changed(lambda: pending_notify.append(True))

    async def list_tools(ctx: Any, params: Any) -> types.ListToolsResult:
        return types.ListToolsResult(
            tools=[types.Tool.model_validate(tool) for tool in core.list_tools()]
        )

    async def call_tool(ctx: Any, params: Any) -> types.CallToolResult:
        result = core.call_tool(params.name, dict(params.arguments or {}))
        if pending_notify:
            pending_notify.clear()
            await ctx.session.send_tool_list_changed()
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=result["text"])],
            is_error=result["is_error"],
        )

    server = Server(
        f"rug-pull-{kind}", on_list_tools=list_tools, on_call_tool=call_tool
    )
    sse = SseServerTransport("/messages/")
    options = server.create_initialization_options(
        notification_options=NotificationOptions(tools_changed=(kind == "toolbox"))
    )

    class HandleSse:
        """Plain ASGI app: ``connect_sse`` sends the whole response itself, so a
        request handler returning a ``Response`` afterwards would send a second one."""

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            completed = False

            async def tracked_send(message: Message) -> None:
                nonlocal completed
                if message["type"] == "http.response.body" and not message.get(
                    "more_body", False
                ):
                    completed = True
                await send(message)

            async with sse.connect_sse(scope, receive, tracked_send) as streams:
                await server.run(streams[0], streams[1], options)
            if not completed:
                # The client closed the stream: end the response so uvicorn does
                # not log "ASGI callable returned without completing response".
                await send(
                    {"type": "http.response.body", "body": b"", "more_body": False}
                )

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "server": kind})

    async def reset(request: Request) -> JSONResponse:
        body = await request.json() if await request.body() else {}
        if kind == "workspace":
            core.reset(str(body.get("canary", "RTL-CANARY-UNSET")))
        else:
            core.reset()
        pending_notify.clear()
        return JSONResponse({"status": "reset", "server": kind})

    return Starlette(
        routes=[
            Route("/health", endpoint=health, methods=["GET"]),
            Route("/admin/reset", endpoint=reset, methods=["POST"]),
            Route("/sse", endpoint=HandleSse(), methods=["GET"]),
            Mount("/messages/", app=sse.handle_post_message),
        ]
    )


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else ""
    uvicorn.run(
        build_app(kind),
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        log_level="warning",
    )
