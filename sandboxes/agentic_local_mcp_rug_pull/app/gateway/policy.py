"""Approval stages and the decision of which tools reach the model.

Stages (``APPROVAL_STAGE``):

* ``0``: no approval. Every discovered tool is offered to the model.
* ``1``: approval bound to ``(server, tool name)``. A changed definition under an
  approved name is offered without asking again.
* ``2``: approval bound to ``(server, tool name, digest)``. A changed definition
  is withheld until it is approved again.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.gateway.digest import tool_digest

VALID_STAGES = {0, 1, 2}
VALID_REFRESH = {"per_request", "on_list_changed", "reconnect"}


@dataclass(frozen=True)
class GatewayConfig:
    """Gateway behaviour selected at start-up."""

    approval_stage: int = 0
    refresh_policy: str = "per_request"
    approvals_file: Path = Path("/tmp/rug_pull_state/approvals.json")
    event_log: Path = Path("/tmp/rug_pull_state/gateway_events.jsonl")
    max_iterations: int = 8

    def __post_init__(self) -> None:
        if self.approval_stage not in VALID_STAGES:
            raise ValueError(f"APPROVAL_STAGE must be one of {sorted(VALID_STAGES)}")
        if self.refresh_policy not in VALID_REFRESH:
            raise ValueError(f"REFRESH_POLICY must be one of {sorted(VALID_REFRESH)}")

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "GatewayConfig":
        env = dict(os.environ if env is None else env)
        state = Path(env.get("STATE_DIR", "/tmp/rug_pull_state"))

        return cls(
            approval_stage=int(env.get("APPROVAL_STAGE", "0")),
            refresh_policy=env.get("REFRESH_POLICY", "per_request"),
            approvals_file=Path(env.get("APPROVALS_FILE", state / "approvals.json")),
            event_log=Path(env.get("EVENT_LOG", state / "gateway_events.jsonl")),
            max_iterations=int(env.get("MAX_ITERATIONS", "8")),
        )


@dataclass(frozen=True)
class Approval:
    server: str
    name: str
    digest: str


def load_approvals(path: Path) -> list[Approval]:
    """Read the approvals file written by the (simulated) user.

    Format: ``{"approvals": [{"server": ..., "name": ..., "digest": ...}]}``.
    A missing file means nothing is approved.
    """
    if not path.exists():
        return []
    document = json.loads(path.read_text(encoding="utf-8"))
    return [
        Approval(str(item["server"]), str(item["name"]), str(item.get("digest", "")))
        for item in document.get("approvals", [])
    ]


@dataclass(frozen=True)
class ToolDecision:
    server: str
    name: str
    digest: str
    offered: bool
    reason: str
    definition: dict[str, Any]


def decide(
    discovered: dict[str, list[dict[str, Any]]],
    approvals: list[Approval],
    config: GatewayConfig,
) -> list[ToolDecision]:
    """Decide, for every discovered tool, whether the model may see it."""
    by_name = {(a.server, a.name): a for a in approvals}

    counts: dict[str, int] = {}
    for tools in discovered.values():
        for tool in tools:
            counts[str(tool["name"])] = counts.get(str(tool["name"]), 0) + 1

    decisions: list[ToolDecision] = []
    for server in sorted(discovered):
        for tool in discovered[server]:
            name = str(tool["name"])
            digest = tool_digest(tool)
            granted = by_name.get((server, name))
            offered, reason = _stage_decision(config.approval_stage, granted, digest)

            if offered and counts[name] > 1:
                # Two servers exposing the same name: neither is offered, so an
                # attacker's server cannot shadow a trusted tool by name.
                offered, reason = False, "duplicate_name"
            decisions.append(ToolDecision(server, name, digest, offered, reason, tool))
    return decisions


def _stage_decision(
    stage: int, approval: Approval | None, digest: str
) -> tuple[bool, str]:
    if stage == 0:
        return True, "no_approval_required"
    if approval is None:
        return False, "pending_approval"
    if stage == 1:
        return True, "approved_by_name"
    if approval.digest == digest:
        return True, "approved_digest_match"
    return False, "definition_changed"
