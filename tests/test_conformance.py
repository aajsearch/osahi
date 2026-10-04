import json

from osahi.conformance import check_trajectory
from osahi.schema import repo_root
from osahi.tools import DecliningTool, EchoTool, FlakyTool
from tests.support import make_harness
from tests.test_harness_escalate import _escalate

FIXTURES = repo_root() / "conformance" / "fixtures"
EXPECTED = json.loads((repo_root() / "conformance" / "expected.json").read_text(encoding="utf-8"))


def _load(name: str) -> list[dict]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_handwritten_accept_fixture_has_no_violations():
    assert check_trajectory(_load("accept-finish.json")) == []


def test_reject_fixtures_report_the_expected_rule():
    for name, rules in EXPECTED.items():
        found = {violation["rule"] for violation in check_trajectory(_load(name))}
        missing = set(rules) - found
        assert not missing, f"{name} did not report {missing}, found {found}"


def test_invoking_without_an_allow_decision_is_caught():
    events = _load("accept-finish.json")
    events.insert(
        3,
        {
            "event_id": "evt_0004",
            "run_id": "run_0001",
            "seq": 4,
            "type": "tool.invoked",
            "at": "2026-10-04T04:30:04Z",
            "payload": {"call_id": "call_0009", "tool_name": "echo", "arguments": {}},
            "causation_id": "evt_0003",
            "correlation_id": "run_0001",
        },
    )
    events[-1]["seq"] = 5
    events[-1]["event_id"] = "evt_0005"
    rules = {violation["rule"] for violation in check_trajectory(events)}
    assert "capability.allow_before_invoke" in rules


def test_reference_harness_trajectories_conform():
    echo = make_harness(
        turns=[
            {
                "kind": "tool",
                "text": "",
                "tool_name": "echo",
                "capability_id": "tool.echo",
                "arguments": {"text": "hi"},
            },
            {"kind": "finish", "text": "done"},
        ],
        tools=[EchoTool()],
        allowed={"tool.echo"},
    )
    echo.run_until_blocked()
    denied = make_harness(
        turns=[
            {
                "kind": "tool",
                "text": "",
                "tool_name": "echo",
                "capability_id": "tool.echo",
                "arguments": {},
            },
            {"kind": "finish", "text": "stopped"},
        ],
        tools=[EchoTool()],
        allowed=set(),
    )
    denied.run_until_blocked()
    flaky = make_harness(
        turns=[
            {
                "kind": "tool",
                "text": "",
                "tool_name": "flaky",
                "capability_id": "tool.flaky",
                "arguments": {},
            },
            {"kind": "finish", "text": "ok"},
        ],
        tools=[FlakyTool(fail_times=1)],
        allowed={"tool.flaky"},
    )
    flaky.run_until_blocked()
    declined = make_harness(
        turns=[
            {
                "kind": "tool",
                "text": "",
                "tool_name": "charge",
                "capability_id": "tool.charge",
                "arguments": {},
            },
            {"kind": "finish", "text": "after"},
        ],
        tools=[DecliningTool()],
        allowed={"tool.charge"},
    )
    declined.run_until_blocked()
    paused = make_harness(
        turns=[{"kind": "human", "text": "approve?"}, {"kind": "finish", "text": "sent"}],
        tools=[EchoTool()],
        allowed={"tool.echo"},
    )
    paused.run_until_blocked()
    paused.resume("yes")
    escalated = make_harness(
        turns=[
            {
                "kind": "tool",
                "text": "",
                "tool_name": "charge",
                "capability_id": "tool.charge",
                "arguments": {},
            }
        ],
        tools=[DecliningTool()],
        allowed={"tool.charge"},
        recovery_policy=_escalate,
    )
    escalated.run_until_blocked()
    for name, harness in {
        "echo": echo,
        "denied": denied,
        "flaky": flaky,
        "declined": declined,
        "paused": paused,
        "escalated": escalated,
    }.items():
        assert check_trajectory(harness.events()) == [], name
