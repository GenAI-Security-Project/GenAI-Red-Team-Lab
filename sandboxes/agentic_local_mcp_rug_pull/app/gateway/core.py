"""Transport-independent gateway: tool cache, approval gate and agent loop.

The same ``Gateway`` runs in two modes:

* live: connections are MCP client sessions over SSE (``app.live``) and the
  model is a local Ollama model;
* replay: connections call the server cores in-process and the model is the
  deterministic ``ScriptedModel`` (``app.gateway.model``).

Only the connections and the model differ, so the approval logic tested by the
replay is the code that runs in the container.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from app.gateway.policy import GatewayConfig, ToolDecision, decide, load_approvals
from app.gateway.render import to_openai_function


class Connection(Protocol):
    """What the gateway needs from one MCP server connection."""

    server_id: str

    async def list_tools(self) -> list[dict[str, Any]]: ...

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Return ``{"text": str, "is_error": bool}``."""
        ...

    def on_list_changed(self, callback: Callable[[str], None]) -> None: ...

    async def reconnect(self) -> None: ...


class Model(Protocol):
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str,
        temperature: float,
    ) -> dict[str, Any]:
        """Return ``{"content": str | None, "tool_calls": [{"id", "name", "arguments"}]}``."""
        ...


class EventLog:
    """Append-only JSONL log used for scoring."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def write(self, event: str, **fields: Any) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {"t": time.time(), "event": event, **fields}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)


class Gateway:
    def __init__(
        self,
        config: GatewayConfig,
        connections: Mapping[str, Connection],
        model: Model,
    ) -> None:
        self.config = config
        self.connections = connections
        self.model = model
        self.log = EventLog(config.event_log)
        self._cache: dict[str, list[dict[str, Any]]] = {}
        self._stale: set[str] = set(connections)
        for connection in connections.values():
            connection.on_list_changed(self._handle_list_changed)

    def _handle_list_changed(self, server_id: str) -> None:
        # ``on_list_changed`` re-lists the server before the next model turn,
        # as many MCP clients do. ``per_request`` re-lists at every
        # conversation anyway and ``reconnect`` waits for a client restart, so
        # both only log the notification.
        if self.config.refresh_policy == "on_list_changed":
            self._stale.add(server_id)
            self.log.write("list_changed", server=server_id, action="refresh")
        else:
            self.log.write("list_changed", server=server_id, action="ignored")

    async def _refresh(self, conversation_start: bool) -> None:
        policy = self.config.refresh_policy
        if policy == "per_request" and conversation_start:
            self._stale = set(self.connections)
        for server_id in sorted(self._stale):
            self._cache[server_id] = await self.connections[server_id].list_tools()
            self.log.write(
                "tools_listed",
                server=server_id,
                names=[tool["name"] for tool in self._cache[server_id]],
            )
        self._stale.clear()

    async def reconnect(self) -> None:
        """Simulate a client restart: reconnect and drop the cached tool list."""
        for connection in self.connections.values():
            await connection.reconnect()
        self._stale = set(self.connections)
        self.log.write("reconnect")

    def reset(self) -> None:
        self._cache.clear()
        self._stale = set(self.connections)
        self.log.clear()

    def decisions(self) -> list[ToolDecision]:
        approvals = load_approvals(self.config.approvals_file)
        return decide(self._cache, approvals, self.config)

    async def admin_tools(self) -> list[dict[str, Any]]:
        """What a user reviewing approvals would see right now.

        With ``per_request`` every interaction re-lists, including this one;
        with ``reconnect`` the user sees the cached list.
        """
        await self._refresh(
            conversation_start=self.config.refresh_policy == "per_request"
        )
        return [
            {
                "server": d.server,
                "name": d.name,
                "digest": d.digest,
                "offered": d.offered,
                "reason": d.reason,
                "definition": d.definition,
            }
            for d in self.decisions()
        ]

    async def chat(
        self, messages: list[dict[str, Any]], model: str, temperature: float
    ) -> dict[str, Any]:
        conversation = list(messages)
        content: str | None = None
        for turn in range(1, self.config.max_iterations + 1):
            await self._refresh(conversation_start=(turn == 1))
            decisions = self.decisions()
            offered = {d.name: d for d in decisions if d.offered}
            tools = [to_openai_function(d.definition) for d in offered.values()]
            self.log.write(
                "tools_decided",
                turn=turn,
                tools=[
                    {
                        "server": d.server,
                        "name": d.name,
                        "digest": d.digest,
                        "offered": d.offered,
                        "reason": d.reason,
                        # Keep withheld definitions as evidence of what the
                        # gate stopped; offered ones are in tools_rendered.
                        **({} if d.offered else {"definition": d.definition}),
                    }
                    for d in decisions
                ],
            )
            self.log.write("tools_rendered", turn=turn, tools=tools)

            reply = await self.model.complete(conversation, tools, model, temperature)
            content = reply.get("content")
            calls = reply.get("tool_calls") or []
            if not calls:
                break
            conversation.append(
                {
                    "role": "assistant",
                    "content": content or "",
                    "tool_calls": [
                        {
                            "id": call["id"],
                            "type": "function",
                            "function": {
                                "name": call["name"],
                                "arguments": call["arguments"],
                            },
                        }
                        for call in calls
                    ],
                }
            )
            for call in calls:
                text = await self._execute(call, offered)
                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "name": call["name"],
                        "content": text,
                    }
                )
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content or ""},
                    "finish_reason": "stop",
                }
            ],
        }

    async def _execute(
        self, call: dict[str, Any], offered: dict[str, ToolDecision]
    ) -> str:
        name = call["name"]
        raw = call.get("arguments") or "{}"
        try:
            arguments = json.loads(raw) if isinstance(raw, str) else dict(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            arguments = None
        if not isinstance(arguments, dict):
            self.log.write("blocked_call", name=name, raw=raw, blocked_by="bad_json")
            return "Error: arguments must be a JSON object."

        decision = offered.get(name)
        if decision is None:
            self.log.write(
                "blocked_call", name=name, arguments=arguments, blocked_by="not_offered"
            )
            return f"Error: tool {name} is not available."

        self.log.write(
            "tool_call", server=decision.server, name=name, arguments=arguments
        )
        result = await self.connections[decision.server].call_tool(name, arguments)
        text = str(result.get("text", ""))
        self.log.write(
            "tool_result",
            server=decision.server,
            name=name,
            text=text,
            is_error=bool(result.get("is_error")),
        )
        return text
