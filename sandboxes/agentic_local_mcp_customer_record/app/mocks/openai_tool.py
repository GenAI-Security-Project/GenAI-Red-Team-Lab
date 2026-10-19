"""OpenAI-compatible MCP tool loop backed by a local Ollama model."""

import asyncio
import json
import os
import traceback
from typing import Any, cast

from fastapi import APIRouter, Depends, Header, HTTPException
from openai import OpenAI
from pydantic import BaseModel

from mcp import ClientSession
from mcp.client.sse import sse_client

from .openai import ChatCompletionRequest, verify_api_key

# Configure Ollama as the backend
os.environ["OPENAI_API_KEY"] = "foo"
os.environ["OPENAI_BASE_URL"] = os.getenv(
    "OLLAMA_BASE_URL", "http://host.containers.internal:11434/v1"
)

router = APIRouter()

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://customer_record_mcp:8000/sse")
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "10"))

client = OpenAI(
    base_url=os.getenv("OLLAMA_BASE_URL", "http://host.containers.internal:11434/v1"),
    api_key="ollama",
)


def _create_completion(**kwargs: Any) -> Any:
    """Give the overloaded synchronous SDK method a stable async-call type."""
    return client.chat.completions.create(**kwargs)


@router.post("/v1/tool/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest, token: str = Depends(verify_api_key)
) -> Any:
    try:
        # Connect to the remote MCP server
        async with sse_client(url=MCP_SERVER_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Fetch available tools from MCP
                openai_tools = await fetch_mcp_tools(session)
                iterations = 0

                while iterations < MAX_ITERATIONS:
                    iterations += 1

                    # The OpenAI client is synchronous. Keep the event loop free
                    # so the MCP SSE session remains served during generation.
                    response = await asyncio.to_thread(
                        _create_completion,
                        model=request.model,
                        messages=request.messages,
                        temperature=request.temperature,
                        tools=openai_tools if openai_tools else None,
                        tool_choice="auto" if openai_tools else None,
                    )

                    response_message = cast(Any, response.choices[0].message)

                    # End loop if no more tool call is required to solve user query
                    if not response_message.tool_calls:
                        return response

                    # Preserve the assistant's tool-call request before adding results.
                    request.messages.append(
                        response_message.model_dump(exclude_none=True)
                    )

                    for tool_call in response_message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args_raw = tool_call.function.arguments

                        # Execute the tool on the MCP Server
                        print(
                            f"DEBUG: Executing MCP Tool: {tool_name} with {tool_args_raw} on iteration #{str(iterations)}"
                        )

                        try:
                            data = json.loads(tool_args_raw)
                            # Execute on MCP Server
                            tool_result = await session.call_tool(
                                tool_name, arguments=data
                            )

                            # Append tool call result to next function call
                            request.messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "name": tool_name,
                                    "content": getattr(
                                        tool_result.content[0],
                                        "text",
                                        str(tool_result.content[0]),
                                    ),
                                }
                            )

                        except Exception as tool_err:
                            # Handle execution failure so one bad tool doesn't crash the whole batch
                            request.messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": f"Error executing tool: {str(tool_err)}",
                                }
                            )

                # Preserve a useful response when the iteration budget is
                # exhausted instead of returning an empty body.
                return response

    except Exception as e:
        print(f"Workflow Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


async def fetch_mcp_tools(session: ClientSession) -> list[dict[str, Any]]:
    mcp_result = await session.list_tools()

    # Transform MCP tools into OpenAI/Ollama Function format
    openai_tools: list[dict[str, Any]] = []
    for tool in mcp_result.tools:
        # MCP 1.x exposed camelCase aliases while MCP 2.x uses Pydantic's
        # snake_case field. Accept both so lockfile updates do not break the lab.
        input_schema = cast(
            dict[str, Any],
            getattr(tool, "input_schema", None) or getattr(tool, "inputSchema", {}),
        )
        openai_tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or f"Use tool: {tool.name}",
                    "parameters": {
                        "type": "object",
                        "properties": input_schema.get("properties", {}),
                        "required": input_schema.get("required", []),
                    },
                },
            }
        )
    print(
        f"DEBUG: Tools available: {', '.join(tool['function']['name'] for tool in openai_tools)}"
    )

    return openai_tools
