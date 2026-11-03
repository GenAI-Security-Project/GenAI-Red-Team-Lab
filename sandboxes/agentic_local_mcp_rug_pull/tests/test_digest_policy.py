"""Digest and approval stages."""

import copy
import json
from pathlib import Path

import pytest

from app.gateway.digest import tool_digest
from app.gateway.policy import Approval, GatewayConfig, decide

DEFAULT = Path(__file__).resolve().parents[1] / "servers" / "toolbox_default.json"
TOOL_A = json.loads(DEFAULT.read_text())["definitions"]["A"]


def config(stage: int, **kwargs) -> GatewayConfig:
    return GatewayConfig(approval_stage=stage, **kwargs)


def test_digest_is_key_order_independent():
    reordered = json.loads(json.dumps(TOOL_A, sort_keys=True))
    assert tool_digest(reordered) == tool_digest(TOOL_A)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda t: t.__setitem__("description", t["description"] + " "),
        lambda t: t["inputSchema"]["properties"].__setitem__("x", {"type": "string"}),
        lambda t: t["annotations"].__setitem__("readOnlyHint", False),
        lambda t: t.__setitem__("title", "Format date (v2)"),
    ],
)
def test_digest_covers_every_rendered_or_annotated_field(mutate):
    changed = copy.deepcopy(TOOL_A)
    mutate(changed)
    assert tool_digest(changed) != tool_digest(TOOL_A)


def test_digest_excludes_meta():
    with_meta = {**copy.deepcopy(TOOL_A), "_meta": {"io.example/x": "anything"}}
    assert tool_digest(with_meta) == tool_digest(TOOL_A)


def _decide(stage, tool, approvals, **kwargs):
    return decide({"toolbox": [tool]}, approvals, config(stage, **kwargs))[0]


def test_stage0_offers_without_approval():
    assert _decide(0, TOOL_A, []).offered


def test_stage1_binds_to_name_only():
    approval = [Approval("toolbox", "format_date", "sha256:old")]
    changed = {**TOOL_A, "description": "different"}
    assert not _decide(1, TOOL_A, []).offered
    assert _decide(1, changed, approval).reason == "approved_by_name"


def test_stage2_withholds_changed_definition():
    approval = [Approval("toolbox", "format_date", tool_digest(TOOL_A))]
    changed = {**TOOL_A, "description": "different"}
    assert _decide(2, TOOL_A, approval).offered
    decision = _decide(2, changed, approval)
    assert not decision.offered and decision.reason == "definition_changed"


def test_approval_is_bound_to_the_configured_server():
    approval = [Approval("workspace", "format_date", tool_digest(TOOL_A))]
    assert _decide(2, TOOL_A, approval).reason == "pending_approval"


def test_duplicate_names_across_servers_are_withheld():
    decisions = decide({"a": [TOOL_A], "b": [TOOL_A]}, [], config(0))
    assert [d.offered for d in decisions] == [False, False]
    assert {d.reason for d in decisions} == {"duplicate_name"}


def test_config_rejects_unknown_values():
    with pytest.raises(ValueError):
        GatewayConfig.from_env({"APPROVAL_STAGE": "3"})
    with pytest.raises(ValueError):
        GatewayConfig.from_env({"REFRESH_POLICY": "sometimes"})
