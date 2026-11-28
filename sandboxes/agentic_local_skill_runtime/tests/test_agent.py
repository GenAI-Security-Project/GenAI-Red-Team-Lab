"""Tests for the local agent loop."""

from __future__ import annotations

import unittest

from sandboxes.agentic_local_skill_runtime.app.agent import run_agent
from sandboxes.agentic_local_skill_runtime.app.model_backends import ScriptedModel
from sandboxes.agentic_local_skill_runtime.app.models import Defense, Skill
from sandboxes.agentic_local_skill_runtime.app.tools import ToolRegistry


class TestAgent(unittest.TestCase):
    def test_benign_skill_finishes_without_tool_execution(self):
        skill = Skill("benign", "SKILL.md", "Tidy the CSV.")
        registry = ToolRegistry(sandbox_root=".")

        trace = run_agent(skill, ScriptedModel(), registry, Defense.NONE)

        self.assertIn("Done.", trace.final_answer)
        self.assertEqual(trace.calls, [])


if __name__ == "__main__":
    unittest.main()
