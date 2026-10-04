import pytest

from osahi.build import build_harness
from osahi.clock import FrozenClock
from osahi.config import ConfigError, HarnessConfig, load_config
from osahi.ids import SequentialIds
from osahi.model import ScriptedModel
from osahi.tools import EchoTool


def _document(**overrides) -> dict:
    document = {
        "spec_version": "0.1.0",
        "profile": "startup",
        "model": {"provider": "scripted", "name": "fixture-model"},
        "workload": {"id": "wl_demo", "name": "demo"},
        "harness": {"name": "acme-harness", "version": "0.1.0"},
        "policy": {"policy_id": "allowlist", "allow": ["tool.echo"]},
        "metadata": {},
    }
    document.update(overrides)
    return document


def _tool_turn(capability_id: str, tool_name: str = "echo") -> dict:
    return {
        "kind": "tool",
        "text": "",
        "tool_name": tool_name,
        "capability_id": capability_id,
        "arguments": {"text": "hello"},
    }


def test_builder_wires_identity_budget_and_retries_from_config():
    config = load_config(
        _document(
            context={"budget": 5},
            recovery={"max_retries": 0, "checkpoints": True},
            metadata={"ticket": "T-1"},
        )
    )
    harness = build_harness(
        config,
        tools=[EchoTool()],
        model=ScriptedModel([{"kind": "finish", "text": "done"}]),
        clock=FrozenClock("2026-10-04T04:30:00Z"),
        ids=SequentialIds(),
    )
    assert harness.context.budget == 5
    assert harness.max_retries == 0
    assert harness.policy.policy_id == "allowlist"
    assert harness.policy.allowed == {"tool.echo"}
    harness.run_until_blocked()
    started = harness.events()[0]["payload"]
    assert started["workload"] == {"id": "wl_demo", "name": "demo"}
    assert started["harness"] == {"name": "acme-harness", "version": "0.1.0"}
    assert started["model"] == {"provider": "scripted", "name": "fixture-model"}
    assert started["metadata"] == {"ticket": "T-1"}


def test_unlisted_tool_is_built_and_denied_at_runtime():
    config = load_config(_document(policy={"policy_id": "allowlist", "allow": []}))
    harness = build_harness(
        config,
        tools=[EchoTool()],
        model=ScriptedModel([_tool_turn("tool.echo"), {"kind": "finish", "text": "stopped"}]),
        clock=FrozenClock("2026-10-04T04:30:00Z"),
        ids=SequentialIds(),
    )
    assert harness.run_until_blocked() == "completed"
    types = [event["type"] for event in harness.events()]
    assert "tool.denied" in types
    assert "tool.invoked" not in types


def test_allow_list_may_reserve_a_capability_with_no_tool():
    config = load_config(
        _document(policy={"policy_id": "catalog", "allow": ["tool.echo", "tool.reserved"]})
    )
    harness = build_harness(
        config,
        tools=[EchoTool()],
        model=ScriptedModel([{"kind": "finish", "text": "done"}]),
    )
    assert harness.policy.allowed == {"tool.echo", "tool.reserved"}
    assert all(getattr(tool, "capability_id", None) != "tool.reserved" for tool in harness.tools.values())


def test_custom_policy_replaces_the_allowlist():
    class DenyAll:
        policy_id = "custom"

        def evaluate(self, capability_id: str) -> dict:
            return {"effect": "deny", "reason": "held", "policy_id": self.policy_id}

    config = load_config(_document())
    harness = build_harness(
        config,
        tools=[EchoTool()],
        model=ScriptedModel([_tool_turn("tool.echo"), {"kind": "finish", "text": "stopped"}]),
        clock=FrozenClock("2026-10-04T04:30:00Z"),
        ids=SequentialIds(),
        policy=DenyAll(),
    )
    harness.run_until_blocked()
    decided = next(event for event in harness.events() if event["type"] == "capability.decided")
    assert decided["payload"]["policy_id"] == "custom"
    assert decided["payload"]["effect"] == "deny"


def test_builder_rejects_a_raw_dict():
    with pytest.raises(ConfigError) as caught:
        build_harness({}, tools=[], model=ScriptedModel([]))
    assert "<root>" in str(caught.value)
    assert not isinstance({}, HarnessConfig)
