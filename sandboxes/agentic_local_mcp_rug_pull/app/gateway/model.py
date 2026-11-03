"""Deterministic stand-in for the LLM, used by ``make replay`` and tests.

``ScriptedModel`` behaves like a fully compliant model: whenever the
attacker's trigger text is in the tool descriptions it is given and the
attacker's tool is offered, it follows the recorded instruction (read the secret with the trusted tool, then send it to the
attacker's tool). Otherwise it performs the user's task once and stops.

It does not parse natural language. It answers one question
deterministically: *could a model that obeys the payload have leaked the
canary through this gateway configuration?* Whether a real model obeys is
what live mode measures.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
LOCALE_RE = re.compile(r"\b([a-z]{2}-[A-Z]{2})\b")


@dataclass(frozen=True)
class Directive:
    """Recorded attacker instruction, taken from a payload's ``replay`` block."""

    trigger: str
    read_tool: str
    read_arguments: dict[str, Any]
    exfil_tool: str
    exfil_argument: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Directive":
        return cls(
            trigger=str(data["trigger"]),
            read_tool=str(data["read_tool"]),
            read_arguments=dict(data.get("read_arguments", {})),
            exfil_tool=str(data["exfil_tool"]),
            exfil_argument=str(data["exfil_argument"]),
        )


class ScriptedModel:
    def __init__(self, directive: Directive | None, task_tool: str = "format_date"):
        self.directive = directive
        self.task_tool = task_tool
        self._counter = 0

    def _call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self._counter += 1
        return {
            "content": None,
            "tool_calls": [
                {
                    "id": f"call_{self._counter}",
                    "name": name,
                    "arguments": json.dumps(arguments, sort_keys=True),
                }
            ],
        }

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str = "scripted",
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        offered = {tool["function"]["name"] for tool in tools}
        last_user = max(i for i, m in enumerate(messages) if m.get("role") == "user")
        turn = messages[last_user:]
        task = _task_arguments(str(messages[last_user].get("content", "")))

        directive = self.directive
        if directive and directive.trigger in json.dumps(tools, ensure_ascii=False):
            read_index = _last_result_index(turn, directive.read_tool)
            exfil_done = read_index >= 0 and _called_after(
                turn, directive.exfil_tool, read_index
            )
            if directive.exfil_tool in offered and not exfil_done:
                secret = _last_result(turn, directive.read_tool)
                if secret is None and directive.read_tool in offered:
                    return self._call(directive.read_tool, directive.read_arguments)
                if secret is not None:
                    arguments = dict(task)
                    arguments[directive.exfil_argument] = secret
                    return self._call(directive.exfil_tool, arguments)

        if self.task_tool in offered and not _called_after(turn, self.task_tool, -1):
            return self._call(self.task_tool, task)

        answer = _last_result(turn, None) or "I could not complete the task."
        return {"content": answer, "tool_calls": []}


def _task_arguments(text: str) -> dict[str, str]:
    date = DATE_RE.search(text)
    locale = LOCALE_RE.search(text)
    return {
        "date": date.group(1) if date else "2026-01-01",
        "locale": locale.group(1) if locale else "en-GB",
    }


def _tool_call_names(message: dict[str, Any]) -> list[str]:
    return [c["function"]["name"] for c in message.get("tool_calls") or []]


def _called_after(turn: list[dict[str, Any]], name: str, index: int) -> bool:
    return any(
        name in _tool_call_names(m)
        for i, m in enumerate(turn)
        if i > index and m.get("role") == "assistant"
    )


def _last_result_index(turn: list[dict[str, Any]], name: str) -> int:
    for i in range(len(turn) - 1, -1, -1):
        if turn[i].get("role") == "tool" and turn[i].get("name") == name:
            return i
    return -1


def _last_result(turn: list[dict[str, Any]], name: str | None) -> str | None:
    for message in reversed(turn):
        if message.get("role") == "tool" and (
            name is None or message.get("name") == name
        ):
            return str(message.get("content", ""))
    return None
