from examples.enterprise_audit import main as enterprise_main
from examples.enterprise_audit import run_enterprise_audit
from examples.startup_echo import main as startup_main
from examples.startup_echo import run_startup_echo
from osahi.conformance import check_trajectory


def test_startup_echo_completes_and_conforms(capsys):
    status, events = run_startup_echo()
    assert status == "completed"
    assert check_trajectory(events) == []
    assert any(event["type"] == "tool.completed" for event in events)
    assert startup_main() == 0
    printed = capsys.readouterr().out
    assert "tool.completed" in printed
    assert "status completed" in printed


def test_enterprise_audit_denies_then_allows_and_records_config_on_the_run(capsys):
    status, events, config = run_enterprise_audit()
    assert status == "completed"
    assert check_trajectory(events) == []
    denied = next(event for event in events if event["type"] == "tool.denied")
    denied_calls = {
        event["payload"]["call_id"]
        for event in events
        if event["type"] == "tool.invoked"
    }
    assert denied["payload"]["call_id"] not in denied_calls
    assert denied["payload"]["capability_id"] == "tool.export"
    allowed = next(event for event in events if event["type"] == "tool.completed")
    assert allowed["payload"]["tool_name"] == "echo"
    assert allowed["payload"]["output"] == {"text": "audited"}
    started = events[0]["payload"]
    assert started["workload"] == {"id": config.workload.id, "name": config.workload.name}
    assert started["harness"] == {"name": config.harness.name, "version": config.harness.version}
    assert started["metadata"] == {
        "owner": config.metadata["owner"],
        "environment": config.metadata["environment"],
    }
    assert started["metadata"]["owner"] == "platform-team"
    assert enterprise_main() == 0
    printed = capsys.readouterr().out
    assert "denied export" in printed
    assert "allowed echo" in printed
    assert "status completed" in printed
