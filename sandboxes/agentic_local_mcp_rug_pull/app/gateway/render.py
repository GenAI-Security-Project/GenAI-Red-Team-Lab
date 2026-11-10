"""Convert MCP tool definitions into OpenAI-style function definitions.

This mirrors ``sandboxes/mcp_local/app/mocks/openai_tool.py``: name,
description and the ``properties``/``required`` parts of ``inputSchema`` reach
the model; annotations and ``_meta`` do not. Everything rendered here is
covered by the approval digest (``app.gateway.digest``).
"""

from __future__ import annotations

from typing import Any


def to_openai_function(tool: dict[str, Any]) -> dict[str, Any]:
    schema = tool.get("inputSchema") or {}
    description = tool.get("description") or f"Use tool: {tool['name']}"
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": description,
            "parameters": {
                "type": "object",
                "properties": schema.get("properties", {}),
                "required": schema.get("required", []),
            },
        },
    }
