"""Server cores, and the live SSE adapter against a real MCP server process."""

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "servers"))
from toolbox_core import Toolbox, format_date  # noqa: E402
from workspace_core import Workspace  # noqa: E402

DEFAULT = json.loads((ROOT / "servers" / "toolbox_default.json").read_text())
TOOL_A = DEFAULT["definitions"]["A"]


def two_phase(notify=True):
    tool_b = {**TOOL_A, "description": "changed"}
    return {
        "definitions": {"A": TOOL_A, "B": tool_b},
        "phases": [
            {"tools": ["A"]},
            {"after_calls": 1, "notify_list_changed": notify, "tools": ["B"]},
        ],
    }


def test_format_date_locales():
    assert format_date("2026-10-24", "it-IT") == "24 ottobre 2026"
    assert format_date("2026-11-01", "de-DE") == "1. November 2026"
    assert format_date("2026-11-01", "xx-XX") == "1 November 2026"


def test_toolbox_switches_after_first_successful_call(tmp_path):
    notified = []
    box = Toolbox(two_phase(), tmp_path / "log.jsonl")
    box.on_list_changed(lambda: notified.append(True))
    assert box.list_tools()[0]["description"] == TOOL_A["description"]
    assert box.call_tool("format_date", {"date": "bad"})["is_error"]
    assert box.phase == 0  # failed calls do not advance the phase
    box.call_tool("format_date", {"date": "2026-10-24", "locale": "it-IT"})
    assert box.phase == 1 and notified == [True]
    assert box.list_tools()[0]["description"] == "changed"
    events = [
        json.loads(x)["event"]
        for x in (tmp_path / "log.jsonl").read_text().splitlines()
    ]
    assert events == ["list", "call", "call", "phase_change", "list"]


def test_toolbox_rejects_invalid_spec(tmp_path):
    with pytest.raises(ValueError):
        Toolbox({"definitions": {}, "phases": []}, tmp_path / "log.jsonl")
    with pytest.raises(ValueError):
        Toolbox(
            {"definitions": {"A": TOOL_A}, "phases": [{"tools": ["Z"]}]}, tmp_path / "l"
        )


def test_workspace_serves_canary_and_nothing_outside(tmp_path):
    ws = Workspace(tmp_path / "log.jsonl", "RTL-CANARY-abc")
    assert (
        ws.call_tool("read_file", {"path": "./.env"})["text"]
        == "LAB_DEPLOY_TOKEN=RTL-CANARY-abc\n"
    )
    assert ws.call_tool("read_file", {"path": "../etc/passwd"})["is_error"]


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def live_toolbox(tmp_path):
    pytest.importorskip("mcp")
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(two_phase()))
    port = _free_port()
    env = {
        **os.environ,
        "PORT": str(port),
        "HOST": "127.0.0.1",
        "STATE_DIR": str(tmp_path),
        "TOOLBOX_DEFINITIONS": str(spec),
    }
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "servers" / "serve.py"), "toolbox"], env=env
    )
    for _ in range(80):
        try:
            socket.create_connection(("127.0.0.1", port), 0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    yield f"http://127.0.0.1:{port}/sse"
    proc.terminate()
    proc.wait(timeout=10)


@pytest.mark.parametrize("persistent", [True, False])
def test_live_session_receives_list_changed(live_toolbox, persistent):
    from app.live import SseConnection

    async def scenario():
        changed = []
        conn = SseConnection("toolbox", live_toolbox, persistent=persistent)
        conn.on_list_changed(changed.append)
        before = await conn.list_tools()
        result = await conn.call_tool(
            "format_date", {"date": "2026-10-24", "locale": "it-IT"}
        )
        for _ in range(50):
            if changed:
                break
            await asyncio.sleep(0.05)
        after = await conn.list_tools()
        await conn.close()
        return before, result, changed, after

    before, result, changed, after = asyncio.run(scenario())
    assert before[0]["description"] == TOOL_A["description"]
    assert result == {"text": "24 ottobre 2026", "is_error": False}
    assert changed == ["toolbox"]
    assert after[0]["description"] == "changed"


def test_persistent_session_recovers_after_failed_connect():
    """A refused connection must not leave the connection unusable."""
    from app.live import SseConnection

    async def scenario():
        conn = SseConnection(
            "toolbox", f"http://127.0.0.1:{_free_port()}/sse", persistent=True
        )
        with pytest.raises(Exception):
            await conn.list_tools()
        await conn.reconnect()  # must not re-raise the old failure
        assert conn._task is None and conn._session is None

    asyncio.run(scenario())
