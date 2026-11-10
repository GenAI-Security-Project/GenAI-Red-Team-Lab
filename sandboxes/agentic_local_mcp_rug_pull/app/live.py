"""Live adapters: MCP over SSE and an Ollama-backed model.

``SseConnection`` has two modes, chosen from ``REFRESH_POLICY``:

* ``per_request``: a fresh MCP session per operation, like
  ``sandboxes/mcp_local``. The gateway re-lists tools at the start of every
  conversation, so it always sees the server's current definitions.
* ``on_list_changed`` and ``reconnect``: one persistent session per server.
  The gateway keeps the tool list cached; with ``on_list_changed`` it re-lists
  a server after ``notifications/tools/list_changed``, with ``reconnect`` only
  after ``POST /admin/reconnect`` (a client restart).

In every mode ``notifications/tools/list_changed`` is received and passed to
the gateway, which decides what to do with it (``app.gateway.core``).
"""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Callable, cast

from mcp import ClientSession
from mcp.client.sse import sse_client
from openai import OpenAI

from app.gateway.core import Gateway
from app.gateway.model import Directive, ScriptedModel
from app.gateway.policy import GatewayConfig


def _tool_to_dict(tool: Any) -> dict[str, Any]:
    return tool.model_dump(by_alias=True, exclude_none=True, mode="json")


def _result_to_dict(result: Any) -> dict[str, Any]:
    texts = [getattr(item, "text", str(item)) for item in result.content]
    return {
        "text": "\n".join(texts),
        "is_error": bool(getattr(result, "is_error", False)),
    }


class SseConnection:
    def __init__(self, server_id: str, url: str, persistent: bool) -> None:
        self.server_id = server_id
        self.url = url
        self.persistent = persistent
        self._callbacks: list[Callable[[str], None]] = []
        self._session: ClientSession | None = None
        self._task: asyncio.Task[None] | None = None
        self._stop: asyncio.Event | None = None
        self._lock = asyncio.Lock()

    def on_list_changed(self, callback: Callable[[str], None]) -> None:
        self._callbacks.append(callback)

    async def _message_handler(self, message: Any) -> None:
        method = getattr(message, "method", None)
        if method == "notifications/tools/list_changed":
            for callback in self._callbacks:
                callback(self.server_id)

    async def _run(self, ready: asyncio.Event) -> None:
        assert self._stop is not None
        async with sse_client(url=self.url) as (read, write):
            async with ClientSession(
                read, write, message_handler=self._message_handler
            ) as session:
                await session.initialize()
                self._session = session
                ready.set()
                await self._stop.wait()
        self._session = None

    async def _ensure(self) -> ClientSession:
        async with self._lock:
            return await self._connect()

    async def _connect(self) -> ClientSession:
        if self._session is not None:
            return self._session
        await self.close()  # drop any task left over from a failed connect
        self._stop = asyncio.Event()
        ready = asyncio.Event()
        task = asyncio.create_task(self._run(ready))
        self._task = task
        waiter = asyncio.ensure_future(ready.wait())
        done, _ = await asyncio.wait(
            {waiter, task}, timeout=30, return_when=asyncio.FIRST_COMPLETED
        )
        waiter.cancel()
        if task in done:
            # The connection failed (or closed) before it was ready.
            self._task = None
            task.result()
            raise ConnectionError(f"MCP session to {self.url} closed early")
        if not done:
            await self.close()
            raise TimeoutError(f"MCP session to {self.url} not ready after 30 s")
        assert self._session is not None
        return self._session

    async def close(self) -> None:
        task, self._task = self._task, None
        if self._stop is not None:
            self._stop.set()
        try:
            if task is not None:
                await asyncio.wait_for(task, timeout=10)
        except Exception:  # noqa: BLE001 - a dead session must not block reconnects
            pass
        finally:
            self._session = None
            self._stop = None

    async def reconnect(self) -> None:
        await self.close()

    @asynccontextmanager
    async def _ephemeral(self) -> AsyncIterator[ClientSession]:
        """One-off session; the server sends list_changed in the session of the call."""
        async with sse_client(url=self.url) as (read, write):
            async with ClientSession(
                read, write, message_handler=self._message_handler
            ) as session:
                await session.initialize()
                yield session

    async def list_tools(self) -> list[dict[str, Any]]:
        if self.persistent:
            try:
                result = await (await self._ensure()).list_tools()
            except Exception:
                # The server may have restarted: reopen the session once.
                # Listing is read-only, so a retry is safe (calls are not retried).
                await self.close()
                result = await (await self._ensure()).list_tools()
            return [_tool_to_dict(tool) for tool in result.tools]
        async with self._ephemeral() as session:
            result = await session.list_tools()
            return [_tool_to_dict(tool) for tool in result.tools]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if self.persistent:
            try:
                result = await (await self._ensure()).call_tool(name, arguments)
            except Exception:
                await self.close()  # a dead session is reopened on the next use
                raise
            return _result_to_dict(result)
        async with self._ephemeral() as session:
            return _result_to_dict(await session.call_tool(name, arguments))


class OllamaModel:
    """OpenAI-compatible chat completions against a local Ollama server."""

    def __init__(self, base_url: str) -> None:
        self.client = OpenAI(base_url=base_url, api_key="ollama")

    def _create(self, **kwargs: Any) -> Any:
        """Give the overloaded synchronous SDK method a stable type."""
        return self.client.chat.completions.create(**kwargs)

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str,
        temperature: float,
    ) -> dict[str, Any]:
        response = await asyncio.to_thread(
            self._create,
            model=model,
            messages=messages,
            temperature=temperature,
            tools=tools or None,
            tool_choice="auto" if tools else None,
        )
        message = cast(Any, response.choices[0].message)
        return {
            "content": message.content,
            "tool_calls": [
                {
                    "id": call.id,
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                }
                for call in message.tool_calls or []
            ],
        }


def build_gateway(env: dict[str, str] | None = None) -> Gateway:
    env = dict(os.environ if env is None else env)
    config = GatewayConfig.from_env(env)
    persistent = config.refresh_policy != "per_request"
    connections = {
        "workspace": SseConnection(
            "workspace",
            env.get("WORKSPACE_MCP_URL", "http://rug_pull_workspace:8000/sse"),
            persistent,
        ),
        "toolbox": SseConnection(
            "toolbox",
            env.get("TOOLBOX_MCP_URL", "http://rug_pull_toolbox:8000/sse"),
            persistent,
        ),
    }
    backend = env.get("MODEL_BACKEND", "ollama")
    model: Any
    if backend == "ollama":
        model = OllamaModel(
            env.get("OLLAMA_BASE_URL", "http://host.containers.internal:11434/v1")
        )
    elif backend == "scripted":
        directive = None
        directive_file = env.get("SCRIPTED_DIRECTIVE_FILE")
        if directive_file:
            with open(directive_file, encoding="utf-8") as handle:
                block = json.load(handle).get("replay")
            directive = Directive.from_dict(block) if block else None
        model = ScriptedModel(directive)
    else:
        raise ValueError("MODEL_BACKEND must be 'ollama' or 'scripted'")
    return Gateway(config, connections, model)
