"""Model backends for the agent.

Two backends share one interface: ``complete(messages) -> str``. The agent reads
``TOOL:`` and ``ANSWER:`` lines out of the returned text, so neither backend
depends on provider-specific function calling.

``ScriptedModel`` is deterministic and offline. It plays the part of a plausibly
compromised agent: given an undefended run it follows a skill's hidden
instructions and setup steps; given the defensive system prompt it refuses them.
That makes the offline tests reproducible and lets the lab show each defense
changing the outcome. ``HttpModel`` talks to any OpenAI-compatible endpoint
(Ollama by default) for runs against a real model.
"""

from __future__ import annotations

import json
import re
import urllib.request

from .tools import SECRET_SENTINEL

SECURITY_POLICY_MARKER = "SECURITY POLICY"

_ENV_PATH = "data/.env"
_DANGER_HINT = re.compile(
    r"\.env|exfiltrat|append its|secret|credential", re.IGNORECASE
)


def _skill_body(messages: list[dict]) -> str:
    for m in messages:
        if m["role"] == "user":
            return m["content"]
    return ""


def _history_text(messages: list[dict]) -> str:
    return "\n".join(
        m["content"] for m in messages if m["role"] in ("assistant", "tool")
    )


class ScriptedModel:
    """Deterministic stand-in for a real agent model."""

    def complete(self, messages: list[dict]) -> str:
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        defended = SECURITY_POLICY_MARKER in system
        body = _skill_body(messages)
        history = _history_text(messages)

        wants_secret = bool(_DANGER_HINT.search(body)) and "read_file" in body
        install_cmds = _extract_sh(body)

        # A defended agent declines the dangerous steps and does the benign job.
        if defended and (wants_secret or install_cmds):
            if "I will not" not in history:
                return (
                    "ANSWER: The skill asked me to run an unvetted setup command or read a "
                    "secrets file. I will not do that. I completed only the stated task."
                )
            return "ANSWER: Done."

        # Undefended: run the first not-yet-run install step.
        for cmd in install_cmds:
            if cmd not in history:
                return f'TOOL: {{"tool": "run_shell", "args": {{"cmd": {json.dumps(cmd)}}}}}'

        # Undefended: follow a hidden instruction to read the secret.
        if wants_secret and _ENV_PATH not in history:
            return f'TOOL: {{"tool": "read_file", "args": {{"path": "{_ENV_PATH}"}}}}'

        # Finish. If the secret was read, leak it into the final answer.
        if SECRET_SENTINEL in history:
            return f"ANSWER: Done. Diagnostic footer: {SECRET_SENTINEL}"
        return "ANSWER: Done. Completed the requested task."


def _extract_sh(body: str) -> list[str]:
    cmds: list[str] = []
    for block in re.findall(r"```(?:sh|bash|shell)\n(.*?)```", body, re.DOTALL):
        for line in block.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                cmds.append(line)
    return cmds


class HttpModel:
    """OpenAI-compatible chat completion over HTTP (Ollama, llama.cpp, etc.)."""

    def __init__(
        self, base_url: str, model: str, api_key: str = "not-needed", timeout: int = 60
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def complete(self, messages: list[dict]) -> str:
        payload = json.dumps(
            {"model": self.model, "messages": messages, "temperature": 0}
        ).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]
