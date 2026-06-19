"""Mock OpenAI API implementation using Ollama as the backend.

This module provides a FastAPI router that mimics the OpenAI chat completions API,
routing requests to a local Ollama instance for testing purposes.
"""

import json
import os
from typing import Any, Dict, List, Optional

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

# Initialize OpenAI client with Ollama backend
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp_container:8000/sse")
# Set a safety limit for recursive calls
MAX_ITERATIONS = 5

client = OpenAI(
    base_url=os.getenv("OLLAMA_BASE_URL", "http://host.containers.internal:11434/v1"),
    api_key="ollama",
)


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

                    # Ask LLM for response
                    response = client.chat.completions.create(
                        model=request.model,
                        messages=request.messages,
                        temperature=request.temperature,
                        tools=openai_tools if openai_tools else None,
                        tool_choice="auto" if openai_tools else None,
                    )

                    response_message = response.choices[0].message

                    # End loop if no more tool call is required to solve user query
                    if not response_message.tool_calls:
                        return response

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
                                    "content": tool_result.content[0].text,
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

    except Exception as e:
        print(f"Workflow Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def fetch_mcp_tools(session: ClientSession) -> [dict]:
    mcp_result = await session.list_tools()

    # Transform MCP tools into OpenAI/Ollama Function format
    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or f"Use tool: {tool.name}",
                "parameters": {
                    "type": "object",
                    "properties": tool.inputSchema.get("properties", {}),
                    "required": tool.inputSchema.get("required", []),
                },
            },
        }
        for tool in mcp_result.tools
    ]
    print(
        f"DEBUG: Tools available: {', '.join(tool['function']['name'] for tool in openai_tools)}"
    )

    return openai_tools
