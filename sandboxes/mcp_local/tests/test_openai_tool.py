"""Regression tests for MCP tool-call message ordering."""

import copy
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from app.mocks import openai_tool
from app.mocks.openai import ChatCompletionRequest


class AsyncContext:
    """Minimal async context manager used by the MCP client fakes."""

    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeAssistantMessage:
    """Assistant response containing one or more tool calls."""

    def __init__(self, tool_call_count=1):
        self.tool_calls = [
            SimpleNamespace(
                id=f"call-{index}",
                function=SimpleNamespace(
                    name=f"lookup-{index}",
                    arguments='{"query": "test"}',
                ),
            )
            for index in range(1, tool_call_count + 1)
        ]

    def model_dump(self, *, exclude_none):
        assert exclude_none is True
        return {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in self.tool_calls
            ],
        }


class FakeCompletions:
    """Record messages passed to consecutive completion calls."""

    def __init__(self, tool_call_count=1):
        self.calls = []
        self.responses = iter(
            [
                SimpleNamespace(
                    choices=[
                        SimpleNamespace(message=FakeAssistantMessage(tool_call_count))
                    ]
                ),
                SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[]))]
                ),
            ]
        )

    def create(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs["messages"]))
        return next(self.responses)


class ToolMessageOrderingTests(IsolatedAsyncioTestCase):
    async def run_completion(self, tool_result, tool_call_count=1):
        completions = FakeCompletions(tool_call_count)
        if isinstance(tool_result, BaseException):
            call_tool = AsyncMock(side_effect=tool_result)
        elif tool_call_count > 1:
            call_tool = AsyncMock(
                side_effect=[tool_result for _ in range(tool_call_count)]
            )
        else:
            call_tool = AsyncMock(return_value=tool_result)
        session = SimpleNamespace(
            initialize=AsyncMock(),
            call_tool=call_tool,
        )
        request = ChatCompletionRequest(
            model="test",
            messages=[{"role": "user", "content": "hello"}],
        )

        with (
            patch.object(
                openai_tool,
                "client",
                SimpleNamespace(chat=SimpleNamespace(completions=completions)),
            ),
            patch.object(
                openai_tool,
                "sse_client",
                lambda **kwargs: AsyncContext((object(), object())),
            ),
            patch.object(
                openai_tool,
                "ClientSession",
                lambda read, write: AsyncContext(session),
            ),
            patch.object(
                openai_tool,
                "fetch_mcp_tools",
                AsyncMock(return_value=[{"type": "function"}]),
            ),
        ):
            await openai_tool.chat_completions(request, token="test")

        return completions.calls

    def assert_valid_tool_message_order(self, calls):
        self.assertEqual(
            [message["role"] for message in calls[1]],
            ["user", "assistant", "tool"],
        )
        assistant_message, tool_message = calls[1][1:]
        self.assertEqual(
            assistant_message["tool_calls"][0]["id"],
            tool_message["tool_call_id"],
        )

    async def test_tool_result_follows_assistant_tool_call(self):
        calls = await self.run_completion(
            SimpleNamespace(content=[SimpleNamespace(text="result")])
        )

        self.assert_valid_tool_message_order(calls)
        self.assertEqual(calls[1][2]["content"], "result")

    async def test_tool_error_follows_assistant_tool_call(self):
        calls = await self.run_completion(RuntimeError("tool failed"))

        self.assert_valid_tool_message_order(calls)
        self.assertEqual(
            calls[1][2]["content"],
            "Error executing tool: tool failed",
        )

    async def test_multiple_tool_results_follow_one_assistant_message(self):
        calls = await self.run_completion(
            SimpleNamespace(content=[SimpleNamespace(text="result")]),
            tool_call_count=2,
        )

        self.assertEqual(
            [message["role"] for message in calls[1]],
            ["user", "assistant", "tool", "tool"],
        )
        self.assertEqual(
            [message["tool_call_id"] for message in calls[1][2:]],
            ["call-1", "call-2"],
        )
        self.assertEqual(len(calls[1][1]["tool_calls"]), 2)
