from osahi.tools import AddTool, DecliningTool, EchoTool, FlakyTool


def test_echo_and_add_return_their_results_and_are_idempotent():
    assert EchoTool().invoke({"text": "hi"})["output"] == {"text": "hi"}
    assert AddTool().invoke({"a": 2, "b": 5})["output"] == {"sum": 7}
    assert EchoTool().idempotent is True
    assert DecliningTool().idempotent is False


def test_flaky_tool_fails_a_fixed_number_of_times_then_succeeds():
    tool = FlakyTool(fail_times=2)
    assert tool.invoke({})["ok"] is False
    assert tool.invoke({})["ok"] is False
    assert tool.invoke({})["output"] == {"recovered": True}
