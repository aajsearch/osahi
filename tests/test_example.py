from examples.echo_run import build_echo_run, main
from osahi.conformance import check_trajectory


def test_example_echo_run_completes_and_conforms(capsys):
    status, events = build_echo_run()
    assert status == "completed"
    assert check_trajectory(events) == []
    assert main() == 0
    printed = capsys.readouterr().out
    assert "tool.completed" in printed
    assert "status completed" in printed
