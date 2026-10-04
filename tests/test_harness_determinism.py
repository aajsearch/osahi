from osahi.tools import EchoTool
from tests.support import make_harness


def _run(text: str):
    harness = make_harness(
        turns=[{"kind": "finish", "text": text}],
        tools=[EchoTool()],
        allowed={"tool.echo"},
    )
    harness.run_until_blocked()
    return harness.events()


def test_same_script_replays_the_same_trajectory():
    assert _run("done") == _run("done")


def test_different_model_text_is_recorded_rather_than_forced_equal():
    assert _run("alpha") != _run("beta")
