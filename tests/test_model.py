from osahi.model import ScriptedModel


def test_script_ends_in_an_empty_finish_once_turns_are_consumed():
    model = ScriptedModel([{"kind": "human", "text": "wait"}])
    assert model.next_turn([])["kind"] == "human"
    assert model.next_turn([{"role": "human", "content": "go"}]) == {"kind": "finish", "text": ""}
    assert model.contexts[1] == [{"role": "human", "content": "go"}]
