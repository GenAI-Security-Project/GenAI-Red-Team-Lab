"""Tests for filesystem boundaries and record-only tool execution."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sandboxes.agentic_local_skill_runtime.app.tools import ToolRegistry


class TestToolRegistry(unittest.TestCase):
    def test_read_file_stays_inside_sandbox(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "sandbox"
            root.mkdir()
            (root / "inside.txt").write_text("inside", encoding="utf-8")
            outside = Path(temp_dir) / "outside.txt"
            outside.write_text("outside", encoding="utf-8")
            registry = ToolRegistry(sandbox_root=root)

            self.assertEqual(
                registry.call("read_file", {"path": "inside.txt"}), "inside"
            )
            outside_result = registry.call("read_file", {"path": "../outside.txt"})
            self.assertIn("no such file", outside_result)

    def test_run_shell_only_records(self):
        registry = ToolRegistry(sandbox_root=Path("."))

        result = registry.call("run_shell", {"cmd": "echo inert"})

        self.assertIn("not executed", result)
        self.assertEqual(registry.calls[0].tool, "run_shell")


if __name__ == "__main__":
    unittest.main()
