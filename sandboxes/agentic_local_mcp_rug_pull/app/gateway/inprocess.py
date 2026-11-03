"""In-process connection used by the deterministic replay and the tests.

It calls a server core directly instead of going through MCP over SSE. The
server core is the same code the containerised MCP server wraps, so tool
definitions, phase switches and the server-side log are identical.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Protocol


class ServerCore(Protocol):
    def list_tools(self) -> list[dict[str, Any]]: ...

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]: ...

    def on_list_changed(self, callback: Callable[[], None]) -> None: ...


class InProcessConnection:
    def __init__(self, server_id: str, core: ServerCore) -> None:
        self.server_id = server_id
        self.core = core

    async def list_tools(self) -> list[dict[str, Any]]:
        # Round-trip through JSON, as a real transport would.
        return json.loads(json.dumps(self.core.list_tools()))

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.core.call_tool(name, json.loads(json.dumps(arguments)))

    def on_list_changed(self, callback: Callable[[str], None]) -> None:
        self.core.on_list_changed(lambda: callback(self.server_id))

    async def reconnect(self) -> None:
        return None
