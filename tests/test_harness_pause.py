from osahi.tools import EchoTool
from tests.support import make_harness


def test_human_pause_resumes_without_dropping_the_request():
    harness = make_harness(
        turns=[
            {"kind": "human", "text": "approve the send?"},
            {"kind": "finish", "text": "sent"},
        ],
        tools=[EchoTool()],
        allowed={"tool.echo"},
    )
    assert harness.run_until_blocked() == "paused"
    assert harness.projection()["status"] == "paused"
    requested = [event for event in harness.events() if event["type"] == "human.requested"]
    assert requested[0]["payload"]["text"] == "approve the send?"
    assert harness.resume("yes") == "completed"
    types = [event["type"] for event in harness.events()]
    assert types.index("human.responded") < types.index("run.resumed")
    assert types.index("run.resumed") < types.index("run.completed")
    assert harness.events()[-1]["payload"]["text"] == "sent"
